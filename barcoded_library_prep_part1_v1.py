# Script name: barcoded_library_prep_part1_v1.py
# Directory path: C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe barcoded_library_prep_part1_v1.py -e

# FIRST VERSION OF SCRIPT
# Handles 1 sample at a time

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

    # Liquid handling commands for gDNA repair rxn setup #
    p20x1.flow_rate.aspirate = 2.0  # p20 single gen2 default flowrate = 7.6 ul/sec
    p20x1.flow_rate.dispense = 7.6
    loopCount = 0
    for tube in list(range(1, 5)):
        loopCount += 1

        if tube == 1:
            transfer_volume = nebnext_ffpe_dna_repair_buffer
        elif tube == 2:
            transfer_volume = ultra_ii_end_prep_reaction_buffer
        elif tube == 3:
            transfer_volume = ultra_ii_end_prep_enzyme_mix
        elif tube == 4:
            transfer_volume = nebnext_ffpe_dna_repair_mix

        sourceWellIndex = (loopCount - 1) * 4
        destinationWellIndex = 0

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
    p300x8.pick_up_tip()
    p300x8.mix(repetitions=3,
               volume=(total_rxn_volume / 2),
               location=temp_plate.wells()[0].bottom(3.0),
               rate=1.0)
    p300x8.drop_tip(location=p300x8_tips1.wells()[0])
    p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[0], num_channels=8)

    # Incubate samples at 20C for 10min
    temperature_module.set_temperature(20)
    protocol.delay(seconds=0, minutes=10, msg="20C hold for 10min")

    # Incubate samples at 65C for 10min
    temperature_module.set_temperature(65)
    protocol.delay(seconds=0, minutes=10, msg="65C hold for 10min")
    temperature_module.deactivate()

    # Add AMPure XP beads to samples
    ampure_xp_beads = 30
    sourceWellIndex = 16
    destinationWellIndex = 0

    sourceLocation = reagent_tube_carrier.wells()[sourceWellIndex]
    destinationLocation = temp_plate.wells()[destinationWellIndex].top(2.0)

    p20x1.flow_rate.aspirate = 15  # 2x p20 single gen2 default flowrate = 15.2 ul/sec
    p20x1.flow_rate.dispense = 15
    p20x1.transfer(volume=ampure_xp_beads,
                   source=sourceLocation,
                   dest=destinationLocation,
                   new_tip='once',
                   trash=True,
                   touch_tip=False,
                   blow_out=True,
                   blowout_location='destination well',
                   mix_before=(5, 20),
                   #mix_after=(1, 20),
                   carryover=True)

    total_rxn_volume += ampure_xp_beads

    # Very slow sample mix to replace Hula mixing step
    p300x8.flow_rate.aspirate = 18  # 90ul at 18/sec = 1 mix cycle per 10 sec = 6 cycles/min; 10min = 60 cycles
    p300x8.flow_rate.dispense = 18
    p300x8.pick_up_tip()
    p300x8.mix(repetitions=60,
               volume=total_rxn_volume,
               location=temp_plate.wells()[0].bottom(1.0),
               rate=1.0)

    # Transfer samples from temp module plate to mag module plate
    p300x8.flow_rate.aspirate = 18
    p300x8.flow_rate.dispense = 94
    p300x8.aspirate(volume=total_rxn_volume,
                    location=temp_plate.wells()[0].bottom(0.25),
                    rate=1.0)
    p300x8.dispense(volume=total_rxn_volume,
                    location=mag_plate.wells()[0].center(),
                    rate=1.0)
    p300x8.blow_out()
    p300x8.drop_tip(location=p300x8_tips1.wells()[0])
    p300x8_tips1.return_tips(start_well=p300x8_tips1.wells()[0],num_channels=8)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=11) # NEEDS TO BE TESTED STILL. Try height_from_base instead in future.
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove supernatant from magbeads
    p300x8.flow_rate.aspirate = 94 # p300 multi gen2 default flowrate = 94 ul/sec
    p300x8.flow_rate.dispense = 94
    p300x8.pick_up_tip()
    p300x8.aspirate(volume=total_rxn_volume,
                    location=mag_plate.wells()[0].bottom(0.25),
                    rate=0.25) # 25% very slow aspirate speed
    p300x8.drop_tip() # VERIFY THAT NO BLOWOUT IS NEEDED IN TRASH

    # Disengage magnet module
    magnetic_module.disengage()

    # First Ethanol wash
    ethanol_volume = 200
    sourceLocation = ethanol_reservoir.wells()[0]
    destinationLocation = mag_plate.wells()[0].center().move(types.Point(x=1.0, y=0, z=0)) # Center-right in well

    p300x8.flow_rate.aspirate = 94  # p300 multi gen2 default flowrate = 94 ul/sec
    p300x8.flow_rate.dispense = 94

    p300x8.pick_up_tip()
    p300x8.aspirate(volume=ethanol_volume,
                    location=sourceLocation,
                    rate=0.5) # 50% slow aspirate speed for ethanol
    p300x8.air_gap(volume=20) # 20ul airgap to keep ethanol from dripping
    p300x8.dispense(volume=220,
                    location=destinationLocation,
                    rate=2.0) # 200% fast forceful dispense

    for mix in range(0,3): # 3 EtOH washes
        p300x8.aspirate(volume=ethanol_volume,
                        location=mag_plate.wells()[0].bottom(1.0),
                        rate=1.0)
        p300x8.dispense(volume=ethanol_volume,
                        location=destinationLocation,
                        rate=2.0)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=11)  # NEEDS TO BE TESTED STILL. Try height_from_base instead in future.
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove Ethanol from magbeads
    p300x8.aspirate(volume=ethanol_volume,
                    location=mag_plate.wells()[0].bottom(0.25),
                    rate=0.25) # 25% very slow aspirate speed
    p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
    p300x8.drop_tip() # VERIFY THAT NO BLOWOUT IS NEEDED IN TRASH

    # Disengage magnet module
    magnetic_module.disengage()

    # Second Ethanol wash (variable values reused from first wash above)
    p300x8.pick_up_tip()
    p300x8.aspirate(volume=ethanol_volume,
                    location=sourceLocation,
                    rate=0.5)  # 50% slow aspirate speed for ethanol
    p300x8.air_gap(volume=20)  # 20ul airgap to keep ethanol from dripping
    p300x8.dispense(volume=220,
                    location=destinationLocation,
                    rate=2.0)  # 200% fast forceful dispense

    for mix in range(0, 3):  # 3 EtOH washes
        p300x8.aspirate(volume=ethanol_volume,
                        location=mag_plate.wells()[0].bottom(1.0),
                        rate=1.0)
        p300x8.dispense(volume=ethanol_volume,
                        location=destinationLocation,
                        rate=2.0)

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=11)  # NEEDS TO BE TESTED STILL. Try height_from_base instead in future.
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Remove Ethanol from magbeads
    p300x8.aspirate(volume=ethanol_volume,
                    location=mag_plate.wells()[0].bottom(0.25),
                    rate=0.25)  # 25% very slow aspirate speed
    p300x8.air_gap(volume=20) # 20ul airgap to keep ethanol from dripping
    p300x8.drop_tip()  # VERIFY THAT NO BLOWOUT IS NEEDED IN TRASH

    # Delay to evaporate residual Ethanol
    protocol.delay(seconds=30, minutes=0, msg="Wait for residual Ethanol to evaporate")

    # Disengage magnet module
    magnetic_module.disengage()

    # Water elution
    water_volume = 61
    sourceLocation = water_reservoir.wells()[0]

    p300x8.pick_up_tip()
    p300x8.aspirate(volume=water_volume,
                    location=sourceLocation,
                    rate=1.0)
    p300x8.dispense(volume=water_volume,
                    location=destinationLocation,
                    rate=2.0)  # 200% fast forceful dispense

    for mix in range(0, 5):  # 3 water washes
        p300x8.aspirate(volume=water_volume,
                        location=mag_plate.wells()[0].bottom(0.5),
                        rate=0.5) # 50% slow aspirate speed to avoid air bubbles
        p300x8.dispense(volume=water_volume,
                        location=destinationLocation,
                        rate=2.0)
    p300x8.drop_tip()

    # Delay to incubate at room temp
    protocol.delay(seconds=0, minutes=2, msg="Incubate at room temp while gDNA elutes")

    # Engage magnet module to pellet magbeads
    magnetic_module.engage(height=11)  # NEEDS TO BE TESTED STILL. Try height_from_base instead in future.
    protocol.delay(seconds=0, minutes=2, msg="Wait for magnetic beads to pellet")

    # Separate eluate from magbeads
    p300x8.transfer(volume=water_volume,
                   source=mag_plate.wells()[0],
                   dest=temp_plate.wells()[8], # Dest is shifted over by 1 column for sample purity
                   new_tip='once',
                   trash=True,
                   touch_tip=True,
                   blow_out=True,
                   blowout_location='destination well')

    # 4C hold for sample stability
    temperature_module.set_temperature(4)
    protocol.delay(seconds=0, minutes=60*18, msg="Retrieve samples for Qubit quant")
