# Script name: barcoded_library_prep_part1_v2.py
# Directory path: C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe barcoded_library_prep_part1_v2.py -e

# SECOND VERSION OF SCRIPT
# Handles 12 samples at a time

from opentrons import protocol_api
from opentrons import types

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Barcoded Library Prep, Part 1 (gDNA repair and end-prep)',
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
    starting_sample_volume = 48
    nebnext_ffpe_dna_repair_buffer = 3.5
    ultra_ii_end_prep_reaction_buffer = 3.5
    ultra_ii_end_prep_enzyme_mix = 3
    nebnext_ffpe_dna_repair_mix = 2
    total_rxn_volume = starting_sample_volume + nebnext_ffpe_dna_repair_buffer + ultra_ii_end_prep_reaction_buffer + ultra_ii_end_prep_enzyme_mix + nebnext_ffpe_dna_repair_mix

    # Set temp module to 4C to prevent rxn from starting during setup
    temperature_module.set_temperature(4)
    temperature_module.await_temperature(4)

    # Liquid handling commands for gDNA repair rxn setup #
    p20x1.flow_rate.aspirate = 2.0 # p20 single gen2 default flowrate = 7.6 ul/sec
    p20x1.flow_rate.dispense = 7.6

    reagent_tube_list = list(range(1, 5))
    reagent_tube_index = 0
    for tube in reagent_tube_list:
        reagent_tube_index += 1
        sourceWellIndex = (reagent_tube_index - 1) * 4

        if tube == 1:
            transfer_volume = nebnext_ffpe_dna_repair_buffer
        elif tube == 2:
            transfer_volume = ultra_ii_end_prep_reaction_buffer
        elif tube == 3:
            transfer_volume = ultra_ii_end_prep_enzyme_mix
        elif tube == 4:
            transfer_volume = nebnext_ffpe_dna_repair_mix

        sample_well_list = [0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13]
        for well in range(0, 12):
            destinationWellIndex = sample_well_list[well]
            sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]
            destinationLocation = temp_plate.wells()[destinationWellIndex]

            p20x1.transfer(volume=transfer_volume,
                        source=sourceLocation,
                        dest=destinationLocation,
                        new_tip='once',
                        trash=True,
                        touch_tip=False,
                        blow_out=True,
                        blowout_location='destination well',
                        # mix_before = ,
                        mix_after=(1, transfer_volume * 2),
                        carryover=True)

    # Mix samples before temp module is activated
    p300x8.flow_rate.aspirate = 94  # p300 multi gen2 default flowrate = 94
    p300x8.flow_rate.dispense = 94

    for column in range(0,2):
        columnIndex = column*8
        p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8.mix(repetitions=3,
                volume=(total_rxn_volume / 2),
                location=temp_plate.wells()[columnIndex].bottom(3.0),
                rate=1.0)
        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex], num_channels=8)

    # Incubate samples at 20C for 10min
    temperature_module.set_temperature(20)
    protocol.delay(seconds=0, minutes=10, msg="20C hold for 10min")

    # Incubate samples at 65C for 10min
    temperature_module.set_temperature(65)
    protocol.delay(seconds=0, minutes=10, msg="65C hold for 10min")
    
    # Incubate samples at 4C for the rest of the protocol/overnight
    temperature_module.set_temperature(4)

    # Add AMPure XP beads to samples
    ampure_xp_beads = 30
    sourceWellIndex = 16
    sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]

    p20x1.flow_rate.aspirate = 15  # 200% p20 single gen2 default flowrate = 15.2 ul/sec
    p20x1.flow_rate.dispense = 15
    p20x1.flow_rate.blow_out = 15 # Increase blowout speed to compensate for higher dispense height

    for well in range(0,12):
        destinationWellIndex = sample_well_list[well]
        destinationLocation = temp_plate.wells()[destinationWellIndex].top(2.0) # Dispense from just barely inside the well

        p20x1.transfer(volume=ampure_xp_beads,
                    source=sourceLocation,
                    dest=destinationLocation,
                    new_tip='once',
                    trash=True,
                    touch_tip=False,
                    blow_out=True,
                    blowout_location='destination well',
                    #mix_before=(5, 20),
                    #mix_after=(1, 20),
                    carryover=True)

    total_rxn_volume += ampure_xp_beads
        
    # Very slow sample mix to replace Hula mixing step
    p300x8.flow_rate.aspirate = 18  # 90ul at 18/sec = 1 mix cycle per 10 sec = 6 cycles/min; 10min = 60 cycles
    p300x8.flow_rate.dispense = 18

    for cycle in range(0,10): # 5 cycles X 2 mixes for each of 2 columns per cycle
        for column in range(0,2):
            columnIndex = column*8
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
            p300x8.mix(repetitions=2,
                    volume=total_rxn_volume,
                    location=temp_plate.wells()[column].bottom(1.0),
                    rate=1.0)
            p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
            p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex], num_channels=8)
    
    # Transfer samples from temp module plate to mag module plate
    p300x8.flow_rate.aspirate = 18 
    p300x8.flow_rate.dispense = 94

    for column in range(0,2):
        columnIndex = column*8
        p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8.aspirate(volume=total_rxn_volume,
                        location=temp_plate.wells()[columnIndex].bottom(0.5),
                        rate=1.0)
        p300x8.dispense(volume=total_rxn_volume,
                        location=mag_plate.wells()[columnIndex].center(),
                        rate=1.0)
        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])

    # Engage magnet module to pellet magbeads
    mag_engage_height = 15 # This should bring magbeads to the center/right (odd-number columns) or center/left(even-number columns) of wells. Reused in subsequent mag module steps.
    magnetic_module.engage(height=mag_engage_height) 
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove supernatant from magbeads
    p300x8.flow_rate.aspirate = 94 # p300 multi gen2 default flowrate = 94 ul/sec
    p300x8.flow_rate.dispense = 94

    for column in range(0,2):
        columnIndex = column*8
        p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8.aspirate(volume=total_rxn_volume,
                        location=mag_plate.wells()[columnIndex].bottom(0.5),
                        rate=0.25) # 25% very slow aspirate speed
        p300x8.blow_out(location=protocol.fixed_trash['A1'])
        p300x8.drop_tip() # VERIFY THAT NO BLOWOUT IS NEEDED IN TRASH

    # Disengage magnet module
    magnetic_module.disengage()

    # First Ethanol wash
    ethanol_volume = 200
    sourceLocation = ethanol_reservoir.wells()[0]

    p300x8.flow_rate.aspirate = 94  # p300 multi gen2 default flowrate = 94 ul/sec
    p300x8.flow_rate.dispense = 94

    p300x8.pick_up_tip()
    for column in range(0,2): # Add EtOH to both columns to keep beads from drying 
        columnIndex = column*8

        if column == 0:
            x_offset = 1.0
        elif column == 1:
            x_offset = -1.0

        destinationLocation = mag_plate.wells()[columnIndex].top(1.0).move(types.Point(x=x_offset, y=0, z=0)) # Upper-right (odd-numbered columns) or upper left (even-numbered columns) in well
        
        p300x8.aspirate(volume=ethanol_volume,
                        location=sourceLocation,
                        rate=0.5) # 50% slow aspirate speed for ethanol
        p300x8.air_gap(volume=20) # 20ul airgap to keep ethanol from dripping
        p300x8.dispense(volume=220,
                        location=destinationLocation,
                        rate=2.0) # 200% fast forceful dispense

    for column in range(0,2): # Now mix both columns, using currently loaded tips for the first and loading new ones for the second
        columnIndex = column*8

        if column == 0:
            x_offset = 1.0
        elif column == 1:
            x_offset = -1.0

        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0)
        destinationLocation = mag_plate.wells()[columnIndex].center().move(types.Point(x=x_offset, y=0, z=0)) # Middle-right (odd-number columns) or middle left (even-numbered columns) in well

        if column == 1:
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        
        for mix in range(0,5): # 5 EtOH washes
            p300x8.aspirate(volume=ethanol_volume,
                            location=sourceLocation,
                            rate=1.0)
            p300x8.dispense(volume=ethanol_volume,
                            location=destinationLocation,
                            rate=2.0)

        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex],num_channels=8)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=mag_engage_height) 
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove Ethanol from magbeads
    for column in range(0,2):
        columnIndex = column*8
        sourceLocation = mag_plate.wells()[columnIndex].bottom(0.5)

        p300x8.pick_up_tip()
        p300x8.aspirate(volume=ethanol_volume,
                        location=sourceLocation,
                        rate=0.25) # 25% very slow aspirate speed
        p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
        p300x8.blow_out(location=protocol.fixed_trash['A1'])
        p300x8.drop_tip()

    # Disengage magnet module
    magnetic_module.disengage()

    # Second Ethanol wash (variable values reused from first wash above)
    p300x8.pick_up_tip()
    for column in range(0,2): # Add EtOH to both columns to keep beads from drying 
        columnIndex = column*8

        if column == 0:
            x_offset = 1.0
        elif column == 1:
            x_offset = -1.0

        destinationLocation = mag_plate.wells()[columnIndex].top(1.0).move(types.Point(x=x_offset, y=0, z=0)) # Upper-right (odd-numbered columns) or upper left (even-numbered columns) in well
        
        p300x8.aspirate(volume=ethanol_volume,
                        location=sourceLocation,
                        rate=0.5) # 50% slow aspirate speed for ethanol
        p300x8.air_gap(volume=20) # 20ul airgap to keep ethanol from dripping
        p300x8.dispense(volume=220,
                        location=destinationLocation,
                        rate=2.0) # 200% fast forceful dispense

    for column in range(0,2):  # Now mix both columns, using currently loaded tips for the first and loading new ones for the second
        columnIndex = column * 8

        if column == 0:
            x_offset = 1.0
        elif column == 1:
            x_offset = -1.0

        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0)
        destinationLocation = mag_plate.wells()[columnIndex].center().move(
            types.Point(x=x_offset, y=0, z=0))  # Middle-right (odd-numbered columns) or middle-left (even-numbered columns) in well

        if column == 1:
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])

        for mix in range(0, 5):  # 5 EtOH washes
            p300x8.aspirate(volume=ethanol_volume,
                            location=sourceLocation,
                            rate=1.0)
            p300x8.dispense(volume=ethanol_volume,
                            location=destinationLocation,
                            rate=2.0)

        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex], num_channels=8)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=mag_engage_height) 
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove Ethanol from magbeads
    for column in range(0,2):
        columnIndex = column*8
        sourceLocation = mag_plate.wells()[columnIndex].bottom(0.5)

        p300x8.pick_up_tip()
        p300x8.aspirate(volume=ethanol_volume,
                        location=sourceLocation,
                        rate=0.25) # 25% very slow aspirate speed
        p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
        p300x8.blow_out(location=protocol.fixed_trash['A1'])
        p300x8.drop_tip()

    # Disengage magnet module
    magnetic_module.disengage()

    # Delay to evaporate residual Ethanol
    protocol.delay(seconds=30, minutes=0, msg="Wait for residual Ethanol to evaporate")

    # Water elution
    water_volume = 61
    sourceLocation = water_reservoir.wells()[0]
    
    p300x8.pick_up_tip()
    p300x8.aspirate(volume=water_volume*2, # Multiaspirate
                    location=sourceLocation,
                    rate=1.0)

    destinationLocation = mag_plate.wells()[0].top(1.0).move(types.Point(x=1.0, y=0, z=0)) # Upper-right in well; First dispense
    p300x8.dispense(volume=water_volume,
                    location=destinationLocation,
                    rate=2.0) # 200% fast forceful dispense

    destinationLocation = mag_plate.wells()[8].top(1.0).move(types.Point(x=-1.0, y=0, z=0)) # Upper-left in well; Second dispense
    p300x8.dispense(volume=water_volume,
                    location=destinationLocation,
                    rate=2.0) # 200% fast forceful dispense

    for column in range(0,2): # Now mix both columns, using currently loaded tips for the first and loading new ones for the second
        columnIndex = column*8

        if column == 0:
            x_offset = 1.0
        elif column == 1:
            x_offset = -1.0

        sourceLocation = mag_plate.wells()[columnIndex].bottom(1.0)
        destinationLocation = mag_plate.wells()[columnIndex].center().move(types.Point(x=x_offset, y=0, z=0)) # Middle-right (odd-numbered columns) or middle-left (even-numbered columns) in well

        if column == 1:
            p300x8.pick_up_tip(location=p300x8_tips1.wells()[columnIndex])
        
        for mix in range(0,5): # 5 Water washes
            p300x8.aspirate(volume=water_volume,
                            location=sourceLocation,
                            rate=1.0)
            p300x8.dispense(volume=water_volume,
                            location=destinationLocation,
                            rate=2.0)

        p300x8.drop_tip(location=p300x8_tips1.wells()[columnIndex])
        p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[columnIndex],num_channels=8)

    # Delay to incubate at room temp
    protocol.delay(seconds=0, minutes=2, msg="Incubate at room temp while gDNA elutes")

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=mag_engage_height)  
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Separate eluate from magbeads
    p300x8.flow_rate.aspirate = 23.5 # 25% default p300 multi gen2 aspirate speed
    p300x8.flow_rate.dispense = 94 # Default p300 multi gen2 dispense speed

    for column in range(0,2): # Slowly aspirate eluate from magbeads in each column
        columnIndex = column*8
        sourceLocation = mag_plate.wells()[columnIndex].bottom(0.5)
        destinationLocation = temp_plate.wells()[16 + columnIndex].bottom(1.0)

        p300x8.transfer(volume=water_volume,
                        source=sourceLocation,
                        dest=destinationLocation, # Dest is shifted over by 2 columns (into clean columns) for sample purity
                        new_tip='once',
                        trash=True,
                        touch_tip=True,
                        blow_out=True,
                        blowout_location='destination well')

    # 4C hold for sample stability
    protocol.delay(seconds=0, minutes=60*18, msg="Retrieve samples for Qubit quant")