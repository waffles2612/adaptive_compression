"""Approach 02 - motion / activity analysis.

For every frame we estimate how much of the scene is changing. Two methods:
  * "mog2": OpenCV MOG2 background subtraction (robust to sensor noise and slow
             lighting changes) - default.
  * "diff": plain absolute difference between consecutive frames.
The activity score is the fraction of pixels classified as moving (0..1).
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .video_io import VideoInfo, iter_frames


def analyse_motion(src: str, info: VideoInfo, method: str = "mog2",
                   work_width: int = 320, diff_threshold: int = 25) -> dict:
    scale = work_width / info.width
    size = (work_width, max(2, int(round(info.height * scale))))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mog = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=False)

    scores, prev = [], None
    t0 = time.perf_counter()
    for i, frame in enumerate(iter_frames(src, info)):
        gray = cv2.cvtColor(cv2.resize(frame, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        if method == "diff":
            mask = np.zeros_like(gray) if prev is None else \
                cv2.threshold(cv2.absdiff(gray, prev), diff_threshold, 255, cv2.THRESH_BINARY)[1]
            prev = gray
        else:
            mask = mog.apply(gray)
            if i < 5:  # model warm-up: first frames are all "foreground"
                mask[:] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # remove isolated noise pixels
        scores.append(float(np.count_nonzero(mask)) / mask.size)
    elapsed = time.perf_counter() - t0
    return {"method": method, "scores": scores, "analysis_time": elapsed}
