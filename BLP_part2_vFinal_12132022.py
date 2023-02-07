# Script name: BLP_part2_vFinal_12132022.py
# Directory path: cd C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe BLP_part2_vFinal_12132022.py -e

# SECOND VERSION OF SCRIPT, FINAL MAJOR UPDATES (vFinal)
# Handles 12 samples at a time

from opentrons import protocol_api
from opentrons import types

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Barcoded Library Prep, Part 2 (Native Barcode Ligation)',
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
    starting_sample_volume = 22.5
    native_barcode_volume = 2.5
    blunt_ta_ligase_mastermix_volume = 25
    total_rxn_volume = starting_sample_volume + native_barcode_volume + blunt_ta_ligase_mastermix_volume

    # Liquid handling commands for barcoding rxn setup
    sample_well_list = [32,33,34,35,36,37,40,41,42,43,44,45]  # Well list for samples in columns 5 and 6
    def rxn_setup_from_tubes(sample_count):
        p20x1.flow_rate.aspirate = 2.0  # p20 single gen2 default flowrate = 7.6 ul/sec
        p20x1.flow_rate.dispense = 7.6

        # Liquid handling for barcode tube dispensing
        barcode_tube_count = sample_count # 12 barcode tubes, 1 for each sample
        for tube in list(range(0, barcode_tube_count)):
            sourceLocation = reagent_tube_carrier.wells()[tube]
            destinationLocation = temp_plate.wells()[sample_well_list[tube]]
            tube_adjustment_offset = 18.5
            transfer_volume = native_barcode_volume

            p20x1.pick_up_tip()
            p20x1.aspirate(volume=transfer_volume,
                           location=sourceLocation.bottom(tube_adjustment_offset),
                           rate=1.0)  # p20 gen2 single flow rate set to 2ul/sec above
            p20x1.dispense(volume=transfer_volume,
                           location=destinationLocation.bottom(2.0),
                           rate=1.0)  # p20 gen2 single flow rate set to 7.6ul/sec above
            p20x1.mix(repetitions=1,
                      volume=transfer_volume,
                      rate=2.0)  # Mix can be 200% faster than transfer
            p20x1.blow_out()
            p20x1.drop_tip()

        # Liquid handling for blunt ta ligase mastermix dispensing
        reagent_tube_index = 12
        p20x1.pick_up_tip()
        for destination_well in list(range(0, sample_count)):
            sourceLocation = reagent_tube_carrier.wells()[reagent_tube_index]
            destinationLocation = temp_plate.wells()[sample_well_list[destination_well]]
            transfer_volume = blunt_ta_ligase_mastermix_volume/2

            for dispense in list((range(0,2))):
                p20x1.aspirate(volume=transfer_volume,
                               location=sourceLocation.bottom(1.0),
                               rate=1.0)  # p20 gen2 single flow rate set to 2ul/sec above

                # Move commands to mimic a tip-wipe to eliminate reagent droplets
                for tip_wipe in range(0, 2):
                    if tip_wipe == 0:
                        tip_wipe_x_offset = 4.5
                    elif tip_wipe == 1:
                        tip_wipe_x_offset = -4.5

                    p20x1.move_to(location=sourceLocation.top().move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                                  speed=60,
                                  publish=False)
                    p20x1.move_to(location=sourceLocation.top(-5.0).move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                                  speed=60,  # Default is 400mm/sec; set to Tip-touch max of 80mm/sec
                                  publish=False)
                    p20x1.move_to(location=sourceLocation.top().move(types.Point(x=tip_wipe_x_offset, y=0, z=0)),
                                  speed=60,
                                  publish=False)

                p20x1.dispense(volume=transfer_volume,
                               location=destinationLocation.top(-4.0),
                               rate=1.0)  # p20 gen2 single flow rate set to 7.6ul/sec above
                p20x1.blow_out()
        p20x1.drop_tip()
    rxn_setup_from_tubes(12)

    # Mix barcoding rxn and incubate for 20min at 20C
    def pre_incubation_mix(column_count):
        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94
        for column in range(0,column_count):
            columnIndex = 32 + (column*8) # Well Index 32 to start at column 5
            sourceLocation = temp_plate.wells()[columnIndex].bottom(1.0)
            tipLocation = p300x8_tips1.wells()[column*8]
            p300x8.pick_up_tip(location=tipLocation)
            p300x8.mix(repetitions=3,
                    volume=(total_rxn_volume-10),
                    location=sourceLocation,
                    rate=0.25) # 25% flow rate to avoid bubbles
            p300x8.blow_out(sourceLocation)
            p300x8.drop_tip(location=tipLocation)
            p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    pre_incubation_mix(2)
    temperature_module.set_temperature(20)
    protocol.delay(seconds=0, minutes=20, msg="20C hold for 20min")

    # Add AMPure XP beads to samples
    ampure_xp_beads_volume = 50
    def ampure_bead_addition(sample_count):
        p20x1.flow_rate.aspirate = 15  # 200% p20 single gen2 default flowrate = 15.2 ul/sec
        p20x1.flow_rate.dispense = 15
        p20x1.flow_rate.blow_out = 15  # Increase blowout speed to compensate for higher dispense height
        sourceWellIndex = 16
        sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]

        p20x1.pick_up_tip()
        for well in range(0, sample_count):
            destinationWellIndex = sample_well_list[well]
            destinationLocation = temp_plate.wells()[destinationWellIndex].top(-4.0)  # Dispense from just barely inside the well
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
    ampure_bead_addition(12)
    total_rxn_volume += ampure_xp_beads_volume

    # Hula mix replication
    def hula_mix_replication(column_count):
        p300x8.flow_rate.aspirate = 20  # 100ul at 20/sec = 1 mix per 10 sec = 0.5 cycle/min; 10min = 5 cycles
        p300x8.flow_rate.dispense = 20
        for cycle in range(0, 5):  # 5 cycles X 3 mixes for each of 2 columns per cycle
            for column in range(0, column_count):
                columnIndex = 32 + (column * 8) # Well Index 32 to start at column 5
                tipLocation = p300x8_tips1.wells()[column*8]
                p300x8.pick_up_tip(location=tipLocation)
                p300x8.mix(repetitions=3,
                           volume=total_rxn_volume,
                           location=temp_plate.wells()[columnIndex].bottom(1.0),
                           rate=1.0)
                p300x8.blow_out()
                p300x8.drop_tip(location=tipLocation)
                p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    hula_mix_replication(2)

    # Transfer samples from temp module plate to mag module plate
    def temp_to_mag_transfer(column_count, transfer_volume):

        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94

        for column in range(0, column_count):
            columnIndex = 32 + (column * 8) # Well Index 32 to start at column 5
            tipLocation = p300x8_tips1.wells()[column*8]
            sourceLocation = temp_plate.wells()[columnIndex].bottom(1.0)
            destinationLocation = mag_plate.wells()[columnIndex].center()
            p300x8.pick_up_tip(location=tipLocation)
            p300x8.aspirate(volume=transfer_volume, # Extra volume to get everything
                            location=sourceLocation,
                            rate=0.1)  # 10% default flowrate for better aspiration at well bottom
            p300x8.dispense(volume=transfer_volume,
                            location=destinationLocation,
                            rate=1.0)
            p300x8.blow_out()
            p300x8.drop_tip(location=tipLocation)
    temp_to_mag_transfer(2,total_rxn_volume+10)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(14.5) # This should bring magbeads to the bottom/right (odd-number columns) or bottom/left(even-number columns)
    protocol.delay(seconds=0, minutes=3, msg="Wait for magnetic beads to pellet")

    # Remove supernatant from magbeads, first column only
    def supernatant_removal(column_index):
        p300x8.flow_rate.aspirate = 94  # Slow flow rate to minimize magbead loss
        p300x8.flow_rate.dispense = 94

        if column_index == 32:
            tipLocation = p300x8_tips1.wells()[0]
            x_offset = -1.5
        if column_index == 40:
            tipLocation = p300x8_tips1.wells()[8]
            x_offset = 1.5

        sourceLocation = mag_plate.wells()[column_index].bottom(0).move(types.Point(x=x_offset, y=0, z=0))  # Bottom left/bottom right well locations

        p300x8.pick_up_tip(location=tipLocation)
        p300x8.aspirate(volume=total_rxn_volume,
                        location=sourceLocation,
                        rate=0.10) # 10% very slow aspirate speed
        p300x8.drop_tip()

    supernatant_removal(32) # Well index 32 for column 5 supernatant removal

    # 2x Ethanol washes, first column only
    def gentle_ethanol_wash(column_index, residual_ethanol_removal_volume):
        ethanol_volume = 200
        p300x8.flow_rate.aspirate = 94  # Default flow rate
        p300x8.flow_rate.dispense = 94

        if column_index == 32:
            tipLocation = p300x8_tips1.wells()[0]
            x_offset = 1.5
        if column_index == 40:
            tipLocation = p300x8_tips1.wells()[8]
            x_offset = -1.5

        sourceLocation = ethanol_reservoir.wells()[0].bottom(1.5)
        destinationLocation = mag_plate.wells()[column_index].top(-4.0).move(types.Point(x=x_offset, y=0, z=0))  # Upper-right (odd-numbered columns) or upper left (even-numbered columns) in well

        p300x8.pick_up_tip(location=tipLocation)

        for each in range(0,2): # Loop through 2 EtOH washes
            # Add Ethanol to magbeads
            p300x8.aspirate(volume=ethanol_volume,
                            location=sourceLocation,
                            rate=0.5)  # 50% slow aspirate for ethanol
            p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
            p300x8.dispense(volume=220,
                            location=destinationLocation,
                            rate=0.15)  # 15% gentle drip dispense to keep magbeads from getting knocked to bottom of wells

            # Remove Ethanol from magbeads
            if column_index == 32:
                aspirate_x_offset = -1.5
            if column_index == 40:
                aspirate_x_offset = 1.5

            sourceLocation = mag_plate.wells()[column_index].bottom(-1.0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns) or right (even columns)

            p300x8.aspirate(volume=ethanol_volume+residual_ethanol_removal_volume,
                            location=sourceLocation,
                            rate=0.10)  # 10% very slow aspirate speed
            p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
            p300x8.blow_out(location=protocol.fixed_trash['A1'])

        p300x8.drop_tip()

    gentle_ethanol_wash(32,25) # Well index 32 for column 5 ethanol washes

    # Disengage magnet module
    magnetic_module.disengage()

    # Elute gDNA from magbeads, first column only
    def water_elution(column_index, water_volume):
        # Water addition
        p300x8.flow_rate.aspirate = 94  # Reset flow rate to default
        p300x8.flow_rate.dispense = 94  # Reset flow rate to default

        if column_index == 32:
            aspirate_x_offset = -1.5
            dispense_x_offset = 1.5
        if column_index == 40:
            aspirate_x_offset = 1.5
            dispense_x_offset = -1.5

        sourceLocation = water_reservoir.wells()[0]
        destinationLocation = mag_plate.wells()[column_index].top(-4.0).move(types.Point(x=dispense_x_offset, y=0, z=0))

        p300x8.pick_up_tip()
        p300x8.aspirate(volume=water_volume,
                        location=sourceLocation,
                        rate=1.0)
        p300x8.dispense(volume=water_volume,
                        location=destinationLocation,
                        rate=1.0)  # Standard water dispense

        # Now mix to resuspend magbeads in water
        sourceLocation = mag_plate.wells()[column_index].bottom(-1.0).move(types.Point(x=aspirate_x_offset, y=0, z=0))
        destinationLocation = mag_plate.wells()[column_index].center().move(types.Point(x=dispense_x_offset, y=0, z=0))

        for mix in range(0, 30):  # 30 mixes
            p300x8.aspirate(volume=water_volume,
                            location=sourceLocation,
                            rate=1.0)
            p300x8.dispense(volume=water_volume,
                            location=destinationLocation,
                            rate=3.0)  # Faster dispense to knock magbeads off well sides
        p300x8.blow_out(destinationLocation)
        p300x8.drop_tip()

    water_elution(32,26) # Elute in 26ul water

    # Re-engage magnet module; second column sample processing starts here
    magnetic_module.engage(14.5)
    protocol.delay(seconds=0, minutes=3, msg="Wait for magnetic beads to pellet")
    # Remove supernatant from magbeads, second column only
    supernatant_removal(40)
    # 2x Ethanol washes, second column only
    gentle_ethanol_wash(40,25)
    # Disengage magnet module
    magnetic_module.disengage()
    # Elute gDNA from magbeads, second column only
    water_elution(40,26)
    # Engage magnet module to pellet all magbeads
    magnetic_module.engage(14.5)
    protocol.delay(seconds=0, minutes=3, msg="Wait for magnetic beads to pellet")

    # Transfer eluate from mag module plate to temp module plate
    def mag_to_temp_transfer(column_count, transfer_volume):
        transfer_volume += 5
        p300x8.flow_rate.aspirate = 9.4  # 10% default p300 multi gen2 aspirate speed
        p300x8.flow_rate.dispense = 94  # Default p300 multi gen2 dispense speed

        for column in range(0, column_count):  # Slowly aspirate eluate from magbeads in each column
            sourceColumnIndex = 32 + (column * 8)
            destinationColumnIndex = 16 + sourceColumnIndex

            if column == 0:
                aspirate_x_offset = -1.5
            elif column == 1:
                aspirate_x_offset = 1.5

            sourceLocation = mag_plate.wells()[sourceColumnIndex].bottom(-1.0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns) or right (even columns)
            destinationLocation = temp_plate.wells()[destinationColumnIndex].bottom(1.0)

            p300x8.transfer(volume=transfer_volume,
                            source=sourceLocation,
                            dest=destinationLocation, # Dest is shifted over by 2 columns (into clean columns) for sample purity
                            new_tip='once',
                            trash=True,
                            blow_out=True,
                            blowout_location='destination well',
                            touch_tip=False)
    mag_to_temp_transfer(2,26)

    # 4C hold for sample stability
    temperature_module.set_temperature(4)