# Walmart M5 (Experiment A) results: stage `fifty_no_incumbent`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `dcf0228da853`, selection `8b6067be83a4`; 3750 runs, 3625 complete, 125 not complete; wall 3184 s, peak RSS 238 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 49/50 | 395.376 | 412.059 | 396.286 | 2.6838 | 35.122 | 0.927 | 14.801 | 19.903 | 1.9 | 10.8 |  | 0.47 |
| final | observed | fill_only | gated | 49/50 | 393.860 | 413.119 | 418.531 | 5.1236 | 24.042 | 0.948 | 9.924 | 35.902 | 1.2 | 8.4 | 0.46 | 5.08 |
| final | observed | fill_only | order_up_to | 49/50 | 401.208 | 413.216 | 330.587 | 1.2199 | 82.664 | 0.803 | 36.484 | 9.640 | 4.3 | 10.6 |  | 0.23 |
| final | observed | fill_only | periodic:1 | 49/50 | 395.587 | 411.668 | 390.534 | 2.4697 | 37.946 | 0.922 | 16.002 | 18.467 | 2.0 | 11.2 |  | 0.04 |
| final | observed | fill_only | reorder_point | 49/50 | 395.534 | 411.598 | 390.147 | 2.4615 | 38.188 | 0.921 | 16.072 | 18.357 | 2.1 | 10.4 |  | 0.04 |
| final | observed | lead_only | base_stock | 49/50 | 371.213 | 387.549 | 326.700 | 2.3859 | 79.127 | 0.847 | 29.439 | 17.012 | 2.9 | 10.6 |  | 0.46 |
| final | observed | lead_only | gated | 49/50 | 363.966 | 387.280 | 391.483 | 4.4920 | 44.281 | 0.916 | 13.855 | 29.781 | 1.7 | 10.4 | 0.43 | 3.71 |
| final | observed | lead_only | order_up_to | 49/50 | 386.345 | 398.102 | 262.188 | 1.2238 | 135.076 | 0.700 | 55.971 | 9.329 | 5.4 | 10.0 |  | 0.23 |
| final | observed | lead_only | periodic:1 | 49/50 | 371.212 | 387.548 | 326.700 | 2.3850 | 79.127 | 0.847 | 29.439 | 17.006 | 2.9 | 10.6 |  | 0.04 |
| final | observed | lead_only | reorder_point | 49/50 | 371.396 | 387.671 | 325.875 | 2.3772 | 79.799 | 0.844 | 29.939 | 16.930 | 3.0 | 9.6 |  | 0.04 |
| final | observed | mild_lead | base_stock | 49/50 | 369.145 | 386.641 | 337.853 | 2.3176 | 72.149 | 0.858 | 28.304 | 17.299 | 2.9 | 10.7 |  | 0.48 |
| final | observed | mild_lead | gated | 49/50 | 362.165 | 382.765 | 376.979 | 3.6809 | 42.457 | 0.907 | 16.634 | 25.597 | 1.9 | 10.8 | 0.47 | 3.85 |
| final | observed | mild_lead | order_up_to | 49/50 | 386.627 | 399.733 | 269.032 | 1.1985 | 135.729 | 0.707 | 56.303 | 9.539 | 5.2 | 10.1 |  | 0.23 |
| final | observed | mild_lead | periodic:1 | 49/50 | 369.144 | 386.640 | 337.853 | 2.3168 | 72.149 | 0.858 | 28.304 | 17.294 | 2.9 | 10.7 |  | 0.03 |
| final | observed | mild_lead | reorder_point | 49/50 | 369.483 | 386.947 | 336.848 | 2.3135 | 73.311 | 0.855 | 28.854 | 17.272 | 3.0 | 9.6 |  | 0.04 |
| final | observed | stable | base_stock | 49/50 | 358.202 | 374.709 | 358.305 | 2.6597 | 34.957 | 0.929 | 14.820 | 19.899 | 1.9 | 10.9 |  | 0.48 |
| final | observed | stable | gated | 49/50 | 356.956 | 374.573 | 369.662 | 3.1371 | 28.400 | 0.940 | 11.297 | 24.110 | 1.6 | 10.9 | 0.23 | 3.65 |
| final | observed | stable | order_up_to | 49/50 | 370.486 | 382.334 | 299.205 | 1.1951 | 82.478 | 0.803 | 36.904 | 9.555 | 4.5 | 10.5 |  | 0.22 |
| final | observed | stable | periodic:1 | 49/50 | 358.201 | 374.708 | 358.305 | 2.6589 | 34.957 | 0.929 | 14.820 | 19.893 | 1.9 | 10.8 |  | 0.03 |
| final | observed | stable | reorder_point | 49/50 | 358.264 | 374.725 | 357.843 | 2.6466 | 35.233 | 0.927 | 15.207 | 19.858 | 2.0 | 9.9 |  | 0.04 |
| final | observed | uncertain | base_stock | 49/50 | 420.014 | 436.507 | 355.912 | 2.0804 | 100.188 | 0.815 | 38.578 | 15.586 | 3.5 | 10.6 |  | 0.44 |
| final | observed | uncertain | gated | 49/50 | 418.738 | 441.768 | 431.767 | 6.0513 | 56.007 | 0.885 | 21.196 | 39.750 | 2.0 | 7.8 | 0.40 | 2.79 |
| final | observed | uncertain | order_up_to | 49/50 | 426.793 | 438.600 | 280.452 | 1.1152 | 158.091 | 0.670 | 61.663 | 8.689 | 5.7 | 10.0 |  | 0.22 |
| final | observed | uncertain | periodic:1 | 49/50 | 419.939 | 435.828 | 348.313 | 1.9596 | 104.481 | 0.808 | 40.046 | 14.757 | 3.5 | 11.1 |  | 0.04 |
| final | observed | uncertain | reorder_point | 49/50 | 419.929 | 435.813 | 347.980 | 1.9472 | 104.792 | 0.806 | 40.128 | 14.679 | 3.5 | 10.0 |  | 0.03 |
| val1 | observed | fill_only | base_stock | 43/50 | 313.839 | 328.638 | 299.669 | 3.4418 | 44.542 | 0.912 | 15.305 | 23.780 | 1.5 | 10.4 |  | 0.48 |
| val1 | observed | fill_only | gated | 43/50 | 320.022 | 339.145 | 339.045 | 5.6804 | 34.673 | 0.931 | 12.196 | 37.658 | 1.1 | 8.6 | 0.43 | 4.87 |
| val1 | observed | fill_only | order_up_to | 43/50 | 318.937 | 328.548 | 231.158 | 1.8428 | 91.196 | 0.786 | 33.631 | 11.206 | 4.3 | 10.1 |  | 0.23 |
| val1 | observed | fill_only | periodic:1 | 43/50 | 314.094 | 328.438 | 296.265 | 3.2682 | 45.832 | 0.908 | 15.739 | 22.479 | 1.6 | 11.0 |  | 0.03 |
| val1 | observed | fill_only | reorder_point | 43/50 | 314.219 | 328.508 | 295.584 | 3.2231 | 46.362 | 0.907 | 15.880 | 22.332 | 1.6 | 10.0 |  | 0.04 |
| val1 | observed | lead_only | base_stock | 43/50 | 291.147 | 306.123 | 253.132 | 2.9324 | 69.928 | 0.833 | 26.700 | 20.053 | 2.8 | 10.2 |  | 0.46 |
| val1 | observed | lead_only | gated | 43/50 | 289.251 | 311.473 | 311.354 | 5.1742 | 50.528 | 0.885 | 19.781 | 39.270 | 1.9 | 10.0 | 0.44 | 3.54 |
| val1 | observed | lead_only | order_up_to | 43/50 | 305.541 | 315.448 | 186.886 | 1.6881 | 124.062 | 0.687 | 48.180 | 10.142 | 5.5 | 9.6 |  | 0.22 |
| val1 | observed | lead_only | periodic:1 | 43/50 | 291.195 | 306.171 | 253.020 | 2.9331 | 70.087 | 0.832 | 26.766 | 20.058 | 2.8 | 10.2 |  | 0.03 |
| val1 | observed | lead_only | reorder_point | 43/50 | 291.439 | 306.375 | 252.110 | 2.8885 | 71.065 | 0.830 | 27.264 | 19.939 | 2.8 | 9.0 |  | 0.04 |
| val1 | observed | mild_lead | base_stock | 43/50 | 290.071 | 305.208 | 257.159 | 3.0966 | 65.645 | 0.857 | 23.665 | 21.050 | 2.5 | 10.4 |  | 0.47 |
| val1 | observed | mild_lead | gated | 43/50 | 288.749 | 308.847 | 296.241 | 4.4558 | 53.062 | 0.886 | 19.013 | 33.738 | 2.0 | 10.3 | 0.44 | 3.62 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 303.282 | 313.426 | 193.618 | 1.7614 | 116.240 | 0.719 | 46.213 | 10.697 | 5.1 | 9.8 |  | 0.22 |
| val1 | observed | mild_lead | periodic:1 | 43/50 | 290.119 | 305.256 | 257.048 | 3.0966 | 65.804 | 0.856 | 23.732 | 21.050 | 2.5 | 10.4 |  | 0.04 |
| val1 | observed | mild_lead | reorder_point | 43/50 | 290.436 | 305.526 | 255.937 | 3.0684 | 66.986 | 0.854 | 24.229 | 20.943 | 2.5 | 9.1 |  | 0.03 |
| val1 | observed | stable | base_stock | 43/50 | 283.794 | 298.560 | 270.151 | 3.4535 | 43.820 | 0.913 | 15.148 | 23.624 | 1.5 | 10.6 |  | 0.49 |
| val1 | observed | stable | gated | 43/50 | 283.569 | 300.836 | 289.118 | 4.2900 | 38.469 | 0.924 | 13.577 | 27.893 | 1.3 | 10.2 | 0.16 | 3.08 |
| val1 | observed | stable | order_up_to | 43/50 | 295.439 | 304.992 | 208.409 | 1.8521 | 90.142 | 0.789 | 33.338 | 11.138 | 4.3 | 10.2 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 43/50 | 283.795 | 298.562 | 270.144 | 3.4521 | 43.829 | 0.913 | 15.152 | 23.615 | 1.5 | 10.5 |  | 0.03 |
| val1 | observed | stable | reorder_point | 43/50 | 284.111 | 298.827 | 268.974 | 3.4049 | 45.072 | 0.911 | 15.660 | 23.472 | 1.6 | 9.4 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 43/50 | 324.614 | 339.379 | 279.746 | 2.8625 | 75.876 | 0.832 | 28.988 | 20.024 | 3.0 | 10.4 |  | 0.44 |
| val1 | observed | uncertain | gated | 43/50 | 332.922 | 355.098 | 356.965 | 5.4673 | 48.751 | 0.887 | 20.044 | 47.233 | 1.9 | 8.2 | 0.37 | 2.87 |
| val1 | observed | uncertain | order_up_to | 43/50 | 329.280 | 338.971 | 206.158 | 1.6199 | 127.504 | 0.689 | 50.356 | 9.941 | 5.3 | 9.8 |  | 0.22 |
| val1 | observed | uncertain | periodic:1 | 43/50 | 324.494 | 338.905 | 275.808 | 2.7305 | 77.838 | 0.828 | 29.625 | 18.854 | 3.1 | 10.8 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 43/50 | 325.080 | 339.453 | 274.479 | 2.6930 | 79.605 | 0.823 | 30.305 | 18.701 | 3.1 | 9.7 |  | 0.03 |
| val2 | observed | fill_only | base_stock | 49/50 | 321.940 | 336.189 | 331.600 | 2.6510 | 23.003 | 0.915 | 16.175 | 21.610 | 1.7 | 11.2 |  | 0.51 |
| val2 | observed | fill_only | gated | 49/50 | 324.283 | 341.317 | 352.900 | 5.1143 | 17.866 | 0.929 | 12.802 | 40.670 | 1.3 | 8.4 | 0.47 | 4.68 |
| val2 | observed | fill_only | order_up_to | 49/50 | 325.738 | 335.064 | 266.700 | 1.0675 | 66.475 | 0.787 | 38.713 | 9.017 | 4.5 | 11.1 |  | 0.24 |
| val2 | observed | fill_only | periodic:1 | 49/50 | 321.823 | 335.628 | 327.682 | 2.4652 | 24.537 | 0.911 | 16.847 | 20.123 | 1.9 | 11.7 |  | 0.04 |
| val2 | observed | fill_only | reorder_point | 49/50 | 321.716 | 335.434 | 326.933 | 2.4482 | 24.690 | 0.911 | 17.273 | 19.992 | 1.8 | 10.7 |  | 0.04 |
| val2 | observed | lead_only | base_stock | 49/50 | 295.474 | 309.695 | 268.600 | 2.1361 | 60.062 | 0.834 | 33.226 | 17.279 | 3.1 | 10.9 |  | 0.46 |
| val2 | observed | lead_only | gated | 49/50 | 291.202 | 311.143 | 319.296 | 4.0363 | 35.989 | 0.892 | 22.550 | 32.127 | 1.9 | 10.8 | 0.47 | 3.90 |
| val2 | observed | lead_only | order_up_to | 49/50 | 310.951 | 320.408 | 202.595 | 0.9828 | 117.033 | 0.673 | 58.968 | 7.555 | 5.9 | 10.3 |  | 0.23 |
| val2 | observed | lead_only | periodic:1 | 49/50 | 295.474 | 309.695 | 268.600 | 2.1361 | 60.062 | 0.834 | 33.226 | 17.279 | 3.1 | 10.9 |  | 0.04 |
| val2 | observed | lead_only | reorder_point | 49/50 | 295.561 | 309.715 | 267.925 | 2.1113 | 60.470 | 0.832 | 33.695 | 17.043 | 3.2 | 9.5 |  | 0.04 |
| val2 | observed | mild_lead | base_stock | 49/50 | 292.011 | 306.166 | 276.711 | 2.3650 | 47.833 | 0.854 | 25.856 | 19.241 | 2.7 | 11.1 |  | 0.47 |
| val2 | observed | mild_lead | gated | 49/50 | 289.787 | 307.819 | 309.473 | 3.6882 | 33.691 | 0.887 | 20.146 | 31.639 | 1.9 | 10.9 | 0.49 | 3.60 |
| val2 | observed | mild_lead | order_up_to | 49/50 | 305.941 | 315.332 | 213.656 | 1.0552 | 100.304 | 0.708 | 51.097 | 8.425 | 5.2 | 10.6 |  | 0.24 |
| val2 | observed | mild_lead | periodic:1 | 49/50 | 292.011 | 306.166 | 276.711 | 2.3650 | 47.833 | 0.854 | 25.856 | 19.241 | 2.7 | 11.1 |  | 0.04 |
| val2 | observed | mild_lead | reorder_point | 49/50 | 292.086 | 306.211 | 276.280 | 2.3424 | 48.183 | 0.852 | 26.010 | 18.969 | 2.8 | 9.8 |  | 0.04 |
| val2 | observed | stable | base_stock | 49/50 | 284.683 | 298.885 | 294.645 | 2.6848 | 22.408 | 0.915 | 15.135 | 21.264 | 1.6 | 11.3 |  | 0.49 |
| val2 | observed | stable | gated | 49/50 | 284.657 | 299.984 | 302.956 | 3.2496 | 19.844 | 0.923 | 13.573 | 26.287 | 1.5 | 11.0 | 0.22 | 3.13 |
| val2 | observed | stable | order_up_to | 49/50 | 295.230 | 304.427 | 237.209 | 1.0819 | 64.751 | 0.789 | 37.199 | 8.616 | 4.5 | 11.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 49/50 | 284.683 | 298.885 | 294.645 | 2.6848 | 22.408 | 0.915 | 15.135 | 21.264 | 1.6 | 11.3 |  | 0.03 |
| val2 | observed | stable | reorder_point | 49/50 | 284.723 | 298.869 | 294.136 | 2.6625 | 22.653 | 0.914 | 15.264 | 20.975 | 1.7 | 10.1 |  | 0.04 |
| val2 | observed | uncertain | base_stock | 49/50 | 322.045 | 335.970 | 302.117 | 2.2763 | 51.376 | 0.836 | 30.418 | 17.551 | 3.1 | 10.9 |  | 0.49 |
| val2 | observed | uncertain | gated | 49/50 | 324.194 | 344.285 | 357.783 | 5.8446 | 29.833 | 0.890 | 18.514 | 42.860 | 1.8 | 7.8 | 0.44 | 2.82 |
| val2 | observed | uncertain | order_up_to | 49/50 | 331.443 | 340.849 | 228.738 | 1.0340 | 110.878 | 0.673 | 59.138 | 8.094 | 5.6 | 10.5 |  | 0.24 |
| val2 | observed | uncertain | periodic:1 | 49/50 | 322.453 | 335.990 | 297.778 | 2.1330 | 54.126 | 0.829 | 31.938 | 16.532 | 3.3 | 11.5 |  | 0.04 |
| val2 | observed | uncertain | reorder_point | 49/50 | 322.357 | 335.837 | 297.248 | 2.1076 | 54.245 | 0.829 | 32.069 | 16.138 | 3.3 | 10.3 |  | 0.04 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 49 | -1.674 | [-3.960, +0.748] | [-5.318, +1.905] | 27 / 21 / 1 | 0.471 |
| final | observed | fill_only | periodic:1 | 49 | -1.727 | [-4.078, +0.587] | [-5.329, +1.720] | 27 / 22 / 0 | 0.568 |
| final | observed | fill_only | base_stock | 49 | -1.516 | [-3.766, +0.730] | [-4.989, +1.782] | 28 / 21 / 0 | 0.392 |
| final | observed | fill_only | order_up_to | 49 | -7.348 | [-11.218, -3.828] | [-13.509, -2.306] | 29 / 19 / 1 | 0.193 |
| final | observed | lead_only | reorder_point | 49 | -7.430 | [-9.979, -4.963] | [-11.601, -3.795] | 35 / 13 / 1 | 0.002 |
| final | observed | lead_only | periodic:1 | 49 | -7.246 | [-9.903, -4.852] | [-11.552, -3.837] | 36 / 13 / 0 | 0.001 |
| final | observed | lead_only | base_stock | 49 | -7.247 | [-9.962, -4.792] | [-11.601, -3.699] | 36 / 13 / 0 | 0.001 |
| final | observed | lead_only | order_up_to | 49 | -22.379 | [-27.451, -17.642] | [-30.495, -15.584] | 45 / 3 / 1 | 0.0 |
| final | observed | mild_lead | reorder_point | 49 | -7.317 | [-10.400, -4.644] | [-12.435, -3.651] | 36 / 12 / 1 | 0.001 |
| final | observed | mild_lead | periodic:1 | 49 | -6.979 | [-9.926, -4.257] | [-11.658, -3.184] | 36 / 13 / 0 | 0.001 |
| final | observed | mild_lead | base_stock | 49 | -6.980 | [-10.063, -4.221] | [-11.774, -3.153] | 36 / 13 / 0 | 0.001 |
| final | observed | mild_lead | order_up_to | 49 | -24.462 | [-31.196, -18.182] | [-35.344, -15.645] | 46 / 2 / 1 | 0.0 |
| final | observed | stable | reorder_point | 49 | -1.307 | [-2.656, -0.114] | [-3.733, +0.141] | 28 / 20 / 1 | 0.312 |
| final | observed | stable | periodic:1 | 49 | -1.245 | [-2.572, -0.050] | [-3.552, +0.225] | 28 / 21 / 0 | 0.392 |
| final | observed | stable | base_stock | 49 | -1.246 | [-2.573, -0.078] | [-3.565, +0.163] | 28 / 21 / 0 | 0.392 |
| final | observed | stable | order_up_to | 49 | -13.530 | [-17.681, -9.882] | [-20.357, -8.546] | 44 / 4 / 1 | 0.0 |
| final | observed | uncertain | reorder_point | 49 | -1.192 | [-6.556, +4.115] | [-9.566, +6.822] | 20 / 28 / 1 | 0.312 |
| final | observed | uncertain | periodic:1 | 49 | -1.201 | [-6.523, +3.983] | [-9.488, +6.978] | 21 / 28 / 0 | 0.392 |
| final | observed | uncertain | base_stock | 49 | -1.276 | [-6.514, +3.872] | [-9.625, +6.781] | 21 / 28 / 0 | 0.392 |
| final | observed | uncertain | order_up_to | 49 | -8.056 | [-14.570, -1.871] | [-19.227, +0.834] | 30 / 18 / 1 | 0.111 |
| val1 | observed | fill_only | reorder_point | 43 | +5.803 | [+2.447, +9.238] | [+1.084, +11.414] | 18 / 25 / 0 | 0.36 |
| val1 | observed | fill_only | periodic:1 | 43 | +5.928 | [+2.730, +9.493] | [+1.179, +11.628] | 18 / 25 / 0 | 0.36 |
| val1 | observed | fill_only | base_stock | 43 | +6.182 | [+2.946, +9.723] | [+1.580, +11.838] | 18 / 25 / 0 | 0.36 |
| val1 | observed | fill_only | order_up_to | 43 | +1.085 | [-2.551, +4.806] | [-4.315, +6.976] | 22 / 21 / 0 | 1.0 |
| val1 | observed | lead_only | reorder_point | 43 | -2.188 | [-4.078, -0.254] | [-5.013, +0.697] | 26 / 17 / 0 | 0.222 |
| val1 | observed | lead_only | periodic:1 | 43 | -1.944 | [-3.733, -0.082] | [-4.733, +0.896] | 26 / 17 / 0 | 0.222 |
| val1 | observed | lead_only | base_stock | 43 | -1.896 | [-3.721, -0.054] | [-4.654, +0.890] | 25 / 18 / 0 | 0.36 |
| val1 | observed | lead_only | order_up_to | 43 | -16.290 | [-20.353, -12.331] | [-23.066, -10.647] | 39 / 4 / 0 | 0.0 |
| val1 | observed | mild_lead | reorder_point | 43 | -1.688 | [-3.664, +0.188] | [-4.760, +1.199] | 23 / 20 / 0 | 0.761 |
| val1 | observed | mild_lead | periodic:1 | 43 | -1.371 | [-3.178, +0.351] | [-4.104, +1.276] | 22 / 21 / 0 | 1.0 |
| val1 | observed | mild_lead | base_stock | 43 | -1.323 | [-3.067, +0.367] | [-4.053, +1.306] | 21 / 22 / 0 | 1.0 |
| val1 | observed | mild_lead | order_up_to | 43 | -14.534 | [-18.529, -10.755] | [-21.038, -9.053] | 39 / 4 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 43 | -0.542 | [-2.368, +1.271] | [-3.378, +2.334] | 13 / 30 / 0 | 0.014 |
| val1 | observed | stable | periodic:1 | 43 | -0.226 | [-1.889, +1.401] | [-2.829, +2.292] | 13 / 30 / 0 | 0.014 |
| val1 | observed | stable | base_stock | 43 | -0.224 | [-1.848, +1.366] | [-2.860, +2.336] | 13 / 30 / 0 | 0.014 |
| val1 | observed | stable | order_up_to | 43 | -11.870 | [-15.493, -8.547] | [-17.925, -7.276] | 39 / 4 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 43 | +7.842 | [+2.433, +13.627] | [+0.070, +17.113] | 15 / 28 / 0 | 0.066 |
| val1 | observed | uncertain | periodic:1 | 43 | +8.428 | [+3.079, +13.945] | [+0.844, +17.514] | 15 / 28 / 0 | 0.066 |
| val1 | observed | uncertain | base_stock | 43 | +8.308 | [+3.181, +13.739] | [+1.123, +17.210] | 15 / 28 / 0 | 0.066 |
| val1 | observed | uncertain | order_up_to | 43 | +3.642 | [-3.005, +11.133] | [-6.110, +15.095] | 19 / 24 / 0 | 0.542 |
| val2 | observed | fill_only | reorder_point | 49 | +2.567 | [-0.445, +5.598] | [-2.242, +7.282] | 11 / 38 / 0 | 0.0 |
| val2 | observed | fill_only | periodic:1 | 49 | +2.460 | [-0.650, +5.474] | [-2.344, +7.064] | 11 / 38 / 0 | 0.0 |
| val2 | observed | fill_only | base_stock | 49 | +2.343 | [-0.727, +5.369] | [-2.483, +7.008] | 14 / 35 / 0 | 0.004 |
| val2 | observed | fill_only | order_up_to | 49 | -1.455 | [-5.177, +2.107] | [-7.372, +3.844] | 23 / 26 / 0 | 0.775 |
| val2 | observed | lead_only | reorder_point | 49 | -4.359 | [-6.279, -2.495] | [-7.397, -1.640] | 33 / 16 / 0 | 0.021 |
| val2 | observed | lead_only | periodic:1 | 49 | -4.272 | [-6.205, -2.350] | [-7.347, -1.489] | 32 / 17 / 0 | 0.044 |
| val2 | observed | lead_only | base_stock | 49 | -4.272 | [-6.176, -2.431] | [-7.172, -1.496] | 32 / 17 / 0 | 0.044 |
| val2 | observed | lead_only | order_up_to | 49 | -19.749 | [-24.854, -14.991] | [-27.998, -12.834] | 47 / 2 / 0 | 0.0 |
| val2 | observed | mild_lead | reorder_point | 49 | -2.299 | [-3.905, -0.774] | [-4.960, -0.090] | 29 / 20 / 0 | 0.253 |
| val2 | observed | mild_lead | periodic:1 | 49 | -2.224 | [-3.895, -0.681] | [-4.948, -0.045] | 28 / 21 / 0 | 0.392 |
| val2 | observed | mild_lead | base_stock | 49 | -2.224 | [-3.855, -0.659] | [-4.993, +0.003] | 28 / 21 / 0 | 0.392 |
| val2 | observed | mild_lead | order_up_to | 49 | -16.154 | [-21.122, -11.427] | [-24.196, -9.474] | 46 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 49 | -0.066 | [-0.397, +0.247] | [-0.595, +0.381] | 19 / 30 / 0 | 0.152 |
| val2 | observed | stable | periodic:1 | 49 | -0.026 | [-0.359, +0.270] | [-0.552, +0.403] | 19 / 30 / 0 | 0.152 |
| val2 | observed | stable | base_stock | 49 | -0.026 | [-0.347, +0.281] | [-0.547, +0.416] | 19 / 30 / 0 | 0.152 |
| val2 | observed | stable | order_up_to | 49 | -10.574 | [-13.292, -7.851] | [-14.999, -6.822] | 45 / 4 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 49 | +1.837 | [-0.378, +4.040] | [-1.530, +5.216] | 20 / 29 / 0 | 0.253 |
| val2 | observed | uncertain | periodic:1 | 49 | +1.740 | [-0.378, +3.929] | [-1.735, +5.352] | 20 / 29 / 0 | 0.253 |
| val2 | observed | uncertain | base_stock | 49 | +2.149 | [-0.027, +4.229] | [-1.260, +5.208] | 20 / 29 / 0 | 0.253 |
| val2 | observed | uncertain | order_up_to | 49 | -7.249 | [-11.268, -3.398] | [-13.548, -1.677] | 30 / 19 / 0 | 0.152 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 49 | -14.1456 | [-26.2486, -5.9647] | 32 / 3 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 49 | +17.5446 | [+10.4161, +26.6863] | 0 / 48 |
| final | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0275 | [+0.0168, +0.0394] | 32 / 3 |
| final | observed | fill_only | periodic:1 | shortage | 49 | -13.9039 | [-26.1350, -5.7788] | 31 / 3 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +17.4349 | [+10.3755, +26.1266] | 1 / 47 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0264 | [+0.0157, +0.0380] | 31 / 3 |
| final | observed | fill_only | base_stock | shortage | 49 | -11.0793 | [-22.0099, -3.8627] | 30 / 3 |
| final | observed | fill_only | base_stock | avg_inventory_units | 49 | +15.9991 | [+9.3502, +24.8022] | 2 / 46 |
| final | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0211 | [+0.0112, +0.0322] | 30 / 3 |
| final | observed | fill_only | order_up_to | shortage | 49 | -58.6219 | [-83.1839, -38.9096] | 46 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 49 | +26.2619 | [+15.9207, +40.3318] | 0 / 48 |
| final | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1453 | [+0.1211, +0.1701] | 46 / 0 |
| final | observed | lead_only | reorder_point | shortage | 49 | -35.5174 | [-51.3897, -22.4529] | 41 / 0 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 49 | +12.8507 | [+8.5143, +17.7892] | 0 / 48 |
| final | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0716 | [+0.0576, +0.0861] | 41 / 0 |
| final | observed | lead_only | periodic:1 | shortage | 49 | -34.8453 | [-50.6941, -22.1682] | 41 / 0 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +12.7750 | [+8.8250, +17.3431] | 0 / 48 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0684 | [+0.0545, +0.0829] | 41 / 0 |
| final | observed | lead_only | base_stock | shortage | 49 | -34.8453 | [-50.3228, -22.0433] | 41 / 0 |
| final | observed | lead_only | base_stock | avg_inventory_units | 49 | +12.7692 | [+8.6938, +17.7396] | 0 / 48 |
| final | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0684 | [+0.0544, +0.0825] | 41 / 0 |
| final | observed | lead_only | order_up_to | shortage | 49 | -90.7944 | [-120.6674, -65.0275] | 46 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 49 | +20.4513 | [+13.1505, +29.6538] | 0 / 48 |
| final | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.2158 | [+0.1887, +0.2424] | 46 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 49 | -30.8542 | [-47.8093, -17.2560] | 40 / 0 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +8.3249 | [+5.6156, +11.5535] | 0 / 48 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0516 | [+0.0387, +0.0647] | 40 / 0 |
| final | observed | mild_lead | periodic:1 | shortage | 49 | -29.6928 | [-46.9127, -15.9855] | 40 / 0 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +8.3029 | [+5.6047, +11.5460] | 0 / 48 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0484 | [+0.0359, +0.0614] | 40 / 0 |
| final | observed | mild_lead | base_stock | shortage | 49 | -29.6928 | [-47.1422, -16.1043] | 40 / 0 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 49 | +8.2980 | [+5.5819, +11.3280] | 0 / 48 |
| final | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0484 | [+0.0359, +0.0615] | 40 / 0 |
| final | observed | mild_lead | order_up_to | shortage | 49 | -93.2726 | [-130.5792, -62.1598] | 46 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +16.0572 | [+10.2279, +23.9328] | 0 / 48 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1994 | [+0.1735, +0.2243] | 46 / 0 |
| final | observed | stable | reorder_point | shortage | 49 | -6.8332 | [-14.9078, -2.2947] | 31 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 49 | +4.2516 | [+1.9143, +7.1079] | 6 / 42 |
| final | observed | stable | reorder_point | service_unit_fill | 49 | +0.0125 | [+0.0077, +0.0182] | 31 / 1 |
| final | observed | stable | periodic:1 | shortage | 49 | -6.5569 | [-14.4614, -2.0201] | 30 / 1 |
| final | observed | stable | periodic:1 | avg_inventory_units | 49 | +4.2172 | [+1.8464, +7.0596] | 6 / 42 |
| final | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0107 | [+0.0062, +0.0165] | 30 / 1 |
| final | observed | stable | base_stock | shortage | 49 | -6.5569 | [-14.5214, -2.0280] | 30 / 1 |
| final | observed | stable | base_stock | avg_inventory_units | 49 | +4.2113 | [+1.8965, +7.2111] | 6 / 42 |
| final | observed | stable | base_stock | service_unit_fill | 49 | +0.0107 | [+0.0061, +0.0162] | 30 / 1 |
| final | observed | stable | order_up_to | shortage | 49 | -54.0781 | [-77.0423, -36.2058] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 49 | +14.5545 | [+8.0843, +23.9707] | 0 / 48 |
| final | observed | stable | order_up_to | service_unit_fill | 49 | +0.1371 | [+0.1153, +0.1590] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 49 | -48.7845 | [-76.1186, -27.1043] | 40 / 0 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 49 | +25.0707 | [+15.8325, +35.9762] | 0 / 48 |
| final | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0786 | [+0.0623, +0.0951] | 40 / 0 |
| final | observed | uncertain | periodic:1 | shortage | 49 | -48.4740 | [-76.8848, -26.3118] | 40 / 0 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +24.9931 | [+15.6499, +36.0291] | 0 / 48 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0769 | [+0.0611, +0.0934] | 40 / 0 |
| final | observed | uncertain | base_stock | shortage | 49 | -44.1811 | [-70.3478, -23.5150] | 39 / 0 |
| final | observed | uncertain | base_stock | avg_inventory_units | 49 | +24.1641 | [+15.1258, +34.9406] | 0 / 48 |
| final | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0700 | [+0.0542, +0.0867] | 39 / 0 |
| final | observed | uncertain | order_up_to | shortage | 49 | -102.0832 | [-145.5923, -67.1146] | 46 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 49 | +31.0611 | [+19.8886, +44.6084] | 0 / 48 |
| final | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.2154 | [+0.1895, +0.2404] | 46 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 43 | -11.6896 | [-20.8217, -3.1696] | 19 / 3 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 43 | +15.3260 | [+9.5125, +22.3788] | 0 / 43 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 43 | +0.0244 | [+0.0113, +0.0385] | 19 / 3 |
| val1 | observed | fill_only | periodic:1 | shortage | 43 | -11.1596 | [-20.4246, -2.7226] | 19 / 3 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 43 | +15.1789 | [+9.4177, +22.0887] | 0 / 43 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 43 | +0.0229 | [+0.0104, +0.0367] | 19 / 3 |
| val1 | observed | fill_only | base_stock | shortage | 43 | -9.8688 | [-19.2343, -1.6111] | 16 / 4 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 43 | +13.8777 | [+8.5013, +20.6633] | 1 / 42 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 43 | +0.0198 | [+0.0073, +0.0323] | 16 / 4 |
| val1 | observed | fill_only | order_up_to | shortage | 43 | -56.5228 | [-79.1000, -38.2487] | 41 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 43 | +26.4522 | [+15.7128, +41.1282] | 0 / 43 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 43 | +0.1452 | [+0.1208, +0.1714] | 41 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 43 | -20.5365 | [-30.4444, -11.6214] | 31 / 1 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 43 | +19.3307 | [+8.4568, +34.7274] | 0 / 43 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 43 | +0.0547 | [+0.0394, +0.0696] | 31 / 1 |
| val1 | observed | lead_only | periodic:1 | shortage | 43 | -19.5588 | [-28.9979, -11.3337] | 31 / 1 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 43 | +19.2119 | [+8.3400, +35.7217] | 0 / 43 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 43 | +0.0524 | [+0.0379, +0.0672] | 31 / 1 |
| val1 | observed | lead_only | base_stock | shortage | 43 | -19.3998 | [-28.7382, -10.9708] | 30 / 2 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 43 | +19.2170 | [+8.3867, +34.9870] | 0 / 43 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 43 | +0.0513 | [+0.0366, +0.0659] | 30 / 2 |
| val1 | observed | lead_only | order_up_to | shortage | 43 | -73.5335 | [-97.6037, -52.8749] | 42 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 43 | +29.1278 | [+13.6651, +53.1779] | 0 / 43 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 43 | +0.1975 | [+0.1690, +0.2240] | 42 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 43 | -13.9242 | [-23.2361, -5.9020] | 27 / 3 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 43 | +12.7957 | [+5.2296, +25.5839] | 0 / 43 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 43 | +0.0322 | [+0.0198, +0.0451] | 27 / 3 |
| val1 | observed | mild_lead | periodic:1 | shortage | 43 | -12.7414 | [-20.9146, -5.0172] | 27 / 3 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 43 | +12.6886 | [+5.3338, +25.3373] | 0 / 43 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 43 | +0.0304 | [+0.0188, +0.0438] | 27 / 3 |
| val1 | observed | mild_lead | base_stock | shortage | 43 | -12.5824 | [-21.2295, -4.9786] | 27 / 3 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 43 | +12.6886 | [+5.2992, +25.8966] | 0 / 43 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 43 | +0.0293 | [+0.0173, +0.0420] | 27 / 3 |
| val1 | observed | mild_lead | order_up_to | shortage | 43 | -63.1773 | [-85.9391, -43.7290] | 42 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 43 | +23.0415 | [+11.1962, +43.6941] | 0 / 43 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 43 | +0.1670 | [+0.1440, +0.1910] | 42 / 0 |
| val1 | observed | stable | reorder_point | shortage | 43 | -6.6025 | [-15.6406, +0.9251] | 18 / 3 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 43 | +4.4213 | [+2.6926, +6.3708] | 1 / 42 |
| val1 | observed | stable | reorder_point | service_unit_fill | 43 | +0.0132 | [+0.0040, +0.0240] | 18 / 3 |
| val1 | observed | stable | periodic:1 | shortage | 43 | -5.3601 | [-13.2132, +1.3744] | 18 / 3 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 43 | +4.2781 | [+2.5964, +6.1345] | 1 / 42 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 43 | +0.0112 | [+0.0026, +0.0208] | 18 / 3 |
| val1 | observed | stable | base_stock | shortage | 43 | -5.3508 | [-13.0891, +1.2358] | 18 / 3 |
| val1 | observed | stable | base_stock | avg_inventory_units | 43 | +4.2687 | [+2.6068, +6.1936] | 1 / 42 |
| val1 | observed | stable | base_stock | service_unit_fill | 43 | +0.0111 | [+0.0027, +0.0211] | 18 / 3 |
| val1 | observed | stable | order_up_to | shortage | 43 | -51.6727 | [-72.6951, -33.8280] | 41 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 43 | +16.7554 | [+9.5793, +27.5982] | 0 / 43 |
| val1 | observed | stable | order_up_to | service_unit_fill | 43 | +0.1357 | [+0.1113, +0.1608] | 41 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 43 | -30.8536 | [-48.9568, -15.3298] | 28 / 4 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 43 | +28.5325 | [+11.5846, +57.6992] | 1 / 42 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 43 | +0.0634 | [+0.0420, +0.0862] | 28 / 4 |
| val1 | observed | uncertain | periodic:1 | shortage | 43 | -29.0869 | [-46.4229, -14.2499] | 28 / 4 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 43 | +28.3790 | [+11.4116, +56.9753] | 1 / 42 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 43 | +0.0591 | [+0.0388, +0.0807] | 28 / 4 |
| val1 | observed | uncertain | base_stock | shortage | 43 | -27.1241 | [-44.6477, -13.1844] | 28 / 4 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 43 | +27.2093 | [+10.9987, +55.9888] | 1 / 42 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 43 | +0.0547 | [+0.0356, +0.0745] | 28 / 4 |
| val1 | observed | uncertain | order_up_to | shortage | 43 | -78.7527 | [-108.5144, -53.1460] | 42 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 43 | +37.2920 | [+16.1823, +73.8706] | 0 / 43 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 43 | +0.1981 | [+0.1673, +0.2296] | 42 / 0 |
| val2 | observed | fill_only | reorder_point | shortage | 49 | -6.8240 | [-10.7570, -3.5767] | 28 / 0 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 49 | +20.6779 | [+11.4242, +33.0968] | 1 / 48 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0183 | [+0.0116, +0.0254] | 28 / 0 |
| val2 | observed | fill_only | periodic:1 | shortage | 49 | -6.6705 | [-10.6359, -3.4879] | 28 / 0 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +20.5472 | [+10.9393, +33.2436] | 2 / 47 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0176 | [+0.0112, +0.0244] | 28 / 0 |
| val2 | observed | fill_only | base_stock | shortage | 49 | -5.1370 | [-8.1991, -2.4822] | 26 / 0 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 49 | +19.0600 | [+10.3411, +30.6501] | 3 / 46 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0142 | [+0.0085, +0.0207] | 26 / 0 |
| val2 | observed | fill_only | order_up_to | shortage | 49 | -48.6092 | [-67.0620, -33.5078] | 47 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 49 | +31.6527 | [+17.9537, +51.1024] | 0 / 49 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1417 | [+0.1210, +0.1624] | 47 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 49 | -24.4807 | [-35.6368, -14.9666] | 40 / 0 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 49 | +15.0838 | [+8.6677, +22.9741] | 1 / 48 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0595 | [+0.0457, +0.0731] | 40 / 0 |
| val2 | observed | lead_only | periodic:1 | shortage | 49 | -24.0726 | [-35.3424, -14.6447] | 37 / 0 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +14.8479 | [+8.5315, +23.0811] | 1 / 48 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0573 | [+0.0436, +0.0711] | 37 / 0 |
| val2 | observed | lead_only | base_stock | shortage | 49 | -24.0726 | [-35.2759, -14.5061] | 37 / 0 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 49 | +14.8479 | [+8.6388, +22.8980] | 1 / 48 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0573 | [+0.0435, +0.0709] | 37 / 0 |
| val2 | observed | lead_only | order_up_to | shortage | 49 | -81.0438 | [-110.3770, -55.8363] | 48 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 49 | +24.5721 | [+14.2764, +38.8898] | 0 / 49 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.2186 | [+0.1953, +0.2411] | 48 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 49 | -14.4915 | [-23.3975, -7.0950] | 35 / 0 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +12.6695 | [+5.3850, +22.9141] | 2 / 47 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0345 | [+0.0250, +0.0445] | 35 / 0 |
| val2 | observed | mild_lead | periodic:1 | shortage | 49 | -14.1415 | [-23.4029, -6.9369] | 33 / 0 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +12.3977 | [+5.3223, +22.0490] | 2 / 47 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0325 | [+0.0235, +0.0426] | 33 / 0 |
| val2 | observed | mild_lead | base_stock | shortage | 49 | -14.1415 | [-23.9117, -6.8715] | 33 / 0 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 49 | +12.3977 | [+5.5082, +22.4853] | 2 / 47 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0325 | [+0.0229, +0.0425] | 33 / 0 |
| val2 | observed | mild_lead | order_up_to | shortage | 49 | -66.6128 | [-96.4614, -44.8373] | 47 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +23.2134 | [+11.8487, +40.9057] | 0 / 49 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1786 | [+0.1572, +0.2004] | 47 / 0 |
| val2 | observed | stable | reorder_point | shortage | 49 | -2.8087 | [-5.1245, -1.1038] | 23 / 0 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 49 | +5.3111 | [+2.1719, +9.3344] | 6 / 43 |
| val2 | observed | stable | reorder_point | service_unit_fill | 49 | +0.0093 | [+0.0050, +0.0140] | 23 / 0 |
| val2 | observed | stable | periodic:1 | shortage | 49 | -2.5637 | [-4.8832, -0.8852] | 22 / 0 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 49 | +5.0229 | [+2.0269, +8.8366] | 5 / 44 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0078 | [+0.0040, +0.0124] | 22 / 0 |
| val2 | observed | stable | base_stock | shortage | 49 | -2.5637 | [-4.8756, -0.8685] | 22 / 0 |
| val2 | observed | stable | base_stock | avg_inventory_units | 49 | +5.0229 | [+2.0589, +8.9472] | 5 / 44 |
| val2 | observed | stable | base_stock | service_unit_fill | 49 | +0.0078 | [+0.0039, +0.0123] | 22 / 0 |
| val2 | observed | stable | order_up_to | shortage | 49 | -44.9076 | [-62.0255, -31.6175] | 47 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 49 | +17.6706 | [+9.8742, +28.3965] | 0 / 49 |
| val2 | observed | stable | order_up_to | service_unit_fill | 49 | +0.1344 | [+0.1150, +0.1541] | 47 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 49 | -24.4118 | [-34.8441, -15.3893] | 41 / 0 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 49 | +26.7219 | [+16.1851, +38.9548] | 0 / 49 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0607 | [+0.0486, +0.0730] | 41 / 0 |
| val2 | observed | uncertain | periodic:1 | shortage | 49 | -24.2924 | [-35.0731, -15.0813] | 40 / 0 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +26.3279 | [+15.7805, +38.5837] | 0 / 49 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0602 | [+0.0482, +0.0721] | 40 / 0 |
| val2 | observed | uncertain | base_stock | shortage | 49 | -21.5424 | [-31.0431, -13.5266] | 40 / 0 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 49 | +25.3083 | [+15.4524, +37.5095] | 0 / 49 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0534 | [+0.0425, +0.0644] | 40 / 0 |
| val2 | observed | uncertain | order_up_to | shortage | 49 | -81.0447 | [-109.2630, -57.4298] | 48 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 49 | +34.7654 | [+21.3551, +50.6230] | 0 / 49 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.2164 | [+0.1961, +0.2374] | 48 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 725/750 complete, 0 infeasible, 0 abstained; gated: 725/750 complete, 0 infeasible, 0 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 725/750 complete, 0 infeasible, 0 abstained; reorder_point: 725/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 125
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/uncertain store TX_1 product HOUSEHOLD_1_456: ZAAD minus order_up_to = +163.614 (fill 0.503 vs 0.429, inventory 21.13 vs 15.20, retained incumbent on None reviews)
- val1/observed/uncertain store TX_3 product HOBBIES_1_029: ZAAD minus order_up_to = +124.526 (fill 0.913 vs 0.808, inventory 82.69 vs 15.50, retained incumbent on None reviews)
- final/observed/uncertain store CA_4 product HOBBIES_1_158: ZAAD minus reorder_point = +122.455 (fill 0.896 vs 0.859, inventory 19.44 vs 7.45, retained incumbent on None reviews)
- val1/observed/fill_only store TX_2 product FOODS_1_046: ZAAD minus order_up_to = +73.136 (fill 1.000 vs 0.980, inventory 193.31 vs 45.55, retained incumbent on None reviews)
- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +66.022 (fill 0.964 vs 0.946, inventory 70.12 vs 25.22, retained incumbent on None reviews)
- val1/observed/fill_only store CA_1 product HOUSEHOLD_1_324: ZAAD minus reorder_point = +51.610 (fill 0.937 vs 0.992, inventory 12.12 vs 7.39, retained incumbent on None reviews)
- val1/observed/fill_only store TX_3 product HOBBIES_1_029: ZAAD minus reorder_point = +51.373 (fill 0.913 vs 0.913, inventory 88.41 vs 38.87, retained incumbent on None reviews)
- val2/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +50.032 (fill 0.950 vs 0.950, inventory 181.31 vs 71.79, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +46.727 (fill 0.777 vs 0.723, inventory 35.21 vs 8.45, retained incumbent on None reviews)
- val2/observed/fill_only store CA_1 product HOUSEHOLD_1_324: ZAAD minus order_up_to = +38.847 (fill 1.000 vs 0.918, inventory 19.30 vs 3.33, retained incumbent on None reviews)
