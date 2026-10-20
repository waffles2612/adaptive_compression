# Results

Input: 720x404, 15.00 fps, 981 frames (65.4 s)

## All runs

| method   |   base_qp |   size_mb |   bitrate_kbps |   storage_reduction_pct |   psnr |   ssim |   roi_psnr |   event_psnr |   idle_psnr |   vmaf |   det_f1 |   ms_per_frame |
|:---------|----------:|----------:|---------------:|------------------------:|-------:|-------:|-----------:|-------------:|------------:|-------:|---------:|---------------:|
| fixed    |        22 |     6.397 |        782.448 |                   0     | 38.511 |  0.984 |     38.27  |       38.439 |      38.993 | 92.377 |    0.991 |          1.983 |
| fixed    |        27 |     3.483 |        426.095 |                   0     | 35.67  |  0.969 |     35.35  |       35.594 |      36.183 | 89.098 |    0.98  |          1.924 |
| fixed    |        32 |     1.941 |        237.457 |                   0     | 32.803 |  0.944 |     32.225 |       32.691 |      33.582 | 83.493 |    0.967 |          1.924 |
| fixed    |        37 |     1.112 |        135.97  |                   0     | 29.824 |  0.896 |     29.202 |       29.743 |      30.365 | 73.974 |    0.959 |          1.938 |
| motion   |        22 |     6.09  |        744.905 |                   4.798 | 37.95  |  0.982 |     38.008 |       38.024 |      37.518 | 91.969 |    0.993 |          4.852 |
| motion   |        27 |     3.299 |        403.557 |                   5.289 | 35.077 |  0.965 |     35.046 |       35.24  |      34.176 | 88.251 |    0.985 |          4.726 |
| motion   |        32 |     1.812 |        221.708 |                   6.632 | 32.047 |  0.934 |     31.897 |       32.238 |      31.008 | 81.698 |    0.961 |          4.721 |
| motion   |        37 |     1.027 |        125.677 |                   7.57  | 29.032 |  0.879 |     28.854 |       29.242 |      27.902 | 70.878 |    0.954 |          4.686 |
| ai_qp    |        22 |     6.243 |        763.681 |                   2.398 | 38.155 |  0.982 |     38.27  |       38.439 |      36.704 | 92.102 |    0.991 |         19.685 |
| ai_qp    |        27 |     3.394 |        415.21  |                   2.555 | 35.192 |  0.966 |     35.35  |       35.594 |      33.276 | 88.45  |    0.98  |         19.633 |
| ai_qp    |        32 |     1.872 |        229.034 |                   3.547 | 32.218 |  0.936 |     32.225 |       32.691 |      30.052 | 82.131 |    0.967 |         19.604 |
| ai_qp    |        37 |     1.067 |        130.517 |                   4.011 | 29.249 |  0.884 |     29.202 |       29.743 |      27.012 | 71.784 |    0.959 |         19.548 |
| ai       |        22 |     5.249 |        642.033 |                  17.946 | 23.433 |  0.748 |     38.012 |       22.819 |      36.704 | 50.667 |    0.974 |         30.209 |
| ai       |        27 |     2.873 |        351.42  |                  17.526 | 23.314 |  0.736 |     35.201 |       22.732 |      33.276 | 48.27  |    0.967 |         31.219 |
| ai       |        32 |     1.559 |        190.718 |                  19.683 | 23.074 |  0.714 |     32.118 |       22.552 |      30.052 | 43.99  |    0.958 |         30.402 |
| ai       |        37 |     0.86  |        105.146 |                  22.67  | 22.672 |  0.679 |     29.099 |       22.255 |      27.012 | 37.489 |    0.956 |         31.34  |


## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)

| method   |   BD-rate psnr (%) |   BD-rate ssim (%) |   BD-rate roi_psnr (%) |   BD-rate event_psnr (%) |
|:---------|-------------------:|-------------------:|-----------------------:|-------------------------:|
| motion   |                7.5 |                7.5 |                   -0.2 |                      2.2 |
| ai_qp    |                7.4 |                7.3 |                   -3.1 |                     -3.1 |
| ai       |              nan   |              nan   |                  -16.8 |                    nan   |


Notes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR split frames into activity vs. empty periods (ground truth if an events file is given). det_f1 compares detections on the decoded video with detections on the original (all objects, including parked vehicles). storage_reduction_pct compares file size with fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.
