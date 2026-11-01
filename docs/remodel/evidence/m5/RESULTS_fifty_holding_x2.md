# Walmart M5 (Experiment A) results: stage `fifty_holding_x2`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `e9a8c6f4d888`, selection `8b6067be83a4`; 3750 runs, 3625 complete, 125 not complete; wall 3117 s, peak RSS 240 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 49/50 | 399.137 | 414.743 | 396.286 | 5.3675 | 35.122 | 0.927 | 14.801 | 19.903 | 1.9 | 10.8 |  | 0.48 |
| final | observed | fill_only | gated | 49/50 | 396.660 | 412.434 | 399.621 | 7.9249 | 27.926 | 0.936 | 12.626 | 26.054 | 1.6 | 8.9 | 0.37 | 5.53 |
| final | observed | fill_only | order_up_to | 49/50 | 402.987 | 414.436 | 330.587 | 2.4399 | 82.664 | 0.803 | 36.484 | 9.640 | 4.3 | 10.6 |  | 0.21 |
| final | observed | fill_only | periodic:1 | 49/50 | 399.048 | 414.138 | 390.534 | 4.9393 | 37.946 | 0.922 | 16.002 | 18.467 | 2.0 | 11.2 |  | 0.04 |
| final | observed | fill_only | reorder_point | 49/50 | 398.983 | 414.060 | 390.147 | 4.9230 | 38.188 | 0.921 | 16.072 | 18.357 | 2.1 | 10.4 |  | 0.04 |
| final | observed | lead_only | base_stock | 49/50 | 374.681 | 389.935 | 326.700 | 4.7719 | 79.127 | 0.847 | 29.439 | 17.012 | 2.9 | 10.6 |  | 0.46 |
| final | observed | lead_only | gated | 49/50 | 372.605 | 389.497 | 346.422 | 6.0934 | 66.164 | 0.875 | 24.881 | 20.221 | 2.7 | 9.5 | 0.38 | 3.38 |
| final | observed | lead_only | order_up_to | 49/50 | 388.160 | 399.326 | 262.188 | 2.4476 | 135.076 | 0.700 | 55.971 | 9.329 | 5.4 | 10.0 |  | 0.23 |
| final | observed | lead_only | periodic:1 | 49/50 | 374.679 | 389.933 | 326.700 | 4.7701 | 79.127 | 0.847 | 29.439 | 17.006 | 2.9 | 10.6 |  | 0.03 |
| final | observed | lead_only | reorder_point | 49/50 | 374.844 | 390.048 | 325.875 | 4.7544 | 79.799 | 0.844 | 29.939 | 16.930 | 3.0 | 9.6 |  | 0.04 |
| final | observed | mild_lead | base_stock | 49/50 | 372.639 | 388.959 | 337.853 | 4.6352 | 72.149 | 0.858 | 28.304 | 17.299 | 2.9 | 10.7 |  | 0.46 |
| final | observed | mild_lead | gated | 49/50 | 370.459 | 387.868 | 354.689 | 5.7267 | 59.538 | 0.873 | 23.258 | 20.450 | 2.4 | 9.7 | 0.38 | 3.30 |
| final | observed | mild_lead | order_up_to | 49/50 | 388.529 | 400.931 | 269.032 | 2.3969 | 135.729 | 0.707 | 56.303 | 9.539 | 5.2 | 10.1 |  | 0.22 |
| final | observed | mild_lead | periodic:1 | 49/50 | 372.637 | 388.957 | 337.853 | 4.6337 | 72.149 | 0.858 | 28.304 | 17.294 | 2.9 | 10.7 |  | 0.03 |
| final | observed | mild_lead | reorder_point | 49/50 | 372.965 | 389.261 | 336.848 | 4.6270 | 73.311 | 0.855 | 28.854 | 17.272 | 3.0 | 9.6 |  | 0.04 |
| final | observed | stable | base_stock | 49/50 | 361.910 | 377.369 | 358.305 | 5.3195 | 34.957 | 0.929 | 14.820 | 19.899 | 1.9 | 10.9 |  | 0.46 |
| final | observed | stable | gated | 49/50 | 361.433 | 376.932 | 359.938 | 5.3519 | 33.149 | 0.930 | 12.407 | 19.680 | 1.9 | 10.0 | 0.18 | 3.30 |
| final | observed | stable | order_up_to | 49/50 | 372.222 | 383.529 | 299.205 | 2.3902 | 82.478 | 0.803 | 36.904 | 9.555 | 4.5 | 10.5 |  | 0.22 |
| final | observed | stable | periodic:1 | 49/50 | 361.908 | 377.367 | 358.305 | 5.3177 | 34.957 | 0.929 | 14.820 | 19.893 | 1.9 | 10.8 |  | 0.03 |
| final | observed | stable | reorder_point | 49/50 | 361.950 | 377.372 | 357.843 | 5.2932 | 35.233 | 0.927 | 15.207 | 19.858 | 2.0 | 9.9 |  | 0.03 |
| final | observed | uncertain | base_stock | 49/50 | 423.272 | 438.587 | 355.912 | 4.1608 | 100.188 | 0.815 | 38.578 | 15.586 | 3.5 | 10.6 |  | 0.44 |
| final | observed | uncertain | gated | 49/50 | 420.294 | 437.282 | 380.381 | 6.3882 | 80.705 | 0.843 | 31.814 | 21.176 | 2.9 | 8.6 | 0.33 | 2.83 |
| final | observed | uncertain | order_up_to | 49/50 | 428.618 | 439.715 | 280.452 | 2.2303 | 158.091 | 0.670 | 61.663 | 8.689 | 5.7 | 10.0 |  | 0.23 |
| final | observed | uncertain | periodic:1 | 49/50 | 422.993 | 437.788 | 348.313 | 3.9192 | 104.481 | 0.808 | 40.046 | 14.757 | 3.5 | 11.1 |  | 0.04 |
| final | observed | uncertain | reorder_point | 49/50 | 422.971 | 437.761 | 347.980 | 3.8944 | 104.792 | 0.806 | 40.128 | 14.679 | 3.5 | 10.0 |  | 0.03 |
| val1 | observed | fill_only | base_stock | 43/50 | 318.371 | 332.085 | 299.674 | 6.8839 | 44.542 | 0.912 | 15.305 | 23.782 | 1.5 | 10.4 |  | 0.49 |
| val1 | observed | fill_only | gated | 43/50 | 322.547 | 337.055 | 311.522 | 8.6663 | 40.775 | 0.918 | 14.405 | 28.609 | 1.4 | 8.8 | 0.33 | 5.15 |
| val1 | observed | fill_only | order_up_to | 43/50 | 321.191 | 330.372 | 231.188 | 3.6849 | 91.147 | 0.787 | 33.609 | 11.203 | 4.4 | 10.1 |  | 0.22 |
| val1 | observed | fill_only | periodic:1 | 43/50 | 318.383 | 331.711 | 296.269 | 6.5367 | 45.832 | 0.908 | 15.739 | 22.481 | 1.6 | 11.0 |  | 0.04 |
| val1 | observed | fill_only | reorder_point | 43/50 | 318.453 | 331.736 | 295.588 | 6.4466 | 46.362 | 0.907 | 15.880 | 22.334 | 1.6 | 10.0 |  | 0.04 |
| val1 | observed | lead_only | base_stock | 43/50 | 295.215 | 309.071 | 253.099 | 5.8665 | 69.974 | 0.833 | 26.721 | 20.060 | 2.8 | 10.2 |  | 0.45 |
| val1 | observed | lead_only | gated | 43/50 | 294.847 | 310.784 | 274.748 | 7.0914 | 61.244 | 0.853 | 24.397 | 24.030 | 2.4 | 9.3 | 0.35 | 3.49 |
| val1 | observed | lead_only | order_up_to | 43/50 | 307.742 | 317.130 | 186.900 | 3.3760 | 124.042 | 0.687 | 48.171 | 10.141 | 5.5 | 9.6 |  | 0.23 |
| val1 | observed | lead_only | periodic:1 | 43/50 | 295.264 | 309.120 | 252.988 | 5.8680 | 70.133 | 0.832 | 26.788 | 20.065 | 2.8 | 10.2 |  | 0.04 |
| val1 | observed | lead_only | reorder_point | 43/50 | 295.459 | 309.279 | 252.078 | 5.7788 | 71.111 | 0.829 | 27.285 | 19.946 | 2.8 | 9.0 |  | 0.04 |
| val1 | observed | mild_lead | base_stock | 43/50 | 294.335 | 308.305 | 257.159 | 6.1942 | 65.645 | 0.857 | 23.665 | 21.053 | 2.5 | 10.4 |  | 0.47 |
| val1 | observed | mild_lead | gated | 43/50 | 295.310 | 310.912 | 272.682 | 7.3227 | 61.949 | 0.866 | 22.761 | 24.886 | 2.2 | 9.0 | 0.33 | 3.30 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 305.562 | 315.173 | 193.650 | 3.5215 | 116.194 | 0.720 | 46.192 | 10.692 | 5.2 | 9.8 |  | 0.23 |
| val1 | observed | mild_lead | periodic:1 | 43/50 | 294.383 | 308.353 | 257.048 | 6.1942 | 65.804 | 0.856 | 23.732 | 21.053 | 2.5 | 10.4 |  | 0.04 |
| val1 | observed | mild_lead | reorder_point | 43/50 | 294.662 | 308.595 | 255.937 | 6.1377 | 66.986 | 0.854 | 24.229 | 20.946 | 2.5 | 9.1 |  | 0.04 |
| val1 | observed | stable | base_stock | 43/50 | 288.327 | 302.014 | 270.151 | 6.9074 | 43.820 | 0.913 | 15.148 | 23.626 | 1.5 | 10.6 |  | 0.49 |
| val1 | observed | stable | gated | 43/50 | 288.945 | 302.737 | 270.097 | 6.9893 | 45.301 | 0.911 | 15.751 | 24.359 | 1.6 | 9.4 | 0.10 | 2.75 |
| val1 | observed | stable | order_up_to | 43/50 | 297.705 | 306.828 | 208.444 | 3.7033 | 90.092 | 0.789 | 33.315 | 11.134 | 4.3 | 10.2 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 43/50 | 288.327 | 302.014 | 270.144 | 6.9047 | 43.829 | 0.913 | 15.152 | 23.617 | 1.5 | 10.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 43/50 | 288.586 | 302.232 | 268.974 | 6.8103 | 45.072 | 0.911 | 15.660 | 23.474 | 1.6 | 9.4 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 43/50 | 328.624 | 342.247 | 279.742 | 5.7255 | 75.885 | 0.832 | 28.992 | 20.026 | 3.0 | 10.4 |  | 0.46 |
| val1 | observed | uncertain | gated | 43/50 | 333.827 | 349.432 | 307.223 | 8.0416 | 67.532 | 0.848 | 27.207 | 37.095 | 2.7 | 8.2 | 0.30 | 2.93 |
| val1 | observed | uncertain | order_up_to | 43/50 | 331.421 | 340.596 | 206.154 | 3.2402 | 127.513 | 0.688 | 50.360 | 9.943 | 5.3 | 9.8 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 43/50 | 328.317 | 341.640 | 275.806 | 5.4613 | 77.845 | 0.828 | 29.628 | 18.855 | 3.1 | 10.8 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 43/50 | 328.864 | 342.151 | 274.477 | 5.3864 | 79.611 | 0.823 | 30.308 | 18.702 | 3.1 | 9.7 |  | 0.04 |
| val2 | observed | fill_only | base_stock | 49/50 | 325.540 | 338.850 | 331.609 | 5.3013 | 23.003 | 0.915 | 16.175 | 21.605 | 1.7 | 11.2 |  | 0.51 |
| val2 | observed | fill_only | gated | 49/50 | 327.498 | 341.102 | 336.528 | 8.1709 | 20.350 | 0.920 | 14.766 | 30.489 | 1.5 | 8.9 | 0.35 | 5.07 |
| val2 | observed | fill_only | order_up_to | 49/50 | 327.143 | 336.085 | 266.828 | 2.1300 | 66.328 | 0.786 | 38.721 | 9.014 | 4.5 | 11.1 |  | 0.23 |
| val2 | observed | fill_only | periodic:1 | 49/50 | 325.177 | 338.102 | 327.696 | 4.9306 | 24.537 | 0.911 | 16.847 | 20.120 | 1.9 | 11.7 |  | 0.04 |
| val2 | observed | fill_only | reorder_point | 49/50 | 325.040 | 337.895 | 326.921 | 4.8972 | 24.715 | 0.910 | 17.279 | 19.990 | 1.9 | 10.7 |  | 0.04 |
| val2 | observed | lead_only | base_stock | 49/50 | 298.448 | 311.694 | 268.901 | 4.2638 | 59.631 | 0.835 | 33.164 | 17.266 | 3.1 | 10.9 |  | 0.48 |
| val2 | observed | lead_only | gated | 49/50 | 296.845 | 311.890 | 290.203 | 5.4381 | 47.726 | 0.859 | 29.367 | 20.119 | 2.6 | 9.6 | 0.41 | 3.50 |
| val2 | observed | lead_only | order_up_to | 49/50 | 312.332 | 321.276 | 202.845 | 1.9573 | 116.675 | 0.673 | 58.924 | 7.545 | 5.9 | 10.3 |  | 0.23 |
| val2 | observed | lead_only | periodic:1 | 49/50 | 298.448 | 311.694 | 268.901 | 4.2638 | 59.631 | 0.835 | 33.164 | 17.266 | 3.1 | 10.9 |  | 0.04 |
| val2 | observed | lead_only | reorder_point | 49/50 | 298.498 | 311.689 | 268.226 | 4.2141 | 60.040 | 0.833 | 33.633 | 17.029 | 3.2 | 9.5 |  | 0.04 |
| val2 | observed | mild_lead | base_stock | 49/50 | 295.325 | 308.528 | 276.711 | 4.7274 | 47.833 | 0.854 | 25.856 | 19.232 | 2.7 | 11.1 |  | 0.47 |
| val2 | observed | mild_lead | gated | 49/50 | 293.364 | 308.036 | 293.647 | 5.3881 | 37.513 | 0.873 | 21.615 | 21.471 | 2.3 | 10.0 | 0.40 | 3.47 |
| val2 | observed | mild_lead | order_up_to | 49/50 | 307.386 | 316.327 | 213.788 | 2.1061 | 100.115 | 0.707 | 51.096 | 8.422 | 5.2 | 10.5 |  | 0.23 |
| val2 | observed | mild_lead | periodic:1 | 49/50 | 295.325 | 308.528 | 276.711 | 4.7274 | 47.833 | 0.854 | 25.856 | 19.232 | 2.7 | 11.1 |  | 0.04 |
| val2 | observed | mild_lead | reorder_point | 49/50 | 295.369 | 308.551 | 276.280 | 4.6820 | 48.183 | 0.852 | 26.010 | 18.960 | 2.8 | 9.8 |  | 0.04 |
| val2 | observed | stable | base_stock | 49/50 | 288.299 | 301.570 | 294.643 | 5.3693 | 22.410 | 0.915 | 15.135 | 21.260 | 1.7 | 11.3 |  | 0.49 |
| val2 | observed | stable | gated | 49/50 | 288.461 | 301.885 | 295.636 | 5.4343 | 22.526 | 0.914 | 15.070 | 21.394 | 1.7 | 10.2 | 0.15 | 2.92 |
| val2 | observed | stable | order_up_to | 49/50 | 296.640 | 305.458 | 237.315 | 2.1590 | 64.600 | 0.788 | 37.204 | 8.612 | 4.5 | 11.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 49/50 | 288.299 | 301.570 | 294.643 | 5.3693 | 22.410 | 0.915 | 15.135 | 21.260 | 1.7 | 11.3 |  | 0.04 |
| val2 | observed | stable | reorder_point | 49/50 | 288.305 | 301.532 | 294.134 | 5.3245 | 22.655 | 0.914 | 15.264 | 20.971 | 1.7 | 10.1 |  | 0.04 |
| val2 | observed | uncertain | base_stock | 49/50 | 325.239 | 338.218 | 302.085 | 4.5576 | 51.376 | 0.836 | 30.418 | 17.554 | 3.1 | 10.9 |  | 0.47 |
| val2 | observed | uncertain | gated | 49/50 | 329.055 | 343.103 | 319.414 | 6.9896 | 43.807 | 0.860 | 27.987 | 24.267 | 2.3 | 8.5 | 0.35 | 2.91 |
| val2 | observed | uncertain | order_up_to | 49/50 | 332.836 | 341.778 | 228.968 | 2.0644 | 110.539 | 0.673 | 59.102 | 8.091 | 5.6 | 10.5 |  | 0.23 |
| val2 | observed | uncertain | periodic:1 | 49/50 | 325.454 | 338.096 | 297.760 | 4.2709 | 54.109 | 0.829 | 31.935 | 16.534 | 3.2 | 11.5 |  | 0.04 |
| val2 | observed | uncertain | reorder_point | 49/50 | 325.308 | 337.905 | 297.218 | 4.2199 | 54.229 | 0.829 | 32.067 | 16.140 | 3.3 | 10.2 |  | 0.04 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 49 | -2.323 | [-4.482, -0.140] | [-5.911, +0.879] | 25 / 20 / 4 | 0.551 |
| final | observed | fill_only | periodic:1 | 49 | -2.388 | [-4.652, -0.259] | [-5.815, +0.798] | 28 / 20 / 1 | 0.312 |
| final | observed | fill_only | base_stock | 49 | -2.477 | [-4.555, -0.456] | [-5.781, +0.500] | 29 / 19 / 1 | 0.193 |
| final | observed | fill_only | order_up_to | 49 | -6.327 | [-10.311, -2.733] | [-12.750, -1.165] | 30 / 17 / 2 | 0.079 |
| final | observed | lead_only | reorder_point | 49 | -2.240 | [-3.555, -0.970] | [-4.276, -0.315] | 25 / 22 / 2 | 0.771 |
| final | observed | lead_only | periodic:1 | 49 | -2.074 | [-3.367, -0.847] | [-4.080, -0.239] | 23 / 26 / 0 | 0.775 |
| final | observed | lead_only | base_stock | 49 | -2.076 | [-3.401, -0.821] | [-4.116, -0.207] | 23 / 26 / 0 | 0.775 |
| final | observed | lead_only | order_up_to | 49 | -15.555 | [-19.117, -12.235] | [-21.257, -10.794] | 44 / 4 / 1 | 0.0 |
| final | observed | mild_lead | reorder_point | 49 | -2.506 | [-4.410, -0.776] | [-5.751, -0.110] | 22 / 25 / 2 | 0.771 |
| final | observed | mild_lead | periodic:1 | 49 | -2.178 | [-4.124, -0.423] | [-5.294, +0.305] | 20 / 28 / 1 | 0.312 |
| final | observed | mild_lead | base_stock | 49 | -2.179 | [-4.150, -0.399] | [-5.347, +0.318] | 20 / 28 / 1 | 0.312 |
| final | observed | mild_lead | order_up_to | 49 | -18.069 | [-23.900, -12.733] | [-27.685, -10.694] | 45 / 2 / 2 | 0.0 |
| final | observed | stable | reorder_point | 49 | -0.517 | [-1.098, -0.007] | [-1.533, +0.156] | 20 / 19 / 10 | 1.0 |
| final | observed | stable | periodic:1 | 49 | -0.476 | [-1.019, +0.032] | [-1.393, +0.210] | 21 / 23 / 5 | 0.88 |
| final | observed | stable | base_stock | 49 | -0.477 | [-1.023, +0.012] | [-1.383, +0.175] | 22 / 22 / 5 | 1.0 |
| final | observed | stable | order_up_to | 49 | -10.789 | [-14.221, -7.754] | [-16.227, -6.459] | 42 / 5 / 2 | 0.0 |
| final | observed | uncertain | reorder_point | 49 | -2.677 | [-6.000, +0.428] | [-8.107, +1.647] | 20 / 26 / 3 | 0.461 |
| final | observed | uncertain | periodic:1 | 49 | -2.699 | [-5.973, +0.363] | [-8.100, +1.528] | 22 / 26 / 1 | 0.665 |
| final | observed | uncertain | base_stock | 49 | -2.978 | [-6.265, +0.144] | [-8.350, +1.359] | 23 / 25 / 1 | 0.885 |
| final | observed | uncertain | order_up_to | 49 | -8.324 | [-13.344, -3.796] | [-16.801, -1.988] | 28 / 19 / 2 | 0.243 |
| val1 | observed | fill_only | reorder_point | 43 | +4.094 | [+1.603, +6.842] | [+0.648, +8.653] | 13 / 27 / 3 | 0.038 |
| val1 | observed | fill_only | periodic:1 | 43 | +4.163 | [+1.828, +6.810] | [+0.902, +8.667] | 12 / 31 / 0 | 0.005 |
| val1 | observed | fill_only | base_stock | 43 | +4.175 | [+1.744, +7.055] | [+0.918, +8.854] | 14 / 29 / 0 | 0.032 |
| val1 | observed | fill_only | order_up_to | 43 | +1.355 | [-1.391, +4.298] | [-2.588, +6.250] | 23 / 20 / 0 | 0.761 |
| val1 | observed | lead_only | reorder_point | 43 | -0.612 | [-1.726, +0.516] | [-2.478, +1.045] | 17 / 24 / 2 | 0.349 |
| val1 | observed | lead_only | periodic:1 | 43 | -0.418 | [-1.559, +0.661] | [-2.249, +1.244] | 17 / 24 / 2 | 0.349 |
| val1 | observed | lead_only | base_stock | 43 | -0.368 | [-1.510, +0.722] | [-2.174, +1.250] | 17 / 24 / 2 | 0.349 |
| val1 | observed | lead_only | order_up_to | 43 | -12.895 | [-16.052, -9.601] | [-18.081, -8.057] | 37 / 6 / 0 | 0.0 |
| val1 | observed | mild_lead | reorder_point | 43 | +0.648 | [-0.394, +1.713] | [-0.809, +2.411] | 14 / 25 / 4 | 0.108 |
| val1 | observed | mild_lead | periodic:1 | 43 | +0.927 | [-0.055, +1.964] | [-0.434, +2.591] | 14 / 28 / 1 | 0.044 |
| val1 | observed | mild_lead | base_stock | 43 | +0.975 | [-0.020, +2.004] | [-0.446, +2.640] | 14 / 28 / 1 | 0.044 |
| val1 | observed | mild_lead | order_up_to | 43 | -10.252 | [-13.253, -7.377] | [-15.114, -6.033] | 39 / 4 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 43 | +0.360 | [+0.173, +0.558] | [+0.093, +0.686] | 6 / 24 / 13 | 0.001 |
| val1 | observed | stable | periodic:1 | 43 | +0.618 | [+0.252, +1.015] | [+0.106, +1.257] | 16 / 24 / 3 | 0.268 |
| val1 | observed | stable | base_stock | 43 | +0.618 | [+0.248, +1.008] | [+0.099, +1.238] | 16 / 24 / 3 | 0.268 |
| val1 | observed | stable | order_up_to | 43 | -8.759 | [-11.290, -6.331] | [-12.946, -5.371] | 37 / 6 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 43 | +4.963 | [+1.640, +8.405] | [-0.464, +10.293] | 10 / 29 / 4 | 0.003 |
| val1 | observed | uncertain | periodic:1 | 43 | +5.510 | [+2.093, +8.879] | [+0.072, +10.699] | 9 / 33 / 1 | 0.0 |
| val1 | observed | uncertain | base_stock | 43 | +5.204 | [+1.702, +8.609] | [-0.155, +10.438] | 13 / 30 / 0 | 0.014 |
| val1 | observed | uncertain | order_up_to | 43 | +2.406 | [-1.952, +6.752] | [-4.127, +9.064] | 21 / 22 / 0 | 1.0 |
| val2 | observed | fill_only | reorder_point | 49 | +2.458 | [-0.620, +5.615] | [-2.245, +7.375] | 17 / 30 / 2 | 0.079 |
| val2 | observed | fill_only | periodic:1 | 49 | +2.322 | [-0.687, +5.369] | [-2.313, +7.103] | 18 / 31 / 0 | 0.085 |
| val2 | observed | fill_only | base_stock | 49 | +1.959 | [-1.043, +5.029] | [-2.574, +6.944] | 20 / 29 / 0 | 0.253 |
| val2 | observed | fill_only | order_up_to | 49 | +0.356 | [-3.472, +4.084] | [-5.792, +6.051] | 27 / 22 / 0 | 0.568 |
| val2 | observed | lead_only | reorder_point | 49 | -1.653 | [-2.970, -0.366] | [-3.823, +0.227] | 26 / 22 / 1 | 0.665 |
| val2 | observed | lead_only | periodic:1 | 49 | -1.603 | [-2.956, -0.294] | [-3.830, +0.230] | 25 / 24 / 0 | 1.0 |
| val2 | observed | lead_only | base_stock | 49 | -1.603 | [-2.934, -0.339] | [-3.700, +0.200] | 25 / 24 / 0 | 1.0 |
| val2 | observed | lead_only | order_up_to | 49 | -15.487 | [-20.003, -11.265] | [-22.907, -9.517] | 47 / 2 / 0 | 0.0 |
| val2 | observed | mild_lead | reorder_point | 49 | -2.004 | [-3.484, -0.625] | [-4.469, -0.055] | 23 / 25 / 1 | 0.885 |
| val2 | observed | mild_lead | periodic:1 | 49 | -1.960 | [-3.489, -0.577] | [-4.492, -0.017] | 22 / 27 / 0 | 0.568 |
| val2 | observed | mild_lead | base_stock | 49 | -1.960 | [-3.507, -0.579] | [-4.501, -0.026] | 22 / 27 / 0 | 0.568 |
| val2 | observed | mild_lead | order_up_to | 49 | -14.021 | [-18.802, -9.538] | [-21.747, -7.733] | 44 / 5 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 49 | +0.156 | [+0.090, +0.228] | [+0.055, +0.270] | 13 / 26 / 10 | 0.053 |
| val2 | observed | stable | periodic:1 | 49 | +0.162 | [+0.067, +0.257] | [+0.025, +0.306] | 19 / 28 / 2 | 0.243 |
| val2 | observed | stable | base_stock | 49 | +0.162 | [+0.067, +0.255] | [+0.018, +0.306] | 19 / 28 / 2 | 0.243 |
| val2 | observed | stable | order_up_to | 49 | -8.179 | [-10.701, -5.643] | [-12.190, -4.568] | 44 / 5 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 49 | +3.747 | [+1.792, +5.852] | [+0.799, +7.065] | 15 / 33 / 1 | 0.013 |
| val2 | observed | uncertain | periodic:1 | 49 | +3.600 | [+1.631, +5.653] | [+0.642, +6.955] | 17 / 32 / 0 | 0.044 |
| val2 | observed | uncertain | base_stock | 49 | +3.815 | [+1.754, +5.943] | [+0.697, +7.019] | 18 / 31 / 0 | 0.085 |
| val2 | observed | uncertain | order_up_to | 49 | -3.782 | [-6.467, -0.919] | [-7.815, +0.649] | 31 / 18 / 0 | 0.085 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 49 | -10.2617 | [-19.1872, -3.5683] | 23 / 6 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 49 | +7.6964 | [+4.0210, +12.3471] | 6 / 38 |
| final | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0150 | [+0.0050, +0.0263] | 23 / 6 |
| final | observed | fill_only | periodic:1 | shortage | 49 | -10.0199 | [-19.1135, -3.0467] | 23 / 6 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +7.5867 | [+3.8851, +12.0408] | 10 / 37 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0139 | [+0.0041, +0.0247] | 23 / 6 |
| final | observed | fill_only | base_stock | shortage | 49 | -7.1953 | [-14.7792, -1.2524] | 19 / 14 |
| final | observed | fill_only | base_stock | avg_inventory_units | 49 | +6.1509 | [+2.6519, +10.7003] | 17 / 30 |
| final | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0086 | [-0.0009, +0.0191] | 19 / 14 |
| final | observed | fill_only | order_up_to | shortage | 49 | -54.7379 | [-76.7052, -36.6290] | 46 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 49 | +16.4137 | [+10.4614, +24.4797] | 0 / 47 |
| final | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1327 | [+0.1110, +0.1548] | 46 / 0 |
| final | observed | lead_only | reorder_point | shortage | 49 | -13.6349 | [-20.2570, -7.7226] | 25 / 5 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 49 | +3.2906 | [+1.9448, +4.9385] | 3 / 42 |
| final | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0305 | [+0.0188, +0.0437] | 25 / 5 |
| final | observed | lead_only | periodic:1 | shortage | 49 | -12.9628 | [-19.5510, -7.0192] | 25 / 8 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +3.2149 | [+1.8688, +4.7776] | 6 / 42 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0274 | [+0.0159, +0.0404] | 25 / 8 |
| final | observed | lead_only | base_stock | shortage | 49 | -12.9628 | [-19.4026, -7.2008] | 25 / 8 |
| final | observed | lead_only | base_stock | avg_inventory_units | 49 | +3.2091 | [+1.8698, +4.8212] | 6 / 42 |
| final | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0274 | [+0.0158, +0.0403] | 25 / 8 |
| final | observed | lead_only | order_up_to | shortage | 49 | -68.9119 | [-90.4087, -50.3965] | 46 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 49 | +10.8912 | [+6.7549, +16.2508] | 0 / 48 |
| final | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1747 | [+0.1494, +0.1996] | 46 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 49 | -13.7731 | [-24.9089, -5.4991] | 23 / 2 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +3.1781 | [+1.5286, +5.3235] | 5 / 40 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0181 | [+0.0102, +0.0267] | 23 / 2 |
| final | observed | mild_lead | periodic:1 | shortage | 49 | -12.6116 | [-23.9732, -4.0466] | 23 / 8 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +3.1561 | [+1.5728, +5.1471] | 4 / 42 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0150 | [+0.0066, +0.0239] | 23 / 8 |
| final | observed | mild_lead | base_stock | shortage | 49 | -12.6116 | [-24.0426, -4.0752] | 23 / 8 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 49 | +3.1511 | [+1.5633, +5.1486] | 5 / 41 |
| final | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0150 | [+0.0066, +0.0242] | 23 / 8 |
| final | observed | mild_lead | order_up_to | shortage | 49 | -76.1915 | [-110.6244, -49.3132] | 46 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +10.9103 | [+6.3739, +17.1044] | 0 / 47 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1660 | [+0.1441, +0.1872] | 46 / 0 |
| final | observed | stable | reorder_point | shortage | 49 | -2.0846 | [-5.0896, +0.0331] | 8 / 4 |
| final | observed | stable | reorder_point | avg_inventory_units | 49 | -0.1784 | [-1.1151, +0.5921] | 19 / 19 |
| final | observed | stable | reorder_point | service_unit_fill | 49 | +0.0034 | [-0.0011, +0.0089] | 8 / 4 |
| final | observed | stable | periodic:1 | shortage | 49 | -1.8083 | [-4.7423, +0.2953] | 8 / 10 |
| final | observed | stable | periodic:1 | avg_inventory_units | 49 | -0.2128 | [-1.0821, +0.5200] | 22 / 20 |
| final | observed | stable | periodic:1 | service_unit_fill | 49 | +0.0016 | [-0.0029, +0.0073] | 8 / 10 |
| final | observed | stable | base_stock | shortage | 49 | -1.8083 | [-4.8165, +0.3109] | 8 / 10 |
| final | observed | stable | base_stock | avg_inventory_units | 49 | -0.2187 | [-1.1271, +0.4754] | 23 / 19 |
| final | observed | stable | base_stock | service_unit_fill | 49 | +0.0016 | [-0.0032, +0.0072] | 8 / 10 |
| final | observed | stable | order_up_to | shortage | 49 | -49.3295 | [-68.5651, -33.9664] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 49 | +10.1245 | [+5.8052, +16.2448] | 0 / 47 |
| final | observed | stable | order_up_to | service_unit_fill | 49 | +0.1279 | [+0.1069, +0.1495] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 49 | -24.0873 | [-38.7997, -11.6903] | 30 / 5 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 49 | +6.4968 | [+3.5059, +10.4275] | 3 / 39 |
| final | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0363 | [+0.0231, +0.0500] | 30 / 5 |
| final | observed | uncertain | periodic:1 | shortage | 49 | -23.7769 | [-38.9150, -11.2837] | 30 / 7 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +6.4192 | [+3.3292, +10.4524] | 6 / 41 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0346 | [+0.0214, +0.0485] | 30 / 7 |
| final | observed | uncertain | base_stock | shortage | 49 | -19.4839 | [-33.3369, -8.3718] | 28 / 13 |
| final | observed | uncertain | base_stock | avg_inventory_units | 49 | +5.5902 | [+2.4552, +9.4424] | 11 / 36 |
| final | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0277 | [+0.0142, +0.0418] | 28 / 13 |
| final | observed | uncertain | order_up_to | shortage | 49 | -77.3861 | [-108.5612, -51.8460] | 46 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 49 | +12.4873 | [+7.7565, +18.1177] | 0 / 47 |
| final | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1731 | [+0.1511, +0.1954] | 46 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 43 | -5.5878 | [-11.9144, -0.6105] | 12 / 2 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 43 | +6.2757 | [+3.2002, +10.4031] | 4 / 35 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 43 | +0.0106 | [+0.0027, +0.0210] | 12 / 2 |
| val1 | observed | fill_only | periodic:1 | shortage | 43 | -5.0578 | [-11.6827, -0.1539] | 12 / 5 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 43 | +6.1286 | [+3.1336, +10.2833] | 8 / 35 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 43 | +0.0092 | [+0.0013, +0.0193] | 12 / 5 |
| val1 | observed | fill_only | base_stock | shortage | 43 | -3.7670 | [-10.4859, +1.2077] | 9 / 13 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 43 | +4.8275 | [+2.1884, +8.4705] | 16 / 27 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 43 | +0.0061 | [-0.0019, +0.0160] | 9 / 13 |
| val1 | observed | fill_only | order_up_to | shortage | 43 | -50.3726 | [-69.3465, -34.2861] | 41 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 43 | +17.4059 | [+9.8028, +29.4803] | 0 / 43 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 43 | +0.1308 | [+0.1100, +0.1525] | 41 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 43 | -9.8663 | [-17.1723, -4.3149] | 20 / 1 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 43 | +4.0841 | [+2.2270, +6.2194] | 4 / 34 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 43 | +0.0239 | [+0.0140, +0.0352] | 20 / 1 |
| val1 | observed | lead_only | periodic:1 | shortage | 43 | -8.8885 | [-16.5408, -3.1365] | 19 / 3 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 43 | +3.9652 | [+2.1451, +6.1984] | 3 / 36 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 43 | +0.0215 | [+0.0118, +0.0326] | 19 / 3 |
| val1 | observed | lead_only | base_stock | shortage | 43 | -8.7295 | [-16.3413, -3.0934] | 19 / 4 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 43 | +3.9704 | [+2.1554, +6.0498] | 3 / 36 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 43 | +0.0204 | [+0.0100, +0.0314] | 19 / 4 |
| val1 | observed | lead_only | order_up_to | shortage | 43 | -62.7973 | [-84.0439, -44.8897] | 42 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 43 | +13.8887 | [+7.5218, +24.1769] | 0 / 43 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 43 | +0.1658 | [+0.1421, +0.1884] | 42 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 43 | -5.0377 | [-8.2382, -2.3790] | 13 / 3 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 43 | +3.9393 | [+1.8848, +6.4842] | 4 / 34 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 43 | +0.0121 | [+0.0054, +0.0203] | 13 / 3 |
| val1 | observed | mild_lead | periodic:1 | shortage | 43 | -3.8550 | [-7.1033, -1.0742] | 11 / 7 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 43 | +3.8322 | [+1.9078, +6.4510] | 7 / 35 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 43 | +0.0103 | [+0.0033, +0.0183] | 11 / 7 |
| val1 | observed | mild_lead | base_stock | shortage | 43 | -3.6960 | [-6.8681, -0.8991] | 11 / 8 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 43 | +3.8322 | [+1.9052, +6.4876] | 7 / 35 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 43 | +0.0092 | [+0.0018, +0.0177] | 11 / 8 |
| val1 | observed | mild_lead | order_up_to | shortage | 43 | -54.2453 | [-72.0049, -38.3397] | 42 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 43 | +14.1935 | [+7.8570, +24.2959] | 0 / 43 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 43 | +0.1463 | [+0.1279, +0.1662] | 42 / 0 |
| val1 | observed | stable | reorder_point | shortage | 43 | +0.2297 | [-0.3247, +0.9149] | 3 / 4 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 43 | +0.8855 | [+0.1575, +1.9710] | 4 / 22 |
| val1 | observed | stable | reorder_point | service_unit_fill | 43 | +0.0000 | [-0.0021, +0.0021] | 3 / 4 |
| val1 | observed | stable | periodic:1 | shortage | 43 | +1.4721 | [-0.0274, +3.5132] | 3 / 6 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 43 | +0.7423 | [+0.0178, +1.7429] | 17 / 21 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 43 | -0.0020 | [-0.0047, +0.0003] | 3 / 6 |
| val1 | observed | stable | base_stock | shortage | 43 | +1.4813 | [-0.0073, +3.5330] | 3 / 7 |
| val1 | observed | stable | base_stock | avg_inventory_units | 43 | +0.7329 | [-0.0023, +1.7958] | 18 / 20 |
| val1 | observed | stable | base_stock | service_unit_fill | 43 | -0.0020 | [-0.0047, +0.0003] | 3 / 7 |
| val1 | observed | stable | order_up_to | shortage | 43 | -44.7905 | [-60.8065, -30.5847] | 41 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 43 | +13.2248 | [+6.9465, +23.4901] | 0 / 43 |
| val1 | observed | stable | order_up_to | service_unit_fill | 43 | +0.1218 | [+0.1023, +0.1426] | 41 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 43 | -12.0799 | [-23.5598, -3.3411] | 16 / 4 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 43 | +18.3929 | [+3.9685, +44.3952] | 5 / 32 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 43 | +0.0247 | [+0.0092, +0.0419] | 16 / 4 |
| val1 | observed | uncertain | periodic:1 | shortage | 43 | -10.3136 | [-21.5419, -1.1486] | 16 / 10 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 43 | +18.2394 | [+3.8382, +43.9472] | 8 / 33 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 43 | +0.0203 | [+0.0046, +0.0378] | 16 / 10 |
| val1 | observed | uncertain | base_stock | shortage | 43 | -8.3531 | [-19.4322, +0.4093] | 15 / 18 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 43 | +17.0693 | [+3.1241, +42.4188] | 15 / 28 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 43 | +0.0160 | [-0.0001, +0.0329] | 15 / 18 |
| val1 | observed | uncertain | order_up_to | shortage | 43 | -59.9817 | [-79.8667, -42.1998] | 41 / 1 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 43 | +27.1520 | [+8.7168, +60.2846] | 0 / 43 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 43 | +0.1594 | [+0.1356, +0.1843] | 41 / 1 |
| val2 | observed | fill_only | reorder_point | shortage | 49 | -4.3644 | [-8.2724, -1.0263] | 19 / 3 |
| val2 | observed | fill_only | reorder_point | avg_inventory_units | 49 | +10.4987 | [+5.8955, +16.4269] | 5 / 41 |
| val2 | observed | fill_only | reorder_point | service_unit_fill | 49 | +0.0096 | [+0.0035, +0.0162] | 19 / 3 |
| val2 | observed | fill_only | periodic:1 | shortage | 49 | -4.1863 | [-8.1588, -0.9704] | 19 / 5 |
| val2 | observed | fill_only | periodic:1 | avg_inventory_units | 49 | +10.3687 | [+5.8887, +16.3359] | 9 / 40 |
| val2 | observed | fill_only | periodic:1 | service_unit_fill | 49 | +0.0087 | [+0.0026, +0.0154] | 19 / 5 |
| val2 | observed | fill_only | base_stock | shortage | 49 | -2.6528 | [-5.9021, +0.1733] | 12 / 15 |
| val2 | observed | fill_only | base_stock | avg_inventory_units | 49 | +8.8835 | [+4.5861, +14.5514] | 16 / 33 |
| val2 | observed | fill_only | base_stock | service_unit_fill | 49 | +0.0054 | [-0.0002, +0.0115] | 12 / 15 |
| val2 | observed | fill_only | order_up_to | shortage | 49 | -45.9772 | [-64.3008, -31.5197] | 47 / 0 |
| val2 | observed | fill_only | order_up_to | avg_inventory_units | 49 | +21.4745 | [+13.0163, +32.1841] | 0 / 49 |
| val2 | observed | fill_only | order_up_to | service_unit_fill | 49 | +0.1340 | [+0.1142, +0.1537] | 47 / 0 |
| val2 | observed | lead_only | reorder_point | shortage | 49 | -12.3136 | [-19.7635, -6.1586] | 31 / 2 |
| val2 | observed | lead_only | reorder_point | avg_inventory_units | 49 | +3.0893 | [+1.9811, +4.4140] | 5 / 40 |
| val2 | observed | lead_only | reorder_point | service_unit_fill | 49 | +0.0269 | [+0.0172, +0.0356] | 31 / 2 |
| val2 | observed | lead_only | periodic:1 | shortage | 49 | -11.9055 | [-19.8458, -5.7803] | 30 / 4 |
| val2 | observed | lead_only | periodic:1 | avg_inventory_units | 49 | +2.8528 | [+1.7401, +4.0772] | 8 / 40 |
| val2 | observed | lead_only | periodic:1 | service_unit_fill | 49 | +0.0246 | [+0.0155, +0.0341] | 30 / 4 |
| val2 | observed | lead_only | base_stock | shortage | 49 | -11.9055 | [-20.0063, -5.8340] | 30 / 4 |
| val2 | observed | lead_only | base_stock | avg_inventory_units | 49 | +2.8528 | [+1.7004, +4.0806] | 8 / 40 |
| val2 | observed | lead_only | base_stock | service_unit_fill | 49 | +0.0246 | [+0.0153, +0.0339] | 30 / 4 |
| val2 | observed | lead_only | order_up_to | shortage | 49 | -68.9491 | [-95.3223, -46.8704] | 48 / 0 |
| val2 | observed | lead_only | order_up_to | avg_inventory_units | 49 | +12.5735 | [+7.8597, +19.0206] | 0 / 49 |
| val2 | observed | lead_only | order_up_to | service_unit_fill | 49 | +0.1863 | [+0.1672, +0.2052] | 48 / 0 |
| val2 | observed | mild_lead | reorder_point | shortage | 49 | -10.6694 | [-18.9784, -3.8900] | 24 / 1 |
| val2 | observed | mild_lead | reorder_point | avg_inventory_units | 49 | +2.5117 | [+0.9370, +4.3080] | 6 / 40 |
| val2 | observed | mild_lead | reorder_point | service_unit_fill | 49 | +0.0212 | [+0.0129, +0.0298] | 24 / 1 |
| val2 | observed | mild_lead | periodic:1 | shortage | 49 | -10.3194 | [-18.8367, -3.7532] | 23 / 5 |
| val2 | observed | mild_lead | periodic:1 | avg_inventory_units | 49 | +2.2393 | [+0.6841, +3.9442] | 11 / 38 |
| val2 | observed | mild_lead | periodic:1 | service_unit_fill | 49 | +0.0192 | [+0.0109, +0.0282] | 23 / 5 |
| val2 | observed | mild_lead | base_stock | shortage | 49 | -10.3194 | [-19.4527, -3.6262] | 23 / 5 |
| val2 | observed | mild_lead | base_stock | avg_inventory_units | 49 | +2.2393 | [+0.7285, +4.0389] | 11 / 38 |
| val2 | observed | mild_lead | base_stock | service_unit_fill | 49 | +0.0192 | [+0.0108, +0.0285] | 23 / 5 |
| val2 | observed | mild_lead | order_up_to | shortage | 49 | -62.6021 | [-91.4708, -41.7165] | 47 / 0 |
| val2 | observed | mild_lead | order_up_to | avg_inventory_units | 49 | +13.0495 | [+7.6144, +21.8498] | 0 / 49 |
| val2 | observed | mild_lead | order_up_to | service_unit_fill | 49 | +0.1663 | [+0.1461, +0.1859] | 47 / 0 |
| val2 | observed | stable | reorder_point | shortage | 49 | -0.1287 | [-0.5660, +0.2136] | 3 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 49 | +0.4231 | [+0.0325, +0.9236] | 10 / 25 |
| val2 | observed | stable | reorder_point | service_unit_fill | 49 | +0.0002 | [-0.0012, +0.0016] | 3 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 49 | +0.1163 | [-0.3798, +0.5370] | 3 / 7 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 49 | +0.1343 | [-0.3489, +0.6753] | 20 / 26 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 49 | -0.0012 | [-0.0032, +0.0006] | 3 / 7 |
| val2 | observed | stable | base_stock | shortage | 49 | +0.1163 | [-0.3827, +0.5577] | 3 / 7 |
| val2 | observed | stable | base_stock | avg_inventory_units | 49 | +0.1343 | [-0.3425, +0.7056] | 20 / 26 |
| val2 | observed | stable | base_stock | service_unit_fill | 49 | -0.0012 | [-0.0031, +0.0006] | 3 / 7 |
| val2 | observed | stable | order_up_to | shortage | 49 | -42.0743 | [-57.7254, -29.6694] | 47 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 49 | +12.7817 | [+7.6649, +19.9966] | 0 / 49 |
| val2 | observed | stable | order_up_to | service_unit_fill | 49 | +0.1263 | [+0.1078, +0.1450] | 47 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 49 | -10.4213 | [-15.4210, -6.0173] | 28 / 3 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 49 | +8.1271 | [+4.9180, +12.0689] | 4 / 43 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 49 | +0.0315 | [+0.0196, +0.0441] | 28 / 3 |
| val2 | observed | uncertain | periodic:1 | shortage | 49 | -10.3021 | [-15.1098, -5.7711] | 27 / 5 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 49 | +7.7326 | [+4.4362, +11.6528] | 7 / 42 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 49 | +0.0310 | [+0.0196, +0.0436] | 27 / 5 |
| val2 | observed | uncertain | base_stock | shortage | 49 | -7.5684 | [-12.2032, -3.1149] | 24 / 16 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 49 | +6.7131 | [+3.5760, +10.5628] | 9 / 40 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 49 | +0.0242 | [+0.0124, +0.0364] | 24 / 16 |
| val2 | observed | uncertain | order_up_to | shortage | 49 | -66.7322 | [-86.1112, -49.6293] | 48 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 49 | +16.1765 | [+10.6027, +23.1291] | 0 / 49 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 49 | +0.1874 | [+0.1682, +0.2074] | 48 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 725/750 complete, 0 infeasible, 0 abstained; gated: 725/750 complete, 0 infeasible, 0 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 725/750 complete, 0 infeasible, 0 abstained; reorder_point: 725/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 125
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/fill_only store TX_3 product HOBBIES_1_029: ZAAD minus reorder_point = +80.494 (fill 0.913 vs 0.913, inventory 69.24 vs 38.87, retained incumbent on None reviews)
- val2/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus reorder_point = +78.546 (fill 0.964 vs 0.938, inventory 68.34 vs 21.96, retained incumbent on None reviews)
- val2/observed/fill_only store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +67.675 (fill 0.950 vs 0.950, inventory 170.27 vs 71.79, retained incumbent on None reviews)
- val2/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +61.122 (fill 0.950 vs 0.950, inventory 182.65 vs 73.67, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product FOODS_1_137: ZAAD minus order_up_to = +58.632 (fill 0.716 vs 0.723, inventory 18.16 vs 8.45, retained incumbent on None reviews)
- val1/observed/uncertain store TX_3 product HOBBIES_1_029: ZAAD minus order_up_to = +55.845 (fill 0.913 vs 0.808, inventory 52.47 vs 15.50, retained incumbent on None reviews)
- val1/observed/uncertain store TX_1 product HOUSEHOLD_1_456: ZAAD minus order_up_to = +49.087 (fill 0.526 vs 0.429, inventory 24.44 vs 15.20, retained incumbent on None reviews)
- val1/observed/uncertain store CA_4 product HOUSEHOLD_1_433: ZAAD minus base_stock = +39.591 (fill 0.682 vs 0.686, inventory 11.57 vs 7.90, retained incumbent on None reviews)
- val2/observed/fill_only store CA_1 product HOUSEHOLD_1_324: ZAAD minus order_up_to = +34.896 (fill 1.000 vs 0.918, inventory 18.27 vs 3.33, retained incumbent on None reviews)
- val1/observed/uncertain store TX_2 product FOODS_1_046: ZAAD minus order_up_to = +34.804 (fill 1.000 vs 0.972, inventory 136.14 vs 40.72, retained incumbent on None reviews)
