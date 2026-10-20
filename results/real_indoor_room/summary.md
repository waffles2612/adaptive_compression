# Results

Input: 768x432, 10.00 fps, 1394 frames (139.4 s)

## All runs

| method   |   base_qp |   size_mb |   bitrate_kbps |   storage_reduction_pct |   psnr |   ssim |   roi_psnr |   event_psnr |   idle_psnr |   vmaf |   det_f1 |   ms_per_frame |
|:---------|----------:|----------:|---------------:|------------------------:|-------:|-------:|-----------:|-------------:|------------:|-------:|---------:|---------------:|
| fixed    |        22 |     3.544 |        203.374 |                   0     | 41.13  |  0.987 |     40.589 |       41.062 |      41.359 | 90.523 |        1 |          1.653 |
| fixed    |        27 |     1.984 |        113.851 |                   0     | 39.779 |  0.981 |     38.31  |       39.669 |      40.165 | 88.031 |        1 |          1.562 |
| fixed    |        32 |     1.091 |         62.596 |                   0     | 37.619 |  0.967 |     35.361 |       37.484 |      38.095 | 83.498 |        1 |          1.474 |
| fixed    |        37 |     0.638 |         36.64  |                   0     | 35.353 |  0.947 |     32.588 |       35.252 |      35.705 | 76.146 |        1 |          1.442 |
| motion   |        22 |     3.222 |        184.892 |                   9.088 | 40.693 |  0.985 |     39.898 |       40.605 |      40.998 | 89.954 |        1 |          4.465 |
| motion   |        27 |     1.763 |        101.169 |                  11.14  | 38.984 |  0.975 |     37.225 |       38.884 |      39.33  | 86.581 |        1 |          4.367 |
| motion   |        32 |     0.978 |         56.105 |                  10.37  | 36.698 |  0.958 |     34.317 |       36.588 |      37.084 | 80.659 |        1 |          4.313 |
| motion   |        37 |     0.57  |         32.686 |                  10.79  | 34.284 |  0.934 |     31.529 |       34.209 |      34.542 | 71.287 |        1 |          4.307 |
| ai_qp    |        22 |     3.459 |        198.51  |                   2.392 | 41.009 |  0.987 |     40.589 |       41.062 |      40.836 | 90.329 |        1 |         25.32  |
| ai_qp    |        27 |     1.923 |        110.367 |                   3.061 | 39.489 |  0.979 |     38.31  |       39.669 |      38.942 | 87.462 |        1 |         25.282 |
| ai_qp    |        32 |     1.057 |         60.645 |                   3.117 | 37.277 |  0.964 |     35.361 |       37.484 |      36.656 | 82.401 |        1 |         25.198 |
| ai_qp    |        37 |     0.619 |         35.509 |                   3.087 | 34.971 |  0.943 |     32.588 |       35.252 |      34.153 | 74.325 |        1 |         25.161 |
| ai       |        22 |     3.108 |        178.336 |                  12.312 | 31.905 |  0.931 |     40.457 |       30.887 |      40.833 | 59.569 |        1 |         37.381 |
| ai       |        27 |     1.735 |         99.556 |                  12.556 | 31.685 |  0.925 |     38.236 |       30.73  |      38.947 | 57.283 |        1 |         37.344 |
| ai       |        32 |     0.975 |         55.951 |                  10.616 | 31.27  |  0.916 |     35.323 |       30.423 |      36.66  | 53.323 |        1 |         36.174 |
| ai       |        37 |     0.578 |         33.163 |                   9.49  | 30.654 |  0.902 |     32.575 |       29.98  |      34.165 | 47.259 |        1 |         36.612 |


## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)

| method   |   BD-rate psnr (%) |   BD-rate ssim (%) |   BD-rate roi_psnr (%) |   BD-rate event_psnr (%) |
|:---------|-------------------:|-------------------:|-----------------------:|-------------------------:|
| motion   |               12.6 |               15.2 |                   10.7 |                     12.1 |
| ai_qp    |                5.6 |                5.7 |                   -3   |                     -3   |
| ai       |              nan   |              nan   |                  -10.2 |                    nan   |


Notes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR split frames into activity vs. empty periods (ground truth if an events file is given). det_f1 compares detections on the decoded video with detections on the original (all objects, including parked vehicles). storage_reduction_pct compares file size with fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.
