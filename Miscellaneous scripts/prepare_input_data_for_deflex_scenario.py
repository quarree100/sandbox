from disaggregator import data, config
from deflex import geometries as geo_deflex
from reegis import geometries as geo_reegis
import integrate_demandregio, Land_Availability_GLAES
import pandas as pd
import os


#data.cfg['base_year'] = 2015
nuts3_regions = list(config.dict_region_code(keys='natcode_nuts3', values='name').keys())
nuts3_regions[0:2]=[]

# Fetch electricity consumption for all NUTS3-Regions
elc_consumption = integrate_demandregio.get_demandregio_electricity_consumption_by_nuts3(2015, nuts3_regions)
# Fetch heat consumption for all NUTS3-Regions
heat_consumption = integrate_demandregio.get_combined_heatload_for_region(2015, nuts3_regions)

# Load suitable PV/Wind-areas from csv
#filename = os.getcwd() + '/GLAES_Eignungsflaechen_Wind_PV.csv'
#suitable_area = pd.read_csv(filename)
#suitable_area.set_index('nuts3', drop=True, inplace=True)

# Alternatively if no precalculation is available:
path = os.getcwd() + '/nuts3_geojson/'
suitable_area = Land_Availability_GLAES.get_pv_wind_areas_by_nuts3(path, create_geojson=True)

# Define installable capacity per square meter in MW
p_per_qm_wind = 8 / 1e6 # 8 W/m² Fläche
p_per_qm_pv = 200 / 1e6 # 200 W/m² Fläche -> eta=20%

# Calculate maximum installable capacity for onshore wind and rooftop-PV
P_max_wind = suitable_area['wind_area'] * p_per_qm_wind
P_max_pv = suitable_area['pv_area'] * p_per_qm_pv

# Get indices for zones of interest
de22_list = geo_deflex.deflex_regions(rmap='de22', rtype='polygons').index
de17_list = geo_reegis.get_federal_states_polygon().index

# Aggregate values for de17 and de22 regions to prepare for
# Create empty Dataframe
dflx_input = pd.DataFrame(index=de22_list, columns = ['power','lt-heat','ht-heat','P_wind', 'P_pv'])
dflx_input_fedstates = pd.DataFrame(index=de17_list, columns = ['power','lt-heat','ht-heat','P_wind', 'P_pv'])

for zone in de22_list:
    region_pick = integrate_demandregio.get_nutslist_per_zone(region_sel=zone, zones='de22')
    dflx_input.loc[zone]['power'] = elc_consumption.sum(axis=1)[region_pick].sum()
    dflx_input.loc[zone]['lt-heat'] = (heat_consumption['Households']+heat_consumption['CTS']+heat_consumption['Industry'])[region_pick].sum()
    dflx_input.loc[zone]['ht-heat'] = heat_consumption['ProcessHeat'][region_pick].sum()
    dflx_input.loc[zone]['P_wind'] = P_max_wind[region_pick].sum()
    dflx_input.loc[zone]['P_pv'] = P_max_pv[region_pick].sum()


for zone in de17_list:
    region_pick = integrate_demandregio.get_nutslist_per_zone(region_sel=zone, zones='fed_states')
    dflx_input_fedstates.loc[zone]['power'] = elc_consumption.sum(axis=1)[region_pick].sum()
    dflx_input_fedstates.loc[zone]['lt-heat'] = (heat_consumption['Households']+heat_consumption['CTS']+heat_consumption['Industry'])[region_pick].sum()
    dflx_input_fedstates.loc[zone]['ht-heat'] = heat_consumption['ProcessHeat'][region_pick].sum()
    dflx_input_fedstates.loc[zone]['P_wind'] = P_max_wind[region_pick].sum()
    dflx_input_fedstates.loc[zone]['P_pv'] = P_max_pv[region_pick].sum()

