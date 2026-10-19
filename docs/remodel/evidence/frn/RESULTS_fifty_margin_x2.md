# FreshRetailNet pilot results: stage `fifty_margin_x2`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `7d69e59fbd60`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3662 s, peak RSS 226 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.331 | 10.970 | 10.564 | 0.0055 | 0.492 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.14 |
| final | observed | stable | gated | 50/50 | 10.346 | 10.688 | 9.055 | 0.0056 | 0.526 | 0.978 | 0.263 | 1.615 | 0.5 | 5.1 | 0.11 | 0.65 |
| final | observed | stable | order_up_to | 50/50 | 11.325 | 11.678 | 8.089 | 0.0023 | 2.503 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.09 |
| final | observed | stable | periodic:1 | 50/50 | 10.331 | 10.970 | 10.564 | 0.0055 | 0.492 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.02 |
| final | observed | stable | reorder_point | 50/50 | 10.344 | 10.732 | 9.285 | 0.0055 | 0.522 | 0.978 | 0.261 | 1.585 | 0.5 | 5.3 |  | 0.02 |
| final | observed | uncertain | base_stock | 50/50 | 13.064 | 14.080 | 12.809 | 0.0053 | 2.888 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.921 | 13.691 | 11.405 | 0.0071 | 2.947 | 0.887 | 1.474 | 2.068 | 1.4 | 4.0 | 0.30 | 0.62 |
| final | observed | uncertain | order_up_to | 50/50 | 13.691 | 14.382 | 9.724 | 0.0027 | 4.926 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.913 | 13.662 | 11.231 | 0.0048 | 2.971 | 0.883 | 1.485 | 1.397 | 1.4 | 5.5 |  | 0.02 |
| final | observed | uncertain | reorder_point | 50/50 | 12.920 | 13.669 | 11.221 | 0.0048 | 2.987 | 0.881 | 1.494 | 1.395 | 1.5 | 5.3 |  | 0.02 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 12.084 | 13.083 | 13.134 | 0.0064 | 1.523 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.780 | 12.544 | 11.735 | 0.0087 | 1.508 | 0.950 | 0.754 | 2.506 | 0.9 | 4.1 | 0.33 | 0.74 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 12.798 | 13.458 | 10.129 | 0.0033 | 3.477 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.10 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.888 | 12.596 | 11.391 | 0.0060 | 1.607 | 0.947 | 0.803 | 1.731 | 1.0 | 5.6 |  | 0.03 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.890 | 12.598 | 11.382 | 0.0060 | 1.614 | 0.947 | 0.807 | 1.728 | 1.0 | 5.3 |  | 0.02 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 11.675 | 12.727 | 11.336 | 0.0050 | 3.164 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.12 |
| final | observed | uncertain_lead_only | gated | 50/50 | 11.596 | 12.164 | 9.003 | 0.0054 | 3.002 | 0.904 | 1.501 | 1.562 | 1.2 | 4.2 | 0.33 | 0.72 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 12.654 | 13.369 | 8.578 | 0.0025 | 5.157 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.10 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 11.673 | 12.468 | 10.039 | 0.0050 | 3.164 | 0.896 | 1.582 | 1.451 | 1.3 | 5.4 |  | 0.03 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 11.692 | 12.490 | 10.028 | 0.0050 | 3.206 | 0.895 | 1.603 | 1.444 | 1.3 | 5.0 |  | 0.03 |
| final | recovered | stable | base_stock | 50/50 | 11.462 | 12.248 | 11.939 | 0.0076 | 0.413 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.14 |
| final | recovered | stable | gated | 50/50 | 11.469 | 11.928 | 10.321 | 0.0077 | 0.420 | 0.975 | 0.210 | 2.217 | 0.5 | 4.8 | 0.11 | 0.59 |
| final | recovered | stable | order_up_to | 50/50 | 12.808 | 13.216 | 8.640 | 0.0030 | 3.134 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.10 |
| final | recovered | stable | periodic:1 | 50/50 | 11.462 | 12.248 | 11.939 | 0.0076 | 0.413 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.03 |
| final | recovered | stable | reorder_point | 50/50 | 11.488 | 12.000 | 10.526 | 0.0076 | 0.470 | 0.971 | 0.235 | 2.192 | 0.5 | 5.1 |  | 0.03 |
| final | recovered | uncertain | base_stock | 50/50 | 14.364 | 15.576 | 14.958 | 0.0069 | 2.473 | 0.896 | 1.237 | 1.994 | 1.3 | 6.2 |  | 0.12 |
| final | recovered | uncertain | gated | 50/50 | 14.053 | 14.854 | 12.781 | 0.0082 | 2.328 | 0.895 | 1.164 | 2.385 | 1.2 | 4.0 | 0.31 | 0.62 |
| final | recovered | uncertain | order_up_to | 50/50 | 15.054 | 15.825 | 10.883 | 0.0030 | 4.959 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.10 |
| final | recovered | uncertain | periodic:1 | 50/50 | 14.163 | 15.081 | 13.214 | 0.0064 | 2.522 | 0.894 | 1.261 | 1.841 | 1.3 | 5.5 |  | 0.02 |
| final | recovered | uncertain | reorder_point | 50/50 | 14.188 | 15.106 | 13.192 | 0.0063 | 2.567 | 0.889 | 1.283 | 1.832 | 1.4 | 5.0 |  | 0.03 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 13.121 | 14.328 | 15.203 | 0.0085 | 0.973 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.879 | 13.714 | 13.104 | 0.0106 | 1.085 | 0.953 | 0.542 | 3.082 | 0.8 | 4.1 | 0.37 | 0.73 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 14.018 | 14.768 | 11.255 | 0.0040 | 3.440 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.895 | 13.791 | 13.331 | 0.0080 | 1.034 | 0.956 | 0.517 | 2.306 | 0.9 | 5.5 |  | 0.03 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.910 | 13.807 | 13.318 | 0.0079 | 1.071 | 0.953 | 0.535 | 2.301 | 0.9 | 5.0 |  | 0.03 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 12.551 | 13.815 | 13.295 | 0.0067 | 2.575 | 0.910 | 1.287 | 1.940 | 1.2 | 6.2 |  | 0.12 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 12.508 | 13.180 | 10.361 | 0.0070 | 2.493 | 0.913 | 1.247 | 2.027 | 1.2 | 3.9 | 0.34 | 0.70 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 13.820 | 14.626 | 9.627 | 0.0030 | 5.154 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.10 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 12.548 | 13.535 | 11.894 | 0.0067 | 2.575 | 0.910 | 1.287 | 1.940 | 1.2 | 5.3 |  | 0.03 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 12.573 | 13.559 | 11.858 | 0.0067 | 2.627 | 0.908 | 1.314 | 1.931 | 1.3 | 4.7 |  | 0.02 |
| val1 | observed | stable | base_stock | 50/50 | 18.480 | 18.967 | 17.937 | 0.0125 | 0.956 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.54 |
| val1 | observed | stable | gated | 50/50 | 18.453 | 18.943 | 17.989 | 0.0130 | 0.898 | 0.961 | 0.449 | 1.432 | 1.2 | 11.1 | 0.10 | 4.51 |
| val1 | observed | stable | order_up_to | 50/50 | 20.772 | 21.059 | 14.512 | 0.0047 | 5.680 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.480 | 18.967 | 17.937 | 0.0125 | 0.956 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.498 | 18.982 | 17.901 | 0.0124 | 0.993 | 0.956 | 0.497 | 1.350 | 1.3 | 11.1 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 22.296 | 23.075 | 19.912 | 0.0144 | 4.325 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.42 |
| val1 | observed | uncertain | gated | 50/50 | 21.909 | 23.031 | 22.797 | 0.0313 | 2.885 | 0.925 | 1.442 | 2.930 | 1.7 | 9.1 | 0.48 | 2.63 |
| val1 | observed | uncertain | order_up_to | 50/50 | 24.609 | 25.208 | 15.839 | 0.0061 | 9.774 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 22.417 | 23.170 | 19.576 | 0.0131 | 4.649 | 0.889 | 2.324 | 1.452 | 2.8 | 12.3 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 22.440 | 23.192 | 19.550 | 0.0130 | 4.689 | 0.887 | 2.344 | 1.444 | 2.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 21.318 | 22.132 | 20.968 | 0.0171 | 2.452 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.43 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.815 | 22.882 | 23.063 | 0.0405 | 2.243 | 0.941 | 1.122 | 3.240 | 1.5 | 8.9 | 0.47 | 3.18 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 22.885 | 23.452 | 17.195 | 0.0073 | 6.532 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.24 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.378 | 22.161 | 20.717 | 0.0157 | 2.600 | 0.923 | 1.300 | 1.582 | 1.9 | 12.4 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.377 | 22.158 | 20.686 | 0.0157 | 2.620 | 0.922 | 1.310 | 1.571 | 1.9 | 11.4 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 19.953 | 20.778 | 18.241 | 0.0151 | 3.865 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.43 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 19.782 | 20.716 | 19.350 | 0.0274 | 3.177 | 0.905 | 1.588 | 2.217 | 1.9 | 11.1 | 0.47 | 3.24 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 22.537 | 23.177 | 14.535 | 0.0062 | 9.195 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.22 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 19.953 | 20.778 | 18.241 | 0.0151 | 3.865 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.04 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 19.969 | 20.790 | 18.215 | 0.0150 | 3.895 | 0.873 | 1.948 | 1.487 | 2.7 | 10.7 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.430 | 23.031 | 21.249 | 0.0155 | 1.375 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.54 |
| val1 | recovered | stable | gated | 50/50 | 22.401 | 22.996 | 21.249 | 0.0158 | 1.316 | 0.954 | 0.658 | 1.870 | 1.0 | 10.6 | 0.08 | 3.99 |
| val1 | recovered | stable | order_up_to | 50/50 | 25.261 | 25.645 | 17.176 | 0.0057 | 7.197 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.22 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.430 | 23.031 | 21.249 | 0.0155 | 1.375 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.451 | 23.046 | 21.202 | 0.0153 | 1.416 | 0.953 | 0.708 | 1.799 | 1.1 | 10.6 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 26.779 | 27.777 | 24.322 | 0.0170 | 4.714 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.41 |
| val1 | recovered | uncertain | gated | 50/50 | 26.403 | 27.551 | 26.698 | 0.0390 | 2.849 | 0.923 | 1.424 | 3.276 | 1.6 | 8.7 | 0.42 | 2.70 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 29.556 | 30.300 | 19.189 | 0.0071 | 11.312 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.23 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 26.926 | 27.890 | 23.883 | 0.0156 | 5.125 | 0.905 | 2.563 | 1.897 | 2.2 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 26.942 | 27.904 | 23.851 | 0.0156 | 5.161 | 0.904 | 2.581 | 1.886 | 2.2 | 10.9 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 25.383 | 26.368 | 25.415 | 0.0202 | 2.152 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.778 | 26.772 | 26.016 | 0.0445 | 2.139 | 0.938 | 1.070 | 3.596 | 1.4 | 8.7 | 0.42 | 3.11 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.363 | 28.053 | 20.790 | 0.0082 | 7.243 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.22 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 25.403 | 26.343 | 25.057 | 0.0185 | 2.302 | 0.932 | 1.151 | 2.055 | 1.6 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 25.413 | 26.352 | 25.031 | 0.0184 | 2.330 | 0.931 | 1.165 | 2.040 | 1.7 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.767 | 24.823 | 22.271 | 0.0175 | 4.046 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.41 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 23.591 | 24.756 | 23.312 | 0.0279 | 3.416 | 0.923 | 1.708 | 2.625 | 1.5 | 10.5 | 0.47 | 3.10 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 26.775 | 27.570 | 17.761 | 0.0070 | 10.205 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.23 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.767 | 24.823 | 22.271 | 0.0175 | 4.046 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.788 | 24.842 | 22.239 | 0.0175 | 4.089 | 0.897 | 2.045 | 1.950 | 2.1 | 10.2 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.410 | 18.922 | 17.975 | 0.0130 | 0.799 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.52 |
| val2 | observed | stable | gated | 50/50 | 18.443 | 18.957 | 17.970 | 0.0134 | 0.859 | 0.966 | 0.429 | 1.409 | 1.0 | 11.3 | 0.09 | 3.91 |
| val2 | observed | stable | order_up_to | 50/50 | 21.041 | 21.388 | 14.397 | 0.0047 | 6.176 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.410 | 18.922 | 17.975 | 0.0130 | 0.799 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.05 |
| val2 | observed | stable | reorder_point | 50/50 | 18.467 | 18.981 | 17.934 | 0.0129 | 0.913 | 0.960 | 0.456 | 1.341 | 1.1 | 11.4 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 50/50 | 22.363 | 23.231 | 20.616 | 0.0143 | 3.915 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.42 |
| val2 | observed | uncertain | gated | 50/50 | 22.690 | 23.656 | 22.536 | 0.0280 | 3.081 | 0.926 | 1.541 | 2.686 | 1.5 | 8.8 | 0.49 | 2.63 |
| val2 | observed | uncertain | order_up_to | 50/50 | 24.673 | 25.309 | 15.949 | 0.0055 | 9.705 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.24 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 22.538 | 23.382 | 20.285 | 0.0131 | 4.297 | 0.896 | 2.149 | 1.265 | 2.2 | 12.3 |  | 0.05 |
| val2 | observed | uncertain | reorder_point | 50/50 | 22.562 | 23.406 | 20.265 | 0.0130 | 4.345 | 0.893 | 2.173 | 1.263 | 2.2 | 11.6 |  | 0.06 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.794 | 22.599 | 21.984 | 0.0153 | 1.673 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.43 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 22.309 | 23.362 | 24.635 | 0.0351 | 1.107 | 0.960 | 0.554 | 2.883 | 0.9 | 9.7 | 0.49 | 3.30 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 23.185 | 23.733 | 17.687 | 0.0057 | 6.039 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.24 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.835 | 22.613 | 21.677 | 0.0140 | 1.884 | 0.937 | 0.942 | 1.438 | 1.3 | 12.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.835 | 22.613 | 21.645 | 0.0138 | 1.920 | 0.935 | 0.960 | 1.428 | 1.4 | 11.7 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 19.547 | 20.386 | 18.553 | 0.0141 | 3.035 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.44 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 19.260 | 20.233 | 19.742 | 0.0227 | 2.234 | 0.912 | 1.117 | 2.352 | 1.6 | 11.0 | 0.47 | 3.36 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 22.209 | 22.784 | 14.388 | 0.0059 | 8.504 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.24 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 19.549 | 20.389 | 18.550 | 0.0141 | 3.040 | 0.888 | 1.520 | 1.456 | 2.2 | 12.0 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 19.554 | 20.396 | 18.536 | 0.0138 | 3.063 | 0.887 | 1.532 | 1.448 | 2.2 | 10.9 |  | 0.05 |
| val2 | recovered | stable | base_stock | 50/50 | 23.725 | 24.419 | 21.632 | 0.0172 | 2.688 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.54 |
| val2 | recovered | stable | gated | 50/50 | 23.735 | 24.460 | 21.791 | 0.0174 | 2.676 | 0.947 | 1.338 | 2.020 | 1.2 | 10.5 | 0.08 | 4.24 |
| val2 | recovered | stable | order_up_to | 50/50 | 26.535 | 26.942 | 17.222 | 0.0065 | 8.435 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.24 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.725 | 24.419 | 21.632 | 0.0172 | 2.688 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.781 | 24.474 | 21.565 | 0.0169 | 2.803 | 0.940 | 1.401 | 1.948 | 1.3 | 10.5 |  | 0.05 |
| val2 | recovered | uncertain | base_stock | 50/50 | 28.035 | 29.041 | 24.888 | 0.0195 | 5.466 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.43 |
| val2 | recovered | uncertain | gated | 50/50 | 27.440 | 28.791 | 29.228 | 0.0370 | 2.908 | 0.929 | 1.454 | 3.507 | 1.5 | 8.9 | 0.44 | 2.66 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 30.847 | 31.561 | 18.942 | 0.0081 | 12.567 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.24 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 28.210 | 29.182 | 24.369 | 0.0180 | 5.942 | 0.895 | 2.971 | 1.961 | 2.1 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 28.228 | 29.200 | 24.330 | 0.0179 | 5.993 | 0.892 | 2.997 | 1.953 | 2.1 | 10.9 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 27.608 | 28.656 | 26.642 | 0.0209 | 3.392 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.43 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 27.935 | 29.287 | 30.296 | 0.0417 | 1.955 | 0.945 | 0.978 | 3.528 | 1.1 | 9.4 | 0.47 | 3.18 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 29.277 | 29.948 | 21.195 | 0.0082 | 8.535 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.24 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 27.644 | 28.647 | 26.208 | 0.0191 | 3.635 | 0.931 | 1.818 | 2.158 | 1.5 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 27.636 | 28.638 | 26.143 | 0.0190 | 3.678 | 0.928 | 1.839 | 2.140 | 1.5 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 24.899 | 25.969 | 22.603 | 0.0206 | 4.896 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.44 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.994 | 25.326 | 25.029 | 0.0276 | 2.881 | 0.911 | 1.440 | 2.912 | 1.5 | 10.6 | 0.45 | 3.36 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 27.727 | 28.414 | 17.457 | 0.0083 | 10.807 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.24 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 24.902 | 25.972 | 22.600 | 0.0206 | 4.902 | 0.883 | 2.451 | 2.187 | 2.2 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 24.966 | 26.037 | 22.525 | 0.0205 | 5.035 | 0.878 | 2.517 | 2.174 | 2.3 | 10.1 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | +0.002 | [-0.010, +0.015] | [-0.015, +0.023] | 15 / 9 / 26 | 0.307 |
| final | observed | stable | periodic:1 | 50 | +0.015 | [-0.002, +0.034] | [-0.009, +0.045] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | base_stock | 50 | +0.015 | [-0.002, +0.033] | [-0.009, +0.044] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | order_up_to | 50 | -0.979 | [-1.171, -0.803] | [-1.277, -0.726] | 46 / 4 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | +0.001 | [-0.089, +0.093] | [-0.137, +0.139] | 24 / 21 / 5 | 0.766 |
| final | observed | uncertain | periodic:1 | 50 | +0.008 | [-0.078, +0.094] | [-0.125, +0.146] | 25 / 22 / 3 | 0.771 |
| final | observed | uncertain | base_stock | 50 | -0.143 | [-0.229, -0.054] | [-0.276, -0.005] | 34 / 16 / 0 | 0.015 |
| final | observed | uncertain | order_up_to | 50 | -0.770 | [-0.952, -0.583] | [-1.055, -0.482] | 41 / 9 / 0 | 0.0 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.110 | [-0.311, +0.066] | [-0.444, +0.115] | 24 / 22 / 4 | 0.883 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.108 | [-0.302, +0.070] | [-0.463, +0.120] | 25 / 23 / 2 | 0.885 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.304 | [-0.608, -0.022] | [-0.869, +0.033] | 30 / 20 / 0 | 0.203 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -1.018 | [-1.357, -0.725] | [-1.554, -0.617] | 41 / 9 / 0 | 0.0 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.097 | [-0.162, -0.036] | [-0.201, -0.013] | 33 / 11 / 6 | 0.001 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.077 | [-0.131, -0.028] | [-0.165, -0.009] | 36 / 11 / 3 | 0.0 |
| final | observed | uncertain_lead_only | base_stock | 50 | -0.079 | [-0.131, -0.029] | [-0.164, -0.012] | 44 / 6 / 0 | 0.0 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -1.058 | [-1.286, -0.841] | [-1.429, -0.741] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | -0.020 | [-0.049, +0.009] | [-0.067, +0.022] | 18 / 7 / 25 | 0.043 |
| final | recovered | stable | periodic:1 | 50 | +0.007 | [-0.019, +0.035] | [-0.036, +0.047] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | base_stock | 50 | +0.007 | [-0.021, +0.033] | [-0.036, +0.047] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | order_up_to | 50 | -1.339 | [-1.644, -1.057] | [-1.820, -0.939] | 45 / 5 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | -0.136 | [-0.354, +0.078] | [-0.518, +0.178] | 28 / 19 / 3 | 0.243 |
| final | recovered | uncertain | periodic:1 | 50 | -0.111 | [-0.332, +0.104] | [-0.497, +0.208] | 28 / 20 / 2 | 0.312 |
| final | recovered | uncertain | base_stock | 50 | -0.312 | [-0.538, -0.101] | [-0.676, -0.004] | 34 / 16 / 0 | 0.015 |
| final | recovered | uncertain | order_up_to | 50 | -1.001 | [-1.364, -0.667] | [-1.595, -0.547] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.031 | [-0.260, +0.174] | [-0.397, +0.254] | 27 / 21 / 2 | 0.471 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.017 | [-0.245, +0.191] | [-0.403, +0.267] | 25 / 24 / 1 | 1.0 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.242 | [-0.593, +0.076] | [-0.831, +0.180] | 32 / 18 / 0 | 0.065 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -1.140 | [-1.524, -0.781] | [-1.770, -0.642] | 42 / 8 / 0 | 0.0 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.066 | [-0.124, -0.014] | [-0.162, +0.003] | 31 / 14 / 5 | 0.016 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.041 | [-0.080, -0.006] | [-0.104, +0.008] | 34 / 13 / 3 | 0.003 |
| final | recovered | uncertain_lead_only | base_stock | 50 | -0.043 | [-0.083, -0.008] | [-0.109, +0.006] | 43 / 6 / 1 | 0.0 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -1.312 | [-1.646, -0.988] | [-1.879, -0.874] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.045 | [-0.074, -0.017] | [-0.094, -0.004] | 8 / 26 / 16 | 0.003 |
| val1 | observed | stable | periodic:1 | 50 | -0.027 | [-0.054, -0.001] | [-0.070, +0.010] | 21 / 23 / 6 | 0.88 |
| val1 | observed | stable | base_stock | 50 | -0.027 | [-0.052, -0.002] | [-0.068, +0.011] | 21 / 23 / 6 | 0.88 |
| val1 | observed | stable | order_up_to | 50 | -2.318 | [-2.945, -1.755] | [-3.431, -1.625] | 49 / 1 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | -0.532 | [-1.026, -0.096] | [-1.347, +0.043] | 31 / 18 / 1 | 0.085 |
| val1 | observed | uncertain | periodic:1 | 50 | -0.509 | [-1.016, -0.086] | [-1.369, +0.045] | 32 / 18 / 0 | 0.065 |
| val1 | observed | uncertain | base_stock | 50 | -0.387 | [-0.778, -0.024] | [-1.061, +0.105] | 30 / 20 / 0 | 0.203 |
| val1 | observed | uncertain | order_up_to | 50 | -2.700 | [-4.063, -1.532] | [-5.151, -1.319] | 45 / 5 / 0 | 0.0 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.438 | [+0.212, +0.681] | [+0.111, +0.828] | 19 / 30 / 1 | 0.152 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.437 | [+0.206, +0.677] | [+0.107, +0.811] | 19 / 30 / 1 | 0.152 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.496 | [+0.261, +0.744] | [+0.151, +0.903] | 18 / 32 / 0 | 0.065 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | -1.070 | [-1.458, -0.692] | [-1.708, -0.513] | 40 / 10 / 0 | 0.0 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.187 | [-0.352, -0.009] | [-0.434, +0.096] | 26 / 24 / 0 | 0.888 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.171 | [-0.338, +0.007] | [-0.418, +0.116] | 26 / 24 / 0 | 0.888 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | -0.171 | [-0.346, +0.005] | [-0.430, +0.104] | 26 / 24 / 0 | 0.888 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -2.755 | [-3.756, -1.881] | [-4.488, -1.669] | 46 / 4 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | -0.050 | [-0.107, +0.003] | [-0.153, +0.007] | 6 / 25 / 19 | 0.001 |
| val1 | recovered | stable | periodic:1 | 50 | -0.029 | [-0.089, +0.025] | [-0.138, +0.036] | 20 / 26 / 4 | 0.461 |
| val1 | recovered | stable | base_stock | 50 | -0.029 | [-0.090, +0.026] | [-0.139, +0.037] | 20 / 26 / 4 | 0.461 |
| val1 | recovered | stable | order_up_to | 50 | -2.860 | [-3.797, -2.078] | [-4.481, -1.927] | 49 / 1 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | -0.539 | [-1.386, +0.194] | [-2.040, +0.395] | 22 / 26 / 2 | 0.665 |
| val1 | recovered | uncertain | periodic:1 | 50 | -0.523 | [-1.367, +0.208] | [-1.992, +0.430] | 21 / 29 / 0 | 0.322 |
| val1 | recovered | uncertain | base_stock | 50 | -0.376 | [-1.152, +0.274] | [-1.646, +0.471] | 18 / 32 / 0 | 0.065 |
| val1 | recovered | uncertain | order_up_to | 50 | -3.154 | [-4.904, -1.599] | [-6.201, -1.304] | 42 / 8 / 0 | 0.0 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +0.366 | [+0.110, +0.624] | [-0.029, +0.768] | 17 / 31 / 2 | 0.059 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.376 | [+0.110, +0.650] | [-0.029, +0.778] | 18 / 31 / 1 | 0.085 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +0.395 | [+0.134, +0.659] | [-0.002, +0.794] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | -1.584 | [-2.409, -0.859] | [-2.981, -0.630] | 39 / 11 / 0 | 0.0 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.197 | [-0.340, -0.059] | [-0.416, +0.022] | 24 / 26 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.176 | [-0.317, -0.034] | [-0.389, +0.045] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | -0.176 | [-0.316, -0.032] | [-0.394, +0.045] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -3.184 | [-4.123, -2.359] | [-4.847, -2.103] | 47 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | -0.024 | [-0.047, -0.003] | [-0.064, +0.003] | 10 / 25 / 15 | 0.017 |
| val2 | observed | stable | periodic:1 | 50 | +0.032 | [+0.009, +0.054] | [-0.002, +0.069] | 19 / 29 / 2 | 0.193 |
| val2 | observed | stable | base_stock | 50 | +0.032 | [+0.010, +0.056] | [-0.002, +0.069] | 19 / 29 / 2 | 0.193 |
| val2 | observed | stable | order_up_to | 50 | -2.598 | [-3.647, -1.632] | [-4.554, -1.494] | 50 / 0 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | +0.128 | [-0.134, +0.402] | [-0.261, +0.559] | 25 / 25 / 0 | 1.0 |
| val2 | observed | uncertain | periodic:1 | 50 | +0.151 | [-0.109, +0.415] | [-0.240, +0.566] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain | base_stock | 50 | +0.327 | [+0.096, +0.582] | [-0.002, +0.741] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain | order_up_to | 50 | -1.984 | [-3.048, -1.017] | [-3.846, -0.824] | 42 / 8 / 0 | 0.0 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.473 | [+0.147, +0.826] | [+0.010, +1.012] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.473 | [+0.153, +0.802] | [+0.007, +0.985] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.515 | [+0.179, +0.869] | [+0.028, +1.051] | 21 / 29 / 0 | 0.322 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | -0.876 | [-1.379, -0.395] | [-1.694, -0.163] | 38 / 12 / 0 | 0.0 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.295 | [-0.479, -0.112] | [-0.587, -0.034] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.290 | [-0.466, -0.122] | [-0.567, -0.040] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.287 | [-0.471, -0.115] | [-0.577, -0.031] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -2.949 | [-4.214, -1.856] | [-5.142, -1.584] | 47 / 3 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | -0.046 | [-0.090, -0.004] | [-0.118, +0.016] | 8 / 25 / 17 | 0.005 |
| val2 | recovered | stable | periodic:1 | 50 | +0.010 | [-0.030, +0.050] | [-0.052, +0.073] | 21 / 27 / 2 | 0.471 |
| val2 | recovered | stable | base_stock | 50 | +0.010 | [-0.029, +0.049] | [-0.050, +0.069] | 21 / 27 / 2 | 0.471 |
| val2 | recovered | stable | order_up_to | 50 | -2.800 | [-3.670, -2.041] | [-4.266, -1.884] | 50 / 0 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | -0.787 | [-1.889, +0.185] | [-2.674, +0.447] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain | periodic:1 | 50 | -0.769 | [-1.873, +0.229] | [-2.723, +0.493] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain | base_stock | 50 | -0.594 | [-1.530, +0.253] | [-2.244, +0.480] | 28 / 22 / 0 | 0.48 |
| val2 | recovered | uncertain | order_up_to | 50 | -3.407 | [-5.740, -1.411] | [-7.484, -1.077] | 42 / 8 / 0 | 0.0 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | +0.299 | [-0.138, +0.720] | [-0.403, +0.946] | 21 / 28 / 1 | 0.392 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.291 | [-0.183, +0.737] | [-0.452, +0.968] | 20 / 30 / 0 | 0.203 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | +0.327 | [-0.083, +0.744] | [-0.308, +0.964] | 20 / 30 / 0 | 0.203 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | -1.342 | [-2.192, -0.544] | [-2.768, -0.264] | 40 / 10 / 0 | 0.0 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.972 | [-1.646, -0.377] | [-2.177, -0.235] | 30 / 19 / 1 | 0.152 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.908 | [-1.542, -0.321] | [-2.059, -0.184] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.904 | [-1.576, -0.313] | [-2.101, -0.167] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -3.733 | [-5.260, -2.397] | [-6.315, -2.080] | 47 / 3 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | +0.0037 | [-0.0307, +0.0440] | 2 / 3 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0296 | [-0.0170, +0.0907] | 10 / 9 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | +0.0005 | [-0.0017, +0.0034] | 2 / 3 |
| final | observed | stable | periodic:1 | shortage | 50 | +0.0340 | [-0.0136, +0.0932] | 2 / 9 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0177 | [-0.0317, +0.0799] | 26 / 11 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0014 | [-0.0044, +0.0019] | 2 / 9 |
| final | observed | stable | base_stock | shortage | 50 | +0.0340 | [-0.0154, +0.0923] | 2 / 9 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | +0.0177 | [-0.0307, +0.0836] | 26 / 11 |
| final | observed | stable | base_stock | service_unit_fill | 50 | -0.0014 | [-0.0044, +0.0020] | 2 / 9 |
| final | observed | stable | order_up_to | shortage | 50 | -1.9770 | [-2.5479, -1.4677] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9624 | [+0.5896, +1.5983] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1422 | [+0.1138, +0.1699] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.0399 | [-0.2652, +0.1792] | 8 / 9 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.6733 | [+0.1032, +1.7100] | 13 / 25 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0058 | [-0.0113, +0.0218] | 8 / 9 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.0234 | [-0.2413, +0.1925] | 8 / 10 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.6712 | [+0.1065, +1.7315] | 15 / 26 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0041 | [-0.0133, +0.0195] | 8 / 10 |
| final | observed | uncertain | base_stock | shortage | 50 | +0.0590 | [-0.1663, +0.2773] | 8 / 18 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.5469 | [+0.0268, +1.4918] | 30 / 20 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | -0.0010 | [-0.0194, +0.0146] | 8 / 18 |
| final | observed | uncertain | order_up_to | shortage | 50 | -1.9788 | [-2.5689, -1.4433] | 41 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.2993 | [+0.5057, +2.7959] | 1 / 49 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1455 | [+0.1159, +0.1758] | 41 / 0 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.1065 | [-0.4308, +0.1266] | 9 / 8 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.7786 | [+0.1629, +1.9165] | 11 / 31 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0031 | [-0.0049, +0.0123] | 9 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0987 | [-0.4194, +0.1427] | 8 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.7750 | [+0.1585, +1.9068] | 14 / 31 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0023 | [-0.0051, +0.0114] | 8 / 8 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.0146 | [-0.3447, +0.2443] | 6 / 12 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.6470 | [+0.0638, +1.7491] | 27 / 23 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0010 | [-0.0089, +0.0078] | 6 / 12 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.9688 | [-2.6442, -1.4037] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.5442 | [+0.6576, +3.1894] | 0 / 50 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1339 | [+0.1059, +0.1635] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.2034 | [-0.4115, -0.0347] | 8 / 2 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.1189 | [+0.0388, +0.2188] | 14 / 26 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0086 | [+0.0009, +0.0178] | 8 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.1618 | [-0.3308, -0.0286] | 7 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.1114 | [+0.0318, +0.2134] | 18 / 25 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0075 | [+0.0004, +0.0163] | 7 / 2 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.1618 | [-0.3267, -0.0300] | 7 / 2 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.1114 | [+0.0332, +0.2068] | 18 / 25 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0075 | [+0.0008, +0.0162] | 7 / 2 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -2.1548 | [-2.8692, -1.5189] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.8408 | [+0.5332, +1.3817] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1421 | [+0.1143, +0.1703] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | -0.0502 | [-0.1400, +0.0284] | 3 / 1 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0249 | [-0.0282, +0.0833] | 13 / 8 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0041 | [-0.0003, +0.0104] | 3 / 1 |
| final | recovered | stable | periodic:1 | shortage | 50 | +0.0070 | [-0.0783, +0.0861] | 3 / 5 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0044 | [-0.0497, +0.0659] | 26 / 8 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0006 | [-0.0048, +0.0071] | 3 / 5 |
| final | recovered | stable | base_stock | shortage | 50 | +0.0070 | [-0.0785, +0.0848] | 3 / 5 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0044 | [-0.0496, +0.0683] | 26 / 8 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | +0.0006 | [-0.0047, +0.0071] | 3 / 5 |
| final | recovered | stable | order_up_to | shortage | 50 | -2.7139 | [-3.6759, -1.9107] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.3476 | [+0.8552, +2.1432] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1558 | [+0.1313, +0.1802] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.2390 | [-0.7675, +0.1027] | 11 / 9 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.5529 | [+0.1144, +1.3259] | 13 / 30 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0053 | [-0.0117, +0.0206] | 11 / 9 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.1946 | [-0.7107, +0.1470] | 10 / 9 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5438 | [+0.1073, +1.3375] | 15 / 30 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0011 | [-0.0144, +0.0149] | 10 / 9 |
| final | recovered | uncertain | base_stock | shortage | 50 | -0.1453 | [-0.6763, +0.1909] | 7 / 14 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.3911 | [+0.0113, +1.0803] | 29 / 21 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | -0.0016 | [-0.0181, +0.0129] | 7 / 14 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -2.6308 | [-3.8492, -1.7014] | 42 / 0 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +1.5211 | [+0.7224, +2.9261] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1487 | [+0.1187, +0.1796] | 42 / 0 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | +0.0141 | [-0.1690, +0.2541] | 8 / 8 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.7805 | [+0.1996, +1.6827] | 13 / 33 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | -0.0000 | [-0.0059, +0.0056] | 8 / 8 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | +0.0506 | [-0.1241, +0.2719] | 6 / 11 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.7754 | [+0.2083, +1.7043] | 14 / 34 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | -0.0030 | [-0.0086, +0.0024] | 6 / 11 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | +0.1119 | [-0.0479, +0.3377] | 3 / 12 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.6132 | [+0.0895, +1.4435] | 24 / 26 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0062 | [-0.0116, -0.0012] | 3 / 12 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -2.3557 | [-3.2583, -1.6320] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.9316 | [+0.9439, +3.5471] | 0 / 50 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1381 | [+0.1099, +0.1679] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.1340 | [-0.3286, +0.0061] | 9 / 5 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.0964 | [+0.0265, +0.1727] | 10 / 26 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0045 | [-0.0014, +0.0106] | 9 / 5 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.0813 | [-0.2071, +0.0153] | 8 / 5 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.0879 | [+0.0215, +0.1687] | 16 / 24 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0023 | [-0.0024, +0.0071] | 8 / 5 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.0813 | [-0.2061, +0.0134] | 8 / 5 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.0879 | [+0.0197, +0.1665] | 16 / 24 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0023 | [-0.0025, +0.0070] | 8 / 5 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -2.6611 | [-3.7346, -1.7701] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.1662 | [+0.7409, +1.8551] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1500 | [+0.1208, +0.1790] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.0955 | [-0.1944, -0.0176] | 7 / 2 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0824 | [+0.0387, +0.1487] | 1 / 32 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0057 | [+0.0013, +0.0116] | 7 / 2 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.0587 | [-0.1432, +0.0114] | 7 / 6 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0632 | [+0.0194, +0.1242] | 16 / 28 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0039 | [-0.0001, +0.0094] | 7 / 6 |
| val1 | observed | stable | base_stock | shortage | 50 | -0.0587 | [-0.1432, +0.0142] | 7 / 6 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0632 | [+0.0178, +0.1258] | 16 / 28 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | +0.0039 | [+0.0000, +0.0092] | 7 / 6 |
| val1 | observed | stable | order_up_to | shortage | 50 | -4.7823 | [-6.9954, -3.4029] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9698 | [+0.6603, +1.4367] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1695 | [+0.1493, +0.1914] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -1.8038 | [-3.5090, -0.7635] | 35 / 1 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.4861 | [+0.7709, +2.6954] | 0 / 49 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0377 | [+0.0275, +0.0488] | 35 / 1 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -1.7638 | [-3.4465, -0.7246] | 37 / 1 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.4777 | [+0.7526, +2.6763] | 1 / 49 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0360 | [+0.0263, +0.0469] | 37 / 1 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.4403 | [-2.8430, -0.5546] | 34 / 6 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.3718 | [+0.6859, +2.5072] | 4 / 46 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0302 | [+0.0209, +0.0398] | 34 / 6 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -6.8890 | [-11.4229, -4.1066] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +2.2355 | [+1.2795, +3.8740] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1973 | [+0.1797, +0.2159] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.3764 | [-0.5735, -0.2063] | 23 / 3 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.6688 | [+0.8095, +3.0120] | 2 / 47 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0194 | [+0.0089, +0.0309] | 23 / 3 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.3573 | [-0.5463, -0.1853] | 23 / 4 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.6577 | [+0.8031, +3.0561] | 2 / 47 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0187 | [+0.0089, +0.0297] | 23 / 4 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.2084 | [-0.3861, -0.0479] | 15 / 14 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.5166 | [+0.7127, +2.6905] | 3 / 47 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0132 | [+0.0039, +0.0237] | 15 / 14 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -4.2893 | [-6.1767, -3.0849] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.5307 | [+1.4088, +4.3388] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1568 | [+0.1347, +0.1795] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.7186 | [-1.0842, -0.3927] | 29 / 4 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7297 | [+0.4517, +1.0922] | 0 / 50 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0328 | [+0.0139, +0.0587] | 29 / 4 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.6889 | [-1.0401, -0.3612] | 29 / 4 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7225 | [+0.4371, +1.0792] | 0 / 50 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0300 | [+0.0139, +0.0512] | 29 / 4 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.6889 | [-1.0555, -0.3530] | 29 / 4 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.7225 | [+0.4380, +1.0821] | 0 / 50 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0300 | [+0.0136, +0.0524] | 29 / 4 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -6.0183 | [-9.2555, -3.9474] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.5650 | [+1.0287, +2.3778] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1917 | [+0.1726, +0.2115] | 50 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 50 | -0.1003 | [-0.3037, +0.0137] | 4 / 2 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0709 | [+0.0326, +0.1304] | 4 / 26 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0018 | [-0.0007, +0.0059] | 4 / 2 |
| val1 | recovered | stable | periodic:1 | shortage | 50 | -0.0592 | [-0.2806, +0.0718] | 4 / 8 |
| val1 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0455 | [+0.0053, +0.1051] | 22 / 24 |
| val1 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0008 | [-0.0047, +0.0041] | 4 / 8 |
| val1 | recovered | stable | base_stock | shortage | 50 | -0.0592 | [-0.2760, +0.0735] | 4 / 8 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0455 | [+0.0068, +0.1049] | 22 / 24 |
| val1 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0008 | [-0.0047, +0.0043] | 4 / 8 |
| val1 | recovered | stable | order_up_to | shortage | 50 | -5.8814 | [-8.9552, -4.0038] | 50 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.2713 | [+0.9178, +1.8739] | 0 / 50 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1726 | [+0.1512, +0.1962] | 50 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -2.3125 | [-5.2729, -0.4795] | 25 / 6 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.3905 | [+0.8433, +2.1113] | 1 / 47 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0192 | [+0.0062, +0.0314] | 25 / 6 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -2.2765 | [-5.3554, -0.4440] | 24 / 8 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3793 | [+0.8359, +2.0922] | 3 / 47 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0176 | [+0.0054, +0.0302] | 24 / 8 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -1.8658 | [-4.6364, -0.2408] | 21 / 14 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.2551 | [+0.7512, +1.9167] | 5 / 45 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0125 | [-0.0003, +0.0246] | 21 / 14 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -8.4632 | [-14.7599, -4.6264] | 49 / 0 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.4520 | [+1.6793, +3.6557] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1887 | [+0.1654, +0.2123] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.1904 | [-0.5547, +0.1394] | 18 / 9 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.5562 | [+0.8157, +2.6354] | 2 / 46 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0074 | [-0.0034, +0.0192] | 18 / 9 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.1631 | [-0.5165, +0.1462] | 15 / 11 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.5414 | [+0.8047, +2.5675] | 4 / 45 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0064 | [-0.0047, +0.0176] | 15 / 11 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.0122 | [-0.3417, +0.2890] | 11 / 18 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.3798 | [+0.6968, +2.3346] | 5 / 45 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0012 | [-0.0100, +0.0121] | 11 / 18 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -5.1034 | [-7.7577, -3.4201] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.7645 | [+1.7392, +4.2936] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1511 | [+0.1273, +0.1764] | 48 / 1 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.6734 | [-1.0060, -0.3666] | 23 / 4 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.6743 | [+0.4570, +0.9489] | 3 / 47 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0259 | [+0.0114, +0.0474] | 23 / 4 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.6304 | [-0.9657, -0.3337] | 22 / 6 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.6646 | [+0.4496, +0.9467] | 5 / 45 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0240 | [+0.0092, +0.0453] | 22 / 6 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.6304 | [-0.9639, -0.3271] | 22 / 6 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.6646 | [+0.4383, +0.9361] | 5 / 45 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0240 | [+0.0095, +0.0444] | 22 / 6 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -6.7892 | [-9.9864, -4.7044] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.8631 | [+1.3144, +2.6735] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1957 | [+0.1728, +0.2201] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.0541 | [-0.1341, -0.0006] | 6 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0678 | [+0.0326, +0.1153] | 5 / 28 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0056 | [+0.0004, +0.0141] | 6 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 50 | +0.0591 | [-0.0099, +0.1346] | 6 / 11 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0548 | [+0.0180, +0.1070] | 19 / 29 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0014 | [-0.0055, +0.0032] | 6 / 11 |
| val2 | observed | stable | base_stock | shortage | 50 | +0.0591 | [-0.0081, +0.1314] | 6 / 11 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0548 | [+0.0181, +0.1074] | 19 / 29 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | -0.0014 | [-0.0056, +0.0030] | 6 / 11 |
| val2 | observed | stable | order_up_to | shortage | 50 | -5.3174 | [-9.1455, -3.1315] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9381 | [+0.6788, +1.3409] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1644 | [+0.1419, +0.1896] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -1.2638 | [-2.2653, -0.6338] | 32 / 4 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.4230 | [+0.8428, +2.2335] | 1 / 49 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0332 | [+0.0225, +0.0443] | 32 / 4 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -1.2160 | [-2.2048, -0.5750] | 31 / 7 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.4213 | [+0.8481, +2.2210] | 1 / 49 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0301 | [+0.0198, +0.0413] | 31 / 7 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -0.8340 | [-1.2737, -0.4764] | 30 / 7 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.3040 | [+0.7759, +2.0056] | 3 / 47 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0261 | [+0.0157, +0.0376] | 30 / 7 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -6.6238 | [-11.4817, -3.7951] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +2.0988 | [+1.4150, +3.0910] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1903 | [+0.1686, +0.2149] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.8131 | [-1.4405, -0.3339] | 25 / 2 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.4556 | [+0.8062, +2.4135] | 0 / 50 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0256 | [+0.0111, +0.0456] | 25 / 2 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.7766 | [-1.3746, -0.3116] | 24 / 2 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.4456 | [+0.8106, +2.3838] | 1 / 49 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0228 | [+0.0100, +0.0410] | 24 / 2 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.5661 | [-0.9606, -0.2345] | 17 / 8 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.3122 | [+0.7302, +2.2129] | 5 / 45 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0203 | [+0.0072, +0.0382] | 17 / 8 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -4.9314 | [-8.7071, -2.7906] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.2716 | [+1.5153, +3.3988] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1500 | [+0.1230, +0.1821] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.8289 | [-1.3493, -0.4153] | 24 / 1 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.9043 | [+0.3923, +1.7688] | 3 / 47 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0253 | [+0.0152, +0.0369] | 24 / 1 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.8057 | [-1.3203, -0.3883] | 23 / 3 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.8956 | [+0.3873, +1.7630] | 3 / 47 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0240 | [+0.0137, +0.0358] | 23 / 3 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.8008 | [-1.3184, -0.3691] | 23 / 3 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.8954 | [+0.3835, +1.7678] | 3 / 47 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0237 | [+0.0134, +0.0356] | 23 / 3 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -6.2694 | [-10.3779, -3.6232] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7113 | [+1.0326, +2.8698] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1743 | [+0.1533, +0.1977] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.1270 | [-0.2468, -0.0328] | 8 / 0 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0717 | [+0.0422, +0.1057] | 0 / 31 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0079 | [+0.0016, +0.0171] | 8 / 0 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | -0.0124 | [-0.1204, +0.0839] | 8 / 9 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0363 | [+0.0037, +0.0753] | 24 / 24 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0008 | [-0.0043, +0.0063] | 8 / 9 |
| val2 | recovered | stable | base_stock | shortage | 50 | -0.0124 | [-0.1197, +0.0865] | 8 / 9 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0363 | [+0.0035, +0.0736] | 24 / 24 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | +0.0008 | [-0.0043, +0.0064] | 8 / 9 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -5.7590 | [-8.7772, -3.9074] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.3402 | [+0.9650, +1.9574] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1728 | [+0.1508, +0.1962] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -3.0858 | [-7.4033, -0.7431] | 27 / 4 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.5539 | [+0.8496, +2.6672] | 1 / 49 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0369 | [+0.0198, +0.0577] | 27 / 4 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -3.0340 | [-7.2550, -0.6755] | 26 / 7 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.5456 | [+0.8457, +2.6922] | 2 / 48 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0341 | [+0.0165, +0.0543] | 26 / 7 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -2.5585 | [-6.0685, -0.5329] | 24 / 11 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.4039 | [+0.7304, +2.3793] | 3 / 47 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0304 | [+0.0126, +0.0501] | 24 / 11 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -9.6593 | [-18.1924, -4.7702] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.5860 | [+1.6952, +4.0495] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2056 | [+0.1783, +0.2367] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -1.7233 | [-4.4892, -0.1536] | 26 / 4 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.3875 | [+0.7620, +2.2868] | 3 / 46 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0167 | [+0.0003, +0.0305] | 26 / 4 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -1.6800 | [-4.4044, -0.1408] | 25 / 6 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.3702 | [+0.7573, +2.2896] | 4 / 46 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0137 | [-0.0018, +0.0270] | 25 / 6 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -1.4372 | [-3.8430, -0.0184] | 22 / 10 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.2073 | [+0.6333, +2.0179] | 5 / 45 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0104 | [-0.0046, +0.0239] | 22 / 10 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -6.5798 | [-11.8092, -3.5051] | 46 / 2 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.5934 | [+1.7567, +3.9170] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1574 | [+0.1328, +0.1820] | 46 / 2 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -2.1540 | [-4.4265, -0.7346] | 31 / 2 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7373 | [+0.3561, +1.3569] | 3 / 45 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0330 | [+0.0213, +0.0461] | 31 / 2 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -2.0215 | [-4.4484, -0.6203] | 29 / 4 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7247 | [+0.3450, +1.3853] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0284 | [+0.0171, +0.0412] | 29 / 4 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -2.0152 | [-4.3142, -0.6169] | 29 / 4 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.7245 | [+0.3440, +1.3638] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0280 | [+0.0169, +0.0410] | 29 / 4 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -7.9261 | [-12.9682, -4.6410] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.9590 | [+1.2741, +3.1170] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1938 | [+0.1732, +0.2141] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1200 of 1200 (9115 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus reorder_point = +8.792 (fill 0.679 vs 0.918, inventory 5.17 vs 3.23, retained incumbent on 10 reviews)
- val2/observed/uncertain_fill_only store 102 product 467: ZAAD minus reorder_point = +7.247 (fill 1.000 vs 0.987, inventory 6.02 vs 3.62, retained incumbent on 7 reviews)
- val2/recovered/uncertain_fill_only store 102 product 467: ZAAD minus reorder_point = +7.190 (fill 1.000 vs 0.988, inventory 6.00 vs 3.64, retained incumbent on 7 reviews)
- val2/observed/uncertain store 869 product 191: ZAAD minus base_stock = +7.081 (fill 0.969 vs 0.969, inventory 5.94 vs 2.14, retained incumbent on 8 reviews)
- val2/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +6.794 (fill 0.985 vs 0.977, inventory 29.90 vs 11.56, retained incumbent on 3 reviews)
- val2/recovered/uncertain store 855 product 647: ZAAD minus reorder_point = +6.476 (fill 0.799 vs 0.918, inventory 5.33 vs 3.28, retained incumbent on 10 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +6.434 (fill 0.922 vs 0.922, inventory 47.55 vs 20.54, retained incumbent on 4 reviews)
- val1/recovered/uncertain store 75 product 350: ZAAD minus reorder_point = +5.466 (fill 0.836 vs 1.000, inventory 3.16 vs 2.01, retained incumbent on 8 reviews)
- val2/observed/uncertain_fill_only store 869 product 191: ZAAD minus reorder_point = +5.422 (fill 0.969 vs 0.969, inventory 5.15 vs 2.42, retained incumbent on 6 reviews)
- val2/recovered/uncertain store 102 product 467: ZAAD minus periodic:1 = +5.268 (fill 0.981 vs 0.906, inventory 5.77 vs 2.57, retained incumbent on 7 reviews)
