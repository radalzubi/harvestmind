# Walmart M5 (Experiment A) results: stage `fifty_target_90`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `be1b45054352`, selection `8b6067be83a4`; 3750 runs, 3625 complete, 125 not complete; wall 3353 s, peak RSS 241 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 49/50 | 395.376 | 412.059 | 396.286 | 2.6838 | 35.122 | 0.927 | 14.801 | 19.903 | 1.9 | 10.8 |  | 0.44 |
| final | observed | fill_only | gated | 49/50 | 391.287 | 407.538 | 396.003 | 4.3106 | 27.488 | 0.931 | 13.671 | 27.033 | 1.6 | 8.8 | 0.53 | 5.57 |
| final | observed | fill_only | order_up_to | 49/50 | 401.208 | 413.216 | 330.587 | 1.2199 | 82.664 | 0.803 | 36.484 | 9.640 | 4.3 | 10.6 |  | 0.22 |
| final | observed | fill_only | periodic:1 | 49/50 | 396.020 | 411.085 | 378.707 | 2.1072 | 44.955 | 0.903 | 19.472 | 15.977 | 2.4 | 11.2 |  | 0.04 |
| final | observed | fill_only | reorder_point | 49/50 | 395.991 | 411.051 | 378.489 | 2.1031 | 45.113 | 0.902 | 19.533 | 15.914 | 2.4 | 10.6 |  | 0.04 |
| final | observed | lead_only | base_stock | 49/50 | 371.213 | 387.549 | 326.700 | 2.3859 | 79.127 | 0.847 | 29.439 | 17.012 | 2.9 | 10.6 |  | 0.46 |
| final | observed | lead_only | gated | 49/50 | 367.609 | 386.689 | 353.485 | 3.0879 | 63.402 | 0.878 | 25.681 | 20.871 | 2.4 | 10.5 | 0.54 | 4.03 |
| final | observed | lead_only | order_up_to | 49/50 | 386.345 | 398.102 | 262.188 | 1.2238 | 135.076 | 0.700 | 55.971 | 9.329 | 5.4 | 10.0 |  | 0.23 |
| final | observed | lead_only | periodic:1 | 49/50 | 373.611 | 388.905 | 314.190 | 2.0851 | 88.579 | 0.823 | 34.593 | 15.005 | 3.4 | 10.5 |  | 0.03 |
| final | observed | lead_only | reorder_point | 49/50 | 373.810 | 389.061 | 313.453 | 2.0813 | 89.277 | 0.819 | 35.890 | 15.058 | 3.4 | 9.7 |  | 0.03 |
| final | observed | mild_lead | base_stock | 49/50 | 369.145 | 386.641 | 337.853 | 2.3176 | 72.149 | 0.858 | 28.304 | 17.299 | 2.9 | 10.7 |  | 0.45 |
| final | observed | mild_lead | gated | 49/50 | 366.650 | 386.262 | 358.060 | 2.8428 | 60.909 | 0.873 | 21.265 | 19.446 | 2.5 | 10.3 | 0.51 | 3.94 |
| final | observed | mild_lead | order_up_to | 49/50 | 386.627 | 399.733 | 269.032 | 1.1985 | 135.729 | 0.707 | 56.303 | 9.539 | 5.2 | 10.1 |  | 0.23 |
| final | observed | mild_lead | periodic:1 | 49/50 | 372.362 | 388.923 | 324.147 | 2.0348 | 84.208 | 0.831 | 33.523 | 15.315 | 3.3 | 10.6 |  | 0.04 |
| final | observed | mild_lead | reorder_point | 49/50 | 372.703 | 389.242 | 323.204 | 2.0351 | 85.362 | 0.829 | 34.302 | 15.321 | 3.3 | 9.7 |  | 0.04 |
| final | observed | stable | base_stock | 49/50 | 358.202 | 374.709 | 358.305 | 2.6597 | 34.957 | 0.929 | 14.820 | 19.899 | 1.9 | 10.9 |  | 0.48 |
| final | observed | stable | gated | 49/50 | 358.823 | 374.382 | 350.844 | 2.3879 | 38.223 | 0.915 | 17.249 | 18.225 | 2.2 | 10.3 | 0.18 | 3.77 |
| final | observed | stable | order_up_to | 49/50 | 370.486 | 382.334 | 299.205 | 1.1951 | 82.478 | 0.803 | 36.904 | 9.555 | 4.5 | 10.5 |  | 0.22 |
| final | observed | stable | periodic:1 | 49/50 | 359.564 | 375.043 | 348.065 | 2.2761 | 41.242 | 0.911 | 18.096 | 17.218 | 2.3 | 10.8 |  | 0.04 |
| final | observed | stable | reorder_point | 49/50 | 359.635 | 375.084 | 347.688 | 2.2660 | 41.529 | 0.909 | 18.759 | 17.218 | 2.3 | 10.1 |  | 0.03 |
| final | observed | uncertain | base_stock | 49/50 | 420.014 | 436.507 | 355.912 | 2.0804 | 100.188 | 0.815 | 38.578 | 15.586 | 3.5 | 10.6 |  | 0.46 |
| final | observed | uncertain | gated | 49/50 | 416.663 | 436.417 | 398.931 | 4.1420 | 70.092 | 0.854 | 29.354 | 25.605 | 2.6 | 8.4 | 0.51 | 3.17 |
| final | observed | uncertain | order_up_to | 49/50 | 426.793 | 438.600 | 280.452 | 1.1152 | 158.091 | 0.670 | 61.663 | 8.689 | 5.7 | 10.0 |  | 0.23 |
| final | observed | uncertain | periodic:1 | 49/50 | 420.960 | 435.814 | 333.259 | 1.7166 | 115.151 | 0.783 | 44.328 | 12.977 | 4.0 | 11.0 |  | 0.04 |
| final | observed | uncertain | reorder_point | 49/50 | 421.028 | 435.896 | 333.012 | 1.7118 | 115.553 | 0.781 | 44.453 | 12.934 | 4.0 | 10.1 |  | 0.04 |
| val1 | observed | fill_only | base_stock | 43/50 | 313.839 | 328.638 | 299.669 | 3.4418 | 44.542 | 0.912 | 15.305 | 23.780 | 1.5 | 10.4 |  | 0.47 |
| val1 | observed | fill_only | gated | 43/50 | 316.338 | 332.232 | 305.912 | 4.4775 | 46.399 | 0.909 | 16.221 | 27.635 | 1.5 | 8.9 | 0.45 | 5.23 |
| val1 | observed | fill_only | order_up_to | 43/50 | 318.937 | 328.548 | 231.158 | 1.8428 | 91.196 | 0.786 | 33.631 | 11.206 | 4.3 | 10.1 |  | 0.22 |
| val1 | observed | fill_only | periodic:1 | 43/50 | 314.457 | 327.606 | 283.158 | 2.8798 | 53.000 | 0.893 | 18.303 | 19.359 | 2.0 | 10.9 |  | 0.04 |
| val1 | observed | fill_only | reorder_point | 43/50 | 314.437 | 327.600 | 282.534 | 2.8780 | 53.677 | 0.891 | 18.491 | 19.335 | 2.0 | 10.1 |  | 0.04 |
| val1 | observed | lead_only | base_stock | 43/50 | 291.147 | 306.123 | 253.132 | 2.9324 | 69.928 | 0.833 | 26.700 | 20.053 | 2.8 | 10.2 |  | 0.46 |
| val1 | observed | lead_only | gated | 43/50 | 290.087 | 308.691 | 282.031 | 3.9267 | 60.368 | 0.852 | 23.795 | 28.151 | 2.4 | 9.8 | 0.54 | 3.75 |
| val1 | observed | lead_only | order_up_to | 43/50 | 305.541 | 315.448 | 186.886 | 1.6881 | 124.062 | 0.687 | 48.180 | 10.142 | 5.5 | 9.6 |  | 0.22 |
| val1 | observed | lead_only | periodic:1 | 43/50 | 293.453 | 307.312 | 240.176 | 2.6130 | 79.245 | 0.809 | 30.327 | 17.505 | 3.1 | 10.2 |  | 0.04 |
| val1 | observed | lead_only | reorder_point | 43/50 | 293.815 | 307.655 | 239.224 | 2.6147 | 80.455 | 0.806 | 30.629 | 17.483 | 3.2 | 9.2 |  | 0.03 |
| val1 | observed | mild_lead | base_stock | 43/50 | 290.071 | 305.208 | 257.159 | 3.0966 | 65.645 | 0.857 | 23.665 | 21.050 | 2.5 | 10.4 |  | 0.47 |
| val1 | observed | mild_lead | gated | 43/50 | 290.512 | 307.235 | 267.542 | 3.5187 | 64.574 | 0.861 | 22.715 | 24.219 | 2.3 | 9.6 | 0.46 | 3.82 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 303.282 | 313.426 | 193.618 | 1.7614 | 116.240 | 0.719 | 46.213 | 10.697 | 5.1 | 9.8 |  | 0.24 |
| val1 | observed | mild_lead | periodic:1 | 43/50 | 292.139 | 306.098 | 244.346 | 2.7643 | 74.247 | 0.837 | 26.797 | 18.286 | 2.8 | 10.4 |  | 0.04 |
| val1 | observed | mild_lead | reorder_point | 43/50 | 292.380 | 306.316 | 243.593 | 2.7398 | 75.140 | 0.835 | 27.013 | 18.217 | 2.9 | 9.2 |  | 0.04 |
| val1 | observed | stable | base_stock | 43/50 | 283.794 | 298.560 | 270.151 | 3.4535 | 43.820 | 0.913 | 15.148 | 23.624 | 1.5 | 10.6 |  | 0.49 |
| val1 | observed | stable | gated | 43/50 | 285.274 | 299.479 | 263.004 | 3.1843 | 49.768 | 0.900 | 17.243 | 21.716 | 1.8 | 9.8 | 0.13 | 2.92 |
| val1 | observed | stable | order_up_to | 43/50 | 295.439 | 304.992 | 208.409 | 1.8521 | 90.142 | 0.789 | 33.338 | 11.138 | 4.3 | 10.2 |  | 0.23 |
| val1 | observed | stable | periodic:1 | 43/50 | 285.220 | 298.765 | 258.408 | 3.0493 | 50.542 | 0.899 | 17.576 | 20.445 | 1.8 | 10.5 |  | 0.03 |
| val1 | observed | stable | reorder_point | 43/50 | 285.432 | 298.947 | 257.709 | 3.0391 | 51.295 | 0.897 | 17.757 | 20.403 | 1.9 | 9.5 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 43/50 | 324.614 | 339.379 | 279.746 | 2.8625 | 75.876 | 0.832 | 28.988 | 20.024 | 3.0 | 10.4 |  | 0.45 |
| val1 | observed | uncertain | gated | 43/50 | 329.250 | 346.218 | 304.053 | 4.0148 | 68.513 | 0.852 | 27.290 | 37.031 | 2.6 | 8.3 | 0.45 | 2.99 |
| val1 | observed | uncertain | order_up_to | 43/50 | 329.280 | 338.971 | 206.158 | 1.6199 | 127.504 | 0.689 | 50.356 | 9.941 | 5.3 | 9.8 |  | 0.22 |
| val1 | observed | uncertain | periodic:1 | 43/50 | 325.157 | 338.442 | 261.050 | 2.4300 | 87.321 | 0.804 | 33.070 | 16.261 | 3.5 | 10.8 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 43/50 | 325.183 | 338.427 | 260.362 | 2.4084 | 87.829 | 0.802 | 33.246 | 16.185 | 3.6 | 9.8 |  | 0.04 |
| val2 | observed | fill_only | base_stock | 49/50 | 321.940 | 336.189 | 331.600 | 2.6510 | 23.003 | 0.915 | 16.175 | 21.610 | 1.7 | 11.2 |  | 0.49 |
| val2 | observed | fill_only | gated | 49/50 | 322.445 | 337.581 | 338.233 | 4.3009 | 20.847 | 0.916 | 13.761 | 32.500 | 1.5 | 8.8 | 0.52 | 5.24 |
| val2 | observed | fill_only | order_up_to | 49/50 | 325.738 | 335.064 | 266.700 | 1.0675 | 66.475 | 0.787 | 38.713 | 9.017 | 4.5 | 11.1 |  | 0.22 |
| val2 | observed | fill_only | periodic:1 | 49/50 | 321.818 | 334.533 | 316.507 | 2.0620 | 30.072 | 0.895 | 20.170 | 17.050 | 2.1 | 11.7 |  | 0.04 |
| val2 | observed | fill_only | reorder_point | 49/50 | 321.801 | 334.470 | 316.008 | 2.0466 | 30.302 | 0.894 | 20.653 | 16.915 | 2.1 | 10.9 |  | 0.04 |
| val2 | observed | lead_only | base_stock | 49/50 | 295.474 | 309.695 | 268.600 | 2.1361 | 60.062 | 0.834 | 33.226 | 17.279 | 3.1 | 10.9 |  | 0.46 |
| val2 | observed | lead_only | gated | 49/50 | 292.498 | 310.000 | 299.515 | 3.0965 | 44.518 | 0.862 | 27.395 | 22.000 | 2.6 | 10.6 | 0.57 | 4.10 |
| val2 | observed | lead_only | order_up_to | 49/50 | 310.951 | 320.408 | 202.595 | 0.9828 | 117.033 | 0.673 | 58.968 | 7.555 | 5.9 | 10.3 |  | 0.22 |
| val2 | observed | lead_only | periodic:1 | 49/50 | 298.091 | 311.220 | 255.343 | 1.8346 | 70.238 | 0.808 | 37.674 | 14.765 | 3.7 | 10.8 |  | 0.04 |
| val2 | observed | lead_only | reorder_point | 49/50 | 298.229 | 311.326 | 254.798 | 1.8213 | 70.756 | 0.805 | 38.183 | 14.673 | 3.7 | 9.7 |  | 0.04 |
| val2 | observed | mild_lead | base_stock | 49/50 | 292.011 | 306.166 | 276.711 | 2.3650 | 47.833 | 0.854 | 25.856 | 19.241 | 2.7 | 11.1 |  | 0.47 |
| val2 | observed | mild_lead | gated | 49/50 | 290.853 | 306.978 | 292.492 | 2.6979 | 41.750 | 0.862 | 23.879 | 21.416 | 2.3 | 10.8 | 0.54 | 4.11 |
| val2 | observed | mild_lead | order_up_to | 49/50 | 305.941 | 315.332 | 213.656 | 1.0552 | 100.304 | 0.708 | 51.097 | 8.425 | 5.2 | 10.6 |  | 0.23 |
| val2 | observed | mild_lead | periodic:1 | 49/50 | 294.150 | 307.244 | 264.596 | 2.0262 | 56.560 | 0.832 | 30.309 | 16.564 | 3.0 | 11.1 |  | 0.03 |
| val2 | observed | mild_lead | reorder_point | 49/50 | 294.222 | 307.295 | 264.253 | 2.0124 | 56.864 | 0.830 | 30.473 | 16.415 | 3.0 | 10.0 |  | 0.04 |
| val2 | observed | stable | base_stock | 49/50 | 284.683 | 298.885 | 294.645 | 2.6848 | 22.408 | 0.915 | 15.135 | 21.264 | 1.6 | 11.3 |  | 0.48 |
| val2 | observed | stable | gated | 49/50 | 285.279 | 298.712 | 287.868 | 2.3414 | 25.875 | 0.903 | 17.712 | 18.815 | 2.0 | 10.6 | 0.15 | 2.96 |
| val2 | observed | stable | order_up_to | 49/50 | 295.230 | 304.427 | 237.209 | 1.0819 | 64.751 | 0.789 | 37.199 | 8.616 | 4.5 | 11.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 49/50 | 285.490 | 298.558 | 284.979 | 2.2637 | 27.014 | 0.901 | 18.075 | 18.070 | 2.0 | 11.4 |  | 0.04 |
| val2 | observed | stable | reorder_point | 49/50 | 285.547 | 298.592 | 284.663 | 2.2510 | 27.264 | 0.900 | 18.209 | 17.931 | 2.0 | 10.3 |  | 0.04 |
| val2 | observed | uncertain | base_stock | 49/50 | 322.045 | 335.970 | 302.117 | 2.2763 | 51.376 | 0.836 | 30.418 | 17.551 | 3.1 | 10.9 |  | 0.47 |
| val2 | observed | uncertain | gated | 49/50 | 324.016 | 340.320 | 324.556 | 4.0966 | 42.896 | 0.843 | 29.762 | 29.090 | 2.7 | 8.7 | 0.50 | 3.21 |
| val2 | observed | uncertain | order_up_to | 49/50 | 331.443 | 340.849 | 228.738 | 1.0340 | 110.878 | 0.673 | 59.138 | 8.094 | 5.6 | 10.5 |  | 0.22 |
| val2 | observed | uncertain | periodic:1 | 49/50 | 323.612 | 336.157 | 284.042 | 1.8164 | 63.879 | 0.803 | 36.868 | 14.173 | 3.8 | 11.5 |  | 0.03 |
| val2 | observed | uncertain | reorder_point | 49/50 | 323.502 | 336.032 | 283.762 | 1.8102 | 63.966 | 0.802 | 36.861 | 14.106 | 3.8 | 10.5 |  | 0.03 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 49 | -4.704 | [-8.146, -1.311] | [-10.264, +0.310] | 30 / 16 / 3 | 0.054 |
| final | observed | fill_only | periodic:1 | 49 | -4.733 | [-8.213, -1.439] | [-10.352, +0.196] | 30 / 17 / 2 | 0.079 |
| final | observed | fill_only | base_stock | 49 | -4.089 | [-7.241, -0.985] | [-9.221, +0.311] | 29 / 19 / 1 | 0.193 |
| final | observed | fill_only | order_up_to | 49 | -9.921 | [-14.745, -5.431] | [-17.716, -3.540] | 34 / 13 / 2 | 0.003 |
| final | observed | lead_only | reorder_point | 49 | -6.201 | [-7.985, -4.472] | [-8.986, -3.728] | 37 / 11 / 1 | 0.0 |
| final | observed | lead_only | periodic:1 | 49 | -6.002 | [-7.781, -4.328] | [-8.692, -3.606] | 36 / 12 / 1 | 0.001 |
| final | observed | lead_only | base_stock | 49 | -3.604 | [-4.910, -2.364] | [-5.617, -1.808] | 31 / 18 / 0 | 0.085 |
| final | observed | lead_only | order_up_to | 49 | -18.735 | [-22.927, -14.883] | [-25.333, -13.273] | 45 / 3 / 1 | 0.0 |
| final | observed | mild_lead | reorder_point | 49 | -6.053 | [-8.437, -3.914] | [-9.964, -3.050] | 32 / 15 / 2 | 0.019 |
| final | observed | mild_lead | periodic:1 | 49 | -5.712 | [-7.990, -3.452] | [-9.439, -2.657] | 30 / 17 / 2 | 0.079 |
| final | observed | mild_lead | base_stock | 49 | -2.495 | [-4.667, -0.506] | [-5.875, +0.481] | 23 / 25 / 1 | 0.885 |
| final | observed | mild_lead | order_up_to | 49 | -19.977 | [-24.921, -15.375] | [-27.638, -13.160] | 46 / 1 / 2 | 0.0 |
| final | observed | stable | reorder_point | 49 | -0.812 | [-1.657, -0.095] | [-2.311, +0.115] | 19 / 14 / 16 | 0.487 |
| final | observed | stable | periodic:1 | 49 | -0.742 | [-1.573, -0.003] | [-2.112, +0.170] | 22 / 18 / 9 | 0.636 |
| final | observed | stable | base_stock | 49 | +0.620 | [+0.075, +1.152] | [-0.244, +1.397] | 19 / 29 / 1 | 0.193 |
| final | observed | stable | order_up_to | 49 | -11.664 | [-14.867, -8.771] | [-16.852, -7.567] | 44 / 3 / 2 | 0.0 |
| final | observed | uncertain | reorder_point | 49 | -4.365 | [-10.296, +1.880] | [-14.001, +5.125] | 25 / 21 / 3 | 0.659 |
| final | observed | uncertain | periodic:1 | 49 | -4.297 | [-10.239, +1.796] | [-13.743, +5.433] | 25 / 22 / 2 | 0.771 |
| final | observed | uncertain | base_stock | 49 | -3.350 | [-9.507, +3.070] | [-13.208, +6.306] | 27 / 21 / 1 | 0.471 |
| final | observed | uncertain | order_up_to | 49 | -10.130 | [-16.349, -4.213] | [-20.006, -0.916] | 34 / 13 / 2 | 0.003 |
| val1 | observed | fill_only | reorder_point | 43 | +1.901 | [+0.078, +3.730] | [-0.827, +4.725] | 18 / 23 / 2 | 0.533 |
| val1 | observed | fill_only | periodic:1 | 43 | +1.881 | [+0.055, +3.755] | [-0.812, +4.777] | 17 / 26 / 0 | 0.222 |
| val1 | observed | fill_only | base_stock | 43 | +2.498 | [+0.420, +4.703] | [-0.611, +6.039] | 18 / 25 / 0 | 0.36 |
| val1 | observed | fill_only | order_up_to | 43 | -2.599 | [-4.335, -0.975] | [-5.195, -0.116] | 31 / 12 / 0 | 0.005 |
| val1 | observed | lead_only | reorder_point | 43 | -3.729 | [-5.547, -1.889] | [-6.594, -1.018] | 27 / 16 / 0 | 0.126 |
| val1 | observed | lead_only | periodic:1 | 43 | -3.366 | [-5.243, -1.573] | [-6.268, -0.728] | 26 / 17 / 0 | 0.222 |
| val1 | observed | lead_only | base_stock | 43 | -1.060 | [-2.596, +0.491] | [-3.459, +1.276] | 21 / 22 / 0 | 1.0 |
| val1 | observed | lead_only | order_up_to | 43 | -15.455 | [-19.038, -11.847] | [-21.313, -10.314] | 41 / 2 / 0 | 0.0 |
| val1 | observed | mild_lead | reorder_point | 43 | -1.868 | [-2.983, -0.807] | [-3.583, -0.347] | 20 / 23 / 0 | 0.761 |
| val1 | observed | mild_lead | periodic:1 | 43 | -1.627 | [-2.784, -0.564] | [-3.460, -0.063] | 19 / 24 / 0 | 0.542 |
| val1 | observed | mild_lead | base_stock | 43 | +0.440 | [-0.538, +1.443] | [-0.993, +2.065] | 20 / 23 / 0 | 0.761 |
| val1 | observed | mild_lead | order_up_to | 43 | -12.770 | [-15.877, -9.813] | [-17.926, -8.716] | 41 / 2 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 43 | -0.157 | [-0.528, +0.175] | [-0.729, +0.332] | 7 / 23 / 13 | 0.005 |
| val1 | observed | stable | periodic:1 | 43 | +0.055 | [-0.185, +0.290] | [-0.311, +0.411] | 15 / 23 / 5 | 0.256 |
| val1 | observed | stable | base_stock | 43 | +1.480 | [+0.876, +2.081] | [+0.630, +2.462] | 16 / 27 / 0 | 0.126 |
| val1 | observed | stable | order_up_to | 43 | -10.165 | [-12.669, -7.817] | [-14.219, -6.844] | 40 / 3 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 43 | +4.067 | [+1.183, +6.916] | [-0.097, +8.551] | 17 / 26 / 0 | 0.222 |
| val1 | observed | uncertain | periodic:1 | 43 | +4.093 | [+1.485, +6.888] | [+0.099, +8.549] | 17 / 26 / 0 | 0.222 |
| val1 | observed | uncertain | base_stock | 43 | +4.635 | [+2.017, +7.289] | [+0.751, +8.713] | 15 / 28 / 0 | 0.066 |
| val1 | observed | uncertain | order_up_to | 43 | -0.031 | [-3.606, +3.686] | [-5.441, +5.659] | 26 / 17 / 0 | 0.222 |
| val2 | observed | fill_only | reorder_point | 49 | +0.644 | [-2.275, +3.331] | [-3.864, +4.799] | 22 / 27 / 0 | 0.568 |
| val2 | observed | fill_only | periodic:1 | 49 | +0.627 | [-2.273, +3.306] | [-3.975, +4.783] | 22 / 27 / 0 | 0.568 |
| val2 | observed | fill_only | base_stock | 49 | +0.505 | [-2.181, +3.088] | [-3.871, +4.496] | 21 / 28 / 0 | 0.392 |
| val2 | observed | fill_only | order_up_to | 49 | -3.293 | [-6.834, +0.050] | [-9.046, +1.738] | 27 / 22 / 0 | 0.568 |
| val2 | observed | lead_only | reorder_point | 49 | -5.731 | [-8.122, -3.411] | [-9.666, -2.412] | 36 / 13 / 0 | 0.001 |
| val2 | observed | lead_only | periodic:1 | 49 | -5.593 | [-8.011, -3.230] | [-9.581, -2.282] | 36 / 13 / 0 | 0.001 |
| val2 | observed | lead_only | base_stock | 49 | -2.977 | [-4.777, -1.248] | [-5.778, -0.425] | 24 / 25 / 0 | 1.0 |
| val2 | observed | lead_only | order_up_to | 49 | -18.453 | [-23.575, -13.696] | [-26.841, -11.580] | 48 / 1 / 0 | 0.0 |
| val2 | observed | mild_lead | reorder_point | 49 | -3.369 | [-5.395, -1.531] | [-6.640, -0.874] | 29 / 20 / 0 | 0.253 |
| val2 | observed | mild_lead | periodic:1 | 49 | -3.297 | [-5.367, -1.418] | [-6.665, -0.812] | 28 / 21 / 0 | 0.392 |
| val2 | observed | mild_lead | base_stock | 49 | -1.158 | [-2.640, +0.172] | [-3.610, +0.596] | 20 / 29 / 0 | 0.253 |
| val2 | observed | mild_lead | order_up_to | 49 | -15.088 | [-19.923, -10.685] | [-22.869, -9.036] | 46 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 49 | -0.267 | [-0.570, +0.003] | [-0.784, +0.066] | 11 / 28 / 10 | 0.009 |
| val2 | observed | stable | periodic:1 | 49 | -0.210 | [-0.524, +0.062] | [-0.748, +0.126] | 17 / 27 / 5 | 0.174 |
| val2 | observed | stable | base_stock | 49 | +0.597 | [+0.274, +0.905] | [+0.127, +1.095] | 24 / 25 / 0 | 1.0 |
| val2 | observed | stable | order_up_to | 49 | -9.951 | [-12.535, -7.420] | [-14.202, -6.458] | 46 / 3 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 49 | +0.513 | [-2.433, +3.348] | [-4.032, +4.633] | 21 / 28 / 0 | 0.392 |
| val2 | observed | uncertain | periodic:1 | 49 | +0.404 | [-2.491, +3.139] | [-4.147, +4.610] | 23 / 26 / 0 | 0.775 |
| val2 | observed | uncertain | base_stock | 49 | +1.970 | [-0.821, +4.612] | [-2.473, +6.052] | 19 / 30 / 0 | 0.152 |
| val2 | observed | uncertain | order_up_to | 49 | -7.427 | [-11.616, -3.386] | [-14.319, -1.579] | 32 / 17 / 0 | 0.044 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 49 | -17.6247 | [-34.0149, -6.5867] | 26 / 8 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 49 | +11.1191 | [+7.0514, +15.9975] | 3 / 43 |
| final | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0293 | [+0.0180, +0.0416] | 26 / 8 |
| final | observed | fill_only | periodic:1 | shortage | 49 | -17.4662 | [-34.3603, -6.4856] | 26 / 8 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +11.0565 | [+7.0210, +15.6121] | 4 / 43 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0284 | [+0.0166, +0.0409] | 26 / 8 |
| final | observed | fill_only | base_stock | shortage | 49 | -7.6333 | [-20.6586, +1.0998] | 18 / 17 |
| final | observed | fill_only | base_stock | avg_inventory_units | 49 | +7.1305 | [+2.7076, +11.5625] | 13 / 34 |
| final | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0040 | [-0.0074, +0.0161] | 18 / 17 |
| final | observed | fill_only | order_up_to | shortage | 49 | -55.1759 | [-81.0355, -34.9432] | 46 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 49 | +17.3934 | [+11.8419, +24.2000] | 0 / 47 |
| final | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1282 | [+0.1079, +0.1493] | 46 / 0 |
| final | observed | lead_only | reorder_point | shortage | 49 | -25.8754 | [-36.6485, -17.3637] | 40 / 0 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 49 | +5.8131 | [+3.4531, +8.6761] | 2 / 46 |
| final | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0581 | [+0.0452, +0.0712] | 40 / 0 |
| final | observed | lead_only | periodic:1 | shortage | 49 | -25.1775 | [-35.9099, -16.4579] | 39 / 1 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +5.8661 | [+3.6212, +8.5679] | 1 / 47 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0546 | [+0.0420, +0.0680] | 39 / 1 |
| final | observed | lead_only | base_stock | shortage | 49 | -15.7251 | [-23.1259, -9.2253] | 32 / 10 |
| final | observed | lead_only | base_stock | avg_inventory_units | 49 | +3.8598 | [+1.3618, +6.5156] | 10 / 38 |
| final | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0302 | [+0.0178, +0.0422] | 32 / 10 |
| final | observed | lead_only | order_up_to | shortage | 49 | -71.6742 | [-95.2471, -51.7592] | 46 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 49 | +11.5419 | [+7.2734, +16.7649] | 0 / 48 |
| final | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1776 | [+0.1530, +0.2022] | 46 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 49 | -24.4534 | [-37.2623, -13.6728] | 32 / 1 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +4.1253 | [+1.9693, +6.6055] | 4 / 42 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0442 | [+0.0314, +0.0575] | 32 / 1 |
| final | observed | mild_lead | periodic:1 | shortage | 49 | -23.2992 | [-35.6745, -12.8090] | 32 / 1 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +4.1311 | [+2.1223, +6.5414] | 4 / 42 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0413 | [+0.0290, +0.0546] | 32 / 1 |
| final | observed | mild_lead | base_stock | shortage | 49 | -11.2408 | [-22.6080, -1.9747] | 22 / 19 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 49 | +2.1475 | [-0.8369, +4.6464] | 13 / 34 |
| final | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0145 | [+0.0019, +0.0281] | 22 / 19 |
| final | observed | mild_lead | order_up_to | shortage | 49 | -74.8206 | [-101.8126, -51.4857] | 46 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +9.9067 | [+6.3568, +14.3709] | 0 / 47 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1655 | [+0.1430, +0.1893] | 46 / 0 |
| final | observed | stable | reorder_point | shortage | 49 | -3.3058 | [-8.0886, -0.6407] | 11 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 49 | +1.0066 | [+0.1099, +2.4425] | 11 / 20 |
| final | observed | stable | reorder_point | service_unit_fill | 49 | +0.0060 | [+0.0025, +0.0101] | 11 / 1 |
| final | observed | stable | periodic:1 | shortage | 49 | -3.0185 | [-7.6921, -0.3641] | 10 / 5 |
| final | observed | stable | periodic:1 | avg_inventory_units | 49 | +1.0068 | [+0.1267, +2.3725] | 18 / 20 |
| final | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0046 | [+0.0009, +0.0090] | 10 / 5 |
| final | observed | stable | base_stock | shortage | 49 | +3.2665 | [+0.5025, +5.7234] | 5 / 30 |
| final | observed | stable | base_stock | avg_inventory_units | 49 | -1.6736 | [-3.6131, -0.0365] | 41 / 6 |
| final | observed | stable | base_stock | service_unit_fill | 49 | -0.0135 | [-0.0199, -0.0074] | 5 / 30 |
| final | observed | stable | order_up_to | shortage | 49 | -44.2547 | [-61.1495, -30.2389] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 49 | +8.6696 | [+4.7538, +14.0026] | 0 / 47 |
| final | observed | stable | order_up_to | service_unit_fill | 49 | +0.1128 | [+0.0952, +0.1303] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 49 | -45.4614 | [-69.5353, -25.4822] | 39 / 1 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 49 | +12.6711 | [+8.1541, +17.8535] | 0 / 45 |
| final | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0730 | [+0.0563, +0.0898] | 39 / 1 |
| final | observed | uncertain | periodic:1 | shortage | 49 | -45.0598 | [-69.8488, -25.0151] | 39 / 2 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +12.6279 | [+8.1084, +17.8665] | 2 / 45 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0707 | [+0.0544, +0.0877] | 39 / 2 |
| final | observed | uncertain | base_stock | shortage | 49 | -30.0969 | [-50.5778, -13.9739] | 31 / 9 |
| final | observed | uncertain | base_stock | avg_inventory_units | 49 | +10.0195 | [+5.7109, +15.1392] | 5 / 42 |
| final | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0389 | [+0.0230, +0.0557] | 31 / 9 |
| final | observed | uncertain | order_up_to | shortage | 49 | -87.9990 | [-124.2628, -57.5632] | 46 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 49 | +16.9165 | [+11.4859, +23.2289] | 0 / 47 |
| final | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1843 | [+0.1597, +0.2071] | 46 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 43 | -7.2787 | [-15.4052, -0.1730] | 16 / 4 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 43 | +8.2994 | [+5.0690, +12.0254] | 3 / 37 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 43 | +0.0176 | [+0.0064, +0.0307] | 16 / 4 |
| val1 | observed | fill_only | periodic:1 | shortage | 43 | -6.6016 | [-15.0529, +0.3779] | 15 / 8 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 43 | +8.2757 | [+5.1960, +12.0914] | 4 / 38 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 43 | +0.0157 | [+0.0043, +0.0290] | 15 / 8 |
| val1 | observed | fill_only | base_stock | shortage | 43 | +1.8569 | [-7.3548, +10.6615] | 8 / 18 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 43 | +3.8541 | [+1.4176, +6.5900] | 14 / 29 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 43 | -0.0028 | [-0.0144, +0.0103] | 8 / 18 |
| val1 | observed | fill_only | order_up_to | shortage | 43 | -44.7971 | [-60.3791, -31.3408] | 41 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 43 | +16.4286 | [+10.0993, +25.9213] | 0 / 43 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 43 | +0.1226 | [+0.1018, +0.1447] | 41 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 43 | -20.0867 | [-30.0419, -11.5690] | 31 / 2 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 43 | +10.6681 | [+4.5201, +19.0074] | 1 / 42 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 43 | +0.0464 | [+0.0334, +0.0598] | 31 / 2 |
| val1 | observed | lead_only | periodic:1 | shortage | 43 | -18.8772 | [-29.0605, -10.8570] | 30 / 3 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 43 | +10.6459 | [+4.4880, +19.1361] | 1 / 42 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 43 | +0.0429 | [+0.0299, +0.0565] | 30 / 3 |
| val1 | observed | lead_only | base_stock | shortage | 43 | -9.5598 | [-17.7535, -2.7418] | 24 / 9 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 43 | +8.0975 | [+3.0304, +15.1197] | 5 / 38 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 43 | +0.0191 | [+0.0064, +0.0315] | 24 / 9 |
| val1 | observed | lead_only | order_up_to | shortage | 43 | -63.6936 | [-85.3229, -45.4307] | 42 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 43 | +18.0083 | [+8.3499, +32.0604] | 0 / 43 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 43 | +0.1653 | [+0.1429, +0.1861] | 42 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 43 | -10.5667 | [-16.5231, -5.7093] | 24 / 5 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 43 | +6.0023 | [+2.7106, +10.4629] | 3 / 39 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 43 | +0.0266 | [+0.0165, +0.0373] | 24 / 5 |
| val1 | observed | mild_lead | periodic:1 | shortage | 43 | -9.6734 | [-15.6895, -4.4921] | 23 / 9 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 43 | +5.9336 | [+2.6765, +10.4460] | 4 / 39 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 43 | +0.0244 | [+0.0142, +0.0356] | 23 / 9 |
| val1 | observed | mild_lead | base_stock | shortage | 43 | -1.0709 | [-5.8449, +3.9759] | 17 / 15 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 43 | +3.1697 | [+1.0264, +6.1344] | 15 / 28 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 43 | +0.0041 | [-0.0050, +0.0139] | 17 / 15 |
| val1 | observed | mild_lead | order_up_to | shortage | 43 | -51.6658 | [-69.0115, -36.5408] | 42 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 43 | +13.5226 | [+7.2015, +23.3562] | 0 / 43 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 43 | +0.1419 | [+0.1232, +0.1612] | 42 / 0 |
| val1 | observed | stable | reorder_point | shortage | 43 | -1.5267 | [-3.2164, -0.2610] | 6 / 1 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 43 | +1.3127 | [+0.2549, +2.8592] | 5 / 22 |
| val1 | observed | stable | reorder_point | service_unit_fill | 43 | +0.0026 | [-0.0005, +0.0064] | 6 / 1 |
| val1 | observed | stable | periodic:1 | shortage | 43 | -0.7732 | [-1.8638, +0.1017] | 6 / 5 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 43 | +1.2707 | [+0.2212, +2.7243] | 15 / 21 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 43 | +0.0010 | [-0.0019, +0.0043] | 6 / 5 |
| val1 | observed | stable | base_stock | shortage | 43 | +5.9483 | [+3.0524, +9.5090] | 0 / 26 |
| val1 | observed | stable | base_stock | avg_inventory_units | 43 | -1.9085 | [-3.1164, -0.8500] | 39 / 4 |
| val1 | observed | stable | base_stock | service_unit_fill | 43 | -0.0133 | [-0.0179, -0.0089] | 0 / 26 |
| val1 | observed | stable | order_up_to | shortage | 43 | -40.3735 | [-54.7466, -27.8369] | 41 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 43 | +10.5781 | [+5.5492, +19.0183] | 0 / 43 |
| val1 | observed | stable | order_up_to | service_unit_fill | 43 | +0.1112 | [+0.0929, +0.1308] | 41 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 43 | -19.3153 | [-31.2978, -9.4656] | 25 / 7 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 43 | +20.8457 | [+6.2926, +45.5271] | 4 / 39 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 43 | +0.0507 | [+0.0311, +0.0716] | 25 / 7 |
| val1 | observed | uncertain | periodic:1 | shortage | 43 | -18.8075 | [-29.8455, -9.0585] | 24 / 9 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 43 | +20.7702 | [+6.3764, +45.3187] | 4 / 39 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 43 | +0.0488 | [+0.0296, +0.0687] | 24 / 9 |
| val1 | observed | uncertain | base_stock | shortage | 43 | -7.3623 | [-17.8549, +2.4697] | 19 / 16 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 43 | +17.0070 | [+4.0090, +39.7460] | 8 / 35 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 43 | +0.0203 | [+0.0012, +0.0395] | 19 / 16 |
| val1 | observed | uncertain | order_up_to | shortage | 43 | -58.9909 | [-77.2697, -42.2952] | 42 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 43 | +27.0897 | [+9.8486, +57.6295] | 1 / 42 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 43 | +0.1638 | [+0.1393, +0.1892] | 42 / 0 |
| val2 | observed | fill_only | reorder_point | shortage | 49 | -9.4555 | [-15.2209, -4.6424] | 28 / 3 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 49 | +15.5850 | [+8.9330, +23.4668] | 1 / 48 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0221 | [+0.0133, +0.0311] | 28 / 3 |
| val2 | observed | fill_only | periodic:1 | shortage | 49 | -9.2259 | [-14.9718, -4.4473] | 28 / 5 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +15.4505 | [+8.8321, +23.3195] | 3 / 46 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0207 | [+0.0126, +0.0298] | 28 / 5 |
| val2 | observed | fill_only | base_stock | shortage | 49 | -2.1566 | [-5.7076, +1.0229] | 16 / 13 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 49 | +10.8901 | [+5.6708, +17.2300] | 12 / 37 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0013 | [-0.0067, +0.0095] | 16 / 13 |
| val2 | observed | fill_only | order_up_to | shortage | 49 | -45.6288 | [-63.8714, -30.8183] | 47 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 49 | +23.4828 | [+13.8158, +35.7831] | 0 / 49 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1289 | [+0.1109, +0.1468] | 47 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 49 | -26.2380 | [-40.7759, -14.5290] | 39 / 0 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 49 | +7.3269 | [+4.2997, +11.5298] | 2 / 46 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0566 | [+0.0424, +0.0709] | 39 / 0 |
| val2 | observed | lead_only | periodic:1 | shortage | 49 | -25.7194 | [-40.8546, -14.0040] | 39 / 2 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +7.2347 | [+4.2236, +11.1057] | 3 / 46 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0538 | [+0.0402, +0.0683] | 39 / 2 |
| val2 | observed | lead_only | base_stock | shortage | 49 | -15.5432 | [-26.4595, -6.6310] | 31 / 9 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 49 | +4.7206 | [+1.9179, +8.2237] | 13 / 36 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0271 | [+0.0144, +0.0401] | 31 / 9 |
| val2 | observed | lead_only | order_up_to | shortage | 49 | -72.5144 | [-102.1013, -47.9088] | 48 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 49 | +14.4448 | [+8.7321, +21.7516] | 0 / 49 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1884 | [+0.1689, +0.2083] | 48 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 49 | -15.1142 | [-27.0317, -6.6488] | 30 / 2 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +5.0016 | [+2.7479, +7.8342] | 3 / 46 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0321 | [+0.0216, +0.0427] | 30 / 2 |
| val2 | observed | mild_lead | periodic:1 | shortage | 49 | -14.8108 | [-27.0031, -6.3782] | 29 / 3 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +4.8525 | [+2.7077, +7.4805] | 5 / 44 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0303 | [+0.0199, +0.0413] | 29 / 3 |
| val2 | observed | mild_lead | base_stock | shortage | 49 | -6.0831 | [-15.0276, +0.0445] | 19 / 17 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 49 | +2.1754 | [+0.8962, +3.6558] | 20 / 29 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0078 | [-0.0018, +0.0176] | 19 / 17 |
| val2 | observed | mild_lead | order_up_to | shortage | 49 | -58.5544 | [-86.5555, -38.5094] | 47 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +12.9911 | [+7.5023, +21.4796] | 0 / 49 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1539 | [+0.1351, +0.1722] | 47 / 0 |
| val2 | observed | stable | reorder_point | shortage | 49 | -1.3892 | [-3.2441, -0.2296] | 7 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 49 | +0.8842 | [+0.3129, +1.6090] | 5 / 27 |
| val2 | observed | stable | reorder_point | service_unit_fill | 49 | +0.0035 | [+0.0006, +0.0072] | 7 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 49 | -1.1392 | [-3.0009, +0.0693] | 7 / 8 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 49 | +0.7448 | [+0.2155, +1.4184] | 15 / 27 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0019 | [-0.0011, +0.0055] | 7 / 8 |
| val2 | observed | stable | base_stock | shortage | 49 | +3.4672 | [+1.9927, +5.0834] | 3 / 30 |
| val2 | observed | stable | base_stock | avg_inventory_units | 49 | -2.4488 | [-3.7773, -1.4504] | 46 / 3 |
| val2 | observed | stable | base_stock | service_unit_fill | 49 | -0.0120 | [-0.0172, -0.0070] | 3 / 30 |
| val2 | observed | stable | order_up_to | shortage | 49 | -38.8767 | [-54.2423, -26.8315] | 47 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 49 | +10.1989 | [+5.9222, +16.4738] | 0 / 49 |
| val2 | observed | stable | order_up_to | service_unit_fill | 49 | +0.1146 | [+0.0983, +0.1315] | 47 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 49 | -21.0702 | [-32.0897, -11.7292] | 31 / 7 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 49 | +14.9836 | [+8.7679, +22.3472] | 3 / 45 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0403 | [+0.0264, +0.0544] | 31 / 7 |
| val2 | observed | uncertain | periodic:1 | shortage | 49 | -20.9823 | [-32.4218, -11.4958] | 33 / 7 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +14.9174 | [+8.4423, +22.3667] | 4 / 45 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0399 | [+0.0265, +0.0546] | 33 / 7 |
| val2 | observed | uncertain | base_stock | shortage | 49 | -8.4794 | [-16.6064, -1.7816] | 22 / 20 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 49 | +11.5386 | [+6.1968, +18.0137] | 10 / 39 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0064 | [-0.0079, +0.0210] | 22 / 20 |
| val2 | observed | uncertain | order_up_to | shortage | 49 | -67.9817 | [-93.8219, -45.8732] | 48 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 49 | +20.9957 | [+12.6114, +31.0276] | 0 / 49 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1694 | [+0.1520, +0.1875] | 48 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 725/750 complete, 0 infeasible, 0 abstained; gated: 725/750 complete, 0 infeasible, 0 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 725/750 complete, 0 infeasible, 0 abstained; reorder_point: 725/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 125
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- final/observed/uncertain store TX_1 product HOUSEHOLD_1_456: ZAAD minus base_stock = +150.657 (fill 0.795 vs 0.745, inventory 23.74 vs 4.19, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product HOUSEHOLD_1_456: ZAAD minus order_up_to = +54.268 (fill 0.493 vs 0.429, inventory 21.75 vs 15.20, retained incumbent on None reviews)
- val2/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +52.749 (fill 0.950 vs 0.950, inventory 162.29 vs 71.79, retained incumbent on None reviews)
- final/observed/uncertain store CA_4 product HOBBIES_1_158: ZAAD minus reorder_point = +50.832 (fill 0.896 vs 0.837, inventory 18.85 vs 6.52, retained incumbent on None reviews)
- val1/observed/fill_only store WI_1 product FOODS_3_288: ZAAD minus base_stock = +48.132 (fill 0.854 vs 0.911, inventory 50.81 vs 64.54, retained incumbent on None reviews)
- val1/observed/uncertain store CA_4 product HOBBIES_1_423: ZAAD minus reorder_point = +46.982 (fill 0.841 vs 0.731, inventory 9.34 vs 5.39, retained incumbent on None reviews)
- val2/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +45.964 (fill 0.950 vs 0.950, inventory 148.21 vs 73.67, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +40.982 (fill 0.725 vs 0.723, inventory 43.79 vs 8.45, retained incumbent on None reviews)
- val2/observed/uncertain store TX_2 product FOODS_1_046: ZAAD minus base_stock = +40.471 (fill 0.908 vs 0.888, inventory 115.84 vs 56.80, retained incumbent on None reviews)
- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +39.925 (fill 0.964 vs 0.946, inventory 62.98 vs 25.22, retained incumbent on None reviews)
