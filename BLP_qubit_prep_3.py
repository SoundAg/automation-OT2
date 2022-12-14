# Script name: qubit_prep_3_v1.py
# Directory path: cd C:\Users\Max\PycharmProjects\pythonProject\ot2_scripting
# Command line simulation = opentrons_simulate.exe qubit_prep_3_v1.py -e

# FIRST VERSION OF SCRIPT (v1)
# Preps Qubit tubes for 6 samples plus 2 standards
# Same as Qubit Prep 1, but with different source wells

from opentrons import protocol_api
from opentrons import types

metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Barcoded Library Prep: Qubit Prep 3',
    'description': '''WORK IN PROGRESS''',
    'author': 'Max Benjamin'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load modules into worktable locations
    temperature_module = protocol.load_module('temperature module gen2', 3)

    temp_plate = temperature_module.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul',
                                                 label='Temp-controlled LoBind Plate')

    # Set tip box locations #
    p20x1_tips1 = protocol.load_labware('opentrons_96_tiprack_20ul', 9)
    p1000x1_tips1 = protocol.load_labware('opentrons_96_tiprack_1000ul', 6)

    # Set labware locations #
    reagent_tube_carrier = protocol.load_labware('opentrons_24_tuberack_generic_2ml_screwcap', 2)
    qubit_buffer_carrier = protocol.load_labware('opentrons_6_tuberack_falcon_50ml_conical', 4)
    qubit_tube_carrier = protocol.load_labware('custom_24_tuberack_750ul', 5)

    # Set mounted pipette types #
    p20x1 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[p20x1_tips1])
    p1000x1 = protocol.load_instrument('p1000_single_gen2', 'right', tip_racks=[p1000x1_tips1])

    # Declare liquid handling variables and reagent tube locations#
    qubit_buffer_location = qubit_buffer_carrier.wells()[0]
    qubit_reagent_location = reagent_tube_carrier.wells()[0]
    qubit_standard_1_location = reagent_tube_carrier.wells()[4]
    qubit_standard_2_location = reagent_tube_carrier.wells()[8]
    qubit_working_solution_prep_tube_1_location = reagent_tube_carrier.wells()[12]
    qubit_working_solution_prep_tube_2_location = reagent_tube_carrier.wells()[16]

    qubit_buffer_volume = (199*6) + (199*2) + (199*2) # Samples + Standards + DV
    qubit_reagent_volume = 6 + 2 + 2 # Samples + Standards + DV
    qubit_standards_volume = 10
    sample_volume = 1

    source_sample_well_list = [80, 81, 82, 83, 84, 85] # Well list for samples in columns 3 and 4
    destination_qubit_tube_list = [0,1,2,3,4,5,6,7]

    # Add qubit buffer to the prep tubes, half total volume in each prep tube

    p1000x1.flow_rate.aspirate = 0.5 * 274.7  # Cut flowrate in half for Qubit Buffer asp/disp
    p1000x1.flow_rate.dispense = 0.5 * 274.7

    p1000x1.pick_up_tip()
    for loop in range(0,2):
        if loop == 0:
            destination_tube = qubit_working_solution_prep_tube_1_location.top()
        elif loop == 1:
            destination_tube = qubit_working_solution_prep_tube_2_location.top()
        p1000x1.transfer(volume=qubit_buffer_volume/2,
                        source=qubit_buffer_location,
                        dest=destination_tube,
                        new_tip='never',
                        trash=False,
                        blow_out=True,
                        blowout_location='destination well',
                        touch_tip=False)
    p1000x1.drop_tip()

    # Add qubit reagent to the prep tubes, half total volume in each prep tube
    for loop in range(0,2):
        if loop == 0:
            destination_tube = qubit_working_solution_prep_tube_1_location
        elif loop == 1:
            destination_tube = qubit_working_solution_prep_tube_2_location

        p20x1.pick_up_tip()
        p20x1.transfer(volume=qubit_reagent_volume/2,
                    source=qubit_reagent_location,
                    dest=destination_tube,
                    new_tip='never',
                    trash=True,
                    blow_out=True,
                    blowout_location='destination well',
                    touch_tip=False,
                    mix_after=(1,5))
        p20x1.drop_tip()

    # Mix qubit working solution and pick up the qubit distribution tip

    p1000x1.pick_up_tip()
    for loop in range(0,2):
        if loop == 0:
            destination_tube = qubit_working_solution_prep_tube_1_location.bottom(2)
        elif loop == 1:
            destination_tube = qubit_working_solution_prep_tube_2_location.bottom(2)

        p1000x1.mix(repetitions=3,
                    volume=500,
                    location=destination_tube,
                    rate=1.0)
        p1000x1.blow_out()

    # Distribute qubit working solution among qubit tubes for standards
    p1000x1.transfer(volume=190,
                    source=qubit_working_solution_prep_tube_1_location.bottom(2),
                    dest=qubit_tube_carrier.wells()[0:2],
                    new_tip='never',
                    trash=False,
                    blow_out=True,
                    blowout_location='destination well',
                    touch_tip=False)

    # Distribute qubit working solution among qubit tubes for samples, then dispose of 1000ul tip finally
    for loop in range(0,2):
        if loop == 0:
            source_tube = qubit_working_solution_prep_tube_1_location
            destination_tubes = qubit_tube_carrier.wells()[2:5]
        elif loop == 1:
            source_tube = qubit_working_solution_prep_tube_2_location
            destination_tubes = qubit_tube_carrier.wells()[5:8]

        p1000x1.transfer(volume=199,
                       source=source_tube,
                       dest=destination_tubes,
                       new_tip='never',
                       trash=False,
                       blow_out=True,
                       blowout_location='destination well',
                       touch_tip=False)
    p1000x1.drop_tip()

    # Add standards to qubit standards tubes
    for loop in range(0,2):
        if loop == 0:
            source_tube = qubit_standard_1_location
            destination_tube = qubit_tube_carrier.wells()[0]
        elif loop == 1:
            source_tube = qubit_standard_2_location
            destination_tube = qubit_tube_carrier.wells()[1]

        p20x1.pick_up_tip()
        # Pre-wet the tip using a mix
        p20x1.mix(repetitions=1,
                  volume=10,
                  location=source_tube,
                  rate=1.0)
        # Blowout to reset the tip
        p20x1.blow_out(source_tube.center())
        # Aspirate sample in source tube
        p20x1.aspirate(volume=qubit_standards_volume,
                       location=source_tube,
                       rate=1.0)
        protocol.delay(seconds=2)
        # Aspirate in the dest tube to get better low-volume transfer
        p20x1.aspirate(volume=5,
                       location=destination_tube,
                       rate=1.0)
        # Empty everything out of the tip in dest tube
        p20x1.blow_out(location=destination_tube.bottom(1.0))
        protocol.delay(seconds=2)
        p20x1.drop_tip()

    # Transfer gDNA samples from columns 3 and 4 of temperature plate to qubit tubes
    p20x1.flow_rate.aspirate = 7.6 # Default p20x1 single gen2 flowrate = 7.6ul/sec
    p20x1.flow_rate.dispense = 7.6

    for well in range(0, len(source_sample_well_list)):
        source_tube = temp_plate.wells()[source_sample_well_list[well]]
        destination_tube = qubit_tube_carrier.wells()[destination_qubit_tube_list[well+2]]

        p20x1.pick_up_tip()
        """
        # Pre-wet the tip using a mix
        p20x1.mix(repetitions=1,
                  volume=5,
                  location=source_tube,
                  rate=1.0)
        # Blowout to reset the tip
        p20x1.blow_out(source_tube.center())
        """
        # Aspirate sample in source tube
        p20x1.aspirate(volume=sample_volume,
                       location=source_tube.bottom(1.0),
                       rate=1.0)
        protocol.delay(seconds=2)
        # Aspirate in the dest tube to get better low-volume transfer
        p20x1.aspirate(volume=4,
                       location=destination_tube,
                       rate=1.0)
        # Empty everything out of the tip in dest tube
        p20x1.blow_out(location=destination_tube.bottom(1.0))
        protocol.delay(seconds=2)
        p20x1.drop_tip()