# Katastar saobraćajne signalizacije

GIS platforma za evidenciju i analizu saobraćajne infrastrukture Novog Sada — ulice, raskrsnice, saobraćajni znakovi i semafori — sa prostornim analizama nad PostgreSQL/PostGIS bazom i automatskom detekcijom saobraćajnih znakova pomoću mašinskog učenja.

## Pregled

Aplikacija objedinjuje tri celine oko jedne baze podataka:

- **Relaciona/prostorna baza** (PostgreSQL + PostGIS) sa katastrom ulica, raskrsnica, znakova, semafora i ML detekcija, upravljanom isključivo kroz Python (psycopg2, pandas).
- **Geoprostorna obrada** (GeoPandas) koja OSM/Geofabrik podatke za Srbiju filtrira na područje Novog Sada, izvodi overlay analize (clip, buffer, intersection, union, difference) i prikazuje slojeve na interaktivnoj mapi.
- **Detekcija znakova mašinskim učenjem** (YOLOv8) koja na osnovu fotografija generiše geolociranu evidenciju, upisuje je u bazu i povezuje sa postojećim katastrom.

Sve tri celine su spojene u jednu Streamlit aplikaciju: dashboard, interaktivna mapa, pregled tabela, CRUD upravljanje, SQL analitika, prostorne analize i AI detekcija.

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
├── database/            psycopg2 konekcija, kreiranje tabela, CRUD, SQL upiti, unos OSM/ručnih podataka
├── geo/                 učitavanje i obrada shapefile podataka, overlay i prostorne analize, statička mapa
├── ml/                  YOLOv8 detekcija saobraćajnih znakova
└── app/                 Streamlit aplikacija
scripts/                 trening YOLOv8 modela na Google Colab-u
data/
├── shp/                 Geofabrik shapefile podaci za Srbiju (preuzima se posebno, nije u git-u)
└── processed/           GeoJSON slojevi filtrirani na područje Novog Sada
results/
├── analysis/            rezultati prostornih i SQL analiza (CSV)
├── maps/                generisane HTML mape
└── ml/detections/       fotografije sa iscrtanim ML detekcijama
models/                  istrenirani YOLOv8 model (best.pt)
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

   Popuni `DB_USER`, `DB_PASSWORD` i ostale vrednosti u `.env`. Fajl je u `.gitignore`-u i nikad se ne komituje — `src/database/connection.py` kredencijale čita isključivo odatle, bez ijedne hardkodovane vrednosti u kodu.

4. **Preuzmi geoprostorne podatke**

   Skini shapefile paket za Srbiju sa [Geofabrik-a](https://download.geofabrik.de/europe/serbia.html) i raspakuj ga u `data/shp/`.

5. **Postavi ML model**

   Kopiraj istrenirani YOLOv8 model na `models/best.pt`. Skripta za trening (Google Colab, DFG Traffic Sign Dataset, 200 klasa) nalazi se u `scripts/train_dfg_colab.py`.

## Pokretanje

Redosled ide od prazne baze do potpuno funkcionalne aplikacije:

| Korak | Komanda | Opis |
|---|---|---|
| 1 | `python -m src.database.create_tables` | Kreira 5 tabela: `ulice`, `raskrsnice`, `saobracajni_znakovi`, `semafori`, `ml_detekcije` |
| 2 | `python -m src.database.seed_manual_data` | Ručni demo unos — najmanje 5 redova po tabeli |
| 3 | `python -m src.geo.preprocessing` | Filtrira Geofabrik SHP podatke na Novi Sad, upisuje `data/processed/*.geojson` |
| 4 | `python -m src.database.insert_osm_to_tables` | Masovno ubacuje OSM geometrije u tabele i povezuje znakove sa najbližom ulicom (FK) |
| 5 | `python -m src.geo.overlay_analysis` | Pokreće 5 overlay tehnika: clip, buffer, intersection, union, difference |
| 6 | `python -m src.geo.spatial_analysis` | Prostorni upiti (nearest, within, intersects) i heatmap gustine signalizacije |
| 7 | `python -m src.geo.map_view` | Generiše statičku HTML mapu sa svim slojevima |
| 8 | `python -m src.database.queries` | Ispisuje 10 SQL upita (JOIN/WHERE primeri) u konzoli |
| 9 | `python main.py` | Pokreće Streamlit aplikaciju |

`main.py` pokreće isključivo Streamlit interfejs — koraci 1–8 pripremaju bazu i rezultate analiza koje aplikacija zatim prikazuje.

## Pokrivenost zahteva projekta

### Deo 1 — Python SQL

| Zahtev | Implementacija |
|---|---|
| Baza povezana sa temom, PostgreSQL/PostGIS | `katastar_saobracajne_signalizacije`, konekcija preko psycopg2 (`src/database/connection.py`) |
| 5+ tabela, 5–10 kolona, PK i FK | `ulice`, `raskrsnice`, `saobracajni_znakovi`, `semafori`, `ml_detekcije` (`src/database/create_tables.py`); FK: `saobracajni_znakovi.ulica_id → ulice`, `semafori.raskrsnica_id → raskrsnice`, `ml_detekcije.znak_id → saobracajni_znakovi` |
| Ručni INSERT, 5+ redova po tabeli | `src/database/seed_manual_data.py` |
| Pandas DataFrame iz tabela | `src/database/crud.py::read_table()` |
| CRUD operacije | `src/database/crud.py`, izloženo kroz Streamlit CRUD stranicu |
| 5–10 upita sa JOIN po FK i WHERE filterom | `src/database/queries.py` — 8 od 10 upita koristi JOIN |

### Deo 2 — Python GEO

| Zahtev | Implementacija |
|---|---|
| SHP podaci za Srbiju (Geofabrik), više slojeva | `data/shp/`, filtrirano na Novi Sad u `src/geo/preprocessing.py` |
| Učitavanje kroz GeoPandas | `src/geo/load_data.py` |
| Spajanje shapefile podataka sa tabelama iz Dela 1 | `src/database/insert_osm_to_tables.py` |
| Uključivanje/isključivanje slojeva, promena stila | Streamlit stranica "Interaktivna mapa" (`src/app/streamlit_app.py::map_page`) |
| 5+ overlay tehnika | `src/geo/overlay_analysis.py` — clip, buffer, intersection, union, difference |
| Prostorni upiti (within, intersects, nearest) | `src/geo/spatial_analysis.py` |
| Raster podloga ispod vektorskih slojeva | OpenStreetMap/CartoDB tile slojevi u Folium mapama |

### Deo 3 — Python ML

| Zahtev | Implementacija |
|---|---|
| Detekcija objekata mašinskim učenjem | YOLOv8 (`src/ml/detector.py`), model treniran na DFG Traffic Sign Dataset-u (200 klasa) |
| Konverzija u vektorski format, upis u PostGIS i DataFrame, prikaz na mapi | `insert_detection_to_database()` upisuje geometriju u `ml_detekcije.geom`, prikazano kao poseban sloj na mapi i u tabelama |
| Atributi i izmena kroz aplikaciju | Tab "Korekcija zapisa" na ML stranici |
| Prostorne analize nad ML rezultatima | `src/geo/spatial_analysis.py::analysis_5_ml_detections_vs_katastar` — poredi detekcije sa postojećim katastrom i izdvaja kandidate za nove znakove |

## Poznata ograničenja

- `models/best.pt` je trenutno checkpoint niskog poverenja — finalni istrenirani model se dodaje naknadno.
- Geolokacija ML detekcije unosi se ručno po fotografiji (fotografije nemaju GPS EXIF metapodatke), pa svi znakovi detektovani na istoj slici dobijaju istu tačku.
