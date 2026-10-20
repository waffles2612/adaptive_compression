#!/usr/bin/env python3
"""Run the whole comparison on real surveillance videos and print Table III.

Steps (all automatic):
  1. download four fixed-camera clips from Intel's public sample-videos set
     (CC BY 4.0, https://github.com/intel-iot-devkit/sample-videos)
  2. convert them to CCTV-style lossless reference videos in data/real/
  3. run run_experiment.py on each (fixed, motion, AI QP-only, AI + ROI)
  4. print the Table III values (storage saving at QP 27, BD-rate on ROI-PSNR)

Usage:
    python run_real_videos.py                 # all four clips
    python run_real_videos.py indoor_room     # just one (names below)
    python run_real_videos.py --fast          # x264 'veryfast' preset, much quicker
    python run_real_videos.py --no-vmaf       # skip the (optional) VMAF metric

If it stops half-way, run it again: finished work is reused.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.request

import pandas as pd

BASE = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/"
CLIPS = {
    # name: (source file, extra ffmpeg filter, description)
    "outdoor_parking": ("person-bicycle-car-detection.mp4", None, "Outdoor car park"),
    "indoor_room": ("one-by-one-person-detection.mp4", None, "Indoor room"),
    "retail_aisle": ("store-aisle-detection.mp4", "fps=15", "Retail aisle"),
    "industrial": ("worker-zone-detection.mp4", "fps=15,scale=960:540", "Industrial floor"),
}
METHODS = ["fixed", "motion", "ai_qp", "ai"]

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "real", "source")
REF = os.path.join(HERE, "data", "real")


def download(name: str) -> str:
    src, _, _ = CLIPS[name]
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, src)
    if not os.path.exists(path):
        print(f"Downloading {src} ...")
        urllib.request.urlretrieve(BASE + src, path)
    return path


def convert(name: str, src_path: str) -> str:
    _, vf, _ = CLIPS[name]
    out = os.path.join(REF, f"{name}.mp4")
    if not os.path.exists(out):
        print(f"Converting {name} ...")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", src_path, "-an"]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-qp", "0", "-pix_fmt", "yuv420p", out]
        subprocess.run(cmd, check=True)
    return out


def run(name: str, ref: str, fast: bool) -> str:
    out = os.path.join(HERE, "results", f"real_{name}")
    cmd = [sys.executable, os.path.join(HERE, "run_experiment.py"), "--input", ref, "--out", out,
           "--methods", *METHODS, "--reuse"]
    if fast:
        cmd += ["--preset", "veryfast"]
    if "--no-vmaf" in sys.argv:
        cmd += ["--no-vmaf"]
    print(f"\n===== Running {name} (this takes several minutes) =====")
    subprocess.run(cmd, check=True, cwd=HERE)
    return out


def table_row(name: str, out: str) -> dict:
    df = pd.read_csv(os.path.join(out, "results.csv"))
    q = df[df.base_qp == 27].set_index("method")
    bd = {}
    text = open(os.path.join(out, "summary.md"), encoding="utf-8").read()
    for line in text.splitlines():
        m = re.match(r"\|\s*(motion|ai_qp|ai)\s*\|(.*)\|", line)
        if m and "BD-rate" not in line:
            cells = [c.strip() for c in m.group(2).split("|")]
            bd[m.group(1)] = cells[2]  # columns: psnr, ssim, roi_psnr, event_psnr
    row = {"Sequence": CLIPS[name][2]}
    for meth, label in [("motion", "Motion"), ("ai_qp", "AI (QP)"), ("ai", "AI+ROI")]:
        row[f"{label} Save"] = round(float(q.loc[meth, "storage_reduction_pct"]), 1)
        row[f"{label} BD"] = bd.get(meth, "n/a")
    return row


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fast = "--fast" in sys.argv
    names = args or list(CLIPS)
    for n in names:
        if n not in CLIPS:
            sys.exit(f"Unknown clip '{n}'. Choose from: {', '.join(CLIPS)}")
    rows = []
    for n in names:
        ref = convert(n, download(n))
        out = run(n, ref, fast)
        rows.append(table_row(n, out))
    table = pd.DataFrame(rows)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    table.to_csv(os.path.join(HERE, "results", "table3.csv"), index=False)
    print("\n================ TABLE III ================")
    print("Save = storage saving at QP 27 (%), BD = BD-rate on ROI-PSNR (%)\n")
    print(table.to_string(index=False))
    print("\nAlso saved to results/table3.csv")


if __name__ == "__main__":
    main()
