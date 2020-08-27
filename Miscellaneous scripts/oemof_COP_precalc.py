"""
Example on how to use the 'calc_cops' function to get the
COPs of an exemplary air-source heat pump (ASHP) and use the
pre-calculated COPs in a solph.Transformer.
Furthermore, the maximal possible heat output of the heat pump is
pre-calculated and varies with the temperature levels of the heat reservoirs.

We use the ambient air as low temperature heat reservoir.
"""

import os
import oemof.thermal.compression_heatpumps_and_chillers as cmpr_hp_chiller
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read data file
#filename = os.path.join(os.path.dirname(__file__), 'data/ASHP_example.csv')
filename = '/home/dbeier/SeaDrive/Meine Bibliotheken/QUARREE 100/02_Modellierung/02_Modellierung_oemof/oemof_data/q100_oemof_app/Input_Daten.xls'
data_air = pd.read_excel(filename)



def flow_temperature_dependent_on_ambient(t_max, t_min, t_amb):
    delta_t_flow = t_max - t_min
    delta_t_amb = 30
    T_flow = [t_max - (delta_t_flow/delta_t_amb) * i for i in range(31)]
    T_round = np.round(t_amb)

    t_ind = np.zeros(shape=(8760))
    tvl = np.zeros(shape=(8760))  # Vorlauftemperatur
    for i in range(8760):
        if T_round[i] <= -16 and T_round[i] > -15:
            t_ind[i] = 1
        elif T_round[i] >= -15 and T_round[i] < 0:
            t_ind[i] = abs(15 + T_round[i])  # nimm erste 15 Stellen bei -10 bis 0°C
        elif T_round[i] >= 0:
            t_ind[i] = min(26, 16 + T_round[i])
        tvl[i] = int(max(t_min, T_flow[int(t_ind[i] - 1)]))

    tvl = list(tvl)

    return tvl


def calculate_COP(temp_high, temp_low, quality_grade):
    cops = cmpr_hp_chiller.calc_cops(
        temp_high=list([temp_high]),
        temp_low=temp_low,
        quality_grade=quality_grade,
        mode='heat_pump',
        temp_threshold_icing=2,
        factor_icing=0.8)

    return cops


def calculate_dynamic_COP(t_vl, t_low, quality_grade):
    cops = []
    for i in range(1, len(tvl)):
        tmp_high = list([t_vl[i]])
        tmp_low = list([t_low[i]])

        cop = cmpr_hp_chiller.calc_cops(
            temp_high=tmp_high,
            temp_low=tmp_low,
            quality_grade=quality_grade,
            mode='heat_pump',
            temp_threshold_icing=2,
            factor_icing=0.8)

        cops.append(cop[0])

    cops = pd.Series(cops)

    return cops


def calculate_mixed_COPS_per_region(t_amb, t_ground, quality_grade, share_ashp=0.7, share_gshp=0.3):

    t_flow = dict(high = 75, medium=55, low = 40)

    # Calculate flow temperature for different temperature levels
    tvl75 = flow_temperature_dependent_on_ambient(t_flow['high'], 50, t_amb)
    tvl50 = flow_temperature_dependent_on_ambient(t_flow['medium'], 30 , t_amb)
    tvl35 = flow_temperature_dependent_on_ambient(t_flow['low'], 30 , t_amb)

    cop75_ASHP = calculate_dynamic_COP(tvl75, t_amb, quality_grade)
    cop50_ASHP = calculate_dynamic_COP(tvl50, t_amb, quality_grade)
    cop35_ASHP = calculate_dynamic_COP(tvl35, t_amb, quality_grade)
    copwater_ASHP = calculate_dynamic_COP(np.ones(shape=8760)*50, t_amb, quality_grade)

    cop75_GSHP = calculate_dynamic_COP(tvl75, t_ground, quality_grade)
    cop50_GSHP = calculate_dynamic_COP(tvl50, t_ground, quality_grade)
    cop35_GSHP = calculate_dynamic_COP(tvl35, t_ground, quality_grade)
    copwater_GSHP = calculate_dynamic_COP(np.ones(shape=8760)*50, t_ground, quality_grade)

    cops_aggregated = pd.DataFrame(columns=['COP35_air', 'COP50_air', 'COP75_air', 'COP35_ground', 'COP50_ground',
                                            'COP75_ground', 'COPwater_air', 'COPwater_ground','COP_mean' ])

    cops_aggregated['COP35_air'] = cop35_ASHP
    cops_aggregated['COP50_air'] = cop50_ASHP
    cops_aggregated['COP75_air'] = cop75_ASHP
    cops_aggregated['COP35_ground'] = cop35_GSHP
    cops_aggregated['COP50_ground'] = cop50_GSHP
    cops_aggregated['COP75_ground'] = cop75_GSHP
    cops_aggregated['COPwater_air'] = copwater_ASHP
    cops_aggregated['COPwater_ground'] = copwater_GSHP


    cop_air_mean = (cop35_ASHP + cop50_ASHP + cop75_ASHP) / 3
    cop_ground_mean = (cop35_GSHP + cop50_GSHP + cop75_GSHP) / 3
    cop_mean = share_ashp * cop_air_mean + share_gshp * cop_ground_mean
    cops_aggregated['COP_mean'] = cop_mean

    # Limit COP to 7
    limit = cops_aggregated >= 7
    cops_aggregated[limit] = 7

    return cops_aggregated

# Set params
t_high = 60
t_amb = data_air['T_amb_TRY2015']
t_ground = pd.Series(np.ones(8760)*10)
quality_grade = 0.4

# Calculate COP for constant flow temperature of t_high
cop_static = calculate_COP(t_high, t_amb, quality_grade)

# Calculate dynamic flow temperature depending on ambient temperature
tvl = flow_temperature_dependent_on_ambient(75, 50, t_amb)

# Calculate COP based on dyamic flow temperature
cop_dynamic = calculate_dynamic_COP(tvl, t_amb, quality_grade=0.4)

# Caluculate some cops for different potential heating systems
mixed_cops  = calculate_mixed_COPS_per_region(t_amb, t_ground, quality_grade=0.4, share_ashp=0.6, share_gshp=0.4)




