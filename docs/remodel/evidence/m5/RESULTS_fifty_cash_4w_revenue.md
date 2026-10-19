# Walmart M5 (Experiment A) results: stage `fifty_cash_4w_revenue`

Commit `a391e99a6e905a52233630e52f5182fcb72c1c71`, declaration `f69edda8e106`, selection `8b6067be83a4`; 3750 runs, 3335 complete, 415 not complete; wall 2768 s, peak RSS 255 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 49/50 | 395.201 | 410.243 | 383.556 | 2.5684 | 40.182 | 0.920 | 17.317 | 18.992 | 2.1 | 10.8 |  | 0.37 |
| final | observed | fill_only | gated | 47/50 | 401.682 | 417.888 | 401.953 | 3.9613 | 31.683 | 0.939 | 11.654 | 26.449 | 1.4 | 8.9 | 0.39 | 5.12 |
| final | observed | fill_only | order_up_to | 49/50 | 401.044 | 412.240 | 325.713 | 1.1970 | 83.738 | 0.800 | 37.625 | 9.330 | 4.4 | 10.6 |  | 0.19 |
| final | observed | fill_only | periodic:1 | 47/50 | 405.983 | 421.307 | 392.918 | 2.4983 | 41.397 | 0.918 | 18.139 | 18.470 | 2.1 | 11.3 |  | 0.03 |
| final | observed | fill_only | reorder_point | 47/50 | 405.923 | 421.231 | 392.613 | 2.4891 | 41.547 | 0.918 | 18.186 | 18.352 | 2.1 | 10.5 |  | 0.03 |
| final | observed | lead_only | base_stock | 49/50 | 372.008 | 387.872 | 324.950 | 2.3595 | 80.365 | 0.844 | 30.987 | 16.557 | 3.0 | 10.6 |  | 0.39 |
| final | observed | lead_only | gated | 48/50 | 370.280 | 389.356 | 357.653 | 3.3043 | 62.618 | 0.883 | 22.448 | 20.991 | 2.4 | 9.9 | 0.43 | 3.38 |
| final | observed | lead_only | order_up_to | 49/50 | 386.739 | 398.292 | 261.662 | 1.2179 | 135.559 | 0.699 | 56.575 | 9.209 | 5.4 | 10.0 |  | 0.19 |
| final | observed | lead_only | periodic:1 | 48/50 | 373.740 | 389.850 | 328.481 | 2.4059 | 79.158 | 0.849 | 28.031 | 16.795 | 2.9 | 10.5 |  | 0.03 |
| final | observed | lead_only | reorder_point | 48/50 | 373.929 | 389.984 | 327.667 | 2.3998 | 79.844 | 0.846 | 28.542 | 16.722 | 2.9 | 9.5 |  | 0.03 |
| final | observed | mild_lead | base_stock | 49/50 | 369.787 | 386.607 | 335.468 | 2.2940 | 72.874 | 0.856 | 29.210 | 16.988 | 3.0 | 10.7 |  | 0.38 |
| final | observed | mild_lead | gated | 46/50 | 379.282 | 398.987 | 369.862 | 3.0864 | 61.655 | 0.883 | 22.051 | 21.291 | 2.3 | 9.8 | 0.42 | 3.34 |
| final | observed | mild_lead | order_up_to | 49/50 | 387.016 | 399.843 | 268.351 | 1.1918 | 136.121 | 0.706 | 56.793 | 9.404 | 5.3 | 10.0 |  | 0.19 |
| final | observed | mild_lead | periodic:1 | 48/50 | 371.591 | 388.830 | 339.846 | 2.3448 | 71.827 | 0.860 | 26.612 | 17.267 | 2.9 | 10.6 |  | 0.03 |
| final | observed | mild_lead | reorder_point | 48/50 | 371.937 | 389.153 | 338.867 | 2.3417 | 73.013 | 0.857 | 27.174 | 17.245 | 2.9 | 9.6 |  | 0.03 |
| final | observed | stable | base_stock | 49/50 | 358.883 | 374.275 | 352.838 | 2.6020 | 36.348 | 0.925 | 16.558 | 19.351 | 2.0 | 10.9 |  | 0.38 |
| final | observed | stable | gated | 47/50 | 367.991 | 384.121 | 365.011 | 2.6879 | 35.719 | 0.928 | 15.494 | 20.079 | 1.9 | 10.3 | 0.22 | 3.51 |
| final | observed | stable | order_up_to | 49/50 | 370.907 | 382.507 | 298.163 | 1.1856 | 83.257 | 0.800 | 37.805 | 9.375 | 4.6 | 10.4 |  | 0.20 |
| final | observed | stable | periodic:1 | 48/50 | 362.145 | 378.265 | 359.150 | 2.6444 | 36.519 | 0.925 | 16.370 | 19.709 | 2.0 | 10.9 |  | 0.03 |
| final | observed | stable | reorder_point | 48/50 | 362.179 | 378.256 | 358.750 | 2.6314 | 36.708 | 0.924 | 16.742 | 19.673 | 2.0 | 10.0 |  | 0.03 |
| final | observed | uncertain | base_stock | 49/50 | 420.101 | 435.808 | 351.455 | 2.0500 | 101.719 | 0.810 | 40.557 | 15.265 | 3.6 | 10.7 |  | 0.38 |
| final | observed | uncertain | gated | 46/50 | 431.975 | 452.245 | 406.088 | 3.7985 | 81.372 | 0.849 | 30.640 | 24.162 | 2.7 | 8.6 | 0.38 | 2.65 |
| final | observed | uncertain | order_up_to | 49/50 | 427.209 | 438.771 | 279.416 | 1.1103 | 159.008 | 0.667 | 62.811 | 8.590 | 5.8 | 10.0 |  | 0.19 |
| final | observed | uncertain | periodic:1 | 47/50 | 429.850 | 445.739 | 355.823 | 2.0215 | 106.370 | 0.810 | 38.633 | 14.987 | 3.4 | 11.1 |  | 0.03 |
| final | observed | uncertain | reorder_point | 47/50 | 429.844 | 445.728 | 355.478 | 2.0086 | 106.697 | 0.808 | 38.724 | 14.906 | 3.4 | 10.1 |  | 0.03 |
| val1 | observed | fill_only | base_stock | 43/50 | 317.861 | 329.056 | 250.065 | 2.6718 | 80.452 | 0.814 | 23.681 | 20.875 | 3.1 | 9.9 |  | 0.37 |
| val1 | observed | fill_only | gated | 31/50 | 318.983 | 334.887 | 322.291 | 4.9246 | 20.312 | 0.961 | 11.768 | 35.629 | 0.8 | 8.6 | 0.38 | 5.14 |
| val1 | observed | fill_only | order_up_to | 43/50 | 323.137 | 330.865 | 200.843 | 1.4415 | 116.673 | 0.710 | 39.771 | 9.826 | 5.5 | 9.8 |  | 0.19 |
| val1 | observed | fill_only | periodic:1 | 36/50 | 299.844 | 312.652 | 281.357 | 2.9755 | 32.667 | 0.920 | 15.433 | 23.379 | 1.7 | 11.3 |  | 0.04 |
| val1 | observed | fill_only | reorder_point | 36/50 | 300.005 | 312.796 | 281.117 | 2.9259 | 33.004 | 0.919 | 15.551 | 23.228 | 1.8 | 10.5 |  | 0.04 |
| val1 | observed | lead_only | base_stock | 43/50 | 298.512 | 310.453 | 219.453 | 2.3513 | 96.160 | 0.765 | 32.733 | 17.949 | 3.8 | 9.6 |  | 0.40 |
| val1 | observed | lead_only | gated | 33/50 | 279.024 | 296.134 | 277.658 | 4.1003 | 36.336 | 0.908 | 22.224 | 34.597 | 1.7 | 9.7 | 0.45 | 3.67 |
| val1 | observed | lead_only | order_up_to | 43/50 | 310.141 | 318.651 | 168.988 | 1.3672 | 140.066 | 0.642 | 51.894 | 9.075 | 6.3 | 9.3 |  | 0.20 |
| val1 | observed | lead_only | periodic:1 | 33/50 | 280.352 | 294.565 | 251.912 | 2.9037 | 47.269 | 0.882 | 25.356 | 22.693 | 2.2 | 10.6 |  | 0.03 |
| val1 | observed | lead_only | reorder_point | 33/50 | 280.629 | 294.818 | 250.995 | 2.8499 | 48.381 | 0.880 | 25.947 | 22.560 | 2.2 | 9.5 |  | 0.03 |
| val1 | observed | mild_lead | base_stock | 43/50 | 297.039 | 308.678 | 221.474 | 2.4349 | 91.000 | 0.780 | 29.916 | 18.684 | 3.6 | 9.8 |  | 0.39 |
| val1 | observed | mild_lead | gated | 33/50 | 278.162 | 294.389 | 272.497 | 3.7688 | 35.522 | 0.911 | 20.134 | 29.236 | 1.6 | 9.5 | 0.41 | 3.68 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 308.328 | 316.687 | 172.425 | 1.3967 | 133.976 | 0.664 | 50.485 | 9.545 | 6.0 | 9.5 |  | 0.19 |
| val1 | observed | mild_lead | periodic:1 | 34/50 | 274.339 | 288.219 | 250.670 | 2.9419 | 41.982 | 0.895 | 21.664 | 23.095 | 2.1 | 10.7 |  | 0.03 |
| val1 | observed | mild_lead | reorder_point | 34/50 | 274.730 | 288.588 | 249.519 | 2.9124 | 43.408 | 0.893 | 22.266 | 22.985 | 2.1 | 9.5 |  | 0.03 |
| val1 | observed | stable | base_stock | 43/50 | 292.740 | 304.167 | 230.587 | 2.7141 | 76.027 | 0.826 | 22.525 | 20.965 | 2.8 | 9.9 |  | 0.39 |
| val1 | observed | stable | gated | 35/50 | 263.825 | 277.195 | 255.185 | 3.2403 | 25.261 | 0.935 | 14.249 | 26.351 | 1.4 | 10.1 | 0.16 | 3.07 |
| val1 | observed | stable | order_up_to | 43/50 | 302.021 | 310.051 | 184.858 | 1.4677 | 113.114 | 0.723 | 38.573 | 9.871 | 5.4 | 9.7 |  | 0.20 |
| val1 | observed | stable | periodic:1 | 35/50 | 263.274 | 276.604 | 256.009 | 3.1808 | 23.679 | 0.937 | 13.583 | 25.168 | 1.5 | 10.9 |  | 0.04 |
| val1 | observed | stable | reorder_point | 35/50 | 263.599 | 276.907 | 254.960 | 3.1297 | 24.957 | 0.935 | 14.170 | 25.015 | 1.5 | 9.9 |  | 0.03 |
| val1 | observed | uncertain | base_stock | 43/50 | 329.820 | 341.256 | 235.149 | 2.2392 | 109.304 | 0.739 | 37.107 | 17.658 | 4.2 | 10.0 |  | 0.39 |
| val1 | observed | uncertain | gated | 33/50 | 321.553 | 338.138 | 305.917 | 3.9917 | 48.386 | 0.884 | 27.312 | 33.356 | 2.2 | 8.3 | 0.33 | 2.85 |
| val1 | observed | uncertain | order_up_to | 43/50 | 333.357 | 341.648 | 180.800 | 1.2730 | 150.481 | 0.625 | 55.668 | 8.728 | 6.2 | 9.4 |  | 0.21 |
| val1 | observed | uncertain | periodic:1 | 32/50 | 323.360 | 337.362 | 278.104 | 2.7485 | 61.608 | 0.859 | 30.726 | 21.747 | 2.7 | 11.1 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 32/50 | 324.060 | 337.982 | 276.662 | 2.7087 | 63.364 | 0.856 | 31.409 | 21.600 | 2.8 | 10.0 |  | 0.03 |
| val2 | observed | fill_only | base_stock | 49/50 | 323.196 | 335.956 | 317.232 | 2.2950 | 31.811 | 0.855 | 20.932 | 18.750 | 2.7 | 11.0 |  | 0.37 |
| val2 | observed | fill_only | gated | 39/50 | 359.920 | 375.000 | 370.541 | 4.2459 | 18.880 | 0.935 | 14.485 | 31.378 | 1.4 | 9.0 | 0.44 | 4.92 |
| val2 | observed | fill_only | order_up_to | 49/50 | 326.905 | 335.770 | 259.940 | 0.9860 | 72.465 | 0.744 | 41.995 | 8.347 | 5.1 | 10.8 |  | 0.20 |
| val2 | observed | fill_only | periodic:1 | 39/50 | 360.713 | 375.395 | 365.247 | 2.3406 | 24.579 | 0.923 | 17.420 | 19.434 | 1.9 | 12.0 |  | 0.03 |
| val2 | observed | fill_only | reorder_point | 39/50 | 360.618 | 375.238 | 364.606 | 2.3307 | 24.763 | 0.922 | 17.955 | 19.371 | 1.9 | 11.2 |  | 0.04 |
| val2 | observed | lead_only | base_stock | 49/50 | 297.015 | 310.491 | 262.873 | 1.9871 | 64.511 | 0.791 | 36.097 | 16.023 | 3.8 | 10.7 |  | 0.38 |
| val2 | observed | lead_only | gated | 41/50 | 323.940 | 341.144 | 325.230 | 2.8221 | 43.776 | 0.890 | 26.883 | 21.192 | 2.3 | 11.0 | 0.49 | 3.75 |
| val2 | observed | lead_only | order_up_to | 49/50 | 311.905 | 321.035 | 199.805 | 0.9615 | 119.620 | 0.646 | 60.787 | 7.348 | 6.2 | 10.1 |  | 0.20 |
| val2 | observed | lead_only | periodic:1 | 43/50 | 321.602 | 336.265 | 290.261 | 1.9601 | 63.933 | 0.847 | 35.213 | 15.765 | 3.1 | 11.3 |  | 0.03 |
| val2 | observed | lead_only | reorder_point | 43/50 | 321.676 | 336.272 | 289.651 | 1.9458 | 64.257 | 0.845 | 35.716 | 15.615 | 3.2 | 10.0 |  | 0.03 |
| val2 | observed | mild_lead | base_stock | 49/50 | 293.955 | 307.396 | 270.164 | 2.1996 | 53.672 | 0.806 | 29.427 | 17.893 | 3.4 | 10.9 |  | 0.37 |
| val2 | observed | mild_lead | gated | 41/50 | 312.516 | 329.958 | 325.237 | 2.8294 | 34.208 | 0.895 | 20.449 | 21.226 | 2.0 | 10.7 | 0.45 | 3.34 |
| val2 | observed | mild_lead | order_up_to | 49/50 | 306.887 | 315.955 | 210.707 | 1.0116 | 102.996 | 0.679 | 52.916 | 8.063 | 5.6 | 10.5 |  | 0.20 |
| val2 | observed | mild_lead | periodic:1 | 41/50 | 319.387 | 334.638 | 304.180 | 2.5380 | 48.418 | 0.869 | 26.092 | 20.709 | 2.6 | 11.3 |  | 0.03 |
| val2 | observed | mild_lead | reorder_point | 41/50 | 319.437 | 334.642 | 303.658 | 2.5124 | 48.724 | 0.867 | 26.242 | 20.391 | 2.7 | 10.1 |  | 0.03 |
| val2 | observed | stable | base_stock | 49/50 | 286.842 | 300.146 | 286.201 | 2.4429 | 29.435 | 0.862 | 19.261 | 19.321 | 2.5 | 11.1 |  | 0.36 |
| val2 | observed | stable | gated | 41/50 | 317.200 | 332.503 | 327.257 | 2.6025 | 23.859 | 0.927 | 16.115 | 20.550 | 1.6 | 10.8 | 0.22 | 3.47 |
| val2 | observed | stable | order_up_to | 49/50 | 296.515 | 305.339 | 233.001 | 1.0220 | 68.769 | 0.752 | 39.655 | 8.121 | 5.1 | 11.0 |  | 0.20 |
| val2 | observed | stable | periodic:1 | 41/50 | 317.257 | 332.153 | 324.275 | 2.5456 | 24.536 | 0.925 | 16.755 | 20.274 | 1.6 | 11.8 |  | 0.03 |
| val2 | observed | stable | reorder_point | 41/50 | 317.294 | 332.146 | 323.865 | 2.5297 | 24.739 | 0.924 | 16.872 | 20.022 | 1.7 | 10.6 |  | 0.03 |
| val2 | observed | uncertain | base_stock | 49/50 | 323.471 | 336.264 | 291.213 | 2.0026 | 58.782 | 0.783 | 34.586 | 15.415 | 3.9 | 10.7 |  | 0.37 |
| val2 | observed | uncertain | gated | 40/50 | 358.827 | 375.093 | 355.529 | 3.7759 | 41.950 | 0.877 | 29.019 | 23.502 | 2.2 | 8.6 | 0.41 | 2.85 |
| val2 | observed | uncertain | order_up_to | 49/50 | 332.410 | 341.404 | 224.530 | 0.9632 | 114.446 | 0.642 | 61.312 | 7.495 | 6.0 | 10.3 |  | 0.21 |
| val2 | observed | uncertain | periodic:1 | 40/50 | 355.899 | 370.095 | 326.553 | 1.9735 | 57.323 | 0.837 | 34.138 | 15.113 | 3.4 | 11.8 |  | 0.03 |
| val2 | observed | uncertain | reorder_point | 40/50 | 355.820 | 369.994 | 326.254 | 1.9584 | 57.433 | 0.837 | 34.278 | 14.765 | 3.4 | 10.7 |  | 0.03 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 46 | -2.532 | [-5.410, +0.206] | [-7.107, +1.339] | 26 / 16 / 4 | 0.164 |
| final | observed | fill_only | periodic:1 | 46 | -2.593 | [-5.588, +0.071] | [-7.631, +1.194] | 29 / 16 / 1 | 0.072 |
| final | observed | fill_only | base_stock | 47 | -2.202 | [-4.705, +0.164] | [-6.495, +1.107] | 30 / 16 / 1 | 0.054 |
| final | observed | fill_only | order_up_to | 47 | -8.128 | [-12.840, -3.660] | [-16.643, -2.199] | 32 / 13 / 2 | 0.007 |
| final | observed | lead_only | reorder_point | 48 | -3.649 | [-5.104, -2.289] | [-5.895, -1.664] | 26 / 21 / 1 | 0.56 |
| final | observed | lead_only | periodic:1 | 48 | -3.461 | [-4.926, -2.111] | [-5.718, -1.498] | 25 / 23 / 0 | 0.885 |
| final | observed | lead_only | base_stock | 48 | -3.455 | [-4.879, -2.091] | [-5.658, -1.416] | 24 / 24 / 0 | 1.0 |
| final | observed | lead_only | order_up_to | 48 | -18.467 | [-22.285, -14.706] | [-24.728, -13.041] | 44 / 3 / 1 | 0.0 |
| final | observed | mild_lead | reorder_point | 46 | -2.724 | [-4.061, -1.400] | [-4.939, -0.774] | 22 / 22 / 2 | 1.0 |
| final | observed | mild_lead | periodic:1 | 46 | -2.406 | [-3.837, -0.998] | [-4.640, -0.285] | 21 / 24 / 1 | 0.766 |
| final | observed | mild_lead | base_stock | 46 | -2.380 | [-3.860, -0.983] | [-4.668, -0.316] | 21 / 24 / 1 | 0.766 |
| final | observed | mild_lead | order_up_to | 46 | -20.146 | [-25.372, -15.174] | [-28.358, -13.044] | 43 / 1 / 2 | 0.0 |
| final | observed | stable | reorder_point | 47 | -0.417 | [-0.797, -0.092] | [-1.028, +0.060] | 22 / 18 / 7 | 0.636 |
| final | observed | stable | periodic:1 | 47 | -0.393 | [-0.766, -0.052] | [-0.971, +0.084] | 21 / 22 / 4 | 1.0 |
| final | observed | stable | base_stock | 47 | -0.433 | [-0.872, -0.052] | [-1.163, +0.101] | 21 / 22 / 4 | 1.0 |
| final | observed | stable | order_up_to | 47 | -12.529 | [-16.018, -9.350] | [-18.114, -8.033] | 42 / 3 / 2 | 0.0 |
| final | observed | uncertain | reorder_point | 46 | -2.106 | [-5.588, +1.174] | [-7.803, +2.484] | 21 / 22 / 3 | 1.0 |
| final | observed | uncertain | periodic:1 | 46 | -2.113 | [-5.603, +1.055] | [-7.715, +2.462] | 21 / 24 / 1 | 0.766 |
| final | observed | uncertain | base_stock | 46 | -1.816 | [-5.177, +1.296] | [-7.253, +2.712] | 22 / 23 / 1 | 1.0 |
| final | observed | uncertain | order_up_to | 46 | -8.840 | [-14.055, -4.341] | [-17.146, -2.457] | 31 / 13 / 2 | 0.01 |
| val1 | observed | fill_only | reorder_point | 31 | +3.916 | [+1.376, +6.650] | [+0.140, +8.364] | 9 / 21 / 1 | 0.043 |
| val1 | observed | fill_only | periodic:1 | 31 | +4.102 | [+1.608, +6.747] | [+0.508, +8.542] | 10 / 21 / 0 | 0.071 |
| val1 | observed | fill_only | base_stock | 31 | +4.540 | [+2.052, +7.175] | [+1.002, +8.783] | 11 / 20 / 0 | 0.15 |
| val1 | observed | fill_only | order_up_to | 31 | -1.874 | [-4.725, +1.064] | [-6.221, +2.706] | 17 / 14 / 0 | 0.72 |
| val1 | observed | lead_only | reorder_point | 33 | -1.606 | [-3.141, -0.133] | [-4.129, +0.479] | 14 / 19 / 0 | 0.487 |
| val1 | observed | lead_only | periodic:1 | 33 | -1.328 | [-2.883, +0.132] | [-3.899, +0.803] | 13 / 20 / 0 | 0.296 |
| val1 | observed | lead_only | base_stock | 33 | -1.328 | [-2.884, +0.154] | [-3.798, +0.798] | 13 / 20 / 0 | 0.296 |
| val1 | observed | lead_only | order_up_to | 33 | -15.309 | [-19.389, -11.360] | [-21.809, -9.488] | 30 / 3 / 0 | 0.0 |
| val1 | observed | mild_lead | reorder_point | 33 | -1.342 | [-2.674, -0.063] | [-3.450, +0.537] | 13 / 19 / 1 | 0.377 |
| val1 | observed | mild_lead | periodic:1 | 33 | -0.939 | [-2.301, +0.371] | [-3.117, +0.970] | 13 / 20 / 0 | 0.296 |
| val1 | observed | mild_lead | base_stock | 33 | -0.937 | [-2.324, +0.376] | [-3.192, +0.957] | 13 / 20 / 0 | 0.296 |
| val1 | observed | mild_lead | order_up_to | 33 | -14.574 | [-18.553, -10.661] | [-21.059, -8.951] | 30 / 3 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 35 | +0.226 | [+0.013, +0.454] | [-0.074, +0.605] | 10 / 18 / 7 | 0.185 |
| val1 | observed | stable | periodic:1 | 35 | +0.551 | [+0.133, +1.044] | [-0.034, +1.338] | 17 / 17 / 1 | 1.0 |
| val1 | observed | stable | base_stock | 35 | +0.404 | [-0.036, +0.858] | [-0.202, +1.163] | 16 / 18 / 1 | 0.864 |
| val1 | observed | stable | order_up_to | 35 | -10.572 | [-13.707, -7.687] | [-15.503, -6.590] | 32 / 3 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 32 | +5.839 | [+2.449, +9.246] | [+0.887, +11.214] | 9 / 22 / 1 | 0.029 |
| val1 | observed | uncertain | periodic:1 | 32 | +6.539 | [+3.134, +10.210] | [+1.383, +12.162] | 8 / 24 / 0 | 0.007 |
| val1 | observed | uncertain | base_stock | 33 | +6.202 | [+2.828, +9.800] | [+1.138, +11.701] | 9 / 24 / 0 | 0.014 |
| val1 | observed | uncertain | order_up_to | 33 | +0.820 | [-3.276, +4.867] | [-5.316, +7.125] | 19 / 14 / 0 | 0.487 |
| val2 | observed | fill_only | reorder_point | 39 | -0.698 | [-4.685, +3.080] | [-6.866, +5.170] | 17 / 21 / 1 | 0.627 |
| val2 | observed | fill_only | periodic:1 | 39 | -0.793 | [-4.664, +3.167] | [-6.839, +5.368] | 18 / 21 / 0 | 0.749 |
| val2 | observed | fill_only | base_stock | 39 | -0.840 | [-4.538, +3.000] | [-6.615, +5.441] | 19 / 20 / 0 | 1.0 |
| val2 | observed | fill_only | order_up_to | 39 | -5.689 | [-10.209, -1.559] | [-12.763, +0.358] | 24 / 15 / 0 | 0.2 |
| val2 | observed | lead_only | reorder_point | 41 | -5.093 | [-7.225, -3.086] | [-8.482, -2.200] | 27 / 14 / 0 | 0.06 |
| val2 | observed | lead_only | periodic:1 | 41 | -5.016 | [-7.205, -3.018] | [-8.445, -2.269] | 27 / 14 / 0 | 0.06 |
| val2 | observed | lead_only | base_stock | 41 | -5.008 | [-7.125, -2.997] | [-8.468, -2.223] | 27 / 14 / 0 | 0.06 |
| val2 | observed | lead_only | order_up_to | 41 | -22.434 | [-28.621, -16.801] | [-32.472, -14.761] | 41 / 0 / 0 | 0.0 |
| val2 | observed | mild_lead | reorder_point | 40 | -2.862 | [-4.934, -1.032] | [-6.084, -0.296] | 20 / 20 / 0 | 1.0 |
| val2 | observed | mild_lead | periodic:1 | 40 | -2.790 | [-4.898, -0.891] | [-6.117, -0.182] | 20 / 20 / 0 | 1.0 |
| val2 | observed | mild_lead | base_stock | 41 | -2.721 | [-4.683, -0.861] | [-5.947, -0.191] | 20 / 21 / 0 | 1.0 |
| val2 | observed | mild_lead | order_up_to | 41 | -17.920 | [-23.626, -12.604] | [-27.096, -10.556] | 39 / 2 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 41 | -0.094 | [-0.378, +0.145] | [-0.564, +0.220] | 14 / 22 / 5 | 0.243 |
| val2 | observed | stable | periodic:1 | 41 | -0.058 | [-0.342, +0.188] | [-0.519, +0.278] | 16 / 23 / 2 | 0.337 |
| val2 | observed | stable | base_stock | 41 | -0.245 | [-0.711, +0.176] | [-1.109, +0.258] | 17 / 22 / 2 | 0.522 |
| val2 | observed | stable | order_up_to | 41 | -11.618 | [-14.611, -8.662] | [-16.510, -7.530] | 38 / 3 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 40 | +3.007 | [+0.899, +5.162] | [-0.067, +6.453] | 16 / 23 / 1 | 0.337 |
| val2 | observed | uncertain | periodic:1 | 40 | +2.928 | [+0.807, +5.080] | [-0.223, +6.397] | 17 / 23 / 0 | 0.43 |
| val2 | observed | uncertain | base_stock | 40 | +3.404 | [+1.141, +5.641] | [+0.136, +6.822] | 15 / 25 / 0 | 0.154 |
| val2 | observed | uncertain | order_up_to | 40 | -7.297 | [-10.602, -4.092] | [-12.814, -2.357] | 27 / 13 / 0 | 0.038 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 46 | -7.5816 | [-13.6965, -2.2081] | 20 / 7 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 46 | +8.3180 | [+4.3799, +13.5319] | 3 / 38 |
| final | observed | fill_only | reorder_point | service_unit_fill | 46 | +0.0153 | [+0.0055, +0.0268] | 20 / 7 |
| final | observed | fill_only | periodic:1 | shortage | 46 | -7.4291 | [-13.0755, -2.3276] | 20 / 7 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 46 | +8.1973 | [+4.1915, +13.6511] | 6 / 38 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 46 | +0.0145 | [+0.0041, +0.0257] | 20 / 7 |
| final | observed | fill_only | base_stock | shortage | 47 | -6.9374 | [-12.5481, -2.2525] | 20 / 12 |
| final | observed | fill_only | base_stock | avg_inventory_units | 47 | +6.9391 | [+3.0254, +11.8021] | 10 / 35 |
| final | observed | fill_only | base_stock | service_unit_fill | 47 | +0.0104 | [+0.0007, +0.0207] | 20 / 12 |
| final | observed | fill_only | order_up_to | shortage | 47 | -51.9311 | [-70.5727, -36.9426] | 44 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 47 | +16.8959 | [+10.1259, +25.4798] | 0 / 45 |
| final | observed | fill_only | order_up_to | service_unit_fill | 47 | +0.1321 | [+0.1100, +0.1548] | 44 / 0 |
| final | observed | lead_only | reorder_point | shortage | 48 | -17.2258 | [-24.7911, -10.6345] | 27 / 3 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 48 | +4.2685 | [+2.3455, +6.6190] | 2 / 42 |
| final | observed | lead_only | reorder_point | service_unit_fill | 48 | +0.0374 | [+0.0245, +0.0511] | 27 / 3 |
| final | observed | lead_only | periodic:1 | shortage | 48 | -16.5397 | [-24.1000, -9.8723] | 27 / 6 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 48 | +4.1963 | [+2.3157, +6.4495] | 5 / 42 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 48 | +0.0342 | [+0.0213, +0.0479] | 27 / 6 |
| final | observed | lead_only | base_stock | shortage | 48 | -16.5397 | [-24.2594, -9.8623] | 27 / 6 |
| final | observed | lead_only | base_stock | avg_inventory_units | 48 | +4.2541 | [+2.3821, +6.5912] | 4 / 43 |
| final | observed | lead_only | base_stock | service_unit_fill | 48 | +0.0342 | [+0.0217, +0.0472] | 27 / 6 |
| final | observed | lead_only | order_up_to | shortage | 48 | -72.8126 | [-95.7029, -52.7127] | 45 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 48 | +11.8007 | [+7.2638, +17.6122] | 0 / 47 |
| final | observed | lead_only | order_up_to | service_unit_fill | 48 | +0.1823 | [+0.1565, +0.2076] | 45 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 46 | -13.3057 | [-20.4177, -7.1203] | 24 / 5 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 46 | +3.6469 | [+2.0042, +5.8292] | 2 / 41 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 46 | +0.0250 | [+0.0137, +0.0375] | 24 / 5 |
| final | observed | mild_lead | periodic:1 | shortage | 46 | -12.1977 | [-19.4106, -5.7245] | 23 / 10 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 46 | +3.6088 | [+2.0255, +5.6876] | 2 / 42 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 46 | +0.0224 | [+0.0116, +0.0345] | 23 / 10 |
| final | observed | mild_lead | base_stock | shortage | 46 | -12.1977 | [-19.5943, -5.7537] | 23 / 10 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 46 | +3.6034 | [+1.9597, +5.7534] | 2 / 42 |
| final | observed | mild_lead | base_stock | service_unit_fill | 46 | +0.0224 | [+0.0114, +0.0344] | 23 / 10 |
| final | observed | mild_lead | order_up_to | shortage | 46 | -77.5023 | [-107.3857, -51.9144] | 43 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 46 | +11.5579 | [+6.7786, +18.3333] | 0 / 44 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 46 | +0.1719 | [+0.1468, +0.1973] | 43 / 0 |
| final | observed | stable | reorder_point | shortage | 47 | -1.4832 | [-2.9780, -0.2155] | 10 / 3 |
| final | observed | stable | reorder_point | avg_inventory_units | 47 | +0.2049 | [-0.3790, +0.8986] | 20 / 19 |
| final | observed | stable | reorder_point | service_unit_fill | 47 | +0.0030 | [-0.0009, +0.0074] | 10 / 3 |
| final | observed | stable | periodic:1 | shortage | 47 | -1.3216 | [-2.8483, -0.0341] | 10 / 7 |
| final | observed | stable | periodic:1 | avg_inventory_units | 47 | +0.1564 | [-0.3744, +0.7886] | 23 / 18 |
| final | observed | stable | periodic:1 | service_unit_fill | 47 | +0.0018 | [-0.0023, +0.0064] | 10 / 7 |
| final | observed | stable | base_stock | shortage | 47 | -1.7155 | [-4.0065, +0.0039] | 10 / 7 |
| final | observed | stable | base_stock | avg_inventory_units | 47 | +0.1615 | [-0.3632, +0.8035] | 25 / 16 |
| final | observed | stable | base_stock | service_unit_fill | 47 | +0.0029 | [-0.0022, +0.0094] | 10 / 7 |
| final | observed | stable | order_up_to | shortage | 47 | -49.0919 | [-68.8599, -33.5766] | 44 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 47 | +10.5403 | [+5.6509, +17.8716] | 0 / 45 |
| final | observed | stable | order_up_to | service_unit_fill | 47 | +0.1241 | [+0.1033, +0.1460] | 44 / 0 |
| final | observed | uncertain | reorder_point | shortage | 46 | -26.5363 | [-41.0461, -14.2417] | 30 / 3 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 46 | +9.0929 | [+4.8577, +14.5372] | 1 / 40 |
| final | observed | uncertain | reorder_point | service_unit_fill | 46 | +0.0410 | [+0.0279, +0.0559] | 30 / 3 |
| final | observed | uncertain | periodic:1 | shortage | 46 | -26.2020 | [-41.0538, -13.8069] | 30 / 4 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 46 | +9.0135 | [+4.7468, +14.3930] | 4 / 40 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 46 | +0.0392 | [+0.0257, +0.0539] | 30 / 4 |
| final | observed | uncertain | base_stock | shortage | 46 | -21.8042 | [-34.9903, -11.0261] | 28 / 9 |
| final | observed | uncertain | base_stock | avg_inventory_units | 46 | +8.1981 | [+3.9676, +13.5498] | 10 / 34 |
| final | observed | uncertain | base_stock | service_unit_fill | 46 | +0.0328 | [+0.0194, +0.0480] | 28 / 9 |
| final | observed | uncertain | order_up_to | shortage | 46 | -81.0441 | [-113.8925, -54.3682] | 43 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 46 | +15.2048 | [+9.3831, +22.2665] | 0 / 44 |
| final | observed | uncertain | order_up_to | service_unit_fill | 46 | +0.1758 | [+0.1514, +0.2012] | 43 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 31 | -5.3086 | [-10.6225, -1.6184] | 10 / 1 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 31 | +9.4282 | [+4.7623, +15.3899] | 3 / 27 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 31 | +0.0088 | [+0.0023, +0.0171] | 10 / 1 |
| val1 | observed | fill_only | periodic:1 | shortage | 31 | -4.9169 | [-10.3481, -1.2493] | 10 / 2 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 31 | +9.2529 | [+4.5253, +15.3725] | 4 / 27 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 31 | +0.0072 | [+0.0005, +0.0153] | 10 / 2 |
| val1 | observed | fill_only | base_stock | shortage | 31 | -3.6897 | [-8.6153, -0.4631] | 7 / 5 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 31 | +7.7804 | [+3.5655, +12.9004] | 7 / 24 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 31 | +0.0047 | [-0.0016, +0.0124] | 7 / 5 |
| val1 | observed | fill_only | order_up_to | shortage | 31 | -52.5618 | [-76.1526, -33.4377] | 29 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 31 | +22.6783 | [+11.6399, +39.9483] | 0 / 31 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 31 | +0.1349 | [+0.1087, +0.1628] | 29 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 33 | -12.0457 | [-21.9002, -4.8785] | 15 / 1 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 33 | +12.0369 | [+3.7169, +26.4531] | 5 / 27 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 33 | +0.0284 | [+0.0160, +0.0422] | 15 / 1 |
| val1 | observed | lead_only | periodic:1 | shortage | 33 | -10.9331 | [-20.5337, -3.7145] | 15 / 3 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 33 | +11.9041 | [+3.7760, +26.0267] | 4 / 28 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 33 | +0.0261 | [+0.0137, +0.0394] | 15 / 3 |
| val1 | observed | lead_only | base_stock | shortage | 33 | -10.9331 | [-20.6546, -3.5419] | 15 / 3 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 33 | +11.9111 | [+3.6003, +26.2486] | 4 / 28 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 33 | +0.0261 | [+0.0132, +0.0400] | 15 / 3 |
| val1 | observed | lead_only | order_up_to | shortage | 33 | -64.1118 | [-87.4926, -42.8342] | 32 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 33 | +23.3654 | [+9.3028, +47.0729] | 0 / 33 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 33 | +0.1744 | [+0.1456, +0.2028] | 32 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 33 | -8.6927 | [-15.6441, -3.4645] | 13 / 2 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 33 | +5.6807 | [+2.6896, +9.5805] | 1 / 30 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 33 | +0.0179 | [+0.0084, +0.0281] | 13 / 2 |
| val1 | observed | mild_lead | periodic:1 | shortage | 33 | -7.2232 | [-14.3976, -1.4423] | 12 / 5 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 33 | +5.5672 | [+2.6050, +9.3822] | 5 / 28 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 33 | +0.0160 | [+0.0064, +0.0275] | 12 / 5 |
| val1 | observed | mild_lead | base_stock | shortage | 33 | -7.2232 | [-14.4008, -1.4805] | 12 / 5 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 33 | +5.5862 | [+2.6375, +9.4922] | 5 / 28 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 33 | +0.0160 | [+0.0063, +0.0265] | 12 / 5 |
| val1 | observed | mild_lead | order_up_to | shortage | 33 | -59.4796 | [-81.5975, -39.9336] | 32 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 33 | +17.3074 | [+8.4343, +30.3515] | 0 / 33 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 33 | +0.1584 | [+0.1342, +0.1839] | 32 / 0 |
| val1 | observed | stable | reorder_point | shortage | 35 | +0.3039 | [-0.7058, +1.5583] | 5 / 3 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 35 | +1.3366 | [+0.2855, +2.6796] | 5 / 18 |
| val1 | observed | stable | reorder_point | service_unit_fill | 35 | -0.0006 | [-0.0073, +0.0041] | 5 / 3 |
| val1 | observed | stable | periodic:1 | shortage | 35 | +1.5812 | [-0.4685, +4.2547] | 5 / 3 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 35 | +1.1833 | [+0.1760, +2.5175] | 14 / 17 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 35 | -0.0023 | [-0.0084, +0.0025] | 5 / 3 |
| val1 | observed | stable | base_stock | shortage | 35 | +1.0940 | [-0.9535, +3.6144] | 5 / 3 |
| val1 | observed | stable | base_stock | avg_inventory_units | 35 | +1.1950 | [+0.1609, +2.6041] | 15 / 18 |
| val1 | observed | stable | base_stock | service_unit_fill | 35 | +0.0025 | [-0.0043, +0.0124] | 5 / 3 |
| val1 | observed | stable | order_up_to | shortage | 35 | -42.8458 | [-60.5973, -28.1884] | 33 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 35 | +14.6377 | [+6.7925, +26.8333] | 0 / 35 |
| val1 | observed | stable | order_up_to | service_unit_fill | 35 | +0.1244 | [+0.0989, +0.1516] | 33 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 32 | -13.6465 | [-28.4312, -2.2216] | 13 / 4 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 32 | +12.5613 | [+4.7916, +24.5440] | 4 / 25 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 32 | +0.0272 | [+0.0084, +0.0498] | 13 / 4 |
| val1 | observed | uncertain | periodic:1 | shortage | 32 | -11.8906 | [-26.8477, -0.1523] | 12 / 8 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 32 | +12.4146 | [+4.5528, +24.0766] | 5 / 26 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 32 | +0.0238 | [+0.0046, +0.0459] | 12 / 8 |
| val1 | observed | uncertain | base_stock | shortage | 33 | -9.5852 | [-23.9653, +1.4516] | 14 / 10 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 33 | +10.8055 | [+3.8193, +21.0243] | 10 / 23 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 33 | +0.0206 | [+0.0014, +0.0412] | 14 / 10 |
| val1 | observed | uncertain | order_up_to | shortage | 33 | -61.9938 | [-86.2814, -40.9797] | 32 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 33 | +22.3802 | [+9.7681, +42.5144] | 0 / 33 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 33 | +0.1654 | [+0.1367, +0.1948] | 32 / 0 |
| val2 | observed | fill_only | reorder_point | shortage | 39 | -5.8832 | [-10.5641, -1.8375] | 20 / 3 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 39 | +12.0074 | [+6.4033, +19.3103] | 5 / 32 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 39 | +0.0132 | [+0.0056, +0.0211] | 20 / 3 |
| val2 | observed | fill_only | periodic:1 | shortage | 39 | -5.6993 | [-10.8802, -1.6658] | 19 / 4 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 39 | +11.9440 | [+6.5018, +18.8932] | 7 / 32 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 39 | +0.0125 | [+0.0050, +0.0205] | 19 / 4 |
| val2 | observed | fill_only | base_stock | shortage | 39 | -3.7604 | [-7.8893, -0.2904] | 14 / 11 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 39 | +10.7910 | [+5.7503, +17.6018] | 10 / 29 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 39 | +0.0073 | [-0.0001, +0.0152] | 14 / 11 |
| val2 | observed | fill_only | order_up_to | shortage | 39 | -53.1205 | [-75.4903, -35.2531] | 38 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 39 | +22.9544 | [+13.3168, +35.4930] | 0 / 39 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 39 | +0.1331 | [+0.1120, +0.1543] | 38 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 41 | -21.5630 | [-34.3012, -11.5429] | 30 / 1 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 41 | +5.0163 | [+2.9722, +7.3148] | 6 / 35 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 41 | +0.0438 | [+0.0316, +0.0563] | 30 / 1 |
| val2 | observed | lead_only | periodic:1 | shortage | 41 | -21.2232 | [-34.7829, -10.8320] | 30 / 3 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 41 | +4.8661 | [+2.8832, +7.2731] | 6 / 35 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 41 | +0.0419 | [+0.0285, +0.0546] | 30 / 3 |
| val2 | observed | lead_only | base_stock | shortage | 41 | -21.2733 | [-33.7240, -10.7981] | 31 / 3 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 41 | +5.0497 | [+3.0072, +7.2532] | 6 / 35 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 41 | +0.0419 | [+0.0295, +0.0548] | 31 / 3 |
| val2 | observed | lead_only | order_up_to | shortage | 41 | -85.0962 | [-120.0209, -57.8402] | 41 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 41 | +14.3492 | [+8.1837, +23.0865] | 0 / 41 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 41 | +0.2031 | [+0.1830, +0.2245] | 41 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 40 | -13.6927 | [-24.5481, -5.0923] | 20 / 1 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 40 | +3.4861 | [+1.4087, +5.7341] | 5 / 35 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 40 | +0.0252 | [+0.0150, +0.0367] | 20 / 1 |
| val2 | observed | mild_lead | periodic:1 | shortage | 40 | -13.3784 | [-24.8556, -4.5312] | 20 / 4 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 40 | +3.2436 | [+1.1898, +5.4205] | 7 / 33 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 40 | +0.0236 | [+0.0129, +0.0347] | 20 / 4 |
| val2 | observed | mild_lead | base_stock | shortage | 41 | -13.0521 | [-24.3385, -4.5340] | 20 / 4 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 41 | +3.1609 | [+1.1671, +5.3112] | 8 / 33 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 41 | +0.0230 | [+0.0129, +0.0344] | 20 / 4 |
| val2 | observed | mild_lead | order_up_to | shortage | 41 | -70.3211 | [-103.9691, -45.1729] | 40 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 41 | +13.7869 | [+7.5002, +23.9280] | 0 / 41 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 41 | +0.1679 | [+0.1461, +0.1889] | 40 / 0 |
| val2 | observed | stable | reorder_point | shortage | 41 | -0.8805 | [-2.3193, +0.0518] | 6 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 41 | +0.5280 | [-0.1303, +1.3356] | 13 / 22 |
| val2 | observed | stable | reorder_point | service_unit_fill | 41 | +0.0020 | [-0.0007, +0.0049] | 6 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 41 | -0.6774 | [-2.1230, +0.3329] | 5 / 4 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 41 | +0.2762 | [-0.3487, +1.0094] | 18 / 21 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 41 | +0.0010 | [-0.0019, +0.0042] | 5 / 4 |
| val2 | observed | stable | base_stock | shortage | 41 | -1.3501 | [-4.1739, +0.3101] | 5 / 4 |
| val2 | observed | stable | base_stock | avg_inventory_units | 41 | +0.4419 | [-0.0940, +1.0911] | 18 / 21 |
| val2 | observed | stable | base_stock | service_unit_fill | 41 | +0.0020 | [-0.0019, +0.0069] | 5 / 4 |
| val2 | observed | stable | order_up_to | shortage | 41 | -46.9735 | [-64.6896, -32.2443] | 40 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 41 | +12.8380 | [+7.1366, +22.1631] | 0 / 41 |
| val2 | observed | stable | order_up_to | service_unit_fill | 41 | +0.1246 | [+0.1048, +0.1438] | 40 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 40 | -15.4827 | [-22.7119, -9.0365] | 26 / 2 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 40 | +8.7370 | [+5.2140, +13.2321] | 5 / 34 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 40 | +0.0404 | [+0.0263, +0.0561] | 26 / 2 |
| val2 | observed | uncertain | periodic:1 | shortage | 40 | -15.3726 | [-22.8238, -8.9817] | 26 / 4 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 40 | +8.3887 | [+4.8938, +12.8235] | 6 / 34 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 40 | +0.0401 | [+0.0260, +0.0557] | 26 / 4 |
| val2 | observed | uncertain | base_stock | shortage | 40 | -12.3182 | [-18.8416, -6.0729] | 22 / 12 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 40 | +7.3122 | [+3.6255, +11.4793] | 8 / 32 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 40 | +0.0332 | [+0.0184, +0.0485] | 22 / 12 |
| val2 | observed | uncertain | order_up_to | shortage | 40 | -78.7257 | [-107.8242, -55.3109] | 40 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 40 | +16.2960 | [+10.8017, +22.9851] | 0 / 40 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 40 | +0.1949 | [+0.1724, +0.2184] | 40 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 725/750 complete, 0 infeasible, 0 abstained; gated: 621/750 complete, 0 infeasible, 104 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 632/750 complete, 0 infeasible, 0 abstained; reorder_point: 632/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 415
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +67.043 (fill 0.964 vs 0.946, inventory 68.34 vs 25.22, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +51.184 (fill 0.746 vs 0.723, inventory 18.75 vs 8.45, retained incumbent on None reviews)
- val1/observed/uncertain store TX_3 product HOBBIES_1_029: ZAAD minus order_up_to = +43.610 (fill 0.913 vs 0.808, inventory 53.08 vs 15.50, retained incumbent on None reviews)
- val1/observed/fill_only store TX_3 product HOBBIES_1_029: ZAAD minus reorder_point = +41.852 (fill 0.913 vs 0.913, inventory 66.87 vs 38.87, retained incumbent on None reviews)
- final/observed/uncertain store CA_1 product HOUSEHOLD_1_299: ZAAD minus order_up_to = +40.013 (fill 0.874 vs 0.700, inventory 32.80 vs 12.26, retained incumbent on None reviews)
- val2/observed/fill_only store CA_1 product HOUSEHOLD_1_324: ZAAD minus order_up_to = +37.022 (fill 1.000 vs 0.918, inventory 18.95 vs 3.33, retained incumbent on None reviews)
- val1/observed/uncertain store CA_1 product FOODS_3_535: ZAAD minus base_stock = +34.978 (fill 0.841 vs 0.831, inventory 4.18 vs 4.57, retained incumbent on None reviews)
- val1/observed/fill_only store CA_1 product FOODS_3_535: ZAAD minus periodic:1 = +34.769 (fill 0.947 vs 0.947, inventory 12.16 vs 6.16, retained incumbent on None reviews)
- val1/observed/uncertain store CA_3 product FOODS_2_318: ZAAD minus periodic:1 = +33.915 (fill 0.720 vs 0.750, inventory 55.09 vs 54.67, retained incumbent on None reviews)
- val2/observed/uncertain store CA_1 product FOODS_3_535: ZAAD minus reorder_point = +32.041 (fill 0.915 vs 0.882, inventory 25.30 vs 7.72, retained incumbent on None reviews)
