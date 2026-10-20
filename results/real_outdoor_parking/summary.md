# Results

Input: 768x432, 12.00 fps, 647 frames (53.9 s)

## All runs

| method   |   base_qp |   size_mb |   bitrate_kbps |   storage_reduction_pct |   psnr |   ssim |   roi_psnr |   event_psnr |   idle_psnr |   vmaf |   det_f1 |   ms_per_frame |
|:---------|----------:|----------:|---------------:|------------------------:|-------:|-------:|-----------:|-------------:|------------:|-------:|---------:|---------------:|
| fixed    |        22 |     1.109 |        164.516 |                   0     | 42.676 |  0.984 |     38.471 |       42.592 |      42.73  | 93.734 |    0.941 |          1.695 |
| fixed    |        27 |     0.477 |         70.776 |                   0     | 41.194 |  0.981 |     35.661 |       40.944 |      41.363 | 90.122 |    0.941 |          1.83  |
| fixed    |        32 |     0.253 |         37.475 |                   0     | 39.563 |  0.976 |     32.578 |       39.124 |      39.873 | 84.4   |    0.866 |          1.543 |
| fixed    |        37 |     0.154 |         22.784 |                   0     | 37.477 |  0.97  |     29.551 |       36.929 |      37.872 | 75.294 |    0.831 |          1.646 |
| motion   |        22 |     0.871 |        129.275 |                  21.421 | 42.112 |  0.983 |     38.177 |       42.18  |      42.069 | 92.493 |    0.941 |          4.872 |
| motion   |        27 |     0.405 |         60.058 |                  15.143 | 40.68  |  0.979 |     35.269 |       40.592 |      40.737 | 87.524 |    0.923 |          4.792 |
| motion   |        32 |     0.22  |         32.63  |                  12.929 | 38.733 |  0.973 |     32.169 |       38.607 |      38.817 | 79.543 |    0.8   |          4.309 |
| motion   |        37 |     0.135 |         19.995 |                  12.238 | 36.252 |  0.965 |     29.114 |       36.161 |      36.311 | 65.878 |    0.733 |          4.923 |
| ai_qp    |        22 |     0.979 |        145.224 |                  11.727 | 42.347 |  0.983 |     38.471 |       42.592 |      42.196 | 93.003 |    0.941 |         35.142 |
| ai_qp    |        27 |     0.439 |         65.132 |                   7.974 | 40.882 |  0.979 |     35.661 |       40.944 |      40.843 | 88.446 |    0.941 |         34.613 |
| ai_qp    |        32 |     0.235 |         34.941 |                   6.764 | 39.029 |  0.974 |     32.578 |       39.124 |      38.969 | 81.168 |    0.866 |         34.651 |
| ai_qp    |        37 |     0.144 |         21.364 |                   6.232 | 36.669 |  0.967 |     29.551 |       36.929 |      36.508 | 68.985 |    0.831 |         34.672 |
| ai       |        22 |     0.822 |        121.991 |                  25.848 | 36.41  |  0.967 |     38.402 |       33.109 |      42.193 | 70.714 |    0.909 |         40.3   |
| ai       |        27 |     0.397 |         58.85  |                  16.85  | 35.991 |  0.964 |     35.637 |       32.892 |      40.844 | 66.5   |    0.87  |         40.795 |
| ai       |        32 |     0.221 |         32.83  |                  12.396 | 35.318 |  0.96  |     32.614 |       32.571 |      38.986 | 59.701 |    0.896 |         40.255 |
| ai       |        37 |     0.137 |         20.26  |                  11.076 | 34.264 |  0.954 |     29.51  |       32.166 |      36.492 | 48.919 |    0.825 |         40.443 |


## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)

| method   |   BD-rate psnr (%) |   BD-rate ssim (%) |   BD-rate roi_psnr (%) |   BD-rate event_psnr (%) |
|:---------|-------------------:|-------------------:|-----------------------:|-------------------------:|
| motion   |                8.8 |               15.8 |                   -7.4 |                     -0.7 |
| ai_qp    |                8   |               12.2 |                   -7.7 |                     -7.7 |
| ai       |              nan   |              nan   |                  -15.2 |                    nan   |


Notes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR split frames into activity vs. empty periods (ground truth if an events file is given). det_f1 compares detections on the decoded video with detections on the original (all objects, including parked vehicles). storage_reduction_pct compares file size with fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.
