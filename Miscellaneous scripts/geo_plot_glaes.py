import geopandas as gpd
from matplotlib import pyplot as plt
import contextily as ctx


def plot_sites_with_map(filename, yoff=0, xoff=0, zoom=8, alpha=0.8,
                        url='https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'):

    # Einlesen eines Pointlayers
    coords = gpd.read_file(filename)
    # Ggf. Versatz der Punktkoordinaten notwendig
    coords=coords.translate(yoff=yoff, xoff=xoff)
        # Plot der Punkte auf Karte
    ax = plt.figure(figsize=(5, 6)).add_subplot(1, 1, 1)
    ax = coords.plot(ax=ax)
    ctx.add_basemap(ax, zoom=zoom, url=my_url, alpha=alpha)
    ax.set_axis_off()
    #plt.show()



osm_maps = {
    'OSM default': 'https://a.tile.openstreetmap.org/',
    'Wikimedia Maps': 'https://maps.wikimedia.org/osm-intl/',
    'OpenCycleMap': 'http://tile.thunderforest.com/cycle/',
    'Humanitarian map style': 'http://a.tile.openstreetmap.fr/hot/',
    'OSM France': 'http://a.tile.openstreetmap.fr/osmfr/',
    'wmflabs_hike_bike': 'https://tiles.wmflabs.org/hikebike/',
    'wmflabs Hillshading': 'http://tiles.wmflabs.org/hillshading/',
    'wmflabs OSM BW': 'https://tiles.wmflabs.org/bw-mapnik/',
    'wmflabs OSM no labels': 'https://tiles.wmflabs.org/osm-no-labels/',
    'Stamen Toner': 'http://a.tile.stamen.com/toner/',
    'Stamen Watercolor': 'http://c.tile.stamen.com/watercolor/',
    'Thunderforest Landscape': 'http://tile.thunderforest.com/landscape/',
    'Thunderforest Outdoors': 'http://tile.thunderforest.com/outdoors/',
    'OpenTopoMap': 'https://a.tile.opentopomap.org/'
}

# Parameter für plot
#filename = '/home/dbeier/git-projects/deflex/deflex/data/geometries/region_polygons_de21.geojson'
filename='/home/dbeier/git-projects/db_test_repo/nuts3_geojson/DE111.geojson'
#filename = 'site_coordsWind_epsg3857_BB.geojson'
url = osm_maps['OSM default']
my_url = '/'.join(s.strip('/') for s in [url, '/{z}/{x}/{y}.png'])
zoom = 10
alpha = 0.8

# Plot Sites
plot_sites_with_map(filename, yoff=0, url=my_url, zoom=zoom)



