#!/usr/bin/env python3
"""Comparative analysis of adaptive H.264 compression for CCTV.

Runs every method over a sweep of base QPs on the same input, measures storage,
quality, cost and surveillance utility, and writes:

    <out>/encodes/<method>_qp<NN>.mp4   compressed videos
    <out>/analysis.json                 cached motion + detection analysis
    <out>/results.csv                   one row per (method, QP)
    <out>/summary.md                    tables incl. BD-rate vs. the fixed baseline
    <out>/plots/*.png                   RD curves, storage, timeline, cost

Methods
    fixed   - 01 Fixed H.264: one QP for the whole video
    motion  - 02 Motion-based adaptive QP (background subtraction activity score)
    ai_qp   - 03a AI-based adaptive QP only (YOLO decides the QP over time)
    ai      - 03b AI-based adaptive QP + spatial ROI (background smoothed outside objects)
    hybrid  - AI + motion fused (the "motion analysis: optional" column on slide 9)

Example
    python run_experiment.py --input data/cctv_test.mp4 --out results/cctv_test
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import pandas as pd

from acc import controller as ctl
from acc.metrics import (bd_rate, compression_metrics, detection_metrics,
                         quality_metrics, vmaf, vmaf_available)
from acc.motion import analyse_motion
from acc.video_io import encode_h264, probe

METHODS = ["fixed", "motion", "ai_qp", "ai", "hybrid"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="CCTV video file")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--methods", nargs="+", default=METHODS, choices=METHODS)
    p.add_argument("--qps", nargs="+", type=int, default=[22, 27, 32, 37],
                   help="base QPs to sweep (>=4 needed for BD-rate)")
    p.add_argument("--preset", default="medium", help="x264 preset")
    p.add_argument("--gop-sec", type=float, default=2.0,
                   help="keyframe interval in seconds (CCTV recorders typically use 1-4 s); 0 = x264 default")
    # controller
    p.add_argument("--segment-sec", type=float, default=1.0, help="decision granularity in seconds")
    p.add_argument("--idle-offset", type=int, default=10, help="QP added to idle segments")
    p.add_argument("--medium-offset", type=int, default=4, help="QP added to medium-importance segments")
    # motion
    p.add_argument("--motion-method", default="mog2", choices=["mog2", "diff"])
    p.add_argument("--motion-low", type=float, default=0.002, help="activity fraction for 'medium'")
    p.add_argument("--motion-high", type=float, default=0.01, help="activity fraction for 'high'")
    # AI
    p.add_argument("--model", default="yolov8n.pt", help="ultralytics model used by the AI method")
    p.add_argument("--eval-model", default=None,
                   help="model used to measure detection accuracy (default: same as --model). "
                        "Using a different one (e.g. yolov8s.pt) avoids favouring the AI method.")
    p.add_argument("--det-per-sec", type=float, default=5.0, help="detector runs per second of video")
    p.add_argument("--ai-low", type=float, default=0.25, help="importance score for 'medium'")
    p.add_argument("--ai-high", type=float, default=0.5, help="importance score for 'high'")
    p.add_argument("--static-sec", type=float, default=5.0,
                   help="objects that stay in place this long are treated as background")
    p.add_argument("--no-roi", action="store_true", help="AI method: disable spatial ROI filtering")
    p.add_argument("--roi-sigma", type=float, default=3.0, help="background smoothing strength")
    # evaluation
    p.add_argument("--eval-det-per-sec", type=float, default=1.0,
                   help="frames per second of video used for the detection-accuracy check")
    p.add_argument("--skip-detection-eval", action="store_true")
    p.add_argument("--no-vmaf", action="store_true", help="skip VMAF even if ffmpeg supports it (faster)")
    p.add_argument("--events", default=None,
                   help="JSON file with ground-truth activity intervals [[start_s, end_s], ...] "
                        "(default: <input>.events.json if present, else derived from detections)")
    p.add_argument("--reuse", action="store_true", help="reuse existing encodes / analysis")
    return p.parse_args()


def main():
    a = parse_args()
    os.makedirs(os.path.join(a.out, "encodes"), exist_ok=True)
    info = probe(a.input)
    print(f"Input: {a.input}  {info.width}x{info.height} @ {info.fps:.2f} fps, "
          f"{info.n_frames} frames ({info.duration:.1f} s)")

    needs_ai = any(m in ("ai_qp", "ai", "hybrid") for m in a.methods) or not a.skip_detection_eval
    seg = max(1, int(round(a.segment_sec * info.fps)))
    offsets = {0: a.idle_offset, 1: a.medium_offset, 2: 0}

    # ---------------- 1. scene analysis (cached) ----------------
    cache = os.path.join(a.out, "analysis.json")
    analysis = json.load(open(cache)) if (a.reuse and os.path.exists(cache)) else {}
    if "motion" not in analysis:
        print("Motion analysis ...")
        analysis["motion"] = analyse_motion(a.input, info, method=a.motion_method)
    detector = None
    if needs_ai:
        from acc.detector import Detector, analyse_objects
        detector = Detector(a.model)
        if "objects" not in analysis:
            stride = max(1, int(round(info.fps / a.det_per_sec)))
            print(f"Object detection with {a.model} every {stride} frame(s) ...")
            analysis["objects"] = analyse_objects(a.input, info, detector, stride=stride)
    json.dump(analysis, open(cache, "w"))
    mot = analysis["motion"]
    print(f"  motion analysis: {mot['analysis_time']:.1f} s "
          f"({1000 * mot['analysis_time'] / info.n_frames:.2f} ms/frame)")
    obj = analysis.get("objects")
    if obj:
        print(f"  object analysis: {obj['analysis_time']:.1f} s "
              f"({1000 * obj['analysis_time'] / info.n_frames:.2f} ms/frame)")

    # ---------------- 2. importance levels per method ----------------
    motion_cfg = ctl.ControllerConfig(a.motion_low, a.motion_high, offsets, seg)
    levels = {"fixed": np.full(info.n_frames, 2)}
    levels["motion"] = ctl.score_to_levels(mot["scores"], motion_cfg)
    moving_boxes = None
    if obj:
        from acc.detector import importance_scores, mark_static
        # Objects that stay put (parked cars, ...) are scene background, not activity.
        static = mark_static(obj["boxes"], obj["sampled_frames"], info.fps, a.static_sec)
        moving_boxes = [[b for b, s in zip(bx, fl) if not s] for bx, fl in zip(obj["boxes"], static)]
        obj["scores"] = importance_scores(obj["boxes"], static)
        n_static = sum(sum(f) for f in static) / max(1, sum(len(b) for b in obj["boxes"]))
        print(f"  {100 * n_static:.0f}% of detections are static objects (ignored for importance)")
        ai_cfg = ctl.ControllerConfig(a.ai_low, a.ai_high, offsets, seg)
        levels["ai"] = ctl.score_to_levels(obj["scores"], ai_cfg)
        levels["ai_qp"] = levels["ai"]
        levels["hybrid"] = ctl.fuse_levels(levels["ai"], levels["motion"])
    analysis_cost = {"fixed": 0.0, "motion": mot["analysis_time"],
                     "ai": obj["analysis_time"] if obj else 0.0,
                     "ai_qp": obj["analysis_time"] if obj else 0.0,
                     "hybrid": (obj["analysis_time"] if obj else 0.0) + mot["analysis_time"]}

    # Reference for evaluation = detections on the ORIGINAL video.
    event_flags = roi_boxes = None
    eval_frames = []
    events_file = a.events or (a.input + ".events.json" if os.path.exists(a.input + ".events.json") else None)
    if events_file:
        # ground-truth activity intervals in seconds: [[start, end], ...]
        intervals = json.load(open(events_file))
        t = np.arange(info.n_frames) / info.fps
        event_flags = [bool(any(s0 <= x < s1 for s0, s1 in intervals)) for x in t]
        print(f"  ground-truth events from {events_file}: {sum(event_flags)} event frames")
    if obj:
        if event_flags is None:  # fall back to "a moving object is present"
            event_flags = [len(b) > 0 for b in moving_boxes]
        # ROI-PSNR is measured on moving objects (people, moving vehicles) at frames
        # where the detector actually ran, so the boxes are exact.
        roi_boxes = {i: moving_boxes[i] for i in obj["sampled_frames"]}
        step = max(1, int(round(info.fps / a.eval_det_per_sec)))
        eval_frames = [i for i in obj["sampled_frames"] if i % step == 0]
    eval_detector = detector
    if needs_ai and a.eval_model and a.eval_model != a.model and not a.skip_detection_eval:
        from acc.detector import Detector, analyse_objects
        eval_detector = Detector(a.eval_model)
        # the reference boxes must come from the same model that is evaluated
        print(f"Reference detections with evaluation model {a.eval_model} ...")
        ref = analyse_objects(a.input, info, eval_detector, stride=max(1, int(round(info.fps / a.det_per_sec))))
        ref_boxes_eval = ref["boxes"]
    else:
        ref_boxes_eval = obj["boxes"] if obj else None

    do_vmaf = vmaf_available() and not a.no_vmaf
    if not do_vmaf:
        print("  (ffmpeg has no libvmaf -> VMAF column skipped)")

    # ---------------- 3. encode + evaluate ----------------
    rows = []
    for method in a.methods:
        if method not in levels:
            continue
        for qp in a.qps:
            out = os.path.join(a.out, "encodes", f"{method}_qp{qp}.mp4")
            qp_plan = ctl.levels_to_qp(levels[method], qp, motion_cfg)
            zones, runs = ctl.qp_to_zones(qp_plan) if method != "fixed" else ("", [])
            pre = None
            if method in ("ai", "hybrid") and not a.no_roi:
                from acc.roi import make_roi_preprocessor
                pre = make_roi_preprocessor(moving_boxes, [l == 2 for l in levels[method]], sigma=a.roi_sigma)

            meta_path = out + ".json"
            meta = json.load(open(meta_path)) if (a.reuse and os.path.exists(out) and os.path.exists(meta_path)) else None
            if meta and "row" in meta:  # fully cached (use --reuse only if settings are unchanged)
                rows.append(meta["row"])
                print(f"  {method:7s} QP{qp}: cached")
                continue
            if meta:
                enc_time = meta["encode_time_s"]
            else:
                enc_time = encode_h264(a.input, info, out, qp, zones, a.preset, pre,
                                       keyint=int(round(a.gop_sec * info.fps)))
                json.dump({"encode_time_s": enc_time, "zones": zones}, open(out + ".json", "w"))
            row = {"method": method, "base_qp": qp, "mean_qp": float(qp_plan.mean()),
                   "n_zones": len(runs), "encode_time_s": enc_time,
                   "analysis_time_s": analysis_cost[method]}
            row["total_time_s"] = row["encode_time_s"] + row["analysis_time_s"]
            row["ms_per_frame"] = 1000 * row["total_time_s"] / info.n_frames
            row.update(compression_metrics(out, info))

            t0 = time.perf_counter()
            row.update(quality_metrics(a.input, out, info, event_flags, roi_boxes))
            if do_vmaf:
                try:
                    row["vmaf"] = vmaf(a.input, out, info, out + ".vmaf.json")
                except Exception as e:  # VMAF is optional: never let it stop the run
                    print(f"  (VMAF failed, continuing without it: {e})")
                    do_vmaf = False
            if eval_detector is not None and not a.skip_detection_eval:
                row.update(detection_metrics(out, info, eval_detector, ref_boxes_eval, eval_frames))
            rows.append(row)
            json.dump({"encode_time_s": enc_time, "zones": zones, "row": row}, open(meta_path, "w"))
            print(f"  {method:7s} QP{qp}: {row['size_mb']:7.2f} MB  {row['bitrate_kbps']:7.1f} kb/s  "
                  f"PSNR {row['psnr']:.2f}  SSIM {row['ssim']:.4f}"
                  + (f"  ROI-PSNR {row['roi_psnr']:.2f}" if 'roi_psnr' in row else "")
                  + (f"  det-F1 {row['det_f1']:.3f}" if 'det_f1' in row else "")
                  + f"   (eval {time.perf_counter() - t0:.0f}s)")

    df = pd.DataFrame(rows)
    # storage reduction vs fixed at the same base QP
    fixed = df[df.method == "fixed"].set_index("base_qp")["size_bytes"]
    df["storage_reduction_pct"] = [100 * (1 - r.size_bytes / fixed[r.base_qp]) if r.base_qp in fixed else np.nan
                                   for r in df.itertuples()]
    df.to_csv(os.path.join(a.out, "results.csv"), index=False)

    # timeline data for plotting
    timeline = pd.DataFrame({"frame": np.arange(info.n_frames), "time_s": np.arange(info.n_frames) / info.fps,
                             "motion_score": mot["scores"]})
    if obj:
        timeline["object_score"] = obj["scores"]
        timeline["n_objects"] = [len(b) for b in obj["boxes"]]
        timeline["n_moving_objects"] = [len(b) for b in moving_boxes]
    if event_flags is not None:
        timeline["event"] = event_flags
    for m, l in levels.items():
        timeline[f"level_{m}"] = l
    timeline.to_csv(os.path.join(a.out, "timeline.csv"), index=False)

    write_summary(df, a.out, info)
    from plots import make_plots
    make_plots(a.out)
    print(f"\nDone. Results in {a.out}/ (results.csv, summary.md, plots/)")


def write_summary(df: pd.DataFrame, out: str, info) -> None:
    lines = [f"# Results\n", f"Input: {info.width}x{info.height}, {info.fps:.2f} fps, "
             f"{info.n_frames} frames ({info.duration:.1f} s)\n"]
    cols = ["method", "base_qp", "size_mb", "bitrate_kbps", "storage_reduction_pct", "psnr", "ssim",
            "roi_psnr", "event_psnr", "idle_psnr", "vmaf", "det_f1", "ms_per_frame"]
    cols = [c for c in cols if c in df.columns]
    lines.append("## All runs\n")
    lines.append(df[cols].round(3).to_markdown(index=False))

    # BD-rate: bitrate change for equal quality vs fixed baseline
    lines.append("\n\n## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)\n")
    metrics = [m for m in ["psnr", "ssim", "roi_psnr", "event_psnr"] if m in df.columns]
    base = df[df.method == "fixed"].sort_values("base_qp")
    bd_rows = []
    for m in df.method.unique():
        if m == "fixed" or len(base) < 4 or (df.method == m).sum() < 4:
            continue
        d = df[df.method == m].sort_values("base_qp")
        r = {"method": m}
        for met in metrics:
            try:
                r[f"BD-rate {met} (%)"] = round(bd_rate(base.bitrate_kbps.values, base[met].values,
                                                        d.bitrate_kbps.values, d[met].values), 1)
            except Exception:
                r[f"BD-rate {met} (%)"] = float("nan")
        bd_rows.append(r)
    if bd_rows and len(base) >= 4:
        lines.append(pd.DataFrame(bd_rows).to_markdown(index=False))
    else:
        lines.append("(needs the fixed method and >= 4 QPs)")
    lines.append("\n\nNotes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside "
                 "moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR "
                 "split frames into activity vs. empty periods (ground truth if an events file is given). "
                 "det_f1 compares detections on the decoded video with detections on the original "
                 "(all objects, including parked vehicles). storage_reduction_pct compares file size with "
                 "fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.\n")
    with open(os.path.join(out, "summary.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
