from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from src.geo.load_data import load_roads, load_traffic, load_pois


PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

NOVI_SAD_BBOX = box(19.70, 45.18, 19.98, 45.35)


def filter_by_novi_sad_area(gdf):
    novi_sad_area = gpd.GeoDataFrame(
        geometry=[NOVI_SAD_BBOX],
        crs="EPSG:4326"
    )

    return gpd.clip(gdf, novi_sad_area)


def preprocess_roads():
    roads = load_roads()
    roads_ns = filter_by_novi_sad_area(roads)

    important_classes = [
        "motorway", "trunk", "primary", "secondary", "tertiary",
        "residential", "unclassified", "service", "living_street",
    ]

    roads_ns = roads_ns[roads_ns["fclass"].isin(important_classes)]

    roads_ns = roads_ns[
        ["osm_id", "fclass", "name", "ref", "oneway", "maxspeed", "geometry"]
    ]

    roads_ns = roads_ns.dropna(subset=["geometry"])
    roads_ns = roads_ns.reset_index(drop=True)

    roads_ns.to_file(PROCESSED_PATH / "novi_sad_roads.geojson", driver="GeoJSON")

    print(f"Sacuvani putevi za Novi Sad: {len(roads_ns)}")
    return roads_ns


def preprocess_traffic():
    traffic = load_traffic()
    traffic_ns = filter_by_novi_sad_area(traffic)

    traffic_ns = traffic_ns[
        ["osm_id", "fclass", "name", "calming", "geometry"]
    ]

    traffic_ns = traffic_ns.dropna(subset=["geometry"])
    traffic_ns = traffic_ns.reset_index(drop=True)

    traffic_ns.to_file(PROCESSED_PATH / "novi_sad_traffic.geojson", driver="GeoJSON")

    print(f"Sacuvani saobracajni objekti za Novi Sad: {len(traffic_ns)}")
    return traffic_ns


def preprocess_pois():
    pois = load_pois()
    pois_ns = filter_by_novi_sad_area(pois)

    useful_pois = [
        "school", "kindergarten", "hospital", "bus_stop",
        "parking", "fuel", "police", "university",
    ]

    pois_ns = pois_ns[pois_ns["fclass"].isin(useful_pois)]

    pois_ns = pois_ns[
        ["osm_id", "fclass", "name", "geometry"]
    ]

    pois_ns = pois_ns.dropna(subset=["geometry"])
    pois_ns = pois_ns.reset_index(drop=True)

    pois_ns.to_file(PROCESSED_PATH / "novi_sad_pois.geojson", driver="GeoJSON")

    print(f"Sacuvani POI objekti za Novi Sad: {len(pois_ns)}")
    return pois_ns


def main():
    print("Pocinje obrada Geofabrik OSM podataka...")

    roads = preprocess_roads()
    traffic = preprocess_traffic()
    pois = preprocess_pois()

    print()
    print("Obrada zavrsena.")
    print(f"Putevi: {len(roads)}")
    print(f"Saobracajni objekti: {len(traffic)}")
    print(f"POI objekti: {len(pois)}")


if __name__ == "__main__":
    main()