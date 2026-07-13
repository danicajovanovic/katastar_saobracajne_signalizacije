"""
Rucno uneti demo podaci (INSERT), najmanje 5 redova po tabeli.

Za razliku od insert_osm_to_tables.py (koji masovno ucitava OSM podatke),
ovaj skript sluzi kao direktna demonstracija rucnog unosa preko INSERT
naredbi, sa doslovno ispisanim vrednostima za svaku tabelu.
"""

from src.database.connection import get_connection


def insert_ulice(cur):
    ulice = [
        ("Bulevar Mihajla Pupina", "primary", 60, 4, 3.2),
        ("Bulevar Oslobođenja", "primary", 60, 4, 4.5),
        ("Futoška ulica", "secondary", 50, 2, 2.8),
        ("Temerinska ulica", "secondary", 50, 2, 3.1),
        ("Ulica Laze Telečkog", "residential", 40, 2, 1.4),
    ]

    ids = []
    for naziv, tip_ulice, ogranicenje, trake, duzina in ulice:
        cur.execute("""
            INSERT INTO ulice (naziv, tip_ulice, ogranicenje_brzine, broj_traka, duzina_km, geom)
            VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(
                'LINESTRING(19.83 45.25, 19.84 45.26)'
            ), 4326))
            RETURNING id;
        """, (naziv, tip_ulice, ogranicenje, trake, duzina))
        ids.append(cur.fetchone()[0])

    return ids


def insert_raskrsnice(cur):
    raskrsnice = [
        ("Raskrsnica Bulevar / Futoška", "kontrolisana raskrsnica", 4, True, "velika", 19.8321, 45.2512),
        ("Raskrsnica Bulevar / Temerinska", "kontrolisana raskrsnica", 4, True, "velika", 19.8452, 45.2601),
        ("Raskrsnica Laze Telečkog / Futoška", "nekontrolisana raskrsnica", 3, False, "srednja", 19.8290, 45.2489),
        ("Kružni tok Liman", "kruzni tok", 5, False, "velika", 19.8267, 45.2404),
        ("Raskrsnica Temerinska / Kisačka", "kontrolisana raskrsnica", 4, True, "srednja", 19.8478, 45.2622),
    ]

    ids = []
    for naziv, tip, broj_prilaza, ima_semafor, prometnost, lon, lat in raskrsnice:
        cur.execute("""
            INSERT INTO raskrsnice (naziv, tip, broj_prilaza, ima_semafor, prometnost, geom)
            VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            RETURNING id;
        """, (naziv, tip, broj_prilaza, ima_semafor, prometnost, lon, lat))
        ids.append(cur.fetchone()[0])

    return ids


def insert_saobracajni_znakovi(cur, ulica_ids):
    znakovi = [
        ("stop", "Znak obaveznog zaustavljanja", "dobro", "Signal d.o.o.", 19.8321, 45.2512),
        ("ogranicenje_brzine", "Ograničenje brzine 50 km/h", "dobro", "Saobraćajni znakovi Novi Sad", 19.8452, 45.2601),
        ("pesacki_prelaz", "Obeležen pešački prelaz", "ostecen", "Signal d.o.o.", 19.8290, 45.2489),
        ("zabrana_parkiranja", "Zabrana parkiranja", "potrebno odrzavanje", "Grad Novi Sad", 19.8267, 45.2404),
        ("obavezan_smer", "Obavezan smer desno", "dobro", "Signal d.o.o.", 19.8478, 45.2622),
    ]

    ids = []
    for (tip_znaka, opis, stanje, proizvodjac, lon, lat), ulica_id in zip(znakovi, ulica_ids):
        cur.execute("""
            INSERT INTO saobracajni_znakovi
            (tip_znaka, opis, stanje, datum_postavljanja, proizvodjac, ulica_id, geom)
            VALUES (%s, %s, %s, CURRENT_DATE, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            RETURNING id;
        """, (tip_znaka, opis, stanje, proizvodjac, ulica_id, lon, lat))
        ids.append(cur.fetchone()[0])

    return ids


def insert_semafori(cur, raskrsnica_ids):
    semafori = [
        ("aktivan", "semafor", 3, 19.8321, 45.2512),
        ("aktivan", "semafor", 4, 19.8452, 45.2601),
        ("neispravan", "semafor sa zvučnom signalizacijom", 2, 19.8290, 45.2489),
        ("aktivan", "semafor", 4, 19.8267, 45.2404),
        ("u_odrzavanju", "semafor", 3, 19.8478, 45.2622),
    ]

    ids = []
    for (status, tip, broj_glava, lon, lat), raskrsnica_id in zip(semafori, raskrsnica_ids):
        cur.execute("""
            INSERT INTO semafori (status, tip, datum_servisa, broj_signalnih_glava, raskrsnica_id, geom)
            VALUES (%s, %s, CURRENT_DATE, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            RETURNING id;
        """, (status, tip, broj_glava, raskrsnica_id, lon, lat))
        ids.append(cur.fetchone()[0])

    return ids


def insert_ml_detekcije(cur, znak_ids):
    detekcije = [
        ("stop", 0.94, "test_1.jpg"),
        ("ogranicenje_brzine", 0.88, "test_2.jpg"),
        ("pesacki_prelaz", 0.76, "test_3.jpg"),
        ("zabrana_parkiranja", 0.61, "test_4.jpg"),
        ("obavezan_smer", 0.83, "test_5.jpg"),
    ]

    for (klasa, confidence, naziv_slike), znak_id in zip(detekcije, znak_ids):
        cur.execute("""
            INSERT INTO ml_detekcije (klasa, confidence, naziv_slike, datum, znak_id, geom)
            SELECT %s, %s, %s, CURRENT_DATE, %s, geom
            FROM saobracajni_znakovi
            WHERE id = %s;
        """, (klasa, confidence, naziv_slike, znak_id, znak_id))


def seed_manual_data():
    conn = get_connection()
    cur = conn.cursor()

    ulica_ids = insert_ulice(cur)
    raskrsnica_ids = insert_raskrsnice(cur)
    znak_ids = insert_saobracajni_znakovi(cur, ulica_ids)
    insert_semafori(cur, raskrsnica_ids)
    insert_ml_detekcije(cur, znak_ids)

    conn.commit()
    cur.close()
    conn.close()

    print("Rucni unos zavrsen: 5 redova u svakoj od 5 tabela.")


if __name__ == "__main__":
    seed_manual_data()
