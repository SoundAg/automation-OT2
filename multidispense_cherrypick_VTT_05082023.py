# Script name: multidispense_cherrypick_VTT_04292023.py
# Directory path: cd C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe multidispense_cherrypick_VTT_04292023.py -e

import csv
import math
from opentrons import protocol_api

metadata = {
    'protocolName': 'Multidispense Cherrypick:[Volume Validation Test - 05/08/2023]',
    'author': 'Max Benjamin',
    'description': 'Perform multidispense hitpick transfers',
    'apiLevel': '2.8'
}

csv_raw = '''
Source Plate,Source Well,Destination Plate,Destination Well,Volume
Source 1,A1,Destination 1,A1,50
Source 1,A2,Destination 2,A2,50
Source 1,A3,Destination 3,A3,50
Source 1,A4,Destination 4,A4,50
Source 1,A1,Destination 1,A1,50
Source 1,A2,Destination 2,A2,50
Source 1,A3,Destination 3,A3,50
Source 1,A4,Destination 4,A4,50
Source 1,A1,Destination 1,A1,50
Source 1,A2,Destination 2,A2,50
Source 1,A3,Destination 3,A3,50
Source 1,A4,Destination 4,A4,50
Source 1,A1,Destination 1,A1,50
Source 1,A2,Destination 2,A2,50
Source 1,A3,Destination 3,A3,50
Source 1,A4,Destination 4,A4,50
'''

csv_data = csv_raw.splitlines()[1:] # Discard the blank first line.
csv_reader = csv.DictReader(csv_data)
transfer_info = []
for row in csv_reader:
    transfer_info.append(row)

# The following block creates a list of dictionaries, where each dictionary reps a unique Source Plate:Source Well combo, based on the csv_raw input above.
# Output transfer_info_consolidated list is used as a reference to iterate through transfers in liquid handling command block.
transfer_info_consolidated = []
for transfer in transfer_info:
    # Get the unique identifier for each transfer
    transfer_key = (transfer['Source Plate'], transfer['Source Well'])

    # Check if the transfer_key already exists in transfer_info_consolidated
    transfer_exists = False
    for consolidated_transfer in transfer_info_consolidated:
        if (consolidated_transfer['Source Plate'], consolidated_transfer['Source Well']) == transfer_key:
            # If transfer already exists in transfer_info_consolidated, update the lists
            consolidated_transfer['Destination Wells'].append(transfer['Destination Well'])
            consolidated_transfer['Volumes'].append(float(transfer['Volume']))
            consolidated_transfer['Destination Plates'].append(transfer['Destination Plate'])
            consolidated_transfer['Total Volume'] += float(transfer['Volume'])
            consolidated_transfer['Dispense Count'] = len(consolidated_transfer['Destination Wells'])
            transfer_exists = True
            break

    if not transfer_exists:
        # If transfer does not exist in transfer_info_consolidated, create a new dictionary
        dest_well_list = [transfer['Destination Well']]
        volumes_list = [float(transfer['Volume'])]
        dest_plate_list = [transfer['Destination Plate']]
        total_volume = float(transfer['Volume'])
        dispense_count = 1
        transfer_info_consolidated.append({
            'Source Plate': transfer['Source Plate'],
            'Source Well': transfer['Source Well'],
            'Destination Plates': dest_plate_list,
            'Destination Wells': dest_well_list,
            'Volumes': volumes_list,
            'Total Volume': total_volume,
            'Dispense Count': dispense_count
        })

def run(protocol: protocol_api.ProtocolContext):

    # Load labware to the Worktable
    tiprack_1 = protocol.load_labware('opentrons_96_tiprack_300ul', '3', 'Tip Rack 1')
    tiprack_2 = protocol.load_labware('opentrons_96_tiprack_300ul', '6', 'Tip Rack 2')
    tiprack_3 = protocol.load_labware('opentrons_96_tiprack_300ul', '9', 'Tip Rack 3')

    source_plate_labware_type = 'thermoscientificnunc_96_wellplate_2000ul'
    source_plate_1 = protocol.load_labware(source_plate_labware_type, '1', 'Source Plate 1')
    source_plate_2 = protocol.load_labware(source_plate_labware_type, '4', 'Source Plate 2')
    source_plate_3 = protocol.load_labware(source_plate_labware_type, '7', 'Source Plate 3')
    source_plate_4 = protocol.load_labware(source_plate_labware_type, '10', 'Source Plate 4')

    destination_plate_labware_type = 'thermoscientificnunc_96_wellplate_2000ul'
    destination_plate_1 = protocol.load_labware(destination_plate_labware_type, '2', 'Destination Plate 1')
    destination_plate_2 = protocol.load_labware(destination_plate_labware_type, '5', 'Destination Plate 2')
    destination_plate_3 = protocol.load_labware(destination_plate_labware_type, '8', 'Destination Plate 3')
    destination_plate_4 = protocol.load_labware(destination_plate_labware_type, '11', 'Destination Plate 4')

    pipette_head_type = 'p300_single_gen2'
    pipette = protocol.load_instrument(pipette_head_type, mount='left', tip_racks=[tiprack_1,tiprack_2,tiprack_3])

    # Time for pipetting commands! Liquid handling commands live in this codeblock.
    if pipette_head_type == 'p20_single_gen2':
        max_pipette_volume = 20
    if pipette_head_type == 'p300_single_gen2':
        max_pipette_volume = 300
    if pipette_head_type == 'p1000_single_gen2':
        max_pipette_volume = 1000

    # Iterate through each transfer group, moving through 1 source plate/source well combination at a time.
    for dictionary in transfer_info_consolidated:
        # Set source location for aspirate command.
        source_plate = dictionary['Source Plate']
        source_well = dictionary['Source Well']

        # Set source location for each aspirate.
        if source_plate == "Source 1":
            source_location = source_plate_1.wells_by_name()[source_well].bottom(0.5)
        if source_plate == "Source 2":
            source_location = source_plate_2.wells_by_name()[source_well].bottom(0.5)
        if source_plate == "Source 3":
            source_location = source_plate_3.wells_by_name()[source_well].bottom(0.5)
        if source_plate == "Source 4":
            source_location = source_plate_4.wells_by_name()[source_well].bottom(0.5)

        # Set destination location to be the correct variable based on string name.
        destination_plates_list = dictionary['Destination Plates']
        renamed_destination_plates_list = []
        for n in range(0,len(destination_plates_list)):
            if destination_plates_list[n] == "Destination 1":
                renamed_destination_plate = destination_plate_1
                renamed_destination_plates_list.append(renamed_destination_plate)
            if destination_plates_list[n] == "Destination 2":
                renamed_destination_plate = destination_plate_2
                renamed_destination_plates_list.append(renamed_destination_plate)
            if destination_plates_list[n] == "Destination 3":
                renamed_destination_plate = destination_plate_3
                renamed_destination_plates_list.append(renamed_destination_plate)
            if destination_plates_list[n] == "Destination 4":
                renamed_destination_plate = destination_plate_4
                renamed_destination_plates_list.append(renamed_destination_plate)

        destination_wells_list = dictionary['Destination Wells']

        distribute_compatible_dest_wells_list = [plate.wells_by_name()[well_name] for plate, well_name in zip(renamed_destination_plates_list, destination_wells_list)]
        destination_volumes_list = dictionary['Volumes']
        total_volume = dictionary['Total Volume']
        dispense_count = dictionary['Dispense Count']

        # Liquid handling commands go here.
        pipette.flow_rate.dispense = 92.86 * 0.5 # 50% flow rate on dispense
        pipette.distribute(volume=destination_volumes_list,
                            source=source_location,
                            dest=[well.top(-5) for well in distribute_compatible_dest_wells_list],
                            new_tip='once',
                            touch_tip=True,
                            blow_out=True,
                            blowout_location='source well',
                            mix_before=(3,300),
                            disposal_volume=50)
        