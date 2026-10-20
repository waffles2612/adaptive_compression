# Results

Input: 960x540, 15.00 fps, 1138 frames (75.9 s)

## All runs

| method   |   base_qp |   size_mb |   bitrate_kbps |   storage_reduction_pct |   psnr |   ssim |   roi_psnr |   event_psnr |   idle_psnr |   vmaf |   det_f1 |   ms_per_frame |
|:---------|----------:|----------:|---------------:|------------------------:|-------:|-------:|-----------:|-------------:|------------:|-------:|---------:|---------------:|
| fixed    |        22 |     6.252 |        659.313 |                   0     | 39.584 |  0.971 |     38.93  |       39.599 |      39.528 | 93.125 |    0.993 |          4.206 |
| fixed    |        27 |     2.845 |        300.005 |                   0     | 37.782 |  0.953 |     36.825 |       37.791 |      37.747 | 87.909 |    0.993 |          4.039 |
| fixed    |        32 |     1.419 |        149.641 |                   0     | 35.679 |  0.928 |     34.242 |       35.67  |      35.716 | 79.764 |    0.993 |          3.907 |
| fixed    |        37 |     0.791 |         83.36  |                   0     | 33.764 |  0.898 |     31.608 |       33.726 |      33.917 | 68.984 |    0.978 |          3.602 |
| motion   |        22 |     6.074 |        640.53  |                   2.849 | 39.447 |  0.97  |     38.778 |       39.463 |      39.386 | 92.834 |    0.993 |          8.09  |
| motion   |        27 |     2.769 |        291.936 |                   2.69  | 37.584 |  0.951 |     36.592 |       37.591 |      37.556 | 87.254 |    0.993 |          7.884 |
| motion   |        32 |     1.38  |        145.54  |                   2.741 | 35.454 |  0.924 |     33.97  |       35.446 |      35.485 | 78.596 |    0.993 |          7.784 |
| motion   |        37 |     0.769 |         81.071 |                   2.746 | 33.507 |  0.894 |     31.303 |       33.472 |      33.641 | 67.264 |    0.978 |          7.71  |
| ai_qp    |        22 |     6.189 |        652.606 |                   1.017 | 39.533 |  0.971 |     38.93  |       39.599 |      39.288 | 93.017 |    0.993 |         24.103 |
| ai_qp    |        27 |     2.82  |        297.384 |                   0.874 | 37.704 |  0.952 |     36.825 |       37.791 |      37.384 | 87.647 |    0.993 |         23.895 |
| ai_qp    |        32 |     1.406 |        148.274 |                   0.914 | 35.587 |  0.926 |     34.242 |       35.67  |      35.281 | 79.23  |    0.993 |         23.774 |
| ai_qp    |        37 |     0.783 |         82.513 |                   1.015 | 33.655 |  0.896 |     31.608 |       33.726 |      33.392 | 68.214 |    0.978 |         23.76  |
| ai       |        22 |     4.494 |        473.905 |                  28.121 | 31.112 |  0.882 |     38.739 |       30.247 |      39.269 | 55.778 |    0.993 |         40.83  |
| ai       |        27 |     2.225 |        234.664 |                  21.78  | 30.871 |  0.872 |     36.719 |       30.075 |      37.319 | 52.307 |    0.993 |         45.639 |
| ai       |        32 |     1.171 |        123.513 |                  17.461 | 30.471 |  0.859 |     34.21  |       29.785 |      35.131 | 46.838 |    0.993 |         45.329 |
| ai       |        37 |     0.676 |         71.311 |                  14.453 | 29.923 |  0.843 |     31.58  |       29.363 |      33.191 | 39.808 |    0.993 |         40.434 |


## BD-rate vs. fixed H.264 (negative = fewer bits for the same quality)

| method   |   BD-rate psnr (%) |   BD-rate ssim (%) |   BD-rate roi_psnr (%) |   BD-rate event_psnr (%) |
|:---------|-------------------:|-------------------:|-----------------------:|-------------------------:|
| motion   |                4.5 |                5.4 |                    4   |                      4.4 |
| ai_qp    |                2   |                2.5 |                   -0.9 |                     -0.9 |
| ai       |              nan   |              nan   |                  -17.8 |                    nan   |


Notes: PSNR/SSIM are on luma over all frames. ROI-PSNR is measured only inside moving objects (people, moving vehicles) detected on the original video. Event/Idle PSNR split frames into activity vs. empty periods (ground truth if an events file is given). det_f1 compares detections on the decoded video with detections on the original (all objects, including parked vehicles). storage_reduction_pct compares file size with fixed H.264 at the same base QP; BD-rate compares at equal quality and is the fairer number.
