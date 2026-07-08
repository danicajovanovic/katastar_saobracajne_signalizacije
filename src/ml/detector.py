from pathlib import Path
from datetime import date

import pandas as pd
from ultralytics import YOLO

from src.database.connection import get_connection


RESULTS_DIR = Path("results/ml/detections")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

CUSTOM_MODEL_PATH = Path("models/traffic_sign_yolo.pt")
DEFAULT_MODEL = "yolov8n.pt"


def get_model():
    if CUSTOM_MODEL_PATH.exists():
        print("Koristi se specijalizovani model za saobracajne znakove.")
        return YOLO(str(CUSTOM_MODEL_PATH))

    print("Specijalizovani model nije pronadjen. Koristi se opsti YOLOv8n model.")
    return YOLO(DEFAULT_MODEL)


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
            %s, %s, %s, %s, NULL,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s, %s, %s, %s, %s
        );
    """, (
        klasa,
        float(confidence),
        image_name,
        date.today(),
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

        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            insert_detection_to_database(
                klasa=class_name,
                confidence=confidence,
                image_name=image_name,
                lon=lon,
                lat=lat,
                model_name=str(CUSTOM_MODEL_PATH if CUSTOM_MODEL_PATH.exists() else DEFAULT_MODEL),
                bbox=(x1, y1, x2, y2)
            )

            detections.append({
                "klasa": class_name,
                "confidence": round(confidence, 3),
                "naziv_slike": image_name,
                "lon": lon,
                "lat": lat,
                "bbox_x1": round(x1, 2),
                "bbox_y1": round(y1, 2),
                "bbox_x2": round(x2, 2),
                "bbox_y2": round(y2, 2),
                "rezultat": str(output_path)
            })

    return detections


def detections_to_dataframe(detections):
    return pd.DataFrame(detections)