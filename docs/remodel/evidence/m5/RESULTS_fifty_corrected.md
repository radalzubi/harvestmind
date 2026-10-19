# Walmart M5 (Experiment A) results: stage `fifty_corrected`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `ecd18b01e12d`, selection `8b6067be83a4`; 3750 runs, 3625 complete, 125 not complete; wall 3282 s, peak RSS 238 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 49/50 | 395.376 | 412.059 | 396.286 | 2.6838 | 35.122 | 0.927 | 14.801 | 19.903 | 1.9 | 10.8 |  | 0.47 |
| final | observed | fill_only | gated | 49/50 | 392.666 | 410.160 | 405.351 | 4.3448 | 26.510 | 0.939 | 12.044 | 28.660 | 1.5 | 8.9 | 0.40 | 5.42 |
| final | observed | fill_only | order_up_to | 49/50 | 401.208 | 413.216 | 330.587 | 1.2199 | 82.664 | 0.803 | 36.484 | 9.640 | 4.3 | 10.6 |  | 0.22 |
| final | observed | fill_only | periodic:1 | 49/50 | 395.587 | 411.668 | 390.534 | 2.4697 | 37.946 | 0.922 | 16.002 | 18.467 | 2.0 | 11.2 |  | 0.04 |
| final | observed | fill_only | reorder_point | 49/50 | 395.534 | 411.598 | 390.147 | 2.4615 | 38.188 | 0.921 | 16.072 | 18.357 | 2.1 | 10.4 |  | 0.03 |
| final | observed | lead_only | base_stock | 49/50 | 371.213 | 387.549 | 326.700 | 2.3859 | 79.127 | 0.847 | 29.439 | 17.012 | 2.9 | 10.6 |  | 0.46 |
| final | observed | lead_only | gated | 49/50 | 367.626 | 387.217 | 356.897 | 3.3175 | 62.529 | 0.882 | 23.378 | 21.284 | 2.4 | 9.9 | 0.42 | 3.76 |
| final | observed | lead_only | order_up_to | 49/50 | 386.345 | 398.102 | 262.188 | 1.2238 | 135.076 | 0.700 | 55.971 | 9.329 | 5.4 | 10.0 |  | 0.23 |
| final | observed | lead_only | periodic:1 | 49/50 | 371.212 | 387.548 | 326.700 | 2.3850 | 79.127 | 0.847 | 29.439 | 17.006 | 2.9 | 10.6 |  | 0.04 |
| final | observed | lead_only | reorder_point | 49/50 | 371.396 | 387.671 | 325.875 | 2.3772 | 79.799 | 0.844 | 29.939 | 16.930 | 3.0 | 9.6 |  | 0.04 |
| final | observed | mild_lead | base_stock | 49/50 | 369.145 | 386.641 | 337.853 | 2.3176 | 72.149 | 0.858 | 28.304 | 17.299 | 2.9 | 10.7 |  | 0.47 |
| final | observed | mild_lead | gated | 49/50 | 366.657 | 386.667 | 361.212 | 3.0036 | 60.031 | 0.880 | 23.210 | 21.139 | 2.4 | 9.9 | 0.41 | 3.69 |
| final | observed | mild_lead | order_up_to | 49/50 | 386.627 | 399.733 | 269.032 | 1.1985 | 135.729 | 0.707 | 56.303 | 9.539 | 5.2 | 10.1 |  | 0.22 |
| final | observed | mild_lead | periodic:1 | 49/50 | 369.144 | 386.640 | 337.853 | 2.3168 | 72.149 | 0.858 | 28.304 | 17.294 | 2.9 | 10.7 |  | 0.04 |
| final | observed | mild_lead | reorder_point | 49/50 | 369.483 | 386.947 | 336.848 | 2.3135 | 73.311 | 0.855 | 28.854 | 17.272 | 3.0 | 9.6 |  | 0.04 |
| final | observed | stable | base_stock | 49/50 | 358.202 | 374.709 | 358.305 | 2.6597 | 34.957 | 0.929 | 14.820 | 19.899 | 1.9 | 10.9 |  | 0.47 |
| final | observed | stable | gated | 49/50 | 357.682 | 374.547 | 361.880 | 2.7079 | 32.854 | 0.930 | 14.325 | 20.289 | 1.8 | 10.2 | 0.21 | 3.92 |
| final | observed | stable | order_up_to | 49/50 | 370.486 | 382.334 | 299.205 | 1.1951 | 82.478 | 0.803 | 36.904 | 9.555 | 4.5 | 10.5 |  | 0.22 |
| final | observed | stable | periodic:1 | 49/50 | 358.201 | 374.708 | 358.305 | 2.6589 | 34.957 | 0.929 | 14.820 | 19.893 | 1.9 | 10.8 |  | 0.04 |
| final | observed | stable | reorder_point | 49/50 | 358.264 | 374.725 | 357.843 | 2.6466 | 35.233 | 0.927 | 15.207 | 19.858 | 2.0 | 9.9 |  | 0.04 |
| final | observed | uncertain | base_stock | 49/50 | 420.014 | 436.507 | 355.912 | 2.0804 | 100.188 | 0.815 | 38.578 | 15.586 | 3.5 | 10.6 |  | 0.46 |
| final | observed | uncertain | gated | 49/50 | 418.760 | 440.228 | 407.824 | 3.9342 | 73.692 | 0.853 | 29.454 | 25.000 | 2.6 | 8.4 | 0.38 | 2.87 |
| final | observed | uncertain | order_up_to | 49/50 | 426.793 | 438.600 | 280.452 | 1.1152 | 158.091 | 0.670 | 61.663 | 8.689 | 5.7 | 10.0 |  | 0.22 |
| final | observed | uncertain | periodic:1 | 49/50 | 419.939 | 435.828 | 348.313 | 1.9596 | 104.481 | 0.808 | 40.046 | 14.757 | 3.5 | 11.1 |  | 0.04 |
| final | observed | uncertain | reorder_point | 49/50 | 419.929 | 435.813 | 347.980 | 1.9472 | 104.792 | 0.806 | 40.128 | 14.679 | 3.5 | 10.0 |  | 0.04 |
| val1 | observed | fill_only | base_stock | 43/50 | 313.839 | 328.638 | 299.669 | 3.4418 | 44.542 | 0.912 | 15.305 | 23.780 | 1.5 | 10.4 |  | 0.46 |
| val1 | observed | fill_only | gated | 43/50 | 316.898 | 333.203 | 315.862 | 4.6775 | 38.958 | 0.921 | 13.799 | 30.427 | 1.3 | 8.7 | 0.37 | 5.16 |
| val1 | observed | fill_only | order_up_to | 43/50 | 318.937 | 328.548 | 231.158 | 1.8428 | 91.196 | 0.786 | 33.631 | 11.206 | 4.3 | 10.1 |  | 0.22 |
| val1 | observed | fill_only | periodic:1 | 43/50 | 314.094 | 328.438 | 296.265 | 3.2682 | 45.832 | 0.908 | 15.739 | 22.479 | 1.6 | 11.0 |  | 0.04 |
| val1 | observed | fill_only | reorder_point | 43/50 | 314.219 | 328.508 | 295.584 | 3.2231 | 46.362 | 0.907 | 15.880 | 22.332 | 1.6 | 10.0 |  | 0.04 |
| val1 | observed | lead_only | base_stock | 43/50 | 291.147 | 306.123 | 253.132 | 2.9324 | 69.928 | 0.833 | 26.700 | 20.053 | 2.8 | 10.2 |  | 0.45 |
| val1 | observed | lead_only | gated | 43/50 | 289.799 | 308.785 | 284.962 | 3.9881 | 59.110 | 0.858 | 23.912 | 29.907 | 2.3 | 9.5 | 0.42 | 3.58 |
| val1 | observed | lead_only | order_up_to | 43/50 | 305.541 | 315.448 | 186.886 | 1.6881 | 124.062 | 0.687 | 48.180 | 10.142 | 5.5 | 9.6 |  | 0.22 |
| val1 | observed | lead_only | periodic:1 | 43/50 | 291.195 | 306.171 | 253.020 | 2.9331 | 70.087 | 0.832 | 26.766 | 20.058 | 2.8 | 10.2 |  | 0.03 |
| val1 | observed | lead_only | reorder_point | 43/50 | 291.439 | 306.375 | 252.110 | 2.8885 | 71.065 | 0.830 | 27.264 | 19.939 | 2.8 | 9.0 |  | 0.03 |
| val1 | observed | mild_lead | base_stock | 43/50 | 290.071 | 305.208 | 257.159 | 3.0966 | 65.645 | 0.857 | 23.665 | 21.050 | 2.5 | 10.4 |  | 0.46 |
| val1 | observed | mild_lead | gated | 43/50 | 289.515 | 307.946 | 281.481 | 3.8012 | 59.211 | 0.870 | 22.002 | 25.577 | 2.0 | 9.6 | 0.39 | 3.73 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 303.282 | 313.426 | 193.618 | 1.7614 | 116.240 | 0.719 | 46.213 | 10.697 | 5.1 | 9.8 |  | 0.22 |
| val1 | observed | mild_lead | periodic:1 | 43/50 | 290.119 | 305.256 | 257.048 | 3.0966 | 65.804 | 0.856 | 23.732 | 21.050 | 2.5 | 10.4 |  | 0.03 |
| val1 | observed | mild_lead | reorder_point | 43/50 | 290.436 | 305.526 | 255.937 | 3.0684 | 66.986 | 0.854 | 24.229 | 20.943 | 2.5 | 9.1 |  | 0.03 |
| val1 | observed | stable | base_stock | 43/50 | 283.794 | 298.560 | 270.151 | 3.4535 | 43.820 | 0.913 | 15.148 | 23.624 | 1.5 | 10.6 |  | 0.49 |
| val1 | observed | stable | gated | 43/50 | 284.315 | 299.347 | 271.081 | 3.5823 | 44.892 | 0.913 | 15.620 | 24.866 | 1.5 | 9.5 | 0.14 | 3.24 |
| val1 | observed | stable | order_up_to | 43/50 | 295.439 | 304.992 | 208.409 | 1.8521 | 90.142 | 0.789 | 33.338 | 11.138 | 4.3 | 10.2 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 43/50 | 283.795 | 298.562 | 270.144 | 3.4521 | 43.829 | 0.913 | 15.152 | 23.615 | 1.5 | 10.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 43/50 | 284.111 | 298.827 | 268.974 | 3.4049 | 45.072 | 0.911 | 15.660 | 23.472 | 1.6 | 9.4 |  | 0.03 |
| val1 | observed | uncertain | base_stock | 43/50 | 324.614 | 339.379 | 279.746 | 2.8625 | 75.876 | 0.832 | 28.988 | 20.024 | 3.0 | 10.4 |  | 0.45 |
| val1 | observed | uncertain | gated | 43/50 | 328.964 | 346.650 | 311.278 | 4.1907 | 65.237 | 0.852 | 27.088 | 39.051 | 2.6 | 8.1 | 0.33 | 3.03 |
| val1 | observed | uncertain | order_up_to | 43/50 | 329.280 | 338.971 | 206.158 | 1.6199 | 127.504 | 0.689 | 50.356 | 9.941 | 5.3 | 9.8 |  | 0.22 |
| val1 | observed | uncertain | periodic:1 | 43/50 | 324.494 | 338.905 | 275.808 | 2.7305 | 77.838 | 0.828 | 29.625 | 18.854 | 3.1 | 10.8 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 43/50 | 325.080 | 339.453 | 274.479 | 2.6930 | 79.605 | 0.823 | 30.305 | 18.701 | 3.1 | 9.7 |  | 0.04 |
| val2 | observed | fill_only | base_stock | 49/50 | 321.940 | 336.189 | 331.600 | 2.6510 | 23.003 | 0.915 | 16.175 | 21.610 | 1.7 | 11.2 |  | 0.50 |
| val2 | observed | fill_only | gated | 49/50 | 322.493 | 337.959 | 340.790 | 4.3034 | 20.267 | 0.920 | 14.274 | 32.372 | 1.5 | 8.7 | 0.39 | 5.17 |
| val2 | observed | fill_only | order_up_to | 49/50 | 325.738 | 335.064 | 266.700 | 1.0675 | 66.475 | 0.787 | 38.713 | 9.017 | 4.5 | 11.1 |  | 0.23 |
| val2 | observed | fill_only | periodic:1 | 49/50 | 321.823 | 335.628 | 327.682 | 2.4652 | 24.537 | 0.911 | 16.847 | 20.123 | 1.9 | 11.7 |  | 0.04 |
| val2 | observed | fill_only | reorder_point | 49/50 | 321.716 | 335.434 | 326.933 | 2.4482 | 24.690 | 0.911 | 17.273 | 19.992 | 1.8 | 10.7 |  | 0.04 |
| val2 | observed | lead_only | base_stock | 49/50 | 295.474 | 309.695 | 268.600 | 2.1361 | 60.062 | 0.834 | 33.226 | 17.279 | 3.1 | 10.9 |  | 0.46 |
| val2 | observed | lead_only | gated | 49/50 | 292.167 | 309.628 | 299.078 | 3.0174 | 44.052 | 0.870 | 25.332 | 23.141 | 2.3 | 10.4 | 0.48 | 3.71 |
| val2 | observed | lead_only | order_up_to | 49/50 | 310.951 | 320.408 | 202.595 | 0.9828 | 117.033 | 0.673 | 58.968 | 7.555 | 5.9 | 10.3 |  | 0.23 |
| val2 | observed | lead_only | periodic:1 | 49/50 | 295.474 | 309.695 | 268.600 | 2.1361 | 60.062 | 0.834 | 33.226 | 17.279 | 3.1 | 10.9 |  | 0.04 |
| val2 | observed | lead_only | reorder_point | 49/50 | 295.561 | 309.715 | 267.925 | 2.1113 | 60.470 | 0.832 | 33.695 | 17.043 | 3.2 | 9.5 |  | 0.03 |
| val2 | observed | mild_lead | base_stock | 49/50 | 292.011 | 306.166 | 276.711 | 2.3650 | 47.833 | 0.854 | 25.856 | 19.241 | 2.7 | 11.1 |  | 0.47 |
| val2 | observed | mild_lead | gated | 49/50 | 289.745 | 306.175 | 297.736 | 3.0659 | 36.703 | 0.874 | 21.419 | 23.759 | 2.1 | 10.4 | 0.45 | 3.78 |
| val2 | observed | mild_lead | order_up_to | 49/50 | 305.941 | 315.332 | 213.656 | 1.0552 | 100.304 | 0.708 | 51.097 | 8.425 | 5.2 | 10.6 |  | 0.23 |
| val2 | observed | mild_lead | periodic:1 | 49/50 | 292.011 | 306.166 | 276.711 | 2.3650 | 47.833 | 0.854 | 25.856 | 19.241 | 2.7 | 11.1 |  | 0.03 |
| val2 | observed | mild_lead | reorder_point | 49/50 | 292.086 | 306.211 | 276.280 | 2.3424 | 48.183 | 0.852 | 26.010 | 18.969 | 2.8 | 9.8 |  | 0.04 |
| val2 | observed | stable | base_stock | 49/50 | 284.683 | 298.885 | 294.645 | 2.6848 | 22.408 | 0.915 | 15.135 | 21.264 | 1.6 | 11.3 |  | 0.48 |
| val2 | observed | stable | gated | 49/50 | 284.744 | 299.364 | 297.374 | 2.7879 | 22.022 | 0.916 | 14.725 | 22.195 | 1.6 | 10.3 | 0.19 | 3.31 |
| val2 | observed | stable | order_up_to | 49/50 | 295.230 | 304.427 | 237.209 | 1.0819 | 64.751 | 0.789 | 37.199 | 8.616 | 4.5 | 11.1 |  | 0.22 |
| val2 | observed | stable | periodic:1 | 49/50 | 284.683 | 298.885 | 294.645 | 2.6848 | 22.408 | 0.915 | 15.135 | 21.264 | 1.6 | 11.3 |  | 0.04 |
| val2 | observed | stable | reorder_point | 49/50 | 284.723 | 298.869 | 294.136 | 2.6625 | 22.653 | 0.914 | 15.264 | 20.975 | 1.7 | 10.1 |  | 0.04 |
| val2 | observed | uncertain | base_stock | 49/50 | 322.045 | 335.970 | 302.117 | 2.2763 | 51.376 | 0.836 | 30.418 | 17.551 | 3.1 | 10.9 |  | 0.47 |
| val2 | observed | uncertain | gated | 49/50 | 326.602 | 343.939 | 333.608 | 4.0661 | 42.510 | 0.863 | 27.647 | 26.125 | 2.2 | 8.3 | 0.40 | 2.98 |
| val2 | observed | uncertain | order_up_to | 49/50 | 331.443 | 340.849 | 228.738 | 1.0340 | 110.878 | 0.673 | 59.138 | 8.094 | 5.6 | 10.5 |  | 0.22 |
| val2 | observed | uncertain | periodic:1 | 49/50 | 322.453 | 335.990 | 297.778 | 2.1330 | 54.126 | 0.829 | 31.938 | 16.532 | 3.3 | 11.5 |  | 0.03 |
| val2 | observed | uncertain | reorder_point | 49/50 | 322.357 | 335.837 | 297.248 | 2.1076 | 54.245 | 0.829 | 32.069 | 16.138 | 3.3 | 10.3 |  | 0.04 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 49 | -2.868 | [-5.523, -0.135] | [-7.282, +0.920] | 28 / 17 / 4 | 0.135 |
| final | observed | fill_only | periodic:1 | 49 | -2.921 | [-5.764, -0.357] | [-7.468, +0.847] | 31 / 17 / 1 | 0.059 |
| final | observed | fill_only | base_stock | 49 | -2.710 | [-5.265, -0.266] | [-6.824, +0.830] | 33 / 15 / 1 | 0.013 |
| final | observed | fill_only | order_up_to | 49 | -8.542 | [-13.618, -4.094] | [-16.571, -2.285] | 34 / 13 / 2 | 0.003 |
| final | observed | lead_only | reorder_point | 49 | -3.770 | [-5.188, -2.396] | [-5.989, -1.748] | 27 / 21 / 1 | 0.471 |
| final | observed | lead_only | periodic:1 | 49 | -3.586 | [-5.000, -2.257] | [-5.771, -1.663] | 27 / 22 / 0 | 0.568 |
| final | observed | lead_only | base_stock | 49 | -3.587 | [-5.018, -2.245] | [-5.734, -1.524] | 27 / 22 / 0 | 0.568 |
| final | observed | lead_only | order_up_to | 49 | -18.719 | [-22.669, -15.040] | [-24.815, -13.465] | 45 / 3 / 1 | 0.0 |
| final | observed | mild_lead | reorder_point | 49 | -2.826 | [-4.176, -1.604] | [-4.902, -1.038] | 25 / 22 / 2 | 0.771 |
| final | observed | mild_lead | periodic:1 | 49 | -2.488 | [-3.818, -1.153] | [-4.614, -0.529] | 24 / 24 / 1 | 1.0 |
| final | observed | mild_lead | base_stock | 49 | -2.488 | [-3.843, -1.130] | [-4.569, -0.511] | 24 / 24 / 1 | 1.0 |
| final | observed | mild_lead | order_up_to | 49 | -19.971 | [-25.071, -15.240] | [-28.012, -13.126] | 46 / 1 / 2 | 0.0 |
| final | observed | stable | reorder_point | 49 | -0.582 | [-1.269, -0.006] | [-1.784, +0.138] | 21 / 21 / 7 | 1.0 |
| final | observed | stable | periodic:1 | 49 | -0.519 | [-1.174, +0.068] | [-1.652, +0.203] | 19 / 26 / 4 | 0.371 |
| final | observed | stable | base_stock | 49 | -0.520 | [-1.197, +0.065] | [-1.625, +0.204] | 19 / 26 / 4 | 0.371 |
| final | observed | stable | order_up_to | 49 | -12.804 | [-16.421, -9.604] | [-18.638, -8.334] | 44 / 3 / 2 | 0.0 |
| final | observed | uncertain | reorder_point | 49 | -1.169 | [-4.466, +1.996] | [-6.522, +3.506] | 22 / 24 / 3 | 0.883 |
| final | observed | uncertain | periodic:1 | 49 | -1.179 | [-4.424, +2.007] | [-6.655, +3.385] | 23 / 25 / 1 | 0.885 |
| final | observed | uncertain | base_stock | 49 | -1.254 | [-4.664, +1.941] | [-6.557, +3.394] | 24 / 24 / 1 | 1.0 |
| final | observed | uncertain | order_up_to | 49 | -8.033 | [-12.877, -3.632] | [-16.146, -2.011] | 32 / 15 / 2 | 0.019 |
| val1 | observed | fill_only | reorder_point | 43 | +2.679 | [+0.486, +4.966] | [-0.462, +6.382] | 15 / 26 / 2 | 0.117 |
| val1 | observed | fill_only | periodic:1 | 43 | +2.805 | [+0.719, +5.091] | [-0.272, +6.587] | 15 / 28 / 0 | 0.066 |
| val1 | observed | fill_only | base_stock | 43 | +3.059 | [+0.912, +5.408] | [-0.018, +6.921] | 17 / 26 / 0 | 0.222 |
| val1 | observed | fill_only | order_up_to | 43 | -2.038 | [-4.463, +0.355] | [-5.764, +1.753] | 26 / 17 / 0 | 0.222 |
| val1 | observed | lead_only | reorder_point | 43 | -1.641 | [-2.857, -0.423] | [-3.627, +0.158] | 20 / 22 / 1 | 0.878 |
| val1 | observed | lead_only | periodic:1 | 43 | -1.397 | [-2.631, -0.238] | [-3.436, +0.354] | 18 / 24 / 1 | 0.441 |
| val1 | observed | lead_only | base_stock | 43 | -1.348 | [-2.575, -0.106] | [-3.340, +0.417] | 18 / 24 / 1 | 0.441 |
| val1 | observed | lead_only | order_up_to | 43 | -15.743 | [-19.365, -12.109] | [-21.650, -10.424] | 40 / 3 / 0 | 0.0 |
| val1 | observed | mild_lead | reorder_point | 43 | -0.921 | [-2.127, +0.237] | [-2.869, +0.828] | 15 / 26 / 2 | 0.117 |
| val1 | observed | mild_lead | periodic:1 | 43 | -0.604 | [-1.757, +0.492] | [-2.451, +1.061] | 14 / 28 / 1 | 0.044 |
| val1 | observed | mild_lead | base_stock | 43 | -0.556 | [-1.715, +0.579] | [-2.297, +1.126] | 14 / 28 / 1 | 0.044 |
| val1 | observed | mild_lead | order_up_to | 43 | -13.767 | [-17.207, -10.523] | [-18.974, -9.196] | 41 / 2 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 43 | +0.204 | [+0.026, +0.390] | [-0.060, +0.482] | 9 / 26 / 8 | 0.006 |
| val1 | observed | stable | periodic:1 | 43 | +0.520 | [+0.164, +0.900] | [+0.016, +1.155] | 13 / 27 / 3 | 0.038 |
| val1 | observed | stable | base_stock | 43 | +0.521 | [+0.160, +0.898] | [+0.007, +1.111] | 13 / 27 / 3 | 0.038 |
| val1 | observed | stable | order_up_to | 43 | -11.124 | [-13.919, -8.487] | [-15.680, -7.399] | 40 / 3 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 43 | +3.884 | [+0.593, +7.179] | [-1.157, +8.996] | 12 / 30 / 1 | 0.008 |
| val1 | observed | uncertain | periodic:1 | 43 | +4.469 | [+1.002, +7.740] | [-0.894, +9.639] | 10 / 33 / 0 | 0.001 |
| val1 | observed | uncertain | base_stock | 43 | +4.349 | [+1.026, +7.726] | [-0.736, +9.520] | 14 / 29 / 0 | 0.032 |
| val1 | observed | uncertain | order_up_to | 43 | -0.317 | [-4.190, +3.752] | [-6.312, +5.749] | 25 / 18 / 0 | 0.36 |
| val2 | observed | fill_only | reorder_point | 49 | +0.777 | [-2.439, +4.040] | [-4.311, +5.763] | 21 / 28 / 0 | 0.392 |
| val2 | observed | fill_only | periodic:1 | 49 | +0.670 | [-2.684, +3.869] | [-4.446, +5.616] | 20 / 29 / 0 | 0.253 |
| val2 | observed | fill_only | base_stock | 49 | +0.553 | [-2.717, +3.740] | [-4.524, +5.558] | 23 / 26 / 0 | 0.775 |
| val2 | observed | fill_only | order_up_to | 49 | -3.245 | [-7.093, +0.474] | [-9.435, +2.273] | 31 / 18 / 0 | 0.085 |
| val2 | observed | lead_only | reorder_point | 49 | -3.393 | [-5.035, -1.787] | [-6.114, -1.115] | 27 / 22 / 0 | 0.568 |
| val2 | observed | lead_only | periodic:1 | 49 | -3.307 | [-4.999, -1.665] | [-6.032, -1.002] | 28 / 21 / 0 | 0.392 |
| val2 | observed | lead_only | base_stock | 49 | -3.307 | [-5.018, -1.709] | [-6.037, -1.003] | 28 / 21 / 0 | 0.392 |
| val2 | observed | lead_only | order_up_to | 49 | -18.784 | [-23.710, -14.253] | [-26.732, -12.322] | 47 / 2 / 0 | 0.0 |
| val2 | observed | mild_lead | reorder_point | 49 | -2.341 | [-3.953, -0.815] | [-4.978, -0.256] | 24 / 25 / 0 | 1.0 |
| val2 | observed | mild_lead | periodic:1 | 49 | -2.267 | [-3.932, -0.775] | [-4.972, -0.156] | 23 / 26 / 0 | 0.775 |
| val2 | observed | mild_lead | base_stock | 49 | -2.267 | [-3.898, -0.743] | [-5.029, -0.167] | 23 / 26 / 0 | 0.775 |
| val2 | observed | mild_lead | order_up_to | 49 | -16.196 | [-21.186, -11.496] | [-24.425, -9.636] | 46 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 49 | +0.021 | [-0.139, +0.165] | [-0.245, +0.223] | 12 / 32 / 5 | 0.004 |
| val2 | observed | stable | periodic:1 | 49 | +0.061 | [-0.104, +0.213] | [-0.207, +0.286] | 15 / 32 / 2 | 0.019 |
| val2 | observed | stable | base_stock | 49 | +0.061 | [-0.105, +0.217] | [-0.195, +0.290] | 15 / 32 / 2 | 0.019 |
| val2 | observed | stable | order_up_to | 49 | -10.487 | [-13.121, -7.863] | [-14.744, -6.861] | 46 / 3 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 49 | +4.244 | [+2.093, +6.598] | [+1.014, +7.944] | 15 / 33 / 1 | 0.013 |
| val2 | observed | uncertain | periodic:1 | 49 | +4.148 | [+1.971, +6.456] | [+1.007, +7.658] | 16 / 33 / 0 | 0.021 |
| val2 | observed | uncertain | base_stock | 49 | +4.556 | [+2.295, +6.880] | [+1.246, +8.146] | 13 / 36 / 0 | 0.001 |
| val2 | observed | uncertain | order_up_to | 49 | -4.841 | [-7.777, -1.847] | [-9.292, -0.318] | 29 / 20 / 0 | 0.253 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 49 | -11.6779 | [-20.7234, -4.6205] | 22 / 6 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 49 | +10.3030 | [+5.6184, +16.4946] | 2 / 42 |
| final | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0187 | [+0.0082, +0.0304] | 22 / 6 |
| final | observed | fill_only | periodic:1 | shortage | 49 | -11.4362 | [-20.8890, -4.2778] | 22 / 6 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +10.1933 | [+5.4221, +16.0370] | 5 / 42 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0176 | [+0.0075, +0.0291] | 22 / 6 |
| final | observed | fill_only | base_stock | shortage | 49 | -8.6116 | [-16.4945, -2.6014] | 20 / 13 |
| final | observed | fill_only | base_stock | avg_inventory_units | 49 | +8.7574 | [+4.2508, +14.9054] | 9 / 38 |
| final | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0123 | [+0.0025, +0.0233] | 20 / 13 |
| final | observed | fill_only | order_up_to | shortage | 49 | -56.1542 | [-78.2834, -37.9323] | 46 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 49 | +19.0203 | [+12.0750, +28.2084] | 0 / 47 |
| final | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1364 | [+0.1146, +0.1585] | 46 / 0 |
| final | observed | lead_only | reorder_point | shortage | 49 | -17.2701 | [-24.8180, -10.6546] | 29 / 3 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 49 | +4.3535 | [+2.4612, +6.6976] | 3 / 43 |
| final | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0382 | [+0.0258, +0.0518] | 29 / 3 |
| final | observed | lead_only | periodic:1 | shortage | 49 | -16.5980 | [-24.1900, -9.9755] | 29 / 5 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +4.2778 | [+2.4334, +6.4711] | 4 / 44 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0350 | [+0.0231, +0.0483] | 29 / 5 |
| final | observed | lead_only | base_stock | shortage | 49 | -16.5980 | [-23.9058, -10.0352] | 29 / 5 |
| final | observed | lead_only | base_stock | avg_inventory_units | 49 | +4.2720 | [+2.4212, +6.5503] | 4 / 44 |
| final | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0350 | [+0.0229, +0.0481] | 29 / 5 |
| final | observed | lead_only | order_up_to | shortage | 49 | -72.5472 | [-94.7063, -53.1315] | 46 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 49 | +11.9541 | [+7.4107, +17.6481] | 0 / 48 |
| final | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1824 | [+0.1564, +0.2081] | 46 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 49 | -13.2799 | [-20.3947, -7.2497] | 26 / 5 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +3.8674 | [+2.1585, +6.0794] | 2 / 44 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0251 | [+0.0141, +0.0371] | 26 / 5 |
| final | observed | mild_lead | periodic:1 | shortage | 49 | -12.1185 | [-19.1388, -5.6622] | 26 / 10 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +3.8454 | [+2.2210, +5.9104] | 1 / 46 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0220 | [+0.0110, +0.0340] | 26 / 10 |
| final | observed | mild_lead | base_stock | shortage | 49 | -12.1185 | [-18.8713, -5.6851] | 26 / 10 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 49 | +3.8404 | [+2.2231, +5.8763] | 1 / 46 |
| final | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0220 | [+0.0109, +0.0337] | 26 / 10 |
| final | observed | mild_lead | order_up_to | shortage | 49 | -75.6983 | [-104.2192, -51.9488] | 46 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +11.5996 | [+7.0256, +17.7683] | 0 / 47 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1730 | [+0.1494, +0.1970] | 46 / 0 |
| final | observed | stable | reorder_point | shortage | 49 | -2.3792 | [-6.2342, -0.0982] | 11 / 2 |
| final | observed | stable | reorder_point | avg_inventory_units | 49 | +0.4306 | [-0.1789, +1.1570] | 17 / 24 |
| final | observed | stable | reorder_point | service_unit_fill | 49 | +0.0029 | [-0.0004, +0.0062] | 11 / 2 |
| final | observed | stable | periodic:1 | shortage | 49 | -2.1029 | [-5.8389, +0.1674] | 10 / 8 |
| final | observed | stable | periodic:1 | avg_inventory_units | 49 | +0.3961 | [-0.1936, +1.1060] | 19 / 24 |
| final | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0011 | [-0.0024, +0.0048] | 10 / 8 |
| final | observed | stable | base_stock | shortage | 49 | -2.1029 | [-5.8066, +0.1883] | 10 / 8 |
| final | observed | stable | base_stock | avg_inventory_units | 49 | +0.3903 | [-0.2036, +1.0892] | 19 / 24 |
| final | observed | stable | base_stock | service_unit_fill | 49 | +0.0011 | [-0.0026, +0.0047] | 10 / 8 |
| final | observed | stable | order_up_to | shortage | 49 | -49.6241 | [-69.2958, -34.0039] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 49 | +10.7335 | [+5.9250, +17.6487] | 0 / 47 |
| final | observed | stable | order_up_to | service_unit_fill | 49 | +0.1274 | [+0.1072, +0.1480] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 49 | -31.0998 | [-49.1481, -16.1296] | 32 / 3 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 49 | +10.3210 | [+5.9590, +15.7420] | 0 / 43 |
| final | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0466 | [+0.0314, +0.0621] | 32 / 3 |
| final | observed | uncertain | periodic:1 | shortage | 49 | -30.7893 | [-49.4730, -15.6587] | 32 / 4 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +10.2434 | [+5.7929, +15.8074] | 3 / 44 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0448 | [+0.0295, +0.0612] | 32 / 4 |
| final | observed | uncertain | base_stock | shortage | 49 | -26.4964 | [-43.2953, -12.8031] | 30 / 10 |
| final | observed | uncertain | base_stock | avg_inventory_units | 49 | +9.4144 | [+5.0155, +14.9148] | 7 / 40 |
| final | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0380 | [+0.0223, +0.0544] | 30 / 10 |
| final | observed | uncertain | order_up_to | shortage | 49 | -84.3985 | [-117.6301, -56.2460] | 46 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 49 | +16.3115 | [+10.4755, +23.2120] | 0 / 47 |
| final | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1834 | [+0.1588, +0.2074] | 46 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 43 | -7.4049 | [-13.9169, -2.4488] | 14 / 1 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 43 | +8.0950 | [+4.3678, +12.7179] | 3 / 37 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 43 | +0.0137 | [+0.0054, +0.0240] | 14 / 1 |
| val1 | observed | fill_only | periodic:1 | shortage | 43 | -6.8749 | [-13.3604, -1.9532] | 14 / 4 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 43 | +7.9478 | [+4.3376, +12.4119] | 7 / 36 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 43 | +0.0123 | [+0.0038, +0.0226] | 14 / 4 |
| val1 | observed | fill_only | base_stock | shortage | 43 | -5.5841 | [-12.3076, -0.7102] | 10 / 11 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 43 | +6.6467 | [+3.3814, +10.7145] | 14 / 29 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 43 | +0.0092 | [+0.0010, +0.0192] | 10 / 11 |
| val1 | observed | fill_only | order_up_to | shortage | 43 | -52.2381 | [-71.5785, -35.6282] | 41 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 43 | +19.2212 | [+11.2745, +31.8102] | 0 / 43 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 43 | +0.1346 | [+0.1135, +0.1567] | 41 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 43 | -11.9548 | [-19.2762, -6.0094] | 22 / 0 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 43 | +9.9673 | [+3.3596, +21.0936] | 4 / 37 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 43 | +0.0285 | [+0.0178, +0.0405] | 22 / 0 |
| val1 | observed | lead_only | periodic:1 | shortage | 43 | -10.9771 | [-18.9803, -4.8534] | 21 / 3 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 43 | +9.8484 | [+3.2930, +21.5138] | 4 / 37 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 43 | +0.0262 | [+0.0154, +0.0381] | 21 / 3 |
| val1 | observed | lead_only | base_stock | shortage | 43 | -10.8181 | [-18.4588, -4.8008] | 21 / 4 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 43 | +9.8536 | [+3.2539, +21.1357] | 4 / 37 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 43 | +0.0251 | [+0.0139, +0.0367] | 21 / 4 |
| val1 | observed | lead_only | order_up_to | shortage | 43 | -64.9518 | [-87.2108, -46.3039] | 42 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 43 | +19.7643 | [+8.6986, +39.0593] | 0 / 43 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 43 | +0.1714 | [+0.1472, +0.1945] | 42 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 43 | -7.7759 | [-13.9417, -2.8791] | 16 / 3 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 43 | +4.6342 | [+2.4514, +7.3954] | 1 / 39 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 43 | +0.0156 | [+0.0080, +0.0244] | 16 / 3 |
| val1 | observed | mild_lead | periodic:1 | shortage | 43 | -6.5932 | [-12.2826, -1.8167] | 14 / 6 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 43 | +4.5271 | [+2.4243, +7.3029] | 5 / 37 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 43 | +0.0138 | [+0.0060, +0.0222] | 14 / 6 |
| val1 | observed | mild_lead | base_stock | shortage | 43 | -6.4341 | [-12.5650, -1.7494] | 14 / 7 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 43 | +4.5271 | [+2.4597, +7.3843] | 5 / 37 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 43 | +0.0127 | [+0.0045, +0.0217] | 14 / 7 |
| val1 | observed | mild_lead | order_up_to | shortage | 43 | -57.0291 | [-76.6095, -39.9490] | 42 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 43 | +14.8800 | [+8.3445, +25.0017] | 0 / 43 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 43 | +0.1504 | [+0.1311, +0.1706] | 42 / 0 |
| val1 | observed | stable | reorder_point | shortage | 43 | -0.1793 | [-1.0433, +0.6792] | 5 / 4 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 43 | +1.3942 | [+0.5243, +2.5304] | 6 / 26 |
| val1 | observed | stable | reorder_point | service_unit_fill | 43 | +0.0015 | [-0.0014, +0.0047] | 5 / 4 |
| val1 | observed | stable | periodic:1 | shortage | 43 | +1.0631 | [-0.6428, +3.2320] | 5 / 5 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 43 | +1.2510 | [+0.3734, +2.3679] | 12 / 26 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 43 | -0.0005 | [-0.0037, +0.0028] | 5 / 5 |
| val1 | observed | stable | base_stock | shortage | 43 | +1.0724 | [-0.6169, +3.2060] | 5 / 6 |
| val1 | observed | stable | base_stock | avg_inventory_units | 43 | +1.2416 | [+0.3326, +2.3852] | 12 / 26 |
| val1 | observed | stable | base_stock | service_unit_fill | 43 | -0.0005 | [-0.0038, +0.0028] | 5 / 6 |
| val1 | observed | stable | order_up_to | shortage | 43 | -45.2494 | [-61.3814, -30.9091] | 41 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 43 | +13.7282 | [+7.2359, +24.1274] | 0 / 43 |
| val1 | observed | stable | order_up_to | service_unit_fill | 43 | +0.1240 | [+0.1033, +0.1458] | 41 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 43 | -14.3685 | [-27.4796, -4.0714] | 19 / 5 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 43 | +20.3497 | [+4.8803, +46.9015] | 5 / 34 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 43 | +0.0283 | [+0.0116, +0.0474] | 19 / 5 |
| val1 | observed | uncertain | periodic:1 | shortage | 43 | -12.6018 | [-25.3586, -2.2104] | 17 / 11 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 43 | +20.1962 | [+4.8997, +46.4206] | 7 / 35 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 43 | +0.0239 | [+0.0071, +0.0431] | 17 / 11 |
| val1 | observed | uncertain | base_stock | shortage | 43 | -10.6390 | [-23.0191, -0.4801] | 16 / 17 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 43 | +19.0265 | [+4.2183, +45.1677] | 13 / 30 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 43 | +0.0196 | [+0.0026, +0.0384] | 16 / 17 |
| val1 | observed | uncertain | order_up_to | shortage | 43 | -62.2676 | [-83.2967, -43.4200] | 42 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 43 | +29.1092 | [+9.7884, +63.1264] | 0 / 43 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 43 | +0.1630 | [+0.1391, +0.1876] | 42 / 0 |
| val2 | observed | fill_only | reorder_point | shortage | 49 | -4.4228 | [-8.3698, -1.1063] | 19 / 4 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 49 | +12.3796 | [+6.9966, +19.1487] | 7 / 41 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0095 | [+0.0034, +0.0164] | 19 / 4 |
| val2 | observed | fill_only | periodic:1 | shortage | 49 | -4.2693 | [-8.2433, -1.0634] | 20 / 4 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +12.2490 | [+6.9029, +18.9236] | 8 / 41 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0088 | [+0.0027, +0.0155] | 20 / 4 |
| val2 | observed | fill_only | base_stock | shortage | 49 | -2.7358 | [-6.0479, +0.0849] | 14 / 12 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 49 | +10.7618 | [+5.8392, +16.8986] | 13 / 36 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0054 | [-0.0004, +0.0118] | 14 / 12 |
| val2 | observed | fill_only | order_up_to | shortage | 49 | -46.2079 | [-64.4667, -31.6268] | 47 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 49 | +23.3544 | [+13.8878, +36.2726] | 0 / 49 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1330 | [+0.1134, +0.1523] | 47 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 49 | -16.4176 | [-26.2246, -8.3086] | 31 / 3 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 49 | +6.0977 | [+3.6199, +9.0279] | 6 / 42 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0381 | [+0.0266, +0.0492] | 31 / 3 |
| val2 | observed | lead_only | periodic:1 | shortage | 49 | -16.0095 | [-26.2674, -7.9319] | 30 / 6 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +5.8618 | [+3.3825, +8.6607] | 8 / 41 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0358 | [+0.0250, +0.0469] | 30 / 6 |
| val2 | observed | lead_only | base_stock | shortage | 49 | -16.0095 | [-26.4964, -8.0309] | 30 / 6 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 49 | +5.8618 | [+3.3917, +8.7258] | 8 / 41 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0358 | [+0.0246, +0.0473] | 30 / 6 |
| val2 | observed | lead_only | order_up_to | shortage | 49 | -72.9807 | [-100.9689, -49.9132] | 48 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 49 | +15.5860 | [+9.4958, +23.2896] | 0 / 49 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1971 | [+0.1771, +0.2167] | 48 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 49 | -11.4793 | [-20.6191, -4.1541] | 24 / 2 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +4.7896 | [+2.2863, +7.5509] | 6 / 42 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0219 | [+0.0128, +0.0313] | 24 / 2 |
| val2 | observed | mild_lead | periodic:1 | shortage | 49 | -11.1293 | [-20.6332, -3.9682] | 23 / 6 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +4.5178 | [+2.0850, +7.1879] | 9 / 40 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0199 | [+0.0108, +0.0296] | 23 / 6 |
| val2 | observed | mild_lead | base_stock | shortage | 49 | -11.1293 | [-21.1931, -3.8277] | 23 / 6 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 49 | +4.5178 | [+2.2202, +7.1999] | 9 / 40 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0199 | [+0.0107, +0.0302] | 23 / 6 |
| val2 | observed | mild_lead | order_up_to | shortage | 49 | -63.6006 | [-93.6556, -41.9961] | 47 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +15.3336 | [+9.0520, +24.2034] | 0 / 49 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1660 | [+0.1461, +0.1856] | 47 / 0 |
| val2 | observed | stable | reorder_point | shortage | 49 | -0.6310 | [-1.4456, -0.0025] | 6 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 49 | +1.2190 | [+0.3604, +2.3070] | 9 / 32 |
| val2 | observed | stable | reorder_point | service_unit_fill | 49 | +0.0026 | [-0.0003, +0.0061] | 6 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 49 | -0.3860 | [-1.2694, +0.3034] | 5 / 6 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 49 | +0.9309 | [+0.1613, +1.9589] | 15 / 32 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0012 | [-0.0022, +0.0050] | 5 / 6 |
| val2 | observed | stable | base_stock | shortage | 49 | -0.3860 | [-1.2051, +0.3201] | 5 / 6 |
| val2 | observed | stable | base_stock | avg_inventory_units | 49 | +0.9309 | [+0.1412, +1.9620] | 15 / 32 |
| val2 | observed | stable | base_stock | service_unit_fill | 49 | +0.0012 | [-0.0020, +0.0050] | 5 / 6 |
| val2 | observed | stable | order_up_to | shortage | 49 | -42.7299 | [-58.4713, -30.0020] | 47 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 49 | +13.5786 | [+7.9823, +21.7351] | 0 / 49 |
| val2 | observed | stable | order_up_to | service_unit_fill | 49 | +0.1278 | [+0.1089, +0.1471] | 47 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 49 | -11.7348 | [-17.0476, -7.0509] | 30 / 2 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 49 | +9.9876 | [+6.5731, +13.8813] | 4 / 43 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0341 | [+0.0214, +0.0478] | 30 / 2 |
| val2 | observed | uncertain | periodic:1 | shortage | 49 | -11.6154 | [-16.9460, -6.7802] | 29 / 4 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +9.5937 | [+6.1206, +13.5814] | 6 / 43 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0335 | [+0.0212, +0.0469] | 29 / 4 |
| val2 | observed | uncertain | base_stock | shortage | 49 | -8.8654 | [-13.7624, -4.3614] | 24 / 16 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 49 | +8.5741 | [+5.1848, +12.3897] | 8 / 41 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0268 | [+0.0141, +0.0396] | 24 / 16 |
| val2 | observed | uncertain | order_up_to | shortage | 49 | -68.3678 | [-89.0744, -50.1911] | 48 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 49 | +18.0311 | [+12.4714, +24.5489] | 0 / 49 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1897 | [+0.1697, +0.2110] | 48 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 725/750 complete, 0 infeasible, 0 abstained; gated: 725/750 complete, 0 infeasible, 0 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 725/750 complete, 0 infeasible, 0 abstained; reorder_point: 725/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 125
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +66.059 (fill 0.964 vs 0.946, inventory 68.34 vs 25.22, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +57.603 (fill 0.742 vs 0.723, inventory 20.70 vs 8.45, retained incumbent on None reviews)
- val2/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +56.300 (fill 0.950 vs 0.950, inventory 174.91 vs 71.79, retained incumbent on None reviews)
- val1/observed/fill_only store TX_3 product HOBBIES_1_029: ZAAD minus reorder_point = +55.840 (fill 0.913 vs 0.913, inventory 70.17 vs 38.87, retained incumbent on None reviews)
- val2/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +54.670 (fill 0.950 vs 0.950, inventory 165.79 vs 73.67, retained incumbent on None reviews)
- val1/observed/uncertain store TX_3 product HOBBIES_1_029: ZAAD minus order_up_to = +41.839 (fill 0.913 vs 0.808, inventory 53.08 vs 15.50, retained incumbent on None reviews)
- final/observed/fill_only store CA_4 product HOBBIES_1_158: ZAAD minus order_up_to = +41.306 (fill 0.981 vs 0.949, inventory 12.79 vs 4.38, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product HOUSEHOLD_1_456: ZAAD minus order_up_to = +40.725 (fill 0.526 vs 0.429, inventory 24.44 vs 15.20, retained incumbent on None reviews)
- final/observed/uncertain store CA_3 product HOBBIES_1_210: ZAAD minus order_up_to = +40.649 (fill 0.749 vs 0.641, inventory 16.24 vs 6.07, retained incumbent on None reviews)
- val2/observed/uncertain store WI_1 product FOODS_3_288: ZAAD minus base_stock = +39.696 (fill 0.834 vs 0.844, inventory 58.98 vs 27.43, retained incumbent on None reviews)
