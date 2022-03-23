# -*- coding: utf-8 -*-

"""Run a DHNx example in combination with LPagg.

Create a district heating network from OpenStreetMap data,
aggregate load profiles from VDI 4655 based on basic assumptions for heat
demand and perform a DHS investment optimisation.

Overview
--------

Part I: Get OSM data
Part II: Run the load profile aggregator
Part III: Process the geometry for DHNx
Part IV: Initialise the ThermalNetwork and perform the Optimisation
Part V: Check the results

Contributors:
- Johannes Röder
- Joris Zimmermann


Installation
------------

These are some special dependencies that may have to be install manually

osmnx:
    conda install osmnx -c conda-forge

DHNx:
    - clone repo from https://github.com/oemof/DHNx/tree/dev
    - pip install -e <path to DHNx>
    - or
    - pip install dhnx

CoolProp:
    - pip install CoolProp
    - conda install -c conda-forge coolprop

LPagg:
    - conda install lpagg -c jnettels
    - in case of package conflicts, this might work instead
    - conda install lpagg -c jnettels -c conda-forge
    - or download source from https://github.com/jnettels/lpagg
    - pip install -e <path to LPagg>

"""
import os
import numpy as np
import pandas as pd
import osmnx as ox
import shapely
import matplotlib.pyplot as plt

import dhnx
import dhnx.gistools.geometry_operations as go
from dhnx.gistools.connect_points import process_geometry

import lpagg.agg
import lpagg.misc

import logging

# Define the logging function
logger = logging.getLogger(__name__)


def setup():
    """Set up logger."""
    # Define the logging function
    logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s')
    log_level = 'DEBUG'
    # log_level = 'INFO'
    logger.setLevel(level=log_level.upper())  # Logger for this module
    logging.getLogger('lpagg.agg').setLevel(level='ERROR')
    logging.getLogger('lpagg.simultaneity').setLevel(level='ERROR')


def save_geojson(gdf, file, path_geo='dhnx_out'):
    """Save a gdf to geojson file."""
    if not os.path.exists(path_geo):
        os.makedirs(path_geo)
    try:
        logger.info('Saving... ' + os.path.join(path_geo, file+'.geojson'))
        gdf.to_file(os.path.join(path_geo, file+'.geojson'), driver='GeoJSON')
    except PermissionError:
        input("Please close QGIS to allow saving the file! Then hit Enter.")
        save_geojson(gdf, file, path_geo=path_geo)
    except Exception as e:
        logger.error(file)
        logger.error(gdf)
        raise e


def run_lpagg(gdf):
    """Integrate the load profile aggregator to define thermal power."""
    gdf = go.check_crs(gdf)
    logger.info('Running load profile aggregator...')

    levels_default = 2
    if 'building:levels' not in gdf:
        gdf['building:levels'] = pd.NA
    gdf['building:levels'].fillna(levels_default, inplace=True)
    gdf['building:levels'] = gdf['building:levels'].astype(float)
    gdf['A_ground'] = gdf.area
    ratio_NRF_to_BGF = 0.8
    gdf['A_BGF'] = (gdf['A_ground'] * gdf['building:levels'])
    gdf['A_NRF'] = gdf['A_BGF'] * ratio_NRF_to_BGF

    # VDI 4655 needs the test-reference-year region, which we have to determine
    TRY_polygons = lpagg.misc.get_TRY_polygons_GeoDataFrame()
    TRY_polygons = go.check_crs(TRY_polygons)

    houses = dict()
    E_th_spec_heat = 150  # kWh / (m² * a); m² = NRF
    E_th_spec_DHW = 18  # kWh / (m² * a); m² = NRF

    for i in gdf.index:
        house_name = str(i)
        for _, TRY_region in TRY_polygons.iterrows():
            if gdf.loc[i].geometry.intersects(TRY_region.geometry):
                try_code = TRY_region['TRY_code']

        if gdf.loc[i, 'building'] in ['house', 'residential', 'detached',
                                      'semidetached_house']:
            house_type = 'EFH'
            N_WE = 1
            N_Pers = 2
            gdf.loc[i, 'E_th_heat'] = E_th_spec_heat * gdf.loc[i, 'A_NRF']
            Q_Heiz_a = gdf.loc[i, 'E_th_heat']
            gdf.loc[i, 'E_th_DHW'] = E_th_spec_DHW * gdf.loc[i, 'A_NRF']
            Q_TWW_a = gdf.loc[i, 'E_th_DHW']
        elif gdf.loc[i, 'building'] in ['apartments']:
            house_type = 'MFH'
            N_WE = 10
            N_Pers = 2*N_WE
            gdf.loc[i, 'E_th_heat'] = E_th_spec_heat * gdf.loc[i, 'A_NRF']
            Q_Heiz_a = gdf.loc[i, 'E_th_heat']
            gdf.loc[i, 'E_th_DHW'] = E_th_spec_DHW * gdf.loc[i, 'A_NRF']
            Q_TWW_a = gdf.loc[i, 'E_th_DHW']
        elif gdf.loc[i, 'building'] in ['retail', 'commercial', 'industrial']:
            house_type = 'G1G'
            N_WE = 0
            N_Pers = 0
            gdf.loc[i, 'E_th_heat'] = E_th_spec_heat * gdf.loc[i, 'A_NRF']
            Q_Heiz_a = gdf.loc[i, 'E_th_heat']
            gdf.loc[i, 'E_th_DHW'] = 0
            Q_TWW_a = gdf.loc[i, 'E_th_DHW']

        else:
            logger.error('House type not defined: {}'.format(house_type))

        if houses.get(house_name):
            raise ValueError('House name duplicate: {}'.format(house_name))

        houses[house_name] = dict({
            'Q_Heiz_a': Q_Heiz_a,
            'Q_Kalt_a': None,  # Cooling is not used
            'Q_TWW_a': Q_TWW_a,
            # 'W_a': None,  # uncomment = use estimation from VDI 2067
            'house_type': house_type,
            'N_Pers': N_Pers,
            'N_WE': N_WE,
            'copies': 0,
            'sigma': 4,  # standard deviation for simultainety
            'TRY': try_code,
            })

    # Create a configuration dictionary. In "normal" use of lpagg, this
    # would be provided as a yaml file, but we can just define it here.
    cfg = dict()
    cfg['settings'] = dict()
    cfg['print_folder'] = './lpagg_out'
    cfg['settings']['weather_file'] = './lpagg_in/DWD_TRY_weather_file.dat'
    cfg['settings']['weather_data_type'] = 'DWD'
    cfg['settings']['intervall'] = '1 hours'
    cfg['settings']['start'] = [2021, 1, 1, 00, 00, 00]
    cfg['settings']['end'] = [2022, 1, 1, 00, 00, 00]
    cfg['settings']['apply_DST'] = True
    cfg['settings']['language'] = 'en'
    cfg['settings']['holidays'] = {'country': 'DE', 'province': 'SH'}
    cfg['settings']['print_houses_xlsx'] = False
    cfg['settings']['print_P_max'] = True
    cfg['settings']['print_GLF_stats'] = True
    cfg['settings']['show_plot'] = False

    # Import the cfg from the dictionary
    cfg = lpagg.agg.perform_configuration(cfg=cfg, ignore_errors=True)

    # Information for all houses is derived from the previously defined table
    cfg['houses'] = houses

    # Now the "sorting" of houses has to be triggered manually
    cfg = lpagg.agg.houses_sort(cfg)

    # Now let the aggregator do its job
    weather_data = lpagg.agg.aggregator_run(cfg)
    lpagg.agg.plot_and_print(weather_data, cfg)

    # The thermal power of each house can be read from a certain file
    df_P_max = pd.read_csv(os.path.join(cfg['print_folder'],
                                        'lpagg_load_P_max.dat'),
                           index_col='house')

    gdf = pd.concat([gdf_poly_houses, df_P_max], axis='columns')
    gdf['P_heat_max'] = gdf['P_th']
    gdf['E_th_total'] = gdf[['E_th_heat', 'E_th_DHW']].sum('columns')
    gdf['Vbh_th'] = gdf['E_th_total'] / gdf['P_th']

    logger.debug('Thermal energy demand: %s kWh', gdf['E_th_total'].sum())

    # breakpoint()
    # return None
    return gdf  # = gdf_poly_houses


def apply_DN(gdf_pipes=None, DN_xlsx='./dhnx_out/DN_table_export.xlsx'):
    """Apply norm diameter of pipes from capacity.

    Export the results to the given xslx file.
    """
    import pre_calc_pmax

    df_DN = pd.DataFrame(
        {'Bezeichnung [DN]': [25, 32, 40, 50, 63, 75, 90, 110, 125,
                              160, 200, 250, 300, 350, 400, 500, 600]})

    df_DN['Innendurchmesser [m]'] = df_DN['Bezeichnung [DN]']/1000
    df_DN['Max delta p [Pa/m]'] = 100
    df_DN['Rauhigkeit [mm]'] = 0.01
    df_DN['T_Vorlauf [°C]'] = 80  # °C
    df_DN['T_Rücklauf [°C]'] = 50  # °C
    df_DN['Temperaturniveau [°C]'] = (
        (df_DN['T_Vorlauf [°C]'] + df_DN['T_Rücklauf [°C]']) / 2)

    df_DN = pre_calc_pmax.calc_dataframe_german(df_DN)

    # Export the diameter data to an Excel file
    if not os.path.exists(os.path.abspath(os.path.dirname(DN_xlsx))):
        os.makedirs(os.path.abspath(os.path.dirname(DN_xlsx)))
    df_DN.to_excel(DN_xlsx)

    # Now apply the norm diameter to the pipes dataframe
    gdf_pipes['DN'] = 0

    for idx in gdf_pipes.index:
        capacity = gdf_pipes.loc[idx, 'capacity']

        if capacity > df_DN["P_max [kW]"].max():
            index = df_DN.sort_values(by=["P_max [kW]"],
                                      ascending=False).index[0]
            logger.error('Maximum heat demand exceeds capacity of biggest '
                         'pipe! The biggest pipe type is selected.')
        else:
            index = df_DN[df_DN["P_max [kW]"] >= capacity].sort_values(
                by=["P_max [kW]"]).index[0]

        gdf_pipes.loc[idx, 'DN'] = df_DN.loc[index, "Bezeichnung [DN]"]

    return gdf_pipes


# Part I: Get OSM data #############
setup()

# select the street types you want to consider as DHS routes
# see: https://wiki.openstreetmap.org/wiki/Key:highway
streets = dict({
    'highway': [
        'residential',
        'service',
        'unclassified',
        # 'primary',
        # 'secondary',
        # 'tertiary',
        # 'track',
    ]
})

# select the building types you want to import
# see: https://wiki.openstreetmap.org/wiki/Key:building
buildings = dict({
    'building': [
        'apartments',
        'commercial',
        'detached',
        'house',
        'industrial',
        'residential',
        'retail',
        'semidetached_house',
        # 'yes',
    ]
})

# Define a bounding box polygon from a list of lat/lon coordinates
bbox = [(9.1008896, 54.1954005),
        (9.1048374, 54.1961024),
        (9.1090996, 54.1906397),
        (9.1027474, 54.1895923),
        ]
polygon = shapely.geometry.Polygon(bbox)
graph = ox.graph_from_polygon(polygon, network_type='drive_service')
ox.plot_graph(graph)  # show a plot of the selected street network

gdf_poly_houses = ox.geometries_from_polygon(polygon, tags=buildings)
gdf_lines_streets = ox.geometries_from_polygon(polygon, tags=streets)
gdf_poly_houses.drop(columns=['nodes'], inplace=True)
gdf_lines_streets.drop(columns=['nodes'], inplace=True)

gdf_poly_houses = go.check_crs(gdf_poly_houses)
gdf_lines_streets = go.check_crs(gdf_lines_streets)

# We need one (or more) buildings that we call "generators".
# Choose one among the buildings at random and move it to a new GeoDataFrame
np.random.seed(42)
id_generator = np.random.randint(len(gdf_poly_houses))
gdf_poly_gen = gdf_poly_houses.iloc[[id_generator]].copy()
gdf_poly_houses.drop(index=gdf_poly_gen.index, inplace=True)
gdf_poly_houses.reset_index(drop=True, inplace=True)

# We may not want to supply all given buildings with heat, to simulate
# a low adoption rate among the building owners:
adoption_rate = 0.7  # fraction of total buildings to connect to DHN
ids_DH = np.random.choice(len(gdf_poly_houses),
                          size=int(adoption_rate*len(gdf_poly_houses)),
                          replace=False)
gdf_poly_houses['DH_stage'] = 0
gdf_poly_houses.loc[ids_DH, 'DH_stage'] = 1

# Part II: Run the load profile aggregator
# The houses need a maximum thermal power. For this example, we get it
# from load profiles
gdf_poly_houses = run_lpagg(gdf_poly_houses)

# plot the given geometry
fig, ax = plt.subplots()
gdf_lines_streets.plot(ax=ax, color='blue')
gdf_poly_gen.plot(ax=ax, color='orange')
gdf_poly_houses[gdf_poly_houses['DH_stage'] == 0].plot(ax=ax, color='grey')
gdf_poly_houses[gdf_poly_houses['DH_stage'] == 1].plot(ax=ax, color='green')
plt.title('Geometry before processing')
plt.show(block=False)
save_geojson(gdf_poly_houses, 'consumers_polygon')
save_geojson(gdf_poly_gen, 'producers_polygon')

gdf_poly_houses = (gdf_poly_houses.where(gdf_poly_houses['DH_stage'] == 1)
                   .dropna(axis='index', how='all'))

# Part III: Process the geometry for DHNx #############

# # optionally you can skip Part I and load your own layer with geopandas, e.g.
# gdf_lines_streets = gpd.read_file('your_file.geojson')
# gdf_poly_gen = gpd.read_file('your_file.geojson')
# gdf_poly_houses = gpd.read_file('your_file.geojson')

# process the geometry
tn_input = process_geometry(
    lines=gdf_lines_streets.copy(),
    producers=gdf_poly_gen.copy(),
    consumers=gdf_poly_houses.copy(),
)

# plot output after processing the geometry
_, ax = plt.subplots()
tn_input['consumers'].plot(ax=ax, color='green')
tn_input['producers'].plot(ax=ax, color='red')
tn_input['pipes'].plot(ax=ax, color='blue')
tn_input['forks'].plot(ax=ax, color='grey')
plt.title('Geometry after processing')
plt.show(block=False)

# optionally export the geodataframes and load it into qgis, arcgis whatever
# for checking the results of the geometry processing
for filename, gdf in tn_input.items():
    save_geojson(gdf, filename)


# Part IV: Initialise the ThermalNetwork and perform the Optimisation #######

# initialize a ThermalNetwork
network = dhnx.network.ThermalNetwork()

# add the pipes, forks, consumer, and producers to the ThermalNetwork
for k, v in tn_input.items():
    network.components[k] = v

# check if ThermalNetwork is consistent
network.is_consistent()

# load the specification of the oemof-solph components
invest_opt = dhnx.input_output.load_invest_options('invest_data')


# optionally, define some settings for the solver. Especially increasing the
# solution tolerance with 'ratioGap' or setting a maximum runtime in 'seconds'
# helps if large networks take too long to solve
settings = dict(
    solver='cbc',
    # solver='gurobi',
    solve_kw={
        'tee': True,  # print solver output
    },
    solver_cmdline_options={
        # 'allowableGap': 1e-5,  # (absolute gap) default: 1e-10
        # 'ratioGap': 0.2,  # (0.2 = 20% gap) default: 0
        # 'seconds': 60 * 1,  # (maximum runtime) default: 1e+100
    },
    )

# perform the investment optimisation
network.optimize_investment(invest_options=invest_opt, **settings)


# Part V: Check the results #############

# get results
results_edges = network.results.optimization['components']['pipes']

# if logger.isEnabledFor(logging.DEBUG):
#     print(results_edges[['from_node', 'to_node', 'hp_type', 'capacity',
#                          'direction', 'costs', 'losses']])

logger.info('Total costs: {}'.format(results_edges[['costs']].sum()))
logger.info('Objective value: {}'.format(
    network.results.optimization['oemof_meta']['objective']))
# (The costs of the objective value and the investment costs of the DHS
# pipelines are the same, since no additional costs (e.g. for energy sources)
# are considered in this example.)

# add the investment results to the geoDataFrame
gdf_pipes = network.components['pipes']
gdf_pipes = gdf_pipes.join(results_edges, rsuffix='results_')

gdf_pipes = apply_DN(gdf_pipes)  # Apply DN from capacity

# plot output after processing the geometry
_, ax = plt.subplots()
# network.components['consumers'].plot(ax=ax, color='green')
# network.components['producers'].plot(ax=ax, color='red')
# network.components['forks'].plot(ax=ax, color='grey')
gdf_pipes[gdf_pipes['capacity'] > 0].plot(ax=ax, color='blue')
gdf_poly_gen.plot(ax=ax, color='orange')
gdf_poly_houses.plot(ax=ax, color='green')
plt.title('Invested pipelines')
plt.show()

# EXPORT RESULTS
save_geojson(gdf_pipes, 'pipes')
