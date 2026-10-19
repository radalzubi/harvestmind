# FreshRetailNet pilot results: stage `five`

Commit `91b9b7d5dc9dd012bbe606dacd1b71920d5df386`, declaration `eea25bb1f36d`, selection `497bf5a8741a`; 360 runs, 312 complete, 48 not complete; wall 161 s, peak RSS 254 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | retained inc. | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 5/5 | 46.333 | 44.133 | 0.0230 | 1.131 | 0.952 | 0.754 | 6.660 | 0.8 | 6.8 | 0.0 | 0.07 |
| final | observed | stable | gated | 5/5 | 45.445 | 40.527 | 0.0356 | 0.746 | 0.967 | 0.498 | 10.313 | 0.6 | 5.4 | 4.4 | 0.58 |
| final | observed | stable | order_up_to | 5/5 | 46.136 | 37.748 | 0.0107 | 3.471 | 0.833 | 2.314 | 3.095 | 2.4 | 6.4 | 0.0 | 0.05 |
| final | observed | stable | reorder_point | 5/5 | 45.376 | 39.345 | 0.0230 | 1.131 | 0.952 | 0.754 | 6.660 | 0.8 | 5.8 | 0.0 | 0.01 |
| final | observed | uncertain | base_stock | 5/5 | 56.719 | 52.626 | 0.0244 | 9.303 | 0.774 | 6.202 | 7.077 | 2.4 | 6.8 | 0.0 | 0.05 |
| final | observed | uncertain | gated | 5/5 | 57.133 | 53.265 | 0.0508 | 9.016 | 0.779 | 6.011 | 14.714 | 2.2 | 4.2 | 3.8 | 0.29 |
| final | observed | uncertain | order_up_to | 5/5 | 55.027 | 44.118 | 0.0139 | 11.414 | 0.705 | 7.609 | 4.037 | 3.0 | 6.6 | 0.0 | 0.05 |
| final | observed | uncertain | reorder_point | 5/5 | 55.338 | 47.219 | 0.0222 | 9.389 | 0.778 | 6.259 | 6.444 | 2.6 | 5.8 | 0.0 | 0.01 |
| final | observed | uncertain_fill_only | base_stock | 4/5 | 65.279 | 62.882 | 0.0370 | 7.419 | 0.890 | 4.946 | 10.717 | 2.2 | 7.0 | 0.0 | 0.06 |
| final | observed | uncertain_fill_only | gated | 4/5 | 61.673 | 59.189 | 0.0606 | 7.383 | 0.890 | 4.922 | 17.563 | 1.8 | 5.2 | 3.5 | 0.43 |
| final | observed | uncertain_fill_only | order_up_to | 5/5 | 52.939 | 43.964 | 0.0187 | 8.535 | 0.791 | 5.690 | 5.421 | 2.8 | 6.8 | 0.0 | 0.05 |
| final | observed | uncertain_fill_only | reorder_point | 5/5 | 51.477 | 46.135 | 0.0289 | 6.173 | 0.905 | 4.115 | 8.359 | 2.0 | 5.8 | 0.0 | 0.01 |
| final | recovered | stable | base_stock | 5/5 | 51.152 | 49.517 | 0.0327 | 0.357 | 0.984 | 0.238 | 9.478 | 0.6 | 6.8 | 0.0 | 0.07 |
| final | recovered | stable | gated | 5/5 | 49.943 | 44.166 | 0.0344 | 0.056 | 0.996 | 0.038 | 9.960 | 0.2 | 5.6 | 5.2 | 0.28 |
| final | recovered | stable | order_up_to | 5/5 | 51.089 | 40.233 | 0.0145 | 4.240 | 0.841 | 2.827 | 4.187 | 1.8 | 6.6 | 0.0 | 0.06 |
| final | recovered | stable | reorder_point | 5/5 | 50.070 | 44.107 | 0.0327 | 0.357 | 0.984 | 0.238 | 9.478 | 0.6 | 6.0 | 0.0 | 0.01 |
| final | recovered | uncertain | base_stock | 5/5 | 62.354 | 62.769 | 0.0305 | 5.611 | 0.839 | 3.741 | 8.845 | 1.6 | 6.8 | 0.0 | 0.06 |
| final | recovered | uncertain | gated | 5/5 | 62.584 | 62.528 | 0.0570 | 5.524 | 0.843 | 3.683 | 16.511 | 1.8 | 4.4 | 3.8 | 0.31 |
| final | recovered | uncertain | order_up_to | 5/5 | 59.938 | 50.498 | 0.0144 | 8.775 | 0.757 | 5.850 | 4.175 | 2.4 | 6.6 | 0.0 | 0.05 |
| final | recovered | uncertain | reorder_point | 5/5 | 60.456 | 55.863 | 0.0279 | 5.562 | 0.846 | 3.708 | 8.068 | 1.6 | 5.6 | 0.0 | 0.01 |
| final | recovered | uncertain_fill_only | base_stock | 4/5 | 71.012 | 74.304 | 0.0481 | 2.890 | 0.969 | 1.927 | 13.941 | 1.0 | 7.0 | 0.0 | 0.07 |
| final | recovered | uncertain_fill_only | gated | 5/5 | 54.941 | 56.712 | 0.0596 | 2.362 | 0.972 | 1.575 | 17.263 | 0.6 | 3.8 | 2.4 | 0.39 |
| final | recovered | uncertain_fill_only | order_up_to | 5/5 | 57.363 | 50.100 | 0.0210 | 5.729 | 0.851 | 3.819 | 6.072 | 2.8 | 6.6 | 0.0 | 0.05 |
| final | recovered | uncertain_fill_only | reorder_point | 5/5 | 55.540 | 54.008 | 0.0373 | 2.342 | 0.973 | 1.561 | 10.817 | 0.8 | 5.6 | 0.0 | 0.01 |
| val1 | observed | stable | base_stock | 4/5 | 95.944 | 95.451 | 0.0362 | 0.412 | 0.991 | 0.275 | 5.240 | 0.5 | 14.0 | 0.0 | 0.31 |
| val1 | observed | stable | gated | 5/5 | 79.311 | 78.740 | 0.0362 | 0.314 | 0.993 | 0.209 | 5.241 | 0.6 | 13.0 | 12.4 | 2.44 |
| val1 | observed | stable | order_up_to | 5/5 | 82.063 | 67.839 | 0.0083 | 10.943 | 0.890 | 7.296 | 1.198 | 4.8 | 12.6 | 0.0 | 0.11 |
| val1 | observed | stable | reorder_point | 5/5 | 79.302 | 78.688 | 0.0310 | 0.330 | 0.993 | 0.220 | 4.496 | 0.4 | 12.4 | 0.0 | 0.02 |
| val1 | observed | uncertain | base_stock | 3/5 | 147.547 | 129.641 | 0.0579 | 24.085 | 0.857 | 16.057 | 8.381 | 3.7 | 13.3 | 0.0 | 0.30 |
| val1 | observed | uncertain | gated | 3/5 | 157.399 | 161.455 | 0.7093 | 11.793 | 0.959 | 7.862 | 26.520 | 0.7 | 10.3 | 4.7 | 1.62 |
| val1 | observed | uncertain | order_up_to | 4/5 | 119.336 | 86.348 | 0.0205 | 37.019 | 0.770 | 24.679 | 2.969 | 5.0 | 13.2 | 0.0 | 0.12 |
| val1 | observed | uncertain | reorder_point | 5/5 | 94.309 | 81.878 | 0.0373 | 15.932 | 0.896 | 10.621 | 5.400 | 2.8 | 12.4 | 0.0 | 0.02 |
| val1 | observed | uncertain_fill_only | base_stock | 3/5 | 140.946 | 138.653 | 0.0603 | 11.327 | 0.969 | 7.551 | 8.730 | 1.0 | 13.3 | 0.0 | 0.28 |
| val1 | observed | uncertain_fill_only | gated | 3/5 | 148.080 | 163.552 | 0.1535 | 11.114 | 0.974 | 7.409 | 22.239 | 0.7 | 8.7 | 4.7 | 2.09 |
| val1 | observed | uncertain_fill_only | order_up_to | 5/5 | 91.149 | 77.185 | 0.0156 | 15.857 | 0.878 | 10.572 | 2.258 | 3.8 | 13.0 | 0.0 | 0.12 |
| val1 | observed | uncertain_fill_only | reorder_point | 5/5 | 90.111 | 87.991 | 0.0377 | 7.093 | 0.969 | 4.728 | 5.456 | 1.0 | 12.6 | 0.0 | 0.02 |
| val1 | recovered | stable | base_stock | 4/5 | 120.623 | 114.191 | 0.0434 | 1.292 | 0.991 | 0.862 | 6.281 | 0.8 | 13.5 | 0.0 | 0.27 |
| val1 | recovered | stable | gated | 4/5 | 120.266 | 114.519 | 0.0561 | 0.359 | 0.994 | 0.239 | 8.120 | 0.2 | 13.5 | 11.2 | 3.52 |
| val1 | recovered | stable | order_up_to | 5/5 | 103.542 | 82.160 | 0.0115 | 15.245 | 0.872 | 10.163 | 1.664 | 3.8 | 12.2 | 0.0 | 0.11 |
| val1 | recovered | stable | reorder_point | 5/5 | 99.280 | 93.877 | 0.0372 | 1.034 | 0.993 | 0.689 | 5.389 | 0.6 | 12.4 | 0.0 | 0.02 |
| val1 | recovered | uncertain | base_stock | 3/5 | 187.050 | 164.418 | 0.0661 | 27.012 | 0.885 | 18.008 | 9.575 | 3.3 | 14.0 | 0.0 | 0.27 |
| val1 | recovered | uncertain | gated | 3/5 | 183.936 | 198.857 | 0.3669 | 5.370 | 0.978 | 3.580 | 32.785 | 0.7 | 8.7 | 6.0 | 1.57 |
| val1 | recovered | uncertain | order_up_to | 5/5 | 123.016 | 89.528 | 0.0195 | 34.848 | 0.775 | 23.232 | 2.820 | 5.4 | 12.6 | 0.0 | 0.13 |
| val1 | recovered | uncertain | reorder_point | 5/5 | 118.114 | 102.091 | 0.0426 | 17.880 | 0.924 | 11.920 | 6.177 | 2.0 | 12.6 | 0.0 | 0.02 |
| val1 | recovered | uncertain_fill_only | base_stock | 3/5 | 174.980 | 174.715 | 0.0674 | 4.618 | 0.992 | 3.078 | 9.765 | 0.3 | 14.0 | 0.0 | 0.26 |
| val1 | recovered | uncertain_fill_only | gated | 3/5 | 175.662 | 174.085 | 0.1613 | 5.430 | 0.977 | 3.620 | 23.367 | 0.7 | 9.0 | 5.0 | 2.17 |
| val1 | recovered | uncertain_fill_only | order_up_to | 5/5 | 112.981 | 97.426 | 0.0163 | 14.912 | 0.894 | 9.941 | 2.362 | 3.6 | 12.8 | 0.0 | 0.12 |
| val1 | recovered | uncertain_fill_only | reorder_point | 5/5 | 110.573 | 109.104 | 0.0418 | 2.778 | 0.995 | 1.852 | 6.052 | 0.4 | 12.6 | 0.0 | 0.02 |
| val2 | observed | stable | base_stock | 4/5 | 99.064 | 96.443 | 0.0326 | 1.450 | 0.978 | 0.967 | 4.725 | 1.0 | 13.0 | 0.0 | 0.28 |
| val2 | observed | stable | gated | 3/5 | 128.494 | 125.474 | 0.0492 | 1.406 | 0.979 | 0.937 | 7.127 | 1.0 | 14.0 | 11.0 | 4.75 |
| val2 | observed | stable | order_up_to | 5/5 | 86.060 | 64.849 | 0.0243 | 18.605 | 0.762 | 12.403 | 1.471 | 5.4 | 10.6 | 0.0 | 0.12 |
| val2 | observed | stable | reorder_point | 5/5 | 80.789 | 78.327 | 0.0432 | 1.482 | 0.940 | 0.988 | 4.165 | 1.0 | 11.0 | 0.0 | 0.03 |
| val2 | observed | uncertain | base_stock | 3/5 | 155.896 | 143.214 | 0.0347 | 23.044 | 0.871 | 15.362 | 5.020 | 3.0 | 13.3 | 0.0 | 0.27 |
| val2 | observed | uncertain | gated | 3/5 | 153.564 | 163.642 | 0.1119 | 5.077 | 0.972 | 3.384 | 16.201 | 1.3 | 10.7 | 5.7 | 1.60 |
| val2 | observed | uncertain | order_up_to | 5/5 | 101.826 | 71.949 | 0.0271 | 34.003 | 0.658 | 22.669 | 1.873 | 5.6 | 10.4 | 0.0 | 0.12 |
| val2 | observed | uncertain | reorder_point | 5/5 | 98.466 | 88.981 | 0.0384 | 16.109 | 0.842 | 10.740 | 3.511 | 2.8 | 11.2 | 0.0 | 0.03 |
| val2 | observed | uncertain_fill_only | base_stock | 3/5 | 157.046 | 156.378 | 0.0377 | 6.520 | 0.945 | 4.347 | 5.454 | 2.0 | 13.3 | 0.0 | 0.27 |
| val2 | observed | uncertain_fill_only | gated | 3/5 | 159.188 | 169.858 | 0.1177 | 2.129 | 0.995 | 1.420 | 17.054 | 0.3 | 10.3 | 4.3 | 1.76 |
| val2 | observed | uncertain_fill_only | order_up_to | 3/5 | 157.146 | 128.813 | 0.0136 | 29.234 | 0.857 | 19.489 | 1.969 | 6.3 | 13.7 | 0.0 | 0.13 |
| val2 | observed | uncertain_fill_only | reorder_point | 5/5 | 98.382 | 97.008 | 0.0400 | 5.226 | 0.884 | 3.484 | 3.748 | 1.4 | 11.2 | 0.0 | 0.03 |
| val2 | recovered | stable | base_stock | 4/5 | 138.203 | 120.786 | 0.0516 | 15.863 | 0.884 | 10.575 | 7.476 | 2.2 | 13.0 | 0.0 | 0.30 |
| val2 | recovered | stable | gated | 4/5 | 137.652 | 127.020 | 0.0684 | 11.976 | 0.910 | 7.984 | 9.906 | 1.8 | 12.5 | 8.2 | 6.18 |
| val2 | recovered | stable | order_up_to | 5/5 | 116.291 | 82.217 | 0.0330 | 28.147 | 0.693 | 18.765 | 2.327 | 5.2 | 10.6 | 0.0 | 0.11 |
| val2 | recovered | stable | reorder_point | 5/5 | 112.493 | 97.716 | 0.0609 | 13.306 | 0.844 | 8.871 | 6.375 | 2.2 | 10.2 | 0.0 | 0.03 |
| val2 | recovered | uncertain | base_stock | 2/5 | 275.492 | 235.296 | 0.0975 | 51.843 | 0.792 | 34.562 | 14.129 | 3.5 | 11.0 | 0.0 | 0.26 |
| val2 | recovered | uncertain | gated | 4/5 | 162.618 | 189.375 | 0.1683 | 8.071 | 0.904 | 5.381 | 21.310 | 1.8 | 9.2 | 7.5 | 1.42 |
| val2 | recovered | uncertain | order_up_to | 4/5 | 166.357 | 109.940 | 0.0305 | 57.144 | 0.716 | 38.096 | 4.420 | 5.5 | 11.0 | 0.0 | 0.12 |
| val2 | recovered | uncertain | reorder_point | 5/5 | 131.239 | 107.786 | 0.0612 | 26.894 | 0.754 | 17.930 | 6.414 | 3.6 | 10.2 | 0.0 | 0.03 |
| val2 | recovered | uncertain_fill_only | base_stock | 3/5 | 196.335 | 180.181 | 0.0684 | 24.550 | 0.846 | 16.367 | 9.910 | 2.7 | 12.0 | 0.0 | 0.26 |
| val2 | recovered | uncertain_fill_only | gated | 3/5 | 206.010 | 209.450 | 0.1205 | 24.057 | 0.868 | 16.038 | 17.454 | 2.3 | 11.3 | 6.3 | 2.51 |
| val2 | recovered | uncertain_fill_only | order_up_to | 4/5 | 163.482 | 126.211 | 0.0261 | 36.255 | 0.797 | 24.170 | 3.773 | 4.8 | 11.0 | 0.0 | 0.13 |
| val2 | recovered | uncertain_fill_only | reorder_point | 5/5 | 133.384 | 119.943 | 0.0612 | 17.374 | 0.804 | 11.583 | 6.414 | 2.4 | 10.6 | 0.0 | 0.03 |

## Paired comparison, ZAAD minus baseline per series (realized cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | order_up_to | 5 | -0.691 | [-1.620, +0.290] | [-1.957, +0.881] | 4 / 1 / 0 | 0.375 |
| final | observed | stable | base_stock | 5 | -0.888 | [-1.229, -0.547] | [-1.396, -0.350] | 5 / 0 / 0 | 0.062 |
| final | observed | stable | reorder_point | 5 | +0.070 | [-0.477, +0.616] | [-0.596, +0.985] | 3 / 2 / 0 | 1.0 |
| final | observed | uncertain | order_up_to | 5 | +2.105 | [+0.148, +4.067] | [-0.455, +4.986] | 1 / 4 / 0 | 0.375 |
| final | observed | uncertain | base_stock | 5 | +0.414 | [-0.709, +1.537] | [-1.110, +2.048] | 2 / 3 / 0 | 1.0 |
| final | observed | uncertain | reorder_point | 5 | +1.795 | [+0.377, +3.239] | [-0.337, +3.930] | 1 / 4 / 0 | 0.375 |
| final | observed | uncertain_fill_only | order_up_to | 4 | -2.682 | [-4.366, -0.998] | [-5.362, -0.002] | 3 / 1 / 0 | 0.625 |
| final | observed | uncertain_fill_only | base_stock | 4 | -3.605 | [-6.618, -0.593] | [-8.510, +0.432] | 2 / 2 / 0 | 1.0 |
| final | observed | uncertain_fill_only | reorder_point | 4 | -1.042 | [-2.383, +0.299] | [-3.042, +0.959] | 2 / 2 / 0 | 1.0 |
| final | recovered | stable | order_up_to | 5 | -1.146 | [-1.846, -0.425] | [-2.122, +0.084] | 4 / 1 / 0 | 0.375 |
| final | recovered | stable | base_stock | 5 | -1.209 | [-1.841, -0.595] | [-2.340, -0.356] | 5 / 0 / 0 | 0.062 |
| final | recovered | stable | reorder_point | 5 | -0.127 | [-0.304, +0.049] | [-0.403, +0.091] | 2 / 3 / 0 | 1.0 |
| final | recovered | uncertain | order_up_to | 5 | +2.646 | [+0.891, +4.437] | [+0.382, +5.842] | 1 / 4 / 0 | 0.375 |
| final | recovered | uncertain | base_stock | 5 | +0.230 | [-0.317, +0.776] | [-0.627, +1.013] | 2 / 3 / 0 | 1.0 |
| final | recovered | uncertain | reorder_point | 5 | +2.128 | [+0.976, +3.293] | [+0.625, +3.969] | 0 / 5 / 0 | 0.062 |
| final | recovered | uncertain_fill_only | order_up_to | 5 | -2.422 | [-3.883, -0.975] | [-5.077, -0.468] | 5 / 0 / 0 | 0.062 |
| final | recovered | uncertain_fill_only | base_stock | 4 | -3.900 | [-7.261, -0.540] | [-9.298, +0.436] | 3 / 1 / 0 | 0.625 |
| final | recovered | uncertain_fill_only | reorder_point | 5 | -0.599 | [-1.917, +0.719] | [-2.667, +1.303] | 3 / 2 / 0 | 1.0 |
| val1 | observed | stable | order_up_to | 5 | -2.752 | [-4.761, -0.800] | [-6.427, -0.476] | 4 / 1 / 0 | 0.375 |
| val1 | observed | stable | base_stock | 4 | +0.002 | [-0.018, +0.023] | [-0.029, +0.032] | 1 / 3 / 0 | 0.625 |
| val1 | observed | stable | reorder_point | 5 | +0.008 | [-0.008, +0.025] | [-0.017, +0.033] | 1 / 4 / 0 | 0.375 |
| val1 | observed | uncertain | order_up_to | 3 | +2.184 | [-0.845, +5.213] | [-1.061, +8.027] | 2 / 1 / 0 | 1.0 |
| val1 | observed | uncertain | base_stock | 3 | +9.851 | [+0.801, +18.902] | [-0.496, +26.657] | 1 / 2 / 0 | 1.0 |
| val1 | observed | uncertain | reorder_point | 3 | +9.238 | [+0.765, +17.712] | [-0.471, +24.951] | 1 / 2 / 0 | 1.0 |
| val1 | observed | uncertain_fill_only | order_up_to | 3 | +5.540 | [-0.394, +11.474] | [-0.950, +16.853] | 1 / 2 / 0 | 1.0 |
| val1 | observed | uncertain_fill_only | base_stock | 3 | +7.134 | [-0.432, +14.701] | [-0.689, +22.011] | 1 / 2 / 0 | 1.0 |
| val1 | observed | uncertain_fill_only | reorder_point | 3 | +7.052 | [-0.339, +14.443] | [-0.623, +21.551] | 1 / 2 / 0 | 1.0 |
| val1 | recovered | stable | order_up_to | 4 | -5.434 | [-9.676, -1.193] | [-13.468, -0.760] | 4 / 0 / 0 | 0.125 |
| val1 | recovered | stable | base_stock | 4 | -0.357 | [-0.810, +0.095] | [-1.210, +0.142] | 2 / 2 / 0 | 1.0 |
| val1 | recovered | stable | reorder_point | 4 | -0.357 | [-0.810, +0.095] | [-1.210, +0.142] | 2 / 2 / 0 | 1.0 |
| val1 | recovered | uncertain | order_up_to | 3 | -11.514 | [-21.499, -1.529] | [-31.398, -1.443] | 3 / 0 / 0 | 0.25 |
| val1 | recovered | uncertain | base_stock | 3 | -3.114 | [-7.609, +1.381] | [-11.426, +2.060] | 1 / 2 / 0 | 1.0 |
| val1 | recovered | uncertain | reorder_point | 3 | -3.660 | [-8.458, +1.137] | [-12.698, +1.694] | 1 / 2 / 0 | 1.0 |
| val1 | recovered | uncertain_fill_only | order_up_to | 3 | -2.453 | [-6.702, +1.797] | [-9.996, +2.752] | 2 / 1 / 0 | 1.0 |
| val1 | recovered | uncertain_fill_only | base_stock | 3 | +0.681 | [-0.152, +1.515] | [-0.153, +2.347] | 2 / 1 / 0 | 1.0 |
| val1 | recovered | uncertain_fill_only | reorder_point | 3 | +1.097 | [+0.334, +1.860] | [+0.223, +2.512] | 0 / 3 / 0 | 0.25 |
| val2 | observed | stable | order_up_to | 3 | -8.500 | [-14.843, -2.158] | [-21.129, -2.101] | 3 / 0 / 0 | 0.25 |
| val2 | observed | stable | base_stock | 3 | -0.030 | [-0.102, +0.042] | [-0.154, +0.061] | 1 / 2 / 0 | 1.0 |
| val2 | observed | stable | reorder_point | 3 | -0.030 | [-0.102, +0.042] | [-0.154, +0.061] | 1 / 2 / 0 | 1.0 |
| val2 | observed | uncertain | order_up_to | 3 | -8.623 | [-16.512, -0.734] | [-24.166, -0.498] | 3 / 0 / 0 | 0.25 |
| val2 | observed | uncertain | base_stock | 3 | -2.332 | [-5.509, +0.845] | [-7.545, +1.985] | 2 / 1 / 0 | 1.0 |
| val2 | observed | uncertain | reorder_point | 3 | -3.158 | [-7.500, +1.184] | [-11.266, +1.761] | 1 / 2 / 0 | 1.0 |
| val2 | observed | uncertain_fill_only | order_up_to | 3 | +2.042 | [-1.514, +5.598] | [-1.675, +8.993] | 2 / 1 / 0 | 1.0 |
| val2 | observed | uncertain_fill_only | base_stock | 3 | +2.142 | [-1.051, +5.334] | [-1.407, +8.170] | 2 / 1 / 0 | 1.0 |
| val2 | observed | uncertain_fill_only | reorder_point | 3 | +2.520 | [-0.386, +5.427] | [-0.395, +8.324] | 2 / 1 / 0 | 1.0 |
| val2 | recovered | stable | order_up_to | 4 | -5.035 | [-10.036, -0.034] | [-13.426, +0.832] | 3 / 1 / 0 | 0.625 |
| val2 | recovered | stable | base_stock | 4 | -0.550 | [-2.273, +1.118] | [-3.034, +1.878] | 2 / 2 / 0 | 1.0 |
| val2 | recovered | stable | reorder_point | 4 | -0.504 | [-2.273, +1.264] | [-3.034, +2.015] | 2 / 2 / 0 | 1.0 |
| val2 | recovered | uncertain | order_up_to | 3 | -2.455 | [-11.753, +6.843] | [-15.838, +12.055] | 2 / 1 / 0 | 1.0 |
| val2 | recovered | uncertain | base_stock | 2 | +8.546 | [+7.139, +9.953] | [+7.139, +9.953] | 0 / 2 / 0 | 0.5 |
| val2 | recovered | uncertain | reorder_point | 4 | +3.200 | [+0.457, +5.943] | [-0.981, +7.381] | 2 / 2 / 0 | 1.0 |
| val2 | recovered | uncertain_fill_only | order_up_to | 3 | +11.470 | [+4.390, +18.549] | [+0.578, +21.817] | 0 / 3 / 0 | 0.25 |
| val2 | recovered | uncertain_fill_only | base_stock | 3 | +9.675 | [+3.124, +16.225] | [+0.616, +20.267] | 0 / 3 / 0 | 0.25 |
| val2 | recovered | uncertain_fill_only | reorder_point | 3 | +10.303 | [+3.261, +17.346] | [+0.638, +21.764] | 0 / 3 / 0 | 0.25 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | order_up_to | shortage | 5 | -2.7249 | [-4.0915, -1.1531] | 4 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 5 | +7.2183 | [+0.8544, +18.9074] | 0 / 5 |
| final | observed | stable | order_up_to | service_unit_fill | 5 | +0.1340 | [+0.0532, +0.2183] | 4 / 0 |
| final | observed | stable | base_stock | shortage | 5 | -0.3842 | [-0.8999, -0.0144] | 3 / 0 |
| final | observed | stable | base_stock | avg_inventory_units | 5 | +3.6532 | [-0.0856, +10.3446] | 1 / 4 |
| final | observed | stable | base_stock | service_unit_fill | 5 | +0.0142 | [+0.0003, +0.0318] | 3 / 0 |
| final | observed | stable | reorder_point | shortage | 5 | -0.3842 | [-0.8999, -0.0144] | 3 / 0 |
| final | observed | stable | reorder_point | avg_inventory_units | 5 | +3.6532 | [-0.0856, +10.3446] | 1 / 4 |
| final | observed | stable | reorder_point | service_unit_fill | 5 | +0.0142 | [+0.0003, +0.0318] | 3 / 0 |
| final | observed | uncertain | order_up_to | shortage | 5 | -2.3983 | [-4.8040, -0.3772] | 3 / 1 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 5 | +10.6771 | [+0.7359, +29.2085] | 0 / 5 |
| final | observed | uncertain | order_up_to | service_unit_fill | 5 | +0.0733 | [+0.0066, +0.1399] | 3 / 1 |
| final | observed | uncertain | base_stock | shortage | 5 | -0.2871 | [-1.8229, +1.0459] | 2 / 2 |
| final | observed | uncertain | base_stock | avg_inventory_units | 5 | +7.6366 | [+0.3038, +21.0323] | 0 / 5 |
| final | observed | uncertain | base_stock | service_unit_fill | 5 | +0.0050 | [-0.0230, +0.0363] | 2 / 2 |
| final | observed | uncertain | reorder_point | shortage | 5 | -0.3733 | [-2.1528, +1.0264] | 2 / 2 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 5 | +8.2703 | [+0.3759, +22.6934] | 0 / 5 |
| final | observed | uncertain | reorder_point | service_unit_fill | 5 | +0.0008 | [-0.0347, +0.0381] | 2 / 2 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 4 | -2.7840 | [-4.5758, -0.9721] | 3 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 4 | +10.9217 | [+0.7222, +30.1352] | 0 / 4 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 4 | +0.0893 | [+0.0246, +0.1495] | 3 / 0 |
| final | observed | uncertain_fill_only | base_stock | shortage | 4 | -0.0356 | [-0.7063, +0.6107] | 2 / 1 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 4 | +6.8463 | [+0.2331, +19.2936] | 1 / 3 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 4 | +0.0002 | [-0.0136, +0.0132] | 2 / 1 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 4 | -0.3328 | [-1.1826, +0.2735] | 2 / 1 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 4 | +7.4260 | [+0.3854, +20.6659] | 1 / 3 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 4 | +0.0088 | [-0.0049, +0.0224] | 2 / 1 |
| final | recovered | stable | order_up_to | shortage | 5 | -4.1835 | [-8.5708, -1.1087] | 4 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 5 | +5.7732 | [+1.2893, +12.1083] | 0 / 5 |
| final | recovered | stable | order_up_to | service_unit_fill | 5 | +0.1546 | [+0.0522, +0.2534] | 4 / 0 |
| final | recovered | stable | base_stock | shortage | 5 | -0.3005 | [-0.6305, +0.0000] | 2 / 0 |
| final | recovered | stable | base_stock | avg_inventory_units | 5 | +0.4816 | [+0.0518, +1.2242] | 0 / 5 |
| final | recovered | stable | base_stock | service_unit_fill | 5 | +0.0125 | [+0.0000, +0.0317] | 2 / 0 |
| final | recovered | stable | reorder_point | shortage | 5 | -0.3005 | [-0.6305, +0.0000] | 2 / 0 |
| final | recovered | stable | reorder_point | avg_inventory_units | 5 | +0.4816 | [+0.0518, +1.2242] | 0 / 5 |
| final | recovered | stable | reorder_point | service_unit_fill | 5 | +0.0125 | [+0.0000, +0.0317] | 2 / 0 |
| final | recovered | uncertain | order_up_to | shortage | 5 | -3.2505 | [-6.5429, -0.5343] | 3 / 1 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 5 | +12.3354 | [+1.3076, +31.6704] | 0 / 5 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 5 | +0.0863 | [+0.0035, +0.1692] | 3 / 1 |
| final | recovered | uncertain | base_stock | shortage | 5 | -0.0867 | [-0.3822, +0.1222] | 1 / 1 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 5 | +7.6658 | [+0.5839, +20.2308] | 0 / 5 |
| final | recovered | uncertain | base_stock | service_unit_fill | 5 | +0.0041 | [-0.0149, +0.0271] | 1 / 1 |
| final | recovered | uncertain | reorder_point | shortage | 5 | -0.0378 | [-0.4294, +0.3160] | 1 / 1 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 5 | +8.4427 | [+0.7142, +22.0181] | 0 / 5 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 5 | -0.0027 | [-0.0386, +0.0305] | 1 / 1 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 5 | -3.3663 | [-7.2256, -0.8554] | 4 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 5 | +11.1902 | [+2.2425, +24.7115] | 0 / 5 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 5 | +0.1206 | [+0.0449, +0.1932] | 4 / 0 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 4 | +0.0631 | [+0.0000, +0.1892] | 0 / 1 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 4 | +7.1574 | [+1.3086, +15.4141] | 0 / 4 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 4 | -0.0045 | [-0.0134, +0.0000] | 0 / 1 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 5 | +0.0207 | [+0.0000, +0.0620] | 0 / 1 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 5 | +6.4460 | [+1.2392, +13.8027] | 0 / 5 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 5 | -0.0015 | [-0.0044, +0.0000] | 0 / 1 |
| val1 | observed | stable | order_up_to | shortage | 5 | -10.6291 | [-24.3165, -2.3464] | 5 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 5 | +4.0431 | [+1.2442, +9.0466] | 0 / 5 |
| val1 | observed | stable | order_up_to | service_unit_fill | 5 | +0.1032 | [+0.0434, +0.1735] | 5 / 0 |
| val1 | observed | stable | base_stock | shortage | 4 | -0.0324 | [-0.0973, +0.0000] | 1 / 0 |
| val1 | observed | stable | base_stock | avg_inventory_units | 4 | +0.8440 | [+0.0882, +2.2452] | 0 / 4 |
| val1 | observed | stable | base_stock | service_unit_fill | 4 | +0.0007 | [+0.0000, +0.0021] | 1 / 0 |
| val1 | observed | stable | reorder_point | shortage | 5 | -0.0156 | [-0.0778, +0.0311] | 1 / 1 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 5 | +0.7454 | [+0.1229, +1.9130] | 0 / 5 |
| val1 | observed | stable | reorder_point | service_unit_fill | 5 | -0.0000 | [-0.0017, +0.0017] | 1 / 1 |
| val1 | observed | uncertain | order_up_to | shortage | 3 | -37.1996 | [-78.7402, -12.6201] | 3 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 3 | +22.8130 | [+3.5275, +59.7428] | 0 / 3 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 3 | +0.2417 | [+0.1854, +0.2705] | 3 / 0 |
| val1 | observed | uncertain | base_stock | shortage | 3 | -12.2923 | [-22.4114, -7.0411] | 3 / 0 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 3 | +18.1391 | [+2.9914, +48.3655] | 0 / 3 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 3 | +0.1019 | [+0.0528, +0.1592] | 3 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 3 | -14.3650 | [-27.6167, -7.6508] | 3 / 0 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 3 | +18.7774 | [+3.0714, +49.9347] | 0 / 3 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 3 | +0.1115 | [+0.0650, +0.1678] | 3 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 3 | -13.6509 | [-30.6304, -4.4831] | 3 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 3 | +18.9454 | [+2.8664, +42.5451] | 0 / 3 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 3 | +0.0856 | [+0.0597, +0.1252] | 3 / 0 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 3 | -0.2135 | [-0.6405, +0.0000] | 1 / 0 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 3 | +13.5099 | [+1.9659, +30.0300] | 0 / 3 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 3 | +0.0046 | [+0.0000, +0.0137] | 1 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 3 | -0.4140 | [-1.2419, +0.0000] | 1 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 3 | +14.5251 | [+2.1472, +32.4627] | 0 / 3 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 3 | +0.0089 | [+0.0000, +0.0266] | 1 / 0 |
| val1 | recovered | stable | order_up_to | shortage | 4 | -17.6709 | [-42.9118, -2.9972] | 4 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 4 | +6.1933 | [+1.4692, +14.8668] | 0 / 4 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 4 | +0.1035 | [+0.0915, +0.1209] | 4 / 0 |
| val1 | recovered | stable | base_stock | shortage | 4 | -0.9335 | [-2.7286, -0.0172] | 3 / 0 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 4 | +1.8393 | [+0.1574, +5.1544] | 0 / 4 |
| val1 | recovered | stable | base_stock | service_unit_fill | 4 | +0.0029 | [+0.0004, +0.0054] | 3 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 4 | -0.9335 | [-2.7286, -0.0172] | 3 / 0 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 4 | +1.8393 | [+0.1569, +5.1496] | 0 / 4 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 4 | +0.0029 | [+0.0004, +0.0054] | 3 / 0 |
| val1 | recovered | uncertain | order_up_to | shortage | 3 | -50.7358 | [-116.9178, -15.0287] | 3 / 0 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 3 | +28.5827 | [+3.9092, +72.6441] | 0 / 3 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 3 | +0.2455 | [+0.2105, +0.2679] | 3 / 0 |
| val1 | recovered | uncertain | base_stock | shortage | 3 | -21.6417 | [-52.0384, -4.5675] | 3 / 0 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 3 | +23.2098 | [+2.3653, +59.8722] | 0 / 3 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 3 | +0.0937 | [+0.0814, +0.1060] | 3 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 3 | -24.4302 | [-58.7029, -5.0684] | 3 / 0 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 3 | +23.8180 | [+2.5204, +61.3280] | 0 / 3 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 3 | +0.1058 | [+0.0903, +0.1212] | 3 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 3 | -17.8646 | [-44.3067, -4.1855] | 3 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 3 | +19.8519 | [+4.8077, +44.0105] | 0 / 3 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 3 | +0.0747 | [+0.0533, +0.0909] | 3 / 0 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 3 | +0.8121 | [+0.0000, +2.4362] | 0 / 1 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 3 | +13.6018 | [+2.7686, +29.8019] | 0 / 3 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 3 | -0.0145 | [-0.0434, +0.0000] | 0 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 3 | +0.8121 | [+0.0000, +2.4362] | 0 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 3 | +14.6450 | [+3.0293, +32.2380] | 0 / 3 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 3 | -0.0145 | [-0.0434, +0.0000] | 0 / 1 |
| val2 | observed | stable | order_up_to | shortage | 3 | -27.4713 | [-67.3220, -6.4410] | 3 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 3 | +5.3848 | [+1.0417, +12.7790] | 0 / 3 |
| val2 | observed | stable | order_up_to | service_unit_fill | 3 | +0.1239 | [+0.0795, +0.1619] | 3 / 0 |
| val2 | observed | stable | base_stock | shortage | 3 | -0.5276 | [-1.5828, +0.0000] | 1 / 0 |
| val2 | observed | stable | base_stock | avg_inventory_units | 3 | +1.5882 | [+0.1368, +4.3956] | 0 / 3 |
| val2 | observed | stable | base_stock | service_unit_fill | 3 | +0.0079 | [+0.0000, +0.0238] | 1 / 0 |
| val2 | observed | stable | reorder_point | shortage | 3 | -0.5276 | [-1.5828, +0.0000] | 1 / 0 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 3 | +1.5882 | [+0.1368, +4.3956] | 0 / 3 |
| val2 | observed | stable | reorder_point | service_unit_fill | 3 | +0.0079 | [+0.0000, +0.0238] | 1 / 0 |
| val2 | observed | uncertain | order_up_to | shortage | 3 | -48.8276 | [-116.5635, -14.4789] | 3 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 3 | +13.9451 | [+2.9747, +27.8008] | 0 / 3 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 3 | +0.2305 | [+0.1788, +0.2803] | 3 / 0 |
| val2 | observed | uncertain | base_stock | shortage | 3 | -17.9669 | [-39.6252, -2.7120] | 3 / 0 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 3 | +11.1809 | [+2.2969, +21.5743] | 0 / 3 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 3 | +0.1009 | [+0.0335, +0.1740] | 3 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 3 | -20.7574 | [-48.9885, -3.7710] | 3 / 0 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 3 | +11.9216 | [+2.4509, +23.3513] | 0 / 3 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 3 | +0.1025 | [+0.0466, +0.1432] | 3 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 3 | -27.1044 | [-63.1401, -4.6223] | 3 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 3 | +15.0849 | [+4.0571, +32.0561] | 0 / 3 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 3 | +0.1376 | [+0.0571, +0.2039] | 3 / 0 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 3 | -4.3908 | [-7.3806, -2.5190] | 3 / 0 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 3 | +11.5999 | [+3.1871, +25.0216] | 0 / 3 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 3 | +0.0500 | [+0.0079, +0.1111] | 3 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 3 | -5.5081 | [-8.3124, +0.0000] | 2 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 3 | +12.5086 | [+3.3985, +27.2974] | 0 / 3 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 3 | +0.0483 | [+0.0000, +0.1251] | 2 / 0 |
| val2 | recovered | stable | order_up_to | shortage | 4 | -21.5535 | [-48.5477, -5.3449] | 4 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 4 | +7.2855 | [+1.5230, +13.0480] | 0 / 4 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 4 | +0.1234 | [+0.0888, +0.1562] | 4 / 0 |
| val2 | recovered | stable | base_stock | shortage | 4 | -3.8867 | [-8.7730, -0.6007] | 4 / 0 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 4 | +2.4298 | [+0.5162, +4.3434] | 0 / 4 |
| val2 | recovered | stable | base_stock | service_unit_fill | 4 | +0.0265 | [+0.0085, +0.0444] | 4 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 4 | -3.8867 | [-8.7730, -0.6007] | 4 / 0 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 4 | +2.4862 | [+0.5287, +4.4436] | 0 / 4 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 4 | +0.0265 | [+0.0085, +0.0444] | 4 / 0 |
| val2 | recovered | uncertain | order_up_to | shortage | 3 | -63.8485 | [-160.9894, -10.4009] | 3 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 3 | +21.5867 | [+6.6497, +43.8210] | 0 / 3 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 3 | +0.2039 | [+0.1069, +0.2850] | 3 / 0 |
| val2 | recovered | uncertain | base_stock | shortage | 2 | -36.3334 | [-69.1465, -3.5203] | 2 / 0 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 2 | +22.2748 | [+10.0529, +34.4967] | 0 / 2 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 2 | +0.0793 | [+0.0362, +0.1224] | 2 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 4 | -24.4104 | [-61.3419, -3.7283] | 4 / 0 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 4 | +13.6268 | [+3.6455, +28.5136] | 0 / 4 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 4 | +0.1601 | [+0.0669, +0.2889] | 4 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 3 | -20.3500 | [-50.7587, -2.7054] | 3 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 3 | +13.1641 | [+1.0137, +27.9150] | 0 / 3 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 3 | +0.0962 | [+0.0779, +0.1207] | 3 / 0 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 3 | -0.4935 | [-1.6646, +1.2983] | 2 / 1 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 3 | +7.5445 | [+0.4343, +15.9934] | 0 / 3 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 3 | +0.0215 | [-0.0023, +0.0497] | 2 / 1 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 3 | -2.2957 | [-3.5344, -1.2412] | 3 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 3 | +8.7274 | [+0.5366, +18.6649] | 0 / 3 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 3 | +0.0278 | [+0.0063, +0.0554] | 3 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 67/90 complete, 23 infeasible, 0 abstained; gated: 70/90 complete, 0 infeasible, 20 abstained; order_up_to: 85/90 complete, 5 infeasible, 0 abstained; reorder_point: 90/90 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 48
- ZAAD runs that retained the incumbent proxy on at least one review: 90 of 90 (487 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/uncertain store 514 product 267: ZAAD minus base_stock = +26.657 (fill 0.922 vs 0.869, inventory 69.00 vs 20.64, retained incumbent on 3 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +22.011 (fill 0.922 vs 0.922, inventory 50.57 vs 20.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 514 product 267: ZAAD minus order_up_to = +21.817 (fill 0.912 vs 0.822, inventory 36.46 vs 8.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain store 230 product 580: ZAAD minus order_up_to = +12.055 (fill 0.755 vs 0.648, inventory 19.59 vs 5.30, retained incumbent on 10 reviews)
- val2/recovered/uncertain_fill_only store 230 product 580: ZAAD minus order_up_to = +12.014 (fill 0.796 vs 0.718, inventory 14.09 vs 3.53, retained incumbent on 8 reviews)
- val2/observed/uncertain_fill_only store 514 product 267: ZAAD minus order_up_to = +8.993 (fill 0.985 vs 0.833, inventory 36.58 vs 4.52, retained incumbent on 2 reviews)
- final/recovered/uncertain store 514 product 267: ZAAD minus order_up_to = +8.703 (fill 0.954 vs 0.954, inventory 68.14 vs 17.32, retained incumbent on 2 reviews)
- final/observed/uncertain store 514 product 267: ZAAD minus order_up_to = +7.713 (fill 0.898 vs 0.898, inventory 65.03 vs 17.53, retained incumbent on 2 reviews)
- val2/recovered/uncertain store 514 product 267: ZAAD minus base_stock = +7.139 (fill 0.987 vs 0.865, inventory 53.22 vs 18.72, retained incumbent on 4 reviews)
- final/observed/uncertain store 230 product 580: ZAAD minus reorder_point = +4.162 (fill 0.770 vs 0.809, inventory 2.77 vs 1.47, retained incumbent on 6 reviews)
