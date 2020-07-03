import os
from matplotlib import pyplot as plt
from deflex import analyses
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

bas_path = "/home/uwe/reegis/scenarios/deflex/2014/"
csv_path = os.path.join(bas_path, "deflex_2014_de02_no-heat_reg-merit_csv")
my_pp1 = plausibility_checks.get_merit_order_reegis(2014)
my_pp2 = analyses.merit_order_from_scenario(csv_path)
my_pp3 = plausibility_checks.get_merit_order_reegis(2014, 1)

f, ax_ar = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

plot_merit_order(my_pp1, ax_ar[0])
plot_merit_order(my_pp2, ax_ar[1])
plot_merit_order(my_pp3, ax_ar[2])
plt.show()
