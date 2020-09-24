import glaes as gl
import pandas as pd
from disaggregator import data
import numpy as np
from reegis import config as cfg
import os


def calculate_wind_area_speed_only(region, v_wind):
    # Choose Region
    ecWind = gl.ExclusionCalculator(region, srs=3035, pixelSize=100, limitOne=False)
    ecWind.excludePrior('windspeed_100m_threshold', value=(None, v_wind))
    area = ecWind.areaAvailable

    return area


def calc_wind_areas_speed_only(path, v_wind):
    nuts3_gdf = data.database_shapes()
    list_filenames = list()
    suitable_area = pd.DataFrame(index=nuts3_gdf.index, columns=["wind_area"])

    for nuts3_name in nuts3_gdf.index:
        list_filenames.append(path + '/' + nuts3_name + '.geojson')

    #list_filenames = list_filenames[0:10]

    for n in list_filenames:
        idx = n[len(path):len(path) + 5]
        area_wind = calculate_wind_area_speed_only(n, v_wind)
        suitable_area["wind_area"][idx] = area_wind

    return suitable_area



path = '/home/dbeier/git-projects/test_repo/nuts3_geojson/'
DE = '/home/dbeier/git-projects/reegis/reegis/data/geometries/germany_polygon.geojson'
nuts3_index = data.database_shapes().index

def calc_average_windspeed_by_nuts3():

    fn = os.path.join(cfg.get("paths", "GLAES"), 'mean_wind_velocity_by_nuts3.csv')

    if not os.path.isfile(fn):

        path = os.path.join(cfg.get("paths", "GLAES"), 'nuts3_geojson')
        nuts3_index = data.database_shapes().index
        area_compare = pd.DataFrame(index=nuts3_index)

        for v_wind in range(0,21):
            v_wind = v_wind/2
            area_tmp = calc_wind_areas_speed_only(path, v_wind)
            area_compare[str(v_wind)+" m/s"] = area_tmp
            #print(area_tmp)

        cols = area_compare.columns
        speed_per_NUTS3 = pd.DataFrame(index=nuts3_index, columns=cols)

        for n in range (0,len(cols)-1):
            speed_per_NUTS3[cols[n]] = abs(area_compare[cols[n+1]] - area_compare[cols[n]])
        speed_per_NUTS3[cols[20]] = area_compare[cols[20]]


        v_wind = np.linspace(0, 10, num=21)
        v_mean = pd.DataFrame(index=nuts3_index, columns=['v_mean'])

        for idx in nuts3_index:
            v_composition = speed_per_NUTS3.loc[idx]
            tmp = sum(v_composition*v_wind) / sum(v_composition)
            v_mean.loc[idx][v_mean] = tmp

        v_mean.to_csv(fn)
    else:
        v_mean = pd.read_csv(fn)
        v_mean.set_index('nuts3', drop=True, inplace=True)

    return v_mean


v_mean = calc_average_windspeed_by_nuts3()

#for v_wind in range(0,12,3):
#    ecWind = gl.ExclusionCalculator(DE, srs=3035, pixelSize=100, limitOne=False)
#    ecWind.excludePrior('windspeed_100m_threshold', value=(None, v_wind))
#    area = ecWind.areaAvailable

