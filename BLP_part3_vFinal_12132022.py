# Script name: barcoded_library_prep_part3_v2.py
# Directory path: cd C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe barcoded_library_prep_part3_v2.py -e

# FIRST VERSION OF SCRIPT (v1)
# Handles 6 pooled samples at a time from column 9 of a 96w plate

from opentrons import protocol_api
from opentrons import types
import math

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
    reagent_reservoir_plate = protocol.load_labware('thermoscientificnunc_96_wellplate_1300ul', 4)
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
    sample_well_list = [64, 65, 66, 67, 68, 69] # Well list for pooled samples in column 9 
    def rxn_setup_from_tubes(sample_count):
        p20x1.flow_rate.aspirate = 2.0  # p20 single gen2 default flowrate = 7.6 ul/sec
        p20x1.flow_rate.dispense = 7.6

        reagent_tube_count = 3 # AMII, Ligation buffer, Ligase
        reagent_tube_index = 0
        for tube in range(0, reagent_tube_count):
            sourceWellIndex = reagent_tube_index * 4
            if tube == 0:
                transfer_volume = adapter_mix_ii
            elif tube == 1:
                transfer_volume = nebnext_quick_ligation_reaction_buffer
            elif tube == 2:
                transfer_volume = t4_dna_ligase

            for well in range(0, len(sample_well_list)):
                destinationWellIndex = sample_well_list[well]
                sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]
                destinationLocation = temp_plate.wells()[destinationWellIndex]
                p20x1.pick_up_tip()
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
    rxn_setup_from_tubes(6)

    # Mix adapter ligation rxn and incubate for 20min at 20C
    def pre_incubation_mix(column_count):
        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94
        for column in range(0, column_count):
            columnIndex = 64 + (column*8) # Well Index 64 to start at column 9
            sourceLocation = temp_plate.wells()[columnIndex].bottom(1.0)
            tipLocation = p300x8_tips1.wells()[column*8]
            p300x8.pick_up_tip(location=tipLocation)
            p300x8.mix(repetitions=3,
                       volume=(ligation_rxn_volume-10),
                       location=sourceLocation,
                       rate=0.25)  # 25% flow rate to avoid bubbles
            p300x8.blow_out(sourceLocation)
            p300x8.drop_tip(location=tipLocation)
            p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    pre_incubation_mix(1)
    temperature_module.set_temperature(20)
    protocol.delay(seconds=0, minutes=20, msg="20C hold for 20min")

    # Add AMPure XP beads to samples
    def ampure_bead_addition(sample_count):
        p20x1.flow_rate.aspirate = 15  # 200% p20 single gen2 default flowrate = 15.2 ul/sec
        p20x1.flow_rate.dispense = 15
        p20x1.flow_rate.blow_out = 15  # Increase blowout speed to compensate for higher dispense height
        sourceWellIndex = 12
        sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]

        p20x1.pick_up_tip()
        for well in range(0, len(sample_well_list)):
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
    total_rxn_volume = ligation_rxn_volume + ampure_xp_beads_volume

    # Hula mix replication
    def hula_mix_replication(mix_time, mix_volume):
        mix_speed = mix_volume/10 # Calc to get 1 aspirate or dispense per 10 sec; 1 mix cycle per 20 sec
        mix_count = math.ceil((mix_time*60)/20) # Turn min into sec, then div by seconds per cycle  
        p300x8.flow_rate.aspirate = mix_speed  # 150ul at 15/sec = 1 mix per 20 sec = 3 mix/min; 10min = 30 cycles
        p300x8.flow_rate.dispense = mix_speed
        
        columnIndex = 64
        tipLocation = p300x8_tips1.wells()[0]
        p300x8.pick_up_tip()
        p300x8.mix(repetitions=mix_count,
                   volume=mix_volume,
                   location=temp_plate.wells()[columnIndex].bottom(1.0),
                   rate=1.0)
        p300x8.blow_out()
        p300x8.drop_tip(location=tipLocation)
        p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    hula_mix_replication(10, total_rxn_volume) # Mix for 10min

    # Transfer samples from temp module plate to mag module plate
    def temp_to_mag_transfer(transfer_volume, columnIndex):
        sourceLocation = temp_plate.wells()[columnIndex].bottom(0)
        destinationLocation = mag_plate.wells()[columnIndex].center()
        tipLocation=p300x8_tips1.wells()[0]

        p300x8.flow_rate.aspirate = 94
        p300x8.flow_rate.dispense = 94
        p300x8.pick_up_tip()
        p300x8.aspirate(volume=transfer_volume,
                        location=sourceLocation,
                        rate=0.1)  # 10% default flowrate for better aspiration at well bottom
        p300x8.dispense(volume=transfer_volume,
                        location=destinationLocation,
                        rate=1.0)
        p300x8.blow_out()
        p300x8.drop_tip(location=tipLocation)
        p300x8_tips1.return_tips(start_well=tipLocation, num_channels=8)
    temp_to_mag_transfer(total_rxn_volume, 64)

    # Engage magnet module to pellet magbeads
    mag_engage_height = 12.0  # This should bring magbeads to the bottom/right (odd-number columns) or bottom/left(even-number columns) of wells.
    magnetic_module.engage(height=mag_engage_height)
    protocol.delay(seconds=0, minutes=3, msg="Wait for magnetic beads to pellet")

    # Remove supernatant from magbeads
    def supernatant_removal():
        p300x8.flow_rate.aspirate = 94  # Slow flow rate to minimize magbead loss (see below)
        p300x8.flow_rate.dispense = 94
        
        columnIndex = 64 # Well Index 64 to start at column 9
        tipLocation = p300x8_tips1.wells()[0]

        x_offset = -1.5
        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0).move(types.Point(x=x_offset, y=0, z=0))  # Bottom left well location

        p300x8.pick_up_tip(location=tipLocation)
        p300x8.aspirate(volume=total_rxn_volume,
                        location=sourceLocation,
                        rate=0.10)  # 10% very slow aspirate speed
        p300x8.drop_tip()
    supernatant_removal()

    # Disengage magnet for Long Fragment Buffer Addition, then wash with Long Fragment Buffer
    def long_fragment_buffer_wash():
        magnetic_module.disengage()
        columnIndex = 64 # Well Index 64 to start at column 9
        # Add LFB to column 9 magplate
        sourceLocation = reagent_reservoir_plate.wells()[0].bottom(0) # Long Fragment Buffer located in wells A1:F1
        x_offset = 1.5
        destinationLocation = mag_plate.wells()[columnIndex].top(-4.0).move(types.Point(x=x_offset, y=0, z=0))  # Upper-right (odd-numbered columns) in well

        p300x8.flow_rate.aspirate = 94  # default aspirate flow rate
        p300x8.flow_rate.dispense = 94 # default dispense flow rate

        p300x8.pick_up_tip()
        p300x8.aspirate(volume=long_fragment_buffer,
                        location=sourceLocation,
                        rate=0.5)
        p300x8.air_gap(volume=20)  # 20ul airgap to keep LFB from dripping
        p300x8.blow_out(destinationLocation)

        # Now mix, using currently loaded tips
        aspirate_x_offset = -1.5
        dispense_x_offset = 1.5
        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns)
        destinationLocation = mag_plate.wells()[columnIndex].top(-2.0).move(types.Point(x=dispense_x_offset, y=0, z=0))  # Top-right (odd-number columns)

        for loop in range(0,3):
            p300x8.aspirate(volume=long_fragment_buffer,
                            location=sourceLocation,
                            rate=0.50)  # 50% slow aspirate
            p300x8.dispense(volume=long_fragment_buffer,
                            location=destinationLocation,
                            rate=2.0)  # 200% fast dispense to dislodge beads
            p300x8.blow_out(destinationLocation)

        # Remove LFB from magbeads, using currently loaded tips
        magnetic_module.engage(mag_engage_height)
        protocol.delay(seconds=0, minutes=3, msg="Wait for magnetic beads to pellet")

        aspirate_x_offset = -1.5
        sourceLocation = mag_plate.wells()[columnIndex].bottom(0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns)

        p300x8.aspirate(volume=long_fragment_buffer,
                        location=sourceLocation,
                        rate=0.10)  # 10% very slow aspirate speed
        p300x8.air_gap(volume=20)  # 20ul airgap to keep buffer from dripping
        p300x8.blow_out(location=protocol.fixed_trash['A1'])
        p300x8.drop_tip()
    long_fragment_buffer_wash()

    # Repeat Long Fragment Buffer Wash
    long_fragment_buffer_wash()

    # Resuspend magbeads in Elution Buffer
    def elution_buffer_addition(transfer_volume):
        transfer_volume += 5 # DV adjustment

        magnetic_module.disengage()
        columnIndex = 64  # Well Index 64 to start at column 9
        # Add EB to column 9 magplate
        sourceLocation = reagent_reservoir_plate.wells()[1].bottom(0)  # Elution Buffer located in wells A2:F2
        x_offset = 1.5
        destinationLocation = mag_plate.wells()[columnIndex].top(-4.0).move(types.Point(x=x_offset, y=0, z=0))  # Upper-right (odd-numbered columns) in well

        p300x8.flow_rate.aspirate = 94  # default aspirate flow rate
        p300x8.flow_rate.dispense = 94  # default dispense flow rate

        p300x8.pick_up_tip()
        p300x8.aspirate(volume=transfer_volume,
                        location=sourceLocation,
                        rate=0.25) # Slow aspirate due to low volume
        p300x8.air_gap(volume=20)  # 20ul airgap to keep EB from dripping
        p300x8.blow_out(destinationLocation)

        # Now mix, using currently loaded tips
        aspirate_x_offset = -1.5
        dispense_x_offset = 1.5
        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns)
        destinationLocation = mag_plate.wells()[columnIndex].center().move(types.Point(x=dispense_x_offset, y=0, z=0))  # Middle-right (odd-number columns)

        for loop in range(0, 5):
            p300x8.aspirate(volume=transfer_volume,
                            location=sourceLocation,
                            rate=0.25)  # 25% slow aspirate due to low volume
            p300x8.dispense(volume=transfer_volume,
                            location=destinationLocation,
                            rate=0.50)  # 50% slow aspirate due to low volume
            p300x8.blow_out(destinationLocation)
        p300x8.drop_tip()
    elution_buffer_addition(elution_buffer)

    # Transfer samples to temp module, then 20min incubation at 37C
    def mag_to_temp_transfer(transfer_volume, sourceColumnIndex):
        transfer_volume += 5
        p300x8.flow_rate.aspirate = 9.4  # 10% default p300 multi gen2 aspirate speed
        p300x8.flow_rate.dispense = 94  # Default p300 multi gen2 dispense speed

       # Slowly aspirate eluate from magbeads
        destinationColumnIndex = 8 + sourceColumnIndex

        if ((sourceColumnIndex/8)+1) % 2 == 0:
            aspirate_x_offset = 1.5
        elif ((sourceColumnIndex/8)+1) % 2 != 0:
            aspirate_x_offset = -1.5

        sourceLocation = mag_plate.wells()[sourceColumnIndex].bottom(0).move(types.Point(x=aspirate_x_offset, y=0, z=0))  # Bottom-left (odd columns) or right (even columns)
        destinationLocation = temp_plate.wells()[destinationColumnIndex].bottom(1.0)

        p300x8.transfer(volume=transfer_volume,
                        source=sourceLocation,
                        dest=destinationLocation,
                        # Dest is shifted over by 1 column (into clean columns) for sample purity
                        new_tip='once',
                        trash=True,
                        blow_out=True,
                        blowout_location='destination well',
                        touch_tip=False)
    mag_to_temp_transfer(elution_buffer, 64)
    temperature_module.set_temperature(37)
    protocol.delay(seconds=0, minutes=20, msg="Wait for Elution Incubation")

    # Transfer samples back to mag module
    temp_to_mag_transfer(elution_buffer, 72)

    # Separate eluate from magbeads, transferring back to temp module
    magnetic_module.engage(mag_engage_height)
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")
    mag_to_temp_transfer(elution_buffer, 72)

    # 4C hold to preserve prepped samples at end of script
    temperature_module.set_temperature(4)