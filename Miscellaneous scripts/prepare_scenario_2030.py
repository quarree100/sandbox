### Within this script releant energy system data for a mid-term scenario is fetched and processed

from disaggregator import data
from scenario_builder import cop_precalc, snippets, heatload_scenario_calculator
from deflex import geometries as geo_deflex
from reegis import land_availability_glaes, demand_disaggregator, entsoe, demand_heat
from scenario_builder import emobpy_processing
import pandas as pd

# Set parameters and get data needed for all scenarios
nuts3_index = data.database_shapes().index
de21 = geo_deflex.deflex_regions(rmap='de21')
year = 2015
# Excel findet sich auch hier: SeaDrive/Für meine Gruppen/QUARREE 100/02_Modellierung/09_Szenarien Q100
path_to_data = '/home/dbeier/reegis/data/scenario_data/commodity_sources_costs.xls'
# Get ENTSO-E load profile from reegis
profile = entsoe.get_entsoe_load(2014).reset_index(drop=True)["DE_load_"]
norm_profile = profile.div(profile.sum())

heat_profiles_reegis = demand_heat.get_heat_profiles_by_region(de21, 2014, name='test')

profile_lt = snippets.return_normalized_domestic_profiles(de21, heat_profiles_reegis)
profile_ht = snippets.return_normalized_industrial_profiles(de21, heat_profiles_reegis)

# Fetch costs and emission applicable for scenario (sheet1)
costs = snippets.get_cost_emission_scenario_data(path_to_data)

# Fetch overall res potential
res_potential = land_availability_glaes.aggregate_capacity_by_region(de21)





###
# 1. Status Quo scenario
keys = ['Storage', 'commodity_source', 'decentralised_heat', 'lt_heat_series', 'ht_heat_series', 'elc_series',
        'storages', 'transformer', 'transmission', 'volatile_series', 'volatile_source']
scen_dict_sq = dict.fromkeys(keys)

# Fetch electricity consumption for all NUTS3-Regions
elc_consumption_sq =  demand_disaggregator.aggregate_power_by_region(de21, year, elc_data=None)
elc_profile_sq = pd.DataFrame(columns=elc_consumption_sq.index[0:18])

for reg in elc_consumption_sq.index[0:18]:
    elc_profile_sq[reg] = elc_consumption_sq.sum(axis=1)[reg] * norm_profile

# Fetch heat consumption for all NUTS3-Regions
heat_consumption_sq = demand_disaggregator.aggregate_heat_by_region(de21, year=year, heat_data=None)

lt_heat_profile_sq = pd.DataFrame(columns=heat_consumption_sq.index[0:18])
ht_heat_profile_sq = pd.DataFrame(columns=heat_consumption_sq.index[0:18])

for reg in heat_consumption_sq.index[0:18]:
    lt_heat_profile_sq[reg] = heat_consumption_sq['lt-heat'][reg] * profile_lt[reg]
    ht_heat_profile_sq[reg] = heat_consumption_sq['ht-heat'][reg] * profile_ht[reg]


# Write data to scenario dict, empty sheets should be equal to basic_scenario
scen_dict_sq['commodity_source'] = costs['StatusQuo']
scen_dict_sq['elc_series'] = elc_profile_sq
scen_dict_sq['lt_heat_series'] = lt_heat_profile_sq
scen_dict_sq['ht_heat_series'] = ht_heat_profile_sq







# 2. NEP 2035
path_to_NEP_capacities= '/home/dbeier/reegis/data/scenario_data/NEP2030_capacities.xls'
# Define overall electrical energy for heat pumps
E_wp = 28.7 * 1e6 # 28.7 TWh elektrische Energie in MWh

# Load NEP2030 pp capacities
# ToDo: Älteste Kraftwerke der Tpyen auf Bundesländerebene reduzieren und dann in de21 transformieren
NEP_pp_capacities = snippets.load_NEP_pp_capacities(path_to_NEP_capacities) # Geo-Operation für spatial join?

# Match NEP capacity with land availability
# Excel auch hier: SeaDrive/Für meine Gruppen/QUARREE 100/02_Modellierung/09_Szenarien Q100/NEP2030_capacities.xls
NEP_capacities = snippets.transform_NEP_capacities_to_de21(path_to_NEP_capacities)

# Load and prepare demand series
# Electrical base load should be similar to today
elc_profile_NEP_base =  elc_profile_sq # MWh

# According to NEP scenario 25 TWh of electrical energy is used for charging BEVs. Profile generated with emobpy
E_emob = 25 * 1e6 # 25 TWh electrical energy in MWh (scaling factor)
# Generate charging profile based on precalculated profiles for immediate, balanced and overnight charging strategies
ch_power = emobpy_processing.return_averaged_charging_series(weight_im=0.4, weight_bal=0.4, weight_night=0.2)
elc_profile_NEP_emob = E_emob * ch_power
# Return population per region to derive distribution keys for charging
pop_per_region = snippets.aggregate_by_region(de21, data.population())
# Intialize DataFrame
ch_power_per_region = pd.DataFrame(index = ch_power.index, columns=pop_per_region.index[0:18])
# Distribute charging power to regions by population (@Uwe can be done better with reegis mobiltiy feature)
for reg in pop_per_region.index[0:18]:
    share = pop_per_region[reg] / pop_per_region.sum()
    ch_power_per_region[reg] = share * elc_profile_NEP_emob


# Calculate and aggregate yearly scenario heatload data
# Attention: If name is not changed function will load existing results and parameter change will have no effect
# With eff_gain factors sectoral heatload can be reduced. (0 no reduction ... 1 reduction to zero)
# Factor m_type refers to modernisation status of redisdential buildings. (1 Status Quo, 2 Conventional Modernisation,
# 3 Future Modernisation).
heat_data_NEP = heatload_scenario_calculator.get_combined_heatload_for_region_scenario\
    ('NEP', m_type=2 , eff_gain_CTS=0.3, eff_gain_ph=0, eff_gain_ihw=0.3)

# Aggregate heatload by de21 regions
heat_consumption_NEP = demand_disaggregator.aggregate_heat_by_region(de21, 2015, heat_data=heat_data_NEP)
# Initialize DataFrames
lt_heat_profile_NEP = pd.DataFrame(columns=heat_consumption_NEP.index[0:18])
ht_heat_profile_NEP = pd.DataFrame(columns=heat_consumption_NEP.index[0:18])
# Multiply heatload with corresponding ht/lt-profiles from reegis
for reg in heat_consumption_NEP.index[0:18]:
    lt_heat_profile_NEP[reg] = heat_consumption_NEP['lt-heat'][reg] * profile_lt[reg]
    ht_heat_profile_NEP[reg] = heat_consumption_NEP['ht-heat'][reg] * profile_ht[reg]

# Calculate mixed COPs for nuts3-regions
COP, COP_water = cop_precalc.calculate_mixed_cops_by_nuts3(2014, 'NEP2030', share_ashp=0.7, share_gshp=0.3,
                                                           quality_grade=0.4)
# Aggregate COP by de21 regions
region_COP = cop_precalc.aggregate_COP_by_region(de21, COP)

# Assign heat pump utilization to regions
heat_distribution = pd.DataFrame(index=heat_consumption_NEP.index[0:18], columns=['rel', 'abs'])
for reg in heat_consumption_NEP.index[0:18]:
    heat_distribution.loc[reg]['rel'] =  heat_consumption_NEP.loc[reg]['lt-heat'] / heat_consumption_NEP["lt-heat"].sum()
    heat_distribution.loc[reg]['abs'] = heat_distribution.loc[reg]['rel'] * (E_wp)


# Calculate heat and electric profiles due to use of Heatpumps
# Initialize DataFrames
lt_heat_profile_NEP_HP = pd.DataFrame(index=profile_lt.index, columns=heat_consumption_NEP.index[0:18])
elc_consumption_NEP_HP = pd.DataFrame(index=profile_lt.index, columns=heat_consumption_NEP.index[0:18])

# Loop through regions and increase heatpump profile until assigned electrical energy is used, return profiles
# of covered heat and electrical power
for reg in heat_consumption_NEP.index[0:18]:
    a, b = cop_precalc.get_hp_timeseries(profile_lt[reg], region_COP[reg], heat_distribution.loc[reg]['abs'])
    elc_consumption_NEP_HP[reg] = a
    lt_heat_profile_NEP_HP[reg] = b


# Sum up electrical load profile per region
elc_profile_NEP_base.index = elc_consumption_NEP_HP.index # Harmonize indices
ch_power_per_region.index = elc_consumption_NEP_HP.index  # Harmonize indices

# Sum of base, bev and hp consumption of electrical energy
elc_consumption_NEP = ch_power_per_region + elc_consumption_NEP_HP + elc_profile_NEP_base


# Write results to dictionary
scen_dict_NEP = dict.fromkeys(keys)
scen_dict_NEP['commodity_source'] = costs['NEP2030']
scen_dict_NEP['elc_series'] = elc_consumption_NEP
scen_dict_NEP['lt_heat_series'] = lt_heat_profile_NEP - lt_heat_profile_NEP_HP
scen_dict_NEP['ht_heat_series'] = ht_heat_profile_NEP
scen_dict_NEP['volatile_source'] = NEP_capacities


del reg, share, year, res_potential, region_COP, COP, COP_water, E_emob, E_wp, NEP_capacities, a, b,\
    ch_power_per_region, ch_power, costs, de21, elc_consumption_NEP, elc_consumption_NEP_HP, elc_consumption_sq,\
    elc_profile_NEP_base, elc_profile_NEP_emob, elc_profile_sq, heat_consumption_NEP, heat_consumption_sq, \
    heat_data_NEP, heat_distribution, heat_profiles_reegis, ht_heat_profile_NEP, ht_heat_profile_sq, keys, \
    lt_heat_profile_NEP, lt_heat_profile_NEP_HP, lt_heat_profile_sq, norm_profile, nuts3_index, \
    pop_per_region, profile, profile_ht, profile_lt