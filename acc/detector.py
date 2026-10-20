"""Approach 03 - AI (semantic) analysis with a pre-trained YOLO object detector.

The detector answers "what is present in the scene?" - people, vehicles, ...
Each frame gets:
  * a list of boxes  [x1, y1, x2, y2, class_id, confidence]
  * a semantic importance score = max(class_weight * confidence) over boxes
To keep the cost practical on CPU, the detector runs every `stride` frames and
boxes are held for the frames in between.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np

from .video_io import VideoInfo, iter_frames

# COCO class id -> importance weight for surveillance. Anything else is ignored.
DEFAULT_CLASS_WEIGHTS: Dict[int, float] = {
    0: 1.0,   # person
    1: 0.8,   # bicycle
    2: 0.8,   # car
    3: 0.8,   # motorcycle
    5: 0.8,   # bus
    7: 0.8,   # truck
    24: 0.6,  # backpack
    26: 0.6,  # handbag
    28: 0.6,  # suitcase
}


class Detector:
    def __init__(self, model: str = "yolov8n.pt", conf: float = 0.25, imgsz: int = 640,
                 class_weights: Optional[Dict[int, float]] = None):
        from ultralytics import YOLO  # imported lazily: only needed for the AI approach
        self.model = YOLO(model)
        self.conf = conf
        self.imgsz = imgsz
        self.class_weights = class_weights or DEFAULT_CLASS_WEIGHTS

    def detect(self, frame: np.ndarray) -> List[list]:
        res = self.model.predict(frame, conf=self.conf, imgsz=self.imgsz,
                                 classes=list(self.class_weights), verbose=False)[0]
        if res.boxes is None or len(res.boxes) == 0:
            return []
        xyxy = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy().astype(int)
        conf = res.boxes.conf.cpu().numpy()
        return [[*map(float, b), int(c), float(p)] for b, c, p in zip(xyxy, cls, conf)]

    def importance(self, boxes: List[list]) -> float:
        return max((self.class_weights.get(b[4], 0.0) * b[5] for b in boxes), default=0.0)


def analyse_objects(src: str, info: VideoInfo, detector: Detector, stride: int = 5) -> dict:
    """Run detection every `stride` frames. Returns per-frame boxes/scores plus
    the list of frames where the detector actually ran (used as evaluation
    reference points)."""
    boxes_per_frame, scores, sampled = [], [], []
    last: List[list] = []
    t0 = time.perf_counter()
    for i, frame in enumerate(iter_frames(src, info)):
        if i % stride == 0:
            last = detector.detect(frame)
            sampled.append(i)
        boxes_per_frame.append(last)
        scores.append(detector.importance(last))
    elapsed = time.perf_counter() - t0
    return {"boxes": boxes_per_frame, "scores": scores, "sampled_frames": sampled,
            "stride": stride, "analysis_time": elapsed}


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def mark_static(boxes_per_frame: List[List[list]], sampled_frames: List[int], fps: float,
                static_sec: float = 5.0, iou_thr: float = 0.7,
                grace_sec: float = 3.0, exempt_classes=(0,)) -> List[List[bool]]:
    """Flag detections that have stayed in the same place for >= `static_sec`
    (parked cars, a bag left on a bench, ...). Such objects are part of the
    scene, not activity, so they should not keep the encoder at high quality.

    Each sampled detection is compared with "anchors" (the box where a static
    candidate was first seen). Comparing against the anchor rather than the
    previous frame prevents slowly walking people from being called static.
    Anchors survive short detector misses / occlusions (`grace_sec`).
    `exempt_classes` are never treated as static (default: person - a person
    standing still / loitering is exactly what an operator wants to see).
    Returns flags aligned with boxes_per_frame."""
    anchors: List[dict] = []          # {"box", "cls", "since", "last"}
    static_at = {}
    for f in sampled_frames:
        flags = []
        for b in boxes_per_frame[f]:
            # class-agnostic: the detector may call the same parked vehicle "car" in one
            # frame and "truck" in the next; duplicates at one spot are one object.
            match = next((an for an in anchors if _iou(an["box"], b) >= iou_thr), None)
            if match is None:
                match = {"box": b[:4], "cls": b[4], "since": f, "last": f}
                anchors.append(match)
            match["last"] = f
            flags.append(b[4] not in exempt_classes and (f - match["since"]) / fps >= static_sec)
        anchors = [an for an in anchors if (f - an["last"]) / fps <= grace_sec]
        static_at[f] = flags
    out, last = [], []
    for i, boxes in enumerate(boxes_per_frame):
        if i in static_at:
            last = static_at[i]
        out.append(last if len(last) == len(boxes) else [False] * len(boxes))
    return out


def importance_scores(boxes_per_frame: List[List[list]], static_flags: List[List[bool]],
                      class_weights: Optional[Dict[int, float]] = None) -> List[float]:
    """Per-frame semantic importance, ignoring static objects."""
    w = class_weights or DEFAULT_CLASS_WEIGHTS
    return [max((w.get(b[4], 0.0) * b[5] for b, s in zip(boxes, flags) if not s), default=0.0)
            for boxes, flags in zip(boxes_per_frame, static_flags)]


def roi_mask(boxes: List[list], h: int, w: int, margin: float = 0.15) -> np.ndarray:
    """Binary mask (uint8 0/1) covering all boxes, enlarged by `margin` of box size."""
    mask = np.zeros((h, w), np.uint8)
    for x1, y1, x2, y2, *_ in boxes:
        mx, my = (x2 - x1) * margin, (y2 - y1) * margin
        xa, ya = max(0, int(x1 - mx)), max(0, int(y1 - my))
        xb, yb = min(w, int(np.ceil(x2 + mx))), min(h, int(np.ceil(y2 + my)))
        mask[ya:yb, xa:xb] = 1
    return mask
