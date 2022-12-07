# Script name: barcoded_library_prep_part3_v1.py
# Directory path: cd C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe barcoded_library_prep_part3_v1.py -e

# FIRST VERSION OF SCRIPT (v1)
# Handles 12 samples at a time
# NEED TO UPDATE TO MATCH SOURCE COLUMNS FROM PART 2 AND USE CLEAN DEST COLUMNS

from opentrons import protocol_api
from opentrons import types

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Barcoded Library Prep, Part 3 (Adapter ligation and cleanup)',
    'description': '''WORK IN PROGRESS''',
    'author': 'Max Benjamin'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load modules into worktable locations
    magnetic_module = protocol.load_module('magnetic module gen2', 1)
    temperature_module = protocol.load_module('temperature module gen2', 3)

    # Set tip box locations #
    p20x1_tips1 = protocol.load_labware('opentrons_96_tiprack_20ul', 9)
    p300x8_tips1 = protocol.load_labware('opentrons_96_tiprack_300ul', 6)

    # Set labware locations #
    ethanol_reservoir = protocol.load_labware('agilent_1_reservoir_290ml', 4)
    water_reservoir = protocol.load_labware('agilent_1_reservoir_290ml', 5)
    reagent_tube_carrier = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 2)

    temp_plate = temperature_module.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul',
                                                 label='Temp-controlled LoBind Plate')
    mag_plate = magnetic_module.load_labware('eppendorf0030129504lobindpcr_96_wellplate_250ul',
                                             label='LoBind PCR plate with Adapter Basepiece on Mag Module')

    # Set mounted pipette types #
    p20x1 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[p20x1_tips1])
    p300x8 = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[p300x8_tips1])

    # Declare liquid handling variables #
    starting_sample_volume = 65
    adapter_mix_ii = 5
    nebnext_quick_ligation_reaction_buffer = 20
    t4_dna_ligase = 10
    ligation_rxn_volume = starting_sample_volume + adapter_mix_ii + nebnext_quick_ligation_reaction_buffer + t4_dna_ligase

    ampure_xp_beads_volume = 50
    long_fragment_buffer = 250
    elution_buffer = 15

    # Liquid handling commands for ligation rxn setup
    sample_well_list = [0, 1, 2, 3, 4, 5]  # This will need to be edited/updated each time it is used
    def rxn_setup_from_tubes(rxn_tube_count, sample_count):
        p20x1.flow_rate.aspirate = 2.0  # p20 single gen2 default flowrate = 7.6 ul/sec
        p20x1.flow_rate.dispense = 7.6
        reagent_tube_index = 0
        for tube in range(0, rxn_tube_count):
            sourceWellIndex = reagent_tube_index * 4
            if tube == 0:
                transfer_volume = adapter_mix_ii
            elif tube == 1:
                transfer_volume = nebnext_quick_ligation_reaction_buffer
            elif tube == 2:
                transfer_volume = t4_dna_ligase

            for well in range(0, sample_count):
                destinationWellIndex = sample_well_list[well]
                sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]
                destinationLocation = temp_plate.wells()[destinationWellIndex]
                p20x1.pick_up_tip()
                p20x1.aspirate(volume=transfer_volume,
                               location=sourceLocation.bottom(1.0),
                               rate=1.0)  # p20 gen2 single flow rate set to 2ul/sec above
                # Move commands to mimic a tip-wipe to eliminate reagent droplets
                tip_wipe_x_offset = 4.5
                p20x1.move_to(location=sourceLocation.top().move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                              speed=80,
                              publish=False)
                p20x1.move_to(location=sourceLocation.top(-5.0).move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                              speed=80,  # Default is 400mm/sec; set to Tip-touch max of 80mm/sec
                              publish=False)
                p20x1.move_to(location=sourceLocation.top().move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                              speed=80,
                              publish=False)
                # Dispense/mix/blowout commands
                p20x1.dispense(volume=transfer_volume,
                               location=destinationLocation.bottom(2.0),
                               rate=1.0)  # p20 gen2 single flow rate set to 7.6ul/sec above
                p20x1.mix(repetitions=1,
                          volume=20,
                          # location=,
                          rate=2.0) # Mix can be 200% faster than transfer
                p20x1.blow_out()
                p20x1.drop_tip()
            reagent_tube_index += 1
    rxn_setup_from_tubes(3, 6)

    # Mix adapter ligation rxn and incubate for 20min at 20C
    def pre_incubation_mix(column_count):
        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94
        for column in range(0, column_count):
            columnIndex = column * 8
            sourceLocation = temp_plate.wells()[columnIndex].bottom(1.0)
            tipLocation = p300x8_tips1.wells()[columnIndex]
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
            p300x8.mix(repetitions=3,
                       volume=(total_rxn_volume - 10),
                       location=sourceLocation,
                       rate=0.25)  # 25% flow rate to avoid bubbles
            p300x8.blow_out(sourceLocation)
            p300x8.drop_tip(location=tipLocation)
            p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    pre_incubation_mix(2)
    temperature_module.set_temperature(20)
    protocol.delay(seconds=0, minutes=20, msg="20C hold for 20min")

    # Add AMPure XP beads to samples
    def ampure_bead_addition(sample_count):
        ampure_xp_beads_volume = 50
        p20x1.flow_rate.aspirate = 15  # 200% p20 single gen2 default flowrate = 15.2 ul/sec
        p20x1.flow_rate.dispense = 15
        p20x1.flow_rate.blow_out = 15  # Increase blowout speed to compensate for higher dispense height
        sourceWellIndex = 24
        sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]

        p20x1.pick_up_tip()
        for well in range(0, sample_count):
            destinationWellIndex = sample_well_list[well]
            destinationLocation = temp_plate.wells()[destinationWellIndex].top(-2.0)  # Dispense from just barely inside the well
            p20x1.transfer(volume=ampure_xp_beads_volume,
                           source=sourceLocation,
                           dest=destinationLocation,
                           new_tip='never',
                           trash=True,
                           blow_out=True,
                           blowout_location='destination well',
                           touch_tip=True,
                           carryover=True)
        p20x1.drop_tip()
    ampure_bead_addition(6)
    total_rxn_volume += ampure_xp_beads_volume

    # Hula mix replication
    def hula_mix_replication(mix_time, mix_volume):
        mix_speed = mix_volume/10
        mix_count = (mix_time*60)/((mix_volume/mix_speed)*2)
        p300x8.flow_rate.aspirate = mix_speed  # 150ul at 15/sec = 1 mix per 20 sec = 3 mix/min; 10min = 30 cycles
        p300x8.flow_rate.dispense = mix_speed

        p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8.mix(repetitions=mix_count,
                   volume=mix_volume,
                   location=temp_plate.wells()[columnIndex].bottom(1.0),
                   rate=1.0)
        p300x8.blow_out()
        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex], num_channels=8)
    hula_mix_replication(10, total_rxn_volume) # Mix for 10min

    # Transfer samples from temp module plate to mag module plate
    def temp_to_mag_transfer(column_count, transfer_volume):
        sourceLocation = temp_plate.wells()[columnIndex].bottom(1.0)
        destinationLocation = mag_plate.wells()[columnIndex].center()

        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94

        for column in range(0, column_count):
            columnIndex = column * 8
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
            p300x8.aspirate(volume=transfer_volume,
                            location=sourceLocation,
                            rate=0.1)  # 10% default flowrate for better aspiration at well bottom
            p300x8.dispense(volume=transfer_volume,
                            location=destinationLocation,
                            rate=1.0)
            p300x8.blow_out()
            p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
    temp_to_mag_transfer(2,total_rxn_volume)
