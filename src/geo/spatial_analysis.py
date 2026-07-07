from pathlib import Path

import folium
import geopandas as gpd
from folium.plugins import HeatMap

from src.database.connection import get_connection


RESULTS_ANALYSIS = Path("results/analysis")
RESULTS_MAPS = Path("results/maps")

RESULTS_ANALYSIS.mkdir(parents=True, exist_ok=True)
RESULTS_MAPS.mkdir(parents=True, exist_ok=True)


def read_geodata(query):
    conn = get_connection()
    gdf = gpd.read_postgis(query, conn, geom_col="geom")
    conn.close()
    return gdf


def load_layers():
    ulice = read_geodata("""
        SELECT id, naziv, tip_ulice, ogranicenje_brzine, duzina_km, geom
        FROM ulice;
    """)

    znakovi = read_geodata("""
        SELECT id, tip_znaka, opis, stanje, geom
        FROM saobracajni_znakovi;
    """)

    semafori = read_geodata("""
        SELECT id, status, tip, geom
        FROM semafori;
    """)

    raskrsnice = read_geodata("""
        SELECT id, naziv, tip, ima_semafor, prometnost, geom
        FROM raskrsnice;
    """)

    return ulice, znakovi, semafori, raskrsnice


def analysis_1_nearest_road_for_signs():
    """
    Za svaki znak pronalazi najbližu ulicu.
    Ovo je prostorna analiza tipa nearest spatial join.
    """
    ulice, znakovi, _, _ = load_layers()

    ulice_m = ulice.to_crs(epsg=32634)
    znakovi_m = znakovi.to_crs(epsg=32634)

    result = gpd.sjoin_nearest(
        znakovi_m,
        ulice_m[["id", "naziv", "tip_ulice", "geom"]],
        how="left",
        distance_col="udaljenost_m"
    )

    result = result.rename(columns={
        "id_left": "znak_id",
        "id_right": "ulica_id",
        "naziv": "najbliza_ulica"
    })

    result = result[
        [
            "znak_id",
            "tip_znaka",
            "stanje",
            "ulica_id",
            "najbliza_ulica",
            "tip_ulice",
            "udaljenost_m"
        ]
    ]

    output = RESULTS_ANALYSIS / "znakovi_najbliza_ulica.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Analiza 1 sacuvana: {output}")
    print(result.head())

    return result


def analysis_2_signs_near_traffic_lights(distance_m=50):
    """
    Pronalazi znakove koji se nalaze u radijusu od 50m od semafora.
    Koristi buffer + spatial join.
    """
    _, znakovi, semafori, _ = load_layers()

    znakovi_m = znakovi.to_crs(epsg=32634)
    semafori_m = semafori.to_crs(epsg=32634)

    semafori_buffer = semafori_m.copy()
    semafori_buffer["geom"] = semafori_buffer.geometry.buffer(distance_m)
    semafori_buffer = semafori_buffer.set_geometry("geom")

    result = gpd.sjoin(
        znakovi_m,
        semafori_buffer[["id", "status", "geom"]],
        how="inner",
        predicate="within"
    )

    result = result.rename(columns={
        "id_left": "znak_id",
        "id_right": "semafor_id"
    })

    result = result[
        [
            "znak_id",
            "tip_znaka",
            "stanje",
            "semafor_id",
            "status"
        ]
    ]

    output = RESULTS_ANALYSIS / "znakovi_u_blizini_semafora.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Analiza 2 sacuvana: {output}")
    print(result.head())

    return result


def analysis_3_signs_by_type():
    """
    Broji saobraćajne znakove po tipu.
    Ovo je atributska analiza nad prostornim slojem.
    """
    _, znakovi, _, _ = load_layers()

    result = (
        znakovi.groupby("tip_znaka")
        .size()
        .reset_index(name="broj_znakova")
        .sort_values("broj_znakova", ascending=False)
    )

    output = RESULTS_ANALYSIS / "broj_znakova_po_tipu.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Analiza 3 sacuvana: {output}")
    print(result)

    return result


def analysis_4_traffic_lights_near_intersections(distance_m=30):
    """
    Proverava da li su semafori prostorno blizu raskrsnica.
    Koristi buffer oko raskrsnica.
    """
    _, _, semafori, raskrsnice = load_layers()

    semafori_m = semafori.to_crs(epsg=32634)
    raskrsnice_m = raskrsnice.to_crs(epsg=32634)

    raskrsnice_buffer = raskrsnice_m.copy()
    raskrsnice_buffer["geom"] = raskrsnice_buffer.geometry.buffer(distance_m)
    raskrsnice_buffer = raskrsnice_buffer.set_geometry("geom")

    result = gpd.sjoin(
        semafori_m,
        raskrsnice_buffer[["id", "naziv", "tip", "geom"]],
        how="inner",
        predicate="within"
    )

    result = result.rename(columns={
        "id_left": "semafor_id",
        "id_right": "raskrsnica_id",
        "naziv": "naziv_raskrsnice",
        "tip_right": "tip_raskrsnice"
    })

    result = result[
        [
            "semafor_id",
            "status",
            "raskrsnica_id",
            "naziv_raskrsnice",
            "tip_raskrsnice"
        ]
    ]

    output = RESULTS_ANALYSIS / "semafori_u_blizini_raskrsnica.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"Analiza 4 sacuvana: {output}")
    print(result.head())

    return result


def analysis_5_create_heatmap():
    """
    Pravi heatmap gustine saobraćajne signalizacije.
    """
    _, znakovi, semafori, _ = load_layers()

    m = folium.Map(
        location=[45.2671, 19.8335],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    heat_points = []

    for _, row in znakovi.iterrows():
        if row.geom is not None:
            heat_points.append([row.geom.y, row.geom.x])

    for _, row in semafori.iterrows():
        if row.geom is not None:
            heat_points.append([row.geom.y, row.geom.x])

    HeatMap(
        heat_points,
        name="Gustina signalizacije",
        radius=15,
        blur=20
    ).add_to(m)

    folium.LayerControl().add_to(m)

    output = RESULTS_MAPS / "heatmap_signalizacije.html"
    m.save(output)

    print(f"Analiza 5 - heatmap sacuvana: {output}")


def run_all_spatial_analyses():
    print("Pokretanje prostornih analiza...")

    analysis_1_nearest_road_for_signs()
    analysis_2_signs_near_traffic_lights()
    analysis_3_signs_by_type()
    analysis_4_traffic_lights_near_intersections()
    analysis_5_create_heatmap()

    print("Sve prostorne analize su zavrsene.")


if __name__ == "__main__":
    run_all_spatial_analyses()