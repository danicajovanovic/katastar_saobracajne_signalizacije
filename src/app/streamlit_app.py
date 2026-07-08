import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import pandas as pd
import streamlit as st
import geopandas as gpd
import folium

from streamlit_folium import st_folium

from src.database.connection import get_connection
from src.database.crud import (
    create_traffic_sign,
    update_traffic_sign,
    delete_traffic_sign,
)
from src.database.queries import (
    query_1_speed_limit_over_50,
    query_2_signs_by_type,
    query_3_traffic_lights_by_status,
    query_4_traffic_lights_with_intersections,
    query_5_ml_with_signs,
    query_6_longest_roads,
    query_7_average_road_length,
    query_8_roads_by_category,
    query_9_signs_by_condition,
    query_10_high_confidence_ml,
)
from src.ml.detector import detect_image


st.set_page_config(
    page_title="Katastar saobraćajne signalizacije",
    layout="wide"
)


def read_dataframe(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def read_geodata(query):
    conn = get_connection()
    gdf = gpd.read_postgis(query, conn, geom_col="geom")
    conn.close()
    return gdf


def dashboard_page():
    st.title("Katastar saobraćajne signalizacije")

    col1, col2, col3, col4, col5 = st.columns(5)

    tables = {
        "Ulice": "ulice",
        "Znakovi": "saobracajni_znakovi",
        "Semafori": "semafori",
        "Raskrsnice": "raskrsnice",
        "ML detekcije": "ml_detekcije",
    }

    for col, (label, table) in zip([col1, col2, col3, col4, col5], tables.items()):
        count = read_dataframe(f"SELECT COUNT(*) AS broj FROM {table};")["broj"][0]
        col.metric(label, int(count))

    st.markdown("""
    Aplikacija koristi PostgreSQL/PostGIS bazu, OpenStreetMap/Geofabrik podatke,
    GeoPandas prostornu obradu, interaktivnu mapu i YOLO model za detekciju objekata
    od interesa na fotografijama.
    """)


def map_page():
    st.title("Interaktivna mapa")

    show_roads = st.checkbox("Prikaži ulice", True)
    show_signs = st.checkbox("Prikaži znakove", True)
    show_lights = st.checkbox("Prikaži semafore", True)
    show_ml = st.checkbox("Prikaži ML detekcije", True)

    m = folium.Map(
        location=[45.2671, 19.8335],
        zoom_start=13,
        tiles="OpenStreetMap"
    )

    if show_roads:
        ulice = read_geodata("""
            SELECT id, naziv, tip_ulice, ogranicenje_brzine, duzina_km, geom
            FROM ulice
            LIMIT 3000;
        """)

        folium.GeoJson(
            ulice,
            name="Ulice",
            tooltip=folium.GeoJsonTooltip(
                fields=["naziv", "tip_ulice", "ogranicenje_brzine"],
                aliases=["Naziv:", "Tip:", "Ograničenje:"],
            ),
            style_function=lambda feature: {
                "color": "blue",
                "weight": 2,
                "opacity": 0.5,
            }
        ).add_to(m)

    if show_signs:
        znakovi = read_geodata("""
            SELECT id, tip_znaka, opis, stanje, geom
            FROM saobracajni_znakovi
            LIMIT 1000;
        """)

        for _, row in znakovi.iterrows():
            if row.geom is None:
                continue

            color = "red" if row["tip_znaka"] == "stop" else "orange"

            folium.Marker(
                location=[row.geom.y, row.geom.x],
                popup=f"""
                <b>Tip:</b> {row['tip_znaka']}<br>
                <b>Opis:</b> {row['opis']}<br>
                <b>Stanje:</b> {row['stanje']}
                """,
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)

    if show_lights:
        semafori = read_geodata("""
            SELECT id, status, tip, geom
            FROM semafori
            LIMIT 1000;
        """)

        for _, row in semafori.iterrows():
            if row.geom is None:
                continue

            folium.Marker(
                location=[row.geom.y, row.geom.x],
                popup=f"""
                <b>Semafor</b><br>
                <b>Status:</b> {row['status']}<br>
                <b>Tip:</b> {row['tip']}
                """,
                icon=folium.Icon(color="green", icon="ok-sign")
            ).add_to(m)

    if show_ml:
        ml = read_geodata("""
            SELECT id, klasa, confidence, naziv_slike, datum, geom
            FROM ml_detekcije
            WHERE geom IS NOT NULL;
        """)

        for _, row in ml.iterrows():
            folium.Marker(
                location=[row.geom.y, row.geom.x],
                popup=f"""
                <b>ML detekcija</b><br>
                <b>Klasa:</b> {row['klasa']}<br>
                <b>Confidence:</b> {row['confidence']}<br>
                <b>Slika:</b> {row['naziv_slike']}<br>
                <b>Datum:</b> {row['datum']}
                """,
                icon=folium.Icon(color="purple", icon="camera")
            ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=1200, height=650)


def tables_page():
    st.title("Pregled tabela")

    table = st.selectbox(
        "Izaberi tabelu",
        ["ulice", "saobracajni_znakovi", "semafori", "raskrsnice", "ml_detekcije"]
    )

    df = read_dataframe(f"SELECT * FROM {table} ORDER BY id LIMIT 200;")
    st.dataframe(df, use_container_width=True)


def crud_page():
    st.title("CRUD operacije nad saobraćajnim znakovima")

    tab1, tab2, tab3 = st.tabs(["Dodaj znak", "Izmeni znak", "Obriši znak"])

    with tab1:
        tip = st.text_input("Tip znaka", "rucno_dodat_znak")
        opis = st.text_area("Opis", "Ručno dodat znak kroz aplikaciju")
        stanje = st.selectbox("Stanje", ["dobro", "ostecen", "potrebno odrzavanje"])
        proizvodjac = st.text_input("Proizvođač", "Korisnički unos")
        lon = st.number_input("Longitude", value=19.8335, format="%.6f")
        lat = st.number_input("Latitude", value=45.2671, format="%.6f")

        if st.button("Dodaj znak"):
            create_traffic_sign(tip, opis, stanje, proizvodjac, lon, lat)
            st.success("Znak je dodat.")

    with tab2:
        sign_id = st.number_input("ID znaka za izmenu", min_value=1, step=1)
        novo_stanje = st.selectbox(
            "Novo stanje",
            ["dobro", "ostecen", "potrebno odrzavanje"],
            key="novo_stanje"
        )

        if st.button("Izmeni znak"):
            update_traffic_sign(sign_id, novo_stanje)
            st.success("Znak je izmenjen.")

    with tab3:
        delete_id = st.number_input("ID znaka za brisanje", min_value=1, step=1, key="delete_id")

        if st.button("Obriši znak"):
            delete_traffic_sign(delete_id)
            st.warning("Znak je obrisan.")


def sql_queries_page():
    st.title("SQL upiti")

    queries = {
        "Ulice sa ograničenjem > 50": query_1_speed_limit_over_50,
        "Broj znakova po tipu": query_2_signs_by_type,
        "Broj semafora po statusu": query_3_traffic_lights_by_status,
        "JOIN semafori-raskrsnice": query_4_traffic_lights_with_intersections,
        "JOIN ML detekcije-znakovi": query_5_ml_with_signs,
        "Najduže ulice": query_6_longest_roads,
        "Prosečna dužina po kategoriji": query_7_average_road_length,
        "Broj ulica po kategoriji": query_8_roads_by_category,
        "Broj znakova po stanju": query_9_signs_by_condition,
        "ML confidence > 0.85": query_10_high_confidence_ml,
    }

    selected = st.selectbox("Izaberi upit", list(queries.keys()))

    if st.button("Pokreni upit"):
        df = queries[selected]()
        st.dataframe(df, use_container_width=True)


def analysis_page():
    st.title("Rezultati prostornih analiza")

    files = [
        "znakovi_najbliza_ulica.csv",
        "znakovi_u_blizini_semafora.csv",
        "broj_znakova_po_tipu.csv",
        "semafori_u_blizini_raskrsnica.csv",
        "overlay_intersection_znakovi_glavni_putevi.csv",
        "overlay_difference_ulice_van_signalizacije.csv",
    ]

    selected = st.selectbox("Izaberi rezultat analize", files)
    path = f"results/analysis/{selected}"

    try:
        df = pd.read_csv(path)
        st.dataframe(df, use_container_width=True)
    except FileNotFoundError:
        st.error("Fajl ne postoji. Prvo pokreni spatial_analysis.py i overlay_analysis.py.")


def ml_page():
    st.title("ML detekcija saobraćajnih znakova")

    st.markdown("""
    Ova stranica omogućava učitavanje fotografije, pokretanje YOLO detekcije,
    konvertovanje detekcije u tačkastu geometriju i upis rezultata u PostGIS bazu.
    Detektovani objekti se zatim mogu prikazati kao poseban sloj na mapi.
    """)

    uploaded_file = st.file_uploader(
        "Učitaj fotografiju ili kadar iz video snimka",
        type=["jpg", "jpeg", "png"]
    )

    lon = st.number_input("Longitude lokacije snimanja", value=19.8335, format="%.6f")
    lat = st.number_input("Latitude lokacije snimanja", value=45.2671, format="%.6f")
    min_conf = st.slider("Minimalni confidence", 0.0, 1.0, 0.25, 0.05)

    if uploaded_file is not None:
        images_dir = Path("data/images")
        images_dir.mkdir(parents=True, exist_ok=True)

        image_path = images_dir / uploaded_file.name

        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.image(str(image_path), caption="Ulazna slika", use_container_width=True)

        if st.button("Pokreni detekciju"):
            detections = detect_image(image_path, lon, lat, min_confidence=min_conf)

            if len(detections) == 0:
                st.warning("Model nije pronašao objekte na slici.")
            else:
                st.success("Detekcija je završena i upisana u PostGIS bazu.")
                st.dataframe(pd.DataFrame(detections), use_container_width=True)

                result_path = detections[0]["rezultat"]
                st.image(result_path, caption="Rezultat detekcije", use_container_width=True)

    st.divider()

    st.subheader("Pregled ML detekcija")

    ml_df = read_dataframe("""
        SELECT id, klasa, confidence, naziv_slike, datum, model, opis
        FROM ml_detekcije
        ORDER BY id DESC
        LIMIT 100;
    """)

    st.dataframe(ml_df, use_container_width=True)

    st.divider()

    st.subheader("Izmena atributa ML detekcije")

    det_id = st.number_input("ID ML detekcije", min_value=1, step=1)
    nova_klasa = st.text_input("Nova klasa")
    novi_conf = st.number_input("Novi confidence", min_value=0.0, max_value=1.0, value=0.90)
    novi_opis = st.text_area("Novi opis", "Izmenjeni atributi detekcije")

    if st.button("Izmeni ML detekciju"):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE ml_detekcije
            SET klasa = %s,
                confidence = %s,
                opis = %s
            WHERE id = %s;
        """, (nova_klasa, novi_conf, novi_opis, det_id))

        conn.commit()
        cur.close()
        conn.close()

        st.success("Atributi ML detekcije su izmenjeni.")


def main():
    st.sidebar.title("Navigacija")

    page = st.sidebar.radio(
        "Izaberi stranicu",
        [
            "Dashboard",
            "Mapa",
            "Tabele",
            "CRUD",
            "SQL upiti",
            "Prostorne analize",
            "ML detekcija",
        ]
    )

    if page == "Dashboard":
        dashboard_page()
    elif page == "Mapa":
        map_page()
    elif page == "Tabele":
        tables_page()
    elif page == "CRUD":
        crud_page()
    elif page == "SQL upiti":
        sql_queries_page()
    elif page == "Prostorne analize":
        analysis_page()
    elif page == "ML detekcija":
        ml_page()


if __name__ == "__main__":
    main()