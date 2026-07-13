"""
Trening YOLOv8 modela na DFG Traffic Sign Dataset (200 klasa, isti taksonomija kao models/best.pt).

Ocekivano trajanje: par sati na Colab T4 GPU-u (batch/imgsz podesi ako OOM-uje).
"""

import json
import os
import tarfile
import zipfile
from pathlib import Path

import requests
from ultralytics import YOLO

# --- 1. Podesavanja -----------------------------------------------------

ROOT = Path("/content/DFG_yolo")
RAW = ROOT / "raw"
IMAGES_SRC = RAW / "JPEGImages"

# Dataset je vec preuzet i lezi direktno u korenu My Drive-a (ne u podfolderu).
# Ako fajlovi ne postoje tu, skripta ce sama skinuti sa vicos.si (fallback).
DRIVE_DATASET_DIR = Path("/content/drive/MyDrive")

URLS = {
    "annot": "https://data.vicos.si/skokec/villard/DFG-tsd-annot-json.zip",
    "images": "https://data.vicos.si/skokec/villard/JPEGImages.tar.bz2",
}

MODEL_BASE = "yolov8s.pt"   # COCO pretrained; probaj yolov8m.pt ako GPU/vreme dozvoljava
EPOCHS = 150
IMG_SIZE = 960
BATCH = 16                  # smanji na 8 ako dobijes CUDA out of memory na imgsz=960
PATIENCE = 30


# --- 2. Preuzimanje i raspakivanje ---------------------------------------

def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"Preskačem, već postoji: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Preuzimam {url} -> {dest}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def prepare_raw_data() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    drive_annot = DRIVE_DATASET_DIR / "DFG-tsd-annot-json.zip"
    drive_images = DRIVE_DATASET_DIR / "JPEGImages.tar.bz2"

    if drive_annot.exists() and drive_images.exists():
        print(f"Koristim vec preuzet dataset sa Drive-a: {DRIVE_DATASET_DIR}")
        annot_zip = drive_annot
        images_tar = drive_images
    else:
        print("Fajlovi nisu nadjeni na Drive-u, skidam dataset sa vicos.si...")
        annot_zip = RAW / "annot.zip"
        download(URLS["annot"], annot_zip)
        images_tar = RAW / "JPEGImages.tar.bz2"
        download(URLS["images"], images_tar)

    if not (RAW / "train.json").exists():
        print("Raspakujem anotacije...")
        with zipfile.ZipFile(annot_zip) as z:
            z.extractall(RAW)

    if not IMAGES_SRC.exists():
        print("Raspakujem slike (7GB, potraje par minuta)...")
        with tarfile.open(images_tar, "r:bz2") as t:
            t.extractall(RAW)


# --- 3. Konverzija COCO -> YOLO format ------------------------------------

def convert_split(json_path: Path, split: str) -> list[str]:
    data = json.loads(json_path.read_text())

    images_by_id = {img["id"]: img for img in data["images"]}
    names_in_order = [c["name"] for c in sorted(data["categories"], key=lambda c: c["id"])]

    anns_by_image: dict[int, list] = {}
    for ann in data["annotations"]:
        if ann.get("ignore"):
            continue
        anns_by_image.setdefault(ann["image_id"], []).append(ann)

    img_dir = ROOT / "images" / split
    lbl_dir = ROOT / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    for image_id, img in images_by_id.items():
        file_name = img["file_name"]
        src = IMAGES_SRC / file_name
        if not src.exists():
            continue

        link = img_dir / file_name
        if not link.exists():
            os.symlink(src.resolve(), link)

        w, h = img["width"], img["height"]
        lines = []
        for ann in anns_by_image.get(image_id, []):
            x, y, bw, bh = ann["bbox"]
            cx = (x + bw / 2) / w
            cy = (y + bh / 2) / h
            nw = bw / w
            nh = bh / h
            lines.append(f"{ann['category_id']} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        (lbl_dir / (Path(file_name).stem + ".txt")).write_text("\n".join(lines))

    print(f"{split}: {len(images_by_id)} slika konvertovano")
    return names_in_order


def write_data_yaml(names: list[str]) -> Path:
    yaml_path = ROOT / "data.yaml"
    names_block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    yaml_path.write_text(
        f"path: {ROOT}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"names:\n{names_block}\n"
    )
    print(f"data.yaml sacuvan: {yaml_path} ({len(names)} klasa)")
    return yaml_path


# --- 4. Trening ------------------------------------------------------------

def train(data_yaml: Path) -> None:
    model = YOLO(MODEL_BASE)  # COCO pretrained tezine, ne .yaml arhitektura
    model.train(
        data=str(data_yaml),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH,
        patience=PATIENCE,
        pretrained=True,
        project="/content/runs",
        name="dfg_200_classes_pretrained",
    )


if __name__ == "__main__":
    prepare_raw_data()
    names = convert_split(RAW / "train.json", "train")
    convert_split(RAW / "test.json", "val")
    data_yaml = write_data_yaml(names)
    train(data_yaml)

    print(
        "\nGotovo. Najbolje tezine su u "
        "/content/runs/dfg_200_classes_pretrained/weights/best.pt\n"
        "Preuzmi taj fajl i zameni njime models/best.pt u projektu."
    )
