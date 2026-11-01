# FreshRetailNet pilot results: stage `fifty_reference_v1`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `8367dc64da5e`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3591 s, peak RSS 221 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.15 |
| final | observed | stable | gated | 50/50 | 10.179 | 10.579 | 9.432 | 0.0071 | 0.278 | 0.985 | 0.185 | 2.071 | 0.4 | 5.4 | 0.29 | 0.62 |
| final | observed | stable | order_up_to | 50/50 | 10.699 | 11.052 | 8.089 | 0.0023 | 1.877 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.10 |
| final | observed | stable | periodic:1 | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.03 |
| final | observed | stable | reorder_point | 50/50 | 10.214 | 10.601 | 9.285 | 0.0055 | 0.391 | 0.978 | 0.261 | 1.585 | 0.5 | 5.3 |  | 0.03 |
| final | observed | uncertain | base_stock | 50/50 | 12.342 | 13.358 | 12.809 | 0.0053 | 2.166 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.193 | 13.095 | 12.654 | 0.0095 | 1.664 | 0.910 | 1.109 | 2.764 | 1.1 | 3.9 | 0.52 | 0.58 |
| final | observed | uncertain | order_up_to | 50/50 | 12.460 | 13.150 | 9.724 | 0.0027 | 3.695 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.170 | 12.919 | 11.231 | 0.0048 | 2.228 | 0.883 | 1.485 | 1.397 | 1.4 | 5.5 |  | 0.03 |
| final | observed | uncertain | reorder_point | 50/50 | 12.173 | 12.922 | 11.221 | 0.0048 | 2.241 | 0.881 | 1.494 | 1.395 | 1.5 | 5.3 |  | 0.03 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 11.704 | 12.703 | 13.134 | 0.0064 | 1.142 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.334 | 12.084 | 11.734 | 0.0094 | 1.015 | 0.957 | 0.677 | 2.726 | 0.8 | 4.2 | 0.54 | 0.70 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 11.929 | 12.589 | 10.129 | 0.0033 | 2.608 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.10 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.486 | 12.194 | 11.391 | 0.0060 | 1.205 | 0.947 | 0.803 | 1.731 | 1.0 | 5.6 |  | 0.03 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.487 | 12.195 | 11.382 | 0.0060 | 1.211 | 0.947 | 0.807 | 1.728 | 1.0 | 5.3 |  | 0.02 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 10.884 | 11.936 | 11.336 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.12 |
| final | observed | uncertain_lead_only | gated | 50/50 | 10.769 | 11.582 | 10.446 | 0.0084 | 1.989 | 0.919 | 1.326 | 2.421 | 1.1 | 4.0 | 0.54 | 0.65 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 11.365 | 12.079 | 8.578 | 0.0025 | 3.868 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.09 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 10.882 | 11.677 | 10.039 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 5.4 |  | 0.03 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 10.891 | 11.689 | 10.028 | 0.0050 | 2.404 | 0.895 | 1.603 | 1.444 | 1.3 | 5.0 |  | 0.02 |
| final | recovered | stable | base_stock | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.15 |
| final | recovered | stable | gated | 50/50 | 11.333 | 11.831 | 10.592 | 0.0083 | 0.215 | 0.979 | 0.143 | 2.393 | 0.4 | 5.3 | 0.30 | 0.57 |
| final | recovered | stable | order_up_to | 50/50 | 12.024 | 12.432 | 8.640 | 0.0030 | 2.350 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.10 |
| final | recovered | stable | periodic:1 | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.03 |
| final | recovered | stable | reorder_point | 50/50 | 11.371 | 11.882 | 10.526 | 0.0076 | 0.353 | 0.971 | 0.235 | 2.192 | 0.5 | 5.1 |  | 0.03 |
| final | recovered | uncertain | base_stock | 50/50 | 13.746 | 14.957 | 14.958 | 0.0069 | 1.855 | 0.896 | 1.237 | 1.994 | 1.3 | 6.2 |  | 0.12 |
| final | recovered | uncertain | gated | 50/50 | 13.760 | 14.908 | 14.958 | 0.0112 | 1.640 | 0.910 | 1.093 | 3.240 | 1.1 | 3.9 | 0.50 | 0.57 |
| final | recovered | uncertain | order_up_to | 50/50 | 13.814 | 14.586 | 10.883 | 0.0030 | 3.719 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.09 |
| final | recovered | uncertain | periodic:1 | 50/50 | 13.533 | 14.451 | 13.214 | 0.0064 | 1.892 | 0.894 | 1.261 | 1.841 | 1.3 | 5.5 |  | 0.03 |
| final | recovered | uncertain | reorder_point | 50/50 | 13.547 | 14.464 | 13.192 | 0.0063 | 1.925 | 0.889 | 1.283 | 1.832 | 1.4 | 5.0 |  | 0.03 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 12.878 | 14.085 | 15.203 | 0.0085 | 0.730 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.557 | 13.462 | 13.550 | 0.0114 | 0.681 | 0.962 | 0.454 | 3.313 | 0.7 | 4.0 | 0.51 | 0.71 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 13.158 | 13.908 | 11.255 | 0.0040 | 2.580 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.637 | 13.532 | 13.331 | 0.0080 | 0.776 | 0.956 | 0.517 | 2.306 | 0.9 | 5.5 |  | 0.03 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.643 | 13.540 | 13.318 | 0.0079 | 0.803 | 0.953 | 0.535 | 2.301 | 0.9 | 5.0 |  | 0.02 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 11.907 | 13.171 | 13.295 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 6.2 |  | 0.12 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 11.795 | 12.758 | 12.104 | 0.0096 | 1.551 | 0.928 | 1.034 | 2.789 | 1.0 | 3.9 | 0.51 | 0.62 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 12.531 | 13.337 | 9.627 | 0.0030 | 3.866 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.10 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 11.905 | 12.891 | 11.894 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 5.3 |  | 0.02 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 11.916 | 12.902 | 11.858 | 0.0067 | 1.970 | 0.908 | 1.314 | 1.931 | 1.3 | 4.7 |  | 0.03 |
| val1 | observed | stable | base_stock | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.53 |
| val1 | observed | stable | gated | 50/50 | 18.208 | 18.722 | 18.222 | 0.0157 | 0.534 | 0.968 | 0.356 | 1.676 | 1.0 | 12.4 | 0.15 | 4.27 |
| val1 | observed | stable | order_up_to | 50/50 | 19.352 | 19.639 | 14.512 | 0.0047 | 4.260 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.250 | 18.733 | 17.901 | 0.0124 | 0.745 | 0.956 | 0.497 | 1.350 | 1.3 | 11.1 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 21.214 | 21.993 | 19.912 | 0.0144 | 3.244 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.41 |
| val1 | observed | uncertain | gated | 50/50 | 22.132 | 23.261 | 24.225 | 0.0797 | 1.665 | 0.946 | 1.110 | 3.843 | 1.3 | 9.5 | 0.48 | 2.60 |
| val1 | observed | uncertain | order_up_to | 50/50 | 22.165 | 22.764 | 15.839 | 0.0061 | 7.330 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 21.255 | 22.008 | 19.576 | 0.0131 | 3.487 | 0.889 | 2.324 | 1.452 | 2.8 | 12.3 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 21.268 | 22.020 | 19.550 | 0.0130 | 3.517 | 0.887 | 2.344 | 1.444 | 2.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 20.705 | 21.519 | 20.968 | 0.0171 | 1.839 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.44 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.386 | 22.575 | 24.212 | 0.0508 | 1.461 | 0.953 | 0.974 | 3.632 | 1.1 | 9.2 | 0.57 | 3.16 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.251 | 21.819 | 17.195 | 0.0073 | 4.899 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.23 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 20.728 | 21.511 | 20.717 | 0.0157 | 1.950 | 0.923 | 1.300 | 1.582 | 1.9 | 12.4 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 20.722 | 21.503 | 20.686 | 0.0157 | 1.965 | 0.922 | 1.310 | 1.571 | 1.9 | 11.4 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.43 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 18.891 | 19.979 | 20.576 | 0.0346 | 1.891 | 0.932 | 1.261 | 2.949 | 1.5 | 11.7 | 0.46 | 3.07 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.239 | 20.878 | 14.535 | 0.0062 | 6.896 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.24 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.05 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.995 | 19.817 | 18.215 | 0.0150 | 2.921 | 0.873 | 1.948 | 1.487 | 2.7 | 10.7 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.55 |
| val1 | recovered | stable | gated | 50/50 | 22.059 | 22.710 | 21.686 | 0.0190 | 0.852 | 0.960 | 0.568 | 2.184 | 0.9 | 12.1 | 0.16 | 4.00 |
| val1 | recovered | stable | order_up_to | 50/50 | 23.462 | 23.845 | 17.176 | 0.0057 | 5.398 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.22 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.097 | 22.692 | 21.202 | 0.0153 | 1.062 | 0.953 | 0.708 | 1.799 | 1.1 | 10.6 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 25.601 | 26.598 | 24.322 | 0.0170 | 3.536 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.42 |
| val1 | recovered | uncertain | gated | 50/50 | 25.958 | 27.367 | 29.197 | 0.0677 | 1.407 | 0.940 | 0.938 | 4.701 | 1.2 | 9.0 | 0.48 | 2.59 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 26.729 | 27.472 | 19.189 | 0.0071 | 8.484 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.23 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 25.645 | 26.609 | 23.883 | 0.0156 | 3.844 | 0.905 | 2.563 | 1.897 | 2.2 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 25.652 | 26.613 | 23.851 | 0.0156 | 3.871 | 0.904 | 2.581 | 1.886 | 2.2 | 10.9 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 24.845 | 25.831 | 25.415 | 0.0202 | 1.614 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.667 | 26.756 | 27.468 | 0.0606 | 1.226 | 0.953 | 0.817 | 4.196 | 1.0 | 8.9 | 0.53 | 3.04 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 25.552 | 26.242 | 20.790 | 0.0082 | 5.432 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.23 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 24.827 | 25.767 | 25.057 | 0.0185 | 1.727 | 0.932 | 1.151 | 2.055 | 1.6 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 24.830 | 25.769 | 25.031 | 0.0184 | 1.747 | 0.931 | 1.165 | 2.040 | 1.7 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.40 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 22.621 | 23.933 | 25.009 | 0.0422 | 1.603 | 0.940 | 1.069 | 3.562 | 1.3 | 11.4 | 0.43 | 2.95 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 24.224 | 25.019 | 17.761 | 0.0070 | 7.654 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.22 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 22.766 | 23.820 | 22.239 | 0.0175 | 3.067 | 0.897 | 2.045 | 1.950 | 2.1 | 10.2 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.53 |
| val2 | observed | stable | gated | 50/50 | 18.171 | 18.701 | 18.171 | 0.0145 | 0.472 | 0.973 | 0.315 | 1.596 | 0.8 | 12.6 | 0.16 | 3.78 |
| val2 | observed | stable | order_up_to | 50/50 | 19.497 | 19.844 | 14.397 | 0.0047 | 4.632 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.06 |
| val2 | observed | stable | reorder_point | 50/50 | 18.238 | 18.753 | 17.934 | 0.0129 | 0.685 | 0.960 | 0.456 | 1.341 | 1.1 | 11.4 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 50/50 | 21.384 | 22.252 | 20.616 | 0.0143 | 2.937 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.42 |
| val2 | observed | uncertain | gated | 50/50 | 21.612 | 22.760 | 24.250 | 0.0410 | 1.216 | 0.944 | 0.810 | 3.231 | 1.1 | 9.5 | 0.52 | 2.73 |
| val2 | observed | uncertain | order_up_to | 50/50 | 22.247 | 22.882 | 15.949 | 0.0055 | 7.279 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.24 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 21.464 | 22.307 | 20.285 | 0.0131 | 3.223 | 0.896 | 2.149 | 1.265 | 2.2 | 12.3 |  | 0.06 |
| val2 | observed | uncertain | reorder_point | 50/50 | 21.476 | 22.320 | 20.265 | 0.0130 | 3.259 | 0.893 | 2.173 | 1.263 | 2.2 | 11.6 |  | 0.05 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.376 | 22.181 | 21.984 | 0.0153 | 1.255 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.43 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 22.098 | 23.135 | 24.642 | 0.0449 | 0.757 | 0.957 | 0.504 | 3.271 | 0.9 | 9.5 | 0.59 | 3.21 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.676 | 22.223 | 17.687 | 0.0057 | 4.529 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.24 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.365 | 22.142 | 21.677 | 0.0140 | 1.413 | 0.937 | 0.942 | 1.438 | 1.3 | 12.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.355 | 22.133 | 21.645 | 0.0138 | 1.440 | 0.935 | 0.960 | 1.428 | 1.4 | 11.7 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 18.788 | 19.627 | 18.553 | 0.0141 | 2.276 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.43 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 18.652 | 19.771 | 20.956 | 0.0310 | 1.232 | 0.930 | 0.822 | 2.866 | 1.1 | 12.0 | 0.44 | 3.31 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.083 | 20.658 | 14.388 | 0.0059 | 6.378 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.25 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.789 | 19.629 | 18.550 | 0.0141 | 2.280 | 0.888 | 1.520 | 1.456 | 2.2 | 12.0 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.789 | 19.630 | 18.536 | 0.0138 | 2.297 | 0.887 | 1.532 | 1.448 | 2.2 | 10.9 |  | 0.05 |
| val2 | recovered | stable | base_stock | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.55 |
| val2 | recovered | stable | gated | 50/50 | 22.990 | 23.715 | 22.347 | 0.0196 | 1.604 | 0.957 | 1.069 | 2.353 | 0.9 | 12.0 | 0.17 | 4.36 |
| val2 | recovered | stable | order_up_to | 50/50 | 24.427 | 24.833 | 17.222 | 0.0065 | 6.326 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.23 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.081 | 23.774 | 21.565 | 0.0169 | 2.102 | 0.940 | 1.401 | 1.948 | 1.3 | 10.5 |  | 0.06 |
| val2 | recovered | uncertain | base_stock | 50/50 | 26.668 | 27.674 | 24.888 | 0.0195 | 4.100 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.43 |
| val2 | recovered | uncertain | gated | 50/50 | 27.182 | 28.730 | 32.098 | 0.0481 | 1.617 | 0.947 | 1.078 | 4.480 | 1.1 | 9.0 | 0.51 | 2.56 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 27.706 | 28.419 | 18.942 | 0.0081 | 9.425 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.24 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 26.724 | 27.697 | 24.369 | 0.0180 | 4.456 | 0.895 | 2.971 | 1.961 | 2.1 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 26.729 | 27.701 | 24.330 | 0.0179 | 4.495 | 0.892 | 2.997 | 1.953 | 2.1 | 10.9 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 26.760 | 27.808 | 26.642 | 0.0209 | 2.544 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.43 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 27.930 | 29.176 | 30.162 | 0.0491 | 2.078 | 0.955 | 1.385 | 3.941 | 0.9 | 9.2 | 0.54 | 3.10 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.143 | 27.815 | 21.195 | 0.0082 | 6.401 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.24 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 26.735 | 27.739 | 26.208 | 0.0191 | 2.726 | 0.931 | 1.818 | 2.158 | 1.5 | 12.2 |  | 0.06 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 26.716 | 27.718 | 26.143 | 0.0190 | 2.759 | 0.928 | 1.839 | 2.140 | 1.5 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.675 | 24.745 | 22.603 | 0.0206 | 3.672 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.43 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.395 | 24.728 | 26.323 | 0.0345 | 1.831 | 0.928 | 1.221 | 3.681 | 1.2 | 11.6 | 0.42 | 3.19 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 25.025 | 25.713 | 17.457 | 0.0083 | 8.105 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.25 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.676 | 24.747 | 22.600 | 0.0206 | 3.677 | 0.883 | 2.451 | 2.187 | 2.2 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.708 | 24.778 | 22.525 | 0.0205 | 3.776 | 0.878 | 2.517 | 2.174 | 2.3 | 10.1 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | -0.035 | [-0.054, -0.017] | [-0.067, -0.011] | 28 / 22 / 0 | 0.48 |
| final | observed | stable | periodic:1 | 50 | -0.029 | [-0.047, -0.013] | [-0.059, -0.008] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | base_stock | 50 | -0.029 | [-0.047, -0.013] | [-0.059, -0.008] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | order_up_to | 50 | -0.520 | [-0.633, -0.419] | [-0.695, -0.373] | 46 / 4 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | +0.020 | [-0.109, +0.146] | [-0.177, +0.220] | 24 / 26 / 0 | 0.888 |
| final | observed | uncertain | periodic:1 | 50 | +0.023 | [-0.105, +0.155] | [-0.175, +0.217] | 24 / 26 / 0 | 0.888 |
| final | observed | uncertain | base_stock | 50 | -0.148 | [-0.274, -0.027] | [-0.344, +0.034] | 31 / 19 / 0 | 0.119 |
| final | observed | uncertain | order_up_to | 50 | -0.266 | [-0.440, -0.084] | [-0.541, +0.015] | 35 / 15 / 0 | 0.007 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.153 | [-0.361, +0.038] | [-0.509, +0.083] | 24 / 26 / 0 | 0.888 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.153 | [-0.360, +0.042] | [-0.522, +0.084] | 23 / 27 / 0 | 0.672 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.370 | [-0.694, -0.078] | [-0.935, -0.027] | 29 / 21 / 0 | 0.322 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -0.595 | [-0.948, -0.299] | [-1.161, -0.207] | 35 / 15 / 0 | 0.007 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.122 | [-0.198, -0.052] | [-0.248, -0.026] | 25 / 25 / 0 | 1.0 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.112 | [-0.180, -0.053] | [-0.222, -0.029] | 24 / 26 / 0 | 0.888 |
| final | observed | uncertain_lead_only | base_stock | 50 | -0.114 | [-0.182, -0.053] | [-0.226, -0.027] | 31 / 19 / 0 | 0.119 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -0.595 | [-0.747, -0.447] | [-0.858, -0.385] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | -0.037 | [-0.062, -0.013] | [-0.076, +0.001] | 25 / 25 / 0 | 1.0 |
| final | recovered | stable | periodic:1 | 50 | -0.025 | [-0.048, -0.002] | [-0.062, +0.010] | 42 / 8 / 0 | 0.0 |
| final | recovered | stable | base_stock | 50 | -0.025 | [-0.049, -0.002] | [-0.060, +0.010] | 42 / 8 / 0 | 0.0 |
| final | recovered | stable | order_up_to | 50 | -0.691 | [-0.857, -0.535] | [-0.958, -0.471] | 44 / 6 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | +0.213 | [+0.109, +0.315] | [+0.059, +0.374] | 24 / 26 / 0 | 0.888 |
| final | recovered | uncertain | periodic:1 | 50 | +0.227 | [+0.125, +0.334] | [+0.074, +0.395] | 22 / 28 / 0 | 0.48 |
| final | recovered | uncertain | base_stock | 50 | +0.013 | [-0.074, +0.105] | [-0.120, +0.152] | 31 / 19 / 0 | 0.119 |
| final | recovered | uncertain | order_up_to | 50 | -0.055 | [-0.196, +0.099] | [-0.270, +0.186] | 28 / 22 / 0 | 0.48 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.086 | [-0.296, +0.102] | [-0.449, +0.161] | 28 / 22 / 0 | 0.48 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.080 | [-0.294, +0.110] | [-0.454, +0.170] | 28 / 22 / 0 | 0.48 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.321 | [-0.653, -0.017] | [-0.885, +0.051] | 33 / 17 / 0 | 0.033 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -0.602 | [-0.957, -0.287] | [-1.208, -0.199] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.121 | [-0.204, -0.049] | [-0.255, -0.021] | 28 / 22 / 0 | 0.48 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.110 | [-0.185, -0.043] | [-0.233, -0.017] | 28 / 22 / 0 | 0.48 |
| final | recovered | uncertain_lead_only | base_stock | 50 | -0.112 | [-0.190, -0.043] | [-0.239, -0.018] | 33 / 17 / 0 | 0.033 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -0.736 | [-0.945, -0.531] | [-1.084, -0.455] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.042 | [-0.077, -0.007] | [-0.095, +0.014] | 27 / 23 / 0 | 0.672 |
| val1 | observed | stable | periodic:1 | 50 | -0.033 | [-0.064, +0.004] | [-0.081, +0.024] | 25 / 25 / 0 | 1.0 |
| val1 | observed | stable | base_stock | 50 | -0.033 | [-0.065, +0.003] | [-0.083, +0.023] | 25 / 25 / 0 | 1.0 |
| val1 | observed | stable | order_up_to | 50 | -1.143 | [-1.471, -0.854] | [-1.728, -0.753] | 48 / 2 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | +0.864 | [+0.351, +1.435] | [+0.199, +1.826] | 20 / 30 / 0 | 0.203 |
| val1 | observed | uncertain | periodic:1 | 50 | +0.877 | [+0.359, +1.440] | [+0.202, +1.850] | 19 / 31 / 0 | 0.119 |
| val1 | observed | uncertain | base_stock | 50 | +0.918 | [+0.356, +1.511] | [+0.227, +1.937] | 19 / 31 / 0 | 0.119 |
| val1 | observed | uncertain | order_up_to | 50 | -0.033 | [-0.339, +0.287] | [-0.488, +0.479] | 33 / 17 / 0 | 0.033 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.664 | [+0.356, +1.001] | [+0.226, +1.200] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.658 | [+0.343, +0.990] | [+0.210, +1.176] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.681 | [+0.358, +1.018] | [+0.216, +1.240] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | +0.135 | [-0.157, +0.442] | [-0.293, +0.643] | 30 / 20 / 0 | 0.203 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.104 | [-0.227, +0.021] | [-0.283, +0.093] | 34 / 16 / 0 | 0.015 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.096 | [-0.215, +0.032] | [-0.276, +0.103] | 33 / 17 / 0 | 0.033 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | -0.096 | [-0.222, +0.028] | [-0.283, +0.102] | 33 / 17 / 0 | 0.033 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -1.348 | [-1.876, -0.877] | [-2.255, -0.732] | 42 / 8 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | -0.037 | [-0.082, +0.006] | [-0.106, +0.030] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | stable | periodic:1 | 50 | -0.027 | [-0.070, +0.016] | [-0.096, +0.035] | 25 / 25 / 0 | 1.0 |
| val1 | recovered | stable | base_stock | 50 | -0.027 | [-0.072, +0.016] | [-0.099, +0.039] | 25 / 25 / 0 | 1.0 |
| val1 | recovered | stable | order_up_to | 50 | -1.403 | [-1.892, -1.000] | [-2.229, -0.899] | 48 / 2 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | +0.306 | [-0.338, +0.880] | [-0.873, +1.071] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain | periodic:1 | 50 | +0.313 | [-0.372, +0.882] | [-0.813, +1.072] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain | base_stock | 50 | +0.357 | [-0.273, +0.896] | [-0.704, +1.066] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain | order_up_to | 50 | -0.771 | [-1.879, +0.183] | [-2.692, +0.412] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +0.837 | [+0.551, +1.121] | [+0.411, +1.287] | 18 / 32 / 0 | 0.065 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.840 | [+0.559, +1.143] | [+0.425, +1.313] | 17 / 33 / 0 | 0.033 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +0.822 | [+0.531, +1.118] | [+0.388, +1.293] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | +0.115 | [-0.355, +0.567] | [-0.636, +0.764] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.145 | [-0.412, +0.108] | [-0.597, +0.211] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.135 | [-0.417, +0.116] | [-0.594, +0.218] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | -0.135 | [-0.416, +0.117] | [-0.579, +0.221] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -1.603 | [-2.306, -0.971] | [-2.845, -0.775] | 41 / 9 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | -0.067 | [-0.095, -0.041] | [-0.113, -0.029] | 29 / 21 / 0 | 0.322 |
| val2 | observed | stable | periodic:1 | 50 | -0.039 | [-0.063, -0.016] | [-0.077, -0.006] | 25 / 25 / 0 | 1.0 |
| val2 | observed | stable | base_stock | 50 | -0.039 | [-0.063, -0.016] | [-0.077, -0.006] | 25 / 25 / 0 | 1.0 |
| val2 | observed | stable | order_up_to | 50 | -1.326 | [-1.859, -0.837] | [-2.309, -0.759] | 50 / 0 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | +0.136 | [-0.252, +0.479] | [-0.519, +0.624] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain | periodic:1 | 50 | +0.148 | [-0.239, +0.497] | [-0.480, +0.651] | 21 / 29 / 0 | 0.322 |
| val2 | observed | uncertain | base_stock | 50 | +0.228 | [-0.064, +0.516] | [-0.245, +0.662] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain | order_up_to | 50 | -0.635 | [-1.380, +0.020] | [-1.917, +0.192] | 30 / 20 / 0 | 0.203 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.743 | [+0.435, +1.081] | [+0.287, +1.261] | 18 / 32 / 0 | 0.065 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.734 | [+0.424, +1.054] | [+0.276, +1.240] | 16 / 34 / 0 | 0.015 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.722 | [+0.410, +1.043] | [+0.259, +1.223] | 17 / 33 / 0 | 0.033 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | +0.423 | [+0.061, +0.772] | [-0.091, +0.969] | 25 / 25 / 0 | 1.0 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.137 | [-0.315, +0.037] | [-0.402, +0.149] | 27 / 23 / 0 | 0.672 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.137 | [-0.312, +0.033] | [-0.399, +0.123] | 26 / 24 / 0 | 0.888 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.136 | [-0.308, +0.034] | [-0.402, +0.127] | 26 / 24 / 0 | 0.888 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -1.431 | [-2.092, -0.859] | [-2.542, -0.666] | 44 / 6 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | -0.090 | [-0.213, +0.023] | [-0.293, +0.083] | 32 / 18 / 0 | 0.065 |
| val2 | recovered | stable | periodic:1 | 50 | -0.062 | [-0.184, +0.050] | [-0.261, +0.104] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | stable | base_stock | 50 | -0.062 | [-0.186, +0.054] | [-0.266, +0.109] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | stable | order_up_to | 50 | -1.436 | [-1.959, -0.975] | [-2.321, -0.883] | 48 / 2 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | +0.452 | [-0.077, +0.963] | [-0.398, +1.215] | 19 / 31 / 0 | 0.119 |
| val2 | recovered | uncertain | periodic:1 | 50 | +0.458 | [-0.082, +1.007] | [-0.417, +1.280] | 18 / 32 / 0 | 0.065 |
| val2 | recovered | uncertain | base_stock | 50 | +0.514 | [+0.041, +0.978] | [-0.240, +1.247] | 20 / 30 / 0 | 0.203 |
| val2 | recovered | uncertain | order_up_to | 50 | -0.524 | [-1.663, +0.431] | [-2.423, +0.761] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | +1.214 | [+0.780, +1.678] | [+0.584, +1.951] | 15 / 35 / 0 | 0.007 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | +1.195 | [+0.775, +1.638] | [+0.582, +1.909] | 14 / 36 / 0 | 0.003 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | +1.170 | [+0.748, +1.618] | [+0.568, +1.881] | 17 / 33 / 0 | 0.033 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | +0.787 | [+0.327, +1.283] | [+0.110, +1.557] | 25 / 25 / 0 | 1.0 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.313 | [-0.691, +0.032] | [-0.962, +0.189] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.281 | [-0.639, +0.072] | [-0.905, +0.202] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.280 | [-0.662, +0.074] | [-0.925, +0.227] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -1.630 | [-2.423, -0.949] | [-2.938, -0.735] | 43 / 7 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | -0.1138 | [-0.2021, -0.0425] | 19 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | +0.4856 | [+0.0857, +1.1977] | 8 / 42 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | +0.0069 | [+0.0028, +0.0117] | 19 / 1 |
| final | observed | stable | periodic:1 | shortage | 50 | -0.0911 | [-0.1793, -0.0276] | 16 / 1 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.4737 | [+0.0717, +1.2010] | 10 / 40 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0050 | [+0.0014, +0.0092] | 16 / 1 |
| final | observed | stable | base_stock | shortage | 50 | -0.0911 | [-0.1799, -0.0265] | 16 / 1 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | +0.4737 | [+0.0720, +1.2149] | 10 / 40 |
| final | observed | stable | base_stock | service_unit_fill | 50 | +0.0050 | [+0.0013, +0.0091] | 16 / 1 |
| final | observed | stable | order_up_to | shortage | 50 | -1.5993 | [-2.0959, -1.1637] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +1.4183 | [+0.7027, +2.6920] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1486 | [+0.1196, +0.1765] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.5768 | [-1.1563, -0.1571] | 21 / 4 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.3694 | [+0.5208, +2.8969] | 2 / 48 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0293 | [+0.0094, +0.0489] | 21 / 4 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.5644 | [-1.1555, -0.1481] | 21 / 4 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3673 | [+0.5189, +2.9280] | 2 / 48 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0277 | [+0.0074, +0.0470] | 21 / 4 |
| final | observed | uncertain | base_stock | shortage | 50 | -0.5026 | [-1.0489, -0.1085] | 19 / 4 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.2431 | [+0.4516, +2.6756] | 2 / 48 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0226 | [+0.0035, +0.0417] | 19 / 4 |
| final | observed | uncertain | order_up_to | shortage | 50 | -2.0310 | [-2.9173, -1.3069] | 40 / 1 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.9954 | [+0.9270, +3.9807] | 0 / 50 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1690 | [+0.1343, +0.2040] | 40 / 1 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.1960 | [-0.3610, -0.0613] | 15 / 4 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.9984 | [+0.3437, +2.1740] | 3 / 47 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0109 | [+0.0022, +0.0205] | 15 / 4 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.1901 | [-0.3640, -0.0537] | 13 / 4 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.9948 | [+0.3261, +2.1749] | 3 / 47 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0101 | [+0.0018, +0.0197] | 13 / 4 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1271 | [-0.2781, -0.0111] | 13 / 4 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.8668 | [+0.2481, +1.9922] | 5 / 45 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0068 | [-0.0011, +0.0155] | 13 / 4 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.5927 | [-2.1345, -1.1259] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.7639 | [+0.8225, +3.4416] | 0 / 50 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1417 | [+0.1116, +0.1731] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.4152 | [-0.7813, -0.1471] | 18 / 2 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.9779 | [+0.4347, +1.9039] | 3 / 47 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0238 | [+0.0125, +0.0363] | 18 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.3840 | [-0.7087, -0.1446] | 17 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.9704 | [+0.4183, +1.9077] | 3 / 47 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0228 | [+0.0124, +0.0347] | 17 / 2 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.3840 | [-0.7034, -0.1439] | 17 / 2 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.9704 | [+0.4256, +1.8948] | 3 / 47 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0228 | [+0.0125, +0.0344] | 17 / 2 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -1.8787 | [-2.6226, -1.2527] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.6999 | [+0.9190, +3.0759] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1574 | [+0.1255, +0.1888] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | -0.1379 | [-0.2401, -0.0466] | 15 / 2 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.2004 | [+0.0687, +0.3635] | 13 / 37 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0079 | [+0.0001, +0.0163] | 15 / 2 |
| final | recovered | stable | periodic:1 | shortage | 50 | -0.0950 | [-0.1859, -0.0078] | 15 / 2 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.1798 | [+0.0491, +0.3479] | 12 / 38 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0044 | [-0.0038, +0.0124] | 15 / 2 |
| final | recovered | stable | base_stock | shortage | 50 | -0.0950 | [-0.1914, -0.0035] | 15 / 2 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | +0.1798 | [+0.0543, +0.3472] | 12 / 38 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | +0.0044 | [-0.0039, +0.0127] | 15 / 2 |
| final | recovered | stable | order_up_to | shortage | 50 | -2.1356 | [-2.9177, -1.4757] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.5231 | [+0.9628, +2.3370] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1596 | [+0.1337, +0.1853] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.2851 | [-0.4770, -0.1133] | 19 / 3 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.4076 | [+0.5682, +2.8959] | 2 / 48 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0203 | [+0.0034, +0.0362] | 19 / 3 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.2519 | [-0.4464, -0.0947] | 18 / 3 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3986 | [+0.5572, +2.9320] | 2 / 48 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0161 | [+0.0004, +0.0304] | 18 / 3 |
| final | recovered | uncertain | base_stock | shortage | 50 | -0.2149 | [-0.3912, -0.0659] | 16 / 4 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.2458 | [+0.4678, +2.6625] | 2 / 48 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0134 | [-0.0019, +0.0270] | 16 / 4 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -2.0790 | [-2.7958, -1.4518] | 41 / 1 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.3759 | [+1.1688, +4.5352] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1637 | [+0.1298, +0.1973] | 41 / 1 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.1219 | [-0.3343, +0.0715] | 12 / 5 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.0123 | [+0.3921, +1.9847] | 5 / 45 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0085 | [+0.0006, +0.0173] | 12 / 5 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0946 | [-0.2972, +0.1041] | 12 / 5 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.0073 | [+0.3855, +1.9894] | 5 / 45 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0055 | [-0.0030, +0.0135] | 12 / 5 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.0486 | [-0.2470, +0.1395] | 10 / 5 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.8450 | [+0.2849, +1.7353] | 10 / 40 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0023 | [-0.0057, +0.0100] | 10 / 5 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -1.8993 | [-2.6335, -1.3019] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.1634 | [+1.1321, +3.8746] | 0 / 50 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1467 | [+0.1164, +0.1778] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.4199 | [-0.7978, -0.1310] | 18 / 4 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.8579 | [+0.4185, +1.5799] | 4 / 46 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0198 | [+0.0099, +0.0310] | 18 / 4 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.3804 | [-0.7384, -0.1132] | 17 / 4 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.8494 | [+0.4031, +1.5459] | 4 / 46 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0177 | [+0.0085, +0.0282] | 17 / 4 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.3804 | [-0.7493, -0.1174] | 17 / 4 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.8494 | [+0.4094, +1.5793] | 4 / 46 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0177 | [+0.0086, +0.0277] | 17 / 4 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -2.3153 | [-3.3464, -1.4788] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.9278 | [+1.1179, +3.3334] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1653 | [+0.1325, +0.1986] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.2109 | [-0.3258, -0.1103] | 30 / 3 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.3258 | [+0.2027, +0.4866] | 1 / 49 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0121 | [+0.0062, +0.0191] | 30 / 3 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.1832 | [-0.2919, -0.0879] | 28 / 3 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.3066 | [+0.1934, +0.4560] | 1 / 49 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0103 | [+0.0044, +0.0171] | 28 / 3 |
| val1 | observed | stable | base_stock | shortage | 50 | -0.1832 | [-0.2987, -0.0861] | 28 / 3 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | +0.3066 | [+0.1916, +0.4564] | 1 / 49 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | +0.0103 | [+0.0048, +0.0170] | 28 / 3 |
| val1 | observed | stable | order_up_to | shortage | 50 | -3.7259 | [-5.4012, -2.6587] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +1.2132 | [+0.8265, +1.8072] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1759 | [+0.1544, +0.1990] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -1.8511 | [-3.1672, -0.9536] | 40 / 0 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +2.3994 | [+1.1970, +4.5646] | 0 / 50 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0589 | [+0.0448, +0.0739] | 40 / 0 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -1.8212 | [-3.1476, -0.9475] | 40 / 0 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +2.3910 | [+1.1795, +4.5752] | 0 / 50 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0572 | [+0.0433, +0.0715] | 40 / 0 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.5786 | [-2.6541, -0.8259] | 39 / 0 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +2.2851 | [+1.1003, +4.3672] | 0 / 50 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0513 | [+0.0378, +0.0652] | 39 / 0 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -5.6651 | [-9.1373, -3.4871] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +3.1488 | [+1.7080, +5.7390] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.2185 | [+0.1967, +0.2410] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.5036 | [-0.6962, -0.3289] | 31 / 2 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +2.0604 | [+1.1176, +3.4999] | 0 / 50 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0308 | [+0.0185, +0.0438] | 31 / 2 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.4893 | [-0.6763, -0.3110] | 31 / 2 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +2.0494 | [+1.1233, +3.5584] | 0 / 50 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0301 | [+0.0184, +0.0433] | 31 / 2 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.3776 | [-0.5517, -0.2236] | 26 / 2 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.9083 | [+1.0314, +3.2211] | 0 / 50 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0245 | [+0.0137, +0.0373] | 26 / 2 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.4383 | [-4.8719, -2.4995] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.9224 | [+1.7234, +4.8534] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1681 | [+0.1449, +0.1925] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -1.0303 | [-1.3565, -0.7452] | 41 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +1.4620 | [+0.8441, +2.4650] | 0 / 50 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0592 | [+0.0405, +0.0846] | 41 / 0 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -1.0080 | [-1.3216, -0.7291] | 41 / 0 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +1.4548 | [+0.8422, +2.4909] | 0 / 50 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0565 | [+0.0398, +0.0774] | 41 / 0 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -1.0080 | [-1.3388, -0.7211] | 41 / 0 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +1.4548 | [+0.8382, +2.4791] | 0 / 50 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0565 | [+0.0392, +0.0792] | 41 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -5.0051 | [-7.5050, -3.3782] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +2.2973 | [+1.4162, +3.8112] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.2181 | [+0.1968, +0.2394] | 50 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 50 | -0.2102 | [-0.3922, -0.0790] | 28 / 1 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.3853 | [+0.2097, +0.6902] | 0 / 50 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0072 | [+0.0032, +0.0114] | 28 / 1 |
| val1 | recovered | stable | periodic:1 | shortage | 50 | -0.1794 | [-0.3616, -0.0502] | 27 / 1 |
| val1 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.3599 | [+0.1857, +0.6569] | 0 / 50 |
| val1 | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0046 | [+0.0015, +0.0083] | 27 / 1 |
| val1 | recovered | stable | base_stock | shortage | 50 | -0.1794 | [-0.3592, -0.0529] | 27 / 1 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.3599 | [+0.1846, +0.6559] | 0 / 50 |
| val1 | recovered | stable | base_stock | service_unit_fill | 50 | +0.0046 | [+0.0013, +0.0082] | 27 / 1 |
| val1 | recovered | stable | order_up_to | shortage | 50 | -4.5460 | [-6.8913, -3.1166] | 50 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.5857 | [+1.1181, +2.4246] | 0 / 50 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1781 | [+0.1568, +0.2005] | 50 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -2.4635 | [-5.0519, -0.8649] | 31 / 3 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +2.8155 | [+1.3260, +5.4143] | 0 / 50 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0357 | [+0.0045, +0.0591] | 31 / 3 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -2.4364 | [-5.0878, -0.8088] | 31 / 3 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +2.8044 | [+1.3246, +5.4336] | 0 / 50 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0341 | [+0.0045, +0.0582] | 31 / 3 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -2.1284 | [-4.5794, -0.6853] | 30 / 3 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +2.6801 | [+1.2285, +5.2174] | 0 / 50 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0290 | [+0.0015, +0.0504] | 30 / 3 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -7.0764 | [-12.1374, -3.9852] | 48 / 1 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +3.8771 | [+2.1541, +6.9663] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2052 | [+0.1742, +0.2341] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.5214 | [-0.8950, -0.1813] | 26 / 6 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +2.1558 | [+1.2741, +3.6421] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0223 | [+0.0096, +0.0366] | 26 / 6 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.5010 | [-0.8734, -0.1556] | 23 / 7 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +2.1410 | [+1.2504, +3.5895] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0212 | [+0.0087, +0.0352] | 23 / 7 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.3878 | [-0.7212, -0.0819] | 19 / 8 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.9794 | [+1.1411, +3.4212] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0161 | [+0.0045, +0.0282] | 19 / 8 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.2062 | [-6.2025, -2.9043] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +3.3641 | [+2.1854, +5.3167] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1660 | [+0.1409, +0.1922] | 49 / 0 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.4634 | [-2.6675, -0.6359] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +1.6116 | [+0.8955, +2.8099] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0430 | [+0.0258, +0.0660] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.4312 | [-2.6579, -0.6105] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +1.6019 | [+0.8945, +2.8466] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0411 | [+0.0239, +0.0629] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -1.4312 | [-2.6411, -0.6090] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +1.6019 | [+0.8870, +2.8300] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0411 | [+0.0241, +0.0635] | 30 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -6.0503 | [-9.5879, -3.8543] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +2.8004 | [+1.7729, +4.5504] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.2129 | [+0.1891, +0.2374] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.2124 | [-0.3286, -0.1120] | 29 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.2547 | [+0.1333, +0.4447] | 0 / 50 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0130 | [+0.0055, +0.0224] | 29 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 50 | -0.1275 | [-0.2298, -0.0441] | 25 / 1 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.2417 | [+0.1168, +0.4425] | 1 / 49 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0060 | [+0.0013, +0.0123] | 25 / 1 |
| val2 | observed | stable | base_stock | shortage | 50 | -0.1275 | [-0.2286, -0.0465] | 25 / 1 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | +0.2417 | [+0.1212, +0.4402] | 1 / 49 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | +0.0060 | [+0.0011, +0.0121] | 25 / 1 |
| val2 | observed | stable | order_up_to | shortage | 50 | -4.1598 | [-7.0901, -2.4837] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +1.1250 | [+0.7919, +1.6561] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1718 | [+0.1494, +0.1962] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -2.0433 | [-4.2441, -0.7452] | 37 / 1 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.9679 | [+1.1955, +3.0663] | 0 / 50 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0505 | [+0.0365, +0.0646] | 37 / 1 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -2.0074 | [-4.1798, -0.6893] | 37 / 1 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.9662 | [+1.2001, +3.0780] | 0 / 50 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0474 | [+0.0348, +0.0612] | 37 / 1 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -1.7209 | [-3.4789, -0.6371] | 36 / 1 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.8490 | [+1.1352, +2.8341] | 0 / 50 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0433 | [+0.0311, +0.0565] | 36 / 1 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -6.0633 | [-11.1888, -3.1619] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +2.6438 | [+1.7672, +3.9677] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.2076 | [+0.1843, +0.2326] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.6834 | [-1.2286, -0.2572] | 25 / 5 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.8434 | [+1.0330, +3.0676] | 0 / 50 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0226 | [+0.0109, +0.0359] | 25 / 5 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.6561 | [-1.1835, -0.2396] | 24 / 5 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.8334 | [+1.0309, +3.0620] | 0 / 50 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0198 | [+0.0098, +0.0320] | 24 / 5 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.4981 | [-0.9080, -0.1858] | 22 / 5 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.7000 | [+0.9557, +2.9095] | 0 / 50 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0173 | [+0.0069, +0.0291] | 22 / 5 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.7721 | [-6.7413, -2.0922] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.6594 | [+1.7367, +4.0642] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1470 | [+0.1231, +0.1731] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -1.0649 | [-1.6842, -0.5637] | 32 / 1 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +1.4188 | [+0.7613, +2.5596] | 0 / 50 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0432 | [+0.0289, +0.0590] | 32 / 1 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -1.0475 | [-1.6548, -0.5461] | 31 / 1 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +1.4101 | [+0.7527, +2.5317] | 0 / 50 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0418 | [+0.0274, +0.0580] | 31 / 1 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -1.0438 | [-1.6788, -0.5526] | 31 / 1 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +1.4099 | [+0.7539, +2.5348] | 0 / 50 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0415 | [+0.0270, +0.0574] | 31 / 1 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -5.1453 | [-8.3463, -3.0283] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +2.2258 | [+1.4025, +3.6356] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1921 | [+0.1695, +0.2176] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.4980 | [-1.0090, -0.1866] | 32 / 1 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.4050 | [+0.2055, +0.6823] | 1 / 49 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0176 | [+0.0096, +0.0274] | 32 / 1 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | -0.4121 | [-0.9228, -0.1203] | 30 / 1 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.3696 | [+0.1737, +0.6462] | 3 / 47 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0106 | [+0.0055, +0.0165] | 30 / 1 |
| val2 | recovered | stable | base_stock | shortage | 50 | -0.4121 | [-0.9155, -0.1140] | 30 / 1 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.3697 | [+0.1749, +0.6486] | 3 / 47 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | +0.0106 | [+0.0053, +0.0166] | 30 / 1 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -4.7220 | [-7.4612, -3.0916] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.6735 | [+1.1401, +2.4654] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1826 | [+0.1591, +0.2075] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -2.8777 | [-6.4077, -0.9345] | 34 / 2 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +2.5273 | [+1.4619, +4.2267] | 0 / 50 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0557 | [+0.0343, +0.0777] | 34 / 2 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -2.8389 | [-6.3174, -0.8795] | 34 / 2 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +2.5191 | [+1.4832, +4.2670] | 0 / 50 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0529 | [+0.0314, +0.0752] | 34 / 2 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -2.4823 | [-5.4263, -0.7757] | 34 / 2 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +2.3773 | [+1.3585, +3.9052] | 0 / 50 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0491 | [+0.0283, +0.0701] | 34 / 2 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -7.8078 | [-14.5164, -3.9650] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +3.5595 | [+2.2859, +5.5934] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2244 | [+0.1946, +0.2556] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.6811 | [-1.0824, -0.2996] | 31 / 2 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.8005 | [+1.1721, +2.6465] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0266 | [+0.0088, +0.0421] | 31 / 2 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.6487 | [-1.0435, -0.2813] | 30 / 2 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.7831 | [+1.1611, +2.6400] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0237 | [+0.0077, +0.0392] | 30 / 2 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.4666 | [-0.8532, -0.1147] | 27 / 3 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.6202 | [+1.0615, +2.3463] | 1 / 49 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0203 | [+0.0047, +0.0351] | 27 / 3 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.3235 | [-6.5139, -2.8443] | 47 / 1 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +3.0063 | [+2.1469, +4.2766] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1673 | [+0.1420, +0.1927] | 47 / 1 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.9448 | [-3.6799, -0.8454] | 36 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +1.5061 | [+0.8869, +2.4313] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0493 | [+0.0353, +0.0646] | 36 / 0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.8454 | [-3.6142, -0.7689] | 35 / 0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +1.4935 | [+0.8638, +2.4487] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0447 | [+0.0315, +0.0600] | 35 / 0 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -1.8407 | [-3.5716, -0.7805] | 35 / 0 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +1.4933 | [+0.8709, +2.4177] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0443 | [+0.0315, +0.0600] | 35 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -6.2739 | [-10.0151, -3.7672] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +2.7279 | [+1.7859, +4.1844] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.2101 | [+0.1875, +0.2322] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1199 of 1200 (8070 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/uncertain store 514 product 267: ZAAD minus base_stock = +21.538 (fill 0.922 vs 0.869, inventory 69.00 vs 20.64, retained incumbent on 3 reviews)
- val2/recovered/uncertain_fill_only store 514 product 267: ZAAD minus reorder_point = +11.439 (fill 0.912 vs 0.905, inventory 36.46 vs 17.79, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 230 product 580: ZAAD minus order_up_to = +11.137 (fill 0.796 vs 0.718, inventory 14.09 vs 3.53, retained incumbent on 8 reviews)
- val2/recovered/uncertain store 230 product 580: ZAAD minus order_up_to = +11.083 (fill 0.755 vs 0.648, inventory 19.59 vs 5.30, retained incumbent on 10 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +9.291 (fill 0.922 vs 0.922, inventory 50.57 vs 20.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain store 855 product 647: ZAAD minus order_up_to = +8.381 (fill 0.673 vs 0.642, inventory 5.12 vs 1.35, retained incumbent on 9 reviews)
- val1/observed/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +8.154 (fill 0.917 vs 0.883, inventory 8.08 vs 1.08, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus order_up_to = +8.016 (fill 0.679 vs 0.705, inventory 5.13 vs 1.27, retained incumbent on 11 reviews)
- val1/observed/uncertain store 869 product 191: ZAAD minus base_stock = +7.243 (fill 0.917 vs 0.917, inventory 6.82 vs 2.44, retained incumbent on 5 reviews)
- val2/observed/uncertain_fill_only store 730 product 447: ZAAD minus order_up_to = +6.917 (fill 1.000 vs 0.915, inventory 7.11 vs 1.30, retained incumbent on 3 reviews)
