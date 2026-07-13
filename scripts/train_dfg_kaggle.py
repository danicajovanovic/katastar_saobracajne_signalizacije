"""
Trening YOLOv8 modela na DFG Traffic Sign Dataset (200 klasa) - KAGGLE verzija.

NAMENJENO ZA KAGGLE NOTEBOOKS (besplatno 30h GPU/nedeljno, bez payment/region problema).

Podesavanje pre pokretanja:
  1. kaggle.com -> Create -> New Notebook
  2. Desno, Settings -> Accelerator -> GPU T4 x2 (ili P100)
  3. Settings -> Internet -> ON (obavezno, skripta skida dataset sa vicos.si)
  4. Nalepi ovaj fajl u jednu celiju i pokreni

Checkpoint-i idu u /kaggle/working/dfg_training_runs - to PREZIVI restart kernela
u istoj sesiji, ali NE prezivi kraj sesije osim ako klikn Save Version (commit)
ili rucno preuzmes weights/last.pt pre nego sto zatvoris notebook.

Za nastavak u novoj sesiji: preuzmi weights/last.pt sa kraja prethodne sesije,
napravi Kaggle Dataset od njega, dodaj ga kao Input u novi notebook, i postavi
RESUME_CKPT ispod na putanju do tog fajla (npr. /kaggle/input/dfg-checkpoint/last.pt).

Popravke u odnosu na prvobitni trening (dfg_200_classes_from_scratch):
  1. pretrained=True, baza yolov8s.pt (COCO) umesto yolov8n.yaml od nule.
  2. imgsz=960 umesto 640 - DFG ima dosta sitnih/udaljenih znakova.
"""

import json
import os
import tarfile
import zipfile
from pathlib import Path

import requests
from ultralytics import YOLO

# --- 1. Podesavanja -----------------------------------------------------

ROOT = Path("/kaggle/working/DFG_yolo")
RAW = ROOT / "raw"
IMAGES_SRC = RAW / "JPEGImages"

URLS = {
    "annot": "https://data.vicos.si/skokec/villard/DFG-tsd-annot-json.zip",
    "images": "https://data.vicos.si/skokec/villard/JPEGImages.tar.bz2",
}

MODEL_BASE = "yolov8s.pt"
EPOCHS = 150
IMG_SIZE = 960
BATCH = 16          # smanji na 8 ako CUDA out of memory
PATIENCE = 30

PROJECT_DIR = "/kaggle/working/dfg_training_runs"
RUN_NAME = "dfg_200_classes_pretrained"

# Ako nastavljas prekinut trening iz prethodne Kaggle sesije, stavi ovde
# putanju do uploadovanog checkpoint-a (kao Kaggle Dataset Input), npr:
# RESUME_CKPT = "/kaggle/input/dfg-checkpoint/last.pt"
RESUME_CKPT = None


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

    annot_zip = RAW / "annot.zip"
    download(URLS["annot"], annot_zip)
    if not (RAW / "train.json").exists():
        print("Raspakujem anotacije...")
        with zipfile.ZipFile(annot_zip) as z:
            z.extractall(RAW)

    images_tar = RAW / "JPEGImages.tar.bz2"
    download(URLS["images"], images_tar)
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
    last_ckpt = Path(PROJECT_DIR) / RUN_NAME / "weights" / "last.pt"

    if RESUME_CKPT:
        print(f"Nastavljam trening od uploadovanog checkpointa: {RESUME_CKPT}")
        model = YOLO(RESUME_CKPT)
        model.train(
            data=str(data_yaml),
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH,
            patience=PATIENCE,
            project=PROJECT_DIR,
            name=RUN_NAME,
        )
    elif last_ckpt.exists():
        print(f"Nastavljam trening od: {last_ckpt} (ista sesija)")
        model = YOLO(str(last_ckpt))
        model.train(resume=True)
    else:
        model = YOLO(MODEL_BASE)  # COCO pretrained tezine
        model.train(
            data=str(data_yaml),
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH,
            patience=PATIENCE,
            pretrained=True,
            project=PROJECT_DIR,
            name=RUN_NAME,
        )


if __name__ == "__main__":
    prepare_raw_data()
    names = convert_split(RAW / "train.json", "train")
    convert_split(RAW / "test.json", "val")
    data_yaml = write_data_yaml(names)
    train(data_yaml)

    print(
        f"\nGotovo (ili prekinuto zbog vremena). Tezine su u "
        f"{PROJECT_DIR}/{RUN_NAME}/weights/\n"
        "VAZNO: pre nego sto zatvoris notebook, preuzmi weights/last.pt i weights/best.pt "
        "rucno (desni klik u Kaggle file browseru -> Download), ili klikni 'Save Version' "
        "da se /kaggle/working sacuva kao output ove sesije."
    )
