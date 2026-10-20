#!/usr/bin/env python3
"""Plots for the comparative analysis. Can be re-run on its own:
    python plots.py results/cctv_test
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLORS = {"fixed": "#E8743B", "motion": "#2A9DB0", "ai_qp": "#B39DF2", "ai": "#6A4FD0", "hybrid": "#3E9B5B"}
LABELS = {"fixed": "Fixed H.264", "motion": "Motion-based", "ai_qp": "AI (QP only)", "ai": "AI (QP + ROI)",
          "hybrid": "AI + motion (QP + ROI)"}


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def make_plots(out: str) -> None:
    df = pd.read_csv(os.path.join(out, "results.csv"))
    pdir = os.path.join(out, "plots")
    os.makedirs(pdir, exist_ok=True)
    methods = [m for m in COLORS if m in df.method.unique()]

    # 1. Rate-distortion curves
    metrics = [(m, t) for m, t in [("psnr", "PSNR (dB) - whole frame"), ("ssim", "SSIM - whole frame"),
                                   ("roi_psnr", "ROI-PSNR (dB) - inside objects"),
                                   ("det_f1", "Detection F1 on decoded video")] if m in df.columns]
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.6 * len(metrics), 4))
    axes = [axes] if len(metrics) == 1 else axes
    for ax, (met, title) in zip(axes, metrics):
        for m in methods:
            d = df[df.method == m].sort_values("bitrate_kbps")
            ax.plot(d.bitrate_kbps, d[met], "o-", color=COLORS[m], label=LABELS[m], lw=2, ms=5)
        _style(ax, title, "Bitrate (kb/s, log)", "")
        ax.set_xscale("log")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(pdir, "rate_quality_curves.png"), dpi=150)
    plt.close(fig)

    # 2. Storage per method at each base QP
    fig, ax = plt.subplots(figsize=(7, 4))
    qps = sorted(df.base_qp.unique())
    width = 0.8 / len(methods)
    for k, m in enumerate(methods):
        d = df[df.method == m].set_index("base_qp").reindex(qps)
        ax.bar([i + k * width for i in range(len(qps))], d.size_mb, width, color=COLORS[m], label=LABELS[m])
    ax.set_xticks([i + width * (len(methods) - 1) / 2 for i in range(len(qps))])
    ax.set_xticklabels([f"QP {q}" for q in qps])
    _style(ax, "Storage per method (same base QP)", "", "File size (MB)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(pdir, "storage_by_qp.png"), dpi=150)
    plt.close(fig)

    # 3. Cost vs. storage saving
    if "storage_reduction_pct" in df.columns:
        fig, ax = plt.subplots(figsize=(6, 4))
        for m in methods:
            d = df[df.method == m]
            ax.scatter(d.ms_per_frame, d.storage_reduction_pct, color=COLORS[m], label=LABELS[m], s=40)
        _style(ax, "Computational cost vs. storage saving", "Processing time (ms / frame)",
               "Storage reduction vs fixed (%)")
        ax.legend(frameon=False)
        fig.tight_layout()
        fig.savefig(os.path.join(pdir, "cost_vs_saving.png"), dpi=150)
        plt.close(fig)

    # 4. Timeline: what each analyser saw and the resulting decision
    tl_path = os.path.join(out, "timeline.csv")
    if os.path.exists(tl_path):
        tl = pd.read_csv(tl_path)
        lv = [m for m in ["motion", "ai", "hybrid"] if f"level_{m}" in tl.columns]
        has_event = "event" in tl.columns
        rows = 1 + ("object_score" in tl.columns) + len(lv) + has_event
        fig, axes = plt.subplots(rows, 1, figsize=(11, 1.6 * rows + 0.6), sharex=True)
        i = 0
        if has_event:
            axes[0].fill_between(tl.time_s, tl.event.astype(int), step="post", color="#555555", alpha=0.5)
            axes[0].set_yticks([])
            axes[0].set_ylabel("True\nevents", rotation=0, ha="right", va="center")
            i = 1
        axes[i].plot(tl.time_s, tl.motion_score, color=COLORS["motion"], lw=1)
        axes[i].set_ylabel("Motion\nscore", rotation=0, ha="right", va="center")
        i += 1
        if "object_score" in tl.columns:
            axes[i].plot(tl.time_s, tl.object_score, color=COLORS["ai"], lw=1)
            axes[i].set_ylabel("Object\nscore", rotation=0, ha="right", va="center")
            i += 1
        for m in lv:
            axes[i].fill_between(tl.time_s, tl[f"level_{m}"], step="post", color=COLORS[m], alpha=0.6)
            axes[i].set_yticks([0, 1, 2])
            axes[i].set_yticklabels(["idle", "med", "high"])
            axes[i].set_ylabel(LABELS[m].split(" (")[0], rotation=0, ha="right", va="center")
            i += 1
        for ax in axes:
            ax.spines[["top", "right"]].set_visible(False)
        axes[0].set_title("Scene analysis and compression decisions over time "
                          "(idle = strongest compression)", loc="left", fontsize=11)
        axes[-1].set_xlabel("Time (s)")
        fig.tight_layout()
        fig.savefig(os.path.join(pdir, "timeline.png"), dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    make_plots(sys.argv[1])
