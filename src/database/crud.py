import pandas as pd

from src.database.connection import get_connection


def read_table(table_name):
    conn = get_connection()

    query = f"""
        SELECT *
        FROM {table_name}
        ORDER BY id
        LIMIT 100;
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def create_traffic_sign(tip_znaka, opis, stanje, proizvodjac, lon, lat):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO saobracajni_znakovi
        (tip_znaka, opis, stanje, datum_postavljanja, proizvodjac, ulica_id, geom)
        VALUES
        (
            %s, %s, %s, CURRENT_DATE, %s,
            (
                SELECT u.id
                FROM ulice u
                ORDER BY u.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1
            ),
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        );
    """, (
        tip_znaka,
        opis,
        stanje,
        proizvodjac,
        lon,
        lat,
        lon,
        lat
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("Saobracajni znak je dodat.")


def update_traffic_sign(sign_id, novo_stanje):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE saobracajni_znakovi
        SET stanje = %s
        WHERE id = %s;
    """, (
        novo_stanje,
        sign_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("Saobracajni znak je azuriran.")


def delete_traffic_sign(sign_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM saobracajni_znakovi
        WHERE id = %s;
    """, (sign_id,))

    conn.commit()
    cur.close()
    conn.close()

    print("Saobracajni znak je obrisan.")


def create_traffic_light(status, tip, broj_signalnih_glava, lon, lat):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO raskrsnice
        (naziv, tip, broj_prilaza, ima_semafor, prometnost, geom)
        VALUES
        (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        RETURNING id;
    """, (
        "Rucno dodata raskrsnica",
        "kontrolisana raskrsnica",
        None,
        True,
        "nepoznata",
        lon,
        lat
    ))

    raskrsnica_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO semafori
        (status, tip, datum_servisa, broj_signalnih_glava, raskrsnica_id, geom)
        VALUES
        (%s, %s, CURRENT_DATE, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
    """, (
        status,
        tip,
        broj_signalnih_glava,
        raskrsnica_id,
        lon,
        lat
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("Semafor je dodat.")


def update_traffic_light(semafor_id, novi_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE semafori
        SET status = %s
        WHERE id = %s;
    """, (
        novi_status,
        semafor_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    print("Semafor je azuriran.")


def delete_traffic_light(semafor_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM semafori
        WHERE id = %s;
    """, (semafor_id,))

    conn.commit()
    cur.close()
    conn.close()

    print("Semafor je obrisan.")


def demo_crud():
    print("READ - prikaz znakova")
    print(read_table("saobracajni_znakovi").head())

    print("\nCREATE - dodavanje test znaka")
    create_traffic_sign(
        tip_znaka="test_znak",
        opis="Rucno dodat test znak kroz CRUD",
        stanje="dobro",
        proizvodjac="Test proizvodjac",
        lon=19.8335,
        lat=45.2671
    )

    print("\nUPDATE - izmena test znaka")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id
        FROM saobracajni_znakovi
        WHERE tip_znaka = 'test_znak'
        ORDER BY id DESC
        LIMIT 1;
    """)
    test_id = cur.fetchone()[0]
    cur.close()
    conn.close()

    update_traffic_sign(test_id, "ostecen")

    print("\nDELETE - brisanje test znaka")
    delete_traffic_sign(test_id)

    print("\nCRUD demonstracija zavrsena.")


if __name__ == "__main__":
    demo_crud()