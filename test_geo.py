from src.geo.load_data import (
    load_roads,
    load_traffic,
    load_traffic_areas,
    load_pois,
    load_pois_areas,
    print_layer_info,
)


def main():
    roads = load_roads()
    traffic = load_traffic()
    traffic_areas = load_traffic_areas()
    pois = load_pois()
    pois_areas = load_pois_areas()

    print_layer_info("ROADS", roads)
    print_layer_info("TRAFFIC", traffic)
    print_layer_info("TRAFFIC AREAS", traffic_areas)
    print_layer_info("POIS", pois)
    print_layer_info("POIS AREAS", pois_areas)


if __name__ == "__main__":
    main()