# Results

Input: 960x540, 15.00 fps, 221 frames (14.7 s)

## All runs

| method   |   base_qp |   size_mb |   bitrate_kbps |   storage_reduction_pct |   psnr |   ssim |   roi_psnr |   event_psnr |   idle_psnr |   vmaf |   det_f1 |   ms_per_frame |
|:---------|----------:|----------:|---------------:|------------------------:|-------:|-------:|-----------:|-------------:|------------:|-------:|---------:|---------------:|
| fixed    |        22 |     0.62  |        336.526 |                   0     | 40.55  |  0.971 |     38.786 |       40.517 |      40.842 | 91.682 |    0.982 |          3.634 |
| fixed    |        27 |     0.305 |        165.423 |                   0     | 39.073 |  0.959 |     36.308 |       39.035 |      39.416 | 87.468 |    0.881 |          3.832 |
| fixed    |        32 |     0.162 |         88.051 |                   0     | 37.163 |  0.941 |     33.365 |       37.103 |      37.719 | 80.583 |    0.857 |          3.411 |
| fixed    |        37 |     0.091 |         49.419 |                   0     | 35.206 |  0.917 |     30.506 |       35.122 |      36.005 | 68.124 |    0.857 |          3.423 |
| motion   |        22 |     0.543 |        295.034 |                  12.329 | 40.099 |  0.967 |     38.658 |       40.152 |      39.664 | 90.64  |    0.966 |          7.925 |
| motion   |        27 |     0.267 |        144.864 |                  12.428 | 38.39  |  0.953 |     36.129 |       38.472 |      37.736 | 85.386 |    0.867 |          7.897 |
| motion   |        32 |     0.142 |         76.984 |                  12.569 | 36.474 |  0.933 |     33.185 |       36.537 |      35.968 | 76.302 |    0.821 |          8.207 |
| motion   |        37 |     0.08  |         43.386 |                  12.209 | 34.626 |  0.908 |     30.318 |       34.665 |      34.31  | 61.062 |    0.83  |          8.244 |
| ai_qp    |        22 |     0.602 |        326.676 |                   2.927 | 40.497 |  0.971 |     38.786 |       40.517 |      40.328 | 91.574 |    0.982 |         30.042 |
| ai_qp    |        27 |     0.296 |        160.835 |                   2.773 | 38.996 |  0.958 |     36.308 |       39.035 |      38.673 | 87.239 |    0.881 |         30.119 |
| ai_qp    |        32 |     0.158 |         85.689 |                   2.683 | 37.096 |  0.94  |     33.365 |       37.103 |      37.036 | 80.145 |    0.857 |         29.92  |
| ai_qp    |        37 |     0.089 |         48.074 |                   2.723 | 35.134 |  0.916 |     30.506 |       35.122 |      35.238 | 67.306 |    0.857 |         30.214 |
| ai       |        22 |     0.416 |        225.733 |                  32.922 | 33.73  |  0.893 |     38.574 |       33.363 |      39.923 | 41.358 |    0.893 |         55.991 |
| ai       |        27 |     0.221 |        120.041 |                  27.434 | 33.515 |  0.889 |     36.196 |       33.2   |      38.047 | 38.564 |    0.926 |         56.42  |
| ai       |        32 |     0.123 |         66.755 |                  24.186 | 33.051 |  0.882 |     33.336 |       32.811 |      35.966 | 33.67  |    0.793 |         58.936 |
| ai       |        37 |     0.072 |         39.154 |                  20.772 | 32.421 |  0.873 |     30.46  |       32.265 |      34.055 | 26.753 |    0.807 |         67.609 |


## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)

| method   |   BD-rate psnr (%) |   BD-rate ssim (%) |   BD-rate roi_psnr (%) |   BD-rate event_psnr (%) |
|:---------|-------------------:|-------------------:|-----------------------:|-------------------------:|
| motion   |                9.7 |               10.3 |                   -8.9 |                      5.2 |
| ai_qp    |               -0.3 |               -0.3 |                   -2.7 |                     -2.7 |
| ai       |              nan   |              nan   |                  -24.4 |                    nan   |


Notes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR split frames into activity vs. empty periods (ground truth if an events file is given). det_f1 compares detections on the decoded video with detections on the original (all objects, including parked vehicles). storage_reduction_pct compares file size with fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.
