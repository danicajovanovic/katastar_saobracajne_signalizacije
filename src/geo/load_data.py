from pathlib import Path

import geopandas as gpd


DATA_PATH = Path("data/shp")

ROADS_FILE = DATA_PATH / "gis_osm_roads_free_1.shp"
TRAFFIC_FILE = DATA_PATH / "gis_osm_traffic_free_1.shp"
TRAFFIC_AREAS_FILE = DATA_PATH / "gis_osm_traffic_a_free_1.shp"
POIS_FILE = DATA_PATH / "gis_osm_pois_free_1.shp"
POIS_AREAS_FILE = DATA_PATH / "gis_osm_pois_a_free_1.shp"


def load_roads():
    roads = gpd.read_file(ROADS_FILE)
    return roads


def load_traffic():
    traffic = gpd.read_file(TRAFFIC_FILE)
    return traffic


def load_traffic_areas():
    traffic_areas = gpd.read_file(TRAFFIC_AREAS_FILE)
    return traffic_areas


def load_pois():
    pois = gpd.read_file(POIS_FILE)
    return pois


def load_pois_areas():
    pois_areas = gpd.read_file(POIS_AREAS_FILE)
    return pois_areas


def print_layer_info(name, gdf):
    print("=" * 80)
    print(f"SLOJ: {name}")
    print("=" * 80)

    print("\nPrvih 5 redova:")
    print(gdf.head())

    print("\nKolone:")
    print(gdf.columns)

    print("\nCRS:")
    print(gdf.crs)

    print("\nBroj redova:")
    print(len(gdf))

    print("\nTipovi geometrije:")
    print(gdf.geometry.geom_type.value_counts())

    print("\n")