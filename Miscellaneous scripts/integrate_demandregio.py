from disaggregator import data, config, spatial, temporal
from reegis import geometries as geo
from deflex import geometries as geo_deflex
import pandas as pd
import logging


def get_nutslist_per_zone(region_sel, zones='de22'):
    """
    Parameters
    ----------
    region_sel : String
        Abbreviations of Federal States of Germany
        Valid options for fed_states are: HH, NI, MV, SH, ST, RP, HB, NW, BW, BY, SL, TH, BB, BE, HE, SN
        Valid options for de22 are: DE01-DE22
    zones : String
        Choose regional divison of Germany: 'de22' for dena power network zones and 'fed_states' for federal states

    Returns: list
        List of nuts3 regions inside the chosen federal state
    -------
    """
    # Fetch NUTS3-geometries from disaggregator database
    nuts3_disaggregator = data.database_shapes()
    # Transform CRS System to match reegis geometries
    nuts_geo = nuts3_disaggregator.to_crs(crs=4326)

    if zones == 'fed_states':
        # Fetch geometries of German Federal States from reegis
        map = geo.get_federal_states_polygon()
    elif zones == 'de22':
        map = geo_deflex.deflex_regions(rmap='de22', rtype='polygons')

    # Match NUTS3-regions with federal states
    nuts_geo = geo.spatial_join_with_buffer(nuts_geo.centroid, map, 'fs')
    # Create dictionary with lists of all NUTS3-regions for each state
    nuts = {}
    nuts = nuts.fromkeys(map.index)

    for zone in map.index:
        nuts[zone] = list(nuts_geo.loc[nuts_geo['fs'] == zone].index)

    # Get list of NUTS3-regions for state of interest
    outputlist = nuts[region_sel]

    return outputlist


def get_demandregio_hhload_by_NUTS3_profile(year, region_pick, method='SLP'):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format
    method : string
        Chosen method to generate temporal profile, either 'SLP' or 'ZVE'

    Returns: pd.DataFrame
        Dataframe containing yearly household load for selection
    -------
    """

    if method is 'SLP':
        elc_consumption_hh_spattemp = data.elc_consumption_HH_spatiotemporal(year=year)
        df = elc_consumption_hh_spattemp[region_pick]

    elif method is 'ZVE':
        logging.warning('Can be lengthy for larger lists')
        list_result = []
        sum_load = data.elc_consumption_HH_spatial(year=year)
        for reg in region_pick:
            elc_consumption_hh_spattemp_zve = temporal.make_zve_load_profiles(year=year, reg=reg) * sum_load[reg]
            list_result.append(elc_consumption_hh_spattemp_zve)
        df = pd.concat(list_result, axis=1, sort=False)

    else:
        raise ValueError('Chosen method is not valid')

    return df


def get_demandregio_electricity_consumption_by_nuts3(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format
    weight_by_income : bool
        Choose whether electricity demand shall be weighted by household income

    Returns: pd.DataFrame
        Dataframe containing aggregated yearly load (households, CTS and industry) for selection
    -------
    """
    data.cfg["base_year"] = year # Works unfortunately just for 2015 due to limited availability of householdpower
    ec_hh = spatial.disagg_households_power(by='households', weight_by_income=True).sum(axis=1) * 1000
    ec_CTS_detail = spatial.disagg_CTS_industry(sector='CTS', source='power', use_nuts3code=True)
    ec_CTS = ec_CTS_detail.sum()
    ec_industry_detail = spatial.disagg_CTS_industry(sector='industry', source='power', use_nuts3code=True)
    ec_industry = ec_industry_detail.sum()

    ec_sum = pd.concat([ec_hh, ec_CTS, ec_industry], axis=1)
    ec_sum.columns = ['households', 'CTS', 'industry']
    ec_sel = ec_sum.loc[region_pick]

    return ec_sel


def get_household_heatload_by_NUTS3(year, region_pick, how='top-down', weight_by_income='True'):

    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format
    how : string
        Method of disaggreagtion - can be "top-down" or "bottom-up" - top-down recommended
    weight_by_income : bool
        Choose whether heat demand shall be weighted by household income

    Returns: pd.DataFrame
        Dataframe containing yearly household load for selection
    -------
    """
    # Abweichungen in den Jahresmengen bei bottom-up
    data.cfg["base_year"] = year
    qdem_temp = spatial.disagg_households_heatload_DB(how='top-down', weight_by_income=weight_by_income)
    qdem_temp = qdem_temp.sum(axis=1)
    df = qdem_temp[region_pick]

    return df


def get_CTS_heatload(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly heat CTS heat consumption by NUTS-3 region
    -------
    """

    # Define year of interest
    data.cfg['base_year'] = year
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum()/0.47
    # Multiply with CTS heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_CTS = 0.37 * heatload_hh  #Verhältnis aus dem Jahr 2017
    # Calculate CTS gas consumption by economic branch and NUTS3-region
    gc_CTS = spatial.disagg_CTS_industry(sector='CTS', source='gas', use_nuts3code=True)
    # Sum up the gas consumption per NUTS3-region
    sum_gas_CTS = gc_CTS.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_CTS / sum_gas_CTS
    # Calculate CTS heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_CTS_new = gc_CTS.multiply(inc_fac)
    # Select heatload of NUTS3-regions of interest
    gc_CTS_combined = gc_CTS_new.sum()
    df = gc_CTS_combined[region_pick]

    return df


def get_industry_heating_hotwater(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """


    # Define year of interest
    data.cfg['base_year'] = year
    # Get gas consumption of defined year and divide by gas-share in end energy use for heating
    heatload_hh = data.gas_consumption_HH().sum()/0.47
    # Multiply with industries heatload share, Assumption: Share is constant because heatload mainly depends on wheather
    heatload_industry = 0.089 * heatload_hh  #Verhältnis aus dem Jahr 2017
    # Calculate industry gas consumption by economic branch and NUTS3-region
    gc_industry = spatial.disagg_CTS_industry(sector='industry', source='gas', use_nuts3code=True)
    # Sum up the gas consumption per NUTS3-region
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate scaling factor
    inc_fac = heatload_industry / sum_gas_industry
    # Calculate indsutries heatload: Assumption: Heatload correlates strongly with gas consumption
    gc_industry_new = gc_industry.multiply(inc_fac)
    gc_industry_combined = gc_industry_new.sum()
    # Select heatload of NUTS3-regions of interest
    df = gc_industry_combined[region_pick]

    return df


def get_industry_CTS_process_heat(year, region_pick):
    """
    Parameters
    ----------
    year : int
        Year of interest
    region_pick : list
        Selected regions in NUTS-3 format

    Returns: pd.DataFrame
        Dataframe containing yearly industry heat consumption by NUTS-3 region
    -------
    """

    # Select year
    data.cfg['base_year'] = year
    # Get industrial gas consumption by NUTS3
    gc_industry = spatial.disagg_CTS_industry(sector='industry', source='gas', use_nuts3code=True)
    sum_gas_industry = gc_industry.sum().sum()
    # Calculate factor of process heat consumption to gas consumption.
    # Assumption: Process heat demand correlates with gas demand
    inc_fac = (515 + 42) * 1e6 / sum_gas_industry
    # Calculate process heat with factor
    ph_industry = gc_industry.multiply(inc_fac)
    ph_industry_combined = ph_industry.sum()
    # Select process heat consumptions for NUTS3-Regions of interest
    df = ph_industry_combined[region_pick]

    return df


def get_combined_heatload_for_region(year, region_pick):
    # only applicable for 2015, 2016
    tmp0 = get_household_heatload_by_NUTS3(year, region_pick) # Nur bis 2016
    tmp1 = get_CTS_heatload(year, region_pick) # 2015 - 2035 (projection)
    tmp2 = get_industry_heating_hotwater(year, region_pick)
    tmp3 = get_industry_CTS_process_heat(year, region_pick)

    df_heating = pd.concat([tmp0, tmp1, tmp2, tmp3], axis=1)
    df_heating.columns = ['Households', 'CTS', 'Industry', 'ProcessHeat']

    return df_heating


def get_hp_shares():
    # Diese Funktion macht vermutlich überhaupt keinen Sinn
    qdem, age_structure = spatial.disagg_households_heatload_DB(how='bottom-up', weight_by_income=True)
    share_hp = pd.DataFrame(index=age_structure.index, columns=['share_hp35', 'share_hp55','share_hp75'])

    for idx in share_hp.index:
        share_hp.loc[idx]['share_hp35'] = age_structure.loc[idx]['F_>2000'] / age_structure.loc[idx].sum()
        share_hp.loc[idx]['share_hp55'] = (age_structure.loc[idx]['E_1996-2000'] +
                                           age_structure.loc[idx]['D_1986-1995']) / age_structure.loc[idx].sum()
        share_hp.loc[idx]['share_hp75'] = age_structure.loc[idx]['A_<1948'] / age_structure.loc[idx].sum()

    return share_hp




