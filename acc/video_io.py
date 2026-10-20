"""Video reading and H.264 encoding helpers (OpenCV for decoding, FFmpeg/libx264 for encoding)."""
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

import cv2
import numpy as np


@dataclass
class VideoInfo:
    path: str
    width: int
    height: int
    fps: float
    n_frames: int

    @property
    def duration(self) -> float:
        return self.n_frames / self.fps


def probe(path: str) -> VideoInfo:
    """Read basic stream info. Frame count is obtained by actually decoding,
    because container metadata is often wrong for CCTV exports."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = 0
    while cap.grab():
        n += 1
    cap.release()
    # H.264 with yuv420p needs even dimensions; we crop the last row/column if needed.
    return VideoInfo(path, w - (w % 2), h - (h % 2), float(fps), n)


def iter_frames(path: str, info: Optional[VideoInfo] = None) -> Iterator[np.ndarray]:
    """Yield BGR frames, cropped to even dimensions."""
    cap = cv2.VideoCapture(path)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if info is not None:
            frame = frame[: info.height, : info.width]
        yield frame
    cap.release()


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install it (e.g. `sudo apt install ffmpeg`, "
                           "`brew install ffmpeg`, or download from ffmpeg.org on Windows).")


def encode_h264(
    src: str,
    info: VideoInfo,
    out_path: str,
    base_qp: int,
    zones: str = "",
    preset: str = "medium",
    preprocess: Optional[Callable[[int, np.ndarray], np.ndarray]] = None,
    keyint: int = 0,
) -> float:
    """Encode `src` with libx264 in constant-QP mode.

    * `zones` is an x264 zones string ("start,end,q=QP/start,end,q=QP/...") that
      overrides the QP for frame ranges -> this is how the adaptive controllers
      change compression over time.
    * `preprocess(frame_idx, frame)` optionally modifies each frame before
      encoding (used by the AI method for region-of-interest filtering).
    * `keyint` sets a fixed GOP length (0 = x264 default of 250 frames).

    All methods are fed the *same* raw frames through a pipe, so differences in
    the results come only from the compression decisions.
    Returns the wall-clock encoding time in seconds.
    """
    check_ffmpeg()
    params = f"qp={base_qp}"
    if keyint > 0:  # fixed GOP like a CCTV recorder (keyframe every N frames, no scene-cut I-frames)
        params += f":keyint={keyint}:min-keyint={keyint}:scenecut=0"
    if zones:
        params += f":zones={zones}"
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{info.width}x{info.height}", "-r", f"{info.fps}",
        "-i", "-",
        "-c:v", "libx264", "-preset", preset,
        "-x264-params", params,
        "-pix_fmt", "yuv420p",
        out_path,
    ]
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, frame in enumerate(iter_frames(src, info)):
        if preprocess is not None:
            frame = preprocess(i, frame)
        proc.stdin.write(np.ascontiguousarray(frame).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out_path}")
    return time.perf_counter() - t0
