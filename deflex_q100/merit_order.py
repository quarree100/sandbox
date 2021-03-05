import os
from matplotlib import pyplot as plt
from deflex import analyses, DeflexScenario
from plotting import plot_merit_order
import plausibility_checks


cdict = {
    "nuclear": "#DDF45B",
    "hard coal": "#141115",
    "lignite": "#8D6346",
    "natural gas": "#4C2B36",
    "oil": "#C1A5A9",
    "bioenergy": "#163e16",
    "hydro": "#14142c",
    "solar": "#ffde32",
    "wind": "#335a8a",
    "other fossil fuels": "#312473",
    "other": "#312473",
    "waste": "#547969",
    "geothermal": "#f32eb7",
}

bas_path = "/home/uwe/.deflex/tmp_test_32traffic_43/"
csv_path = os.path.join(bas_path, "de02_co2-price_var-costs.xlsx")
sc = DeflexScenario()

# sc.read_xlsx(csv_path)
# my_pp1 = plausibility_checks.get_merit_order_reegis(2014)
# my_pp2 = analyses.merit_order_from_scenario(sc)
# my_pp3 = plausibility_checks.get_merit_order_reegis(2014, 2)
# f, ax_ar = plt.subplots(3, 1, figsize=(15, 10), sharex=True, sharey=True)
#
# d = [i for i in my_pp2.index if "bioenergy" in i[1] or "other" in i[1]]
# print(my_pp2.index)
# print(d)
# my_pp2.drop(d, inplace=True)
#
# plot_merit_order(my_pp1, ax_ar[0])
# plot_merit_order(my_pp3, ax_ar[1])
# plot_merit_order(my_pp2, ax_ar[2])

sc.read_xlsx(csv_path)
pp = analyses.merit_order_from_scenario(sc)

ax = plt.figure(figsize=(15, 4)).add_subplot(1, 1, 1)
ax.step(pp["capacity_cum"].values, pp["costs_total"].values, where="pre")
ax.set_xlabel("Cumulative capacity [GW]")
ax.set_ylabel("Marginal costs [EUR/MWh]")
ax.set_ylim(0)
ax.set_xlim(0, pp["capacity_cum"].max())

# plt.show()
# exit(0)
# d = [i for i in pp.index if "bioenergy" in i[1] or "other" in i[1]]
# pp.drop(d, inplace=True)
g, ax = plt.subplots(1, 1, figsize=(15, 4), sharex=True, sharey=True)
plot_merit_order(pp, ax)
plt.show()
