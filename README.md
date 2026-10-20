# Adaptive Video Compression for CCTV — Fixed vs. Motion-based vs. AI-based H.264

Implementation of the project *"Comparative Analysis of Adaptive Video Compression
Techniques for CCTV Surveillance"* (Riya Samuel, 23MID0150, Advanced Data Compression Techniques).

It implements the pipeline from slide 4 for each approach on slide 5, and the
evaluation strategy from slide 10:

```
CCTV video → scene/activity analysis → importance estimation → compression decision
           → adaptive H.264 (x264) encoding → compressed video → storage & quality evaluation
```

| Method (`--methods`) | Slide | What decides the compression |
|---|---|---|
| `fixed`  | 01 Fixed H.264 | One QP for the whole video (baseline) |
| `motion` | 02 Motion-based adaptive | Background-subtraction activity score → QP per 1-s segment |
| `ai_qp`  | 03 AI-based adaptive (temporal only) | YOLOv8 object detection → semantic importance → QP per segment |
| `ai`     | 03 AI-based adaptive (QP + ROI) | as `ai_qp`, plus the background outside detected objects is smoothed so bits go to the objects |
| `hybrid` | slide 9 "motion analysis: optional" | AI and motion levels fused (highest importance wins) + ROI |

---

## 1. Setup

Requirements: Python 3.9+, and **FFmpeg with libx264** on your PATH.

```bash
# FFmpeg:  Ubuntu: sudo apt install ffmpeg   |  macOS: brew install ffmpeg
#          Windows: download a "full" build from ffmpeg.org / gyan.dev and add its bin/ folder to PATH
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # numpy, opencv, pandas, matplotlib, ultralytics (YOLOv8 + PyTorch)
```

The YOLOv8 weights (`yolov8n.pt`, 6 MB) download automatically on first run. Everything runs on CPU;
an NVIDIA GPU makes the AI analysis much faster but is not needed.

## 2. Quick start (reproduces the included results)

```bash
# a) get OpenCV's sample pedestrian clip
curl -L -o data/vtest.avi https://raw.githubusercontent.com/opencv/opencv/master/samples/data/vtest.avi

# b) turn it into a realistic CCTV test clip: long empty periods + two activity periods
python make_test_clip.py --source data/vtest.avi --out data/cctv_test.mp4
#    -> data/cctv_test.mp4 (135 s) and data/cctv_test.mp4.events.json (ground-truth event times)

# c) run the full comparison (≈30-40 min on a 2-core CPU, much less on a laptop/GPU)
python run_experiment.py --input data/cctv_test.mp4 --out results/cctv_test
```

Outputs in `results/cctv_test/`:

| File | Contents |
|---|---|
| `summary.md` | results table + **BD-rate** of each method vs. the fixed baseline |
| `results.csv` | every metric for every (method, QP) |
| `plots/rate_quality_curves.png` | bitrate vs. PSNR / SSIM / ROI-PSNR / detection F1 |
| `plots/storage_by_qp.png` | file size per method at each QP |
| `plots/cost_vs_saving.png` | processing time vs. storage saving |
| `plots/timeline.png` | what each analyser saw over time and the QP decisions it made |
| `encodes/*.mp4` | the compressed videos (open them to compare visually) |
| `analysis.json`, `timeline.csv` | cached per-frame motion scores and detections |

Useful flags: `--reuse` (skip work already done), `--qps 22 27 32 37`, `--methods fixed motion`,
`--preset veryfast` (faster encodes), `--skip-detection-eval` (much faster),
`--eval-model yolov8s.pt` (see Limitations). `python run_experiment.py -h` lists all options.

## 3. Using real CCTV footage

Any video file works: `python run_experiment.py --input my_camera.mp4 --out results/my_camera`.
Good public surveillance datasets for the report:

* **CDnet 2014** (changedetection.net) — fixed-camera surveillance clips in categories such as
  *baseline*, *lowFramerate*, *nightVideos*, *badWeather*, *intermittentObjectMotion*. Ideal for
  testing robustness (noise, rain, night, objects that stop moving).
* **VIRAT Video Dataset** — outdoor surveillance (parking lots, streets) with people and vehicles.
* **PETS 2009** — multi-camera pedestrian surveillance.

If you know when the real events happen, give them as ground truth so Event/Idle-PSNR are exact:
create `my_camera.mp4.events.json` containing `[[start_s, end_s], ...]` (or pass `--events file.json`).

**Calibrate thresholds per camera:** run once, open `plots/timeline.png`, and check that idle periods
have motion score below `--motion-low` and events exceed `--motion-high` (defaults 0.002 / 0.01 = 0.2 % /
1 % of pixels moving). Noisy night footage usually needs higher motion thresholds; the AI method is much
less sensitive to this.

### Results on the included test clip (135 s, 768×576, 10 fps, 67 % idle)

BD-rate vs. fixed H.264 (negative = fewer bits for the same quality):

| Method | Storage saved at same QP | BD-rate, ROI-PSNR (objects) | BD-rate, whole-frame PSNR | Detection F1 (QP 27) | Processing |
|---|---|---|---|---|---|
| Fixed H.264 | — | — | — | 0.954 | 17 ms/frame |
| Motion-based | 16–24 % | **−19 %** | +25 % | 0.949 | 31 ms/frame |
| AI (QP only) | 15–22 % | **−20 %** | +24 % | 0.950 | 80 ms/frame |
| AI (QP + ROI) | 39–44 % | **−40 %** | n/a (background deliberately degraded) | 0.896 | 82 ms/frame |

Reading it:
* Both adaptive methods keep the people at the same quality as the baseline while cutting storage
  by ~20 %; the cost is lower quality in empty periods (hence worse whole-frame PSNR).
* On this clip, motion and AI make the **same temporal decisions** (see `plots/timeline.png`), so
  AI's extra ~4× computation buys nothing for QP-only adaptation. AI's advantage appears when it also
  works **spatially** (ROI): ~40 % saving at equal object quality, but parked vehicles lose detail
  (detection F1 −0.06). `hybrid` equals `ai` here because there is no motion without objects in this
  clip; its curves sit underneath the `ai` ones.
* AI needed static-object suppression to work at all (Section 4) — a practical finding worth reporting.

## 2b. Real surveillance videos (Table III) — one command

```bash
python run_real_videos.py            # all four clips (≈30–60 min on a laptop)
python run_real_videos.py --fast     # quicker x264 preset
python run_real_videos.py indoor_room   # one clip: outdoor_parking, indoor_room, retail_aisle, industrial
```

Downloads four fixed-camera clips from Intel's public sample-videos set (CC BY 4.0), converts
them to lossless CCTV-style references in `data/real/`, runs fixed / motion / AI (QP only) /
AI + ROI at QPs 22–37, and prints Table III (storage saving at QP 27 and BD-rate on ROI-PSNR).
The table is also saved to `results/table3.csv`; full results are in `results/real_<clip>/`.
If it stops, run it again — finished work is reused.

---

## 4. How it works

### Code map
```
acc/video_io.py    read frames (OpenCV) · encode with FFmpeg/libx264 through a pipe
acc/motion.py      02 motion analysis: MOG2 background subtraction (or frame differencing) → activity score
acc/detector.py    03 AI analysis: YOLOv8 detections → semantic importance; static-object suppression
acc/controller.py  importance score → level (idle / medium / high) → QP per segment → x264 zones
acc/roi.py         spatial ROI for the AI method (background smoothing outside objects)
acc/metrics.py     size, bitrate, PSNR, SSIM, ROI-PSNR, event/idle PSNR, VMAF, detection P/R/F1, BD-rate
run_experiment.py  runs everything, writes results.csv / summary.md
plots.py           figures
make_test_clip.py  builds the idle+activity test clip
```

### Compression decision (all adaptive methods share it)
1. Each analyser gives a **score per frame** (motion: fraction of moving pixels; AI: max of
   class-weight × confidence over detected objects; person = 1.0, vehicles = 0.8, bags = 0.6).
2. Scores are grouped into **1-second segments** (max score per segment) and mapped to a level:
   idle (0), medium (1), high (2).
3. **Dilation**: each segment takes the highest level of its neighbours, so the start and end of every
   event (pre-roll / post-roll) are kept at full quality.
4. Level → QP: `QP = base_QP + offset`, offsets idle **+10**, medium **+4**, high **0**
   (`--idle-offset`, `--medium-offset`). +6 QP ≈ half the bitrate in H.264.
5. The per-frame QP plan is run-length encoded into x264 **zones** (`start,end,q=QP/…`) and passed to
   libx264 in constant-QP mode. The fixed baseline uses the same encoder with no zones.

All methods receive the **same raw frames through the same encoder settings** (preset, fixed 2-s GOP
like a CCTV recorder), so differences come only from the compression decisions.

### AI method details
* **Detector stride**: YOLO runs 5×/s (`--det-per-sec`) and boxes are held in between — ~60 ms/frame on CPU.
* **Static-object suppression**: parked cars are detected in every frame of an empty scene. Without
  handling this, the AI method would keep empty footage at high quality and save nothing. Objects that
  stay in the same place for ≥5 s (`--static-sec`) are treated as background. People are never
  suppressed (a person standing still/loitering is important).
* **Spatial ROI (`ai`, `hybrid`)**: x264 can lower QP inside a region, but per-frame QP maps cannot be
  set from the FFmpeg command line (its `addroi` filter only takes fixed regions). The equivalent
  pre-filtering technique is used instead: outside the enlarged boxes of moving objects the frame is
  Gaussian-smoothed (`--roi-sigma`) with a feathered edge, so the encoder spends almost nothing on
  background texture and noise, while the objects are untouched. `ai_qp` is the same method without
  this step, so the report can separate the temporal and the spatial contribution.

### Metrics (slide 10)
* **Compression**: file size, bitrate, compression ratio (vs raw YUV 4:2:0), storage reduction vs.
  fixed at the same base QP.
* **Quality**: PSNR and SSIM on luma over all frames; **ROI-PSNR** inside moving objects (what the
  operator needs); **Event-PSNR / Idle-PSNR** over activity vs. empty periods; VMAF if your FFmpeg has
  libvmaf (column is skipped otherwise).
* **Surveillance utility**: YOLO is run on the decoded video and matched (IoU ≥ 0.5) to detections on
  the original → precision / recall / F1.
* **System**: analysis time + encode time, ms per frame.
* **BD-rate** (Bjøntegaard): average bitrate difference vs. the fixed baseline *at equal quality*,
  computed from the 4-QP curves. This is the fair single number for "how much storage does this save";
  negative = saves bits.

---

## 5. Limitations (worth stating in the report)
* Detection F1 uses the same YOLO model that drives the AI method as the reference, which can favour
  it. Use `--eval-model yolov8s.pt` (a different, larger model) or dataset ground-truth annotations
  for a stricter test.
* The ROI smoothing lowers whole-frame PSNR/SSIM **by design** (the background is deliberately
  degraded). Judge it with ROI-PSNR, Event-PSNR and detection F1, and look at the videos.
* Smoothing also degrades parked vehicles, which shows up as a lower detection F1 (reference includes
  all objects). If static objects matter (e.g. number plates in a car park), use `ai_qp` or lower
  `--roi-sigma`.
* The test clip is assembled from a real pedestrian video with a synthetic empty background; savings
  depend strongly on how much of the footage is idle and how noisy the camera is. Confirm on real
  datasets (Section 3).
* Thresholds and QP offsets are hand-set; they are the main knobs to study in a sensitivity analysis.

## 6. Possible extensions
* True per-macroblock QP maps via the x264 C API (`quant_offsets`) or NVENC emphasis maps.
* H.265/HEVC (`libx265`, also supports zones) for a codec comparison.
* Lower frame rate for idle periods (many NVRs do this) on top of higher QP.
* Real-time version: analyse a live RTSP stream and adjust the encoder per GOP.
