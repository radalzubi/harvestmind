# FreshRetailNet pilot results: stage `fifty`

Commit `5c39a51d451be694fcc425208a29967f174395bb`, declaration `eea25bb1f36d`, selection `497bf5a8741a`; 3600 runs, 2425 complete, 1175 not complete; wall 950 s, peak RSS 270 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | retained inc. | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 35/50 | 14.002 | 13.574 | 0.0068 | 0.517 | 0.973 | 0.345 | 1.978 | 0.6 | 6.7 | 0.0 | 0.07 |
| final | observed | stable | gated | 35/50 | 13.720 | 12.449 | 0.0092 | 0.344 | 0.983 | 0.230 | 2.655 | 0.4 | 5.4 | 4.9 | 0.34 |
| final | observed | stable | order_up_to | 42/50 | 12.586 | 9.309 | 0.0025 | 2.122 | 0.839 | 1.415 | 0.731 | 2.6 | 6.3 | 0.0 | 0.05 |
| final | observed | stable | reorder_point | 49/50 | 10.766 | 9.473 | 0.0055 | 0.399 | 0.977 | 0.266 | 1.607 | 0.6 | 5.3 | 0.0 | 0.01 |
| final | observed | uncertain | base_stock | 33/50 | 18.114 | 17.115 | 0.0065 | 3.119 | 0.859 | 2.079 | 1.894 | 1.8 | 6.3 | 0.0 | 0.06 |
| final | observed | uncertain | gated | 32/50 | 17.762 | 16.984 | 0.0127 | 2.310 | 0.901 | 1.540 | 3.683 | 1.3 | 3.7 | 3.3 | 0.28 |
| final | observed | uncertain | order_up_to | 38/50 | 16.140 | 11.998 | 0.0032 | 4.519 | 0.734 | 3.013 | 0.941 | 3.0 | 6.2 | 0.0 | 0.05 |
| final | observed | uncertain | reorder_point | 49/50 | 13.111 | 11.402 | 0.0049 | 2.277 | 0.881 | 1.518 | 1.410 | 1.5 | 5.2 | 0.0 | 0.01 |
| final | observed | uncertain_fill_only | base_stock | 29/50 | 18.787 | 19.059 | 0.0087 | 1.885 | 0.930 | 1.257 | 2.534 | 1.4 | 6.4 | 0.0 | 0.06 |
| final | observed | uncertain_fill_only | gated | 33/50 | 15.991 | 15.262 | 0.0122 | 1.460 | 0.950 | 0.973 | 3.533 | 0.9 | 4.1 | 3.2 | 0.38 |
| final | observed | uncertain_fill_only | order_up_to | 38/50 | 15.416 | 12.510 | 0.0041 | 3.117 | 0.824 | 2.078 | 1.186 | 2.5 | 6.4 | 0.0 | 0.05 |
| final | observed | uncertain_fill_only | reorder_point | 49/50 | 12.374 | 11.555 | 0.0060 | 1.229 | 0.947 | 0.819 | 1.750 | 1.0 | 5.3 | 0.0 | 0.02 |
| final | recovered | stable | base_stock | 39/50 | 14.360 | 14.229 | 0.0090 | 0.346 | 0.976 | 0.230 | 2.602 | 0.5 | 6.5 | 0.0 | 0.07 |
| final | recovered | stable | gated | 39/50 | 14.098 | 12.789 | 0.0095 | 0.208 | 0.983 | 0.139 | 2.757 | 0.3 | 5.3 | 5.1 | 0.29 |
| final | recovered | stable | order_up_to | 44/50 | 13.666 | 9.642 | 0.0033 | 2.556 | 0.820 | 1.704 | 0.960 | 2.3 | 6.0 | 0.0 | 0.05 |
| final | recovered | stable | reorder_point | 50/50 | 11.904 | 10.643 | 0.0076 | 0.349 | 0.972 | 0.233 | 2.201 | 0.5 | 5.2 | 0.0 | 0.01 |
| final | recovered | uncertain | base_stock | 36/50 | 18.463 | 18.504 | 0.0082 | 2.281 | 0.892 | 1.521 | 2.378 | 1.4 | 5.9 | 0.0 | 0.06 |
| final | recovered | uncertain | gated | 34/50 | 18.976 | 19.059 | 0.0143 | 2.017 | 0.913 | 1.345 | 4.128 | 1.2 | 3.7 | 3.7 | 0.28 |
| final | recovered | uncertain | order_up_to | 41/50 | 16.778 | 12.741 | 0.0034 | 4.186 | 0.750 | 2.790 | 0.975 | 2.7 | 6.0 | 0.0 | 0.05 |
| final | recovered | uncertain | reorder_point | 50/50 | 14.497 | 13.293 | 0.0063 | 1.925 | 0.889 | 1.283 | 1.832 | 1.4 | 4.9 | 0.0 | 0.01 |
| final | recovered | uncertain_fill_only | base_stock | 32/50 | 18.868 | 20.401 | 0.0110 | 1.019 | 0.954 | 0.679 | 3.196 | 1.0 | 6.0 | 0.0 | 0.06 |
| final | recovered | uncertain_fill_only | gated | 37/50 | 16.299 | 16.600 | 0.0139 | 0.827 | 0.962 | 0.551 | 4.017 | 0.7 | 4.0 | 3.6 | 0.38 |
| final | recovered | uncertain_fill_only | order_up_to | 42/50 | 15.812 | 13.017 | 0.0045 | 2.834 | 0.822 | 1.889 | 1.303 | 2.5 | 6.2 | 0.0 | 0.05 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 13.554 | 13.413 | 0.0079 | 0.803 | 0.953 | 0.535 | 2.301 | 0.9 | 5.0 | 0.0 | 0.02 |
| val1 | observed | stable | base_stock | 23/50 | 30.759 | 29.947 | 0.0132 | 0.697 | 0.977 | 0.464 | 1.906 | 1.1 | 13.2 | 0.0 | 0.26 |
| val1 | observed | stable | gated | 25/50 | 29.025 | 28.552 | 0.0158 | 0.473 | 0.981 | 0.315 | 2.283 | 1.0 | 12.7 | 11.8 | 2.55 |
| val1 | observed | stable | order_up_to | 38/50 | 23.085 | 17.490 | 0.0034 | 4.610 | 0.812 | 3.073 | 0.492 | 5.5 | 12.4 | 0.0 | 0.11 |
| val1 | observed | stable | reorder_point | 50/50 | 18.733 | 17.901 | 0.0124 | 0.745 | 0.956 | 0.497 | 1.350 | 1.3 | 11.1 | 0.0 | 0.03 |
| val1 | observed | uncertain | base_stock | 21/50 | 39.207 | 34.990 | 0.0154 | 6.330 | 0.870 | 4.220 | 2.232 | 3.2 | 12.3 | 0.0 | 0.22 |
| val1 | observed | uncertain | gated | 18/50 | 44.705 | 46.532 | 0.1698 | 3.703 | 0.912 | 2.469 | 7.147 | 1.9 | 9.5 | 8.2 | 1.29 |
| val1 | observed | uncertain | order_up_to | 25/50 | 35.695 | 25.346 | 0.0063 | 11.187 | 0.737 | 7.458 | 0.920 | 5.8 | 12.3 | 0.0 | 0.12 |
| val1 | observed | uncertain | reorder_point | 50/50 | 22.020 | 19.550 | 0.0130 | 3.517 | 0.887 | 2.344 | 1.444 | 2.8 | 11.3 | 0.0 | 0.03 |
| val1 | observed | uncertain_fill_only | base_stock | 16/50 | 45.476 | 44.324 | 0.0199 | 4.040 | 0.917 | 2.693 | 2.875 | 2.2 | 12.2 | 0.0 | 0.23 |
| val1 | observed | uncertain_fill_only | gated | 15/50 | 48.848 | 52.493 | 0.0861 | 3.377 | 0.951 | 2.251 | 7.214 | 1.3 | 9.3 | 6.5 | 1.94 |
| val1 | observed | uncertain_fill_only | order_up_to | 24/50 | 34.631 | 28.364 | 0.0062 | 6.819 | 0.822 | 4.546 | 0.900 | 5.2 | 12.8 | 0.0 | 0.12 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.503 | 20.686 | 0.0157 | 1.965 | 0.922 | 1.310 | 1.571 | 1.9 | 11.4 | 0.0 | 0.03 |
| val1 | recovered | stable | base_stock | 31/50 | 30.448 | 28.835 | 0.0148 | 0.925 | 0.969 | 0.617 | 2.146 | 1.0 | 13.1 | 0.0 | 0.27 |
| val1 | recovered | stable | gated | 29/50 | 31.184 | 29.840 | 0.0180 | 0.846 | 0.969 | 0.564 | 2.611 | 0.8 | 12.4 | 11.7 | 2.37 |
| val1 | recovered | stable | order_up_to | 42/50 | 26.635 | 19.480 | 0.0043 | 5.777 | 0.793 | 3.851 | 0.627 | 4.8 | 12.0 | 0.0 | 0.11 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.692 | 21.202 | 0.0153 | 1.062 | 0.953 | 0.708 | 1.799 | 1.1 | 10.6 | 0.0 | 0.02 |
| val1 | recovered | uncertain | base_stock | 17/50 | 55.280 | 49.476 | 0.0213 | 8.426 | 0.868 | 5.618 | 3.090 | 3.1 | 12.6 | 0.0 | 0.23 |
| val1 | recovered | uncertain | gated | 12/50 | 69.079 | 74.373 | 0.1364 | 2.911 | 0.943 | 1.941 | 11.745 | 1.2 | 9.4 | 6.5 | 1.49 |
| val1 | recovered | uncertain | order_up_to | 34/50 | 34.972 | 24.757 | 0.0065 | 10.602 | 0.739 | 7.068 | 0.936 | 5.4 | 11.9 | 0.0 | 0.12 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 26.613 | 23.851 | 0.0156 | 3.871 | 0.904 | 2.581 | 1.886 | 2.2 | 10.9 | 0.0 | 0.02 |
| val1 | recovered | uncertain_fill_only | base_stock | 14/50 | 59.718 | 59.040 | 0.0249 | 3.683 | 0.910 | 2.455 | 3.607 | 2.2 | 12.4 | 0.0 | 0.22 |
| val1 | recovered | uncertain_fill_only | gated | 12/50 | 66.628 | 68.027 | 0.0807 | 2.439 | 0.959 | 1.626 | 9.013 | 0.9 | 8.9 | 6.3 | 1.94 |
| val1 | recovered | uncertain_fill_only | order_up_to | 34/50 | 33.422 | 27.059 | 0.0066 | 6.364 | 0.805 | 4.243 | 0.957 | 4.5 | 11.9 | 0.0 | 0.12 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 25.769 | 25.031 | 0.0184 | 1.747 | 0.931 | 1.165 | 2.040 | 1.7 | 11.0 | 0.0 | 0.03 |
| val2 | observed | stable | base_stock | 33/50 | 24.438 | 23.738 | 0.0111 | 0.621 | 0.976 | 0.414 | 1.605 | 1.1 | 12.9 | 0.0 | 0.27 |
| val2 | observed | stable | gated | 25/50 | 29.350 | 28.784 | 0.0147 | 0.544 | 0.982 | 0.363 | 2.134 | 0.8 | 13.0 | 11.8 | 2.46 |
| val2 | observed | stable | order_up_to | 35/50 | 24.830 | 18.682 | 0.0062 | 5.300 | 0.837 | 3.533 | 0.609 | 4.7 | 12.3 | 0.0 | 0.12 |
| val2 | observed | stable | reorder_point | 50/50 | 18.766 | 18.087 | 0.0134 | 0.645 | 0.965 | 0.430 | 1.411 | 1.0 | 11.0 | 0.0 | 0.03 |
| val2 | observed | uncertain | base_stock | 15/50 | 49.455 | 45.472 | 0.0143 | 7.032 | 0.892 | 4.688 | 2.071 | 2.3 | 12.9 | 0.0 | 0.24 |
| val2 | observed | uncertain | gated | 9/50 | 68.506 | 72.831 | 0.0894 | 2.801 | 0.942 | 1.867 | 8.197 | 1.4 | 8.8 | 6.2 | 1.47 |
| val2 | observed | uncertain | order_up_to | 31/50 | 31.691 | 22.474 | 0.0076 | 10.014 | 0.736 | 6.676 | 0.765 | 5.3 | 11.9 | 0.0 | 0.13 |
| val2 | observed | uncertain | reorder_point | 50/50 | 22.392 | 20.573 | 0.0136 | 3.224 | 0.897 | 2.149 | 1.342 | 2.2 | 11.1 | 0.0 | 0.03 |
| val2 | observed | uncertain_fill_only | base_stock | 15/50 | 49.495 | 49.322 | 0.0164 | 2.457 | 0.950 | 1.638 | 2.372 | 1.4 | 13.3 | 0.0 | 0.25 |
| val2 | observed | uncertain_fill_only | gated | 14/50 | 51.299 | 54.838 | 0.0479 | 1.044 | 0.975 | 0.696 | 6.216 | 0.7 | 9.7 | 6.4 | 1.99 |
| val2 | observed | uncertain_fill_only | order_up_to | 29/50 | 31.713 | 26.016 | 0.0052 | 5.931 | 0.847 | 3.954 | 0.760 | 4.5 | 12.7 | 0.0 | 0.13 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 22.187 | 21.895 | 0.0145 | 1.432 | 0.937 | 0.954 | 1.526 | 1.3 | 11.2 | 0.0 | 0.03 |
| val2 | recovered | stable | base_stock | 30/50 | 33.141 | 30.060 | 0.0167 | 2.940 | 0.949 | 1.960 | 2.420 | 1.2 | 12.9 | 0.0 | 0.28 |
| val2 | recovered | stable | gated | 32/50 | 32.050 | 30.268 | 0.0219 | 2.171 | 0.960 | 1.447 | 2.965 | 1.0 | 12.1 | 11.6 | 2.62 |
| val2 | recovered | stable | order_up_to | 38/50 | 29.868 | 21.028 | 0.0080 | 7.396 | 0.796 | 4.930 | 0.835 | 4.3 | 11.9 | 0.0 | 0.12 |
| val2 | recovered | stable | reorder_point | 49/50 | 24.058 | 21.901 | 0.0183 | 2.102 | 0.946 | 1.401 | 2.042 | 1.2 | 10.3 | 0.0 | 0.03 |
| val2 | recovered | uncertain | base_stock | 14/50 | 60.133 | 53.264 | 0.0255 | 9.621 | 0.912 | 6.414 | 3.689 | 2.1 | 11.9 | 0.0 | 0.24 |
| val2 | recovered | uncertain | gated | 17/50 | 57.173 | 64.903 | 0.0784 | 3.143 | 0.942 | 2.096 | 8.312 | 1.1 | 8.6 | 6.7 | 1.47 |
| val2 | recovered | uncertain | order_up_to | 33/50 | 37.141 | 25.360 | 0.0084 | 11.928 | 0.760 | 7.952 | 1.210 | 4.8 | 11.4 | 0.0 | 0.13 |
| val2 | recovered | uncertain | reorder_point | 49/50 | 28.118 | 24.797 | 0.0189 | 4.580 | 0.895 | 3.053 | 2.082 | 2.1 | 10.5 | 0.0 | 0.03 |
| val2 | recovered | uncertain_fill_only | base_stock | 13/50 | 64.293 | 60.812 | 0.0268 | 6.506 | 0.941 | 4.338 | 3.887 | 1.4 | 12.5 | 0.0 | 0.24 |
| val2 | recovered | uncertain_fill_only | gated | 16/50 | 58.781 | 60.599 | 0.0704 | 5.390 | 0.932 | 3.593 | 6.521 | 1.3 | 10.0 | 6.9 | 1.92 |
| val2 | recovered | uncertain_fill_only | order_up_to | 34/50 | 35.701 | 28.060 | 0.0085 | 7.599 | 0.834 | 5.066 | 1.226 | 3.8 | 11.6 | 0.0 | 0.13 |
| val2 | recovered | uncertain_fill_only | reorder_point | 49/50 | 28.077 | 26.666 | 0.0200 | 2.760 | 0.932 | 1.840 | 2.268 | 1.5 | 10.7 | 0.0 | 0.03 |

## Paired comparison, ZAAD minus baseline per series (realized cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | order_up_to | 35 | -0.558 | [-0.750, -0.360] | [-0.854, -0.255] | 29 / 6 / 0 | 0.0 |
| final | observed | stable | base_stock | 33 | -0.311 | [-0.416, -0.211] | [-0.483, -0.166] | 28 / 5 / 0 | 0.0 |
| final | observed | stable | reorder_point | 35 | +0.020 | [-0.061, +0.109] | [-0.098, +0.166] | 17 / 18 / 0 | 1.0 |
| final | observed | uncertain | order_up_to | 30 | -0.071 | [-0.481, +0.365] | [-0.636, +0.677] | 20 / 10 / 0 | 0.099 |
| final | observed | uncertain | base_stock | 28 | -0.398 | [-0.666, -0.130] | [-0.804, +0.024] | 22 / 6 / 0 | 0.004 |
| final | observed | uncertain | reorder_point | 32 | +0.239 | [-0.055, +0.552] | [-0.161, +0.727] | 17 / 15 / 0 | 0.86 |
| final | observed | uncertain_fill_only | order_up_to | 30 | -0.824 | [-1.234, -0.441] | [-1.490, -0.290] | 20 / 10 / 0 | 0.099 |
| final | observed | uncertain_fill_only | base_stock | 26 | -1.101 | [-1.734, -0.527] | [-2.193, -0.349] | 19 / 7 / 0 | 0.029 |
| final | observed | uncertain_fill_only | reorder_point | 33 | -0.234 | [-0.487, +0.008] | [-0.640, +0.112] | 19 / 14 / 0 | 0.487 |
| final | recovered | stable | order_up_to | 39 | -0.718 | [-0.904, -0.542] | [-1.017, -0.457] | 33 / 6 / 0 | 0.0 |
| final | recovered | stable | base_stock | 36 | -0.378 | [-0.516, -0.256] | [-0.599, -0.207] | 31 / 5 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 39 | -0.042 | [-0.082, -0.003] | [-0.103, +0.018] | 20 / 19 / 0 | 1.0 |
| final | recovered | uncertain | order_up_to | 30 | +0.559 | [+0.149, +1.000] | [-0.028, +1.293] | 12 / 18 / 0 | 0.362 |
| final | recovered | uncertain | base_stock | 29 | +0.006 | [-0.246, +0.243] | [-0.375, +0.386] | 18 / 11 / 0 | 0.265 |
| final | recovered | uncertain | reorder_point | 34 | +0.647 | [+0.371, +0.940] | [+0.247, +1.128] | 13 / 21 / 0 | 0.229 |
| final | recovered | uncertain_fill_only | order_up_to | 35 | -0.588 | [-0.939, -0.277] | [-1.136, -0.155] | 21 / 14 / 0 | 0.311 |
| final | recovered | uncertain_fill_only | base_stock | 30 | -0.874 | [-1.461, -0.343] | [-1.860, -0.197] | 20 / 10 / 0 | 0.099 |
| final | recovered | uncertain_fill_only | reorder_point | 37 | -0.107 | [-0.340, +0.116] | [-0.467, +0.234] | 22 / 15 / 0 | 0.324 |
| val1 | observed | stable | order_up_to | 22 | -1.533 | [-2.065, -1.071] | [-2.440, -0.965] | 21 / 1 / 0 | 0.0 |
| val1 | observed | stable | base_stock | 20 | -0.043 | [-0.088, +0.002] | [-0.116, +0.020] | 6 / 14 / 0 | 0.115 |
| val1 | observed | stable | reorder_point | 25 | -0.029 | [-0.063, +0.003] | [-0.084, +0.016] | 9 / 16 / 0 | 0.23 |
| val1 | observed | uncertain | order_up_to | 13 | +1.112 | [-0.030, +2.258] | [-0.491, +2.984] | 8 / 5 / 0 | 0.581 |
| val1 | observed | uncertain | base_stock | 15 | +2.820 | [+0.718, +5.109] | [+0.235, +6.717] | 5 / 10 / 0 | 0.302 |
| val1 | observed | uncertain | reorder_point | 18 | +2.529 | [+0.881, +4.369] | [+0.437, +5.566] | 7 / 11 / 0 | 0.481 |
| val1 | observed | uncertain_fill_only | order_up_to | 12 | +2.075 | [+0.155, +4.185] | [-0.197, +5.545] | 5 / 7 / 0 | 0.774 |
| val1 | observed | uncertain_fill_only | base_stock | 12 | +2.852 | [+0.656, +5.375] | [+0.308, +7.061] | 2 / 10 / 0 | 0.039 |
| val1 | observed | uncertain_fill_only | reorder_point | 15 | +2.528 | [+0.810, +4.470] | [+0.421, +5.726] | 3 / 12 / 0 | 0.035 |
| val1 | recovered | stable | order_up_to | 28 | -1.589 | [-2.271, -0.940] | [-2.867, -0.838] | 28 / 0 / 0 | 0.0 |
| val1 | recovered | stable | base_stock | 25 | -0.047 | [-0.144, +0.039] | [-0.207, +0.072] | 10 / 15 / 0 | 0.424 |
| val1 | recovered | stable | reorder_point | 29 | -0.026 | [-0.113, +0.049] | [-0.167, +0.076] | 11 / 18 / 0 | 0.265 |
| val1 | recovered | uncertain | order_up_to | 12 | -2.335 | [-5.627, +0.627] | [-8.209, +1.262] | 7 / 5 / 0 | 0.774 |
| val1 | recovered | uncertain | base_stock | 11 | +0.113 | [-1.587, +1.637] | [-2.720, +2.241] | 4 / 7 / 0 | 0.549 |
| val1 | recovered | uncertain | reorder_point | 12 | +0.085 | [-1.616, +1.563] | [-2.705, +2.122] | 4 / 8 / 0 | 0.388 |
| val1 | recovered | uncertain_fill_only | order_up_to | 11 | -0.288 | [-1.835, +1.163] | [-2.650, +1.817] | 6 / 5 / 0 | 1.0 |
| val1 | recovered | uncertain_fill_only | base_stock | 10 | +0.879 | [+0.101, +1.684] | [-0.244, +2.158] | 6 / 4 / 0 | 0.754 |
| val1 | recovered | uncertain_fill_only | reorder_point | 12 | +0.913 | [+0.275, +1.581] | [+0.030, +1.972] | 4 / 8 / 0 | 0.388 |
| val2 | observed | stable | order_up_to | 25 | -1.751 | [-2.741, -0.867] | [-3.516, -0.749] | 24 / 1 / 0 | 0.0 |
| val2 | observed | stable | base_stock | 25 | -0.012 | [-0.055, +0.031] | [-0.080, +0.052] | 12 / 13 / 0 | 1.0 |
| val2 | observed | stable | reorder_point | 25 | -0.036 | [-0.080, +0.004] | [-0.104, +0.023] | 12 / 13 / 0 | 1.0 |
| val2 | observed | uncertain | order_up_to | 8 | -2.661 | [-6.260, +0.649] | [-9.162, +1.214] | 5 / 3 / 0 | 0.727 |
| val2 | observed | uncertain | base_stock | 8 | +0.025 | [-1.526, +1.509] | [-2.451, +2.088] | 4 / 4 / 0 | 1.0 |
| val2 | observed | uncertain | reorder_point | 9 | +0.362 | [-1.708, +2.150] | [-3.019, +2.833] | 3 / 6 / 0 | 0.508 |
| val2 | observed | uncertain_fill_only | order_up_to | 13 | +0.875 | [-0.117, +1.939] | [-0.483, +2.600] | 6 / 7 / 0 | 1.0 |
| val2 | observed | uncertain_fill_only | base_stock | 11 | +1.140 | [+0.170, +2.222] | [-0.177, +2.902] | 4 / 7 / 0 | 0.549 |
| val2 | observed | uncertain_fill_only | reorder_point | 14 | +1.189 | [+0.392, +2.087] | [+0.122, +2.613] | 5 / 9 / 0 | 0.424 |
| val2 | recovered | stable | order_up_to | 32 | -1.500 | [-2.185, -0.860] | [-2.724, -0.685] | 29 / 3 / 0 | 0.0 |
| val2 | recovered | stable | base_stock | 28 | -0.098 | [-0.342, +0.121] | [-0.488, +0.251] | 11 / 17 / 0 | 0.345 |
| val2 | recovered | stable | reorder_point | 32 | -0.104 | [-0.322, +0.094] | [-0.444, +0.215] | 16 / 16 / 0 | 1.0 |
| val2 | recovered | uncertain | order_up_to | 14 | +0.553 | [-1.560, +2.469] | [-2.806, +3.503] | 5 / 9 / 0 | 0.424 |
| val2 | recovered | uncertain | base_stock | 9 | +2.954 | [+1.468, +4.468] | [+0.860, +5.392] | 2 / 7 / 0 | 0.18 |
| val2 | recovered | uncertain | reorder_point | 17 | +2.018 | [+1.180, +2.901] | [+0.810, +3.405] | 5 / 12 / 0 | 0.143 |
| val2 | recovered | uncertain_fill_only | order_up_to | 15 | +2.621 | [+0.763, +4.711] | [+0.246, +5.909] | 3 / 12 / 0 | 0.035 |
| val2 | recovered | uncertain_fill_only | base_stock | 9 | +3.476 | [+0.764, +6.309] | [+0.160, +8.035] | 1 / 8 / 0 | 0.039 |
| val2 | recovered | uncertain_fill_only | reorder_point | 16 | +2.947 | [+1.275, +4.809] | [+0.797, +5.982] | 1 / 15 / 0 | 0.001 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | order_up_to | shortage | 35 | -1.9653 | [-2.6916, -1.3440] | 32 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 35 | +1.8292 | [+0.8220, +3.6896] | 0 / 35 |
| final | observed | stable | order_up_to | service_unit_fill | 35 | +0.1381 | [+0.1085, +0.1698] | 32 / 0 |
| final | observed | stable | base_stock | shortage | 33 | -0.1517 | [-0.2983, -0.0250] | 11 / 1 |
| final | observed | stable | base_stock | avg_inventory_units | 33 | +0.7224 | [+0.1148, +1.8144] | 4 / 29 |
| final | observed | stable | base_stock | service_unit_fill | 33 | +0.0071 | [+0.0019, +0.0128] | 11 / 1 |
| final | observed | stable | reorder_point | shortage | 35 | -0.1578 | [-0.3046, -0.0351] | 12 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 35 | +0.6955 | [+0.1229, +1.7147] | 2 / 33 |
| final | observed | stable | reorder_point | service_unit_fill | 35 | +0.0069 | [+0.0018, +0.0122] | 12 / 1 |
| final | observed | uncertain | order_up_to | shortage | 30 | -2.7084 | [-4.0293, -1.6237] | 23 / 1 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 30 | +2.7573 | [+1.0324, +5.9487] | 0 / 30 |
| final | observed | uncertain | order_up_to | service_unit_fill | 30 | +0.1656 | [+0.1219, +0.2093] | 23 / 1 |
| final | observed | uncertain | base_stock | shortage | 28 | -0.8030 | [-1.7214, -0.1145] | 12 / 2 |
| final | observed | uncertain | base_stock | avg_inventory_units | 28 | +1.8720 | [+0.5154, +4.3703] | 0 / 28 |
| final | observed | uncertain | base_stock | service_unit_fill | 28 | +0.0314 | [+0.0117, +0.0547] | 12 / 2 |
| final | observed | uncertain | reorder_point | shortage | 32 | -0.7885 | [-1.6561, -0.1774] | 14 / 2 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 32 | +1.8794 | [+0.5996, +4.2666] | 0 / 32 |
| final | observed | uncertain | reorder_point | service_unit_fill | 32 | +0.0331 | [+0.0132, +0.0548] | 14 / 2 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 30 | -1.9477 | [-2.7906, -1.2478] | 24 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 30 | +2.4144 | [+0.9044, +5.1605] | 0 / 30 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 30 | +0.1176 | [+0.0849, +0.1488] | 24 / 0 |
| final | observed | uncertain_fill_only | base_stock | shortage | 26 | -0.1938 | [-0.4487, +0.0084] | 10 / 2 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 26 | +1.3721 | [+0.2243, +3.4524] | 3 / 23 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 26 | +0.0075 | [+0.0008, +0.0161] | 10 / 2 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 33 | -0.2458 | [-0.4879, -0.0527] | 12 / 2 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 33 | +1.3459 | [+0.3748, +3.1159] | 1 / 32 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 33 | +0.0101 | [+0.0035, +0.0183] | 12 / 2 |
| final | recovered | stable | order_up_to | shortage | 39 | -2.5127 | [-3.5259, -1.6783] | 35 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 39 | +1.7164 | [+0.9949, +2.7487] | 0 / 39 |
| final | recovered | stable | order_up_to | service_unit_fill | 39 | +0.1630 | [+0.1332, +0.1934] | 35 / 0 |
| final | recovered | stable | base_stock | shortage | 36 | -0.1305 | [-0.2659, -0.0081] | 11 / 1 |
| final | recovered | stable | base_stock | avg_inventory_units | 36 | +0.2298 | [+0.0702, +0.4518] | 9 / 27 |
| final | recovered | stable | base_stock | service_unit_fill | 36 | +0.0060 | [-0.0035, +0.0166] | 11 / 1 |
| final | recovered | stable | reorder_point | shortage | 39 | -0.1610 | [-0.2897, -0.0504] | 11 / 1 |
| final | recovered | stable | reorder_point | avg_inventory_units | 39 | +0.2330 | [+0.0848, +0.4307] | 8 / 31 |
| final | recovered | stable | reorder_point | service_unit_fill | 39 | +0.0090 | [+0.0013, +0.0182] | 11 / 1 |
| final | recovered | uncertain | order_up_to | shortage | 30 | -2.5263 | [-3.6521, -1.5156] | 23 / 1 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 30 | +3.2906 | [+1.3476, +6.8454] | 0 / 30 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 30 | +0.1438 | [+0.0985, +0.1888] | 23 / 1 |
| final | recovered | uncertain | base_stock | shortage | 29 | -0.2792 | [-0.5375, -0.0693] | 9 / 2 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 29 | +1.8412 | [+0.5361, +4.1574] | 1 / 28 |
| final | recovered | uncertain | base_stock | service_unit_fill | 29 | +0.0167 | [+0.0041, +0.0312] | 9 / 2 |
| final | recovered | uncertain | reorder_point | shortage | 34 | -0.2873 | [-0.5478, -0.0785] | 11 / 1 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 34 | +1.8659 | [+0.6537, +4.0788] | 1 / 33 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 34 | +0.0170 | [+0.0038, +0.0328] | 11 / 1 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 35 | -2.2389 | [-3.2547, -1.4374] | 29 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 35 | +2.6982 | [+1.2325, +5.1372] | 0 / 35 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 35 | +0.1381 | [+0.1035, +0.1740] | 29 / 0 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 30 | -0.0440 | [-0.3642, +0.2585] | 7 / 3 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 30 | +1.1691 | [+0.2371, +2.6211] | 6 / 24 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 30 | -0.0002 | [-0.0135, +0.0102] | 7 / 3 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 37 | -0.1414 | [-0.4197, +0.1129] | 10 / 3 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 37 | +1.2675 | [+0.4230, +2.6532] | 3 / 34 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 37 | +0.0091 | [-0.0011, +0.0200] | 10 / 3 |
| val1 | observed | stable | order_up_to | shortage | 22 | -5.6877 | [-9.0931, -3.6017] | 22 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 22 | +1.8306 | [+1.0315, +3.1287] | 0 / 22 |
| val1 | observed | stable | order_up_to | service_unit_fill | 22 | +0.1643 | [+0.1330, +0.1952] | 22 / 0 |
| val1 | observed | stable | base_stock | shortage | 20 | -0.2413 | [-0.4567, -0.0662] | 12 / 1 |
| val1 | observed | stable | base_stock | avg_inventory_units | 20 | +0.4763 | [+0.2151, +0.8194] | 1 / 19 |
| val1 | observed | stable | base_stock | service_unit_fill | 20 | +0.0060 | [+0.0004, +0.0121] | 12 / 1 |
| val1 | observed | stable | reorder_point | shortage | 25 | -0.2062 | [-0.3738, -0.0702] | 15 / 2 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 25 | +0.4579 | [+0.2324, +0.7559] | 1 / 24 |
| val1 | observed | stable | reorder_point | service_unit_fill | 25 | +0.0075 | [+0.0017, +0.0137] | 15 / 2 |
| val1 | observed | uncertain | order_up_to | shortage | 13 | -13.1161 | [-25.1658, -5.8168] | 13 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 13 | +7.8312 | [+2.7234, +16.8162] | 0 / 13 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 13 | +0.2050 | [+0.1693, +0.2399] | 13 / 0 |
| val1 | observed | uncertain | base_stock | shortage | 15 | -4.0574 | [-7.1313, -1.8575] | 14 / 0 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 15 | +5.4000 | [+1.6955, +12.0760] | 0 / 15 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 15 | +0.0734 | [+0.0495, +0.0994] | 14 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 18 | -3.8905 | [-7.3079, -1.6220] | 16 / 0 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 18 | +4.8048 | [+1.5384, +10.5506] | 0 / 18 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 18 | +0.0751 | [+0.0537, +0.0991] | 16 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 12 | -6.3904 | [-11.0682, -3.5769] | 12 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 12 | +7.1488 | [+2.6596, +14.4375] | 0 / 12 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 12 | +0.1172 | [+0.0875, +0.1471] | 12 / 0 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 12 | -0.4942 | [-0.8359, -0.2134] | 8 / 0 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 12 | +4.9913 | [+1.6842, +9.8028] | 0 / 12 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 12 | +0.0171 | [+0.0075, +0.0277] | 8 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 15 | -0.6187 | [-0.9959, -0.3006] | 10 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 15 | +4.5506 | [+1.6837, +9.2234] | 0 / 15 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 15 | +0.0210 | [+0.0097, +0.0328] | 10 / 0 |
| val1 | recovered | stable | order_up_to | shortage | 28 | -5.7053 | [-9.6294, -3.3384] | 28 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 28 | +1.9428 | [+1.1579, +3.3635] | 0 / 28 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 28 | +0.1559 | [+0.1330, +0.1796] | 28 / 0 |
| val1 | recovered | stable | base_stock | shortage | 25 | -0.2901 | [-0.6567, -0.0483] | 15 / 0 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 25 | +0.5226 | [+0.1965, +1.0944] | 0 / 25 |
| val1 | recovered | stable | base_stock | service_unit_fill | 25 | +0.0044 | [+0.0014, +0.0086] | 15 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 29 | -0.2758 | [-0.5786, -0.0663] | 17 / 0 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 29 | +0.4959 | [+0.2120, +1.0021] | 0 / 29 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 29 | +0.0059 | [+0.0024, +0.0101] | 17 / 0 |
| val1 | recovered | uncertain | order_up_to | shortage | 12 | -18.1244 | [-37.2607, -6.8011] | 12 / 0 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 12 | +10.1060 | [+3.5736, +21.8363] | 0 / 12 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 12 | +0.2048 | [+0.1661, +0.2413] | 12 / 0 |
| val1 | recovered | uncertain | base_stock | shortage | 11 | -8.0550 | [-17.4939, -2.4073] | 10 / 1 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 11 | +8.4292 | [+2.3840, +19.2740] | 0 / 11 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 11 | +0.0704 | [+0.0410, +0.0958] | 10 / 1 |
| val1 | recovered | uncertain | reorder_point | shortage | 12 | -8.2593 | [-17.9051, -2.3429] | 10 / 1 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 12 | +8.1619 | [+2.5207, +18.2185] | 0 / 12 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 12 | +0.0725 | [+0.0441, +0.0989] | 10 / 1 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 11 | -8.9063 | [-16.6562, -4.0630] | 11 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 11 | +8.1063 | [+3.4695, +15.7178] | 0 / 11 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 11 | +0.1285 | [+0.0827, +0.1811] | 11 / 0 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 10 | -1.0087 | [-2.2836, +0.2442] | 6 / 1 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 10 | +5.6694 | [+1.9313, +11.5557] | 0 / 10 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 10 | +0.0268 | [-0.0006, +0.0568] | 6 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 12 | -1.0600 | [-2.3290, +0.0804] | 6 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 12 | +5.2936 | [+1.9669, +10.6395] | 0 / 12 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 12 | +0.0291 | [+0.0014, +0.0630] | 6 / 1 |
| val2 | observed | stable | order_up_to | shortage | 25 | -6.0360 | [-11.6086, -2.8747] | 25 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 25 | +1.5149 | [+0.8762, +2.5938] | 0 / 25 |
| val2 | observed | stable | order_up_to | service_unit_fill | 25 | +0.1370 | [+0.1169, +0.1551] | 25 / 0 |
| val2 | observed | stable | base_stock | shortage | 25 | -0.1607 | [-0.3200, -0.0405] | 14 / 0 |
| val2 | observed | stable | base_stock | avg_inventory_units | 25 | +0.3632 | [+0.1321, +0.7388] | 1 / 24 |
| val2 | observed | stable | base_stock | service_unit_fill | 25 | +0.0042 | [+0.0017, +0.0074] | 14 / 0 |
| val2 | observed | stable | reorder_point | shortage | 25 | -0.2286 | [-0.4035, -0.0932] | 16 / 0 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 25 | +0.3692 | [+0.1383, +0.7406] | 0 / 25 |
| val2 | observed | stable | reorder_point | service_unit_fill | 25 | +0.0070 | [+0.0032, +0.0115] | 16 / 0 |
| val2 | observed | uncertain | order_up_to | shortage | 8 | -22.5681 | [-50.4957, -6.8427] | 8 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 8 | +7.4711 | [+3.1854, +13.8612] | 0 / 8 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 8 | +0.2158 | [+0.1715, +0.2563] | 8 / 0 |
| val2 | observed | uncertain | base_stock | shortage | 8 | -7.9720 | [-17.7892, -1.4820] | 5 / 0 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 8 | +5.8541 | [+2.3792, +10.8491] | 0 / 8 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 8 | +0.0715 | [+0.0262, +0.1203] | 5 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 9 | -7.9556 | [-18.8714, -1.1885] | 6 / 1 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 9 | +5.7745 | [+2.4049, +10.7739] | 0 / 9 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 9 | +0.0543 | [-0.0035, +0.1060] | 6 / 1 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 13 | -8.3464 | [-18.2742, -2.3573] | 13 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 13 | +5.4103 | [+2.1841, +10.3556] | 0 / 13 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 13 | +0.1044 | [+0.0764, +0.1325] | 13 / 0 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 11 | -1.6337 | [-3.0737, -0.4918] | 6 / 0 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 11 | +4.5576 | [+1.5862, +8.8579] | 0 / 11 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 11 | +0.0237 | [+0.0065, +0.0458] | 6 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 14 | -1.6172 | [-3.2952, -0.2885] | 7 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 14 | +4.0651 | [+1.4831, +8.1314] | 0 / 14 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 14 | +0.0219 | [+0.0066, +0.0424] | 7 / 0 |
| val2 | recovered | stable | order_up_to | shortage | 32 | -6.1215 | [-10.3357, -3.5777] | 32 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 32 | +2.1064 | [+1.2968, +3.2810] | 0 / 32 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 32 | +0.1607 | [+0.1364, +0.1845] | 32 / 0 |
| val2 | recovered | stable | base_stock | shortage | 28 | -0.7303 | [-1.6059, -0.1653] | 18 / 0 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 28 | +0.5816 | [+0.2521, +1.0438] | 1 / 27 |
| val2 | recovered | stable | base_stock | service_unit_fill | 28 | +0.0109 | [+0.0046, +0.0189] | 18 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 32 | -0.7401 | [-1.6191, -0.2343] | 22 / 0 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 32 | +0.5716 | [+0.2729, +0.9832] | 1 / 31 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 32 | +0.0143 | [+0.0070, +0.0227] | 22 / 0 |
| val2 | recovered | uncertain | order_up_to | shortage | 14 | -17.9147 | [-41.2916, -4.8080] | 13 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 14 | +7.3368 | [+3.4299, +13.5119] | 0 / 14 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 14 | +0.1717 | [+0.1190, +0.2200] | 13 / 0 |
| val2 | recovered | uncertain | base_stock | shortage | 9 | -9.2077 | [-24.6361, -0.7613] | 5 / 0 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 9 | +7.0540 | [+2.4790, +14.3978] | 0 / 9 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 9 | +0.0385 | [+0.0120, +0.0674] | 5 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 17 | -6.8700 | [-16.6672, -1.3923] | 12 / 0 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 17 | +5.0613 | [+2.3099, +9.4622] | 0 / 17 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 17 | +0.0709 | [+0.0379, +0.1169] | 12 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 15 | -7.5991 | [-14.5473, -3.2545] | 15 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 15 | +5.0663 | [+2.5120, +8.8468] | 0 / 15 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 15 | +0.1232 | [+0.0925, +0.1581] | 15 / 0 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 9 | -0.8843 | [-2.2399, +0.1852] | 4 / 1 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 9 | +4.0925 | [+1.5485, +7.5201] | 0 / 9 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 9 | +0.0208 | [+0.0025, +0.0458] | 4 / 1 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 16 | -0.7865 | [-1.7587, +0.2309] | 10 / 2 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 16 | +3.2672 | [+1.5766, +5.7924] | 0 / 16 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 16 | +0.0038 | [-0.0340, +0.0316] | 10 / 2 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 447/900 complete, 453 infeasible, 0 abstained; gated: 436/900 complete, 0 infeasible, 464 abstained; order_up_to: 642/900 complete, 258 infeasible, 0 abstained; reorder_point: 900/900 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 1175
- ZAAD runs that retained the incumbent proxy on at least one review: 843 of 900 (4305 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/uncertain store 514 product 267: ZAAD minus base_stock = +26.657 (fill 0.922 vs 0.869, inventory 69.00 vs 20.64, retained incumbent on 3 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +22.011 (fill 0.922 vs 0.922, inventory 50.57 vs 20.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 514 product 267: ZAAD minus order_up_to = +21.817 (fill 0.912 vs 0.822, inventory 36.46 vs 8.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain store 230 product 580: ZAAD minus order_up_to = +12.055 (fill 0.755 vs 0.648, inventory 19.59 vs 5.30, retained incumbent on 10 reviews)
- val2/recovered/uncertain_fill_only store 230 product 580: ZAAD minus order_up_to = +12.014 (fill 0.796 vs 0.718, inventory 14.09 vs 3.53, retained incumbent on 8 reviews)
- val2/observed/uncertain_fill_only store 514 product 267: ZAAD minus order_up_to = +8.993 (fill 0.985 vs 0.833, inventory 36.58 vs 4.52, retained incumbent on 2 reviews)
- val1/observed/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +8.729 (fill 0.917 vs 0.883, inventory 8.08 vs 1.08, retained incumbent on 4 reviews)
- final/recovered/uncertain store 514 product 267: ZAAD minus order_up_to = +8.703 (fill 0.954 vs 0.954, inventory 68.14 vs 17.32, retained incumbent on 2 reviews)
- val1/observed/uncertain store 869 product 191: ZAAD minus reorder_point = +7.826 (fill 0.917 vs 0.917, inventory 6.82 vs 2.20, retained incumbent on 5 reviews)
- final/observed/uncertain store 514 product 267: ZAAD minus order_up_to = +7.713 (fill 0.898 vs 0.898, inventory 65.03 vs 17.53, retained incumbent on 2 reviews)
