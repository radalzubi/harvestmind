# Walmart M5 (Experiment A) results: stage `fifty_cash_4w`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `f5f3c29f857d`, selection `8b6067be83a4`; 3750 runs, 1566 complete, 2184 not complete; wall 818 s, peak RSS 268 MB. Every figure is a modelled dollar-of-shelf-price index under declared SYNTHETIC supply and economics (the classes volume / volatility / intermittency / category stand in the strata columns); none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | base_stock | 48/50 | 468.482 | 469.176 | 31.339 | 0.3553 | 390.723 | 0.280 | 137.410 | 5.271 | 10.1 | 4.3 |  | 0.21 |
| final | observed | fill_only | gated | 4/50 | 133.576 | 134.295 | 38.407 | 1.6737 | 58.244 | 0.820 | 34.334 | 16.110 | 3.0 | 1.5 | 0.10 | 1.38 |
| final | observed | fill_only | order_up_to | 49/50 | 464.846 | 465.652 | 29.667 | 0.3319 | 389.977 | 0.268 | 138.983 | 4.647 | 10.2 | 4.4 |  | 0.20 |
| final | observed | fill_only | periodic:1 | 2/50 | 38.174 | 39.778 | 1.218 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.5 |  | 0.02 |
| final | observed | fill_only | reorder_point | 3/50 | 29.523 | 30.481 | 2.089 | 1.8675 | 3.220 | 0.899 | 1.469 | 17.941 | 1.7 | 0.7 |  | 0.03 |
| final | observed | lead_only | base_stock | 49/50 | 457.252 | 458.265 | 37.248 | 0.3523 | 375.894 | 0.302 | 133.098 | 5.650 | 10.2 | 4.7 |  | 0.21 |
| final | observed | lead_only | gated | 2/50 | 37.918 | 39.409 | 0.473 | 2.7143 | 3.215 | 0.946 | 0.538 | 25.448 | 0.5 | 0.5 | 0.15 | 1.29 |
| final | observed | lead_only | order_up_to | 49/50 | 458.783 | 459.786 | 33.639 | 0.3231 | 381.075 | 0.285 | 136.336 | 4.348 | 10.3 | 4.6 |  | 0.21 |
| final | observed | lead_only | periodic:1 | 2/50 | 37.887 | 39.544 | 1.218 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.5 |  | 0.03 |
| final | observed | lead_only | reorder_point | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 |  | 0.03 |
| final | observed | mild_lead | base_stock | 49/50 | 456.811 | 457.751 | 37.875 | 0.3595 | 374.419 | 0.304 | 132.159 | 5.414 | 10.0 | 4.8 |  | 0.21 |
| final | observed | mild_lead | gated | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 | 0.15 | 1.03 |
| final | observed | mild_lead | order_up_to | 49/50 | 458.612 | 459.513 | 33.368 | 0.3415 | 380.533 | 0.288 | 135.184 | 4.757 | 10.1 | 4.8 |  | 0.21 |
| final | observed | mild_lead | periodic:1 | 2/50 | 37.897 | 39.544 | 1.218 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.5 |  | 0.03 |
| final | observed | mild_lead | reorder_point | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 |  | 0.02 |
| final | observed | stable | base_stock | 49/50 | 456.531 | 457.541 | 38.898 | 0.3660 | 373.459 | 0.307 | 131.377 | 5.762 | 10.0 | 4.8 |  | 0.22 |
| final | observed | stable | gated | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 | 0.19 | 0.89 |
| final | observed | stable | order_up_to | 49/50 | 458.133 | 459.227 | 35.522 | 0.3386 | 378.905 | 0.293 | 135.146 | 4.739 | 10.0 | 5.0 |  | 0.21 |
| final | observed | stable | periodic:1 | 2/50 | 37.887 | 39.544 | 1.218 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.5 |  | 0.03 |
| final | observed | stable | reorder_point | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 |  | 0.02 |
| final | observed | uncertain | base_stock | 49/50 | 463.145 | 463.927 | 32.201 | 0.3541 | 385.616 | 0.279 | 135.713 | 5.026 | 10.0 | 4.4 |  | 0.22 |
| final | observed | uncertain | gated | 3/50 | 174.390 | 175.349 | 49.121 | 2.1362 | 77.181 | 0.824 | 45.025 | 20.080 | 3.0 | 1.3 | 0.18 | 1.18 |
| final | observed | uncertain | order_up_to | 49/50 | 464.927 | 465.918 | 29.708 | 0.3323 | 391.003 | 0.265 | 139.863 | 4.419 | 10.3 | 4.5 |  | 0.21 |
| final | observed | uncertain | periodic:1 | 2/50 | 38.204 | 39.790 | 1.218 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.5 |  | 0.03 |
| final | observed | uncertain | reorder_point | 2/50 | 37.862 | 39.300 | 0.000 | 2.7015 | 3.215 | 0.946 | 0.538 | 25.234 | 0.5 | 0.0 |  | 0.04 |
| val1 | observed | fill_only | base_stock | 43/50 | 352.712 | 353.803 | 42.244 | 0.7137 | 270.901 | 0.289 | 126.115 | 4.250 | 10.1 | 5.0 |  | 0.21 |
| val1 | observed | fill_only | gated | 2/50 | 467.357 | 498.726 | 327.458 | 11.5093 | 70.324 | 0.933 | 14.150 | 68.431 | 1.0 | 3.0 | 0.27 | 2.08 |
| val1 | observed | fill_only | order_up_to | 43/50 | 354.019 | 355.380 | 37.067 | 0.6613 | 278.810 | 0.273 | 128.332 | 3.915 | 10.3 | 4.5 |  | 0.21 |
| val1 | observed | fill_only | periodic:1 | 2/50 | 468.840 | 499.504 | 322.855 | 11.1275 | 71.181 | 0.932 | 14.322 | 62.605 | 1.0 | 5.0 |  | 0.03 |
| val1 | observed | fill_only | reorder_point | 2/50 | 471.600 | 501.885 | 320.409 | 11.0447 | 73.982 | 0.929 | 14.886 | 61.792 | 1.0 | 3.5 |  | 0.03 |
| val1 | observed | lead_only | base_stock | 43/50 | 347.039 | 348.381 | 42.006 | 0.7155 | 266.804 | 0.294 | 122.926 | 4.224 | 10.0 | 5.2 |  | 0.21 |
| val1 | observed | lead_only | gated | 3/50 | 466.756 | 488.960 | 233.659 | 8.4326 | 178.903 | 0.737 | 31.500 | 49.174 | 3.0 | 3.3 | 0.26 | 1.80 |
| val1 | observed | lead_only | order_up_to | 43/50 | 347.658 | 349.129 | 41.072 | 0.6734 | 269.038 | 0.291 | 123.283 | 3.983 | 10.1 | 5.3 |  | 0.20 |
| val1 | observed | lead_only | periodic:1 | 2/50 | 425.311 | 457.828 | 287.995 | 10.7535 | 73.881 | 0.929 | 14.865 | 61.263 | 0.5 | 4.5 |  | 0.04 |
| val1 | observed | lead_only | reorder_point | 3/50 | 466.023 | 487.622 | 223.736 | 7.5492 | 182.661 | 0.734 | 32.256 | 41.676 | 3.0 | 2.3 |  | 0.02 |
| val1 | observed | mild_lead | base_stock | 43/50 | 346.959 | 348.515 | 43.502 | 0.7327 | 266.380 | 0.297 | 123.822 | 4.361 | 10.2 | 5.3 |  | 0.21 |
| val1 | observed | mild_lead | gated | 3/50 | 466.927 | 488.943 | 228.654 | 8.1307 | 181.951 | 0.734 | 32.114 | 47.555 | 3.3 | 2.3 | 0.18 | 1.67 |
| val1 | observed | mild_lead | order_up_to | 43/50 | 347.972 | 349.502 | 40.637 | 0.6747 | 270.084 | 0.288 | 124.851 | 3.977 | 10.2 | 5.3 |  | 0.21 |
| val1 | observed | mild_lead | periodic:1 | 2/50 | 422.443 | 454.960 | 295.400 | 10.9599 | 63.302 | 0.939 | 12.737 | 61.963 | 0.5 | 4.5 |  | 0.02 |
| val1 | observed | mild_lead | reorder_point | 3/50 | 466.066 | 487.665 | 224.232 | 7.7455 | 181.951 | 0.734 | 32.114 | 42.321 | 3.3 | 2.0 |  | 0.02 |
| val1 | observed | stable | base_stock | 43/50 | 346.064 | 347.680 | 45.937 | 0.7504 | 263.324 | 0.306 | 122.521 | 4.426 | 10.0 | 5.3 |  | 0.21 |
| val1 | observed | stable | gated | 3/50 | 467.127 | 487.026 | 211.916 | 7.9214 | 185.692 | 0.731 | 32.866 | 44.267 | 3.7 | 2.3 | 0.21 | 1.86 |
| val1 | observed | stable | order_up_to | 43/50 | 347.009 | 348.324 | 41.688 | 0.6676 | 266.935 | 0.296 | 123.458 | 3.934 | 10.1 | 5.5 |  | 0.21 |
| val1 | observed | stable | periodic:1 | 2/50 | 422.765 | 455.283 | 295.400 | 11.2824 | 63.302 | 0.939 | 12.737 | 63.197 | 0.5 | 4.5 |  | 0.03 |
| val1 | observed | stable | reorder_point | 3/50 | 466.272 | 487.871 | 224.232 | 7.9518 | 181.951 | 0.734 | 32.114 | 42.999 | 3.3 | 2.0 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 43/50 | 354.788 | 356.445 | 40.972 | 0.6837 | 277.366 | 0.279 | 127.910 | 4.135 | 10.2 | 5.0 |  | 0.22 |
| val1 | observed | uncertain | gated | 2/50 | 486.209 | 518.150 | 282.878 | 11.2944 | 146.265 | 0.860 | 29.430 | 76.014 | 1.5 | 3.0 | 0.19 | 1.70 |
| val1 | observed | uncertain | order_up_to | 43/50 | 355.788 | 357.309 | 35.303 | 0.6506 | 283.255 | 0.265 | 129.146 | 3.891 | 10.4 | 4.8 |  | 0.21 |
| val1 | observed | uncertain | periodic:1 | 2/50 | 475.905 | 507.584 | 277.517 | 10.2580 | 130.615 | 0.875 | 26.281 | 59.611 | 1.5 | 4.5 |  | 0.03 |
| val1 | observed | uncertain | reorder_point | 2/50 | 479.595 | 510.365 | 259.852 | 10.2591 | 146.265 | 0.860 | 29.430 | 58.765 | 1.5 | 2.5 |  | 0.03 |
| val2 | observed | fill_only | base_stock | 49/50 | 368.332 | 368.643 | 27.472 | 0.2241 | 302.500 | 0.228 | 138.027 | 1.747 | 10.9 | 4.1 |  | 0.22 |
| val2 | observed | fill_only | gated | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | fill_only | order_up_to | 49/50 | 369.016 | 369.369 | 26.013 | 0.1950 | 304.899 | 0.216 | 142.325 | 1.538 | 11.1 | 4.0 |  | 0.22 |
| val2 | observed | fill_only | periodic:1 | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | fill_only | reorder_point | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | lead_only | base_stock | 49/50 | 362.490 | 363.035 | 32.573 | 0.2275 | 292.779 | 0.239 | 139.678 | 1.660 | 10.8 | 4.6 |  | 0.22 |
| val2 | observed | lead_only | gated | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | lead_only | order_up_to | 49/50 | 364.251 | 364.790 | 28.316 | 0.1914 | 298.805 | 0.226 | 139.282 | 1.545 | 11.0 | 4.4 |  | 0.22 |
| val2 | observed | lead_only | periodic:1 | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | lead_only | reorder_point | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | mild_lead | base_stock | 49/50 | 362.901 | 363.355 | 31.142 | 0.2289 | 294.157 | 0.238 | 138.347 | 1.735 | 10.9 | 4.5 |  | 0.22 |
| val2 | observed | mild_lead | gated | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | mild_lead | order_up_to | 49/50 | 364.204 | 364.689 | 28.165 | 0.1998 | 298.622 | 0.229 | 139.802 | 1.499 | 11.0 | 4.5 |  | 0.22 |
| val2 | observed | mild_lead | periodic:1 | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | mild_lead | reorder_point | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | stable | base_stock | 49/50 | 362.376 | 362.740 | 31.843 | 0.2269 | 292.442 | 0.244 | 137.198 | 1.713 | 10.9 | 4.5 |  | 0.22 |
| val2 | observed | stable | gated | 1/50 | 159.943 | 159.943 | 57.702 | 0.8461 | 72.434 | 0.631 | 31.769 | 6.059 | 7.0 | 4.0 | 0.00 | 1.68 |
| val2 | observed | stable | order_up_to | 49/50 | 363.585 | 363.928 | 28.814 | 0.1972 | 296.599 | 0.233 | 138.396 | 1.462 | 11.0 | 4.5 |  | 0.21 |
| val2 | observed | stable | periodic:1 | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | stable | reorder_point | 1/50 | 159.943 | 159.943 | 57.702 | 0.8461 | 72.434 | 0.631 | 31.769 | 6.059 | 7.0 | 4.0 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 49/50 | 368.217 | 368.859 | 28.293 | 0.2170 | 303.270 | 0.222 | 141.876 | 1.691 | 10.9 | 4.4 |  | 0.22 |
| val2 | observed | uncertain | gated | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | uncertain | order_up_to | 49/50 | 368.744 | 369.146 | 23.471 | 0.1990 | 307.401 | 0.210 | 144.142 | 1.585 | 11.0 | 3.8 |  | 0.22 |
| val2 | observed | uncertain | periodic:1 | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |
| val2 | observed | uncertain | reorder_point | 0/50 |  |  |  |  |  |  |  |  |  |  |  |  |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | 3 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 3 | None |
| final | observed | fill_only | periodic:1 | 2 | -0.311 | [-0.623, +0.000] | [-0.623, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | fill_only | base_stock | 4 | -8.948 | [-17.357, -0.540] | [-25.399, -0.346] | 3 / 0 / 1 | 0.25 |
| final | observed | fill_only | order_up_to | 4 | -8.992 | [-17.595, -0.389] | [-25.810, +0.000] | 2 / 0 / 2 | 0.5 |
| final | observed | lead_only | reorder_point | 2 | +0.056 | [+0.000, +0.112] | [+0.000, +0.112] | 0 / 1 / 1 | 1.0 |
| final | observed | lead_only | periodic:1 | 2 | +0.032 | [-0.048, +0.112] | [-0.048, +0.112] | 1 / 1 / 0 | 1.0 |
| final | observed | lead_only | base_stock | 2 | +0.032 | [-0.048, +0.112] | [-0.048, +0.112] | 1 / 1 / 0 | 1.0 |
| final | observed | lead_only | order_up_to | 2 | +0.056 | [+0.000, +0.112] | [+0.000, +0.112] | 0 / 1 / 1 | 1.0 |
| final | observed | mild_lead | reorder_point | 2 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 2 | None |
| final | observed | mild_lead | periodic:1 | 2 | -0.035 | [-0.070, +0.000] | [-0.070, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | mild_lead | base_stock | 2 | -0.035 | [-0.070, +0.000] | [-0.070, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | mild_lead | order_up_to | 2 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 2 | None |
| final | observed | stable | reorder_point | 2 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 2 | None |
| final | observed | stable | periodic:1 | 2 | -0.024 | [-0.048, +0.000] | [-0.048, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | stable | base_stock | 2 | -0.024 | [-0.048, +0.000] | [-0.048, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | stable | order_up_to | 2 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 2 | None |
| final | observed | uncertain | reorder_point | 2 | +0.000 | [+0.000, +0.000] | [+0.000, +0.000] | 0 / 0 / 2 | None |
| final | observed | uncertain | periodic:1 | 2 | -0.341 | [-0.682, +0.000] | [-0.682, +0.000] | 1 / 0 / 1 | 1.0 |
| final | observed | uncertain | base_stock | 3 | -11.375 | [-22.498, -0.253] | [-33.368, +0.000] | 2 / 0 / 1 | 0.5 |
| final | observed | uncertain | order_up_to | 3 | -12.909 | [-25.817, +0.000] | [-38.726, +0.000] | 1 / 0 / 2 | 1.0 |
| val1 | observed | fill_only | reorder_point | 2 | -4.243 | [-14.571, +6.085] | [-14.571, +6.085] | 1 / 1 / 0 | 1.0 |
| val1 | observed | fill_only | periodic:1 | 2 | -1.483 | [-8.386, +5.419] | [-8.386, +5.419] | 1 / 1 / 0 | 1.0 |
| val1 | observed | fill_only | base_stock | 2 | +17.807 | [+5.370, +30.243] | [+5.370, +30.243] | 0 / 2 / 0 | 0.5 |
| val1 | observed | fill_only | order_up_to | 2 | +9.453 | [+7.337, +11.569] | [+7.337, +11.569] | 0 / 2 / 0 | 0.5 |
| val1 | observed | lead_only | reorder_point | 3 | +0.733 | [-0.958, +2.424] | [-1.437, +3.635] | 1 / 1 / 1 | 1.0 |
| val1 | observed | lead_only | periodic:1 | 2 | +0.933 | [-1.526, +3.392] | [-1.526, +3.392] | 1 / 1 / 0 | 1.0 |
| val1 | observed | lead_only | base_stock | 3 | -9.124 | [-21.536, +3.287] | [-33.843, +3.392] | 1 / 2 / 0 | 1.0 |
| val1 | observed | lead_only | order_up_to | 3 | -18.505 | [-31.698, -5.311] | [-35.118, +4.463] | 2 / 1 / 0 | 1.0 |
| val1 | observed | mild_lead | reorder_point | 3 | +0.861 | [+0.089, +1.634] | [+0.000, +2.318] | 0 / 2 / 1 | 0.5 |
| val1 | observed | mild_lead | periodic:1 | 2 | +4.056 | [+2.070, +6.042] | [+2.070, +6.042] | 0 / 2 / 0 | 0.5 |
| val1 | observed | mild_lead | base_stock | 3 | -7.539 | [-21.891, +6.813] | [-33.871, +9.184] | 1 / 2 / 0 | 1.0 |
| val1 | observed | mild_lead | order_up_to | 3 | -21.777 | [-34.553, -9.002] | [-35.180, +3.145] | 2 / 1 / 0 | 1.0 |
| val1 | observed | stable | reorder_point | 3 | +0.855 | [+0.243, +1.466] | [+0.000, +1.835] | 0 / 2 / 1 | 0.5 |
| val1 | observed | stable | periodic:1 | 2 | +4.034 | [+0.456, +7.611] | [+0.456, +7.611] | 0 / 2 / 0 | 0.5 |
| val1 | observed | stable | base_stock | 3 | -7.554 | [-22.429, +7.321] | [-33.871, +10.753] | 1 / 2 / 0 | 1.0 |
| val1 | observed | stable | order_up_to | 3 | -21.574 | [-33.820, -9.329] | [-35.180, +1.557] | 2 / 1 / 0 | 1.0 |
| val1 | observed | uncertain | reorder_point | 2 | +6.614 | [+0.000, +13.227] | [+0.000, +13.227] | 0 / 1 / 1 | 1.0 |
| val1 | observed | uncertain | periodic:1 | 2 | +10.303 | [+7.636, +12.971] | [+7.636, +12.971] | 0 / 2 / 0 | 0.5 |
| val1 | observed | uncertain | base_stock | 2 | +17.027 | [+12.923, +21.131] | [+12.923, +21.131] | 0 / 2 / 0 | 0.5 |
| val1 | observed | uncertain | order_up_to | 2 | +8.646 | [+2.273, +15.018] | [+2.273, +15.018] | 0 / 2 / 0 | 0.5 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | fill_only | reorder_point | shortage | 3 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | reorder_point | avg_inventory_units | 3 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | reorder_point | service_unit_fill | 3 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | periodic:1 | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | periodic:1 | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | periodic:1 | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | fill_only | base_stock | shortage | 4 | -31.1319 | [-89.8598, +0.0000] | 2 / 0 |
| final | observed | fill_only | base_stock | avg_inventory_units | 4 | +1.8134 | [+0.0000, +3.8324] | 0 / 2 |
| final | observed | fill_only | base_stock | service_unit_fill | 4 | +0.1275 | [+0.0000, +0.2551] | 2 / 0 |
| final | observed | fill_only | order_up_to | shortage | 4 | -30.0384 | [-86.0486, +0.0000] | 2 / 0 |
| final | observed | fill_only | order_up_to | avg_inventory_units | 4 | +2.1978 | [+0.0000, +4.7135] | 0 / 2 |
| final | observed | fill_only | order_up_to | service_unit_fill | 4 | +0.1359 | [+0.0000, +0.2718] | 2 / 0 |
| final | observed | lead_only | reorder_point | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | reorder_point | avg_inventory_units | 2 | +0.2142 | [+0.0000, +0.4284] | 0 / 1 |
| final | observed | lead_only | reorder_point | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | periodic:1 | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | periodic:1 | avg_inventory_units | 2 | +0.2142 | [+0.0000, +0.4284] | 0 / 1 |
| final | observed | lead_only | periodic:1 | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | base_stock | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | base_stock | avg_inventory_units | 2 | +0.2142 | [+0.0000, +0.4284] | 0 / 1 |
| final | observed | lead_only | base_stock | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | order_up_to | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | lead_only | order_up_to | avg_inventory_units | 2 | +0.2142 | [+0.0000, +0.4284] | 0 / 1 |
| final | observed | lead_only | order_up_to | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | reorder_point | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | reorder_point | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | reorder_point | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | periodic:1 | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | periodic:1 | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | periodic:1 | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | base_stock | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | base_stock | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | base_stock | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | order_up_to | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | order_up_to | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | mild_lead | order_up_to | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | reorder_point | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | reorder_point | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | reorder_point | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | periodic:1 | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | periodic:1 | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | periodic:1 | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | base_stock | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | base_stock | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | base_stock | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | order_up_to | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | stable | order_up_to | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | reorder_point | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | reorder_point | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | periodic:1 | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| final | observed | uncertain | base_stock | shortage | 3 | -39.4643 | [-118.3929, +0.0000] | 1 / 0 |
| final | observed | uncertain | base_stock | avg_inventory_units | 3 | +1.4228 | [+0.0000, +4.2684] | 0 / 1 |
| final | observed | uncertain | base_stock | service_unit_fill | 3 | +0.0739 | [+0.0000, +0.2216] | 1 / 0 |
| final | observed | uncertain | order_up_to | shortage | 3 | -41.2223 | [-123.6669, +0.0000] | 1 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 3 | +1.8137 | [+0.0000, +5.4411] | 0 / 1 |
| final | observed | uncertain | order_up_to | service_unit_fill | 3 | +0.0772 | [+0.0000, +0.2315] | 1 / 0 |
| val1 | observed | fill_only | reorder_point | shortage | 2 | -3.6580 | [-7.3160, +0.0000] | 1 / 0 |
| val1 | observed | fill_only | reorder_point | avg_inventory_units | 2 | +6.6385 | [+0.5415, +12.7355] | 0 / 2 |
| val1 | observed | fill_only | reorder_point | service_unit_fill | 2 | +0.0035 | [+0.0000, +0.0070] | 1 / 0 |
| val1 | observed | fill_only | periodic:1 | shortage | 2 | -0.8566 | [-1.7132, +0.0000] | 1 / 0 |
| val1 | observed | fill_only | periodic:1 | avg_inventory_units | 2 | +5.8257 | [+0.2633, +11.3881] | 0 / 2 |
| val1 | observed | fill_only | periodic:1 | service_unit_fill | 2 | +0.0008 | [+0.0000, +0.0016] | 1 / 0 |
| val1 | observed | fill_only | base_stock | shortage | 2 | +0.5035 | [+0.0000, +1.0069] | 0 / 1 |
| val1 | observed | fill_only | base_stock | avg_inventory_units | 2 | +6.3475 | [+1.5641, +11.1308] | 0 / 2 |
| val1 | observed | fill_only | base_stock | service_unit_fill | 2 | -0.0005 | [-0.0010, +0.0000] | 0 / 1 |
| val1 | observed | fill_only | order_up_to | shortage | 2 | -68.1670 | [-136.3341, +0.0000] | 1 / 0 |
| val1 | observed | fill_only | order_up_to | avg_inventory_units | 2 | +11.1141 | [+4.8253, +17.4030] | 0 / 2 |
| val1 | observed | fill_only | order_up_to | service_unit_fill | 2 | +0.0653 | [+0.0000, +0.1306] | 1 / 0 |
| val1 | observed | lead_only | reorder_point | shortage | 3 | -3.7572 | [-11.2715, +0.0000] | 1 / 0 |
| val1 | observed | lead_only | reorder_point | avg_inventory_units | 3 | +7.4976 | [+0.0000, +17.1734] | 0 / 2 |
| val1 | observed | lead_only | reorder_point | service_unit_fill | 3 | +0.0036 | [+0.0000, +0.0108] | 1 / 0 |
| val1 | observed | lead_only | periodic:1 | shortage | 2 | -5.6357 | [-11.2715, +0.0000] | 1 / 0 |
| val1 | observed | lead_only | periodic:1 | avg_inventory_units | 2 | +10.7595 | [+5.0249, +16.4941] | 0 / 2 |
| val1 | observed | lead_only | periodic:1 | service_unit_fill | 2 | +0.0054 | [+0.0000, +0.0108] | 1 / 0 |
| val1 | observed | lead_only | base_stock | shortage | 3 | -42.5622 | [-116.4150, +0.0000] | 2 / 0 |
| val1 | observed | lead_only | base_stock | avg_inventory_units | 3 | +8.0162 | [+2.5296, +16.4941] | 0 / 3 |
| val1 | observed | lead_only | base_stock | service_unit_fill | 3 | +0.0673 | [+0.0000, +0.1912] | 2 / 0 |
| val1 | observed | lead_only | order_up_to | shortage | 3 | -75.6089 | [-140.4915, +0.0000] | 2 / 0 |
| val1 | observed | lead_only | order_up_to | avg_inventory_units | 3 | +10.7903 | [+2.5296, +22.2258] | 0 / 3 |
| val1 | observed | lead_only | order_up_to | service_unit_fill | 3 | +0.0921 | [+0.0000, +0.1418] | 2 / 0 |
| val1 | observed | mild_lead | reorder_point | shortage | 3 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| val1 | observed | mild_lead | reorder_point | avg_inventory_units | 3 | +5.2341 | [+0.0000, +14.8299] | 0 / 2 |
| val1 | observed | mild_lead | reorder_point | service_unit_fill | 3 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| val1 | observed | mild_lead | periodic:1 | shortage | 2 | +9.5155 | [+0.0000, +19.0311] | 0 / 1 |
| val1 | observed | mild_lead | periodic:1 | avg_inventory_units | 2 | +7.6309 | [+1.1668, +14.0950] | 0 / 2 |
| val1 | observed | mild_lead | periodic:1 | service_unit_fill | 2 | -0.0091 | [-0.0182, +0.0000] | 0 / 1 |
| val1 | observed | mild_lead | base_stock | shortage | 3 | -32.4613 | [-116.4150, +19.0311] | 1 / 1 |
| val1 | observed | mild_lead | base_stock | avg_inventory_units | 3 | +5.9048 | [+1.1668, +14.0950] | 0 / 3 |
| val1 | observed | mild_lead | base_stock | service_unit_fill | 3 | +0.0576 | [-0.0182, +0.1912] | 1 / 1 |
| val1 | observed | mild_lead | order_up_to | shortage | 3 | -84.0800 | [-131.3474, +0.0000] | 2 / 0 |
| val1 | observed | mild_lead | order_up_to | avg_inventory_units | 3 | +9.1714 | [+2.5296, +19.8823] | 0 / 3 |
| val1 | observed | mild_lead | order_up_to | service_unit_fill | 3 | +0.1081 | [+0.0000, +0.1985] | 2 / 0 |
| val1 | observed | stable | reorder_point | shortage | 3 | +3.7406 | [+0.0000, +11.2217] | 0 / 1 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 3 | +1.2682 | [-1.3071, +5.1117] | 1 / 1 |
| val1 | observed | stable | reorder_point | service_unit_fill | 3 | -0.0036 | [-0.0108, +0.0000] | 0 / 1 |
| val1 | observed | stable | periodic:1 | shortage | 2 | +15.1264 | [+0.0000, +30.2528] | 0 / 1 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 2 | +1.4650 | [-1.0125, +3.9425] | 1 / 1 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 2 | -0.0145 | [-0.0290, +0.0000] | 0 / 1 |
| val1 | observed | stable | base_stock | shortage | 3 | -28.7207 | [-116.4150, +30.2528] | 1 / 1 |
| val1 | observed | stable | base_stock | avg_inventory_units | 3 | +1.7942 | [-1.0125, +3.9425] | 1 / 2 |
| val1 | observed | stable | base_stock | service_unit_fill | 3 | +0.0541 | [-0.0290, +0.1912] | 1 / 1 |
| val1 | observed | stable | order_up_to | shortage | 3 | -80.3394 | [-120.8925, +0.0000] | 2 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 3 | +5.8832 | [+2.5296, +10.1641] | 0 / 3 |
| val1 | observed | stable | order_up_to | service_unit_fill | 3 | +0.1045 | [+0.0000, +0.1985] | 2 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 2 | +17.2493 | [+0.0000, +34.4986] | 0 / 1 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 2 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 |
| val1 | observed | uncertain | periodic:1 | shortage | 2 | +15.6496 | [+0.0000, +31.2992] | 0 / 1 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 2 | +16.4032 | [+0.4243, +32.3820] | 0 / 2 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 2 | -0.0150 | [-0.0300, +0.0000] | 0 / 1 |
| val1 | observed | uncertain | base_stock | shortage | 2 | +16.6031 | [+0.0000, +33.2062] | 0 / 1 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 2 | +16.1201 | [+0.1444, +32.0957] | 0 / 2 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 2 | -0.0159 | [-0.0318, +0.0000] | 0 / 1 |
| val1 | observed | uncertain | order_up_to | shortage | 2 | -56.8361 | [-113.6722, +0.0000] | 1 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 2 | +19.3842 | [+0.7146, +38.0538] | 0 / 2 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 2 | +0.0545 | [+0.0000, +0.1089] | 1 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 724/750 complete, 0 infeasible, 0 abstained; gated: 42/750 complete, 0 infeasible, 681 abstained; order_up_to: 725/750 complete, 0 infeasible, 0 abstained; periodic:1: 35/750 complete, 0 infeasible, 0 abstained; reorder_point: 40/750 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 2184
- ZAAD runs that retained the incumbent proxy on at least one review: 0 of 750 (0 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/fill_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +30.243 (fill 0.865 vs 0.866, inventory 60.57 vs 59.01, retained incumbent on None reviews)
- val1/observed/uncertain store CA_3 product FOODS_2_318: ZAAD minus base_stock = +21.131 (fill 0.720 vs 0.752, inventory 55.09 vs 54.95, retained incumbent on None reviews)
- val1/observed/uncertain store CA_4 product FOODS_1_218: ZAAD minus order_up_to = +15.018 (fill 1.000 vs 1.000, inventory 96.94 vs 58.88, retained incumbent on None reviews)
- val1/observed/stable store CA_3 product FOODS_2_318: ZAAD minus base_stock = +10.753 (fill 0.850 vs 0.879, inventory 60.28 vs 61.29, retained incumbent on None reviews)
- val1/observed/mild_lead store CA_3 product FOODS_2_318: ZAAD minus base_stock = +9.184 (fill 0.860 vs 0.879, inventory 60.42 vs 59.25, retained incumbent on None reviews)
- val1/observed/fill_only store CA_4 product FOODS_1_218: ZAAD minus order_up_to = +7.337 (fill 1.000 vs 1.000, inventory 76.29 vs 58.88, retained incumbent on None reviews)
- val1/observed/lead_only store CA_4 product FOODS_1_218: ZAAD minus order_up_to = +4.463 (fill 1.000 vs 1.000, inventory 81.11 vs 58.88, retained incumbent on None reviews)
- val1/observed/mild_lead store CA_4 product FOODS_1_218: ZAAD minus order_up_to = +3.145 (fill 1.000 vs 1.000, inventory 78.77 vs 58.88, retained incumbent on None reviews)
- val1/observed/lead_only store CA_3 product FOODS_2_318: ZAAD minus base_stock = +3.078 (fill 0.869 vs 0.858, inventory 62.93 vs 57.91, retained incumbent on None reviews)
- val1/observed/stable store CA_4 product FOODS_1_218: ZAAD minus order_up_to = +1.557 (fill 1.000 vs 1.000, inventory 69.05 vs 58.88, retained incumbent on None reviews)
