import json
import opentrons.execute
from opentrons import protocol_api
import pandas as pd


print("Script has initiated.")


def Command(sheet_data: list) -> dict:
        'Expects [LETTER, index, volume]'
        return {
            "location": f"{sheet_data[0]}{sheet_data[1]}",
            "volume": int(sheet_data[2])
        }

def setup():
    print("Reading spreadsheet data...")
    xl_data = pd.read_excel("OT2_test_data.xlsx", engine="openpyxl")
    raw_instructions = xl_data.values.tolist()
    print("Finished reading.")
    instructions = list(map(Command, raw_instructions))
    return instructions


def custom_labware(name, location):
    protocol = opentrons.execute.get_protocol_api("2.12")
    with open(str(name)) as labware_file:
        labware_def = json.load(labware_file)
        return protocol.load_labware_from_definition(labware_def, int(location))


try:
    instructions = setup()
except FileNotFoundError:
    print("Excel file not on OT2. Oh well!")
    
#print(instructions)


metadata = {
    "apiLevel": "2.12",
    "protocolName": "Sequential distribution from excel test",
    "author": "RexChem"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware setup
    tips_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', 8)
    tips_1000.set_offset(x=-1.10, y=1.40, z=-0.50)
    
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 7)
    tips_300.set_offset(x=0, y=-0.4, z=0)
 
    reservoir = custom_labware("rexchem_1_reservoir_225112.5ul.json", 1)
    
    plate = custom_labware("plateone_96_wellplate_500ul.json", 6)
    plate.set_offset(x=0.30, y=0.70, z=-0.60)
    
    p1000 = protocol.load_instrument("p1000_single", "left", tip_racks=[tips_1000])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Commands
    p1000.pick_up_tip()
    p300.pick_up_tip()
    for job in instructions:
        vol = job["volume"]
        active = p300
        if vol > 300:
            active = p1000
        active.transfer(vol, reservoir["A1"], plate[job["location"]], new_tip="never")
    
    p1000.drop_tip()
    p300.drop_tip()

