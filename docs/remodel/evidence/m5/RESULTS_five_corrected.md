# Walmart M5 (Experiment A) results: stage `five_corrected`

Commit `91445b15d6647290de8375d5fe08a728a8d4bf30`, declaration `ecd18b01e12d`, selection `8b6067be83a4`; 375 runs, 350 complete, 25 not complete; wall 206 s, peak RSS 287 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 5/5 | 835.061 | 866.330 | 814.149 | 4.5485 | 69.225 | 0.906 | 30.207 | 31.062 | 2.0 | 11.2 |  | 0.20 |
| final | observed | fill_only | gated | 5/5 | 822.065 | 853.110 | 808.957 | 8.6681 | 58.640 | 0.916 | 24.678 | 55.562 | 1.4 | 10.2 | 0.45 | 4.05 |
| final | observed | fill_only | order_up_to | 5/5 | 856.001 | 882.262 | 715.248 | 2.2108 | 163.948 | 0.828 | 66.287 | 17.078 | 4.8 | 10.8 |  | 0.11 |
| final | observed | fill_only | periodic:1 | 5/5 | 837.321 | 867.922 | 806.495 | 4.0887 | 75.977 | 0.899 | 33.225 | 28.411 | 2.2 | 11.8 |  | 0.02 |
| final | observed | fill_only | reorder_point | 5/5 | 837.207 | 867.665 | 805.577 | 4.0530 | 75.980 | 0.899 | 33.226 | 28.121 | 2.2 | 10.8 |  | 0.02 |
| final | observed | lead_only | base_stock | 5/5 | 801.012 | 831.048 | 684.749 | 4.2548 | 158.421 | 0.828 | 65.705 | 27.716 | 3.6 | 11.4 |  | 0.19 |
| final | observed | lead_only | gated | 5/5 | 802.396 | 837.244 | 722.120 | 7.5927 | 147.929 | 0.843 | 58.829 | 45.268 | 3.0 | 10.2 | 0.45 | 2.14 |
| final | observed | lead_only | order_up_to | 5/5 | 828.786 | 854.027 | 587.645 | 2.3942 | 259.012 | 0.739 | 102.922 | 16.550 | 5.6 | 10.6 |  | 0.12 |
| final | observed | lead_only | periodic:1 | 5/5 | 801.012 | 831.048 | 684.749 | 4.2548 | 158.421 | 0.828 | 65.705 | 27.716 | 3.6 | 11.4 |  | 0.02 |
| final | observed | lead_only | reorder_point | 5/5 | 801.105 | 830.940 | 683.111 | 4.2214 | 158.995 | 0.827 | 65.904 | 27.409 | 3.6 | 10.2 |  | 0.02 |
| final | observed | mild_lead | base_stock | 5/5 | 802.302 | 838.470 | 715.734 | 3.7288 | 162.401 | 0.822 | 72.981 | 25.376 | 4.0 | 11.6 |  | 0.21 |
| final | observed | mild_lead | gated | 5/5 | 797.257 | 836.680 | 754.727 | 5.5225 | 136.532 | 0.857 | 54.778 | 36.529 | 3.4 | 11.0 | 0.42 | 2.26 |
| final | observed | mild_lead | order_up_to | 5/5 | 836.851 | 868.364 | 603.294 | 2.0321 | 285.306 | 0.724 | 117.018 | 15.704 | 5.4 | 10.6 |  | 0.11 |
| final | observed | mild_lead | periodic:1 | 5/5 | 802.302 | 838.470 | 715.734 | 3.7288 | 162.401 | 0.822 | 72.981 | 25.376 | 4.0 | 11.6 |  | 0.02 |
| final | observed | mild_lead | reorder_point | 5/5 | 802.429 | 838.397 | 713.978 | 3.6799 | 163.144 | 0.820 | 73.770 | 25.028 | 4.0 | 10.2 |  | 0.02 |
| final | observed | stable | base_stock | 5/5 | 773.255 | 803.298 | 749.597 | 4.2967 | 65.781 | 0.907 | 29.702 | 29.470 | 2.2 | 11.8 |  | 0.21 |
| final | observed | stable | gated | 5/5 | 772.211 | 802.394 | 753.728 | 4.4445 | 61.512 | 0.910 | 27.867 | 29.963 | 2.2 | 11.0 | 0.31 | 3.48 |
| final | observed | stable | order_up_to | 5/5 | 797.813 | 823.110 | 658.833 | 1.9873 | 157.314 | 0.830 | 64.676 | 15.705 | 4.8 | 11.0 |  | 0.11 |
| final | observed | stable | periodic:1 | 5/5 | 773.255 | 803.298 | 749.597 | 4.2967 | 65.781 | 0.907 | 29.702 | 29.470 | 2.2 | 11.8 |  | 0.02 |
| final | observed | stable | reorder_point | 5/5 | 773.166 | 803.008 | 748.361 | 4.2536 | 65.781 | 0.907 | 29.702 | 29.109 | 2.2 | 10.6 |  | 0.02 |
| final | observed | uncertain | base_stock | 5/5 | 878.848 | 909.815 | 740.522 | 3.8442 | 185.963 | 0.802 | 73.040 | 26.955 | 3.8 | 11.8 |  | 0.20 |
| final | observed | uncertain | gated | 5/5 | 856.396 | 909.441 | 915.277 | 11.7480 | 107.694 | 0.879 | 31.276 | 68.191 | 2.4 | 9.8 | 0.48 | 1.63 |
| final | observed | uncertain | order_up_to | 5/5 | 894.816 | 916.988 | 611.816 | 2.2172 | 285.100 | 0.719 | 108.809 | 16.637 | 5.2 | 10.6 |  | 0.11 |
| final | observed | uncertain | periodic:1 | 5/5 | 880.243 | 910.558 | 727.296 | 3.6547 | 197.223 | 0.794 | 76.296 | 25.726 | 3.6 | 11.8 |  | 0.02 |
| final | observed | uncertain | reorder_point | 5/5 | 880.437 | 910.697 | 727.216 | 3.6183 | 197.223 | 0.794 | 76.296 | 25.428 | 3.6 | 11.2 |  | 0.02 |
| val1 | observed | fill_only | base_stock | 4/5 | 493.770 | 521.671 | 434.707 | 7.2204 | 58.302 | 0.889 | 16.228 | 46.993 | 1.8 | 9.5 |  | 0.19 |
| val1 | observed | fill_only | gated | 4/5 | 493.579 | 521.350 | 434.086 | 7.8951 | 57.380 | 0.892 | 15.871 | 52.053 | 1.8 | 8.2 | 0.33 | 3.00 |
| val1 | observed | fill_only | order_up_to | 4/5 | 494.256 | 511.971 | 322.782 | 5.5736 | 116.604 | 0.781 | 34.398 | 29.603 | 3.0 | 8.5 |  | 0.09 |
| val1 | observed | fill_only | periodic:1 | 4/5 | 495.458 | 522.246 | 429.040 | 6.9647 | 59.682 | 0.885 | 16.608 | 44.692 | 1.8 | 10.0 |  | 0.02 |
| val1 | observed | fill_only | reorder_point | 4/5 | 496.967 | 523.626 | 428.460 | 6.9409 | 61.077 | 0.884 | 16.888 | 44.608 | 1.8 | 9.2 |  | 0.02 |
| val1 | observed | lead_only | base_stock | 4/5 | 457.214 | 485.037 | 374.933 | 6.6278 | 82.064 | 0.825 | 28.219 | 40.815 | 2.2 | 8.8 |  | 0.18 |
| val1 | observed | lead_only | gated | 4/5 | 456.357 | 492.855 | 435.627 | 7.7629 | 69.665 | 0.854 | 21.947 | 49.461 | 1.5 | 9.0 | 0.42 | 1.85 |
| val1 | observed | lead_only | order_up_to | 4/5 | 477.500 | 496.063 | 270.952 | 5.5621 | 156.809 | 0.706 | 68.294 | 29.762 | 3.8 | 8.5 |  | 0.09 |
| val1 | observed | lead_only | periodic:1 | 4/5 | 457.214 | 485.037 | 374.933 | 6.6278 | 82.064 | 0.825 | 28.219 | 40.815 | 2.2 | 8.8 |  | 0.02 |
| val1 | observed | lead_only | reorder_point | 4/5 | 457.192 | 485.015 | 374.933 | 6.6054 | 82.064 | 0.825 | 28.219 | 40.741 | 2.2 | 8.5 |  | 0.02 |
| val1 | observed | mild_lead | base_stock | 4/5 | 452.198 | 480.097 | 386.526 | 6.6563 | 65.503 | 0.856 | 19.622 | 40.870 | 2.0 | 9.2 |  | 0.19 |
| val1 | observed | mild_lead | gated | 4/5 | 448.350 | 482.110 | 434.349 | 7.8027 | 45.735 | 0.896 | 13.963 | 52.480 | 1.2 | 9.5 | 0.52 | 2.39 |
| val1 | observed | mild_lead | order_up_to | 4/5 | 470.981 | 489.323 | 283.486 | 5.3403 | 136.298 | 0.738 | 48.830 | 26.530 | 3.8 | 8.8 |  | 0.10 |
| val1 | observed | mild_lead | periodic:1 | 4/5 | 452.198 | 480.097 | 386.526 | 6.6563 | 65.503 | 0.856 | 19.622 | 40.870 | 2.0 | 9.2 |  | 0.02 |
| val1 | observed | mild_lead | reorder_point | 4/5 | 453.648 | 481.547 | 383.195 | 6.6787 | 70.261 | 0.852 | 20.579 | 40.944 | 2.2 | 8.2 |  | 0.02 |
| val1 | observed | stable | base_stock | 4/5 | 449.396 | 477.302 | 394.185 | 7.1439 | 54.561 | 0.893 | 15.405 | 46.335 | 1.8 | 9.0 |  | 0.19 |
| val1 | observed | stable | gated | 4/5 | 450.954 | 478.551 | 389.071 | 7.3400 | 59.277 | 0.896 | 15.938 | 49.539 | 2.0 | 9.5 | 0.27 | 2.18 |
| val1 | observed | stable | order_up_to | 4/5 | 464.456 | 482.159 | 295.264 | 5.4965 | 114.308 | 0.785 | 32.270 | 28.964 | 3.0 | 8.5 |  | 0.09 |
| val1 | observed | stable | periodic:1 | 4/5 | 449.396 | 477.302 | 394.185 | 7.1439 | 54.561 | 0.893 | 15.405 | 46.335 | 1.8 | 9.0 |  | 0.02 |
| val1 | observed | stable | reorder_point | 4/5 | 450.846 | 478.752 | 390.854 | 7.1663 | 59.319 | 0.889 | 16.362 | 46.408 | 2.0 | 8.5 |  | 0.02 |
| val1 | observed | uncertain | base_stock | 4/5 | 500.334 | 527.539 | 398.461 | 6.4040 | 97.967 | 0.833 | 27.291 | 41.631 | 2.2 | 9.2 |  | 0.17 |
| val1 | observed | uncertain | gated | 4/5 | 531.632 | 567.455 | 460.515 | 8.0473 | 115.594 | 0.796 | 33.128 | 65.986 | 2.5 | 7.0 | 0.50 | 1.67 |
| val1 | observed | uncertain | order_up_to | 4/5 | 504.800 | 521.851 | 280.915 | 5.4189 | 165.899 | 0.704 | 50.184 | 28.238 | 3.5 | 8.2 |  | 0.09 |
| val1 | observed | uncertain | periodic:1 | 4/5 | 500.286 | 527.086 | 393.915 | 6.2373 | 100.417 | 0.826 | 28.120 | 39.698 | 2.8 | 9.5 |  | 0.02 |
| val1 | observed | uncertain | reorder_point | 4/5 | 501.885 | 528.285 | 386.337 | 6.2627 | 107.326 | 0.821 | 29.377 | 39.765 | 2.8 | 8.8 |  | 0.02 |
| val2 | observed | fill_only | base_stock | 5/5 | 771.737 | 802.124 | 756.082 | 6.6999 | 66.672 | 0.923 | 30.763 | 54.613 | 1.8 | 10.8 |  | 0.20 |
| val2 | observed | fill_only | gated | 5/5 | 787.140 | 819.615 | 800.035 | 11.9996 | 49.611 | 0.936 | 20.234 | 96.218 | 1.2 | 8.8 | 0.48 | 4.01 |
| val2 | observed | fill_only | order_up_to | 5/5 | 779.769 | 800.309 | 632.469 | 3.3386 | 148.128 | 0.864 | 60.155 | 28.474 | 3.2 | 11.0 |  | 0.10 |
| val2 | observed | fill_only | periodic:1 | 5/5 | 773.241 | 802.721 | 747.050 | 6.2722 | 72.687 | 0.918 | 33.231 | 51.745 | 1.8 | 11.2 |  | 0.02 |
| val2 | observed | fill_only | reorder_point | 5/5 | 772.748 | 801.995 | 745.214 | 6.2023 | 72.687 | 0.918 | 33.231 | 51.175 | 1.8 | 10.8 |  | 0.02 |
| val2 | observed | lead_only | base_stock | 5/5 | 719.116 | 749.680 | 613.032 | 5.5908 | 159.462 | 0.802 | 83.345 | 45.631 | 3.6 | 9.8 |  | 0.19 |
| val2 | observed | lead_only | gated | 5/5 | 709.316 | 751.655 | 720.068 | 8.8718 | 107.842 | 0.836 | 60.101 | 70.994 | 2.6 | 9.8 | 0.51 | 2.07 |
| val2 | observed | lead_only | order_up_to | 5/5 | 746.382 | 766.090 | 481.303 | 3.2135 | 262.038 | 0.731 | 116.038 | 26.356 | 4.6 | 9.0 |  | 0.11 |
| val2 | observed | lead_only | periodic:1 | 5/5 | 719.116 | 749.680 | 613.032 | 5.5908 | 159.462 | 0.802 | 83.345 | 45.631 | 3.6 | 9.8 |  | 0.02 |
| val2 | observed | lead_only | reorder_point | 5/5 | 718.974 | 749.325 | 611.677 | 5.5071 | 159.462 | 0.802 | 83.345 | 44.953 | 3.6 | 8.8 |  | 0.02 |
| val2 | observed | mild_lead | base_stock | 5/5 | 706.914 | 737.625 | 642.030 | 5.6190 | 118.819 | 0.857 | 53.638 | 46.758 | 3.4 | 10.6 |  | 0.17 |
| val2 | observed | mild_lead | gated | 5/5 | 699.660 | 736.100 | 702.603 | 8.6642 | 80.899 | 0.878 | 43.219 | 69.576 | 1.8 | 10.6 | 0.54 | 2.37 |
| val2 | observed | mild_lead | order_up_to | 5/5 | 741.938 | 764.221 | 505.185 | 3.2613 | 246.826 | 0.750 | 105.077 | 27.254 | 4.6 | 9.6 |  | 0.10 |
| val2 | observed | mild_lead | periodic:1 | 5/5 | 706.914 | 737.625 | 642.030 | 5.6190 | 118.819 | 0.857 | 53.638 | 46.758 | 3.4 | 10.6 |  | 0.02 |
| val2 | observed | mild_lead | reorder_point | 5/5 | 706.880 | 737.421 | 640.675 | 5.5370 | 119.157 | 0.856 | 53.756 | 46.088 | 3.4 | 9.6 |  | 0.02 |
| val2 | observed | stable | base_stock | 5/5 | 691.442 | 722.661 | 683.345 | 6.6161 | 63.763 | 0.925 | 29.087 | 53.224 | 2.0 | 11.2 |  | 0.19 |
| val2 | observed | stable | gated | 5/5 | 691.638 | 723.427 | 687.707 | 7.2562 | 62.068 | 0.927 | 27.357 | 58.315 | 1.6 | 10.2 | 0.37 | 3.69 |
| val2 | observed | stable | order_up_to | 5/5 | 710.782 | 731.332 | 568.437 | 3.3052 | 143.227 | 0.866 | 58.747 | 27.642 | 3.2 | 11.0 |  | 0.11 |
| val2 | observed | stable | periodic:1 | 5/5 | 691.442 | 722.661 | 683.345 | 6.6161 | 63.763 | 0.925 | 29.087 | 53.224 | 2.0 | 11.2 |  | 0.02 |
| val2 | observed | stable | reorder_point | 5/5 | 691.300 | 722.305 | 681.980 | 6.5332 | 63.763 | 0.925 | 29.087 | 52.484 | 2.0 | 10.2 |  | 0.02 |
| val2 | observed | uncertain | base_stock | 5/5 | 764.456 | 793.652 | 690.240 | 6.3971 | 120.727 | 0.860 | 55.120 | 50.622 | 3.0 | 10.6 |  | 0.18 |
| val2 | observed | uncertain | gated | 5/5 | 784.441 | 817.510 | 745.262 | 9.0487 | 108.137 | 0.886 | 46.402 | 75.487 | 2.0 | 9.0 | 0.42 | 1.84 |
| val2 | observed | uncertain | order_up_to | 5/5 | 781.902 | 802.226 | 549.954 | 3.4823 | 232.775 | 0.770 | 102.761 | 28.150 | 4.6 | 10.6 |  | 0.11 |
| val2 | observed | uncertain | periodic:1 | 5/5 | 765.834 | 794.241 | 680.930 | 6.0546 | 127.492 | 0.854 | 58.481 | 47.937 | 3.2 | 11.0 |  | 0.02 |
| val2 | observed | uncertain | reorder_point | 5/5 | 765.270 | 793.331 | 678.222 | 5.9564 | 127.632 | 0.854 | 58.606 | 47.102 | 3.0 | 10.2 |  | 0.02 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 5 | -15.142 | [-32.863, +2.578] | [-45.323, +6.511] | 3 / 2 / 0 | 1.0 |
| final | observed | fill_only | periodic:1 | 5 | -15.256 | [-33.087, +2.361] | [-45.341, +6.293] | 3 / 2 / 0 | 1.0 |
| final | observed | fill_only | base_stock | 5 | -12.996 | [-29.247, +3.118] | [-39.805, +6.992] | 3 / 2 / 0 | 1.0 |
| final | observed | fill_only | order_up_to | 5 | -33.936 | [-69.024, +0.726] | [-97.902, +7.787] | 3 / 2 / 0 | 1.0 |
| final | observed | lead_only | reorder_point | 5 | +1.291 | [-1.445, +4.009] | [-2.693, +5.366] | 3 / 2 / 0 | 1.0 |
| final | observed | lead_only | periodic:1 | 5 | +1.385 | [-1.139, +3.972] | [-2.404, +5.232] | 2 / 3 / 0 | 1.0 |
| final | observed | lead_only | base_stock | 5 | +1.385 | [-1.146, +3.909] | [-2.404, +5.232] | 2 / 3 / 0 | 1.0 |
| final | observed | lead_only | order_up_to | 5 | -26.389 | [-46.816, -7.291] | [-59.408, -0.288] | 4 / 1 / 0 | 0.375 |
| final | observed | mild_lead | reorder_point | 5 | -5.172 | [-10.536, +0.191] | [-12.983, +3.107] | 3 / 2 / 0 | 1.0 |
| final | observed | mild_lead | periodic:1 | 5 | -5.045 | [-10.085, -0.004] | [-12.306, +1.788] | 3 / 2 / 0 | 1.0 |
| final | observed | mild_lead | base_stock | 5 | -5.045 | [-10.085, -0.004] | [-12.306, +2.816] | 3 / 2 / 0 | 1.0 |
| final | observed | mild_lead | order_up_to | 5 | -39.594 | [-68.787, -10.401] | [-87.424, -4.334] | 4 / 1 / 0 | 0.375 |
| final | observed | stable | reorder_point | 5 | -0.954 | [-2.290, +0.381] | [-3.025, +0.968] | 3 / 2 / 0 | 1.0 |
| final | observed | stable | periodic:1 | 5 | -1.044 | [-2.439, +0.209] | [-3.255, +0.798] | 3 / 2 / 0 | 1.0 |
| final | observed | stable | base_stock | 5 | -1.044 | [-2.372, +0.209] | [-3.255, +0.798] | 3 / 2 / 0 | 1.0 |
| final | observed | stable | order_up_to | 5 | -25.601 | [-45.289, -5.913] | [-59.727, -2.427] | 4 / 1 / 0 | 0.375 |
| final | observed | uncertain | reorder_point | 5 | -24.041 | [-44.518, -2.740] | [-59.144, +5.116] | 3 / 2 / 0 | 1.0 |
| final | observed | uncertain | periodic:1 | 5 | -23.847 | [-45.243, -3.573] | [-58.999, +5.455] | 3 / 2 / 0 | 1.0 |
| final | observed | uncertain | base_stock | 5 | -22.452 | [-42.361, -2.602] | [-56.278, +5.558] | 3 / 2 / 0 | 1.0 |
| final | observed | uncertain | order_up_to | 5 | -38.419 | [-72.762, -4.077] | [-96.017, +7.932] | 3 / 2 / 0 | 1.0 |
| val1 | observed | fill_only | reorder_point | 4 | -3.388 | [-7.955, +1.178] | [-10.286, +3.235] | 2 / 2 / 0 | 1.0 |
| val1 | observed | fill_only | periodic:1 | 4 | -1.879 | [-4.885, +1.127] | [-6.889, +3.130] | 2 / 2 / 0 | 1.0 |
| val1 | observed | fill_only | base_stock | 4 | -0.191 | [-2.646, +2.264] | [-4.505, +4.123] | 2 / 2 / 0 | 1.0 |
| val1 | observed | fill_only | order_up_to | 4 | -0.677 | [-6.535, +5.181] | [-8.862, +7.508] | 2 / 2 / 0 | 1.0 |
| val1 | observed | lead_only | reorder_point | 4 | -0.834 | [-3.497, +1.828] | [-4.952, +3.283] | 2 / 2 / 0 | 1.0 |
| val1 | observed | lead_only | periodic:1 | 4 | -0.857 | [-3.497, +1.783] | [-4.952, +3.238] | 2 / 2 / 0 | 1.0 |
| val1 | observed | lead_only | base_stock | 4 | -0.857 | [-3.497, +1.783] | [-4.952, +3.238] | 2 / 2 / 0 | 1.0 |
| val1 | observed | lead_only | order_up_to | 4 | -21.143 | [-29.357, -12.928] | [-32.353, -8.660] | 4 / 0 / 0 | 0.125 |
| val1 | observed | mild_lead | reorder_point | 4 | -5.298 | [-10.089, -0.867] | [-12.480, +0.871] | 3 / 1 / 0 | 0.625 |
| val1 | observed | mild_lead | periodic:1 | 4 | -3.849 | [-7.189, -0.508] | [-8.210, +0.871] | 3 / 1 / 0 | 0.625 |
| val1 | observed | mild_lead | base_stock | 4 | -3.849 | [-7.189, -0.508] | [-8.210, +0.871] | 3 / 1 / 0 | 0.625 |
| val1 | observed | mild_lead | order_up_to | 4 | -22.631 | [-33.035, -12.228] | [-41.067, -10.494] | 4 / 0 / 0 | 0.125 |
| val1 | observed | stable | reorder_point | 4 | +0.108 | [-1.165, +1.382] | [-1.859, +1.820] | 1 / 3 / 0 | 0.625 |
| val1 | observed | stable | periodic:1 | 4 | +1.558 | [-1.165, +4.281] | [-1.859, +6.169] | 1 / 3 / 0 | 0.625 |
| val1 | observed | stable | base_stock | 4 | +1.558 | [-1.025, +4.281] | [-1.859, +6.169] | 1 / 3 / 0 | 0.625 |
| val1 | observed | stable | order_up_to | 4 | -13.502 | [-21.961, -5.043] | [-27.863, +0.859] | 3 / 1 / 0 | 0.625 |
| val1 | observed | uncertain | reorder_point | 4 | +29.747 | [+17.643, +41.851] | [+13.473, +48.965] | 0 / 4 / 0 | 0.125 |
| val1 | observed | uncertain | periodic:1 | 4 | +31.346 | [+18.914, +43.777] | [+13.597, +49.786] | 0 / 4 / 0 | 0.125 |
| val1 | observed | uncertain | base_stock | 4 | +31.297 | [+19.220, +43.375] | [+14.433, +49.954] | 0 / 4 / 0 | 0.125 |
| val1 | observed | uncertain | order_up_to | 4 | +26.831 | [+10.969, +42.005] | [+2.907, +49.804] | 1 / 3 / 0 | 0.625 |
| val2 | observed | fill_only | reorder_point | 5 | +14.391 | [-3.712, +33.733] | [-13.860, +46.208] | 3 / 2 / 0 | 1.0 |
| val2 | observed | fill_only | periodic:1 | 5 | +13.898 | [-5.236, +32.702] | [-13.860, +45.190] | 3 / 2 / 0 | 1.0 |
| val2 | observed | fill_only | base_stock | 5 | +15.403 | [-3.261, +34.700] | [-12.945, +46.759] | 3 / 2 / 0 | 1.0 |
| val2 | observed | fill_only | order_up_to | 5 | +7.371 | [-10.586, +25.545] | [-18.725, +33.466] | 3 / 2 / 0 | 1.0 |
| val2 | observed | lead_only | reorder_point | 5 | -9.658 | [-22.198, +2.291] | [-30.373, +7.597] | 2 / 3 / 0 | 1.0 |
| val2 | observed | lead_only | periodic:1 | 5 | -9.800 | [-22.214, +2.095] | [-30.373, +7.314] | 2 / 3 / 0 | 1.0 |
| val2 | observed | lead_only | base_stock | 5 | -9.800 | [-20.973, +1.867] | [-30.373, +7.314] | 2 / 3 / 0 | 1.0 |
| val2 | observed | lead_only | order_up_to | 5 | -37.066 | [-73.708, -1.714] | [-101.673, +5.673] | 3 / 2 / 0 | 1.0 |
| val2 | observed | mild_lead | reorder_point | 5 | -7.220 | [-16.866, +2.339] | [-25.335, +3.518] | 3 / 2 / 0 | 1.0 |
| val2 | observed | mild_lead | periodic:1 | 5 | -7.254 | [-16.759, +1.973] | [-25.142, +3.009] | 3 / 2 / 0 | 1.0 |
| val2 | observed | mild_lead | base_stock | 5 | -7.254 | [-16.759, +2.136] | [-25.142, +3.097] | 3 / 2 / 0 | 1.0 |
| val2 | observed | mild_lead | order_up_to | 5 | -42.278 | [-76.199, -9.741] | [-102.512, -0.938] | 4 / 1 / 0 | 0.375 |
| val2 | observed | stable | reorder_point | 5 | +0.338 | [-0.174, +0.882] | [-0.450, +1.128] | 1 / 4 / 0 | 0.375 |
| val2 | observed | stable | periodic:1 | 5 | +0.196 | [-0.334, +0.749] | [-0.565, +1.083] | 2 / 3 / 0 | 1.0 |
| val2 | observed | stable | base_stock | 5 | +0.196 | [-0.347, +0.749] | [-0.574, +1.083] | 2 / 3 / 0 | 1.0 |
| val2 | observed | stable | order_up_to | 5 | -19.144 | [-35.434, -3.893] | [-46.751, +0.275] | 4 / 1 / 0 | 0.375 |
| val2 | observed | uncertain | reorder_point | 5 | +19.171 | [+8.491, +29.852] | [+3.690, +34.968] | 1 / 4 / 0 | 0.375 |
| val2 | observed | uncertain | periodic:1 | 5 | +18.607 | [+8.130, +28.913] | [+2.637, +33.726] | 1 / 4 / 0 | 0.375 |
| val2 | observed | uncertain | base_stock | 5 | +19.985 | [+8.210, +31.081] | [+2.235, +36.203] | 1 / 4 / 0 | 0.375 |
| val2 | observed | uncertain | order_up_to | 5 | +2.539 | [-14.002, +20.627] | [-21.207, +32.314] | 3 / 2 / 0 | 1.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 5 | -17.3400 | [-36.9415, -1.2584] | 3 / 0 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 5 | +27.4411 | [+9.6592, +45.2230] | 0 / 5 |
| final | observed | fill_only | reorder_point | service_unit_fill | 5 | +0.0165 | [+0.0029, +0.0339] | 3 / 0 |
| final | observed | fill_only | periodic:1 | shortage | 5 | -17.3371 | [-36.9415, -1.2555] | 3 / 0 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 5 | +27.1510 | [+9.7056, +44.6492] | 0 / 5 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 5 | +0.0165 | [+0.0029, +0.0338] | 3 / 0 |
| final | observed | fill_only | base_stock | shortage | 5 | -10.5853 | [-23.1775, +0.4934] | 3 / 1 |
| final | observed | fill_only | base_stock | avg_inventory_units | 5 | +24.4996 | [+8.1593, +40.8398] | 0 / 5 |
| final | observed | fill_only | base_stock | service_unit_fill | 5 | +0.0100 | [-0.0014, +0.0238] | 3 / 1 |
| final | observed | fill_only | order_up_to | shortage | 5 | -105.3087 | [-240.8880, -18.2902] | 4 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 5 | +38.4843 | [+16.3976, +60.5710] | 0 / 5 |
| final | observed | fill_only | order_up_to | service_unit_fill | 5 | +0.0882 | [+0.0371, +0.1398] | 4 / 0 |
| final | observed | lead_only | reorder_point | shortage | 5 | -11.0660 | [-17.5814, -4.1592] | 4 / 0 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 5 | +17.8586 | [+6.3586, +29.8278] | 0 / 5 |
| final | observed | lead_only | reorder_point | service_unit_fill | 5 | +0.0161 | [+0.0044, +0.0287] | 4 / 0 |
| final | observed | lead_only | periodic:1 | shortage | 5 | -10.4927 | [-17.5814, -3.4039] | 4 / 0 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 5 | +17.5518 | [+6.3426, +29.4904] | 0 / 5 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 5 | +0.0145 | [+0.0028, +0.0287] | 4 / 0 |
| final | observed | lead_only | base_stock | shortage | 5 | -10.4927 | [-17.5814, -3.4039] | 4 / 0 |
| final | observed | lead_only | base_stock | avg_inventory_units | 5 | +17.5518 | [+6.3426, +29.4904] | 0 / 5 |
| final | observed | lead_only | base_stock | service_unit_fill | 5 | +0.0145 | [+0.0028, +0.0287] | 4 / 0 |
| final | observed | lead_only | order_up_to | shortage | 5 | -111.0836 | [-234.0380, -27.1940] | 4 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 5 | +28.7178 | [+11.3603, +46.0752] | 0 / 5 |
| final | observed | lead_only | order_up_to | service_unit_fill | 5 | +0.1038 | [+0.0484, +0.1586] | 4 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 5 | -26.6119 | [-47.6184, -5.6054] | 3 / 1 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 5 | +11.5003 | [+3.1448, +23.0761] | 0 / 5 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 5 | +0.0363 | [+0.0007, +0.0813] | 3 / 1 |
| final | observed | mild_lead | periodic:1 | shortage | 5 | -25.8695 | [-47.6758, -5.6054] | 3 / 1 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 5 | +11.1527 | [+3.1743, +21.8492] | 0 / 5 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 5 | +0.0350 | [+0.0007, +0.0777] | 3 / 1 |
| final | observed | mild_lead | base_stock | shortage | 5 | -25.8695 | [-46.1335, -5.6054] | 3 / 1 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 5 | +11.1527 | [+3.1743, +21.8492] | 0 / 5 |
| final | observed | mild_lead | base_stock | service_unit_fill | 5 | +0.0350 | [+0.0007, +0.0770] | 3 / 1 |
| final | observed | mild_lead | order_up_to | shortage | 5 | -148.7738 | [-315.7721, -33.5753] | 4 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 5 | +20.8246 | [+7.5843, +37.9583] | 0 / 5 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 5 | +0.1324 | [+0.0535, +0.2104] | 4 / 0 |
| final | observed | stable | reorder_point | shortage | 5 | -4.2682 | [-10.6968, +0.2875] | 2 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 5 | +0.8537 | [-4.0120, +6.8042] | 3 / 2 |
| final | observed | stable | reorder_point | service_unit_fill | 5 | +0.0028 | [-0.0005, +0.0071] | 2 / 1 |
| final | observed | stable | periodic:1 | shortage | 5 | -4.2682 | [-10.6968, +0.2875] | 2 / 1 |
| final | observed | stable | periodic:1 | avg_inventory_units | 5 | +0.4923 | [-4.0789, +5.8840] | 3 / 2 |
| final | observed | stable | periodic:1 | service_unit_fill | 5 | +0.0028 | [-0.0005, +0.0071] | 2 / 1 |
| final | observed | stable | base_stock | shortage | 5 | -4.2682 | [-10.6968, +0.2875] | 2 / 1 |
| final | observed | stable | base_stock | avg_inventory_units | 5 | +0.4923 | [-4.1280, +5.8840] | 3 / 2 |
| final | observed | stable | base_stock | service_unit_fill | 5 | +0.0028 | [-0.0005, +0.0071] | 2 / 1 |
| final | observed | stable | order_up_to | shortage | 5 | -95.8015 | [-214.3767, -19.1020] | 4 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 5 | +14.2572 | [+5.1377, +25.4137] | 0 / 5 |
| final | observed | stable | order_up_to | service_unit_fill | 5 | +0.0797 | [+0.0370, +0.1201] | 4 / 0 |
| final | observed | uncertain | reorder_point | shortage | 5 | -89.5288 | [-177.9562, -13.5012] | 4 / 0 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 5 | +42.7630 | [+12.4615, +73.1419] | 0 / 5 |
| final | observed | uncertain | reorder_point | service_unit_fill | 5 | +0.0847 | [+0.0146, +0.1608] | 4 / 0 |
| final | observed | uncertain | periodic:1 | shortage | 5 | -89.5288 | [-177.8950, -13.5012] | 4 / 0 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 5 | +42.4656 | [+12.3841, +72.5471] | 0 / 5 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 5 | +0.0847 | [+0.0146, +0.1641] | 4 / 0 |
| final | observed | uncertain | base_stock | shortage | 5 | -78.2684 | [-150.8189, -10.6718] | 3 / 1 |
| final | observed | uncertain | base_stock | avg_inventory_units | 5 | +41.2363 | [+11.3140, +71.1586] | 0 / 5 |
| final | observed | uncertain | base_stock | service_unit_fill | 5 | +0.0769 | [+0.0096, +0.1558] | 3 / 1 |
| final | observed | uncertain | order_up_to | shortage | 5 | -177.4055 | [-369.2537, -44.0684] | 4 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 5 | +51.5546 | [+17.4986, +85.6107] | 0 / 5 |
| final | observed | uncertain | order_up_to | service_unit_fill | 5 | +0.1592 | [+0.0617, +0.2502] | 4 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 4 | -3.6975 | [-7.3949, +0.0000] | 2 / 0 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 4 | +7.4455 | [+1.2131, +17.7858] | 0 / 4 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 4 | +0.0084 | [+0.0000, +0.0199] | 2 / 0 |
| val1 | observed | fill_only | periodic:1 | shortage | 4 | -2.3021 | [-5.6214, +0.0000] | 2 / 0 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 4 | +7.3615 | [+1.0740, +17.7878] | 0 / 4 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 4 | +0.0070 | [+0.0000, +0.0199] | 2 / 0 |
| val1 | observed | fill_only | base_stock | shortage | 4 | -0.9218 | [-3.5206, +0.7552] | 1 / 1 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 4 | +5.0608 | [-2.2641, +15.5733] | 2 / 2 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 4 | +0.0039 | [-0.0007, +0.0125] | 1 / 1 |
| val1 | observed | fill_only | order_up_to | shortage | 4 | -59.2238 | [-106.0349, -12.4593] | 4 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 4 | +22.4509 | [+5.0700, +39.8318] | 0 / 4 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 4 | +0.1117 | [+0.0240, +0.2079] | 4 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 4 | -12.3995 | [-20.9644, -3.5328] | 3 / 0 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 4 | +8.7194 | [+4.7998, +12.6389] | 0 / 4 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 4 | +0.0289 | [+0.0048, +0.0670] | 3 / 0 |
| val1 | observed | lead_only | periodic:1 | shortage | 4 | -12.3995 | [-20.9644, -3.5328] | 3 / 0 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 4 | +8.6457 | [+4.6526, +12.6389] | 0 / 4 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 4 | +0.0289 | [+0.0048, +0.0670] | 3 / 0 |
| val1 | observed | lead_only | base_stock | shortage | 4 | -12.3995 | [-20.9644, -3.5328] | 3 / 0 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 4 | +8.6457 | [+4.6526, +12.6389] | 0 / 4 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 4 | +0.0289 | [+0.0048, +0.0670] | 3 / 0 |
| val1 | observed | lead_only | order_up_to | shortage | 4 | -87.1442 | [-131.1100, -43.1784] | 4 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 4 | +19.6993 | [+7.3721, +32.8420] | 0 / 4 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 4 | +0.1479 | [+0.0796, +0.2221] | 4 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 4 | -24.5254 | [-50.2229, -5.2068] | 3 / 0 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 4 | +11.5359 | [+3.5536, +24.5403] | 0 / 4 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 4 | +0.0440 | [+0.0147, +0.0733] | 3 / 0 |
| val1 | observed | mild_lead | periodic:1 | shortage | 4 | -19.7676 | [-35.9496, -5.2068] | 3 / 0 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 4 | +11.6096 | [+3.7009, +24.5658] | 0 / 4 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 4 | +0.0394 | [+0.0106, +0.0716] | 3 / 0 |
| val1 | observed | mild_lead | base_stock | shortage | 4 | -19.7676 | [-35.9496, -5.2068] | 3 / 0 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 4 | +11.6096 | [+3.7009, +24.5658] | 0 / 4 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 4 | +0.0394 | [+0.0106, +0.0716] | 3 / 0 |
| val1 | observed | mild_lead | order_up_to | shortage | 4 | -90.5629 | [-158.9077, -49.6386] | 4 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 4 | +25.9499 | [+6.8805, +56.6667] | 0 / 4 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 4 | +0.1582 | [+0.0983, +0.2150] | 4 / 0 |
| val1 | observed | stable | reorder_point | shortage | 4 | -0.0420 | [-8.5423, +8.4163] | 1 / 1 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 4 | +3.1303 | [-0.8301, +7.7356] | 1 / 3 |
| val1 | observed | stable | reorder_point | service_unit_fill | 4 | +0.0074 | [-0.0081, +0.0303] | 1 / 1 |
| val1 | observed | stable | periodic:1 | shortage | 4 | +4.7158 | [-8.5423, +22.6896] | 1 / 1 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 4 | +3.2040 | [-0.6828, +7.7356] | 1 / 3 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 4 | +0.0028 | [-0.0217, +0.0303] | 1 / 1 |
| val1 | observed | stable | base_stock | shortage | 4 | +4.7158 | [-8.5423, +22.6896] | 1 / 1 |
| val1 | observed | stable | base_stock | avg_inventory_units | 4 | +3.2040 | [-0.6828, +7.7356] | 1 / 3 |
| val1 | observed | stable | base_stock | service_unit_fill | 4 | +0.0028 | [-0.0217, +0.0303] | 1 / 1 |
| val1 | observed | stable | order_up_to | shortage | 4 | -55.0311 | [-102.0498, -8.0123] | 4 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 4 | +20.5744 | [+4.6619, +45.5839] | 0 / 4 |
| val1 | observed | stable | order_up_to | service_unit_fill | 4 | +0.1117 | [+0.0170, +0.2291] | 4 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 4 | +8.2677 | [+0.0000, +16.5355] | 0 / 2 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 4 | +26.2211 | [+1.6697, +71.7740] | 0 / 3 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 4 | -0.0253 | [-0.0506, +0.0000] | 0 / 2 |
| val1 | observed | uncertain | periodic:1 | shortage | 4 | +15.1770 | [+3.7261, +26.6278] | 0 / 3 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 4 | +26.2881 | [+1.9879, +71.7349] | 0 / 4 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 4 | -0.0296 | [-0.0530, -0.0075] | 0 / 3 |
| val1 | observed | uncertain | base_stock | shortage | 4 | +17.6268 | [+5.7919, +28.4380] | 0 / 3 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 4 | +24.3550 | [+1.4024, +67.4568] | 0 / 4 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 4 | -0.0368 | [-0.0577, -0.0125] | 0 / 3 |
| val1 | observed | uncertain | order_up_to | shortage | 4 | -50.3046 | [-90.4060, -13.6807] | 4 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 4 | +37.7476 | [+2.6476, +101.2303] | 0 / 4 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 4 | +0.0922 | [+0.0234, +0.1669] | 4 / 0 |
| val2 | observed | fill_only | reorder_point | shortage | 5 | -23.0767 | [-48.8341, +0.0000] | 2 / 0 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 5 | +45.0433 | [+14.6361, +78.4659] | 0 / 5 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 5 | +0.0181 | [+0.0000, +0.0437] | 2 / 0 |
| val2 | observed | fill_only | periodic:1 | shortage | 5 | -23.0767 | [-48.8341, +0.0000] | 2 / 0 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 5 | +44.4726 | [+14.0654, +78.4659] | 0 / 5 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 5 | +0.0181 | [+0.0000, +0.0437] | 2 / 0 |
| val2 | observed | fill_only | base_stock | shortage | 5 | -17.0611 | [-36.9814, +2.8084] | 2 / 2 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 5 | +41.6044 | [+12.0189, +75.7176] | 0 / 5 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 5 | +0.0134 | [-0.0041, +0.0351] | 2 / 2 |
| val2 | observed | fill_only | order_up_to | shortage | 5 | -98.5174 | [-212.5235, -17.6961] | 4 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 5 | +67.7443 | [+26.0484, +110.7627] | 0 / 5 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 5 | +0.0728 | [+0.0307, +0.1161] | 4 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 5 | -51.6201 | [-123.9372, +0.5671] | 2 / 1 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 5 | +26.0418 | [+13.4660, +38.6527] | 0 / 5 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 5 | +0.0340 | [-0.0011, +0.0741] | 2 / 1 |
| val2 | observed | lead_only | periodic:1 | shortage | 5 | -51.6201 | [-123.9372, +0.5671] | 2 / 1 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 5 | +25.3631 | [+13.4079, +37.9341] | 0 / 5 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 5 | +0.0340 | [-0.0011, +0.0741] | 2 / 1 |
| val2 | observed | lead_only | base_stock | shortage | 5 | -51.6201 | [-119.5524, +0.5671] | 2 / 1 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 5 | +25.3631 | [+13.4079, +37.9830] | 0 / 5 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 5 | +0.0340 | [-0.0011, +0.0741] | 2 / 1 |
| val2 | observed | lead_only | order_up_to | shortage | 5 | -154.1963 | [-358.6960, -20.0880] | 4 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 5 | +44.6385 | [+21.8893, +67.3877] | 0 / 5 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 5 | +0.1046 | [+0.0334, +0.1803] | 4 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 5 | -38.2574 | [-100.7532, -3.2413] | 4 / 0 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 5 | +23.4880 | [+12.9881, +33.3939] | 0 / 5 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 5 | +0.0216 | [+0.0051, +0.0460] | 4 / 0 |
| val2 | observed | mild_lead | periodic:1 | shortage | 5 | -37.9198 | [-100.7532, -2.5663] | 4 / 0 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 5 | +22.8183 | [+12.3184, +32.8372] | 0 / 5 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 5 | +0.0210 | [+0.0045, +0.0445] | 4 / 0 |
| val2 | observed | mild_lead | base_stock | shortage | 5 | -37.9198 | [-101.1506, -2.5663] | 4 / 0 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 5 | +22.8183 | [+12.3184, +33.3939] | 0 / 5 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 5 | +0.0210 | [+0.0045, +0.0445] | 4 / 0 |
| val2 | observed | mild_lead | order_up_to | shortage | 5 | -165.9268 | [-367.2446, -39.3120] | 4 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 5 | +42.3219 | [+23.5272, +60.0129] | 0 / 5 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 5 | +0.1272 | [+0.0564, +0.1886] | 4 / 0 |
| val2 | observed | stable | reorder_point | shortage | 5 | -1.6951 | [-5.0852, +0.0000] | 1 / 0 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 5 | +5.8314 | [+1.2596, +11.5721] | 0 / 4 |
| val2 | observed | stable | reorder_point | service_unit_fill | 5 | +0.0021 | [+0.0000, +0.0064] | 1 / 0 |
| val2 | observed | stable | periodic:1 | shortage | 5 | -1.6951 | [-5.0852, +0.0000] | 1 / 0 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 5 | +5.0911 | [+0.0431, +10.9157] | 1 / 4 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 5 | +0.0021 | [+0.0000, +0.0064] | 1 / 0 |
| val2 | observed | stable | base_stock | shortage | 5 | -1.6951 | [-5.0852, +0.0000] | 1 / 0 |
| val2 | observed | stable | base_stock | avg_inventory_units | 5 | +5.0911 | [-0.4055, +10.9157] | 1 / 4 |
| val2 | observed | stable | base_stock | service_unit_fill | 5 | +0.0021 | [+0.0000, +0.0064] | 1 / 0 |
| val2 | observed | stable | order_up_to | shortage | 5 | -81.1585 | [-175.6534, -18.4106] | 4 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 5 | +30.6727 | [+16.2608, +45.1013] | 0 / 5 |
| val2 | observed | stable | order_up_to | service_unit_fill | 5 | +0.0616 | [+0.0293, +0.0928] | 4 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 5 | -19.4947 | [-39.8969, -0.8967] | 3 / 1 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 5 | +28.3853 | [+9.6612, +51.4693] | 0 / 5 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 5 | +0.0326 | [+0.0021, +0.0725] | 3 / 1 |
| val2 | observed | uncertain | periodic:1 | shortage | 5 | -19.3553 | [-39.7065, -0.8967] | 3 / 1 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 5 | +27.5504 | [+9.6774, +50.0732] | 0 / 5 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 5 | +0.0324 | [+0.0022, +0.0696] | 3 / 1 |
| val2 | observed | uncertain | base_stock | shortage | 5 | -12.5905 | [-32.3239, +6.9361] | 3 / 1 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 5 | +24.8656 | [+7.6610, +45.9523] | 0 / 5 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 5 | +0.0258 | [-0.0022, +0.0644] | 3 / 1 |
| val2 | observed | uncertain | order_up_to | shortage | 5 | -124.6384 | [-228.1529, -44.6999] | 4 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 5 | +47.3370 | [+18.6450, +76.6451] | 0 / 5 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 5 | +0.1166 | [+0.0568, +0.1575] | 4 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 70/75 complete, 0 infeasible, 0 abstained; gated: 70/75 complete, 0 infeasible, 0 abstained; order_up_to: 70/75 complete, 0 infeasible, 0 abstained; periodic:1: 70/75 complete, 0 infeasible, 0 abstained; reorder_point: 70/75 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 25
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 75 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +66.059 (fill 0.964 vs 0.946, inventory 68.34 vs 25.22, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +57.603 (fill 0.742 vs 0.723, inventory 20.70 vs 8.45, retained incumbent on None reviews)
- val2/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +56.300 (fill 0.950 vs 0.950, inventory 174.91 vs 71.79, retained incumbent on None reviews)
- val2/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +54.670 (fill 0.950 vs 0.950, inventory 165.79 vs 73.67, retained incumbent on None reviews)
- val1/observed/uncertain store CA_3 product FOODS_2_318: ZAAD minus periodic:1 = +32.865 (fill 0.720 vs 0.750, inventory 55.09 vs 54.67, retained incumbent on None reviews)
- val2/observed/uncertain store TX_2 product FOODS_1_046: ZAAD minus base_stock = +31.285 (fill 0.922 vs 0.888, inventory 120.70 vs 56.80, retained incumbent on None reviews)
- val1/observed/uncertain store TX_2 product FOODS_1_046: ZAAD minus order_up_to = +29.157 (fill 1.000 vs 0.972, inventory 174.17 vs 40.72, retained incumbent on None reviews)
- val2/observed/uncertain store CA_3 product FOODS_2_318: ZAAD minus base_stock = +24.675 (fill 0.897 vs 0.904, inventory 32.46 vs 25.42, retained incumbent on None reviews)
- final/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +22.961 (fill 0.770 vs 0.770, inventory 103.53 vs 39.34, retained incumbent on None reviews)
- final/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +22.750 (fill 0.745 vs 0.745, inventory 115.40 vs 31.32, retained incumbent on None reviews)
