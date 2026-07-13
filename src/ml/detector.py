import math
from pathlib import Path
from datetime import date

import pandas as pd
from ultralytics import YOLO

from src.database.connection import get_connection


RESULTS_DIR = Path("results/ml/detections")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CUSTOM_MODEL_PATH = Path("models/best.pt")

def get_model():
    if not CUSTOM_MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model nije pronađen. Dodaj trenirani model na putanju: "
            "models/best.pt"
        )

    print("Koristi se model treniran od nule za saobracajne znakove.")
    return YOLO(str(CUSTOM_MODEL_PATH))


def prepare_ml_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS model VARCHAR(100);
    """)

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS bbox_x1 FLOAT;
    """)

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS bbox_y1 FLOAT;
    """)

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS bbox_x2 FLOAT;
    """)

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS bbox_y2 FLOAT;
    """)

    cur.execute("""
        ALTER TABLE ml_detekcije
        ADD COLUMN IF NOT EXISTS opis TEXT;
    """)

    conn.commit()
    cur.close()
    conn.close()


NEAREST_SIGN_MATCH_DISTANCE_M = 50


def find_nearest_sign(cur, lon, lat, max_distance_m=NEAREST_SIGN_MATCH_DISTANCE_M):
    """
    Trazi najblizi vec evidentirani znak iz katastra u okviru max_distance_m.
    Ako postoji, ML detekcija se vezuje za njega preko znak_id (FK).
    """
    cur.execute("""
        SELECT z.id, ST_DistanceSphere(z.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS udaljenost_m
        FROM saobracajni_znakovi z
        WHERE z.geom IS NOT NULL
        ORDER BY udaljenost_m
        LIMIT 1;
    """, (lon, lat))

    result = cur.fetchone()
    if result is not None and result[1] <= max_distance_m:
        return result[0]

    return None


def insert_detection_to_database(
    klasa,
    confidence,
    image_name,
    lon,
    lat,
    model_name,
    bbox
):
    conn = get_connection()
    cur = conn.cursor()

    x1, y1, x2, y2 = bbox
    znak_id = find_nearest_sign(cur, lon, lat)

    cur.execute("""
        INSERT INTO ml_detekcije
        (
            klasa,
            confidence,
            naziv_slike,
            datum,
            znak_id,
            geom,
            model,
            bbox_x1,
            bbox_y1,
            bbox_x2,
            bbox_y2,
            opis
        )
        VALUES
        (
            %s, %s, %s, %s, %s,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s, %s, %s, %s, %s
        );
    """, (
        klasa,
        float(confidence),
        image_name,
        date.today(),
        znak_id,
        lon,
        lat,
        model_name,
        float(x1),
        float(y1),
        float(x2),
        float(y2),
        "Automatski detektovan objekat pomocu YOLO modela"
    ))

    conn.commit()
    cur.close()
    conn.close()


JITTER_RADIUS_M = 4.0


def apply_jitter(lon, lat, index, total, radius_m=JITTER_RADIUS_M):
    """
    Kozmetički (ne stvarni geolokacioni) pomak: kad je na jednoj fotografiji
    detektovano vise znakova, rasporedjuje ih ravnomerno po malom krugu oko
    unete tacke da se markeri na mapi ne preklapaju tacka-na-tacku.
    """
    if total <= 1:
        return lon, lat

    angle = 2 * math.pi * index / total
    lat_offset = (radius_m * math.cos(angle)) / 111_320
    lon_offset = (radius_m * math.sin(angle)) / (111_320 * math.cos(math.radians(lat)))

    return lon + lon_offset, lat + lat_offset


def detect_image(image_path, lon, lat, min_confidence=0.25):
    prepare_ml_table()

    model = get_model()
    image_path = Path(image_path)
    image_name = image_path.name

    results = model(str(image_path), conf=min_confidence)

    detections = []

    for result in results:
        output_path = RESULTS_DIR / f"detected_{image_name}"
        result.save(filename=str(output_path))

        total_boxes = len(result.boxes)

        for index, box in enumerate(result.boxes):
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detection_lon, detection_lat = apply_jitter(lon, lat, index, total_boxes)

            insert_detection_to_database(
                klasa=class_name,
                confidence=confidence,
                image_name=image_name,
                lon=detection_lon,
                lat=detection_lat,
                model_name=str(CUSTOM_MODEL_PATH),
                bbox=(x1, y1, x2, y2)
            )

            detections.append({
                "klasa": class_name,
                "confidence": round(confidence, 3),
                "naziv_slike": image_name,
                "lon": round(detection_lon, 6),
                "lat": round(detection_lat, 6),
                "bbox_x1": round(x1, 2),
                "bbox_y1": round(y1, 2),
                "bbox_x2": round(x2, 2),
                "bbox_y2": round(y2, 2),
                "rezultat": str(output_path)
            })

    return detections


def detections_to_dataframe(detections):
    return pd.DataFrame(detections)