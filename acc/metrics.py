"""Evaluation metrics (slide 10).

Compression : file size, bitrate, compression ratio, storage reduction
Quality     : PSNR and SSIM on luma (whole frame), plus
              ROI-PSNR   - PSNR only inside detected objects (what an operator cares about)
              Event-PSNR - PSNR over frames that contain objects / activity
              Idle-PSNR  - PSNR over empty frames
              VMAF       - if ffmpeg was built with libvmaf
Utility     : detection precision / recall / F1 of the detector on the decoded
              video, using detections on the original video as reference.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, List, Optional

import cv2
import numpy as np

from .detector import roi_mask
from .video_io import VideoInfo, iter_frames


def _luma(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)[:, :, 0].astype(np.float32)


def _ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Standard SSIM (Wang et al. 2004), 11x11 Gaussian window, sigma 1.5, on 8-bit luma."""
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_a, mu_b = blur(a), blur(b)
    s_aa = blur(a * a) - mu_a ** 2
    s_bb = blur(b * b) - mu_b ** 2
    s_ab = blur(a * b) - mu_a * mu_b
    num = (2 * mu_a * mu_b + c1) * (2 * s_ab + c2)
    den = (mu_a ** 2 + mu_b ** 2 + c1) * (s_aa + s_bb + c2)
    return float((num / den).mean())


def _psnr_from_mse(mse: float) -> float:
    return 100.0 if mse <= 1e-10 else 10 * np.log10(255.0 ** 2 / mse)


def quality_metrics(ref_path: str, enc_path: str, info: VideoInfo,
                    event_flags: Optional[List[bool]] = None,
                    roi_boxes: Optional[Dict[int, List[list]]] = None) -> Dict[str, float]:
    """Frame-by-frame comparison of the encoded file against the source.

    event_flags[i] : True if frame i contains objects of interest (event vs idle PSNR)
    roi_boxes      : {frame_index: boxes} - reference object boxes, measured only on
                     frames where the detector actually ran so boxes are exact.
    PSNR values are aggregated as mean MSE -> PSNR."""
    mse_all, ssim_all = [], []
    roi_sq, roi_px = 0.0, 0
    event_mse, idle_mse = [], []
    enc_iter = iter_frames(enc_path, info)
    for i, ref in enumerate(iter_frames(ref_path, info)):
        enc = next(enc_iter, None)
        if enc is None:
            raise RuntimeError(f"{enc_path} has fewer frames than the source")
        yr, ye = _luma(ref), _luma(enc)
        err = (yr - ye) ** 2
        mse = float(err.mean())
        mse_all.append(mse)
        ssim_all.append(_ssim(yr, ye))
        if event_flags is not None:
            (event_mse if event_flags[i] else idle_mse).append(mse)
        if roi_boxes and roi_boxes.get(i):
            m = roi_mask(roi_boxes[i], info.height, info.width, margin=0.0).astype(bool)
            roi_sq += float(err[m].sum())
            roi_px += int(m.sum())
    out = {
        "psnr": _psnr_from_mse(float(np.mean(mse_all))),
        "ssim": float(np.mean(ssim_all)),
    }
    if roi_boxes is not None:
        out["roi_psnr"] = _psnr_from_mse(roi_sq / roi_px) if roi_px else float("nan")
    if event_flags is not None:
        out["event_psnr"] = _psnr_from_mse(float(np.mean(event_mse))) if event_mse else float("nan")
        out["idle_psnr"] = _psnr_from_mse(float(np.mean(idle_mse))) if idle_mse else float("nan")
    return out


def compression_metrics(enc_path: str, info: VideoInfo) -> Dict[str, float]:
    size = os.path.getsize(enc_path)
    raw = info.width * info.height * 1.5 * info.n_frames  # raw YUV 4:2:0 size
    return {
        "size_bytes": size,
        "size_mb": size / 1e6,
        "bitrate_kbps": size * 8 / info.duration / 1000,
        "compression_ratio": raw / size,
    }


def vmaf_available() -> bool:
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        return " libvmaf " in out
    except FileNotFoundError:
        return False


def vmaf(ref_path: str, enc_path: str, info: VideoInfo, log_path: str) -> float:
    """VMAF via ffmpeg's libvmaf filter (only if available).

    The log file is written with a bare file name from inside its own folder:
    FFmpeg's filter syntax treats ':' and '\\' specially, so a Windows path such
    as C:\\Users\\... cannot be passed inside the filter string."""
    log_dir, log_name = os.path.split(os.path.abspath(log_path))
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.abspath(enc_path), "-i", os.path.abspath(ref_path),
           "-lavfi",
           f"[1:v]crop={info.width}:{info.height}:0:0,format=yuv420p[r];"
           f"[0:v]format=yuv420p[d];[d][r]libvmaf=log_fmt=json:log_path={log_name}",
           "-f", "null", "-"]
    subprocess.run(cmd, check=True, cwd=log_dir)
    with open(os.path.join(log_dir, log_name)) as f:
        return float(json.load(f)["pooled_metrics"]["vmaf"]["mean"])


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_detections(ref: List[list], test: List[list], iou_thr: float = 0.5):
    """Greedy one-to-one matching by IoU (same class). Returns (tp, fp, fn)."""
    used, tp = set(), 0
    for r in sorted(ref, key=lambda b: -b[5]):
        best, best_j = iou_thr, -1
        for j, t in enumerate(test):
            if j in used or t[4] != r[4]:
                continue
            v = _iou(r, t)
            if v >= best:
                best, best_j = v, j
        if best_j >= 0:
            used.add(best_j)
            tp += 1
    return tp, len(test) - len(used), len(ref) - tp


def detection_metrics(enc_path: str, info: VideoInfo, detector, ref_boxes: List[list],
                      frames: List[int]) -> Dict[str, float]:
    """Run the detector on the decoded video at `frames` and compare with the
    reference detections from the original video."""
    wanted = set(frames)
    tp = fp = fn = 0
    for i, frame in enumerate(iter_frames(enc_path, info)):
        if i in wanted:
            a, b, c = match_detections(ref_boxes[i], detector.detect(frame))
            tp, fp, fn = tp + a, fp + b, fn + c
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return {"det_precision": p, "det_recall": r, "det_f1": 2 * p * r / (p + r) if p + r else 0.0}


def bd_rate(rate_a, metric_a, rate_b, metric_b) -> float:
    """Bjontegaard delta-rate (%) of B relative to A: average bitrate change of B
    for the same quality. Negative = B needs fewer bits. Needs >= 4 points each."""
    la, lb = np.log(rate_a), np.log(rate_b)
    pa, pb = np.polyfit(metric_a, la, 3), np.polyfit(metric_b, lb, 3)
    lo, hi = max(min(metric_a), min(metric_b)), min(max(metric_a), max(metric_b))
    if hi <= lo:
        return float("nan")
    ia, ib = np.polyint(pa), np.polyint(pb)
    avg_a = (np.polyval(ia, hi) - np.polyval(ia, lo)) / (hi - lo)
    avg_b = (np.polyval(ib, hi) - np.polyval(ib, lo)) / (hi - lo)
    return float((np.exp(avg_b - avg_a) - 1) * 100)
