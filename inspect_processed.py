import geopandas as gpd


def main():
    roads = gpd.read_file("data/processed/novi_sad_roads.geojson")
    traffic = gpd.read_file("data/processed/novi_sad_traffic.geojson")
    pois = gpd.read_file("data/processed/novi_sad_pois.geojson")

    print("=" * 60)
    print("ROADS fclass:")
    print(roads["fclass"].value_counts().head(30))

    print("=" * 60)
    print("TRAFFIC fclass:")
    print(traffic["fclass"].value_counts().head(50))

    print("=" * 60)
    print("POIS fclass:")
    print(pois["fclass"].value_counts().head(50))

    print("=" * 60)
    print("Primer traffic podataka:")
    print(traffic.head(20))


if __name__ == "__main__":
    main()