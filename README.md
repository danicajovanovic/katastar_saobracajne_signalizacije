# Katastar saobraćajne signalizacije

GIS platforma za evidenciju i analizu saobraćajne infrastrukture Novog Sada — ulice, raskrsnice, saobraćajni znakovi i semafori — sa prostornim analizama nad PostgreSQL/PostGIS bazom i automatskom detekcijom saobraćajnih znakova pomoću mašinskog učenja.

## O projektu

Aplikacija objedinjuje tri celine oko jedne baze podataka:

- **Relaciona/prostorna baza** (PostgreSQL + PostGIS) sa katastrom ulica, raskrsnica, znakova, semafora i ML detekcija, upravljana isključivo kroz Python (psycopg2, pandas).
- **Geoprostorna obrada** (GeoPandas) koja OSM/Geofabrik podatke za Srbiju filtrira na područje Novog Sada, izvodi overlay analize (clip, buffer, intersection, union, difference) i prikazuje slojeve na interaktivnoj mapi.
- **Detekcija znakova mašinskim učenjem** (YOLOv8) koja na osnovu fotografija generiše geolociranu evidenciju, upisuje je u bazu i povezuje sa postojećim katastrom.

Sve tri celine su spojene u jednu Streamlit aplikaciju.

## Funkcionalnosti

- **Dashboard** — pregled broja ulica, znakova, semafora, raskrsnica i ML detekcija, grafikoni po stanju/kategoriji, status baze i modela.
- **Interaktivna mapa** — slojevi ulica, znakova, semafora i ML detekcija sa uključivanjem/isključivanjem po sloju, klasterovanjem markera, promenom stila mape (svetla/tamna/OpenStreetMap) i tooltip/popup informacijama.
- **Pregled tabela** — pretraga, filtriranje i izvoz (CSV) svih tabela iz baze.
- **CRUD upravljanje** — dodavanje, izmena i brisanje saobraćajnih znakova direktno kroz aplikaciju.
- **SQL analitika** — 10 unapred pripremljenih upita nad bazom (JOIN po stranim ključevima, WHERE filteri, agregacije), sa prikazom rezultata i izvozom.
- **Prostorne analize** — najbliža ulica za svaki znak, znakovi u blizini semafora, semafori u blizini raskrsnica, poređenje ML detekcija sa postojećim katastrom, heatmap gustine signalizacije, kao i overlay analize (clip, buffer, intersection, union, difference).
- **AI detekcija** — upload fotografije, detekcija znakova YOLOv8 modelom, automatsko upisivanje u bazu i povezivanje sa najbližim postojećim znakom, istorija detekcija i ručna korekcija atributa.

## Tehnologije

| Sloj | Tehnologije |
|---|---|
| Baza podataka | PostgreSQL, PostGIS |
| Pristup podacima | psycopg2, SQLAlchemy, pandas |
| Geoprostorna obrada | GeoPandas, Shapely, Folium |
| Mašinsko učenje | YOLOv8 (Ultralytics), OpenCV |
| Aplikacija | Streamlit, streamlit-folium |
| Upravljanje zavisnostima | uv |

## Struktura projekta

```
main.py                 pokreće Streamlit aplikaciju
src/
├── database/            psycopg2 konekcija, kreiranje tabela, CRUD, SQL upiti, unos podataka
├── geo/                 učitavanje i obrada shapefile podataka, overlay i prostorne analize, statička mapa
├── ml/                  YOLOv8 detekcija saobraćajnih znakova
└── app/                 Streamlit aplikacija
scripts/                 trening YOLOv8 modela na Google Colab-u
data/
├── shp/                 Geofabrik shapefile podaci za Srbiju
└── processed/           GeoJSON slojevi filtrirani na područje Novog Sada
results/
├── analysis/            rezultati prostornih i SQL analiza (CSV)
├── maps/                generisane HTML mape
└── ml/detections/       fotografije sa iscrtanim ML detekcijama
models/                  YOLOv8 model korišćen za detekciju (best.pt)
```

## Preduslovi

- Python 3.14+
- PostgreSQL sa instaliranom PostGIS ekstenzijom
- [uv](https://docs.astral.sh/uv/) za upravljanje zavisnostima

## Instalacija

1. **Instaliraj zavisnosti**

   ```
   uv sync
   ```

2. **Kreiraj bazu i uključi PostGIS**

   ```sql
   CREATE DATABASE katastar_saobracajne_signalizacije;
   \c katastar_saobracajne_signalizacije
   CREATE EXTENSION postgis;
   ```

3. **Podesi promenljive okruženja**

   ```
   cp .env.example .env
   ```

   Popuni `DB_USER`, `DB_PASSWORD` i ostale vrednosti u `.env`. Fajl je u `.gitignore`-u i nikad se ne komituje — `src/database/connection.py` kredencijale čita isključivo odatle.

4. **Preuzmi geoprostorne podatke**

   Skini shapefile paket za Srbiju sa [Geofabrik-a](https://download.geofabrik.de/europe/serbia.html) i raspakuj ga u `data/shp/`.

## Pokretanje

Redosled ide od prazne baze do potpuno funkcionalne aplikacije:

| Korak | Komanda | Opis |
|---|---|---|
| 1 | `python -m src.database.create_tables` | Kreira tabele: `ulice`, `raskrsnice`, `saobracajni_znakovi`, `semafori`, `ml_detekcije` |
| 2 | `python -m src.database.seed_manual_data` | Ubacuje ručno pripremljene demo podatke |
| 3 | `python -m src.geo.preprocessing` | Filtrira Geofabrik SHP podatke na Novi Sad, upisuje `data/processed/*.geojson` |
| 4 | `python -m src.database.insert_osm_to_tables` | Ubacuje OSM geometrije u tabele i povezuje znakove sa najbližom ulicom |
| 5 | `python -m src.geo.overlay_analysis` | Pokreće overlay analize: clip, buffer, intersection, union, difference |
| 6 | `python -m src.geo.spatial_analysis` | Prostorni upiti (nearest, within, intersects) i heatmap gustine signalizacije |
| 7 | `python -m src.geo.map_view` | Generiše statičku HTML mapu sa svim slojevima |
| 8 | `python -m src.database.queries` | Ispisuje pripremljene SQL upite u konzoli |
| 9 | `python main.py` | Pokreće Streamlit aplikaciju |

`main.py` pokreće isključivo Streamlit interfejs — koraci 1–8 pripremaju bazu i rezultate analiza koje aplikacija zatim prikazuje.

## Poznata ograničenja

- Geolokacija ML detekcije unosi se ručno po fotografiji (fotografije nemaju GPS EXIF metapodatke). Kada je na jednoj slici detektovano više znakova, aplikacija ih kozmetički razmešta po malom krugu oko unete tačke da se markeri na mapi ne bi preklapali — ovo ne predstavlja stvarnu geolokaciju svakog znaka, samo vizuelno razdvajanje.
