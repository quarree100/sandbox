import os
import pandas as pd
# from deflex import data
from scenario_builder import data
from deflex import geometries
from scenario_builder import powerplants as dp

TRANS = {
    "Abfall": "waste",
    "Kernenergie": "nuclear",
    "Braunkohle": "lignite",
    "Steinkohle": "hard coal",
    "Erdgas": "natural gas",
    "GuD": "natural gas",
    "Gasturbine": "natural gas",
    "Öl": "oil",
    "Sonstige": "other",
    "Emissionszertifikatspreis": "co2_price",
}


def get_merit_order_ewi():
    fn = os.path.join(
        os.path.dirname(__file__), "data", "merit_order_ewi.csv"
    )
    pp = pd.read_csv(fn, header=[0], index_col=[0])
    pp = pp.replace(TRANS)
    return pp


def get_merit_order_ewi_raw():
    fn = os.path.join(
        os.path.dirname(__file__), "data", "merit_order_ewi_raw.csv"
    )
    pp = pd.read_csv(fn, header=[0], index_col=[0])
    pp = pp.replace(TRANS)
    print(pp.columns)
    pp["capacity"] = pp["capacity_net"]
    pp["costs_total"] = pp.costs_limit.multiply(pp.efficiency)

    print(pp["costs_total"])
    pp.sort_values(["costs_total", "capacity"], inplace=True)
    pp["capacity_cum"] = pp.capacity.cumsum().div(1000)

    return pp


def get_merit_order_reegis(year=2014, round_efficiency=None):
    fn = os.path.join(
        os.path.dirname(__file__), "data", "merit_order_reegis_base.csv"
    )
    if not os.path.isfile(fn):
        get_reegis_pp_for_merit_order("de02", year)
    pp = pd.read_csv(fn, header=[0], index_col=[0])
    if round_efficiency is not None:
        pp["efficiency"] = pp["efficiency"].round(round_efficiency)
    ewi = data.get_ewi_data()
    ewi_table = pd.DataFrame(index=ewi.fuel_costs.index)
    for table in [
        "fuel_costs",
        "transport_costs",
        "variable_costs",
        "downtime_factor",
        "emission",
    ]:
        ewi_table[table] = getattr(ewi, table).value
    pp = pp.merge(ewi_table, left_on="fuel", right_index=True)
    pp = pp.loc[pp.fillna(0).capacity != 0]
    # pp = pp.loc[pp.capacity >= 100]
    pp["capacity"] = pp.capacity.multiply(1 - pp.downtime_factor)
    pp["costs_total"] = (
        pp.fuel_costs
        + pp.transport_costs
        + pp.emission * float(ewi.co2_price["value"])
    ).div(pp.efficiency) + pp.variable_costs
    pp.sort_values(["costs_total", "capacity"], inplace=True)
    pp["capacity_cum"] = pp.capacity.cumsum().div(1000)
    print(pp)
    return pp


def get_reegis_pp_for_merit_order(name, year, aggregated=None, zero=False):
    """pass"""
    # get_merit_order_ewi()
    if aggregated is None:
        aggregated = ["Solar", "Wind", "Bioenergy", "Hydro", "Geothermal"]
    regions = geometries.deflex_regions("de02")
    pp = dp.get_deflex_pp_by_year(regions, year, name, True)
    pp.drop(
        [
            "chp",
            "com_month",
            "com_year",
            "comment",
            "decom_month",
            "decom_year",
            "efficiency",
            "energy_source_level_1",
            "energy_source_level_3",
            "geometry",
            "technology",
            "thermal_capacity",
            "federal_states",
        ],
        axis=1,
        inplace=True,
    )
    pp["count"] = 1
    pp_agg = (
        pp.groupby("energy_source_level_2").sum().loc[aggregated].reset_index()
    )
    pp_agg.index = [x + pp.index[-1] + 1 for x in range(len(pp_agg))]
    pp = pp.loc[~pp.energy_source_level_2.isin(aggregated)]
    if zero is True:
        pp = pd.concat([pp, pp_agg], sort=False)
    pp["efficiency"] = pp.capacity.div(pp.capacity_in)
    pp.drop(["capacity_in"], axis=1, inplace=True)
    pp.rename({"energy_source_level_2": "fuel"}, inplace=True, axis=1)
    pp = pp.loc[~pp.fuel.isin(["Storage"])]
    pp.loc[
        pp.fuel == "unknown from conventional", "fuel"
    ] = "Other fossil fuels"
    pp.loc[pp.fuel == "Other fuels", "fuel"] = "Other fossil fuels"
    pp["fuel"] = pp.fuel.str.lower()
    fn = os.path.join(
        os.path.dirname(__file__), "data", "merit_order_reegis_base.csv"
    )
    pp.to_csv(fn)
