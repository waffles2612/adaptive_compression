#!/usr/bin/env python3
"""Build a realistic CCTV test clip with long idle periods and short events.

Real surveillance footage is mostly an empty scene. Public pedestrian clips are
usually busy the whole time, so this script takes such a clip and builds a
timeline:   idle -> activity -> idle -> activity -> idle

* Idle frames: the empty background (temporal median of the source) with a
  slow brightness drift.
* Activity frames: consecutive chunks of the real source footage.
* Every frame gets the same temporal sensor noise (--noise), like a live camera.
  Public clips are already compressed, so their own noise has been removed.

The output is written losslessly-ish (x264 QP 0) so it can serve as the reference.

Example (OpenCV's sample pedestrian video):
    python make_test_clip.py --source data/vtest.avi --out data/cctv_test.mp4
"""
from __future__ import annotations

import argparse
import json
import subprocess

import cv2
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--timeline", default="idle:30,act:20,idle:40,act:25,idle:20",
                   help="comma list of idle:SECONDS / act:SECONDS")
    p.add_argument("--noise", type=float, default=1.5, help="sensor noise std-dev added to every frame (0 = none)")
    a = p.parse_args()

    cap = cv2.VideoCapture(a.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    h, w = frames[0].shape[:2]
    h, w = h - h % 2, w - w % 2
    frames = [f[:h, :w] for f in frames]
    background = np.median(np.stack(frames[:: max(1, len(frames) // 60)]), axis=0).astype(np.float32)

    rng = np.random.default_rng(0)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-qp", "0",
           "-pix_fmt", "yuv420p", a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    src_pos, t, n_out = 0, 0, 0
    events, t_sec = [], 0.0
    for item in a.timeline.split(","):
        kind, sec = item.split(":")
        n = int(round(float(sec) * fps))
        if kind == "act":
            events.append([t_sec, t_sec + n / fps])
        t_sec += n / fps
        for _ in range(n):
            if kind == "idle":
                gain = 1.0 + 0.03 * np.sin(2 * np.pi * t / (fps * 60))  # slow lighting drift
                f = background * gain
            else:
                f = frames[src_pos % len(frames)].astype(np.float32)
                src_pos += 1
            if a.noise > 0:
                f = f + rng.normal(0, a.noise, f.shape)
            f = np.clip(f, 0, 255).astype(np.uint8)
            proc.stdin.write(f.tobytes())
            t += 1
            n_out += 1
    proc.stdin.close()
    proc.wait()
    with open(a.out + ".events.json", "w") as fh:  # ground truth for the evaluation
        json.dump(events, fh)
    print(f"Wrote {a.out}: {n_out} frames, {w}x{h} @ {fps} fps ({n_out / fps:.0f} s)")


if __name__ == "__main__":
    main()
