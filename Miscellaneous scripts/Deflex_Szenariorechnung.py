"""
Zum Ausführen des Skriptes müssen folgende Packages installiert sein:

pip install oemof deflex reegis
Für den Energiebilanz area plot (plot_multiregion_io) sind noch folgende Installationen erforderlich:
pip install git+https://github.com/oemof/oemof_visio.git
pip install git+https://github.com/reegis/my_reegis.git
"""

import os
import pandas as pd
import numpy as np
import logging
from deflex import main
from oemof.tools import logger
from my_reegis import results, upstream_analysis, reegis_plot
from matplotlib import pyplot as plt

logger.define_logging(logfile='oemof.log',
                      screen_level=logging.INFO,
                      file_level=logging.DEBUG)

scen_path = os.path.join(os.path.expanduser("~"),
    'ownCloud/FhG-owncloud-Quarree-AB3/Daten/deflex',
    'deflex_2014_de02_NEP.xls')

# Rechne NEP 1-Knoten-Szenario
main.model_scenario(scen_path, name="NEP2030", rmap="de02", year=2014)

res_path= os.path.join(os.path.expanduser("~"),
    'reegis/scenarios/deflex/2014/results_cbc/NEP2030.esys')
de02_NEP = results.load_es(res_path)
results_obj = de02_NEP.results['main']

# Auswertung
cost_em = upstream_analysis.get_emissions_and_costs(de02_NEP,with_chp=True)
vlh = results.fullloadhours(de02_NEP)
mrbb = results.get_multiregion_bus_balance(de02_NEP)

# Extrahiere relevante Größen
demand = mrbb.DE01['out']['demand']['electricity']['all']
transformer = mrbb.DE01['in']['trsf']
ee_single =  mrbb.DE01['in']['source']['ee']
ee_single["bioenergy"] = transformer["pp"]["bioenergy"] + transformer["chp"]["bioenergy"]
ee_single["offshore"] = mrbb.DE02['in']['source']['ee']['wind']
residual_load = demand - ee_single.sum(axis=1)
excess = mrbb.DE01['out']['excess']+mrbb.DE02['out']['excess']
shortage = mrbb.DE01['in']['shortage']

fossil = pd.DataFrame()
fossil_em=pd.DataFrame()
fossil["hard_coal"]=transformer["chp"]["hard_coal"]+transformer["pp"]["hard_coal"]
fossil["lignite"]=transformer["chp"]["lignite"]+transformer["pp"]["lignite"]
fossil["natural_gas"]=transformer["chp"]["natural_gas"]+transformer["pp"]["natural_gas"]
fossil["oil"]=transformer["chp"]["oil"]+transformer["pp"]["oil"]
fossil["other"]=transformer["chp"]["other"]+transformer["pp"]["other"]

# Emissionszeitreihe
em_per_technology = results.fetch_cost_emission(de02_NEP, with_chp=True)
em_mix = pd.DataFrame()
em_mix["hardcoal_chp"] = transformer["chp"]["hard_coal"] * em_per_technology["emission"]["hard_coal"]["DE01"]["chp"]
em_mix["hardcoal_pp"] = transformer["pp"]["hard_coal"] * em_per_technology["emission"]["hard_coal"]["DE01"]["pp"]
em_mix["lignite_chp"] = transformer["chp"]["lignite"] * em_per_technology["emission"]["lignite"]["DE01"]["chp"]
em_mix["lignite_pp"] = transformer["pp"]["lignite"] * em_per_technology["emission"]["lignite"]["DE01"]["pp"]
em_mix["natural_gas_chp"] = transformer["chp"]["natural_gas"] * em_per_technology["emission"]["natural_gas"]["DE01"]["chp"]
em_mix["natural_gas_pp"] = transformer["pp"]["natural_gas"] * em_per_technology["emission"]["natural_gas"]["DE01"]["pp"]
em_mix["oil_chp"] = transformer["chp"]["oil"] * em_per_technology["emission"]["oil"]["DE01"]["chp"]
em_mix["oil_pp"] = transformer["pp"]["oil"] * em_per_technology["emission"]["oil"]["DE01"]["pp"]
em_mix["other_chp"] = transformer["chp"]["other"] * em_per_technology["emission"]["other"]["DE01"]["chp"]
em_mix["other_pp"] = transformer["pp"]["other"] * em_per_technology["emission"]["other"]["DE01"]["pp"]

em_faktor = em_mix.sum(axis=1) / demand

# Plots
# Jahresdauerlinie Residuallast
plt.figure(1)
series = residual_load.sort_values(ascending=False)
series = series.reset_index()
plt_jdl = series.iloc[:,1]
plt.plot(plt_jdl)
plt.grid(), plt.title('Residuallast NEP C2030'), plt.ylabel('Leistung in MW')

# Leistungsbilanz
mr_plot = reegis_plot.plot_multiregion_io(de02_NEP)
plt.show()
plt.ylabel('Leistung in MW', size=16)
plt.title('Leistungsbilanz im Jahresverlauf', size=16)

# Speichereinsatz
plt.figure(2)
storage_out =  mrbb.DE01["in"]["storage"]
storage_in = - mrbb.DE01["out"]["storage"]
plt.figure(), plt.plot(storage_in), plt.plot(storage_out)
plt.title('Ein- und Ausspeicherleistung im Jahresverlauf')

# Überschüsse
plt.figure(3)
series = excess["electricity"]["all"].sort_values(ascending=False)
series = series.reset_index()
plt_excess = series.iloc[:,1]
plt.figure(), plt.grid()
plt.plot(plt_excess, lw=3)
plt.xscale(value="log")
plt.ylabel('Negative Residuallast in MW'), plt.xlabel('Stunde des Jahres'), plt.title('Jahresdauerline des "Überschusses"')
plt.figure()
plt.plot(excess), plt.title("Negative Residuallast im Jahresverlauf"), plt.ylabel('Leistung in MW')

# Emissionsfaktor
fig = plt.figure()
ax1 = fig.add_subplot(111)
line1 = ax1.plot(cost_em["mcp"], label='Maket Clearing Price'), plt.legend(loc='upper right'), plt.ylabel('MCP in €/MWh')
ax2 = ax1.twinx()
line2 = ax2.plot(em_faktor, 'y', label='Emissionsfaktor'), plt.legend(loc='upper left'), plt.ylabel('Emissionsfaktor in  kg CO2/kWh')
plt.title('Emissionsfaktor und Preissignal')

# Energiemengen im Vergleich
frames = [fossil.sum(), ee_single.sum()]
energy_deflex = pd.concat(frames) / 1000000
energy_deflex["demand"] = demand.sum() / 1000000
energy_deflex = energy_deflex.drop(labels='oil')
energy_deflex = energy_deflex.drop(labels='geothermal')

energy_NEP = pd.DataFrame({'NEP': [52.5, 60.8, 41.1, 10.3, 20.1, 99.2, 182.8, 34.1, 74, 576.5]}, index= energy_deflex.index)
bar=energy_NEP
bar["deflex"]=energy_deflex


## Barplot
labels = list(energy_deflex.index)
x = np.arange(len(labels))

fig, ax = plt.subplots()
rects1= ax.bar(x - 0.35/2, bar["NEP"].values, 0.35, label='NEP')
rects2= ax.bar(x + 0.35/2, bar["deflex"], 0.35, label='deflex')
ax.set_xticks(x)
ax.set_xticklabels(labels, size=16)
ax.legend(loc='upper left', fontsize=16)

def autolabel(rects):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = round(rect.get_height())
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', weight='bold')

autolabel(rects1)
autolabel(rects2)

plt.ylabel('Jahresenergie in TWh', size=16)
plt.title('Vergleich deflex de02-Szenario mit NEP C2030')


# Kurze Plausibilitätschecks
results.check_excess_shortage(de02_NEP)
results.emissions(de02_NEP)
results.fetch_cost_emission(de02_NEP)


# years = [2012, 2013, 2014]
# rmaps = ['de02','de17','de21','de22']
#
# for year in years:
#     for rmap in rmaps:
#         main.main(year, rmap)