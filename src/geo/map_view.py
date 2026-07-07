from pathlib import Path

import folium
import geopandas as gpd

from src.database.connection import get_connection


RESULTS_MAPS = Path("results/maps")
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

    return ulice, znakovi, semafori


def create_map():
    ulice, znakovi, semafori = load_layers()

    m = folium.Map(
        location=[45.2671, 19.8335],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    # SLOJ ULICE
    ulice_layer = folium.FeatureGroup(name="Ulice / putevi", show=True)

    folium.GeoJson(
        ulice,
        name="Ulice",
        tooltip=folium.GeoJsonTooltip(
            fields=["naziv", "tip_ulice", "ogranicenje_brzine", "duzina_km"],
            aliases=["Naziv:", "Tip ulice:", "Ogranicenje:", "Duzina km:"],
            localize=True
        ),
        style_function=lambda feature: {
            "color": "blue",
            "weight": 2,
            "opacity": 0.6
        }
    ).add_to(ulice_layer)

    ulice_layer.add_to(m)

    # SLOJ ZNAKOVI
    znakovi_layer = folium.FeatureGroup(name="Saobracajni znakovi", show=True)

    for _, row in znakovi.iterrows():
        if row.geom is None:
            continue

        lat = row.geom.y
        lon = row.geom.x

        color = "red" if row["tip_znaka"] == "stop" else "orange"

        folium.Marker(
            location=[lat, lon],
            popup=f"""
            <b>Tip:</b> {row['tip_znaka']}<br>
            <b>Opis:</b> {row['opis']}<br>
            <b>Stanje:</b> {row['stanje']}
            """,
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(znakovi_layer)

    znakovi_layer.add_to(m)

    # SLOJ SEMAFORI
    semafori_layer = folium.FeatureGroup(name="Semafori", show=True)

    for _, row in semafori.iterrows():
        if row.geom is None:
            continue

        lat = row.geom.y
        lon = row.geom.x

        folium.Marker(
            location=[lat, lon],
            popup=f"""
            <b>Status:</b> {row['status']}<br>
            <b>Tip:</b> {row['tip']}
            """,
            icon=folium.Icon(color="green", icon="ok-sign")
        ).add_to(semafori_layer)

    semafori_layer.add_to(m)

    folium.LayerControl().add_to(m)

    output_path = RESULTS_MAPS / "katastar_signalizacije_map.html"
    m.save(output_path)

    print(f"Mapa je sacuvana: {output_path}")


if __name__ == "__main__":
    create_map()