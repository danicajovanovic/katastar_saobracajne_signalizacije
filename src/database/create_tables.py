from src.database.connection import get_connection


def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ulice (
        id SERIAL PRIMARY KEY,
        naziv VARCHAR(100) NOT NULL,
        tip_ulice VARCHAR(50),
        ogranicenje_brzine INTEGER,
        broj_traka INTEGER,
        duzina_km FLOAT,
        geom geometry(LineString, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raskrsnice (
        id SERIAL PRIMARY KEY,
        naziv VARCHAR(100) NOT NULL,
        tip VARCHAR(50),
        broj_prilaza INTEGER,
        ima_semafor BOOLEAN,
        prometnost VARCHAR(50),
        geom geometry(Point, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS saobracajni_znakovi (
        id SERIAL PRIMARY KEY,
        tip_znaka VARCHAR(100) NOT NULL,
        opis TEXT,
        stanje VARCHAR(50),
        datum_postavljanja DATE,
        proizvodjac VARCHAR(100),
        ulica_id INTEGER REFERENCES ulice(id) ON DELETE CASCADE,
        geom geometry(Point, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS semafori (
        id SERIAL PRIMARY KEY,
        status VARCHAR(50),
        tip VARCHAR(50),
        datum_servisa DATE,
        broj_signalnih_glava INTEGER,
        raskrsnica_id INTEGER REFERENCES raskrsnice(id) ON DELETE CASCADE,
        geom geometry(Point, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ml_detekcije (
        id SERIAL PRIMARY KEY,
        klasa VARCHAR(100),
        confidence FLOAT,
        naziv_slike VARCHAR(200),
        datum DATE,
        znak_id INTEGER REFERENCES saobracajni_znakovi(id) ON DELETE SET NULL,
        geom geometry(Point, 4326)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Tabele su uspesno kreirane.")


if __name__ == "__main__":
    create_tables()