import numpy as np
import pandas as pd


def plot_merit_order(pp, ax):
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

    df = pd.DataFrame(columns=pp.columns)
    remove = []
    pp.reset_index(inplace=True)
    for i in range(len(pp)):
        if 0 < i < len(pp) - 1:
            fuel = pp.iloc[i].fuel
            if pp.iloc[i-1].fuel != fuel and pp.iloc[i+1].fuel != fuel:
                index = pp.iloc[i].name
                capacity = pp.iloc[i].capacity
                for n in range(2):
                    df.loc[index + n/10] = pp.iloc[i]
                    df.loc[index + n/10, "capacity"] = capacity/2
                remove.append(index)
        elif i == 0:
            index = pp.iloc[i].name
            df.loc[index + 1/10] = pp.iloc[i]
            df.loc[index + 1/10, "capacity"] = 0

    pp.drop(remove, inplace=True)
    pp = pd.concat([pp, df])
    pp.sort_values(["costs_total", "capacity"], inplace=True)
    pp["capacity_cum"] = pp.capacity.cumsum().div(1000)

    for src in pp.fuel.unique():
        pp[src] = pp.costs_total
        pp.loc[pp.fuel != src, src] = np.nan
        pp[src].fillna(method="bfill", limit=1, inplace=True)
        ax.fill_between(
            pp["capacity_cum"], pp[src], step="pre", color=cdict[src]
        )
    pp.to_csv("/home/uwe/00aa.csv")
    pp.set_index("capacity_cum")[pp.fuel.unique()].plot(ax=ax, alpha=0)
    ax.set_xlabel("Cumulative capacity [GW]")
    ax.set_ylabel("Marginal costs [EUR/MWh]")
    ax.set_ylim(0)
    ax.set_xlim(0, pp["capacity_cum"].max())
    ax.legend(loc=2, title="fuel of power plant")
    for leg in ax.get_legend().legendHandles:
        leg.set_color(cdict[leg.get_label()])
        leg.set_linewidth(4.0)
        leg.set_alpha(1)
