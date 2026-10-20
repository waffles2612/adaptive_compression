"""Spatial region-of-interest handling for the AI method.

x264 can lower QP for macroblocks inside a region, but per-frame QP maps are not
reachable from the ffmpeg command line (ffmpeg's `addroi` filter only accepts
fixed regions). We therefore use the equivalent pre-filtering technique:
background pixels outside the (enlarged) object boxes are smoothed before
encoding, so the encoder spends almost no bits on background texture and noise,
while the objects themselves are passed through untouched. The mask edge is
feathered so no hard seam is visible.
"""
from __future__ import annotations

from typing import Callable, List

import cv2
import numpy as np

from .detector import roi_mask


def make_roi_preprocessor(boxes_per_frame: List[List[list]], active: List[bool],
                          sigma: float = 3.0, margin: float = 0.25,
                          feather: int = 15) -> Callable[[int, np.ndarray], np.ndarray]:
    """Return preprocess(frame_idx, frame). Only frames where `active[i]` is True
    and objects are present are filtered; idle frames are left to the QP controller."""
    ksize = int(6 * sigma) | 1
    fk = feather | 1

    def preprocess(i: int, frame: np.ndarray) -> np.ndarray:
        boxes = boxes_per_frame[i]
        if not active[i] or not boxes:
            return frame
        h, w = frame.shape[:2]
        m = roi_mask(boxes, h, w, margin).astype(np.float32)
        m = cv2.GaussianBlur(m, (fk, fk), 0)[..., None]
        bg = cv2.GaussianBlur(frame, (ksize, ksize), sigma)
        return (m * frame + (1 - m) * bg).astype(np.uint8)

    return preprocess
