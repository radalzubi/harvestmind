# FreshRetailNet: before/after comparison across pilot stages

Same 50 series, windows and supply draws in every stage. `original` is PR #114's frozen run (uncapped history, 1e6 line caps, no incumbent rule, summarised then on realized cost); the later stages are the corrected benchmark and its predeclared variants. Every figure is a modelled index under declared SYNTHETIC supply; nothing is a realized saving.

## Within-stage: ZAAD vs reorder_point per cell

| stage | window | track | scenario | ZAAD complete | ZAAD cont. | ZAAD fill | ZAAD inv | ZAAD own share | RP complete | RP cont. | RP fill | paired mean diff | 95 % bootstrap | better / worse |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| original | final | observed | stable | 35/50 | 13.167 | 0.983 | 2.65 |  | 50 | 10.380 | 0.977 | -0.048 (35) | [-0.096, -0.005] | 16 / 19 |
| original | final | observed | uncertain | 32/50 | 16.581 | 0.901 | 3.68 |  | 50 | 12.371 | 0.881 | +0.035 (32) | [-0.277, +0.339] | 16 / 16 |
| original | final | observed | uncertain_fill_only | 33/50 | 15.033 | 0.950 | 3.53 |  | 50 | 11.684 | 0.947 | -0.296 (33) | [-0.816, +0.054] | 17 / 16 |
| original | final | recovered | stable | 39/50 | 13.471 | 0.983 | 2.76 |  | 50 | 11.384 | 0.972 | -0.053 (39) | [-0.097, -0.016] | 19 / 20 |
| original | final | recovered | uncertain | 34/50 | 17.525 | 0.913 | 4.13 |  | 50 | 13.586 | 0.889 | +0.307 (34) | [+0.100, +0.530] | 15 / 19 |
| original | final | recovered | uncertain_fill_only | 37/50 | 15.178 | 0.962 | 4.02 |  | 50 | 12.669 | 0.953 | -0.141 (37) | [-0.646, +0.193] | 20 / 17 |
| original | val1 | observed | stable | 25/50 | 28.251 | 0.981 | 2.28 |  | 50 | 18.250 | 0.956 | -0.064 (25) | [-0.118, -0.019] | 15 / 10 |
| original | val1 | observed | uncertain | 18/50 | 42.481 | 0.912 | 7.15 |  | 50 | 21.268 | 0.887 | +1.689 (18) | [-0.068, +4.175] | 9 / 9 |
| original | val1 | observed | uncertain_fill_only | 15/50 | 46.166 | 0.951 | 7.21 |  | 50 | 20.722 | 0.922 | +1.419 (15) | [+0.133, +3.047] | 5 / 10 |
| original | val1 | recovered | stable | 29/50 | 30.344 | 0.969 | 2.61 |  | 50 | 22.097 | 0.953 | -0.088 (29) | [-0.183, -0.020] | 17 / 12 |
| original | val1 | recovered | uncertain | 12/50 | 65.459 | 0.943 | 11.74 |  | 50 | 25.652 | 0.904 | -1.256 (12) | [-5.489, +1.461] | 7 / 5 |
| original | val1 | recovered | uncertain_fill_only | 12/50 | 63.913 | 0.959 | 9.01 |  | 50 | 24.830 | 0.931 | +0.473 (12) | [-0.424, +1.524] | 5 / 7 |
| original | val2 | observed | stable | 25/50 | 28.551 | 0.982 | 2.13 |  | 50 | 18.228 | 0.965 | -0.073 (25) | [-0.128, -0.028] | 16 / 9 |
| original | val2 | observed | uncertain | 9/50 | 65.316 | 0.942 | 8.20 |  | 50 | 21.499 | 0.897 | -0.356 (9) | [-3.587, +2.254] | 5 / 4 |
| original | val2 | observed | uncertain_fill_only | 14/50 | 49.122 | 0.975 | 6.22 |  | 50 | 21.371 | 0.937 | +0.588 (14) | [-0.335, +1.644] | 5 / 9 |
| original | val2 | recovered | stable | 33/50 | 31.097 | 0.960 | 2.97 |  | 50 | 23.348 | 0.946 | -0.153 (32) | [-0.459, +0.108] | 21 / 11 |
| original | val2 | recovered | uncertain | 18/50 | 53.933 | 0.942 | 8.31 |  | 50 | 27.126 | 0.895 | +0.569 (17) | [-1.966, +2.648] | 6 / 11 |
| original | val2 | recovered | uncertain_fill_only | 16/50 | 56.166 | 0.932 | 6.52 |  | 50 | 27.055 | 0.932 | +2.280 (16) | [+0.688, +4.258] | 1 / 15 |
| reference_v1 | final | observed | stable | 50/50 | 10.179 | 0.985 | 2.07 | 0.29 | 50 | 10.214 | 0.978 | -0.035 (50) | [-0.067, -0.011] | 28 / 22 |
| reference_v1 | final | observed | uncertain | 50/50 | 12.193 | 0.910 | 2.76 | 0.52 | 50 | 12.173 | 0.881 | +0.020 (50) | [-0.177, +0.220] | 24 / 26 |
| reference_v1 | final | observed | uncertain_fill_only | 50/50 | 11.334 | 0.957 | 2.73 | 0.54 | 50 | 11.487 | 0.947 | -0.153 (50) | [-0.509, +0.083] | 24 / 26 |
| reference_v1 | final | observed | uncertain_lead_only | 50/50 | 10.769 | 0.919 | 2.42 | 0.54 | 50 | 10.891 | 0.895 | -0.122 (50) | [-0.248, -0.026] | 25 / 25 |
| reference_v1 | final | recovered | stable | 50/50 | 11.333 | 0.979 | 2.39 | 0.30 | 50 | 11.371 | 0.971 | -0.037 (50) | [-0.076, +0.001] | 25 / 25 |
| reference_v1 | final | recovered | uncertain | 50/50 | 13.760 | 0.910 | 3.24 | 0.50 | 50 | 13.547 | 0.889 | +0.213 (50) | [+0.059, +0.374] | 24 / 26 |
| reference_v1 | final | recovered | uncertain_fill_only | 50/50 | 12.557 | 0.962 | 3.31 | 0.51 | 50 | 12.643 | 0.953 | -0.086 (50) | [-0.449, +0.161] | 28 / 22 |
| reference_v1 | final | recovered | uncertain_lead_only | 50/50 | 11.795 | 0.928 | 2.79 | 0.51 | 50 | 11.916 | 0.908 | -0.121 (50) | [-0.255, -0.021] | 28 / 22 |
| reference_v1 | val1 | observed | stable | 50/50 | 18.208 | 0.968 | 1.68 | 0.15 | 50 | 18.250 | 0.956 | -0.042 (50) | [-0.095, +0.014] | 27 / 23 |
| reference_v1 | val1 | observed | uncertain | 50/50 | 22.132 | 0.946 | 3.84 | 0.48 | 50 | 21.268 | 0.887 | +0.864 (50) | [+0.199, +1.826] | 20 / 30 |
| reference_v1 | val1 | observed | uncertain_fill_only | 50/50 | 21.386 | 0.953 | 3.63 | 0.57 | 50 | 20.722 | 0.922 | +0.664 (50) | [+0.226, +1.200] | 21 / 29 |
| reference_v1 | val1 | observed | uncertain_lead_only | 50/50 | 18.891 | 0.932 | 2.95 | 0.46 | 50 | 18.995 | 0.873 | -0.104 (50) | [-0.283, +0.093] | 34 / 16 |
| reference_v1 | val1 | recovered | stable | 50/50 | 22.059 | 0.960 | 2.18 | 0.16 | 50 | 22.097 | 0.953 | -0.037 (50) | [-0.106, +0.030] | 26 / 24 |
| reference_v1 | val1 | recovered | uncertain | 50/50 | 25.958 | 0.940 | 4.70 | 0.48 | 50 | 25.652 | 0.904 | +0.306 (50) | [-0.873, +1.071] | 19 / 31 |
| reference_v1 | val1 | recovered | uncertain_fill_only | 50/50 | 25.667 | 0.953 | 4.20 | 0.53 | 50 | 24.830 | 0.931 | +0.837 (50) | [+0.411, +1.287] | 18 / 32 |
| reference_v1 | val1 | recovered | uncertain_lead_only | 50/50 | 22.621 | 0.940 | 3.56 | 0.43 | 50 | 22.766 | 0.897 | -0.145 (50) | [-0.597, +0.211] | 26 / 24 |
| reference_v1 | val2 | observed | stable | 50/50 | 18.171 | 0.973 | 1.60 | 0.16 | 50 | 18.238 | 0.960 | -0.067 (50) | [-0.113, -0.029] | 29 / 21 |
| reference_v1 | val2 | observed | uncertain | 50/50 | 21.612 | 0.944 | 3.23 | 0.52 | 50 | 21.476 | 0.893 | +0.136 (50) | [-0.519, +0.624] | 22 / 28 |
| reference_v1 | val2 | observed | uncertain_fill_only | 50/50 | 22.098 | 0.957 | 3.27 | 0.59 | 50 | 21.355 | 0.935 | +0.743 (50) | [+0.287, +1.261] | 18 / 32 |
| reference_v1 | val2 | observed | uncertain_lead_only | 50/50 | 18.652 | 0.930 | 2.87 | 0.44 | 50 | 18.789 | 0.887 | -0.137 (50) | [-0.402, +0.149] | 27 / 23 |
| reference_v1 | val2 | recovered | stable | 50/50 | 22.990 | 0.957 | 2.35 | 0.17 | 50 | 23.081 | 0.940 | -0.090 (50) | [-0.293, +0.083] | 32 / 18 |
| reference_v1 | val2 | recovered | uncertain | 50/50 | 27.182 | 0.947 | 4.48 | 0.51 | 50 | 26.729 | 0.892 | +0.452 (50) | [-0.398, +1.215] | 19 / 31 |
| reference_v1 | val2 | recovered | uncertain_fill_only | 50/50 | 27.930 | 0.955 | 3.94 | 0.54 | 50 | 26.716 | 0.928 | +1.214 (50) | [+0.584, +1.951] | 15 / 35 |
| reference_v1 | val2 | recovered | uncertain_lead_only | 50/50 | 23.395 | 0.928 | 3.68 | 0.42 | 50 | 23.708 | 0.878 | -0.313 (50) | [-0.962, +0.189] | 31 / 19 |
| corrected | final | observed | stable | 50/50 | 10.214 | 0.978 | 1.60 | 0.11 | 50 | 10.214 | 0.978 | +0.001 (50) | [-0.008, +0.011] | 16 / 7 |
| corrected | final | observed | uncertain | 50/50 | 12.124 | 0.887 | 1.94 | 0.30 | 50 | 12.173 | 0.881 | -0.049 (50) | [-0.217, +0.083] | 25 / 21 |
| corrected | final | observed | uncertain_fill_only | 50/50 | 11.348 | 0.951 | 2.37 | 0.34 | 50 | 11.487 | 0.947 | -0.139 (50) | [-0.491, +0.094] | 25 / 21 |
| corrected | final | observed | uncertain_lead_only | 50/50 | 10.853 | 0.903 | 1.55 | 0.32 | 50 | 10.891 | 0.895 | -0.038 (50) | [-0.082, -0.003] | 33 / 11 |
| corrected | final | recovered | stable | 50/50 | 11.363 | 0.975 | 2.22 | 0.13 | 50 | 11.371 | 0.971 | -0.007 (50) | [-0.032, +0.016] | 18 / 8 |
| corrected | final | recovered | uncertain | 50/50 | 13.554 | 0.898 | 2.36 | 0.31 | 50 | 13.547 | 0.889 | +0.008 (50) | [-0.160, +0.214] | 25 / 22 |
| corrected | final | recovered | uncertain_fill_only | 50/50 | 12.500 | 0.956 | 3.10 | 0.35 | 50 | 12.643 | 0.953 | -0.143 (50) | [-0.494, +0.092] | 29 / 19 |
| corrected | final | recovered | uncertain_lead_only | 50/50 | 11.897 | 0.910 | 1.99 | 0.34 | 50 | 11.916 | 0.908 | -0.020 (50) | [-0.057, +0.010] | 32 / 13 |
| corrected | val1 | observed | stable | 50/50 | 18.234 | 0.961 | 1.41 | 0.08 | 50 | 18.250 | 0.956 | -0.017 (50) | [-0.039, +0.002] | 6 / 27 |
| corrected | val1 | observed | uncertain | 50/50 | 21.212 | 0.924 | 2.31 | 0.44 | 50 | 21.268 | 0.887 | -0.057 (50) | [-0.284, +0.182] | 29 / 20 |
| corrected | val1 | observed | uncertain_fill_only | 50/50 | 21.189 | 0.938 | 3.30 | 0.47 | 50 | 20.722 | 0.922 | +0.467 (50) | [+0.085, +0.958] | 22 / 28 |
| corrected | val1 | observed | uncertain_lead_only | 50/50 | 18.937 | 0.908 | 2.18 | 0.44 | 50 | 18.995 | 0.873 | -0.058 (50) | [-0.196, +0.109] | 29 / 21 |
| corrected | val1 | recovered | stable | 50/50 | 22.073 | 0.954 | 1.86 | 0.07 | 50 | 22.097 | 0.953 | -0.024 (50) | [-0.074, +0.004] | 6 / 22 |
| corrected | val1 | recovered | uncertain | 50/50 | 25.156 | 0.929 | 3.24 | 0.43 | 50 | 25.652 | 0.904 | -0.496 (50) | [-2.100, +0.444] | 21 / 27 |
| corrected | val1 | recovered | uncertain_fill_only | 50/50 | 25.098 | 0.944 | 3.63 | 0.40 | 50 | 24.830 | 0.931 | +0.268 (50) | [-0.050, +0.599] | 22 / 27 |
| corrected | val1 | recovered | uncertain_lead_only | 50/50 | 22.734 | 0.921 | 2.54 | 0.44 | 50 | 22.766 | 0.897 | -0.032 (50) | [-0.177, +0.137] | 23 / 27 |
| corrected | val2 | observed | stable | 50/50 | 18.226 | 0.966 | 1.38 | 0.08 | 50 | 18.238 | 0.960 | -0.012 (50) | [-0.032, +0.002] | 10 / 24 |
| corrected | val2 | observed | uncertain | 50/50 | 21.805 | 0.922 | 2.62 | 0.47 | 50 | 21.476 | 0.893 | +0.329 (50) | [+0.037, +0.694] | 23 / 27 |
| corrected | val2 | observed | uncertain_fill_only | 50/50 | 21.495 | 0.955 | 2.74 | 0.48 | 50 | 21.355 | 0.935 | +0.139 (50) | [-0.235, +0.537] | 24 / 26 |
| corrected | val2 | observed | uncertain_lead_only | 50/50 | 18.672 | 0.912 | 2.24 | 0.45 | 50 | 18.789 | 0.887 | -0.117 (50) | [-0.260, +0.029] | 22 / 28 |
| corrected | val2 | recovered | stable | 50/50 | 23.000 | 0.947 | 2.09 | 0.07 | 50 | 23.081 | 0.940 | -0.081 (50) | [-0.254, +0.026] | 8 / 22 |
| corrected | val2 | recovered | uncertain | 50/50 | 26.758 | 0.934 | 3.46 | 0.42 | 50 | 26.729 | 0.892 | +0.029 (50) | [-0.632, +0.624] | 31 / 19 |
| corrected | val2 | recovered | uncertain_fill_only | 50/50 | 27.081 | 0.943 | 3.10 | 0.44 | 50 | 26.716 | 0.928 | +0.364 (50) | [-0.218, +0.916] | 17 / 31 |
| corrected | val2 | recovered | uncertain_lead_only | 50/50 | 23.309 | 0.910 | 2.74 | 0.44 | 50 | 23.708 | 0.878 | -0.399 (50) | [-0.993, -0.036] | 28 / 20 |
| target_90 | final | observed | stable | 50/50 | 10.278 | 0.960 | 1.34 | 0.09 | 50 | 10.278 | 0.960 | +0.001 (50) | [-0.000, +0.003] | 14 / 4 |
| target_90 | final | observed | uncertain | 50/50 | 12.185 | 0.868 | 1.79 | 0.37 | 50 | 12.191 | 0.857 | -0.006 (50) | [-0.189, +0.200] | 26 / 21 |
| target_90 | final | observed | uncertain_fill_only | 50/50 | 11.297 | 0.937 | 2.20 | 0.42 | 50 | 11.507 | 0.930 | -0.210 (50) | [-0.542, +0.015] | 26 / 22 |
| target_90 | final | observed | uncertain_lead_only | 50/50 | 10.897 | 0.892 | 1.39 | 0.38 | 50 | 10.945 | 0.881 | -0.048 (50) | [-0.108, +0.003] | 30 / 17 |
| target_90 | final | recovered | stable | 50/50 | 11.447 | 0.959 | 1.84 | 0.12 | 50 | 11.457 | 0.955 | -0.010 (50) | [-0.040, +0.015] | 17 / 11 |
| target_90 | final | recovered | uncertain | 50/50 | 13.641 | 0.877 | 2.16 | 0.40 | 50 | 13.528 | 0.871 | +0.113 (50) | [-0.041, +0.339] | 24 / 24 |
| target_90 | final | recovered | uncertain_fill_only | 50/50 | 12.600 | 0.943 | 2.89 | 0.42 | 50 | 12.665 | 0.937 | -0.064 (50) | [-0.417, +0.204] | 24 / 23 |
| target_90 | final | recovered | uncertain_lead_only | 50/50 | 11.962 | 0.900 | 1.74 | 0.39 | 50 | 12.013 | 0.889 | -0.051 (50) | [-0.101, -0.012] | 33 / 13 |
| target_90 | val1 | observed | stable | 50/50 | 18.328 | 0.942 | 1.17 | 0.08 | 50 | 18.344 | 0.938 | -0.016 (50) | [-0.041, +0.003] | 8 / 19 |
| target_90 | val1 | observed | uncertain | 50/50 | 21.018 | 0.921 | 2.79 | 0.56 | 50 | 21.433 | 0.861 | -0.415 (50) | [-1.288, +0.110] | 28 / 21 |
| target_90 | val1 | observed | uncertain_fill_only | 50/50 | 21.134 | 0.935 | 2.89 | 0.59 | 50 | 20.772 | 0.904 | +0.362 (50) | [+0.094, +0.661] | 23 / 27 |
| target_90 | val1 | observed | uncertain_lead_only | 50/50 | 18.971 | 0.901 | 1.95 | 0.51 | 50 | 19.149 | 0.850 | -0.179 (50) | [-0.331, +0.002] | 36 / 14 |
| target_90 | val1 | recovered | stable | 50/50 | 22.230 | 0.938 | 1.54 | 0.07 | 50 | 22.229 | 0.936 | +0.001 (50) | [-0.016, +0.021] | 9 / 17 |
| target_90 | val1 | recovered | uncertain | 50/50 | 26.691 | 0.933 | 3.89 | 0.57 | 50 | 25.853 | 0.878 | +0.839 (50) | [-0.137, +2.619] | 23 / 27 |
| target_90 | val1 | recovered | uncertain_fill_only | 50/50 | 25.988 | 0.939 | 4.05 | 0.54 | 50 | 24.860 | 0.912 | +1.128 (50) | [+0.194, +2.569] | 20 / 29 |
| target_90 | val1 | recovered | uncertain_lead_only | 50/50 | 22.845 | 0.915 | 2.56 | 0.51 | 50 | 22.929 | 0.875 | -0.084 (50) | [-0.305, +0.162] | 30 / 20 |
| target_90 | val2 | observed | stable | 50/50 | 18.314 | 0.947 | 1.12 | 0.05 | 50 | 18.314 | 0.946 | +0.000 (50) | [-0.008, +0.009] | 3 / 16 |
| target_90 | val2 | observed | uncertain | 50/50 | 21.564 | 0.922 | 2.50 | 0.61 | 50 | 21.617 | 0.869 | -0.053 (50) | [-0.764, +0.468] | 26 / 24 |
| target_90 | val2 | observed | uncertain_fill_only | 50/50 | 21.772 | 0.948 | 2.68 | 0.60 | 50 | 21.344 | 0.921 | +0.428 (50) | [-0.068, +1.102] | 21 / 28 |
| target_90 | val2 | observed | uncertain_lead_only | 50/50 | 18.765 | 0.901 | 2.05 | 0.53 | 50 | 18.946 | 0.867 | -0.181 (50) | [-0.314, -0.062] | 30 / 20 |
| target_90 | val2 | recovered | stable | 50/50 | 23.229 | 0.925 | 1.69 | 0.06 | 50 | 23.221 | 0.919 | +0.008 (50) | [-0.048, +0.088] | 11 / 13 |
| target_90 | val2 | recovered | uncertain | 50/50 | 26.924 | 0.920 | 2.95 | 0.57 | 50 | 26.843 | 0.866 | +0.081 (50) | [-0.558, +0.645] | 24 / 26 |
| target_90 | val2 | recovered | uncertain_fill_only | 50/50 | 27.165 | 0.933 | 3.48 | 0.55 | 50 | 26.719 | 0.912 | +0.446 (50) | [+0.113, +0.804] | 19 / 31 |
| target_90 | val2 | recovered | uncertain_lead_only | 50/50 | 23.424 | 0.895 | 2.56 | 0.50 | 50 | 23.868 | 0.857 | -0.444 (50) | [-0.937, -0.095] | 30 / 19 |
| target_85 | final | observed | stable | 50/50 | 10.281 | 0.958 | 1.33 | 0.10 | 50 | 10.278 | 0.960 | +0.003 (50) | [-0.000, +0.009] | 16 / 6 |
| target_85 | final | observed | uncertain | 50/50 | 12.292 | 0.871 | 1.87 | 0.45 | 50 | 12.191 | 0.857 | +0.101 (50) | [-0.098, +0.374] | 28 / 18 |
| target_85 | final | observed | uncertain_fill_only | 50/50 | 11.237 | 0.942 | 2.28 | 0.51 | 50 | 11.507 | 0.930 | -0.270 (50) | [-0.603, -0.040] | 30 / 18 |
| target_85 | final | observed | uncertain_lead_only | 50/50 | 10.897 | 0.893 | 1.36 | 0.45 | 50 | 10.945 | 0.881 | -0.049 (50) | [-0.117, +0.009] | 34 / 13 |
| target_85 | final | recovered | stable | 50/50 | 11.479 | 0.950 | 1.80 | 0.13 | 50 | 11.457 | 0.955 | +0.022 (50) | [-0.000, +0.051] | 17 / 11 |
| target_85 | final | recovered | uncertain | 50/50 | 13.611 | 0.877 | 2.20 | 0.46 | 50 | 13.528 | 0.871 | +0.084 (50) | [-0.069, +0.279] | 26 / 23 |
| target_85 | final | recovered | uncertain_fill_only | 50/50 | 12.502 | 0.944 | 2.44 | 0.51 | 50 | 12.665 | 0.937 | -0.162 (50) | [-0.514, +0.084] | 26 / 24 |
| target_85 | final | recovered | uncertain_lead_only | 50/50 | 11.969 | 0.895 | 1.74 | 0.44 | 50 | 12.013 | 0.889 | -0.044 (50) | [-0.092, -0.005] | 33 / 13 |
| target_85 | val1 | observed | stable | 50/50 | 18.337 | 0.941 | 1.16 | 0.05 | 50 | 18.344 | 0.938 | -0.007 (50) | [-0.030, +0.009] | 4 / 15 |
| target_85 | val1 | observed | uncertain | 50/50 | 21.021 | 0.920 | 2.54 | 0.67 | 50 | 21.433 | 0.861 | -0.412 (50) | [-1.242, +0.130] | 28 / 21 |
| target_85 | val1 | observed | uncertain_fill_only | 50/50 | 21.399 | 0.933 | 2.99 | 0.68 | 50 | 20.772 | 0.904 | +0.627 (50) | [+0.202, +1.196] | 19 / 31 |
| target_85 | val1 | observed | uncertain_lead_only | 50/50 | 19.049 | 0.897 | 2.04 | 0.57 | 50 | 19.149 | 0.850 | -0.100 (50) | [-0.288, +0.131] | 35 / 15 |
| target_85 | val1 | recovered | stable | 50/50 | 22.229 | 0.938 | 1.50 | 0.04 | 50 | 22.229 | 0.936 | -0.001 (50) | [-0.009, +0.008] | 4 / 8 |
| target_85 | val1 | recovered | uncertain | 50/50 | 26.603 | 0.935 | 3.85 | 0.65 | 50 | 25.853 | 0.878 | +0.751 (50) | [-0.005, +2.073] | 22 / 28 |
| target_85 | val1 | recovered | uncertain_fill_only | 50/50 | 25.457 | 0.943 | 3.77 | 0.66 | 50 | 24.860 | 0.912 | +0.597 (50) | [+0.253, +0.950] | 17 / 33 |
| target_85 | val1 | recovered | uncertain_lead_only | 50/50 | 22.796 | 0.919 | 2.76 | 0.55 | 50 | 22.929 | 0.875 | -0.133 (50) | [-0.350, +0.114] | 32 / 18 |
| target_85 | val2 | observed | stable | 50/50 | 18.313 | 0.947 | 1.12 | 0.03 | 50 | 18.314 | 0.946 | -0.000 (50) | [-0.009, +0.008] | 4 / 9 |
| target_85 | val2 | observed | uncertain | 50/50 | 21.720 | 0.912 | 2.38 | 0.68 | 50 | 21.617 | 0.869 | +0.103 (50) | [-0.219, +0.407] | 24 / 26 |
| target_85 | val2 | observed | uncertain_fill_only | 50/50 | 21.465 | 0.945 | 2.56 | 0.65 | 50 | 21.344 | 0.921 | +0.121 (50) | [-0.250, +0.507] | 25 / 25 |
| target_85 | val2 | observed | uncertain_lead_only | 50/50 | 18.723 | 0.904 | 2.07 | 0.59 | 50 | 18.946 | 0.867 | -0.223 (50) | [-0.350, -0.107] | 31 / 19 |
| target_85 | val2 | recovered | stable | 50/50 | 23.211 | 0.923 | 1.67 | 0.04 | 50 | 23.221 | 0.919 | -0.010 (50) | [-0.023, +0.002] | 10 / 10 |
| target_85 | val2 | recovered | uncertain | 50/50 | 26.540 | 0.927 | 3.46 | 0.65 | 50 | 26.843 | 0.866 | -0.303 (50) | [-1.354, +0.371] | 29 / 21 |
| target_85 | val2 | recovered | uncertain_fill_only | 50/50 | 26.417 | 0.937 | 3.42 | 0.62 | 50 | 26.719 | 0.912 | -0.303 (50) | [-1.779, +0.574] | 25 / 25 |
| target_85 | val2 | recovered | uncertain_lead_only | 50/50 | 23.365 | 0.908 | 2.60 | 0.54 | 50 | 23.868 | 0.857 | -0.503 (50) | [-0.982, -0.180] | 33 / 17 |
| holding_x4 | final | observed | stable | 50/50 | 10.235 | 0.977 | 1.60 | 0.10 | 50 | 10.233 | 0.978 | +0.003 (50) | [-0.005, +0.013] | 15 / 7 |
| holding_x4 | final | observed | uncertain | 50/50 | 12.156 | 0.887 | 1.94 | 0.30 | 50 | 12.195 | 0.881 | -0.039 (50) | [-0.210, +0.090] | 25 / 21 |
| holding_x4 | final | observed | uncertain_fill_only | 50/50 | 11.348 | 0.949 | 2.38 | 0.34 | 50 | 11.512 | 0.947 | -0.164 (50) | [-0.485, +0.040] | 26 / 20 |
| holding_x4 | final | observed | uncertain_lead_only | 50/50 | 10.857 | 0.904 | 1.56 | 0.32 | 50 | 10.915 | 0.895 | -0.058 (50) | [-0.124, -0.007] | 33 / 11 |
| holding_x4 | final | recovered | stable | 50/50 | 11.390 | 0.975 | 2.22 | 0.13 | 50 | 11.397 | 0.971 | -0.007 (50) | [-0.032, +0.015] | 18 / 8 |
| holding_x4 | final | recovered | uncertain | 50/50 | 13.587 | 0.898 | 2.36 | 0.31 | 50 | 13.573 | 0.891 | +0.014 (50) | [-0.158, +0.230] | 26 / 21 |
| holding_x4 | final | recovered | uncertain_fill_only | 50/50 | 12.550 | 0.956 | 3.00 | 0.35 | 50 | 12.676 | 0.953 | -0.126 (50) | [-0.472, +0.098] | 30 / 18 |
| holding_x4 | final | recovered | uncertain_lead_only | 50/50 | 11.925 | 0.910 | 1.99 | 0.34 | 50 | 11.954 | 0.906 | -0.029 (50) | [-0.069, +0.003] | 32 / 13 |
| holding_x4 | val1 | observed | stable | 50/50 | 18.270 | 0.960 | 1.40 | 0.08 | 50 | 18.282 | 0.956 | -0.012 (50) | [-0.028, +0.001] | 5 / 25 |
| holding_x4 | val1 | observed | uncertain | 50/50 | 21.079 | 0.923 | 2.33 | 0.43 | 50 | 21.309 | 0.887 | -0.230 (50) | [-0.750, +0.144] | 27 / 22 |
| holding_x4 | val1 | observed | uncertain_fill_only | 50/50 | 21.233 | 0.939 | 3.20 | 0.47 | 50 | 20.764 | 0.922 | +0.469 (50) | [+0.059, +0.998] | 21 / 29 |
| holding_x4 | val1 | observed | uncertain_lead_only | 50/50 | 19.004 | 0.907 | 2.17 | 0.43 | 50 | 19.037 | 0.873 | -0.033 (50) | [-0.174, +0.139] | 29 / 21 |
| holding_x4 | val1 | recovered | stable | 50/50 | 22.117 | 0.954 | 1.86 | 0.07 | 50 | 22.139 | 0.953 | -0.022 (50) | [-0.072, +0.005] | 6 / 22 |
| holding_x4 | val1 | recovered | uncertain | 50/50 | 25.246 | 0.929 | 3.23 | 0.43 | 50 | 25.705 | 0.904 | -0.460 (50) | [-2.029, +0.472] | 20 / 28 |
| holding_x4 | val1 | recovered | uncertain_fill_only | 50/50 | 25.071 | 0.944 | 3.14 | 0.39 | 50 | 24.884 | 0.931 | +0.187 (50) | [-0.129, +0.508] | 22 / 27 |
| holding_x4 | val1 | recovered | uncertain_lead_only | 50/50 | 22.803 | 0.917 | 2.53 | 0.44 | 50 | 22.822 | 0.897 | -0.018 (50) | [-0.141, +0.112] | 21 / 29 |
| holding_x4 | val2 | observed | stable | 50/50 | 18.262 | 0.965 | 1.38 | 0.08 | 50 | 18.271 | 0.960 | -0.009 (50) | [-0.027, +0.004] | 9 / 25 |
| holding_x4 | val2 | observed | uncertain | 50/50 | 21.836 | 0.919 | 2.58 | 0.46 | 50 | 21.514 | 0.893 | +0.322 (50) | [+0.032, +0.687] | 20 / 30 |
| holding_x4 | val2 | observed | uncertain_fill_only | 50/50 | 21.508 | 0.954 | 2.59 | 0.46 | 50 | 21.395 | 0.935 | +0.113 (50) | [-0.183, +0.437] | 22 / 28 |
| holding_x4 | val2 | observed | uncertain_lead_only | 50/50 | 18.735 | 0.912 | 2.24 | 0.44 | 50 | 18.832 | 0.887 | -0.097 (50) | [-0.239, +0.051] | 22 / 28 |
| holding_x4 | val2 | recovered | stable | 50/50 | 23.123 | 0.946 | 2.00 | 0.06 | 50 | 23.127 | 0.940 | -0.004 (50) | [-0.043, +0.040] | 6 / 22 |
| holding_x4 | val2 | recovered | uncertain | 50/50 | 27.238 | 0.930 | 2.95 | 0.41 | 50 | 26.785 | 0.892 | +0.453 (50) | [-0.023, +1.045] | 30 / 20 |
| holding_x4 | val2 | recovered | uncertain_fill_only | 50/50 | 26.963 | 0.941 | 3.37 | 0.43 | 50 | 26.774 | 0.928 | +0.189 (50) | [-0.663, +0.815] | 16 / 32 |
| holding_x4 | val2 | recovered | uncertain_lead_only | 50/50 | 23.393 | 0.910 | 2.75 | 0.43 | 50 | 23.768 | 0.878 | -0.375 (50) | [-0.957, -0.019] | 24 / 24 |
| margin_x2 | final | observed | stable | 50/50 | 10.346 | 0.978 | 1.61 | 0.11 | 50 | 10.344 | 0.978 | +0.002 (50) | [-0.015, +0.023] | 15 / 9 |
| margin_x2 | final | observed | uncertain | 50/50 | 12.921 | 0.887 | 2.07 | 0.30 | 50 | 12.920 | 0.881 | +0.001 (50) | [-0.137, +0.139] | 24 / 21 |
| margin_x2 | final | observed | uncertain_fill_only | 50/50 | 11.780 | 0.950 | 2.51 | 0.33 | 50 | 11.890 | 0.947 | -0.110 (50) | [-0.444, +0.115] | 24 / 22 |
| margin_x2 | final | observed | uncertain_lead_only | 50/50 | 11.596 | 0.904 | 1.56 | 0.33 | 50 | 11.692 | 0.895 | -0.097 (50) | [-0.201, -0.013] | 33 / 11 |
| margin_x2 | final | recovered | stable | 50/50 | 11.469 | 0.975 | 2.22 | 0.11 | 50 | 11.488 | 0.971 | -0.020 (50) | [-0.067, +0.022] | 18 / 7 |
| margin_x2 | final | recovered | uncertain | 50/50 | 14.053 | 0.895 | 2.39 | 0.31 | 50 | 14.188 | 0.889 | -0.136 (50) | [-0.518, +0.178] | 28 / 19 |
| margin_x2 | final | recovered | uncertain_fill_only | 50/50 | 12.879 | 0.953 | 3.08 | 0.37 | 50 | 12.910 | 0.953 | -0.031 (50) | [-0.397, +0.254] | 27 / 21 |
| margin_x2 | final | recovered | uncertain_lead_only | 50/50 | 12.508 | 0.913 | 2.03 | 0.34 | 50 | 12.573 | 0.908 | -0.066 (50) | [-0.162, +0.003] | 31 / 14 |
| margin_x2 | val1 | observed | stable | 50/50 | 18.453 | 0.961 | 1.43 | 0.10 | 50 | 18.498 | 0.956 | -0.045 (50) | [-0.094, -0.004] | 8 / 26 |
| margin_x2 | val1 | observed | uncertain | 50/50 | 21.909 | 0.925 | 2.93 | 0.48 | 50 | 22.440 | 0.887 | -0.532 (50) | [-1.347, +0.043] | 31 / 18 |
| margin_x2 | val1 | observed | uncertain_fill_only | 50/50 | 21.815 | 0.941 | 3.24 | 0.47 | 50 | 21.377 | 0.922 | +0.438 (50) | [+0.111, +0.828] | 19 / 30 |
| margin_x2 | val1 | observed | uncertain_lead_only | 50/50 | 19.782 | 0.905 | 2.22 | 0.47 | 50 | 19.969 | 0.873 | -0.187 (50) | [-0.434, +0.096] | 26 / 24 |
| margin_x2 | val1 | recovered | stable | 50/50 | 22.401 | 0.954 | 1.87 | 0.08 | 50 | 22.451 | 0.953 | -0.050 (50) | [-0.153, +0.007] | 6 / 25 |
| margin_x2 | val1 | recovered | uncertain | 50/50 | 26.403 | 0.923 | 3.28 | 0.42 | 50 | 26.942 | 0.904 | -0.539 (50) | [-2.040, +0.395] | 22 / 26 |
| margin_x2 | val1 | recovered | uncertain_fill_only | 50/50 | 25.778 | 0.938 | 3.60 | 0.42 | 50 | 25.413 | 0.931 | +0.366 (50) | [-0.029, +0.768] | 17 / 31 |
| margin_x2 | val1 | recovered | uncertain_lead_only | 50/50 | 23.591 | 0.923 | 2.62 | 0.47 | 50 | 23.788 | 0.897 | -0.197 (50) | [-0.416, +0.022] | 24 / 26 |
| margin_x2 | val2 | observed | stable | 50/50 | 18.443 | 0.966 | 1.41 | 0.09 | 50 | 18.467 | 0.960 | -0.024 (50) | [-0.064, +0.003] | 10 / 25 |
| margin_x2 | val2 | observed | uncertain | 50/50 | 22.690 | 0.926 | 2.69 | 0.49 | 50 | 22.562 | 0.893 | +0.128 (50) | [-0.261, +0.559] | 25 / 25 |
| margin_x2 | val2 | observed | uncertain_fill_only | 50/50 | 22.309 | 0.960 | 2.88 | 0.49 | 50 | 21.835 | 0.935 | +0.473 (50) | [+0.010, +1.012] | 22 / 28 |
| margin_x2 | val2 | observed | uncertain_lead_only | 50/50 | 19.260 | 0.912 | 2.35 | 0.47 | 50 | 19.554 | 0.887 | -0.295 (50) | [-0.587, -0.034] | 24 / 26 |
| margin_x2 | val2 | recovered | stable | 50/50 | 23.735 | 0.947 | 2.02 | 0.08 | 50 | 23.781 | 0.940 | -0.046 (50) | [-0.118, +0.016] | 8 / 25 |
| margin_x2 | val2 | recovered | uncertain | 50/50 | 27.440 | 0.929 | 3.51 | 0.44 | 50 | 28.228 | 0.892 | -0.787 (50) | [-2.674, +0.447] | 29 / 21 |
| margin_x2 | val2 | recovered | uncertain_fill_only | 50/50 | 27.935 | 0.945 | 3.53 | 0.47 | 50 | 27.636 | 0.928 | +0.299 (50) | [-0.403, +0.946] | 21 / 28 |
| margin_x2 | val2 | recovered | uncertain_lead_only | 50/50 | 23.994 | 0.911 | 2.91 | 0.45 | 50 | 24.966 | 0.878 | -0.972 (50) | [-2.177, -0.235] | 30 / 19 |

## Cross-stage: what each change did to ZAAD's own continuation cost (later minus earlier, series completed in both)

| from | to | window | track | scenario | series in both | only earlier | only later | mean diff | 95 % bootstrap | later better / worse | fill diff |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original | reference_v1 | final | observed | stable | 35 | 0 | 15 | +0.005 | [-0.017, +0.032] | 4 / 7 | +0.0003 |
| original | reference_v1 | final | observed | uncertain | 32 | 0 | 18 | +0.004 | [-0.039, +0.051] | 7 / 9 | +0.0018 |
| original | reference_v1 | final | observed | uncertain_fill_only | 33 | 0 | 17 | +0.020 | [-0.003, +0.053] | 5 / 8 | +0.0003 |
| original | reference_v1 | final | observed | uncertain_lead_only | 0 | 0 | 50 | | | | |
| original | reference_v1 | final | recovered | stable | 39 | 0 | 11 | -0.000 | [-0.001, +0.000] | 5 / 4 | -0.0000 |
| original | reference_v1 | final | recovered | uncertain | 34 | 0 | 16 | -0.012 | [-0.036, +0.011] | 5 / 4 | -0.0000 |
| original | reference_v1 | final | recovered | uncertain_fill_only | 37 | 0 | 13 | -0.003 | [-0.029, +0.020] | 4 / 9 | +0.0007 |
| original | reference_v1 | final | recovered | uncertain_lead_only | 0 | 0 | 50 | | | | |
| original | reference_v1 | val1 | observed | stable | 25 | 0 | 25 | -0.012 | [-0.031, +0.000] | 8 / 4 | +0.0016 |
| original | reference_v1 | val1 | observed | uncertain | 18 | 0 | 32 | +0.068 | [-0.043, +0.224] | 4 / 7 | +0.0041 |
| original | reference_v1 | val1 | observed | uncertain_fill_only | 15 | 0 | 35 | -0.081 | [-0.203, +0.004] | 4 / 2 | +0.0045 |
| original | reference_v1 | val1 | observed | uncertain_lead_only | 0 | 0 | 50 | | | | |
| original | reference_v1 | val1 | recovered | stable | 29 | 0 | 21 | -0.004 | [-0.011, +0.000] | 3 / 7 | +0.0004 |
| original | reference_v1 | val1 | recovered | uncertain | 12 | 0 | 38 | +0.331 | [-0.000, +0.918] | 0 / 2 | +0.0000 |
| original | reference_v1 | val1 | recovered | uncertain_fill_only | 12 | 0 | 38 | -0.054 | [-0.303, +0.097] | 1 / 2 | -0.0006 |
| original | reference_v1 | val1 | recovered | uncertain_lead_only | 0 | 0 | 50 | | | | |
| original | reference_v1 | val2 | observed | stable | 25 | 0 | 25 | -0.000 | [-0.000, +0.000] | 5 / 6 | -0.0000 |
| original | reference_v1 | val2 | observed | uncertain | 9 | 0 | 41 | -0.012 | [-0.083, +0.045] | 1 / 2 | +0.0107 |
| original | reference_v1 | val2 | observed | uncertain_fill_only | 14 | 0 | 36 | -0.158 | [-0.411, +0.014] | 7 / 4 | +0.0033 |
| original | reference_v1 | val2 | observed | uncertain_lead_only | 0 | 0 | 50 | | | | |
| original | reference_v1 | val2 | recovered | stable | 32 | 0 | 18 | -0.011 | [-0.033, +0.003] | 7 / 9 | -0.0004 |
| original | reference_v1 | val2 | recovered | uncertain | 17 | 0 | 33 | -0.275 | [-1.095, +0.217] | 1 / 3 | +0.0000 |
| original | reference_v1 | val2 | recovered | uncertain_fill_only | 16 | 0 | 34 | +0.123 | [-0.256, +0.594] | 4 / 5 | +0.0050 |
| original | reference_v1 | val2 | recovered | uncertain_lead_only | 0 | 0 | 50 | | | | |
| reference_v1 | corrected | final | observed | stable | 50 | 0 | 0 | +0.036 | [+0.008, +0.075] | 30 / 20 | -0.0064 |
| reference_v1 | corrected | final | observed | uncertain | 50 | 0 | 0 | -0.069 | [-0.221, +0.055] | 28 / 22 | -0.0234 |
| reference_v1 | corrected | final | observed | uncertain_fill_only | 50 | 0 | 0 | +0.014 | [-0.104, +0.178] | 35 / 15 | -0.0063 |
| reference_v1 | corrected | final | observed | uncertain_lead_only | 50 | 0 | 0 | +0.083 | [+0.012, +0.192] | 35 / 15 | -0.0160 |
| reference_v1 | corrected | final | recovered | stable | 50 | 0 | 0 | +0.030 | [+0.000, +0.066] | 32 / 18 | -0.0038 |
| reference_v1 | corrected | final | recovered | uncertain | 50 | 0 | 0 | -0.205 | [-0.425, -0.004] | 31 / 19 | -0.0118 |
| reference_v1 | corrected | final | recovered | uncertain_fill_only | 50 | 0 | 0 | -0.057 | [-0.110, -0.008] | 29 / 20 | -0.0055 |
| reference_v1 | corrected | final | recovered | uncertain_lead_only | 50 | 0 | 0 | +0.102 | [+0.015, +0.219] | 31 / 19 | -0.0175 |
| reference_v1 | corrected | val1 | observed | stable | 50 | 0 | 0 | +0.025 | [-0.033, +0.073] | 23 / 27 | -0.0072 |
| reference_v1 | corrected | val1 | observed | uncertain | 50 | 0 | 0 | -0.920 | [-1.917, -0.262] | 35 / 15 | -0.0220 |
| reference_v1 | corrected | val1 | observed | uncertain_fill_only | 50 | 0 | 0 | -0.197 | [-0.414, -0.018] | 28 / 22 | -0.0148 |
| reference_v1 | corrected | val1 | observed | uncertain_lead_only | 50 | 0 | 0 | +0.046 | [-0.068, +0.149] | 26 / 24 | -0.0242 |
| reference_v1 | corrected | val1 | recovered | stable | 50 | 0 | 0 | +0.014 | [-0.044, +0.062] | 27 / 23 | -0.0062 |
| reference_v1 | corrected | val1 | recovered | uncertain | 50 | 0 | 0 | -0.802 | [-1.377, -0.361] | 35 / 15 | -0.0106 |
| reference_v1 | corrected | val1 | recovered | uncertain_fill_only | 50 | 0 | 0 | -0.569 | [-0.949, -0.247] | 32 / 18 | -0.0087 |
| reference_v1 | corrected | val1 | recovered | uncertain_lead_only | 50 | 0 | 0 | +0.114 | [-0.175, +0.536] | 34 / 16 | -0.0189 |
| reference_v1 | corrected | val2 | observed | stable | 50 | 0 | 0 | +0.055 | [+0.022, +0.089] | 22 / 28 | -0.0074 |
| reference_v1 | corrected | val2 | observed | uncertain | 50 | 0 | 0 | +0.193 | [-0.322, +0.881] | 24 / 26 | -0.0216 |
| reference_v1 | corrected | val2 | observed | uncertain_fill_only | 50 | 0 | 0 | -0.604 | [-1.120, -0.189] | 29 / 21 | -0.0024 |
| reference_v1 | corrected | val2 | observed | uncertain_lead_only | 50 | 0 | 0 | +0.020 | [-0.173, +0.206] | 27 / 23 | -0.0182 |
| reference_v1 | corrected | val2 | recovered | stable | 50 | 0 | 0 | +0.009 | [-0.112, +0.088] | 19 / 31 | -0.0106 |
| reference_v1 | corrected | val2 | recovered | uncertain | 50 | 0 | 0 | -0.423 | [-0.875, +0.011] | 33 / 17 | -0.0135 |
| reference_v1 | corrected | val2 | recovered | uncertain_fill_only | 50 | 0 | 0 | -0.849 | [-1.938, -0.109] | 30 / 20 | -0.0123 |
| reference_v1 | corrected | val2 | recovered | uncertain_lead_only | 50 | 0 | 0 | -0.086 | [-0.361, +0.118] | 30 / 20 | -0.0176 |
