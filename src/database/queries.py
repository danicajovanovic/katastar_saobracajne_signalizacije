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


def query_1_streets_over_speed_limit_with_sign_count():
    return run_query(
        "1. JOIN: ulice sa ogranicenjem brzine > 50 km/h i broj znakova na njima",
        """
        SELECT
            u.id,
            u.naziv,
            u.tip_ulice,
            u.ogranicenje_brzine,
            COUNT(z.id) AS broj_znakova
        FROM ulice u
        LEFT JOIN saobracajni_znakovi z ON z.ulica_id = u.id
        WHERE u.ogranicenje_brzine > 50
        GROUP BY u.id, u.naziv, u.tip_ulice, u.ogranicenje_brzine
        ORDER BY u.ogranicenje_brzine DESC, broj_znakova DESC;
        """
    )


def query_2_damaged_signs_with_street():
    return run_query(
        "2. JOIN: znakovi koji nisu u dobrom stanju, sa ulicom na kojoj se nalaze",
        """
        SELECT
            z.id,
            z.tip_znaka,
            z.stanje,
            u.naziv AS ulica,
            u.tip_ulice
        FROM saobracajni_znakovi z
        JOIN ulice u ON z.ulica_id = u.id
        WHERE z.stanje <> 'dobro'
        ORDER BY u.naziv;
        """
    )


def query_3_active_lights_with_intersection():
    return run_query(
        "3. JOIN: aktivni semafori sa nazivom raskrsnice",
        """
        SELECT
            s.id,
            s.status,
            s.tip AS tip_semafora,
            r.naziv AS raskrsnica,
            r.prometnost
        FROM semafori s
        JOIN raskrsnice r ON s.raskrsnica_id = r.id
        WHERE s.status = 'aktivan'
        ORDER BY r.naziv;
        """
    )


def query_4_traffic_lights_with_intersections():
    return run_query(
        "4. JOIN: semafori na kontrolisanim raskrsnicama",
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
        WHERE r.tip = 'kontrolisana raskrsnica'
        ORDER BY s.id
        LIMIT 20;
        """
    )


def query_5_ml_with_signs():
    return run_query(
        "5. JOIN: ML detekcije sa povezanim znakovima (confidence > 0.5)",
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
        WHERE m.confidence > 0.5
        ORDER BY m.confidence DESC;
        """
    )


def query_6_longest_roads_with_sign_count():
    return run_query(
        "6. JOIN: najduze ulice i broj znakova na njima",
        """
        SELECT
            u.id,
            u.naziv,
            u.tip_ulice,
            ROUND(u.duzina_km::numeric, 3) AS duzina_km,
            COUNT(z.id) AS broj_znakova
        FROM ulice u
        LEFT JOIN saobracajni_znakovi z ON z.ulica_id = u.id
        WHERE u.duzina_km > 0.3
        GROUP BY u.id, u.naziv, u.tip_ulice, u.duzina_km
        ORDER BY u.duzina_km DESC
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
        WHERE tip_ulice IS NOT NULL
        GROUP BY tip_ulice
        ORDER BY prosecna_duzina_km DESC;
        """
    )


def query_8_streets_without_signs():
    return run_query(
        "8. JOIN (anti-join): glavne ulice bez ijednog evidentiranog znaka",
        """
        SELECT
            u.id,
            u.naziv,
            u.tip_ulice,
            ROUND(u.duzina_km::numeric, 3) AS duzina_km
        FROM ulice u
        LEFT JOIN saobracajni_znakovi z ON z.ulica_id = u.id
        WHERE z.id IS NULL
            AND u.tip_ulice IN ('primary', 'secondary', 'tertiary', 'trunk', 'motorway')
        ORDER BY u.duzina_km DESC
        LIMIT 20;
        """
    )


def query_9_signs_by_condition():
    return run_query(
        "9. Broj znakova po stanju",
        """
        SELECT stanje, COUNT(*) AS broj_znakova
        FROM saobracajni_znakovi
        WHERE stanje IS NOT NULL
        GROUP BY stanje
        ORDER BY broj_znakova DESC;
        """
    )


def query_10_high_confidence_ml_with_link_status():
    return run_query(
        "10. JOIN (LEFT): ML detekcije visoke pouzdanosti i status povezanosti sa katastrom",
        """
        SELECT
            m.id,
            m.klasa,
            m.confidence,
            m.naziv_slike,
            m.datum,
            z.tip_znaka AS povezan_znak,
            CASE WHEN m.znak_id IS NULL THEN 'nepovezano' ELSE 'povezano' END AS status_povezanosti
        FROM ml_detekcije m
        LEFT JOIN saobracajni_znakovi z ON m.znak_id = z.id
        WHERE m.confidence > 0.85
        ORDER BY m.confidence DESC;
        """
    )


def run_all_queries():
    query_1_streets_over_speed_limit_with_sign_count()
    query_2_damaged_signs_with_street()
    query_3_active_lights_with_intersection()
    query_4_traffic_lights_with_intersections()
    query_5_ml_with_signs()
    query_6_longest_roads_with_sign_count()
    query_7_average_road_length()
    query_8_streets_without_signs()
    query_9_signs_by_condition()
    query_10_high_confidence_ml_with_link_status()


if __name__ == "__main__":
    run_all_queries()
