import re

import geopandas as gpd
import pandas as pd

from src.database.connection import get_connection


ROADS_FILE = "data/processed/novi_sad_roads.geojson"
TRAFFIC_FILE = "data/processed/novi_sad_traffic.geojson"


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def parse_speed(value):
    if pd.isna(value) or value is None:
        return None

    match = re.search(r"\d+", str(value))
    if match:
        return int(match.group())

    return None


def prepare_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("ALTER TABLE ulice ADD COLUMN IF NOT EXISTS osm_id BIGINT UNIQUE;")
    cur.execute("ALTER TABLE raskrsnice ADD COLUMN IF NOT EXISTS osm_id BIGINT UNIQUE;")
    cur.execute("ALTER TABLE saobracajni_znakovi ADD COLUMN IF NOT EXISTS osm_id BIGINT UNIQUE;")
    cur.execute("ALTER TABLE semafori ADD COLUMN IF NOT EXISTS osm_id BIGINT UNIQUE;")

    cur.execute("""
        ALTER TABLE ulice
        ALTER COLUMN geom TYPE geometry(MultiLineString, 4326)
        USING ST_Multi(geom);
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_ulice_geom ON ulice USING GIST (geom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_raskrsnice_geom ON raskrsnice USING GIST (geom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_znakovi_geom ON saobracajni_znakovi USING GIST (geom);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_semafori_geom ON semafori USING GIST (geom);")

    conn.commit()
    cur.close()
    conn.close()

    print("Baza je pripremljena.")


def clear_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        TRUNCATE TABLE
            ml_detekcije,
            semafori,
            saobracajni_znakovi,
            raskrsnice,
            ulice
        RESTART IDENTITY CASCADE;
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("Stari podaci su obrisani.")


def insert_roads():
    roads = gpd.read_file(ROADS_FILE)

    roads_metric = roads.to_crs(epsg=32634)
    roads["duzina_km"] = roads_metric.geometry.length / 1000

    conn = get_connection()
    cur = conn.cursor()

    for _, row in roads.iterrows():
        naziv = clean_value(row["name"])
        if naziv is None:
            naziv = "Nepoznata ulica"

        cur.execute("""
            INSERT INTO ulice
            (osm_id, naziv, tip_ulice, ogranicenje_brzine, broj_traka, duzina_km, geom)
            VALUES
            (%s, %s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromText(%s), 4326)))
            ON CONFLICT (osm_id) DO NOTHING;
        """, (
            int(row["osm_id"]),
            naziv,
            clean_value(row["fclass"]),
            parse_speed(row["maxspeed"]),
            None,
            float(row["duzina_km"]),
            row.geometry.wkt
        ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Ubacene ulice: {len(roads)}")


def insert_traffic_objects():
    traffic = gpd.read_file(TRAFFIC_FILE)

    signs = traffic[
        traffic["fclass"].isin([
            "stop",
            "pedestrian_crossing",
            "speed_camera",
            "railway_crossing",
            "motorway_junction"
        ])
    ]

    traffic_lights = traffic[traffic["fclass"] == "traffic_signals"]

    conn = get_connection()
    cur = conn.cursor()

    for _, row in signs.iterrows():
        tip = row["fclass"]

        opis = {
            "stop": "Znak obaveznog zaustavljanja",
            "pedestrian_crossing": "Obelezen pesacki prelaz",
            "speed_camera": "Kamera za kontrolu brzine",
            "railway_crossing": "Pruzni prelaz",
            "motorway_junction": "Saobracajno cvoriste"
        }.get(tip, "Saobracajni objekat")

        cur.execute("""
            INSERT INTO saobracajni_znakovi
            (osm_id, tip_znaka, opis, stanje, datum_postavljanja, proizvodjac, ulica_id, geom)
            VALUES
            (%s, %s, %s, %s, CURRENT_DATE, %s, NULL, ST_SetSRID(ST_GeomFromText(%s), 4326))
            ON CONFLICT (osm_id) DO NOTHING;
        """, (
            int(row["osm_id"]),
            tip,
            opis,
            "dobro",
            "OpenStreetMap",
            row.geometry.wkt
        ))

    for _, row in traffic_lights.iterrows():
        cur.execute("""
            INSERT INTO raskrsnice
            (osm_id, naziv, tip, broj_prilaza, ima_semafor, prometnost, geom)
            VALUES
            (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
            ON CONFLICT (osm_id) DO NOTHING
            RETURNING id;
        """, (
            int(row["osm_id"]),
            "Raskrsnica sa semaforom",
            "kontrolisana raskrsnica",
            None,
            True,
            "nepoznata",
            row.geometry.wkt
        ))

        result = cur.fetchone()

        if result is not None:
            raskrsnica_id = result[0]
        else:
            cur.execute(
                "SELECT id FROM raskrsnice WHERE osm_id = %s;",
                (int(row["osm_id"]),)
            )
            raskrsnica_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO semafori
            (osm_id, status, tip, datum_servisa, broj_signalnih_glava, raskrsnica_id, geom)
            VALUES
            (%s, %s, %s, CURRENT_DATE, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))
            ON CONFLICT (osm_id) DO NOTHING;
        """, (
            int(row["osm_id"]),
            "aktivan",
            "semafor",
            None,
            raskrsnica_id,
            row.geometry.wkt
        ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Ubaceni saobracajni znakovi: {len(signs)}")
    print(f"Ubaceni semafori: {len(traffic_lights)}")


def link_signs_to_nearest_street():
    """
    Popunjava FK saobracajni_znakovi.ulica_id najblizom ulicom (KNN preko
    GiST indeksa), za sve znakove kod kojih ta veza jos nije postavljena.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE saobracajni_znakovi z
        SET ulica_id = (
            SELECT u.id
            FROM ulice u
            ORDER BY u.geom <-> z.geom
            LIMIT 1
        )
        WHERE z.ulica_id IS NULL;
    """)

    linked = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    print(f"Povezano znakova sa najblizom ulicom: {linked}")


def insert_demo_ml_detections():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, tip_znaka, geom
        FROM saobracajni_znakovi
        LIMIT 5;
    """)

    signs = cur.fetchall()

    for sign_id, tip_znaka, geom in signs:
        cur.execute("""
            INSERT INTO ml_detekcije
            (klasa, confidence, naziv_slike, datum, znak_id, geom)
            VALUES
            (%s, %s, %s, CURRENT_DATE, %s, %s);
        """, (
            tip_znaka,
            0.90,
            f"demo_detekcija_{sign_id}.jpg",
            sign_id,
            geom
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("Ubaceno 5 demo ML detekcija.")


def print_counts():
    conn = get_connection()
    cur = conn.cursor()

    tables = [
        "ulice",
        "raskrsnice",
        "saobracajni_znakovi",
        "semafori",
        "ml_detekcije"
    ]

    print()
    print("Stanje tabela:")

    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        count = cur.fetchone()[0]
        print(f"{table}: {count}")

    cur.close()
    conn.close()


def main():
    print("Pocinje unos OSM podataka u postojece tabele...")

    prepare_database()
    clear_tables()
    insert_roads()
    insert_traffic_objects()
    link_signs_to_nearest_street()
    insert_demo_ml_detections()
    print_counts()

    print()
    print("Unos podataka je zavrsen.")


if __name__ == "__main__":
    main()