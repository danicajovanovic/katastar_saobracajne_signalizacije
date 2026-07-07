import pandas as pd

from src.database.connection import get_connection


def run_query(title, query):
    conn = get_connection()

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    df = pd.read_sql(query, conn)
    conn.close()

    print(df)
    return df


def query_1_speed_limit_over_50():
    return run_query(
        "1. Ulice sa ogranicenjem brzine vecim od 50 km/h",
        """
        SELECT id, naziv, tip_ulice, ogranicenje_brzine, duzina_km
        FROM ulice
        WHERE ogranicenje_brzine > 50
        ORDER BY ogranicenje_brzine DESC;
        """
    )


def query_2_signs_by_type():
    return run_query(
        "2. Broj saobracajnih znakova po tipu",
        """
        SELECT tip_znaka, COUNT(*) AS broj_znakova
        FROM saobracajni_znakovi
        GROUP BY tip_znaka
        ORDER BY broj_znakova DESC;
        """
    )


def query_3_traffic_lights_by_status():
    return run_query(
        "3. Broj semafora po statusu",
        """
        SELECT status, COUNT(*) AS broj_semafora
        FROM semafori
        GROUP BY status
        ORDER BY broj_semafora DESC;
        """
    )


def query_4_traffic_lights_with_intersections():
    return run_query(
        "4. JOIN: semafori sa pripadajucim raskrsnicama",
        """
        SELECT 
            s.id AS semafor_id,
            s.status,
            s.tip AS tip_semafora,
            r.naziv AS naziv_raskrsnice,
            r.tip AS tip_raskrsnice,
            r.ima_semafor
        FROM semafori s
        JOIN raskrsnice r ON s.raskrsnica_id = r.id
        ORDER BY s.id
        LIMIT 20;
        """
    )


def query_5_ml_with_signs():
    return run_query(
        "5. JOIN: ML detekcije sa povezanim znakovima",
        """
        SELECT 
            m.id AS detekcija_id,
            m.klasa,
            m.confidence,
            m.naziv_slike,
            z.tip_znaka,
            z.opis,
            z.stanje
        FROM ml_detekcije m
        JOIN saobracajni_znakovi z ON m.znak_id = z.id
        ORDER BY m.confidence DESC;
        """
    )


def query_6_longest_roads():
    return run_query(
        "6. Najduzih 10 ulica/puteva",
        """
        SELECT id, naziv, tip_ulice, ROUND(duzina_km::numeric, 3) AS duzina_km
        FROM ulice
        ORDER BY duzina_km DESC
        LIMIT 10;
        """
    )


def query_7_average_road_length():
    return run_query(
        "7. Prosecna duzina ulica po kategoriji",
        """
        SELECT 
            tip_ulice,
            COUNT(*) AS broj_ulica,
            ROUND(AVG(duzina_km)::numeric, 3) AS prosecna_duzina_km
        FROM ulice
        GROUP BY tip_ulice
        ORDER BY prosecna_duzina_km DESC;
        """
    )


def query_8_roads_by_category():
    return run_query(
        "8. Broj ulica po kategoriji",
        """
        SELECT tip_ulice, COUNT(*) AS broj_ulica
        FROM ulice
        GROUP BY tip_ulice
        ORDER BY broj_ulica DESC;
        """
    )


def query_9_signs_by_condition():
    return run_query(
        "9. Broj znakova po stanju",
        """
        SELECT stanje, COUNT(*) AS broj_znakova
        FROM saobracajni_znakovi
        GROUP BY stanje
        ORDER BY broj_znakova DESC;
        """
    )


def query_10_high_confidence_ml():
    return run_query(
        "10. ML detekcije sa confidence vecim od 0.85",
        """
        SELECT id, klasa, confidence, naziv_slike, datum
        FROM ml_detekcije
        WHERE confidence > 0.85
        ORDER BY confidence DESC;
        """
    )


def run_all_queries():
    query_1_speed_limit_over_50()
    query_2_signs_by_type()
    query_3_traffic_lights_by_status()
    query_4_traffic_lights_with_intersections()
    query_5_ml_with_signs()
    query_6_longest_roads()
    query_7_average_road_length()
    query_8_roads_by_category()
    query_9_signs_by_condition()
    query_10_high_confidence_ml()


if __name__ == "__main__":
    run_all_queries()