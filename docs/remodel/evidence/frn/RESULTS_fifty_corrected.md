# FreshRetailNet pilot results: stage `fifty_corrected`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `26b6e5a6b0d4`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3674 s, peak RSS 219 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.15 |
| final | observed | stable | gated | 50/50 | 10.214 | 10.558 | 9.060 | 0.0055 | 0.394 | 0.978 | 0.263 | 1.604 | 0.5 | 5.1 | 0.11 | 0.65 |
| final | observed | stable | order_up_to | 50/50 | 10.699 | 11.052 | 8.089 | 0.0023 | 1.877 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.09 |
| final | observed | stable | periodic:1 | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.03 |
| final | observed | stable | reorder_point | 50/50 | 10.214 | 10.601 | 9.285 | 0.0055 | 0.391 | 0.978 | 0.261 | 1.585 | 0.5 | 5.3 |  | 0.02 |
| final | observed | uncertain | base_stock | 50/50 | 12.342 | 13.358 | 12.809 | 0.0053 | 2.166 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.124 | 12.844 | 11.212 | 0.0067 | 2.088 | 0.887 | 1.392 | 1.936 | 1.4 | 3.9 | 0.30 | 0.63 |
| final | observed | uncertain | order_up_to | 50/50 | 12.460 | 13.150 | 9.724 | 0.0027 | 3.695 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.170 | 12.919 | 11.231 | 0.0048 | 2.228 | 0.883 | 1.485 | 1.397 | 1.4 | 5.5 |  | 0.03 |
| final | observed | uncertain | reorder_point | 50/50 | 12.173 | 12.922 | 11.221 | 0.0048 | 2.241 | 0.881 | 1.494 | 1.395 | 1.5 | 5.3 |  | 0.03 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 11.704 | 12.703 | 13.134 | 0.0064 | 1.142 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.348 | 12.037 | 11.353 | 0.0082 | 1.072 | 0.951 | 0.715 | 2.375 | 0.9 | 4.1 | 0.34 | 0.74 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 11.929 | 12.589 | 10.129 | 0.0033 | 2.608 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.09 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.486 | 12.194 | 11.391 | 0.0060 | 1.205 | 0.947 | 0.803 | 1.731 | 1.0 | 5.6 |  | 0.03 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.487 | 12.195 | 11.382 | 0.0060 | 1.211 | 0.947 | 0.807 | 1.728 | 1.0 | 5.3 |  | 0.02 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 10.884 | 11.936 | 11.336 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.11 |
| final | observed | uncertain_lead_only | gated | 50/50 | 10.853 | 11.433 | 9.037 | 0.0054 | 2.279 | 0.903 | 1.520 | 1.552 | 1.2 | 4.3 | 0.32 | 0.72 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 11.365 | 12.079 | 8.578 | 0.0025 | 3.868 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.10 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 10.882 | 11.677 | 10.039 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 5.4 |  | 0.02 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 10.891 | 11.689 | 10.028 | 0.0050 | 2.404 | 0.895 | 1.603 | 1.444 | 1.3 | 5.0 |  | 0.02 |
| final | recovered | stable | base_stock | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.15 |
| final | recovered | stable | gated | 50/50 | 11.363 | 11.822 | 10.313 | 0.0077 | 0.315 | 0.975 | 0.210 | 2.219 | 0.5 | 4.9 | 0.13 | 0.60 |
| final | recovered | stable | order_up_to | 50/50 | 12.024 | 12.432 | 8.640 | 0.0030 | 2.350 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.09 |
| final | recovered | stable | periodic:1 | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.02 |
| final | recovered | stable | reorder_point | 50/50 | 11.371 | 11.882 | 10.526 | 0.0076 | 0.353 | 0.971 | 0.235 | 2.192 | 0.5 | 5.1 |  | 0.02 |
| final | recovered | uncertain | base_stock | 50/50 | 13.746 | 14.957 | 14.958 | 0.0069 | 1.855 | 0.896 | 1.237 | 1.994 | 1.3 | 6.2 |  | 0.11 |
| final | recovered | uncertain | gated | 50/50 | 13.554 | 14.384 | 13.049 | 0.0082 | 1.736 | 0.898 | 1.157 | 2.363 | 1.2 | 4.1 | 0.31 | 0.61 |
| final | recovered | uncertain | order_up_to | 50/50 | 13.814 | 14.586 | 10.883 | 0.0030 | 3.719 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.09 |
| final | recovered | uncertain | periodic:1 | 50/50 | 13.533 | 14.451 | 13.214 | 0.0064 | 1.892 | 0.894 | 1.261 | 1.841 | 1.3 | 5.5 |  | 0.02 |
| final | recovered | uncertain | reorder_point | 50/50 | 13.547 | 14.464 | 13.192 | 0.0063 | 1.925 | 0.889 | 1.283 | 1.832 | 1.4 | 5.0 |  | 0.02 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 12.878 | 14.085 | 15.203 | 0.0085 | 0.730 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.500 | 13.301 | 12.869 | 0.0107 | 0.764 | 0.956 | 0.509 | 3.099 | 0.7 | 4.0 | 0.35 | 0.72 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 13.158 | 13.908 | 11.255 | 0.0040 | 2.580 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.637 | 13.532 | 13.331 | 0.0080 | 0.776 | 0.956 | 0.517 | 2.306 | 0.9 | 5.5 |  | 0.02 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.643 | 13.540 | 13.318 | 0.0079 | 0.803 | 0.953 | 0.535 | 2.301 | 0.9 | 5.0 |  | 0.03 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 11.907 | 13.171 | 13.295 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 6.2 |  | 0.11 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 11.897 | 12.578 | 10.377 | 0.0069 | 1.909 | 0.910 | 1.273 | 1.994 | 1.2 | 4.0 | 0.34 | 0.68 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 12.531 | 13.337 | 9.627 | 0.0030 | 3.866 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.09 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 11.905 | 12.891 | 11.894 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 5.3 |  | 0.02 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 11.916 | 12.902 | 11.858 | 0.0067 | 1.970 | 0.908 | 1.314 | 1.931 | 1.3 | 4.7 |  | 0.03 |
| val1 | observed | stable | base_stock | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.53 |
| val1 | observed | stable | gated | 50/50 | 18.234 | 18.723 | 17.972 | 0.0128 | 0.693 | 0.961 | 0.462 | 1.413 | 1.2 | 11.2 | 0.08 | 4.47 |
| val1 | observed | stable | order_up_to | 50/50 | 19.352 | 19.639 | 14.512 | 0.0047 | 4.260 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.23 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.250 | 18.733 | 17.901 | 0.0124 | 0.745 | 0.956 | 0.497 | 1.350 | 1.3 | 11.1 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 21.214 | 21.993 | 19.912 | 0.0144 | 3.244 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.43 |
| val1 | observed | uncertain | gated | 50/50 | 21.212 | 22.132 | 21.672 | 0.0240 | 2.231 | 0.924 | 1.488 | 2.308 | 1.8 | 9.1 | 0.44 | 2.73 |
| val1 | observed | uncertain | order_up_to | 50/50 | 22.165 | 22.764 | 15.839 | 0.0061 | 7.330 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 21.255 | 22.008 | 19.576 | 0.0131 | 3.487 | 0.889 | 2.324 | 1.452 | 2.8 | 12.3 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 21.268 | 22.020 | 19.550 | 0.0130 | 3.517 | 0.887 | 2.344 | 1.444 | 2.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 20.705 | 21.519 | 20.968 | 0.0171 | 1.839 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.43 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.189 | 22.313 | 23.288 | 0.0414 | 1.665 | 0.938 | 1.110 | 3.304 | 1.4 | 8.8 | 0.47 | 3.29 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.251 | 21.819 | 17.195 | 0.0073 | 4.899 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.23 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 20.728 | 21.511 | 20.717 | 0.0157 | 1.950 | 0.923 | 1.300 | 1.582 | 1.9 | 12.4 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 20.722 | 21.503 | 20.686 | 0.0157 | 1.965 | 0.922 | 1.310 | 1.571 | 1.9 | 11.4 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.40 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 18.937 | 19.851 | 19.253 | 0.0248 | 2.357 | 0.908 | 1.572 | 2.179 | 1.9 | 11.0 | 0.44 | 3.11 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.239 | 20.878 | 14.535 | 0.0062 | 6.896 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.22 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.04 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.995 | 19.817 | 18.215 | 0.0150 | 2.921 | 0.873 | 1.948 | 1.487 | 2.7 | 10.7 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.52 |
| val1 | recovered | stable | gated | 50/50 | 22.073 | 22.670 | 21.256 | 0.0157 | 0.990 | 0.954 | 0.660 | 1.858 | 1.0 | 10.6 | 0.07 | 3.99 |
| val1 | recovered | stable | order_up_to | 50/50 | 23.462 | 23.845 | 17.176 | 0.0057 | 5.398 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.21 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.097 | 22.692 | 21.202 | 0.0153 | 1.062 | 0.953 | 0.708 | 1.799 | 1.1 | 10.6 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 25.601 | 26.598 | 24.322 | 0.0170 | 3.536 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.41 |
| val1 | recovered | uncertain | gated | 50/50 | 25.156 | 26.194 | 25.818 | 0.0388 | 1.841 | 0.929 | 1.228 | 3.244 | 1.5 | 8.8 | 0.43 | 2.76 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 26.729 | 27.472 | 19.189 | 0.0071 | 8.484 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.22 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 25.645 | 26.609 | 23.883 | 0.0156 | 3.844 | 0.905 | 2.563 | 1.897 | 2.2 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 25.652 | 26.613 | 23.851 | 0.0156 | 3.871 | 0.904 | 2.581 | 1.886 | 2.2 | 10.9 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 24.845 | 25.831 | 25.415 | 0.0202 | 1.614 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.42 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.098 | 26.126 | 26.216 | 0.0419 | 1.422 | 0.944 | 0.948 | 3.627 | 1.3 | 8.8 | 0.40 | 3.10 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 25.552 | 26.242 | 20.790 | 0.0082 | 5.432 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.23 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 24.827 | 25.767 | 25.057 | 0.0185 | 1.727 | 0.932 | 1.151 | 2.055 | 1.6 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 24.830 | 25.769 | 25.031 | 0.0184 | 1.747 | 0.931 | 1.165 | 2.040 | 1.7 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.40 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 22.734 | 23.872 | 23.111 | 0.0269 | 2.598 | 0.921 | 1.732 | 2.537 | 1.6 | 10.5 | 0.44 | 3.09 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 24.224 | 25.019 | 17.761 | 0.0070 | 7.654 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.23 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 22.766 | 23.820 | 22.239 | 0.0175 | 3.067 | 0.897 | 2.045 | 1.950 | 2.1 | 10.2 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.53 |
| val2 | observed | stable | gated | 50/50 | 18.226 | 18.737 | 17.959 | 0.0132 | 0.639 | 0.966 | 0.426 | 1.382 | 1.0 | 11.3 | 0.08 | 3.96 |
| val2 | observed | stable | order_up_to | 50/50 | 19.497 | 19.844 | 14.397 | 0.0047 | 4.632 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.06 |
| val2 | observed | stable | reorder_point | 50/50 | 18.238 | 18.753 | 17.934 | 0.0129 | 0.685 | 0.960 | 0.456 | 1.341 | 1.1 | 11.4 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 50/50 | 21.384 | 22.252 | 20.616 | 0.0143 | 2.937 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.40 |
| val2 | observed | uncertain | gated | 50/50 | 21.805 | 22.807 | 22.554 | 0.0262 | 2.366 | 0.922 | 1.578 | 2.623 | 1.6 | 9.1 | 0.47 | 2.66 |
| val2 | observed | uncertain | order_up_to | 50/50 | 22.247 | 22.882 | 15.949 | 0.0055 | 7.279 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.23 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 21.464 | 22.307 | 20.285 | 0.0131 | 3.223 | 0.896 | 2.149 | 1.265 | 2.2 | 12.3 |  | 0.05 |
| val2 | observed | uncertain | reorder_point | 50/50 | 21.476 | 22.320 | 20.265 | 0.0130 | 3.259 | 0.893 | 2.173 | 1.263 | 2.2 | 11.6 |  | 0.05 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.376 | 22.181 | 21.984 | 0.0153 | 1.255 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.43 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 21.495 | 22.369 | 23.039 | 0.0274 | 0.897 | 0.955 | 0.598 | 2.742 | 0.9 | 9.5 | 0.48 | 3.35 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.676 | 22.223 | 17.687 | 0.0057 | 4.529 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.24 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.365 | 22.142 | 21.677 | 0.0140 | 1.413 | 0.937 | 0.942 | 1.438 | 1.3 | 12.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.355 | 22.133 | 21.645 | 0.0138 | 1.440 | 0.935 | 0.960 | 1.428 | 1.4 | 11.7 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 18.788 | 19.627 | 18.553 | 0.0141 | 2.276 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.43 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 18.672 | 19.605 | 19.482 | 0.0205 | 1.714 | 0.912 | 1.143 | 2.242 | 1.6 | 11.1 | 0.45 | 3.43 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.083 | 20.658 | 14.388 | 0.0059 | 6.378 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.25 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.789 | 19.629 | 18.550 | 0.0141 | 2.280 | 0.888 | 1.520 | 1.456 | 2.2 | 12.0 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.789 | 19.630 | 18.536 | 0.0138 | 2.297 | 0.887 | 1.532 | 1.448 | 2.2 | 10.9 |  | 0.05 |
| val2 | recovered | stable | base_stock | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.54 |
| val2 | recovered | stable | gated | 50/50 | 23.000 | 23.726 | 21.927 | 0.0179 | 1.808 | 0.947 | 1.205 | 2.088 | 1.2 | 10.4 | 0.07 | 4.34 |
| val2 | recovered | stable | order_up_to | 50/50 | 24.427 | 24.833 | 17.222 | 0.0065 | 6.326 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.23 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.081 | 23.774 | 21.565 | 0.0169 | 2.102 | 0.940 | 1.401 | 1.948 | 1.3 | 10.5 |  | 0.05 |
| val2 | recovered | uncertain | base_stock | 50/50 | 26.668 | 27.674 | 24.888 | 0.0195 | 4.100 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.41 |
| val2 | recovered | uncertain | gated | 50/50 | 26.758 | 28.234 | 29.769 | 0.0368 | 1.998 | 0.934 | 1.332 | 3.456 | 1.4 | 9.2 | 0.42 | 2.59 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 27.706 | 28.419 | 18.942 | 0.0081 | 9.425 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.24 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 26.724 | 27.697 | 24.369 | 0.0180 | 4.456 | 0.895 | 2.971 | 1.961 | 2.1 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 26.729 | 27.701 | 24.330 | 0.0179 | 4.495 | 0.892 | 2.997 | 1.953 | 2.1 | 10.9 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 26.760 | 27.808 | 26.642 | 0.0209 | 2.544 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.44 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 27.081 | 28.170 | 28.105 | 0.0375 | 1.883 | 0.943 | 1.255 | 3.096 | 1.1 | 9.3 | 0.44 | 3.26 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.143 | 27.815 | 21.195 | 0.0082 | 6.401 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.25 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 26.735 | 27.739 | 26.208 | 0.0191 | 2.726 | 0.931 | 1.818 | 2.158 | 1.5 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 26.716 | 27.718 | 26.143 | 0.0190 | 2.759 | 0.928 | 1.839 | 2.140 | 1.5 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.675 | 24.745 | 22.603 | 0.0206 | 3.672 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.43 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.309 | 24.681 | 25.129 | 0.0260 | 2.317 | 0.910 | 1.545 | 2.742 | 1.5 | 10.6 | 0.44 | 3.36 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 25.025 | 25.713 | 17.457 | 0.0083 | 8.105 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.23 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.676 | 24.747 | 22.600 | 0.0206 | 3.677 | 0.883 | 2.451 | 2.187 | 2.2 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.708 | 24.778 | 22.525 | 0.0205 | 3.776 | 0.878 | 2.517 | 2.174 | 2.3 | 10.1 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | +0.001 | [-0.005, +0.007] | [-0.008, +0.011] | 16 / 7 / 27 | 0.093 |
| final | observed | stable | periodic:1 | 50 | +0.006 | [-0.002, +0.016] | [-0.006, +0.022] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | base_stock | 50 | +0.006 | [-0.002, +0.015] | [-0.006, +0.021] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | order_up_to | 50 | -0.484 | [-0.581, -0.396] | [-0.634, -0.357] | 46 / 4 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | -0.049 | [-0.150, +0.048] | [-0.217, +0.083] | 25 / 21 / 4 | 0.659 |
| final | observed | uncertain | periodic:1 | 50 | -0.046 | [-0.144, +0.046] | [-0.209, +0.083] | 26 / 22 / 2 | 0.665 |
| final | observed | uncertain | base_stock | 50 | -0.217 | [-0.323, -0.120] | [-0.395, -0.080] | 38 / 12 / 0 | 0.0 |
| final | observed | uncertain | order_up_to | 50 | -0.335 | [-0.469, -0.206] | [-0.550, -0.144] | 37 / 13 / 0 | 0.001 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.139 | [-0.340, +0.041] | [-0.491, +0.094] | 25 / 21 / 4 | 0.659 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.138 | [-0.336, +0.046] | [-0.486, +0.096] | 26 / 22 / 2 | 0.665 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.355 | [-0.675, -0.068] | [-0.930, -0.006] | 31 / 19 / 0 | 0.119 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -0.581 | [-0.907, -0.304] | [-1.134, -0.221] | 37 / 13 / 0 | 0.001 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.038 | [-0.065, -0.013] | [-0.082, -0.003] | 33 / 11 / 6 | 0.001 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.029 | [-0.053, -0.007] | [-0.070, +0.002] | 35 / 12 / 3 | 0.001 |
| final | observed | uncertain_lead_only | base_stock | 50 | -0.031 | [-0.054, -0.009] | [-0.069, -0.001] | 43 / 7 / 0 | 0.0 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -0.512 | [-0.621, -0.407] | [-0.687, -0.355] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | -0.007 | [-0.022, +0.008] | [-0.032, +0.016] | 18 / 8 / 24 | 0.076 |
| final | recovered | stable | periodic:1 | 50 | +0.005 | [-0.009, +0.020] | [-0.017, +0.027] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | base_stock | 50 | +0.005 | [-0.010, +0.020] | [-0.018, +0.027] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | order_up_to | 50 | -0.661 | [-0.814, -0.517] | [-0.902, -0.457] | 44 / 6 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | +0.008 | [-0.107, +0.133] | [-0.160, +0.214] | 25 / 22 / 3 | 0.771 |
| final | recovered | uncertain | periodic:1 | 50 | +0.022 | [-0.092, +0.149] | [-0.141, +0.223] | 27 / 21 / 2 | 0.471 |
| final | recovered | uncertain | base_stock | 50 | -0.192 | [-0.303, -0.075] | [-0.356, -0.011] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain | order_up_to | 50 | -0.260 | [-0.457, -0.053] | [-0.549, +0.079] | 35 / 15 / 0 | 0.007 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.143 | [-0.343, +0.040] | [-0.494, +0.092] | 29 / 19 / 2 | 0.193 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.137 | [-0.347, +0.046] | [-0.500, +0.095] | 28 / 21 / 1 | 0.392 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.378 | [-0.707, -0.078] | [-0.940, -0.015] | 32 / 18 / 0 | 0.065 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -0.659 | [-1.013, -0.345] | [-1.269, -0.249] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.020 | [-0.042, +0.001] | [-0.057, +0.010] | 32 / 13 / 5 | 0.007 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.008 | [-0.022, +0.005] | [-0.029, +0.013] | 35 / 12 / 3 | 0.001 |
| final | recovered | uncertain_lead_only | base_stock | 50 | -0.010 | [-0.025, +0.004] | [-0.033, +0.011] | 42 / 7 / 1 | 0.0 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -0.635 | [-0.797, -0.476] | [-0.913, -0.418] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.017 | [-0.030, -0.004] | [-0.039, +0.002] | 6 / 27 / 17 | 0.0 |
| val1 | observed | stable | periodic:1 | 50 | -0.007 | [-0.019, +0.003] | [-0.026, +0.008] | 18 / 26 / 6 | 0.291 |
| val1 | observed | stable | base_stock | 50 | -0.007 | [-0.018, +0.003] | [-0.026, +0.008] | 18 / 26 / 6 | 0.291 |
| val1 | observed | stable | order_up_to | 50 | -1.118 | [-1.437, -0.836] | [-1.683, -0.758] | 48 / 2 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | -0.057 | [-0.208, +0.101] | [-0.284, +0.182] | 29 / 20 / 1 | 0.253 |
| val1 | observed | uncertain | periodic:1 | 50 | -0.043 | [-0.194, +0.098] | [-0.275, +0.186] | 29 / 21 / 0 | 0.322 |
| val1 | observed | uncertain | base_stock | 50 | -0.003 | [-0.149, +0.149] | [-0.219, +0.240] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain | order_up_to | 50 | -0.954 | [-1.480, -0.497] | [-1.872, -0.362] | 42 / 8 / 0 | 0.0 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.467 | [+0.184, +0.778] | [+0.085, +0.958] | 22 / 28 / 0 | 0.48 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.461 | [+0.182, +0.762] | [+0.067, +0.951] | 22 / 28 / 0 | 0.48 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.484 | [+0.192, +0.795] | [+0.073, +1.000] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | -0.062 | [-0.309, +0.198] | [-0.404, +0.379] | 33 / 17 / 0 | 0.033 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.058 | [-0.153, +0.044] | [-0.196, +0.109] | 29 / 21 / 0 | 0.322 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.050 | [-0.144, +0.056] | [-0.186, +0.123] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | -0.050 | [-0.147, +0.049] | [-0.189, +0.119] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -1.302 | [-1.816, -0.855] | [-2.176, -0.734] | 44 / 6 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | -0.024 | [-0.051, +0.002] | [-0.074, +0.004] | 6 / 22 / 22 | 0.004 |
| val1 | recovered | stable | periodic:1 | 50 | -0.014 | [-0.043, +0.013] | [-0.068, +0.019] | 21 / 24 / 5 | 0.766 |
| val1 | recovered | stable | base_stock | 50 | -0.014 | [-0.044, +0.014] | [-0.068, +0.019] | 21 / 24 / 5 | 0.766 |
| val1 | recovered | stable | order_up_to | 50 | -1.389 | [-1.867, -0.995] | [-2.212, -0.912] | 48 / 2 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | -0.496 | [-1.371, +0.281] | [-2.100, +0.444] | 21 / 27 / 2 | 0.471 |
| val1 | recovered | uncertain | periodic:1 | 50 | -0.489 | [-1.377, +0.288] | [-2.056, +0.450] | 21 / 29 / 0 | 0.322 |
| val1 | recovered | uncertain | base_stock | 50 | -0.445 | [-1.295, +0.290] | [-1.925, +0.447] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain | order_up_to | 50 | -1.573 | [-2.864, -0.409] | [-3.894, -0.202] | 38 / 12 / 0 | 0.0 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +0.268 | [+0.056, +0.481] | [-0.050, +0.599] | 22 / 27 / 1 | 0.568 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.271 | [+0.062, +0.491] | [-0.039, +0.606] | 24 / 25 / 1 | 1.0 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +0.253 | [+0.044, +0.462] | [-0.060, +0.580] | 25 / 25 / 0 | 1.0 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | -0.454 | [-0.849, -0.074] | [-1.132, +0.092] | 32 / 18 / 0 | 0.065 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.032 | [-0.131, +0.072] | [-0.177, +0.137] | 23 / 27 / 0 | 0.672 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.021 | [-0.119, +0.084] | [-0.161, +0.150] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | -0.021 | [-0.120, +0.083] | [-0.168, +0.153] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -1.489 | [-1.967, -1.065] | [-2.331, -0.915] | 47 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | -0.012 | [-0.024, -0.002] | [-0.032, +0.002] | 10 / 24 / 16 | 0.024 |
| val2 | observed | stable | periodic:1 | 50 | +0.016 | [+0.005, +0.026] | [+0.000, +0.033] | 19 / 28 / 3 | 0.243 |
| val2 | observed | stable | base_stock | 50 | +0.016 | [+0.005, +0.027] | [-0.000, +0.033] | 19 / 28 / 3 | 0.243 |
| val2 | observed | stable | order_up_to | 50 | -1.271 | [-1.802, -0.785] | [-2.246, -0.713] | 49 / 1 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | +0.329 | [+0.118, +0.560] | [+0.037, +0.694] | 23 / 27 / 0 | 0.672 |
| val2 | observed | uncertain | periodic:1 | 50 | +0.341 | [+0.126, +0.568] | [+0.043, +0.719] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain | base_stock | 50 | +0.421 | [+0.185, +0.678] | [+0.080, +0.828] | 20 / 30 / 0 | 0.203 |
| val2 | observed | uncertain | order_up_to | 50 | -0.442 | [-0.875, -0.031] | [-1.194, +0.138] | 37 / 13 / 0 | 0.001 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.139 | [-0.106, +0.388] | [-0.235, +0.537] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.130 | [-0.121, +0.385] | [-0.262, +0.517] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.119 | [-0.116, +0.358] | [-0.245, +0.496] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | -0.181 | [-0.480, +0.114] | [-0.641, +0.276] | 33 / 17 / 0 | 0.033 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.117 | [-0.209, -0.021] | [-0.260, +0.029] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.117 | [-0.205, -0.028] | [-0.249, +0.022] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.116 | [-0.204, -0.026] | [-0.251, +0.022] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -1.411 | [-2.036, -0.867] | [-2.498, -0.720] | 46 / 4 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | -0.081 | [-0.178, +0.005] | [-0.254, +0.026] | 8 / 22 / 20 | 0.016 |
| val2 | recovered | stable | periodic:1 | 50 | -0.053 | [-0.150, +0.034] | [-0.222, +0.055] | 24 / 24 / 2 | 1.0 |
| val2 | recovered | stable | base_stock | 50 | -0.053 | [-0.153, +0.033] | [-0.228, +0.052] | 24 / 24 / 2 | 1.0 |
| val2 | recovered | stable | order_up_to | 50 | -1.427 | [-1.938, -0.969] | [-2.307, -0.887] | 48 / 2 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | +0.029 | [-0.383, +0.427] | [-0.632, +0.624] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | uncertain | periodic:1 | 50 | +0.034 | [-0.373, +0.442] | [-0.647, +0.641] | 31 / 19 / 0 | 0.119 |
| val2 | recovered | uncertain | base_stock | 50 | +0.090 | [-0.264, +0.434] | [-0.474, +0.597] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain | order_up_to | 50 | -0.947 | [-1.950, -0.111] | [-2.598, +0.125] | 35 / 15 / 0 | 0.007 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | +0.364 | [-0.004, +0.722] | [-0.218, +0.916] | 17 / 31 / 2 | 0.059 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.346 | [-0.060, +0.735] | [-0.289, +0.923] | 19 / 31 / 0 | 0.119 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | +0.321 | [-0.052, +0.699] | [-0.281, +0.882] | 17 / 33 / 0 | 0.033 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | -0.062 | [-0.488, +0.386] | [-0.786, +0.610] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.399 | [-0.723, -0.113] | [-0.993, -0.036] | 28 / 20 / 2 | 0.312 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.367 | [-0.681, -0.083] | [-0.936, -0.011] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.366 | [-0.690, -0.077] | [-0.939, -0.009] | 28 / 22 / 0 | 0.48 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -1.716 | [-2.467, -1.062] | [-2.987, -0.904] | 46 / 4 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | +0.0028 | [-0.0230, +0.0330] | 2 / 3 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0186 | [-0.0252, +0.0780] | 11 / 7 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | +0.0005 | [-0.0017, +0.0034] | 2 / 3 |
| final | observed | stable | periodic:1 | shortage | 50 | +0.0255 | [-0.0102, +0.0699] | 2 / 9 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0067 | [-0.0394, +0.0674] | 26 / 9 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0014 | [-0.0044, +0.0019] | 2 / 9 |
| final | observed | stable | base_stock | shortage | 50 | +0.0255 | [-0.0115, +0.0692] | 2 / 9 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | +0.0067 | [-0.0385, +0.0701] | 26 / 9 |
| final | observed | stable | base_stock | service_unit_fill | 50 | -0.0014 | [-0.0044, +0.0020] | 2 / 9 |
| final | observed | stable | order_up_to | shortage | 50 | -1.4828 | [-1.9109, -1.1008] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9513 | [+0.5785, +1.5833] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1422 | [+0.1138, +0.1699] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.1523 | [-0.5517, +0.1373] | 10 / 8 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.5410 | [+0.0835, +1.3592] | 10 / 29 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0060 | [-0.0117, +0.0235] | 10 / 8 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.1399 | [-0.5464, +0.1422] | 10 / 9 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5389 | [+0.0850, +1.3684] | 12 / 30 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0043 | [-0.0138, +0.0208] | 10 / 9 |
| final | observed | uncertain | base_stock | shortage | 50 | -0.0781 | [-0.4598, +0.2029] | 9 / 17 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.4147 | [+0.0067, +1.1395] | 27 / 23 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | -0.0008 | [-0.0195, +0.0159] | 9 / 17 |
| final | observed | uncertain | order_up_to | shortage | 50 | -1.6065 | [-2.2252, -1.0927] | 41 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.1670 | [+0.4846, +2.4368] | 1 / 49 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1457 | [+0.1171, +0.1760] | 41 / 0 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.1384 | [-0.3928, +0.0575] | 11 / 8 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.6467 | [+0.1592, +1.5216] | 8 / 34 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0046 | [-0.0043, +0.0149] | 11 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.1325 | [-0.3969, +0.0642] | 9 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.6431 | [+0.1563, +1.5158] | 11 / 34 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0038 | [-0.0048, +0.0139] | 9 / 8 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.0695 | [-0.3296, +0.1350] | 7 / 12 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.5151 | [+0.0610, +1.3567] | 23 / 27 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0005 | [-0.0084, +0.0102] | 7 / 12 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.5351 | [-2.0594, -1.0837] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.4123 | [+0.6618, +2.7946] | 1 / 49 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1355 | [+0.1070, +0.1651] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.1248 | [-0.2527, -0.0234] | 8 / 2 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.1086 | [+0.0322, +0.2069] | 14 / 24 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0078 | [+0.0005, +0.0167] | 8 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.0936 | [-0.2073, -0.0041] | 6 / 3 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.1011 | [+0.0238, +0.1999] | 18 / 23 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0068 | [-0.0001, +0.0151] | 6 / 3 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.0936 | [-0.2089, -0.0053] | 6 / 3 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.1011 | [+0.0267, +0.1953] | 18 / 23 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0068 | [+0.0002, +0.0152] | 6 / 3 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -1.5883 | [-2.0865, -1.1350] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.8306 | [+0.5256, +1.3690] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1414 | [+0.1133, +0.1694] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | -0.0377 | [-0.1050, +0.0213] | 3 / 1 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0265 | [-0.0269, +0.0849] | 13 / 9 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0041 | [-0.0003, +0.0104] | 3 / 1 |
| final | recovered | stable | periodic:1 | shortage | 50 | +0.0053 | [-0.0587, +0.0646] | 3 / 5 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0060 | [-0.0477, +0.0672] | 26 / 8 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0006 | [-0.0048, +0.0071] | 3 / 5 |
| final | recovered | stable | base_stock | shortage | 50 | +0.0053 | [-0.0589, +0.0636] | 3 / 5 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0060 | [-0.0482, +0.0694] | 26 / 8 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | +0.0006 | [-0.0047, +0.0071] | 3 / 5 |
| final | recovered | stable | order_up_to | shortage | 50 | -2.0354 | [-2.7570, -1.4330] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.3492 | [+0.8566, +2.1445] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1558 | [+0.1313, +0.1802] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.1894 | [-0.4415, +0.0131] | 15 / 4 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.5305 | [+0.1006, +1.2873] | 15 / 27 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0085 | [-0.0081, +0.0240] | 15 / 4 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.1562 | [-0.4017, +0.0296] | 12 / 6 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5215 | [+0.0895, +1.2941] | 16 / 28 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0043 | [-0.0112, +0.0175] | 12 / 6 |
| final | recovered | uncertain | base_stock | shortage | 50 | -0.1192 | [-0.3619, +0.0733] | 9 / 11 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.3687 | [-0.0111, +1.0451] | 31 / 19 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0016 | [-0.0149, +0.0157] | 9 / 11 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -1.9833 | [-2.7698, -1.3452] | 42 / 0 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +1.4988 | [+0.7078, +2.8817] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1519 | [+0.1210, +0.1821] | 42 / 0 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.0391 | [-0.2462, +0.2006] | 11 / 5 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.7981 | [+0.2194, +1.7066] | 11 / 34 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0030 | [-0.0048, +0.0113] | 11 / 5 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0118 | [-0.2177, +0.2247] | 10 / 7 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.7930 | [+0.2213, +1.7132] | 12 / 35 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0000 | [-0.0075, +0.0074] | 10 / 7 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | +0.0342 | [-0.1640, +0.2666] | 6 / 9 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.6307 | [+0.1094, +1.4747] | 24 / 26 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0032 | [-0.0106, +0.0040] | 6 / 9 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -1.8165 | [-2.5355, -1.2432] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.9492 | [+0.9645, +3.5784] | 0 / 50 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1412 | [+0.1115, +0.1717] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.0614 | [-0.1729, +0.0274] | 8 / 6 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.0632 | [-0.0301, +0.1455] | 10 / 27 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0024 | [-0.0032, +0.0081] | 8 / 6 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.0218 | [-0.0849, +0.0365] | 7 / 6 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.0547 | [-0.0289, +0.1409] | 16 / 25 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0002 | [-0.0043, +0.0046] | 7 / 6 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.0218 | [-0.0874, +0.0357] | 7 / 6 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.0547 | [-0.0353, +0.1366] | 16 / 25 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0002 | [-0.0043, +0.0046] | 7 / 6 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -1.9567 | [-2.7483, -1.3050] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.1331 | [+0.7449, +1.7513] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1479 | [+0.1193, +0.1766] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.0525 | [-0.1189, -0.0003] | 5 / 3 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0630 | [+0.0247, +0.1278] | 1 / 28 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0050 | [+0.0007, +0.0110] | 5 / 3 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.0248 | [-0.0792, +0.0192] | 5 / 7 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0438 | [+0.0052, +0.1016] | 20 / 24 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0032 | [-0.0007, +0.0085] | 5 / 7 |
| val1 | observed | stable | base_stock | shortage | 50 | -0.0248 | [-0.0818, +0.0212] | 5 / 7 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0438 | [+0.0043, +0.1027] | 20 / 24 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | +0.0032 | [-0.0006, +0.0084] | 5 / 7 |
| val1 | observed | stable | order_up_to | shortage | 50 | -3.5676 | [-5.2185, -2.5386] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9505 | [+0.6400, +1.4221] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1687 | [+0.1485, +0.1907] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -1.2853 | [-2.2165, -0.5878] | 33 / 2 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.8640 | [+0.6247, +1.1472] | 1 / 48 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0369 | [+0.0252, +0.0495] | 33 / 2 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -1.2553 | [-2.2170, -0.5681] | 34 / 3 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.8555 | [+0.6127, +1.1437] | 3 / 47 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0352 | [+0.0240, +0.0483] | 34 / 3 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.0127 | [-1.7307, -0.4325] | 30 / 10 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.7497 | [+0.5271, +1.0079] | 5 / 45 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0294 | [+0.0180, +0.0417] | 30 / 10 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -5.0992 | [-8.1880, -3.1193] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.6134 | [+1.1413, +2.2878] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1965 | [+0.1783, +0.2151] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.2994 | [-0.4731, -0.1469] | 22 / 5 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.7325 | [+0.8396, +3.0789] | 2 / 48 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0160 | [+0.0064, +0.0267] | 22 / 5 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.2851 | [-0.4524, -0.1379] | 22 / 6 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.7214 | [+0.8418, +3.1303] | 3 / 47 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0153 | [+0.0064, +0.0255] | 22 / 6 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1733 | [-0.3218, -0.0471] | 15 / 15 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.5803 | [+0.7403, +2.8140] | 3 / 47 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0098 | [+0.0011, +0.0195] | 15 / 15 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.2340 | [-4.6666, -2.2980] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.5944 | [+1.4518, +4.4213] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1534 | [+0.1316, +0.1768] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.5639 | [-0.8135, -0.3524] | 31 / 2 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.6915 | [+0.4059, +1.0596] | 1 / 49 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0350 | [+0.0185, +0.0595] | 31 / 2 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.5416 | [-0.7919, -0.3279] | 31 / 2 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.6843 | [+0.3959, +1.0598] | 2 / 48 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0322 | [+0.0179, +0.0529] | 31 / 2 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.5416 | [-0.7942, -0.3285] | 31 / 2 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.6843 | [+0.4013, +1.0506] | 2 / 48 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0322 | [+0.0177, +0.0540] | 31 / 2 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.5387 | [-6.9997, -2.9848] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.5268 | [+0.9898, +2.3668] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1939 | [+0.1743, +0.2147] | 50 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 50 | -0.0723 | [-0.2228, +0.0116] | 4 / 2 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0591 | [+0.0227, +0.1203] | 5 / 22 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0010 | [-0.0007, +0.0035] | 4 / 2 |
| val1 | recovered | stable | periodic:1 | shortage | 50 | -0.0414 | [-0.2064, +0.0557] | 4 / 8 |
| val1 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0337 | [-0.0046, +0.0924] | 24 / 21 |
| val1 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0016 | [-0.0048, +0.0017] | 4 / 8 |
| val1 | recovered | stable | base_stock | shortage | 50 | -0.0414 | [-0.2030, +0.0575] | 4 / 8 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0337 | [-0.0051, +0.0912] | 24 / 21 |
| val1 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0016 | [-0.0047, +0.0019] | 4 / 8 |
| val1 | recovered | stable | order_up_to | shortage | 50 | -4.4081 | [-6.7164, -2.9999] | 50 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.2595 | [+0.9095, +1.8551] | 0 / 50 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1718 | [+0.1511, +0.1946] | 50 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -2.0293 | [-4.5863, -0.4516] | 27 / 5 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.3578 | [+0.6820, +2.3459] | 4 / 44 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0250 | [+0.0073, +0.0416] | 27 / 5 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -2.0023 | [-4.6557, -0.4407] | 28 / 5 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3467 | [+0.6740, +2.3565] | 6 / 44 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0235 | [+0.0062, +0.0396] | 28 / 5 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -1.6943 | [-4.0983, -0.2713] | 24 / 11 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.2224 | [+0.5793, +2.1554] | 9 / 41 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0184 | [-0.0000, +0.0339] | 24 / 11 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -6.6423 | [-11.6850, -3.5798] | 48 / 1 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.4194 | [+1.4991, +3.9164] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1946 | [+0.1684, +0.2193] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.3251 | [-0.6371, -0.0516] | 20 / 6 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.5869 | [+0.8516, +2.7162] | 1 / 48 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0136 | [+0.0023, +0.0255] | 20 / 6 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.3046 | [-0.6036, -0.0474] | 18 / 6 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.5721 | [+0.8163, +2.6788] | 3 / 46 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0125 | [+0.0012, +0.0243] | 18 / 6 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.1915 | [-0.4815, +0.0550] | 12 / 14 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.4105 | [+0.7215, +2.4606] | 5 / 45 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0074 | [-0.0042, +0.0185] | 12 / 14 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.0098 | [-6.0142, -2.7055] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.7952 | [+1.7512, +4.3819] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1573 | [+0.1323, +0.1823] | 48 / 1 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.4689 | [-0.7230, -0.2387] | 22 / 4 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.5872 | [+0.3858, +0.8490] | 5 / 45 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0241 | [+0.0094, +0.0456] | 22 / 4 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.4367 | [-0.6907, -0.2092] | 22 / 5 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.5775 | [+0.3704, +0.8436] | 6 / 44 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0221 | [+0.0073, +0.0432] | 22 / 5 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.4367 | [-0.6910, -0.2042] | 22 / 5 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5775 | [+0.3608, +0.8361] | 6 / 44 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0221 | [+0.0074, +0.0431] | 22 / 5 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -5.0558 | [-7.4599, -3.4933] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7760 | [+1.2476, +2.5907] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1939 | [+0.1711, +0.2181] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.0460 | [-0.1016, -0.0047] | 7 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0416 | [+0.0190, +0.0646] | 5 / 27 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0056 | [+0.0008, +0.0132] | 7 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 50 | +0.0390 | [-0.0085, +0.0924] | 6 / 10 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0285 | [+0.0042, +0.0530] | 19 / 28 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0013 | [-0.0051, +0.0024] | 6 / 10 |
| val2 | observed | stable | base_stock | shortage | 50 | +0.0390 | [-0.0069, +0.0904] | 6 / 10 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0285 | [+0.0041, +0.0544] | 19 / 28 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | -0.0013 | [-0.0051, +0.0023] | 6 / 10 |
| val2 | observed | stable | order_up_to | shortage | 50 | -3.9934 | [-6.8627, -2.3485] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9119 | [+0.6783, +1.2650] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1644 | [+0.1420, +0.1893] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -0.8925 | [-1.6286, -0.4248] | 30 / 6 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.3603 | [+0.7773, +2.1442] | 1 / 49 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0288 | [+0.0191, +0.0392] | 30 / 6 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -0.8566 | [-1.5872, -0.3701] | 29 / 9 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3586 | [+0.7810, +2.1794] | 1 / 49 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0258 | [+0.0162, +0.0362] | 29 / 9 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -0.5701 | [-0.9003, -0.2987] | 26 / 11 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.2414 | [+0.7087, +1.9323] | 2 / 48 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0217 | [+0.0124, +0.0324] | 26 / 11 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -4.9125 | [-8.5665, -2.7840] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +2.0362 | [+1.3346, +3.0195] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1859 | [+0.1637, +0.2114] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.5434 | [-0.9989, -0.1967] | 23 / 4 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.3146 | [+0.6576, +2.3302] | 1 / 49 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0202 | [+0.0090, +0.0333] | 23 / 4 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.5161 | [-0.9490, -0.1854] | 22 / 4 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.3045 | [+0.6588, +2.3237] | 1 / 49 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0174 | [+0.0078, +0.0292] | 22 / 4 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.3581 | [-0.6371, -0.1258] | 18 / 8 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.1711 | [+0.5618, +2.1598] | 7 / 43 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0149 | [+0.0049, +0.0263] | 18 / 8 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.6321 | [-6.4651, -2.0439] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.1305 | [+1.3410, +3.3347] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1446 | [+0.1212, +0.1707] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.5834 | [-0.9159, -0.3071] | 22 / 1 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7946 | [+0.3118, +1.6332] | 3 / 46 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0250 | [+0.0141, +0.0388] | 22 / 1 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.5660 | [-0.8885, -0.2899] | 22 / 4 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7858 | [+0.3051, +1.6333] | 3 / 47 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0237 | [+0.0126, +0.0376] | 22 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.5623 | [-0.8987, -0.2749] | 22 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.7857 | [+0.3069, +1.6271] | 3 / 47 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0233 | [+0.0124, +0.0370] | 22 / 4 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.6638 | [-7.7246, -2.7257] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.6015 | [+0.9534, +2.7439] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1740 | [+0.1536, +0.1957] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.2938 | [-0.7866, -0.0151] | 7 / 0 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.1402 | [+0.0279, +0.3457] | 2 / 26 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0070 | [+0.0010, +0.0163] | 7 / 0 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | -0.2079 | [-0.7155, +0.0714] | 7 / 10 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.1048 | [-0.0112, +0.3188] | 30 / 18 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0000 | [-0.0051, +0.0057] | 7 / 10 |
| val2 | recovered | stable | base_stock | shortage | 50 | -0.2079 | [-0.6951, +0.0747] | 7 / 10 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.1048 | [-0.0125, +0.3197] | 30 / 18 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0000 | [-0.0052, +0.0054] | 7 / 10 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -4.5178 | [-7.2254, -2.9064] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.4086 | [+0.9491, +2.2001] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1720 | [+0.1502, +0.1948] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -2.4967 | [-5.7446, -0.7225] | 28 / 5 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.5030 | [+0.8225, +2.5597] | 2 / 48 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0422 | [+0.0245, +0.0626] | 28 / 5 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -2.4579 | [-5.6331, -0.6508] | 28 / 6 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.4947 | [+0.8184, +2.5753] | 3 / 47 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0394 | [+0.0210, +0.0598] | 28 / 6 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -2.1013 | [-4.7510, -0.5523] | 27 / 9 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.3530 | [+0.7081, +2.2853] | 7 / 43 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0357 | [+0.0182, +0.0553] | 27 / 9 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -7.4268 | [-13.8469, -3.7293] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.5351 | [+1.6672, +3.9386] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2109 | [+0.1831, +0.2420] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.8757 | [-2.1281, -0.0916] | 26 / 5 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.9562 | [+0.6659, +1.2933] | 3 / 45 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0143 | [-0.0030, +0.0292] | 26 / 5 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.8432 | [-2.0795, -0.0655] | 26 / 6 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.9388 | [+0.6487, +1.2840] | 5 / 45 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0114 | [-0.0052, +0.0262] | 26 / 6 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.6611 | [-1.6829, +0.0069] | 21 / 12 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.7760 | [+0.5138, +1.0643] | 6 / 44 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0081 | [-0.0081, +0.0227] | 21 / 12 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.5180 | [-7.6595, -2.6033] | 46 / 2 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.1621 | [+1.6360, +2.8565] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1551 | [+0.1290, +0.1807] | 46 / 2 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.4592 | [-3.1305, -0.4755] | 30 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.5679 | [+0.3090, +0.9744] | 3 / 43 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0317 | [+0.0201, +0.0463] | 30 / 0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.3598 | [-3.0630, -0.3818] | 28 / 2 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.5554 | [+0.2995, +0.9929] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0271 | [+0.0157, +0.0412] | 28 / 2 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -1.3551 | [-3.0025, -0.3872] | 27 / 3 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5552 | [+0.2970, +0.9737] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0267 | [+0.0153, +0.0410] | 27 / 3 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -5.7883 | [-9.4332, -3.4195] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7897 | [+1.2252, +2.7327] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1925 | [+0.1719, +0.2134] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1200 of 1200 (9290 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +8.713 (fill 0.922 vs 0.922, inventory 47.94 vs 20.54, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus order_up_to = +8.240 (fill 0.679 vs 0.705, inventory 5.17 vs 1.27, retained incumbent on 12 reviews)
- val1/observed/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +8.035 (fill 0.917 vs 0.883, inventory 8.04 vs 1.08, retained incumbent on 5 reviews)
- val2/recovered/uncertain store 855 product 647: ZAAD minus order_up_to = +6.271 (fill 0.799 vs 0.642, inventory 5.33 vs 1.35, retained incumbent on 12 reviews)
- val2/observed/uncertain store 102 product 467: ZAAD minus periodic:1 = +6.198 (fill 0.971 vs 0.905, inventory 4.10 vs 2.55, retained incumbent on 9 reviews)
- val2/recovered/uncertain store 102 product 467: ZAAD minus periodic:1 = +6.103 (fill 0.976 vs 0.906, inventory 4.09 vs 2.57, retained incumbent on 9 reviews)
- final/recovered/uncertain store 514 product 267: ZAAD minus order_up_to = +5.686 (fill 0.954 vs 0.954, inventory 50.24 vs 17.32, retained incumbent on 3 reviews)
- val2/recovered/uncertain_fill_only store 485 product 127: ZAAD minus order_up_to = +5.493 (fill 0.959 vs 0.959, inventory 5.47 vs 1.05, retained incumbent on 6 reviews)
- val2/observed/uncertain store 869 product 191: ZAAD minus base_stock = +5.463 (fill 0.969 vs 0.969, inventory 6.00 vs 2.14, retained incumbent on 6 reviews)
- val2/observed/uncertain_fill_only store 102 product 467: ZAAD minus reorder_point = +5.380 (fill 1.000 vs 0.987, inventory 5.29 vs 3.62, retained incumbent on 8 reviews)
