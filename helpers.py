import json
import pandas as pd
from string import ascii_uppercase
import requests
import json
import time

start = time.time()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def pulloffsets(cache=True):
    "Gets all labware offsets from the json data pulled from [IP]:31950/runs."
    s = requests.Session()
    s.headers.update({"Opentrons-Version": "2"})
    api_url = "http://127.0.0.1:31950/runs"
    run_history = s.get(api_url).json()
    
    out = {}
    for run in run_history["data"]:
        for labware in run["labwareOffsets"]:
            name = labware["definitionUri"].split("/")[1]
            location = labware["location"]["slotName"]
            offsets = labware["vector"]
            out[name] = {location: offsets}
    
    if cache:
        with open("offsets.json", "w") as f:
            json.dump(out, f)
    
    return out

class Loader:
    "Soft singleton implementation."
    protocol = None
    def __init__(self, protocol):
        if Loader.protocol is None:
            Loader.protocol = protocol
        self.offsets = pulloffsets()
    
    def load(self, file_name: str, location: str):
        loc = str(location)
        try:
            lw = self.protocol.load_labware(file_name, loc)
            self.apply_offsets(lw, loc)
            return lw
        except FileNotFoundError:
            #print(f"Custom labware [{file_name}] detected.")
            return self.custom_labware(file_name, loc)
    
    def custom_labware(self, file_name: str, location: str):
        with open(str(file_name)) as labware_file:
            labware_def = json.load(labware_file)
            c_lab = self.protocol.load_labware_from_definition(labware_def, location)
        self.apply_offsets(c_lab, location)
        return c_lab
    
    def apply_offsets(self, lab_object, location: str):
        #with open("offsets.json", "r") as f:
        #    offsets = json.load(f)
        try:
            offset_data = self.offsets[lab_object.name][location] #  gets dict of x, y, z
            x, y, z = offset_data["x"], offset_data["y"], offset_data["z"]
            lab_object.set_offset(x=x, y=y, z=z)
            print(f"{bcolors.OKGREEN}[{lab_object.name}] @ {location}: {x} {y} {z}{bcolors.ENDC}")
        except KeyError:
            print(f"{bcolors.WARNING}[{lab_object.name}] @ {location}: No offset data{bcolors.ENDC}")
    
    def wipe_deck(self):
        print("Clearing all objects from deck.")
        for i in range(1, 12):
            del self.protocol.deck[i]


            
            

def coord_iter(last_letter="H", last_number=12):
    letter_sequence = ascii_uppercase[:ascii_uppercase.index(last_letter) + 1]
    number_sequence = [i for i in range(1, last_number + 1)]
    coord_grid = [[f"{letter}{number}" for number in number_sequence] for letter in letter_sequence]
    for row in coord_grid:
        for item in row:
            yield item

class Worker:
    
    def __init__(self, sheet_name, index_col=0, vol_col=12, last_letter="H", last_number=12):
        self.index_col, self.vol_col = index_col, vol_col
        self.raw_instructions = self._parse_excel(sheet_name)
        self.sequence = list(coord_iter(last_letter, last_number))
        self.commands = list(map(self._command, self.raw_instructions))
        self._index = -1
    
    @property
    def is_finished(self):
        if self._index >= len(self.commands) - 1:
            return True
        else:
            return False


    def _command(self, sheet_entry: list):
        try:
            attempt_index = sheet_entry[self.index_col] - 1
            location = self.sequence[attempt_index]
        except IndexError:
            print("WARNING: There are more compounds than plate positions.")
            print(f"Command translation has stopped at index {attempt_index}.")
            raise StopIteration # cuts off mapping prematurely.
        return {
            "location": location,
            "volume": int(sheet_entry[self.vol_col])
        }
    
    def _parse_excel(self, sheet_name):
        print("Reading spreadsheet data...")
        xl_data = pd.read_excel(sheet_name, engine="openpyxl")
        raw_instructions = xl_data.values.tolist()
        print("Finished reading.")
        return raw_instructions
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.is_finished:
            raise StopIteration
        self._index += 1
        return self.commands[self._index]

end = time.time()
print(f"Helper initialized in {end - start:.2f} seconds.")