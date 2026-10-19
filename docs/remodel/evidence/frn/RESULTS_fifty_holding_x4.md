# FreshRetailNet pilot results: stage `fifty_holding_x4`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `9efdee1aed0a`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3708 s, peak RSS 224 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.230 | 10.863 | 10.564 | 0.0221 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.14 |
| final | observed | stable | gated | 50/50 | 10.235 | 10.576 | 9.057 | 0.0221 | 0.400 | 0.977 | 0.267 | 1.601 | 0.6 | 5.1 | 0.10 | 0.65 |
| final | observed | stable | order_up_to | 50/50 | 10.708 | 11.059 | 8.089 | 0.0090 | 1.877 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.09 |
| final | observed | stable | periodic:1 | 50/50 | 10.230 | 10.863 | 10.564 | 0.0221 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.03 |
| final | observed | stable | reorder_point | 50/50 | 10.233 | 10.618 | 9.285 | 0.0219 | 0.391 | 0.978 | 0.261 | 1.585 | 0.5 | 5.3 |  | 0.02 |
| final | observed | uncertain | base_stock | 50/50 | 12.372 | 13.373 | 12.809 | 0.0210 | 2.166 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.156 | 12.873 | 11.238 | 0.0267 | 2.088 | 0.887 | 1.392 | 1.935 | 1.4 | 4.0 | 0.30 | 0.61 |
| final | observed | uncertain | order_up_to | 50/50 | 12.475 | 13.158 | 9.724 | 0.0106 | 3.695 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.193 | 12.934 | 11.231 | 0.0193 | 2.228 | 0.883 | 1.485 | 1.397 | 1.4 | 5.5 |  | 0.02 |
| final | observed | uncertain | reorder_point | 50/50 | 12.195 | 12.936 | 11.221 | 0.0193 | 2.241 | 0.881 | 1.494 | 1.395 | 1.5 | 5.3 |  | 0.02 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 11.736 | 12.722 | 13.134 | 0.0257 | 1.142 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.348 | 12.005 | 11.092 | 0.0329 | 1.175 | 0.949 | 0.783 | 2.385 | 0.9 | 4.1 | 0.34 | 0.76 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 11.945 | 12.599 | 10.129 | 0.0133 | 2.608 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.10 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.511 | 12.212 | 11.391 | 0.0239 | 1.205 | 0.947 | 0.803 | 1.731 | 1.0 | 5.6 |  | 0.02 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.512 | 12.212 | 11.382 | 0.0239 | 1.211 | 0.947 | 0.807 | 1.728 | 1.0 | 5.3 |  | 0.03 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 10.914 | 11.951 | 11.336 | 0.0200 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.12 |
| final | observed | uncertain_lead_only | gated | 50/50 | 10.857 | 11.428 | 9.054 | 0.0215 | 2.226 | 0.904 | 1.484 | 1.560 | 1.2 | 4.3 | 0.32 | 0.71 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 11.379 | 12.087 | 8.578 | 0.0100 | 3.868 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.09 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 10.906 | 11.692 | 10.039 | 0.0200 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 5.4 |  | 0.02 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 10.915 | 11.704 | 10.028 | 0.0199 | 2.404 | 0.895 | 1.603 | 1.444 | 1.3 | 5.0 |  | 0.03 |
| final | recovered | stable | base_stock | 50/50 | 11.389 | 12.167 | 11.939 | 0.0306 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.14 |
| final | recovered | stable | gated | 50/50 | 11.390 | 11.845 | 10.313 | 0.0306 | 0.315 | 0.975 | 0.210 | 2.219 | 0.5 | 4.9 | 0.13 | 0.59 |
| final | recovered | stable | order_up_to | 50/50 | 12.035 | 12.441 | 8.640 | 0.0120 | 2.350 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.09 |
| final | recovered | stable | periodic:1 | 50/50 | 11.389 | 12.167 | 11.939 | 0.0306 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.02 |
| final | recovered | stable | reorder_point | 50/50 | 11.397 | 11.905 | 10.526 | 0.0303 | 0.353 | 0.971 | 0.235 | 2.192 | 0.5 | 5.1 |  | 0.02 |
| final | recovered | uncertain | base_stock | 50/50 | 13.784 | 14.978 | 14.958 | 0.0275 | 1.854 | 0.896 | 1.236 | 1.994 | 1.3 | 6.2 |  | 0.12 |
| final | recovered | uncertain | gated | 50/50 | 13.587 | 14.408 | 13.047 | 0.0326 | 1.736 | 0.898 | 1.157 | 2.360 | 1.2 | 4.1 | 0.31 | 0.61 |
| final | recovered | uncertain | order_up_to | 50/50 | 13.831 | 14.594 | 10.883 | 0.0119 | 3.719 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.09 |
| final | recovered | uncertain | periodic:1 | 50/50 | 13.562 | 14.469 | 13.214 | 0.0254 | 1.892 | 0.894 | 1.261 | 1.841 | 1.3 | 5.5 |  | 0.03 |
| final | recovered | uncertain | reorder_point | 50/50 | 13.573 | 14.480 | 13.202 | 0.0252 | 1.910 | 0.891 | 1.274 | 1.828 | 1.4 | 5.0 |  | 0.02 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 12.921 | 14.110 | 15.203 | 0.0341 | 0.729 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.550 | 13.313 | 12.726 | 0.0414 | 0.766 | 0.956 | 0.511 | 2.998 | 0.7 | 4.0 | 0.35 | 0.73 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 13.177 | 13.919 | 11.255 | 0.0159 | 2.580 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.671 | 13.556 | 13.331 | 0.0318 | 0.775 | 0.956 | 0.517 | 2.306 | 0.9 | 5.5 |  | 0.03 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.676 | 13.563 | 13.318 | 0.0318 | 0.803 | 0.953 | 0.535 | 2.301 | 0.9 | 5.0 |  | 0.02 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 11.946 | 13.192 | 13.294 | 0.0268 | 1.933 | 0.910 | 1.289 | 1.940 | 1.2 | 6.2 |  | 0.11 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 11.925 | 12.599 | 10.376 | 0.0275 | 1.911 | 0.910 | 1.274 | 1.994 | 1.2 | 4.0 | 0.34 | 0.68 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 12.549 | 13.346 | 9.627 | 0.0119 | 3.866 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.09 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 11.937 | 12.912 | 11.893 | 0.0268 | 1.933 | 0.910 | 1.289 | 1.940 | 1.2 | 5.3 |  | 0.02 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 11.954 | 12.928 | 11.847 | 0.0267 | 1.987 | 0.906 | 1.325 | 1.934 | 1.3 | 4.7 |  | 0.02 |
| val1 | observed | stable | base_stock | 50/50 | 18.274 | 18.756 | 17.937 | 0.0409 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.53 |
| val1 | observed | stable | gated | 50/50 | 18.270 | 18.752 | 17.938 | 0.0418 | 0.706 | 0.960 | 0.470 | 1.401 | 1.2 | 11.2 | 0.08 | 4.42 |
| val1 | observed | stable | order_up_to | 50/50 | 19.363 | 19.649 | 14.512 | 0.0143 | 4.260 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.274 | 18.756 | 17.937 | 0.0409 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.282 | 18.761 | 17.901 | 0.0404 | 0.745 | 0.956 | 0.497 | 1.350 | 1.3 | 11.1 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 21.258 | 22.025 | 19.912 | 0.0467 | 3.244 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.44 |
| val1 | observed | uncertain | gated | 50/50 | 21.079 | 21.980 | 21.594 | 0.0725 | 2.063 | 0.923 | 1.375 | 2.331 | 1.8 | 9.3 | 0.43 | 2.75 |
| val1 | observed | uncertain | order_up_to | 50/50 | 22.187 | 22.779 | 15.839 | 0.0205 | 7.330 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 21.296 | 22.038 | 19.576 | 0.0432 | 3.487 | 0.889 | 2.324 | 1.452 | 2.8 | 12.3 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 21.309 | 22.050 | 19.550 | 0.0429 | 3.517 | 0.887 | 2.344 | 1.444 | 2.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 20.752 | 21.555 | 20.968 | 0.0528 | 1.839 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.42 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.233 | 22.336 | 23.238 | 0.1062 | 1.642 | 0.939 | 1.095 | 3.197 | 1.4 | 8.9 | 0.47 | 3.28 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.272 | 21.834 | 17.195 | 0.0220 | 4.899 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.22 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 20.771 | 21.544 | 20.717 | 0.0485 | 1.950 | 0.923 | 1.300 | 1.582 | 1.9 | 12.4 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 20.764 | 21.535 | 20.686 | 0.0482 | 1.965 | 0.922 | 1.310 | 1.571 | 1.9 | 11.4 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 19.029 | 19.842 | 18.241 | 0.0460 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.43 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 19.004 | 19.907 | 19.246 | 0.0698 | 2.383 | 0.907 | 1.589 | 2.173 | 1.9 | 10.9 | 0.43 | 3.16 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.259 | 20.892 | 14.535 | 0.0197 | 6.896 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.23 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 19.029 | 19.842 | 18.241 | 0.0460 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.04 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 19.037 | 19.847 | 18.215 | 0.0458 | 2.921 | 0.873 | 1.948 | 1.487 | 2.7 | 10.7 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.130 | 22.725 | 21.249 | 0.0533 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.54 |
| val1 | recovered | stable | gated | 50/50 | 22.117 | 22.708 | 21.256 | 0.0542 | 0.990 | 0.954 | 0.660 | 1.858 | 1.0 | 10.6 | 0.07 | 4.07 |
| val1 | recovered | stable | order_up_to | 50/50 | 23.477 | 23.858 | 17.176 | 0.0181 | 5.398 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.22 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.130 | 22.725 | 21.249 | 0.0533 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.139 | 22.729 | 21.202 | 0.0526 | 1.062 | 0.953 | 0.708 | 1.799 | 1.1 | 10.6 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 25.658 | 26.640 | 24.322 | 0.0589 | 3.536 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.41 |
| val1 | recovered | uncertain | gated | 50/50 | 25.246 | 26.250 | 25.747 | 0.1057 | 1.841 | 0.929 | 1.227 | 3.234 | 1.4 | 8.8 | 0.43 | 2.76 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 26.756 | 27.489 | 19.189 | 0.0241 | 8.484 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.22 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 25.699 | 26.648 | 23.883 | 0.0549 | 3.844 | 0.905 | 2.563 | 1.897 | 2.2 | 12.3 |  | 0.05 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 25.705 | 26.653 | 23.851 | 0.0546 | 3.871 | 0.904 | 2.581 | 1.886 | 2.2 | 10.9 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 24.904 | 25.876 | 25.415 | 0.0661 | 1.614 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.071 | 26.061 | 25.971 | 0.1034 | 1.432 | 0.944 | 0.954 | 3.139 | 1.3 | 8.9 | 0.39 | 3.18 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 25.576 | 26.259 | 20.790 | 0.0254 | 5.432 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.23 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 24.881 | 25.810 | 25.057 | 0.0611 | 1.727 | 0.932 | 1.151 | 2.055 | 1.6 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 24.884 | 25.811 | 25.031 | 0.0607 | 1.747 | 0.931 | 1.165 | 2.040 | 1.7 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 22.811 | 23.852 | 22.271 | 0.0581 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.41 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 22.803 | 23.926 | 23.054 | 0.0781 | 2.670 | 0.917 | 1.780 | 2.532 | 1.6 | 10.4 | 0.44 | 3.18 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 24.249 | 25.035 | 17.761 | 0.0228 | 7.654 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.22 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 22.811 | 23.852 | 22.271 | 0.0581 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 22.822 | 23.861 | 22.239 | 0.0578 | 3.067 | 0.897 | 2.045 | 1.950 | 2.1 | 10.2 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.243 | 18.750 | 17.975 | 0.0410 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.53 |
| val2 | observed | stable | gated | 50/50 | 18.262 | 18.770 | 17.959 | 0.0418 | 0.647 | 0.965 | 0.431 | 1.382 | 1.0 | 11.3 | 0.08 | 3.92 |
| val2 | observed | stable | order_up_to | 50/50 | 19.509 | 19.854 | 14.397 | 0.0144 | 4.632 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.243 | 18.750 | 17.975 | 0.0410 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.05 |
| val2 | observed | stable | reorder_point | 50/50 | 18.271 | 18.781 | 17.934 | 0.0407 | 0.685 | 0.960 | 0.456 | 1.341 | 1.1 | 11.4 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 50/50 | 21.426 | 22.281 | 20.616 | 0.0429 | 2.937 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.44 |
| val2 | observed | uncertain | gated | 50/50 | 21.836 | 22.786 | 22.246 | 0.0790 | 2.399 | 0.919 | 1.599 | 2.580 | 1.6 | 9.3 | 0.46 | 2.76 |
| val2 | observed | uncertain | order_up_to | 50/50 | 22.267 | 22.895 | 15.949 | 0.0177 | 7.279 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.25 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 21.503 | 22.333 | 20.285 | 0.0393 | 3.223 | 0.896 | 2.149 | 1.265 | 2.2 | 12.3 |  | 0.05 |
| val2 | observed | uncertain | reorder_point | 50/50 | 21.514 | 22.346 | 20.265 | 0.0392 | 3.259 | 0.893 | 2.173 | 1.263 | 2.2 | 11.6 |  | 0.05 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.419 | 22.213 | 21.984 | 0.0479 | 1.255 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.43 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 21.508 | 22.363 | 22.826 | 0.0799 | 0.900 | 0.954 | 0.600 | 2.587 | 1.0 | 9.6 | 0.46 | 3.47 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.694 | 22.236 | 17.687 | 0.0183 | 4.529 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.24 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.404 | 22.172 | 21.677 | 0.0438 | 1.413 | 0.937 | 0.942 | 1.438 | 1.3 | 12.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.395 | 22.163 | 21.645 | 0.0434 | 1.440 | 0.935 | 0.960 | 1.428 | 1.4 | 11.7 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 18.831 | 19.658 | 18.553 | 0.0443 | 2.276 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.42 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 18.735 | 19.647 | 19.462 | 0.0668 | 1.714 | 0.912 | 1.143 | 2.237 | 1.6 | 11.0 | 0.44 | 3.36 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.104 | 20.672 | 14.388 | 0.0191 | 6.378 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.24 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.832 | 19.659 | 18.550 | 0.0443 | 2.280 | 0.888 | 1.520 | 1.456 | 2.2 | 12.0 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.832 | 19.660 | 18.536 | 0.0438 | 2.297 | 0.887 | 1.532 | 1.448 | 2.2 | 10.9 |  | 0.05 |
| val2 | recovered | stable | base_stock | 50/50 | 23.100 | 23.788 | 21.632 | 0.0583 | 2.016 | 0.947 | 1.344 | 1.983 | 1.2 | 12.4 |  | 0.54 |
| val2 | recovered | stable | gated | 50/50 | 23.123 | 23.842 | 21.776 | 0.0586 | 2.034 | 0.946 | 1.356 | 1.995 | 1.2 | 10.4 | 0.06 | 4.44 |
| val2 | recovered | stable | order_up_to | 50/50 | 24.443 | 24.848 | 17.222 | 0.0205 | 6.326 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.23 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.100 | 23.788 | 21.632 | 0.0583 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.127 | 23.814 | 21.565 | 0.0573 | 2.102 | 0.940 | 1.401 | 1.948 | 1.3 | 10.5 |  | 0.05 |
| val2 | recovered | uncertain | base_stock | 50/50 | 26.727 | 27.718 | 24.888 | 0.0630 | 4.100 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.40 |
| val2 | recovered | uncertain | gated | 50/50 | 27.238 | 28.404 | 27.136 | 0.0942 | 3.530 | 0.930 | 2.354 | 2.951 | 1.5 | 9.2 | 0.41 | 2.71 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 27.734 | 28.438 | 18.942 | 0.0272 | 9.425 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.24 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 26.779 | 27.737 | 24.369 | 0.0586 | 4.456 | 0.895 | 2.971 | 1.961 | 2.1 | 12.2 |  | 0.06 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 26.785 | 27.742 | 24.330 | 0.0584 | 4.496 | 0.892 | 2.997 | 1.953 | 2.1 | 10.9 |  | 0.06 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 26.822 | 27.856 | 26.642 | 0.0690 | 2.544 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.42 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 26.963 | 28.249 | 29.274 | 0.1091 | 1.533 | 0.941 | 1.022 | 3.369 | 1.1 | 9.5 | 0.43 | 3.36 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.169 | 27.834 | 21.195 | 0.0276 | 6.401 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.24 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 26.793 | 27.783 | 26.208 | 0.0638 | 2.726 | 0.931 | 1.818 | 2.158 | 1.5 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 26.774 | 27.762 | 26.143 | 0.0633 | 2.759 | 0.928 | 1.839 | 2.140 | 1.5 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.735 | 24.791 | 22.603 | 0.0659 | 3.672 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.42 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.393 | 24.731 | 25.078 | 0.0830 | 2.323 | 0.910 | 1.548 | 2.748 | 1.5 | 10.6 | 0.43 | 3.32 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 25.054 | 25.732 | 17.457 | 0.0281 | 8.105 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.23 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.737 | 24.792 | 22.600 | 0.0659 | 3.677 | 0.883 | 2.451 | 2.187 | 2.2 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.768 | 24.823 | 22.525 | 0.0656 | 3.776 | 0.878 | 2.517 | 2.174 | 2.3 | 10.1 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | +0.003 | [-0.003, +0.009] | [-0.005, +0.013] | 15 / 7 / 28 | 0.134 |
| final | observed | stable | periodic:1 | 50 | +0.005 | [-0.003, +0.014] | [-0.007, +0.020] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | base_stock | 50 | +0.005 | [-0.003, +0.013] | [-0.007, +0.019] | 41 / 9 / 0 | 0.0 |
| final | observed | stable | order_up_to | 50 | -0.472 | [-0.570, -0.383] | [-0.624, -0.344] | 45 / 5 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | -0.039 | [-0.140, +0.056] | [-0.210, +0.090] | 25 / 21 / 4 | 0.659 |
| final | observed | uncertain | periodic:1 | 50 | -0.037 | [-0.134, +0.054] | [-0.199, +0.091] | 26 / 22 / 2 | 0.665 |
| final | observed | uncertain | base_stock | 50 | -0.215 | [-0.319, -0.119] | [-0.391, -0.081] | 38 / 12 / 0 | 0.0 |
| final | observed | uncertain | order_up_to | 50 | -0.319 | [-0.455, -0.186] | [-0.538, -0.120] | 36 / 14 / 0 | 0.003 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.164 | [-0.349, +0.005] | [-0.485, +0.040] | 26 / 20 / 4 | 0.461 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.164 | [-0.345, +0.008] | [-0.493, +0.045] | 27 / 21 / 2 | 0.471 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.388 | [-0.693, -0.107] | [-0.937, -0.058] | 33 / 17 / 0 | 0.033 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -0.597 | [-0.911, -0.327] | [-1.128, -0.251] | 38 / 12 / 0 | 0.0 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.058 | [-0.098, -0.022] | [-0.124, -0.007] | 33 / 11 / 6 | 0.001 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.049 | [-0.087, -0.014] | [-0.116, -0.002] | 35 / 12 / 3 | 0.001 |
| final | observed | uncertain_lead_only | base_stock | 50 | -0.057 | [-0.096, -0.022] | [-0.119, -0.010] | 43 / 7 / 0 | 0.0 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -0.523 | [-0.643, -0.408] | [-0.713, -0.357] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | -0.007 | [-0.023, +0.008] | [-0.032, +0.015] | 18 / 8 / 24 | 0.076 |
| final | recovered | stable | periodic:1 | 50 | +0.001 | [-0.014, +0.016] | [-0.022, +0.023] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | base_stock | 50 | +0.001 | [-0.014, +0.015] | [-0.023, +0.023] | 40 / 9 / 1 | 0.0 |
| final | recovered | stable | order_up_to | 50 | -0.646 | [-0.800, -0.503] | [-0.885, -0.441] | 44 / 6 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | +0.014 | [-0.103, +0.145] | [-0.158, +0.230] | 26 / 21 / 3 | 0.56 |
| final | recovered | uncertain | periodic:1 | 50 | +0.025 | [-0.092, +0.158] | [-0.143, +0.234] | 27 / 21 / 2 | 0.471 |
| final | recovered | uncertain | base_stock | 50 | -0.197 | [-0.310, -0.078] | [-0.364, -0.012] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain | order_up_to | 50 | -0.244 | [-0.447, -0.027] | [-0.540, +0.106] | 35 / 15 / 0 | 0.007 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.126 | [-0.319, +0.047] | [-0.472, +0.098] | 30 / 18 / 2 | 0.111 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.121 | [-0.319, +0.056] | [-0.473, +0.101] | 28 / 21 / 1 | 0.392 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.371 | [-0.685, -0.081] | [-0.924, -0.022] | 32 / 18 / 0 | 0.065 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -0.627 | [-0.967, -0.324] | [-1.215, -0.230] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.029 | [-0.053, -0.007] | [-0.069, +0.003] | 32 / 13 / 5 | 0.007 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.013 | [-0.027, +0.002] | [-0.035, +0.009] | 35 / 12 / 3 | 0.001 |
| final | recovered | uncertain_lead_only | base_stock | 50 | -0.022 | [-0.038, -0.006] | [-0.046, +0.002] | 42 / 7 / 1 | 0.0 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -0.624 | [-0.784, -0.466] | [-0.900, -0.407] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.012 | [-0.022, -0.002] | [-0.028, +0.001] | 5 / 25 / 20 | 0.0 |
| val1 | observed | stable | periodic:1 | 50 | -0.003 | [-0.010, +0.003] | [-0.014, +0.005] | 20 / 24 / 6 | 0.652 |
| val1 | observed | stable | base_stock | 50 | -0.003 | [-0.010, +0.003] | [-0.013, +0.005] | 20 / 24 / 6 | 0.652 |
| val1 | observed | stable | order_up_to | 50 | -1.093 | [-1.407, -0.815] | [-1.647, -0.739] | 48 / 2 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | -0.230 | [-0.539, +0.051] | [-0.750, +0.144] | 27 / 22 / 1 | 0.568 |
| val1 | observed | uncertain | periodic:1 | 50 | -0.217 | [-0.529, +0.053] | [-0.755, +0.138] | 27 / 23 / 0 | 0.672 |
| val1 | observed | uncertain | base_stock | 50 | -0.179 | [-0.440, +0.062] | [-0.614, +0.162] | 26 / 24 / 0 | 0.888 |
| val1 | observed | uncertain | order_up_to | 50 | -1.108 | [-1.834, -0.476] | [-2.410, -0.338] | 40 / 10 / 0 | 0.0 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.469 | [+0.169, +0.803] | [+0.059, +0.998] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.462 | [+0.160, +0.789] | [+0.048, +0.981] | 21 / 29 / 0 | 0.322 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.481 | [+0.163, +0.814] | [+0.050, +1.034] | 22 / 28 / 0 | 0.48 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | -0.039 | [-0.295, +0.232] | [-0.392, +0.425] | 34 / 16 / 0 | 0.015 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.033 | [-0.129, +0.071] | [-0.174, +0.139] | 29 / 21 / 0 | 0.322 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.025 | [-0.121, +0.085] | [-0.164, +0.149] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | -0.025 | [-0.124, +0.078] | [-0.166, +0.147] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -1.255 | [-1.760, -0.816] | [-2.110, -0.698] | 44 / 6 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | -0.022 | [-0.049, +0.003] | [-0.072, +0.005] | 6 / 22 / 22 | 0.004 |
| val1 | recovered | stable | periodic:1 | 50 | -0.013 | [-0.042, +0.014] | [-0.066, +0.019] | 21 / 24 / 5 | 0.766 |
| val1 | recovered | stable | base_stock | 50 | -0.013 | [-0.043, +0.014] | [-0.067, +0.019] | 21 / 24 / 5 | 0.766 |
| val1 | recovered | stable | order_up_to | 50 | -1.360 | [-1.831, -0.972] | [-2.172, -0.890] | 48 / 2 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | -0.460 | [-1.322, +0.302] | [-2.029, +0.472] | 20 / 28 / 2 | 0.312 |
| val1 | recovered | uncertain | periodic:1 | 50 | -0.453 | [-1.329, +0.310] | [-2.005, +0.477] | 21 / 29 / 0 | 0.322 |
| val1 | recovered | uncertain | base_stock | 50 | -0.412 | [-1.253, +0.313] | [-1.866, +0.473] | 19 / 31 / 0 | 0.119 |
| val1 | recovered | uncertain | order_up_to | 50 | -1.510 | [-2.784, -0.364] | [-3.793, -0.157] | 39 / 11 / 0 | 0.0 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +0.187 | [-0.026, +0.397] | [-0.129, +0.508] | 22 / 27 / 1 | 0.568 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.189 | [-0.021, +0.404] | [-0.131, +0.530] | 24 / 25 / 1 | 1.0 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +0.167 | [-0.036, +0.373] | [-0.155, +0.492] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | -0.505 | [-0.951, -0.088] | [-1.276, +0.079] | 30 / 20 / 0 | 0.203 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.018 | [-0.102, +0.069] | [-0.141, +0.112] | 21 / 29 / 0 | 0.322 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.008 | [-0.092, +0.079] | [-0.134, +0.131] | 20 / 30 / 0 | 0.203 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | -0.008 | [-0.093, +0.078] | [-0.135, +0.124] | 20 / 30 / 0 | 0.203 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -1.446 | [-1.910, -1.035] | [-2.267, -0.895] | 47 / 3 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | -0.009 | [-0.020, +0.001] | [-0.027, +0.004] | 9 / 25 / 16 | 0.009 |
| val2 | observed | stable | periodic:1 | 50 | +0.019 | [+0.009, +0.029] | [+0.005, +0.035] | 18 / 29 / 3 | 0.144 |
| val2 | observed | stable | base_stock | 50 | +0.019 | [+0.009, +0.029] | [+0.005, +0.035] | 18 / 29 / 3 | 0.144 |
| val2 | observed | stable | order_up_to | 50 | -1.247 | [-1.773, -0.765] | [-2.213, -0.694] | 48 / 2 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | +0.322 | [+0.115, +0.549] | [+0.032, +0.687] | 20 / 30 / 0 | 0.203 |
| val2 | observed | uncertain | periodic:1 | 50 | +0.334 | [+0.122, +0.561] | [+0.045, +0.714] | 19 / 31 / 0 | 0.119 |
| val2 | observed | uncertain | base_stock | 50 | +0.411 | [+0.177, +0.665] | [+0.069, +0.815] | 17 / 33 / 0 | 0.033 |
| val2 | observed | uncertain | order_up_to | 50 | -0.431 | [-0.865, -0.022] | [-1.175, +0.147] | 36 / 14 / 0 | 0.003 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.113 | [-0.084, +0.314] | [-0.183, +0.437] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.104 | [-0.100, +0.314] | [-0.213, +0.424] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.089 | [-0.105, +0.285] | [-0.206, +0.392] | 21 / 29 / 0 | 0.322 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | -0.185 | [-0.432, +0.061] | [-0.567, +0.192] | 33 / 17 / 0 | 0.033 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.097 | [-0.190, +0.000] | [-0.239, +0.051] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.098 | [-0.186, -0.009] | [-0.231, +0.046] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.096 | [-0.185, -0.004] | [-0.229, +0.041] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -1.369 | [-1.977, -0.838] | [-2.429, -0.691] | 46 / 4 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | -0.004 | [-0.029, +0.023] | [-0.043, +0.040] | 6 / 22 / 22 | 0.004 |
| val2 | recovered | stable | periodic:1 | 50 | +0.023 | [-0.002, +0.049] | [-0.015, +0.069] | 23 / 25 / 2 | 0.885 |
| val2 | recovered | stable | base_stock | 50 | +0.023 | [-0.002, +0.050] | [-0.013, +0.066] | 23 / 25 / 2 | 0.885 |
| val2 | recovered | stable | order_up_to | 50 | -1.320 | [-1.749, -0.942] | [-2.040, -0.862] | 48 / 2 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | +0.453 | [+0.116, +0.818] | [-0.023, +1.045] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain | periodic:1 | 50 | +0.459 | [+0.122, +0.816] | [-0.016, +1.016] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain | base_stock | 50 | +0.511 | [+0.142, +0.917] | [-0.003, +1.182] | 28 / 22 / 0 | 0.48 |
| val2 | recovered | uncertain | order_up_to | 50 | -0.496 | [-0.959, -0.062] | [-1.225, +0.137] | 35 / 15 / 0 | 0.007 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | +0.189 | [-0.301, +0.638] | [-0.663, +0.815] | 16 / 32 / 2 | 0.029 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.170 | [-0.394, +0.645] | [-0.726, +0.829] | 19 / 31 / 0 | 0.119 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | +0.141 | [-0.384, +0.613] | [-0.732, +0.794] | 17 / 33 / 0 | 0.033 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | -0.206 | [-0.763, +0.335] | [-1.163, +0.541] | 26 / 24 / 0 | 0.888 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.375 | [-0.696, -0.096] | [-0.957, -0.019] | 24 / 24 / 2 | 1.0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.344 | [-0.654, -0.065] | [-0.899, +0.007] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.342 | [-0.661, -0.058] | [-0.903, +0.011] | 23 / 27 / 0 | 0.672 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -1.661 | [-2.399, -1.018] | [-2.912, -0.859] | 46 / 4 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | +0.0085 | [-0.0126, +0.0368] | 1 / 3 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0158 | [-0.0275, +0.0752] | 11 / 6 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | -0.0005 | [-0.0020, +0.0009] | 1 / 3 |
| final | observed | stable | periodic:1 | shortage | 50 | +0.0312 | [-0.0019, +0.0739] | 1 / 9 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0039 | [-0.0419, +0.0639] | 26 / 8 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0024 | [-0.0049, -0.0003] | 1 / 9 |
| final | observed | stable | base_stock | shortage | 50 | +0.0312 | [-0.0028, +0.0738] | 1 / 9 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | +0.0039 | [-0.0405, +0.0674] | 26 / 8 |
| final | observed | stable | base_stock | service_unit_fill | 50 | -0.0024 | [-0.0049, -0.0003] | 1 / 9 |
| final | observed | stable | order_up_to | shortage | 50 | -1.4771 | [-1.9082, -1.0979] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9486 | [+0.5768, +1.5795] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1412 | [+0.1130, +0.1685] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.1523 | [-0.5517, +0.1373] | 10 / 8 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.5407 | [+0.0841, +1.3581] | 10 / 29 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0060 | [-0.0117, +0.0235] | 10 / 8 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.1399 | [-0.5464, +0.1422] | 10 / 9 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5386 | [+0.0836, +1.3668] | 12 / 30 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0043 | [-0.0138, +0.0208] | 10 / 9 |
| final | observed | uncertain | base_stock | shortage | 50 | -0.0781 | [-0.4598, +0.2029] | 9 / 17 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.4143 | [+0.0089, +1.1412] | 27 / 23 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | -0.0008 | [-0.0195, +0.0159] | 9 / 17 |
| final | observed | uncertain | order_up_to | shortage | 50 | -1.6065 | [-2.2252, -1.0927] | 41 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.1667 | [+0.4851, +2.4367] | 1 / 49 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1457 | [+0.1171, +0.1760] | 41 / 0 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.0362 | [-0.1656, +0.0911] | 10 / 8 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.6569 | [+0.1693, +1.5338] | 7 / 34 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0025 | [-0.0055, +0.0119] | 10 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0303 | [-0.1638, +0.0934] | 8 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.6533 | [+0.1694, +1.5274] | 10 / 34 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0018 | [-0.0060, +0.0106] | 8 / 8 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | +0.0328 | [-0.0911, +0.1690] | 6 / 13 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.5254 | [+0.0742, +1.3698] | 23 / 27 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0016 | [-0.0094, +0.0077] | 6 / 13 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.4329 | [-1.8402, -1.0560] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.4225 | [+0.6731, +2.8026] | 0 / 50 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1334 | [+0.1053, +0.1637] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.1779 | [-0.3738, -0.0274] | 8 / 2 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.1164 | [+0.0413, +0.2139] | 13 / 25 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0089 | [+0.0010, +0.0181] | 8 / 2 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.1467 | [-0.3337, -0.0076] | 6 / 3 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.1089 | [+0.0327, +0.2085] | 17 / 24 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0078 | [+0.0006, +0.0167] | 6 / 3 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.1467 | [-0.3417, -0.0066] | 6 / 3 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.1089 | [+0.0353, +0.1997] | 17 / 24 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0078 | [+0.0008, +0.0165] | 6 / 3 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -1.6414 | [-2.1639, -1.1424] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.8384 | [+0.5317, +1.3721] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1424 | [+0.1147, +0.1704] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | -0.0377 | [-0.1050, +0.0213] | 3 / 1 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0265 | [-0.0269, +0.0849] | 13 / 9 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0041 | [-0.0003, +0.0104] | 3 / 1 |
| final | recovered | stable | periodic:1 | shortage | 50 | +0.0053 | [-0.0587, +0.0646] | 3 / 5 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0061 | [-0.0475, +0.0673] | 26 / 8 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0006 | [-0.0048, +0.0071] | 3 / 5 |
| final | recovered | stable | base_stock | shortage | 50 | +0.0053 | [-0.0589, +0.0636] | 3 / 5 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0061 | [-0.0480, +0.0696] | 26 / 8 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | +0.0006 | [-0.0047, +0.0071] | 3 / 5 |
| final | recovered | stable | order_up_to | shortage | 50 | -2.0354 | [-2.7570, -1.4330] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.3492 | [+0.8566, +2.1445] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1558 | [+0.1313, +0.1802] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.1747 | [-0.4189, +0.0205] | 15 / 4 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.5326 | [+0.1023, +1.2894] | 15 / 27 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0069 | [-0.0090, +0.0209] | 15 / 4 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.1560 | [-0.4016, +0.0296] | 12 / 6 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5191 | [+0.0885, +1.2927] | 16 / 28 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0043 | [-0.0112, +0.0175] | 12 / 6 |
| final | recovered | uncertain | base_stock | shortage | 50 | -0.1188 | [-0.3611, +0.0739] | 9 / 11 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.3664 | [-0.0137, +1.0442] | 32 / 18 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0016 | [-0.0149, +0.0157] | 9 / 11 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -1.9829 | [-2.7691, -1.3451] | 42 / 0 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +1.4965 | [+0.7047, +2.8801] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1518 | [+0.1210, +0.1820] | 42 / 0 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.0367 | [-0.2440, +0.2031] | 11 / 5 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.6974 | [+0.1667, +1.5926] | 11 / 34 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0028 | [-0.0051, +0.0110] | 11 / 5 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0093 | [-0.2154, +0.2272] | 10 / 7 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.6923 | [+0.1687, +1.5769] | 12 / 35 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | -0.0002 | [-0.0080, +0.0072] | 10 / 7 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | +0.0367 | [-0.1622, +0.2706] | 6 / 9 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.5300 | [+0.0493, +1.3428] | 25 / 25 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0034 | [-0.0111, +0.0038] | 6 / 9 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -1.8140 | [-2.5272, -1.2425] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.8484 | [+0.9223, +3.4317] | 0 / 50 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1409 | [+0.1113, +0.1713] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.0763 | [-0.1935, +0.0213] | 8 / 6 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.0600 | [-0.0333, +0.1436] | 10 / 27 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0040 | [-0.0027, +0.0111] | 8 / 6 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.0220 | [-0.0851, +0.0362] | 7 / 6 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.0545 | [-0.0289, +0.1407] | 16 / 25 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0002 | [-0.0043, +0.0047] | 7 / 6 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.0220 | [-0.0876, +0.0356] | 7 / 6 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.0545 | [-0.0355, +0.1363] | 16 / 25 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0002 | [-0.0043, +0.0046] | 7 / 6 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -1.9550 | [-2.7483, -1.3049] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.1334 | [+0.7452, +1.7513] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1477 | [+0.1192, +0.1763] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.0393 | [-0.0880, -0.0010] | 4 / 2 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0507 | [+0.0175, +0.1098] | 1 / 27 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0041 | [+0.0000, +0.0095] | 4 / 2 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.0116 | [-0.0420, +0.0133] | 4 / 7 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0315 | [-0.0030, +0.0867] | 23 / 21 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0023 | [-0.0008, +0.0071] | 4 / 7 |
| val1 | observed | stable | base_stock | shortage | 50 | -0.0116 | [-0.0411, +0.0136] | 4 / 7 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0315 | [-0.0033, +0.0885] | 23 / 21 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | +0.0023 | [-0.0008, +0.0072] | 4 / 7 |
| val1 | observed | stable | order_up_to | shortage | 50 | -3.5544 | [-5.1990, -2.5296] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9382 | [+0.6278, +1.4148] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1679 | [+0.1481, +0.1894] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -1.4535 | [-2.7679, -0.5685] | 32 / 3 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.8871 | [+0.6069, +1.2383] | 2 / 47 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0366 | [+0.0246, +0.0492] | 32 / 3 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -1.4235 | [-2.7733, -0.5468] | 33 / 4 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.8787 | [+0.5875, +1.2300] | 3 / 47 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0349 | [+0.0234, +0.0478] | 33 / 4 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.1809 | [-2.2689, -0.4118] | 31 / 9 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.7729 | [+0.5175, +1.0606] | 6 / 44 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0290 | [+0.0177, +0.0413] | 31 / 9 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -5.2674 | [-8.7448, -3.1006] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.6366 | [+1.1156, +2.3929] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1962 | [+0.1781, +0.2149] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.3222 | [-0.5004, -0.1664] | 22 / 5 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.6255 | [+0.7385, +2.9657] | 3 / 47 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0174 | [+0.0073, +0.0281] | 22 / 5 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.3079 | [-0.4759, -0.1563] | 22 / 6 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.6144 | [+0.7351, +3.0423] | 4 / 46 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0167 | [+0.0073, +0.0272] | 22 / 6 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1961 | [-0.3497, -0.0609] | 16 / 14 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.4733 | [+0.6359, +2.7024] | 4 / 46 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0111 | [+0.0023, +0.0211] | 16 / 14 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.2568 | [-4.7012, -2.3207] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.4874 | [+1.3393, +4.3180] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1547 | [+0.1325, +0.1782] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.5385 | [-0.7992, -0.3057] | 31 / 2 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.6853 | [+0.3989, +1.0541] | 1 / 49 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0343 | [+0.0175, +0.0591] | 31 / 2 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.5162 | [-0.7735, -0.2848] | 31 / 2 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.6781 | [+0.3887, +1.0510] | 2 / 48 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0315 | [+0.0168, +0.0524] | 31 / 2 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.5162 | [-0.7780, -0.2797] | 31 / 2 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.6781 | [+0.3957, +1.0448] | 2 / 48 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0315 | [+0.0164, +0.0527] | 31 / 2 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.5133 | [-6.9710, -2.9730] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.5206 | [+0.9825, +2.3550] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1932 | [+0.1737, +0.2140] | 50 / 0 |
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
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -2.0301 | [-4.5869, -0.4519] | 27 / 5 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.3482 | [+0.6727, +2.3341] | 3 / 45 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0251 | [+0.0074, +0.0416] | 27 / 5 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -2.0031 | [-4.6563, -0.4411] | 28 / 5 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3371 | [+0.6623, +2.3446] | 5 / 45 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0236 | [+0.0062, +0.0397] | 28 / 5 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -1.6951 | [-4.0997, -0.2723] | 24 / 11 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.2129 | [+0.5696, +2.1421] | 9 / 41 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0184 | [+0.0000, +0.0340] | 24 / 11 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -6.6431 | [-11.6855, -3.5824] | 48 / 1 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.4098 | [+1.4898, +3.9051] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1946 | [+0.1684, +0.2194] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.3156 | [-0.6332, -0.0408] | 20 / 7 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.0988 | [+0.7353, +1.5587] | 1 / 48 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0133 | [+0.0021, +0.0253] | 20 / 7 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.2952 | [-0.5920, -0.0337] | 18 / 7 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.0840 | [+0.7126, +1.5352] | 3 / 46 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0123 | [+0.0010, +0.0240] | 18 / 7 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.1820 | [-0.4690, +0.0627] | 12 / 15 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.9224 | [+0.5851, +1.3324] | 6 / 44 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0071 | [-0.0045, +0.0181] | 12 / 15 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.0004 | [-6.0047, -2.7011] | 48 / 1 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.3071 | [+1.6859, +3.1093] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1570 | [+0.1322, +0.1820] | 48 / 1 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.3970 | [-0.6570, -0.1714] | 20 / 6 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.5818 | [+0.3842, +0.8422] | 5 / 45 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0201 | [+0.0038, +0.0426] | 20 / 6 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.3647 | [-0.6128, -0.1387] | 20 / 7 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.5721 | [+0.3680, +0.8314] | 6 / 44 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0182 | [+0.0021, +0.0397] | 20 / 7 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.3647 | [-0.6281, -0.1364] | 20 / 7 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5721 | [+0.3612, +0.8312] | 6 / 44 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0182 | [+0.0023, +0.0399] | 20 / 7 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -4.9838 | [-7.3942, -3.4076] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7706 | [+1.2448, +2.5852] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1900 | [+0.1668, +0.2147] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.0378 | [-0.0888, -0.0001] | 6 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0410 | [+0.0185, +0.0642] | 5 / 27 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0050 | [+0.0004, +0.0124] | 6 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 50 | +0.0472 | [+0.0050, +0.0978] | 5 / 10 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0279 | [+0.0035, +0.0521] | 19 / 28 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0020 | [-0.0055, +0.0015] | 5 / 10 |
| val2 | observed | stable | base_stock | shortage | 50 | +0.0472 | [+0.0052, +0.0967] | 5 / 10 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | +0.0279 | [+0.0039, +0.0528] | 19 / 28 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | -0.0020 | [-0.0055, +0.0015] | 5 / 10 |
| val2 | observed | stable | order_up_to | shortage | 50 | -3.9852 | [-6.8627, -2.3425] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.9113 | [+0.6777, +1.2638] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1638 | [+0.1413, +0.1886] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -0.8601 | [-1.5975, -0.3927] | 28 / 8 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.3168 | [+0.7401, +2.1161] | 1 / 49 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0261 | [+0.0161, +0.0366] | 28 / 8 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -0.8242 | [-1.5543, -0.3404] | 27 / 11 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3151 | [+0.7467, +2.1333] | 1 / 49 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0230 | [+0.0138, +0.0338] | 27 / 11 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -0.5377 | [-0.8753, -0.2648] | 24 / 13 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.1979 | [+0.6728, +1.8988] | 3 / 47 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0190 | [+0.0094, +0.0296] | 24 / 13 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -4.8801 | [-8.5446, -2.7568] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.9927 | [+1.2935, +2.9988] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1832 | [+0.1613, +0.2086] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.5398 | [-1.0011, -0.1913] | 22 / 6 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.1590 | [+0.5502, +2.1547] | 2 / 48 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0196 | [+0.0083, +0.0328] | 22 / 6 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.5124 | [-0.9467, -0.1758] | 21 / 6 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.1490 | [+0.5519, +2.1368] | 2 / 48 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0168 | [+0.0071, +0.0286] | 21 / 6 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.3545 | [-0.6414, -0.1168] | 17 / 10 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.0156 | [+0.4574, +1.9969] | 7 / 43 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0143 | [+0.0041, +0.0259] | 17 / 10 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.6285 | [-6.4636, -2.0350] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.9750 | [+1.2323, +3.1659] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1440 | [+0.1204, +0.1699] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.5834 | [-0.9159, -0.3071] | 22 / 1 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7895 | [+0.3102, +1.6267] | 3 / 46 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0250 | [+0.0141, +0.0388] | 22 / 1 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.5660 | [-0.8885, -0.2899] | 22 / 4 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7808 | [+0.3020, +1.6237] | 3 / 47 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0237 | [+0.0126, +0.0376] | 22 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.5623 | [-0.8987, -0.2749] | 22 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.7806 | [+0.3027, +1.6195] | 3 / 47 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0233 | [+0.0124, +0.0370] | 22 / 4 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.6638 | [-7.7246, -2.7257] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.5964 | [+0.9488, +2.7377] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1740 | [+0.1536, +0.1957] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.0681 | [-0.1520, -0.0087] | 5 / 0 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0473 | [+0.0221, +0.0794] | 2 / 24 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0066 | [+0.0006, +0.0158] | 5 / 0 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | +0.0179 | [-0.0613, +0.0872] | 5 / 10 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0119 | [-0.0181, +0.0487] | 32 / 16 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0005 | [-0.0054, +0.0053] | 5 / 10 |
| val2 | recovered | stable | base_stock | shortage | 50 | +0.0179 | [-0.0612, +0.0888] | 5 / 10 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | +0.0120 | [-0.0173, +0.0488] | 32 / 16 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0005 | [-0.0055, +0.0049] | 5 / 10 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -4.2920 | [-6.5494, -2.9056] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.3158 | [+0.9412, +1.9231] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1715 | [+0.1497, +0.1945] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -0.9653 | [-1.4892, -0.4986] | 26 / 8 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.9982 | [+0.6665, +1.3995] | 3 / 47 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0382 | [+0.0208, +0.0586] | 26 / 8 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -0.9258 | [-1.4259, -0.4619] | 26 / 8 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.9898 | [+0.6573, +1.4031] | 4 / 46 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0353 | [+0.0178, +0.0555] | 26 / 8 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -0.5691 | [-1.2056, +0.1833] | 25 / 11 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.8480 | [+0.5105, +1.2576] | 9 / 41 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0316 | [+0.0144, +0.0513] | 25 / 11 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -5.8947 | [-9.2822, -3.7027] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.0301 | [+1.5708, +2.5653] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2068 | [+0.1794, +0.2381] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -1.2261 | [-3.2797, -0.0511] | 25 / 6 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.2288 | [+0.6193, +2.1773] | 5 / 43 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0123 | [-0.0050, +0.0270] | 25 / 6 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -1.1937 | [-3.2626, -0.0274] | 24 / 8 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.2115 | [+0.5966, +2.1687] | 7 / 43 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0093 | [-0.0070, +0.0236] | 24 / 8 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -1.0116 | [-2.8219, +0.0591] | 19 / 14 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.0486 | [+0.4827, +1.8914] | 8 / 42 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0060 | [-0.0099, +0.0204] | 19 / 14 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.8684 | [-8.8116, -2.5435] | 46 / 2 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.4347 | [+1.5976, +3.7871] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1530 | [+0.1270, +0.1788] | 46 / 2 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.4534 | [-3.1242, -0.4686] | 30 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.5737 | [+0.3118, +0.9790] | 3 / 43 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0313 | [+0.0197, +0.0460] | 30 / 0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.3540 | [-3.0495, -0.3709] | 27 / 3 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.5611 | [+0.3005, +0.9928] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0267 | [+0.0154, +0.0407] | 27 / 3 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -1.3493 | [-3.0025, -0.3787] | 26 / 4 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5609 | [+0.3015, +0.9853] | 5 / 45 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0263 | [+0.0148, +0.0406] | 26 / 4 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -5.7825 | [-9.4316, -3.4137] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7955 | [+1.2284, +2.7391] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1921 | [+0.1716, +0.2131] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1200 of 1200 (9376 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val2/recovered/uncertain store 514 product 267: ZAAD minus base_stock = +12.674 (fill 0.841 vs 0.865, inventory 17.30 vs 18.72, retained incumbent on 11 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +9.708 (fill 0.922 vs 0.922, inventory 47.94 vs 20.54, retained incumbent on 4 reviews)
- val1/observed/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +8.479 (fill 0.917 vs 0.883, inventory 8.19 vs 1.08, retained incumbent on 6 reviews)
- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus order_up_to = +8.335 (fill 0.679 vs 0.705, inventory 5.17 vs 1.27, retained incumbent on 12 reviews)
- val2/recovered/uncertain store 855 product 647: ZAAD minus order_up_to = +6.357 (fill 0.799 vs 0.642, inventory 5.33 vs 1.35, retained incumbent on 12 reviews)
- val2/observed/uncertain store 102 product 467: ZAAD minus periodic:1 = +6.240 (fill 0.971 vs 0.905, inventory 4.10 vs 2.55, retained incumbent on 9 reviews)
- final/recovered/uncertain store 514 product 267: ZAAD minus order_up_to = +6.062 (fill 0.954 vs 0.954, inventory 50.24 vs 17.32, retained incumbent on 3 reviews)
- val2/observed/uncertain store 869 product 191: ZAAD minus base_stock = +5.559 (fill 0.969 vs 0.969, inventory 6.00 vs 2.14, retained incumbent on 6 reviews)
- val1/recovered/uncertain store 116 product 377: ZAAD minus periodic:1 = +4.903 (fill 0.780 vs 0.823, inventory 3.72 vs 1.06, retained incumbent on 6 reviews)
- val1/recovered/uncertain store 75 product 350: ZAAD minus reorder_point = +4.872 (fill 0.725 vs 1.000, inventory 3.03 vs 2.01, retained incumbent on 9 reviews)
