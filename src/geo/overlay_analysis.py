from pathlib import Path

import geopandas as gpd

from src.database.connection import get_connection


RESULTS_ANALYSIS = Path("results/analysis")
RESULTS_ANALYSIS.mkdir(parents=True, exist_ok=True)


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

    return ulice, znakovi, semafori


def create_city_analysis_area(ulice):
    """
    Pravi okvir analize oko svih ulica u Novom Sadu.
    Ovo koristimo kao oblast za clip/intersection analize.
    """
    ulice_m = ulice.to_crs(epsg=32634)

    city_area = gpd.GeoDataFrame(
        {"naziv": ["Zona analize Novi Sad"]},
        geometry=[ulice_m.union_all().convex_hull.buffer(500)],
        crs=ulice_m.crs
    )

    return city_area


def overlay_1_clip_roads_to_analysis_area():
    """
    CLIP analiza:
    izdvajanje ulica koje pripadaju zoni analize.
    """
    ulice, _, _ = load_layers()

    ulice_m = ulice.to_crs(epsg=32634)
    city_area = create_city_analysis_area(ulice)

    clipped = gpd.clip(ulice_m, city_area)

    output = RESULTS_ANALYSIS / "overlay_clip_ulice.csv"
    clipped.drop(columns="geom").to_csv(output, index=False, encoding="utf-8-sig")

    print(f"CLIP analiza sacuvana: {output}")
    print(clipped.head())

    return clipped


def overlay_2_buffer_main_roads(distance_m=100):
    """
    BUFFER analiza:
    pravi buffer od 100m oko glavnih puteva.
    """
    ulice, _, _ = load_layers()

    ulice_m = ulice.to_crs(epsg=32634)

    main_roads = ulice_m[
        ulice_m["tip_ulice"].isin(["primary", "secondary", "tertiary", "trunk", "motorway"])
    ]

    buffers = main_roads.copy()
    buffers["geom"] = buffers.geometry.buffer(distance_m)
    buffers = buffers.set_geometry("geom")

    output = RESULTS_ANALYSIS / "overlay_buffer_glavni_putevi.csv"
    buffers.drop(columns="geom").to_csv(output, index=False, encoding="utf-8-sig")

    print(f"BUFFER analiza sacuvana: {output}")
    print(buffers.head())

    return buffers


def overlay_3_intersection_signs_main_roads_buffer():
    """
    INTERSECTION analiza:
    pronalazi znakove koji se nalaze u buffer zoni glavnih puteva.
    """
    _, znakovi, _ = load_layers()

    znakovi_m = znakovi.to_crs(epsg=32634)
    buffers = overlay_2_buffer_main_roads(distance_m=100)

    result = gpd.sjoin(
        znakovi_m,
        buffers[["id", "naziv", "tip_ulice", "geom"]],
        how="inner",
        predicate="within"
    )

    result = result.rename(columns={
        "id_left": "znak_id",
        "id_right": "ulica_id",
        "naziv": "naziv_ulice"
    })

    result = result[
        [
            "znak_id",
            "tip_znaka",
            "stanje",
            "ulica_id",
            "naziv_ulice",
            "tip_ulice"
        ]
    ]

    output = RESULTS_ANALYSIS / "overlay_intersection_znakovi_glavni_putevi.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")

    print(f"INTERSECTION analiza sacuvana: {output}")
    print(result.head())

    return result


def overlay_4_union_signalization_zones():
    """
    UNION analiza:
    spaja buffer zone znakova i semafora u jednu zonu pokrivenosti signalizacijom.
    """
    _, znakovi, semafori = load_layers()

    znakovi_m = znakovi.to_crs(epsg=32634)
    semafori_m = semafori.to_crs(epsg=32634)

    znakovi_buffer = znakovi_m.copy()
    znakovi_buffer["geom"] = znakovi_buffer.geometry.buffer(30)
    znakovi_buffer = znakovi_buffer.set_geometry("geom")
    znakovi_buffer["tip_zone"] = "zona_znakova"

    semafori_buffer = semafori_m.copy()
    semafori_buffer["geom"] = semafori_buffer.geometry.buffer(50)
    semafori_buffer = semafori_buffer.set_geometry("geom")
    semafori_buffer["tip_zone"] = "zona_semafora"

    zones = gpd.GeoDataFrame(
        columns=["tip_zone", "geom"],
        geometry="geom",
        crs=znakovi_buffer.crs
    )

    zones = gpd.GeoDataFrame(
        [
            {"tip_zone": "zona_znakova", "geom": znakovi_buffer.union_all()},
            {"tip_zone": "zona_semafora", "geom": semafori_buffer.union_all()},
        ],
        geometry="geom",
        crs=znakovi_buffer.crs
    )

    union_zone = gpd.GeoDataFrame(
        [{"tip_zone": "ukupna_zona_signalizacije", "geom": zones.union_all()}],
        geometry="geom",
        crs=zones.crs
    )

    output = RESULTS_ANALYSIS / "overlay_union_zone_signalizacije.csv"
    union_zone.drop(columns="geom").to_csv(output, index=False, encoding="utf-8-sig")

    print(f"UNION analiza sacuvana: {output}")
    print(union_zone)

    return union_zone


def overlay_5_difference_roads_outside_signalization_zone():
    """
    DIFFERENCE analiza:
    pronalazi delove ulica koji nisu pokriveni zonom signalizacije.
    """
    ulice, _, _ = load_layers()

    ulice_m = ulice.to_crs(epsg=32634)
    union_zone = overlay_4_union_signalization_zones()

    roads_union = gpd.GeoDataFrame(
        [{"naziv": "sve_ulice", "geom": ulice_m.union_all()}],
        geometry="geom",
        crs=ulice_m.crs
    )

    difference = gpd.overlay(
        roads_union,
        union_zone,
        how="difference"
    )

    output = RESULTS_ANALYSIS / "overlay_difference_ulice_van_signalizacije.csv"
    difference.drop(columns="geom").to_csv(output, index=False, encoding="utf-8-sig")

    print(f"DIFFERENCE analiza sacuvana: {output}")
    print(difference.head())

    return difference


def run_all_overlay_analyses():
    print("Pokretanje overlay analiza...")

    overlay_1_clip_roads_to_analysis_area()
    overlay_2_buffer_main_roads()
    overlay_3_intersection_signs_main_roads_buffer()
    overlay_4_union_signalization_zones()
    overlay_5_difference_roads_outside_signalization_zone()

    print("Sve overlay analize su zavrsene.")


if __name__ == "__main__":
    run_all_overlay_analyses()