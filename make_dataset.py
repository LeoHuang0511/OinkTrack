#!/usr/bin/env python3
"""
make_dataset.py – Build a MOT‑style dataset from the raw OinkTrack recordings.

Usage
-----
$ python make_dataset.py

Place this script **next to** the `OinkTrack/` folder:

project_root/
├─ make_dataset.py
└─ OinkTrack/
   ├─ C1D-1/
   │   ├─ raw_videos/  ── .ts clips or sub‑folders containing clips
   │   └─ annotation.json   ── Supervisely polygon boxes
   ├─ ...
   └─ masks/
       ├─ C1_mask.png
       └─ C2_mask.png

Output
------
The converted dataset is written to:
project_root/dataset/
    ├─ train/
    ├─ val/
    └─ test/
Each sequence follows the standard MOT layout:
    seq_name/
        ├─ img1/       – extracted 1 fps frames (00000001.jpg …)
        ├─ gt/gt.txt   – MOT ground‑truth converted from annotation.json
        └─ seqinfo.ini – sequence meta‑data

Requirements
------------
* **ffmpeg** available in your system PATH
* `pip install opencv-python numpy`

The conversion pipeline performs:
1. `.ts`  → `.mp4` (copy codec)
2. Concatenate all clips of a recording
3. Down‑sample to **1 fps**
4. Extract JPEG frames to `img1/`
5. Apply the camera‑specific mask (C1 or C2)
6. Convert Supervisely annotations to MOT `gt.txt`
7. Write `seqinfo.ini`

Adjust the `SPLIT` dictionary below if you wish to add more sequences to
train/val/test.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np

# -------------------------------------------------------------------------
# 1)  Train/Val/Test split  –  edit as you wish
# -------------------------------------------------------------------------
SPLIT: dict[str, list[str]] = {
    "train": ["C1D-1", "C1D-3", "C1N-1", "C1N-3",
              "C2D-2", "C2N-2", "C2ND-1"],
    "val":   ["C1ND-1", "C2N-3"],
    "test":  ["C2D-1", "C1DN-1", "C1D-2","C1N-2","C2N-1",
              "C2N-4", "C2DN-1"],
}

# -------------------------------------------------------------------------
# 2)  Directory layout
# -------------------------------------------------------------------------
ROOT     = Path("OinkTrack").resolve()      # dataset root (sibling of this script)
OUT_DIR  = Path("dataset")                  # output goes here (created if absent)
MASK_DIR = ROOT / "masks"                   # contains C1_mask.png  /  C2_mask.png

# -------------------------------------------------------------------------
# 3)  Small helper routines
# -------------------------------------------------------------------------

def _run(cmd: list[str]) -> None:
    """Run a subprocess and abort on error."""
    subprocess.run(cmd, check=True)


def ts_to_mp4(ts_path: Path, mp4_path: Path) -> None:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ts_path), "-c", "copy", str(mp4_path)])


def concat_mp4s(mp4_paths: List[Path], output_path: Path) -> None:
    """Concatenate several .mp4 files **without re‑encoding** using ffmpeg concat demuxer."""
    lst_file = output_path.with_suffix(".txt")
    with lst_file.open("w", encoding="utf-8") as f:
        for p in mp4_paths:
            f.write(f"file '{p.as_posix()}'\n")
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", str(lst_file), "-c", "copy", str(output_path)
    ])
    lst_file.unlink(missing_ok=True)


def downsample_to_1fps(src: Path, dst: Path) -> None:
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "fps=1", str(dst)])


def extract_frames(video: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", "fps=1", "-start_number", "1", str(dst_dir / "%08d.jpg"),
    ])


def apply_mask(img_dir: Path, mask_path: Path) -> None:
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print(f"⚠️  Mask not found: {mask_path}")
        return
    mask = (mask > 0).astype(np.uint8)
    for jpg in sorted(img_dir.glob("*.jpg")):
        img = cv2.imread(str(jpg))
        if img is None:
            continue
        m = mask
        if img.shape[:2] != mask.shape:
            m = cv2.resize(mask, (img.shape[1], img.shape[0]), cv2.INTER_NEAREST)
        cv2.imwrite(str(jpg), img * m[..., None])


def sup_to_mot(json_path: Path, txt_out: Path) -> None:
    """Convert Supervisely annotation.json → MOT gt.txt format."""
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Build a continuous id map: original objectId → 1,2,3,...
    object_ids = sorted({fig["objectId"] for fr in data["frames"] for fig in fr["figures"]})
    id_map = {oid: i + 1 for i, oid in enumerate(object_ids)}

    with txt_out.open("w", encoding="utf-8") as fo:
        for fr in data["frames"]:
            fidx = fr["index"] + 1  # MOT frames start from 1
            for fig in fr["figures"]:
                (x1, y1), (x2, y2) = fig["geometry"]["points"]["exterior"]
                x, y = min(x1, x2), min(y1, y2)
                w, h = abs(x2 - x1), abs(y2 - y1)
                fo.write(
                    f"{fidx},{id_map[fig['objectId']]},{int(round(x))},{int(round(y))},"
                    f"{int(round(w))},{int(round(h))},1,1,1\n"
                )


def write_seqinfo(seq_path: Path) -> None:
    """Generate seqinfo.ini for a MOT sequence."""
    imgs = sorted((seq_path / "img1").glob("*.jpg"))
    if not imgs:
        raise RuntimeError(f"No frames found in {seq_path / 'img1'}")
    height, width = cv2.imread(str(imgs[0])).shape[:2]
    with (seq_path / "seqinfo.ini").open("w", encoding="utf-8") as f:
        f.write(
            "[Sequence]\n"
            f"name={seq_path.name}\n"
            "imDir=img1\n"
            "frameRate=1\n"
            f"seqLength={len(imgs)}\n"
            f"imWidth={width}\n"
            f"imHeight={height}\n"
            "imExt=.jpg\n"
        )

# -------------------------------------------------------------------------
# 4)  Validation helpers
# -------------------------------------------------------------------------

def sanity_check() -> list[str]:
    """Return a list of problems detected in the requested sequences."""
    issues: list[str] = []
    for seq in [*SPLIT["train"], *SPLIT["val"], *SPLIT["test"]]:
        seq_dir = ROOT / seq
        raw_dir = seq_dir / "raw_videos"
        if not seq_dir.exists():
            issues.append(f"{seq}: directory not found")
            continue
        if not raw_dir.exists():
            issues.append(f"{seq}: missing raw_videos/")
        elif not any(raw_dir.rglob("*.ts")):
            issues.append(f"{seq}: no .ts clips found in raw_videos/")
        if not (seq_dir / "annotation.json").exists():
            issues.append(f"{seq}: missing annotation.json")
    return issues

# -------------------------------------------------------------------------
# 5)  Core processing logic
# -------------------------------------------------------------------------

def build_1fps_video(raw_dir: Path, tmp_dir: Path) -> Path | None:
    """Return a single 1 fps .mp4 containing the entire recording."""
    # Some scenes store clips directly in raw_videos/, others use sub‑folders
    segment_dirs = [d for d in raw_dir.iterdir() if d.is_dir()] or [raw_dir]
    segments_1fps: list[Path] = []

    for seg in sorted(segment_dirs):
        mp4_list: list[Path] = []
        for ts_file in sorted(seg.glob("*.ts")):
            mp4_path = tmp_dir / f"{seg.name}_{ts_file.stem}.mp4"
            ts_to_mp4(ts_file, mp4_path)
            mp4_list.append(mp4_path)
        if not mp4_list:
            continue
        # Concatenate all .mp4 clips of this segment
        seg_cat = tmp_dir / f"{seg.name}_cat.mp4"
        concat_mp4s(mp4_list, seg_cat)
        # Down‑sample to 1 fps
        seg_1fps = tmp_dir / f"{seg.name}_1fps.mp4"
        downsample_to_1fps(seg_cat, seg_1fps)
        segments_1fps.append(seg_1fps)

    if not segments_1fps:
        return None
    if len(segments_1fps) == 1:
        return segments_1fps[0]

    merged = tmp_dir / "merged_1fps.mp4"
    concat_mp4s(segments_1fps, merged)
    return merged


def process_sequence(seq_name: str, split: str) -> None:
    seq_dir = ROOT / seq_name
    raw_dir = seq_dir / "raw_videos"
    anno    = seq_dir / "annotation.json"

    dst_seq = OUT_DIR / split / seq_name
    img1    = dst_seq / "img1"
    gt_dir  = dst_seq / "gt"
    gt_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        merged_video = build_1fps_video(raw_dir, Path(td))
        if merged_video is None:
            print(f"❌  {seq_name}: No video produced, skipping.")
            return
        extract_frames(merged_video, img1)

    mask_file = MASK_DIR / ("C1_mask.png" if seq_name.startswith("C1") else "C2_mask.png")
    apply_mask(img1, mask_file)
    sup_to_mot(anno, gt_dir / "gt.txt")
    write_seqinfo(dst_seq)

# -------------------------------------------------------------------------
# 6)  Entry‑point
# -------------------------------------------------------------------------
if __name__ == "__main__":
    if not shutil.which("ffmpeg"):
        sys.exit("❌  ffmpeg not found – please install it first.")

    try:
        _ = cv2.__version__
    except AttributeError:
        sys.exit("❌  OpenCV not found – run: pip install opencv-python")

    problems = sanity_check()
    if problems:
        print("=== Missing or invalid items ===")
        for p in problems:
            print("⚠️  ", p)
        sys.exit("‼️  Please fix the issues above and re‑run the script.")

    OUT_DIR.mkdir(exist_ok=True)

    for sp, sequences in SPLIT.items():
        for seq in sequences:
            print(f"▶ Converting {seq}  →  {sp}")
            process_sequence(seq, sp)

    # Write seqmap files expected by TrackEval / MOTChallenge tools
    for sp, sequences in SPLIT.items():
        if sequences:
            (OUT_DIR / f"{sp}_seqmap.txt").write_text("\n".join(sequences))

    print("\n✅  All sequences processed successfully!  Output folder:", OUT_DIR)
