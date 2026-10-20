"""Compression controller: turns per-frame importance scores into a QP plan.

    importance score per frame
        -> segment-level max (segments of `segment_frames`)
        -> importance level   (0 = idle, 1 = medium, 2 = high)
        -> dilation           (pre/post-roll so the start/end of an event is kept)
        -> QP per segment     (base QP + offset for that level)
        -> x264 "zones" string

Working per segment (not per frame) avoids QP flicker and keeps the zones list short.
Lower QP = higher quality / more bits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np


@dataclass
class ControllerConfig:
    low_threshold: float          # score >= low  -> level 1 (medium)
    high_threshold: float         # score >= high -> level 2 (high)
    qp_offsets: Dict[int, int] = field(default_factory=lambda: {0: 10, 1: 4, 2: 0})
    segment_frames: int = 10      # decision granularity
    dilate_segments: int = 1      # pre/post-roll, in segments
    max_qp: int = 51


def score_to_levels(scores: Sequence[float], cfg: ControllerConfig) -> np.ndarray:
    s = np.asarray(scores, dtype=float)
    n_seg = int(np.ceil(len(s) / cfg.segment_frames))
    seg_max = np.array([s[k * cfg.segment_frames:(k + 1) * cfg.segment_frames].max() for k in range(n_seg)])
    seg_lvl = np.where(seg_max >= cfg.high_threshold, 2, np.where(seg_max >= cfg.low_threshold, 1, 0))
    # Dilation: a segment inherits the highest level among its neighbours, so an
    # event never starts or ends inside a heavily compressed segment.
    d = cfg.dilate_segments
    if d > 0:
        padded = np.pad(seg_lvl, d, mode="edge")
        seg_lvl = np.max(np.stack([padded[i:i + n_seg] for i in range(2 * d + 1)]), axis=0)
    return np.repeat(seg_lvl, cfg.segment_frames)[: len(s)]


def levels_to_qp(levels: np.ndarray, base_qp: int, cfg: ControllerConfig) -> np.ndarray:
    return np.array([min(cfg.max_qp, base_qp + cfg.qp_offsets[int(l)]) for l in levels], dtype=int)


def qp_to_zones(qp_per_frame: np.ndarray) -> Tuple[str, List[Tuple[int, int, int]]]:
    """Run-length encode the per-frame QP into an x264 zones string."""
    runs, start = [], 0
    for i in range(1, len(qp_per_frame) + 1):
        if i == len(qp_per_frame) or qp_per_frame[i] != qp_per_frame[start]:
            runs.append((start, i - 1, int(qp_per_frame[start])))
            start = i
    return "/".join(f"{a},{b},q={q}" for a, b, q in runs), runs


def fuse_levels(*level_arrays: np.ndarray) -> np.ndarray:
    """Hybrid: keep the highest importance any analyser assigned."""
    return np.max(np.stack(level_arrays), axis=0)
