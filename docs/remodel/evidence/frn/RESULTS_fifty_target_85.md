# FreshRetailNet pilot results: stage `fifty_target_85`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `ff56962a149d`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3657 s, peak RSS 223 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.15 |
| final | observed | stable | gated | 50/50 | 10.281 | 10.545 | 8.515 | 0.0046 | 0.602 | 0.958 | 0.401 | 1.333 | 0.8 | 5.3 | 0.10 | 0.54 |
| final | observed | stable | order_up_to | 50/50 | 10.699 | 11.052 | 8.089 | 0.0023 | 1.877 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.09 |
| final | observed | stable | periodic:1 | 50/50 | 10.269 | 10.844 | 10.106 | 0.0047 | 0.560 | 0.965 | 0.374 | 1.358 | 0.8 | 6.6 |  | 0.02 |
| final | observed | stable | reorder_point | 50/50 | 10.278 | 10.606 | 8.845 | 0.0047 | 0.591 | 0.960 | 0.394 | 1.351 | 0.8 | 5.4 |  | 0.02 |
| final | observed | uncertain | base_stock | 50/50 | 12.342 | 13.358 | 12.809 | 0.0053 | 2.166 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.292 | 12.893 | 10.461 | 0.0065 | 2.389 | 0.871 | 1.593 | 1.874 | 1.5 | 3.6 | 0.45 | 0.71 |
| final | observed | uncertain | order_up_to | 50/50 | 12.460 | 13.150 | 9.724 | 0.0027 | 3.695 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.190 | 12.877 | 10.651 | 0.0042 | 2.512 | 0.858 | 1.674 | 1.223 | 1.7 | 5.5 |  | 0.02 |
| final | observed | uncertain | reorder_point | 50/50 | 12.191 | 12.878 | 10.642 | 0.0042 | 2.517 | 0.857 | 1.678 | 1.221 | 1.7 | 5.3 |  | 0.02 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 11.704 | 12.703 | 13.134 | 0.0064 | 1.142 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.237 | 11.814 | 10.424 | 0.0079 | 1.262 | 0.942 | 0.841 | 2.281 | 1.0 | 3.7 | 0.51 | 0.93 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 11.929 | 12.589 | 10.129 | 0.0033 | 2.608 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.10 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.505 | 12.145 | 10.814 | 0.0052 | 1.427 | 0.931 | 0.951 | 1.516 | 1.2 | 5.6 |  | 0.03 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.507 | 12.147 | 10.805 | 0.0052 | 1.433 | 0.930 | 0.955 | 1.513 | 1.2 | 5.4 |  | 0.02 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 10.884 | 11.936 | 11.336 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.12 |
| final | observed | uncertain_lead_only | gated | 50/50 | 10.897 | 11.349 | 8.232 | 0.0047 | 2.446 | 0.893 | 1.630 | 1.360 | 1.4 | 4.0 | 0.45 | 0.85 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 11.365 | 12.079 | 8.578 | 0.0025 | 3.868 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.10 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 10.943 | 11.678 | 9.558 | 0.0043 | 2.583 | 0.881 | 1.722 | 1.253 | 1.5 | 5.4 |  | 0.03 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 10.945 | 11.679 | 9.541 | 0.0043 | 2.592 | 0.881 | 1.728 | 1.249 | 1.5 | 5.1 |  | 0.03 |
| final | recovered | stable | base_stock | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.15 |
| final | recovered | stable | gated | 50/50 | 11.479 | 11.786 | 9.300 | 0.0062 | 0.676 | 0.950 | 0.451 | 1.796 | 0.8 | 5.1 | 0.13 | 0.47 |
| final | recovered | stable | order_up_to | 50/50 | 12.024 | 12.432 | 8.640 | 0.0030 | 2.350 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.09 |
| final | recovered | stable | periodic:1 | 50/50 | 11.444 | 12.145 | 11.323 | 0.0065 | 0.577 | 0.959 | 0.385 | 1.877 | 0.7 | 6.6 |  | 0.03 |
| final | recovered | stable | reorder_point | 50/50 | 11.457 | 11.887 | 9.931 | 0.0065 | 0.621 | 0.955 | 0.414 | 1.870 | 0.7 | 5.3 |  | 0.03 |
| final | recovered | uncertain | base_stock | 50/50 | 13.746 | 14.957 | 14.958 | 0.0069 | 1.855 | 0.896 | 1.237 | 1.994 | 1.3 | 6.2 |  | 0.12 |
| final | recovered | uncertain | gated | 50/50 | 13.611 | 14.335 | 12.098 | 0.0076 | 2.146 | 0.877 | 1.431 | 2.201 | 1.4 | 3.7 | 0.46 | 0.67 |
| final | recovered | uncertain | order_up_to | 50/50 | 13.814 | 14.586 | 10.883 | 0.0030 | 3.719 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.10 |
| final | recovered | uncertain | periodic:1 | 50/50 | 13.520 | 14.349 | 12.476 | 0.0054 | 2.157 | 0.871 | 1.438 | 1.562 | 1.5 | 5.5 |  | 0.02 |
| final | recovered | uncertain | reorder_point | 50/50 | 13.528 | 14.358 | 12.469 | 0.0054 | 2.175 | 0.871 | 1.450 | 1.556 | 1.5 | 5.1 |  | 0.02 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 12.878 | 14.085 | 15.203 | 0.0085 | 0.730 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.502 | 13.107 | 11.558 | 0.0084 | 1.029 | 0.944 | 0.686 | 2.436 | 1.0 | 3.7 | 0.51 | 0.86 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 13.158 | 13.908 | 11.255 | 0.0040 | 2.580 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.664 | 13.465 | 12.605 | 0.0068 | 1.036 | 0.938 | 0.691 | 1.983 | 1.2 | 5.4 |  | 0.02 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.665 | 13.465 | 12.597 | 0.0068 | 1.043 | 0.937 | 0.696 | 1.980 | 1.2 | 5.1 |  | 0.03 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 11.907 | 13.171 | 13.295 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 6.2 |  | 0.11 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 11.969 | 12.577 | 9.850 | 0.0060 | 2.135 | 0.895 | 1.423 | 1.739 | 1.4 | 3.9 | 0.44 | 0.80 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 12.531 | 13.337 | 9.627 | 0.0030 | 3.866 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.10 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 11.999 | 12.896 | 11.226 | 0.0057 | 2.230 | 0.892 | 1.487 | 1.660 | 1.4 | 5.3 |  | 0.03 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 12.013 | 12.910 | 11.194 | 0.0057 | 2.275 | 0.889 | 1.516 | 1.658 | 1.4 | 4.8 |  | 0.03 |
| val1 | observed | stable | base_stock | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.54 |
| val1 | observed | stable | gated | 50/50 | 18.337 | 18.778 | 17.478 | 0.0108 | 1.047 | 0.941 | 0.698 | 1.157 | 1.8 | 11.4 | 0.05 | 2.81 |
| val1 | observed | stable | order_up_to | 50/50 | 19.352 | 19.639 | 14.512 | 0.0047 | 4.260 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.335 | 18.774 | 17.454 | 0.0104 | 1.057 | 0.940 | 0.705 | 1.126 | 1.7 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.344 | 18.782 | 17.433 | 0.0103 | 1.084 | 0.938 | 0.723 | 1.114 | 1.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 21.214 | 21.993 | 19.912 | 0.0144 | 3.244 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.42 |
| val1 | observed | uncertain | gated | 50/50 | 21.021 | 22.116 | 22.453 | 0.0248 | 2.238 | 0.920 | 1.492 | 2.543 | 1.9 | 9.7 | 0.67 | 2.87 |
| val1 | observed | uncertain | order_up_to | 50/50 | 22.165 | 22.764 | 15.839 | 0.0061 | 7.330 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 21.423 | 22.139 | 18.804 | 0.0111 | 4.230 | 0.862 | 2.820 | 1.243 | 3.2 | 12.2 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 21.433 | 22.149 | 18.791 | 0.0111 | 4.253 | 0.861 | 2.835 | 1.240 | 3.2 | 11.5 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 20.705 | 21.519 | 20.968 | 0.0171 | 1.839 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.43 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.399 | 22.412 | 22.853 | 0.0379 | 1.727 | 0.933 | 1.152 | 2.993 | 1.4 | 9.6 | 0.68 | 3.56 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.251 | 21.819 | 17.195 | 0.0073 | 4.899 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.22 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 20.759 | 21.486 | 20.125 | 0.0133 | 2.293 | 0.905 | 1.529 | 1.319 | 2.3 | 12.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 20.772 | 21.500 | 20.089 | 0.0133 | 2.341 | 0.904 | 1.561 | 1.317 | 2.3 | 11.6 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.43 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 19.049 | 19.939 | 18.959 | 0.0244 | 2.655 | 0.897 | 1.770 | 2.040 | 2.3 | 11.7 | 0.57 | 3.52 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.239 | 20.878 | 14.535 | 0.0062 | 6.896 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.23 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 19.143 | 19.925 | 17.617 | 0.0123 | 3.457 | 0.851 | 2.305 | 1.262 | 3.2 | 11.6 |  | 0.04 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 19.149 | 19.931 | 17.601 | 0.0123 | 3.477 | 0.850 | 2.318 | 1.258 | 3.2 | 10.9 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.53 |
| val1 | recovered | stable | gated | 50/50 | 22.229 | 22.794 | 20.735 | 0.0130 | 1.512 | 0.938 | 1.008 | 1.503 | 1.5 | 11.1 | 0.04 | 2.93 |
| val1 | recovered | stable | order_up_to | 50/50 | 23.462 | 23.845 | 17.176 | 0.0057 | 5.398 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.22 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.225 | 22.778 | 20.680 | 0.0130 | 1.502 | 0.937 | 1.001 | 1.502 | 1.6 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.229 | 22.781 | 20.666 | 0.0129 | 1.514 | 0.936 | 1.009 | 1.485 | 1.6 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 25.601 | 26.598 | 24.322 | 0.0170 | 3.536 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain | gated | 50/50 | 26.603 | 27.706 | 27.173 | 0.0676 | 2.352 | 0.935 | 1.568 | 3.846 | 1.4 | 9.2 | 0.65 | 2.87 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 26.729 | 27.472 | 19.189 | 0.0071 | 8.484 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.22 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 25.847 | 26.758 | 22.947 | 0.0131 | 4.710 | 0.879 | 3.140 | 1.601 | 2.7 | 12.1 |  | 0.04 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 25.853 | 26.764 | 22.926 | 0.0131 | 4.740 | 0.878 | 3.160 | 1.598 | 2.8 | 11.2 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 24.845 | 25.831 | 25.415 | 0.0202 | 1.614 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.39 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.457 | 26.511 | 26.680 | 0.0502 | 1.465 | 0.943 | 0.977 | 3.769 | 1.3 | 9.3 | 0.66 | 3.63 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 25.552 | 26.242 | 20.790 | 0.0082 | 5.432 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.22 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 24.854 | 25.718 | 24.294 | 0.0153 | 2.129 | 0.913 | 1.419 | 1.705 | 2.0 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 24.860 | 25.725 | 24.290 | 0.0152 | 2.140 | 0.912 | 1.426 | 1.694 | 2.0 | 11.2 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.41 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 22.796 | 23.892 | 22.841 | 0.0295 | 2.715 | 0.919 | 1.810 | 2.762 | 1.7 | 11.0 | 0.55 | 3.47 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 24.224 | 25.019 | 17.761 | 0.0070 | 7.654 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.22 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 22.921 | 23.923 | 21.551 | 0.0143 | 3.621 | 0.877 | 2.414 | 1.635 | 2.5 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 22.929 | 23.928 | 21.526 | 0.0143 | 3.643 | 0.875 | 2.429 | 1.629 | 2.5 | 10.4 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.53 |
| val2 | observed | stable | gated | 50/50 | 18.313 | 18.787 | 17.523 | 0.0104 | 0.970 | 0.947 | 0.647 | 1.117 | 1.4 | 11.7 | 0.03 | 2.63 |
| val2 | observed | stable | order_up_to | 50/50 | 19.497 | 19.844 | 14.397 | 0.0047 | 4.632 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.24 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.292 | 18.756 | 17.511 | 0.0103 | 0.911 | 0.951 | 0.607 | 1.106 | 1.4 | 12.6 |  | 0.05 |
| val2 | observed | stable | reorder_point | 50/50 | 18.314 | 18.783 | 17.473 | 0.0103 | 0.984 | 0.946 | 0.656 | 1.103 | 1.4 | 11.6 |  | 0.05 |
| val2 | observed | uncertain | base_stock | 50/50 | 21.384 | 22.252 | 20.616 | 0.0143 | 2.937 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.42 |
| val2 | observed | uncertain | gated | 50/50 | 21.720 | 22.677 | 21.923 | 0.0238 | 2.574 | 0.912 | 1.716 | 2.383 | 1.7 | 10.0 | 0.68 | 3.16 |
| val2 | observed | uncertain | order_up_to | 50/50 | 22.247 | 22.882 | 15.949 | 0.0055 | 7.279 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.25 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 21.607 | 22.406 | 19.433 | 0.0106 | 3.981 | 0.871 | 2.654 | 1.061 | 2.8 | 12.3 |  | 0.05 |
| val2 | observed | uncertain | reorder_point | 50/50 | 21.617 | 22.415 | 19.407 | 0.0106 | 4.015 | 0.869 | 2.676 | 1.061 | 2.8 | 11.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.376 | 22.181 | 21.984 | 0.0153 | 1.255 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.42 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 21.465 | 22.474 | 23.442 | 0.0246 | 1.065 | 0.945 | 0.710 | 2.558 | 1.2 | 10.4 | 0.65 | 3.76 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.676 | 22.223 | 17.687 | 0.0057 | 4.529 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.23 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.355 | 22.072 | 20.946 | 0.0113 | 1.828 | 0.922 | 1.219 | 1.187 | 1.7 | 12.6 |  | 0.05 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.344 | 22.060 | 20.882 | 0.0113 | 1.871 | 0.921 | 1.248 | 1.186 | 1.7 | 11.8 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 18.788 | 19.627 | 18.553 | 0.0141 | 2.276 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.44 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 18.723 | 19.633 | 19.060 | 0.0178 | 2.057 | 0.904 | 1.372 | 2.066 | 1.9 | 11.8 | 0.59 | 3.80 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.083 | 20.658 | 14.388 | 0.0059 | 6.378 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.25 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.944 | 19.725 | 17.860 | 0.0114 | 2.827 | 0.869 | 1.885 | 1.228 | 2.7 | 11.9 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.946 | 19.729 | 17.844 | 0.0112 | 2.849 | 0.867 | 1.899 | 1.225 | 2.7 | 11.2 |  | 0.06 |
| val2 | recovered | stable | base_stock | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.53 |
| val2 | recovered | stable | gated | 50/50 | 23.211 | 23.875 | 21.033 | 0.0141 | 2.594 | 0.923 | 1.729 | 1.666 | 1.3 | 11.1 | 0.04 | 3.25 |
| val2 | recovered | stable | order_up_to | 50/50 | 24.427 | 24.833 | 17.222 | 0.0065 | 6.326 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.23 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.193 | 23.824 | 20.891 | 0.0141 | 2.544 | 0.926 | 1.696 | 1.656 | 1.4 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.221 | 23.851 | 20.819 | 0.0139 | 2.633 | 0.919 | 1.755 | 1.639 | 1.4 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain | base_stock | 50/50 | 26.668 | 27.674 | 24.888 | 0.0195 | 4.100 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.41 |
| val2 | recovered | uncertain | gated | 50/50 | 26.540 | 27.813 | 28.109 | 0.0399 | 2.051 | 0.927 | 1.367 | 3.464 | 1.5 | 9.4 | 0.65 | 3.03 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 27.706 | 28.419 | 18.942 | 0.0081 | 9.425 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.24 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 26.832 | 27.741 | 23.242 | 0.0150 | 5.273 | 0.871 | 3.516 | 1.669 | 2.5 | 12.1 |  | 0.05 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 26.843 | 27.754 | 23.186 | 0.0149 | 5.340 | 0.866 | 3.560 | 1.666 | 2.5 | 11.1 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 26.760 | 27.808 | 26.642 | 0.0209 | 2.544 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.42 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 26.417 | 27.637 | 28.471 | 0.0382 | 1.655 | 0.937 | 1.103 | 3.418 | 1.2 | 9.5 | 0.62 | 3.67 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.143 | 27.815 | 21.195 | 0.0082 | 6.401 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.24 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 26.743 | 27.660 | 25.212 | 0.0158 | 3.262 | 0.913 | 2.174 | 1.818 | 1.8 | 12.2 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 26.719 | 27.633 | 25.160 | 0.0158 | 3.274 | 0.912 | 2.183 | 1.808 | 1.8 | 11.3 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.675 | 24.745 | 22.603 | 0.0206 | 3.672 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.44 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.365 | 24.606 | 24.106 | 0.0236 | 2.698 | 0.908 | 1.799 | 2.602 | 1.8 | 11.4 | 0.54 | 3.63 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 25.025 | 25.713 | 17.457 | 0.0083 | 8.105 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.24 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.852 | 24.839 | 21.623 | 0.0170 | 4.348 | 0.860 | 2.899 | 1.878 | 2.6 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.868 | 24.854 | 21.583 | 0.0170 | 4.398 | 0.857 | 2.932 | 1.873 | 2.6 | 10.5 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | +0.003 | [-0.000, +0.007] | [-0.000, +0.009] | 16 / 6 / 28 | 0.052 |
| final | observed | stable | periodic:1 | 50 | +0.012 | [+0.006, +0.018] | [+0.003, +0.022] | 39 / 10 / 1 | 0.0 |
| final | observed | stable | base_stock | 50 | +0.073 | [+0.055, +0.093] | [+0.046, +0.105] | 24 / 26 / 0 | 0.888 |
| final | observed | stable | order_up_to | 50 | -0.418 | [-0.499, -0.344] | [-0.545, -0.309] | 46 / 4 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | +0.101 | [-0.042, +0.262] | [-0.098, +0.374] | 28 / 18 / 4 | 0.184 |
| final | observed | uncertain | periodic:1 | 50 | +0.102 | [-0.038, +0.263] | [-0.090, +0.372] | 30 / 18 / 2 | 0.111 |
| final | observed | uncertain | base_stock | 50 | -0.049 | [-0.170, +0.084] | [-0.219, +0.165] | 39 / 11 / 0 | 0.0 |
| final | observed | uncertain | order_up_to | 50 | -0.167 | [-0.344, +0.046] | [-0.416, +0.175] | 34 / 16 / 0 | 0.015 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.270 | [-0.464, -0.088] | [-0.603, -0.040] | 30 / 18 / 2 | 0.111 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.268 | [-0.461, -0.086] | [-0.619, -0.038] | 31 / 18 / 1 | 0.085 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.466 | [-0.773, -0.185] | [-1.014, -0.128] | 35 / 15 / 0 | 0.007 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -0.692 | [-1.030, -0.405] | [-1.235, -0.315] | 39 / 11 / 0 | 0.0 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.049 | [-0.091, -0.008] | [-0.117, +0.009] | 34 / 13 / 3 | 0.003 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.047 | [-0.088, -0.009] | [-0.116, +0.009] | 36 / 13 / 1 | 0.001 |
| final | observed | uncertain_lead_only | base_stock | 50 | +0.013 | [-0.030, +0.056] | [-0.051, +0.080] | 36 / 14 / 0 | 0.003 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -0.468 | [-0.558, -0.380] | [-0.617, -0.341] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | +0.022 | [+0.006, +0.040] | [-0.000, +0.051] | 17 / 11 / 22 | 0.345 |
| final | recovered | stable | periodic:1 | 50 | +0.035 | [+0.019, +0.053] | [+0.013, +0.063] | 38 / 11 / 1 | 0.0 |
| final | recovered | stable | base_stock | 50 | +0.121 | [+0.082, +0.161] | [+0.065, +0.184] | 27 / 23 / 0 | 0.672 |
| final | recovered | stable | order_up_to | 50 | -0.545 | [-0.667, -0.431] | [-0.738, -0.383] | 44 / 6 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | +0.084 | [-0.026, +0.201] | [-0.069, +0.279] | 26 / 23 / 1 | 0.775 |
| final | recovered | uncertain | periodic:1 | 50 | +0.091 | [-0.016, +0.210] | [-0.063, +0.280] | 26 / 24 / 0 | 0.888 |
| final | recovered | uncertain | base_stock | 50 | -0.135 | [-0.231, -0.031] | [-0.279, +0.023] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain | order_up_to | 50 | -0.203 | [-0.343, -0.048] | [-0.405, +0.040] | 34 / 16 / 0 | 0.015 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.162 | [-0.369, +0.021] | [-0.514, +0.084] | 26 / 24 / 0 | 0.888 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.162 | [-0.371, +0.021] | [-0.519, +0.085] | 26 / 24 / 0 | 0.888 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.376 | [-0.718, -0.071] | [-0.946, +0.018] | 29 / 21 / 0 | 0.322 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -0.656 | [-1.002, -0.346] | [-1.262, -0.253] | 37 / 13 / 0 | 0.001 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.044 | [-0.073, -0.017] | [-0.092, -0.005] | 33 / 13 / 4 | 0.005 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.030 | [-0.054, -0.007] | [-0.070, +0.003] | 34 / 13 / 3 | 0.003 |
| final | recovered | uncertain_lead_only | base_stock | 50 | +0.062 | [+0.030, +0.096] | [+0.018, +0.119] | 31 / 19 / 0 | 0.119 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -0.562 | [-0.694, -0.430] | [-0.790, -0.379] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.007 | [-0.020, +0.005] | [-0.030, +0.009] | 4 / 15 / 31 | 0.019 |
| val1 | observed | stable | periodic:1 | 50 | +0.002 | [-0.013, +0.016] | [-0.022, +0.023] | 18 / 20 / 12 | 0.871 |
| val1 | observed | stable | base_stock | 50 | +0.096 | [+0.068, +0.123] | [+0.054, +0.138] | 14 / 36 / 0 | 0.003 |
| val1 | observed | stable | order_up_to | 50 | -1.015 | [-1.322, -0.739] | [-1.572, -0.676] | 49 / 1 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | -0.412 | [-0.891, +0.019] | [-1.242, +0.130] | 28 / 21 / 1 | 0.392 |
| val1 | observed | uncertain | periodic:1 | 50 | -0.402 | [-0.899, +0.023] | [-1.282, +0.123] | 28 / 22 / 0 | 0.48 |
| val1 | observed | uncertain | base_stock | 50 | -0.193 | [-0.518, +0.111] | [-0.742, +0.217] | 27 / 23 / 0 | 0.672 |
| val1 | observed | uncertain | order_up_to | 50 | -1.144 | [-1.958, -0.451] | [-2.569, -0.309] | 34 / 16 / 0 | 0.015 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.627 | [+0.314, +0.976] | [+0.202, +1.196] | 19 / 31 / 0 | 0.119 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.641 | [+0.319, +0.993] | [+0.207, +1.236] | 19 / 31 / 0 | 0.119 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.694 | [+0.363, +1.054] | [+0.232, +1.299] | 16 / 34 / 0 | 0.015 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | +0.148 | [-0.093, +0.389] | [-0.212, +0.533] | 27 / 23 / 0 | 0.672 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.100 | [-0.227, +0.039] | [-0.288, +0.131] | 35 / 15 / 0 | 0.007 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.094 | [-0.222, +0.052] | [-0.279, +0.133] | 35 / 15 / 0 | 0.007 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | +0.062 | [-0.079, +0.209] | [-0.138, +0.294] | 29 / 21 / 0 | 0.322 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -1.189 | [-1.656, -0.783] | [-1.970, -0.650] | 44 / 6 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | -0.001 | [-0.006, +0.005] | [-0.009, +0.008] | 4 / 8 / 38 | 0.388 |
| val1 | recovered | stable | periodic:1 | 50 | +0.003 | [-0.003, +0.009] | [-0.006, +0.013] | 24 / 13 / 13 | 0.099 |
| val1 | recovered | stable | base_stock | 50 | +0.142 | [+0.095, +0.194] | [+0.079, +0.232] | 11 / 39 / 0 | 0.0 |
| val1 | recovered | stable | order_up_to | 50 | -1.233 | [-1.634, -0.905] | [-1.916, -0.834] | 48 / 2 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | +0.751 | [+0.116, +1.462] | [-0.005, +2.073] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain | periodic:1 | 50 | +0.757 | [+0.119, +1.471] | [+0.000, +2.068] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain | base_stock | 50 | +1.003 | [+0.250, +1.840] | [+0.137, +2.510] | 21 / 29 / 0 | 0.322 |
| val1 | recovered | uncertain | order_up_to | 50 | -0.125 | [-0.540, +0.321] | [-0.700, +0.631] | 30 / 20 / 0 | 0.203 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +0.597 | [+0.358, +0.829] | [+0.253, +0.950] | 17 / 33 / 0 | 0.033 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.604 | [+0.382, +0.841] | [+0.274, +0.962] | 17 / 33 / 0 | 0.033 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +0.612 | [+0.386, +0.839] | [+0.283, +0.970] | 17 / 33 / 0 | 0.033 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | -0.095 | [-0.481, +0.266] | [-0.711, +0.418] | 26 / 24 / 0 | 0.888 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.133 | [-0.280, +0.020] | [-0.350, +0.114] | 32 / 18 / 0 | 0.065 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.126 | [-0.271, +0.031] | [-0.346, +0.129] | 32 / 18 / 0 | 0.065 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | +0.041 | [-0.108, +0.201] | [-0.182, +0.292] | 25 / 25 / 0 | 1.0 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -1.428 | [-1.865, -1.036] | [-2.184, -0.873] | 45 / 5 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | -0.000 | [-0.006, +0.005] | [-0.009, +0.008] | 4 / 9 / 37 | 0.267 |
| val2 | observed | stable | periodic:1 | 50 | +0.021 | [+0.011, +0.031] | [+0.007, +0.037] | 20 / 15 / 15 | 0.5 |
| val2 | observed | stable | base_stock | 50 | +0.103 | [+0.073, +0.133] | [+0.057, +0.151] | 15 / 35 / 0 | 0.007 |
| val2 | observed | stable | order_up_to | 50 | -1.184 | [-1.702, -0.707] | [-2.154, -0.643] | 49 / 1 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | +0.103 | [-0.097, +0.303] | [-0.219, +0.407] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain | periodic:1 | 50 | +0.113 | [-0.090, +0.313] | [-0.204, +0.424] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain | base_stock | 50 | +0.336 | [+0.064, +0.623] | [-0.060, +0.789] | 24 / 26 / 0 | 0.888 |
| val2 | observed | uncertain | order_up_to | 50 | -0.527 | [-0.875, -0.198] | [-1.104, -0.072] | 34 / 16 / 0 | 0.015 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.121 | [-0.115, +0.363] | [-0.250, +0.507] | 25 / 25 / 0 | 1.0 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.110 | [-0.139, +0.354] | [-0.274, +0.495] | 23 / 27 / 0 | 0.672 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.089 | [-0.140, +0.323] | [-0.274, +0.456] | 22 / 28 / 0 | 0.48 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | -0.211 | [-0.491, +0.078] | [-0.672, +0.225] | 34 / 16 / 0 | 0.015 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.223 | [-0.305, -0.144] | [-0.350, -0.107] | 31 / 19 / 0 | 0.119 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.221 | [-0.296, -0.146] | [-0.344, -0.110] | 32 / 18 / 0 | 0.065 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.065 | [-0.144, +0.014] | [-0.187, +0.064] | 27 / 23 / 0 | 0.672 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -1.360 | [-1.927, -0.874] | [-2.336, -0.753] | 47 / 3 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | -0.010 | [-0.018, -0.002] | [-0.023, +0.002] | 10 / 10 / 30 | 1.0 |
| val2 | recovered | stable | periodic:1 | 50 | +0.019 | [+0.004, +0.033] | [-0.003, +0.041] | 22 / 19 / 9 | 0.755 |
| val2 | recovered | stable | base_stock | 50 | +0.159 | [+0.102, +0.222] | [+0.077, +0.263] | 17 / 33 / 0 | 0.033 |
| val2 | recovered | stable | order_up_to | 50 | -1.215 | [-1.591, -0.885] | [-1.862, -0.820] | 50 / 0 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | -0.303 | [-0.919, +0.227] | [-1.354, +0.371] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain | periodic:1 | 50 | -0.292 | [-0.905, +0.256] | [-1.363, +0.402] | 27 / 23 / 0 | 0.672 |
| val2 | recovered | uncertain | base_stock | 50 | -0.128 | [-0.575, +0.270] | [-0.908, +0.389] | 22 / 28 / 0 | 0.48 |
| val2 | recovered | uncertain | order_up_to | 50 | -1.165 | [-2.244, -0.244] | [-3.042, -0.068] | 35 / 15 / 0 | 0.007 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | -0.303 | [-1.095, +0.434] | [-1.779, +0.574] | 25 / 25 / 0 | 1.0 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | -0.327 | [-1.211, +0.423] | [-1.838, +0.567] | 25 / 25 / 0 | 1.0 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | -0.343 | [-1.171, +0.389] | [-1.840, +0.522] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | -0.726 | [-1.613, +0.083] | [-2.292, +0.252] | 28 / 22 / 0 | 0.48 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.503 | [-0.779, -0.259] | [-0.982, -0.180] | 33 / 17 / 0 | 0.033 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.486 | [-0.744, -0.243] | [-0.956, -0.167] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.309 | [-0.523, -0.117] | [-0.661, -0.051] | 29 / 21 / 0 | 0.322 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -1.660 | [-2.293, -1.113] | [-2.718, -0.971] | 47 / 3 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | +0.0106 | [+0.0000, +0.0289] | 0 / 2 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | -0.0172 | [-0.0566, +0.0266] | 14 / 4 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | -0.0023 | [-0.0064, +0.0000] | 0 / 2 |
| final | observed | stable | periodic:1 | shortage | 50 | +0.0412 | [+0.0163, +0.0708] | 0 / 9 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | -0.0243 | [-0.0640, +0.0180] | 23 / 8 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0070 | [-0.0124, -0.0027] | 0 / 9 |
| final | observed | stable | base_stock | shortage | 50 | +0.2328 | [+0.1532, +0.3222] | 0 / 26 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | -0.2636 | [-0.4104, -0.1673] | 48 / 2 |
| final | observed | stable | base_stock | service_unit_fill | 50 | -0.0216 | [-0.0296, -0.0146] | 0 / 26 |
| final | observed | stable | order_up_to | shortage | 50 | -1.2755 | [-1.6400, -0.9496] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +0.6810 | [+0.4136, +1.1348] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1220 | [+0.0977, +0.1452] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.1281 | [-0.3272, +0.0594] | 19 / 8 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.6530 | [+0.1741, +1.4890] | 5 / 40 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0133 | [-0.0045, +0.0299] | 19 / 8 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.1225 | [-0.3160, +0.0569] | 19 / 8 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.6510 | [+0.1756, +1.5113] | 7 / 40 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0125 | [-0.0054, +0.0288] | 19 / 8 |
| final | observed | uncertain | base_stock | shortage | 50 | +0.2228 | [+0.0032, +0.4628] | 9 / 17 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.3525 | [-0.0197, +1.0016] | 29 / 21 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | -0.0168 | [-0.0377, -0.0002] | 9 / 17 |
| final | observed | uncertain | order_up_to | shortage | 50 | -1.3055 | [-1.6914, -0.9499] | 41 / 0 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.1049 | [+0.4635, +2.2858] | 1 / 49 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1296 | [+0.1029, +0.1564] | 41 / 0 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.1716 | [-0.3538, -0.0196] | 17 / 7 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.7682 | [+0.2461, +1.6869] | 4 / 44 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0123 | [-0.0005, +0.0257] | 17 / 7 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.1650 | [-0.3471, -0.0137] | 17 / 7 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.7656 | [+0.2380, +1.6872] | 5 / 44 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0115 | [-0.0011, +0.0254] | 17 / 7 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | +0.1197 | [-0.0556, +0.2921] | 6 / 14 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.4221 | [-0.0064, +1.1893] | 25 / 25 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0086 | [-0.0200, +0.0028] | 6 / 14 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.3459 | [-1.7805, -0.9785] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.3192 | [+0.5888, +2.6148] | 1 / 49 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1263 | [+0.0992, +0.1557] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.1467 | [-0.3454, +0.0293] | 15 / 8 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.1107 | [+0.0526, +0.1884] | 13 / 32 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0129 | [-0.0012, +0.0271] | 15 / 8 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.1374 | [-0.3441, +0.0354] | 15 / 8 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.1071 | [+0.0480, +0.1852] | 15 / 32 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0122 | [-0.0015, +0.0265] | 15 / 8 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | +0.0725 | [-0.1176, +0.2771] | 10 / 14 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | -0.0909 | [-0.2271, +0.0227] | 34 / 16 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | -0.0031 | [-0.0158, +0.0094] | 10 / 14 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -1.4222 | [-1.8233, -1.0251] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.6386 | [+0.4144, +1.0104] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1315 | [+0.1058, +0.1571] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | +0.0549 | [-0.0052, +0.1331] | 1 / 6 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | -0.0735 | [-0.1865, +0.0029] | 16 / 6 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | -0.0046 | [-0.0103, -0.0002] | 1 / 6 |
| final | recovered | stable | periodic:1 | shortage | 50 | +0.0992 | [+0.0376, +0.1743] | 0 / 11 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | -0.0811 | [-0.1947, -0.0015] | 28 / 6 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0083 | [-0.0146, -0.0033] | 0 / 11 |
| final | recovered | stable | base_stock | shortage | 50 | +0.3666 | [+0.2032, +0.5704] | 0 / 23 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | -0.4167 | [-0.6840, -0.2477] | 49 / 1 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | -0.0244 | [-0.0349, -0.0148] | 0 / 23 |
| final | recovered | stable | order_up_to | shortage | 50 | -1.6741 | [-2.2378, -1.1958] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +0.9266 | [+0.5872, +1.4493] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1309 | [+0.1119, +0.1499] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.0286 | [-0.1754, +0.1559] | 18 / 7 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.6457 | [+0.1787, +1.4874] | 9 / 38 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0067 | [-0.0096, +0.0207] | 18 / 7 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.0104 | [-0.1580, +0.1620] | 17 / 7 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.6389 | [+0.1723, +1.4891] | 12 / 36 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0061 | [-0.0100, +0.0200] | 17 / 7 |
| final | recovered | uncertain | base_stock | shortage | 50 | +0.2917 | [+0.0825, +0.5807] | 5 / 16 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.2072 | [-0.1482, +0.8274] | 32 / 18 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | -0.0190 | [-0.0392, -0.0029] | 5 / 16 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -1.5725 | [-2.0866, -1.1364] | 42 / 0 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +1.3372 | [+0.6149, +2.6399] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1312 | [+0.1046, +0.1589] | 42 / 0 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.0148 | [-0.1978, +0.2105] | 13 / 8 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.4565 | [+0.2090, +0.7732] | 9 / 41 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0070 | [-0.0066, +0.0211] | 13 / 8 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0072 | [-0.1848, +0.2054] | 13 / 8 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.4532 | [+0.2083, +0.7821] | 9 / 41 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0057 | [-0.0070, +0.0183] | 13 / 8 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | +0.2990 | [+0.0772, +0.5975] | 4 / 15 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | -0.0321 | [-0.2130, +0.1529] | 31 / 19 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0156 | [-0.0290, -0.0025] | 4 / 15 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -1.5517 | [-2.0936, -1.1090] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.2863 | [+0.7456, +2.1642] | 0 / 50 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1288 | [+0.1007, +0.1586] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.1397 | [-0.2783, -0.0169] | 12 / 7 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.0805 | [-0.0205, +0.1826] | 13 / 29 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0056 | [-0.0061, +0.0154] | 12 / 7 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.0950 | [-0.2031, +0.0057] | 12 / 7 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.0783 | [-0.0167, +0.1811] | 15 / 29 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0033 | [-0.0072, +0.0124] | 12 / 7 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | +0.2041 | [+0.0762, +0.3729] | 6 / 18 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | -0.2009 | [-0.4170, -0.0602] | 42 / 8 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | -0.0151 | [-0.0260, -0.0060] | 6 / 18 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -1.7308 | [-2.3768, -1.1847] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.8774 | [+0.5678, +1.3570] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1326 | [+0.1074, +0.1579] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.0365 | [-0.1029, +0.0075] | 5 / 2 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0430 | [+0.0178, +0.0725] | 1 / 17 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0031 | [+0.0000, +0.0073] | 5 / 2 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.0096 | [-0.0776, +0.0381] | 3 / 8 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0304 | [+0.0053, +0.0601] | 19 / 18 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0013 | [-0.0023, +0.0058] | 3 / 8 |
| val1 | observed | stable | base_stock | shortage | 50 | +0.3301 | [+0.2284, +0.4388] | 2 / 38 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | -0.2123 | [-0.3586, -0.1224] | 46 / 4 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | -0.0163 | [-0.0216, -0.0108] | 2 / 38 |
| val1 | observed | stable | order_up_to | shortage | 50 | -3.2126 | [-4.8392, -2.2275] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.6943 | [+0.4749, +1.0231] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1493 | [+0.1316, +0.1689] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -2.0150 | [-3.8760, -0.9161] | 41 / 1 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.3038 | [+0.7753, +2.2172] | 0 / 49 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0587 | [+0.0449, +0.0729] | 41 / 1 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -1.9922 | [-3.7953, -0.9038] | 41 / 1 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3004 | [+0.7636, +2.1934] | 0 / 49 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0577 | [+0.0443, +0.0712] | 41 / 1 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.0062 | [-2.0640, -0.3390] | 31 / 10 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.9854 | [+0.5405, +1.6915] | 5 / 45 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0253 | [+0.0140, +0.0367] | 31 / 10 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -5.0927 | [-8.5189, -3.0140] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.8491 | [+1.1444, +3.0485] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1924 | [+0.1731, +0.2125] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.6140 | [-0.8527, -0.3889] | 32 / 4 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.6764 | [+0.9157, +2.9041] | 0 / 49 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0293 | [+0.0180, +0.0416] | 32 / 4 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.5654 | [-0.7959, -0.3403] | 30 / 4 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.6741 | [+0.9010, +2.9418] | 0 / 49 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0287 | [+0.0174, +0.0409] | 30 / 4 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1113 | [-0.2868, +0.0495] | 17 / 14 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.2701 | [+0.6368, +2.2595] | 5 / 45 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0050 | [-0.0038, +0.0150] | 17 / 14 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.1720 | [-4.5914, -2.2327] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.2842 | [+1.3438, +3.8450] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1486 | [+0.1262, +0.1717] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.8214 | [-1.1515, -0.5377] | 38 / 1 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7817 | [+0.5035, +1.1062] | 2 / 48 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0469 | [+0.0299, +0.0684] | 38 / 1 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.8019 | [-1.1285, -0.5123] | 38 / 1 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7776 | [+0.5073, +1.1070] | 2 / 48 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0456 | [+0.0293, +0.0662] | 38 / 1 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.2439 | [-0.5889, +0.1400] | 28 / 14 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5452 | [+0.3321, +0.7841] | 8 / 42 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0217 | [+0.0045, +0.0445] | 28 / 14 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.2410 | [-6.4742, -2.7871] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.3876 | [+0.9397, +2.0048] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1833 | [+0.1659, +0.2013] | 50 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 50 | -0.0024 | [-0.0285, +0.0225] | 3 / 3 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0178 | [+0.0005, +0.0410] | 4 / 8 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0013 | [-0.0006, +0.0039] | 3 / 3 |
| val1 | recovered | stable | periodic:1 | shortage | 50 | +0.0102 | [-0.0185, +0.0369] | 3 / 9 |
| val1 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0002 | [-0.0187, +0.0246] | 29 / 8 |
| val1 | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0003 | [-0.0019, +0.0032] | 3 / 9 |
| val1 | recovered | stable | base_stock | shortage | 50 | +0.4803 | [+0.3000, +0.7399] | 1 / 39 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 50 | -0.3218 | [-0.4668, -0.2266] | 48 / 2 |
| val1 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0175 | [-0.0225, -0.0121] | 1 / 39 |
| val1 | recovered | stable | order_up_to | shortage | 50 | -3.8864 | [-5.8101, -2.7108] | 50 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 50 | +0.9040 | [+0.6650, +1.3022] | 0 / 50 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1559 | [+0.1370, +0.1766] | 50 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -2.3880 | [-4.3831, -1.0535] | 39 / 1 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +2.2472 | [+0.9724, +4.4877] | 2 / 47 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0569 | [+0.0404, +0.0736] | 39 / 1 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -2.3589 | [-4.4928, -1.0536] | 39 / 1 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +2.2448 | [+0.9708, +4.5257] | 3 / 46 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0554 | [+0.0396, +0.0720] | 39 / 1 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -1.1842 | [-2.3445, -0.3700] | 29 / 6 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.8243 | [+0.6179, +3.8961] | 8 / 42 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0243 | [+0.0110, +0.0376] | 29 / 6 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -6.1323 | [-10.0519, -3.6787] | 49 / 0 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +3.0212 | [+1.5652, +5.6449] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2005 | [+0.1777, +0.2254] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.6744 | [-1.0424, -0.3433] | 30 / 7 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +2.0748 | [+1.1875, +3.5589] | 1 / 48 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0305 | [+0.0174, +0.0447] | 30 / 7 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.6639 | [-1.0404, -0.3320] | 30 / 7 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +2.0642 | [+1.1701, +3.5056] | 1 / 48 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0299 | [+0.0160, +0.0444] | 30 / 7 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.1485 | [-0.4709, +0.1555] | 17 / 11 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.5528 | [+0.8106, +2.7856] | 4 / 46 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0058 | [-0.0070, +0.0175] | 17 / 11 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -3.9669 | [-5.8910, -2.7171] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.9375 | [+1.8540, +4.7201] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1557 | [+0.1339, +0.1786] | 49 / 0 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.9279 | [-1.3567, -0.5672] | 34 / 2 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +1.1328 | [+0.5588, +2.1011] | 1 / 49 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0437 | [+0.0272, +0.0653] | 34 / 2 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.9058 | [-1.3214, -0.5458] | 34 / 2 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +1.1270 | [+0.5524, +2.1213] | 1 / 49 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0424 | [+0.0260, +0.0634] | 34 / 2 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.3196 | [-0.7595, +0.1355] | 20 / 12 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.8020 | [+0.3006, +1.6541] | 10 / 40 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0205 | [+0.0041, +0.0422] | 20 / 12 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -4.9387 | [-7.0807, -3.4802] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +2.0005 | [+1.1884, +3.3695] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1923 | [+0.1702, +0.2159] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.0137 | [-0.0356, +0.0026] | 3 / 1 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0141 | [-0.0031, +0.0388] | 2 / 8 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0009 | [-0.0001, +0.0022] | 3 / 1 |
| val2 | observed | stable | periodic:1 | shortage | 50 | +0.0593 | [+0.0156, +0.1107] | 3 / 11 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0107 | [-0.0070, +0.0348] | 20 / 12 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0042 | [-0.0079, -0.0009] | 3 / 11 |
| val2 | observed | stable | base_stock | shortage | 50 | +0.3704 | [+0.2591, +0.4919] | 1 / 36 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | -0.2371 | [-0.3793, -0.1504] | 49 / 1 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | -0.0207 | [-0.0279, -0.0145] | 1 / 36 |
| val2 | observed | stable | order_up_to | shortage | 50 | -3.6620 | [-6.5020, -2.0757] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.6463 | [+0.4912, +0.8724] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1451 | [+0.1260, +0.1662] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -1.4411 | [-2.4836, -0.6956] | 38 / 6 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.3226 | [+0.8915, +1.8790] | 0 / 50 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0424 | [+0.0288, +0.0566] | 38 / 6 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -1.4078 | [-2.4292, -0.6441] | 38 / 6 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.3221 | [+0.8984, +1.8707] | 0 / 50 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0403 | [+0.0267, +0.0539] | 38 / 6 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -0.3629 | [-0.8987, +0.0641] | 24 / 15 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.0011 | [+0.6582, +1.4021] | 5 / 45 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0111 | [-0.0017, +0.0249] | 24 / 15 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -4.7054 | [-7.9733, -2.7141] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.7959 | [+1.2961, +2.4560] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1754 | [+0.1589, +0.1932] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.8065 | [-1.5767, -0.2326] | 26 / 5 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.3714 | [+0.8394, +2.0974] | 1 / 49 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0243 | [+0.0116, +0.0375] | 26 / 5 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.7634 | [-1.4794, -0.2239] | 25 / 6 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.3707 | [+0.8549, +2.1149] | 2 / 48 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0227 | [+0.0110, +0.0361] | 25 / 6 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1900 | [-0.5312, +0.0973] | 17 / 13 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.9864 | [+0.5555, +1.5623] | 9 / 41 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0051 | [-0.0051, +0.0158] | 17 / 13 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.4640 | [-6.2283, -1.8719] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.9458 | [+1.3437, +2.7585] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1348 | [+0.1127, +0.1573] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.7918 | [-1.1510, -0.4948] | 33 / 3 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.8411 | [+0.3877, +1.6196] | 2 / 47 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0371 | [+0.0220, +0.0572] | 33 / 3 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.7699 | [-1.1254, -0.4667] | 32 / 4 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.8379 | [+0.3875, +1.6099] | 3 / 47 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0351 | [+0.0205, +0.0537] | 32 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.2190 | [-0.5576, +0.1254] | 23 / 13 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.6095 | [+0.2138, +1.2718] | 12 / 38 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0155 | [+0.0007, +0.0345] | 23 / 13 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.3205 | [-7.1335, -2.5516] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.4253 | [+0.8705, +2.3809] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1661 | [+0.1470, +0.1867] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.0389 | [-0.0764, -0.0093] | 7 / 1 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0272 | [+0.0071, +0.0527] | 5 / 13 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0032 | [+0.0005, +0.0070] | 7 / 1 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | +0.0498 | [-0.0084, +0.1104] | 6 / 11 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0094 | [-0.0135, +0.0372] | 25 / 13 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0033 | [-0.0076, +0.0007] | 6 / 11 |
| val2 | recovered | stable | base_stock | shortage | 50 | +0.5776 | [+0.3633, +0.8701] | 1 / 35 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | -0.3178 | [-0.4578, -0.2233] | 49 / 1 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0239 | [-0.0315, -0.0168] | 1 / 35 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -3.7323 | [-5.7080, -2.5207] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +0.9860 | [+0.7045, +1.4331] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1481 | [+0.1304, +0.1670] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -3.2898 | [-7.3468, -1.0651] | 38 / 3 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.7980 | [+0.9535, +3.2437] | 1 / 49 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0604 | [+0.0423, +0.0806] | 38 / 3 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -3.2229 | [-7.2130, -0.9666] | 37 / 4 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.7950 | [+0.9583, +3.2943] | 1 / 49 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0563 | [+0.0385, +0.0769] | 37 / 4 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -2.0490 | [-4.8541, -0.3876] | 23 / 13 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.3612 | [+0.5897, +2.5865] | 5 / 45 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0286 | [+0.0130, +0.0464] | 23 / 13 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -7.3746 | [-13.9384, -3.6038] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.5433 | [+1.5749, +4.1936] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.2038 | [+0.1783, +0.2316] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -1.6190 | [-3.9880, -0.3014] | 29 / 5 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.6106 | [+0.9486, +2.5872] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0250 | [+0.0102, +0.0380] | 29 / 5 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -1.6067 | [-3.9616, -0.3004] | 29 / 5 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.6003 | [+0.9379, +2.6369] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0243 | [+0.0095, +0.0376] | 29 / 5 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.8892 | [-2.6841, +0.1807] | 20 / 14 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.0978 | [+0.5612, +1.8456] | 9 / 41 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0023 | [-0.0109, +0.0147] | 20 / 14 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -4.7461 | [-8.6522, -2.4974] | 48 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.4839 | [+1.6523, +3.7769] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1493 | [+0.1279, +0.1709] | 48 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.7000 | [-3.0966, -0.8024] | 33 / 1 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.7284 | [+0.4405, +1.1714] | 1 / 49 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0515 | [+0.0317, +0.0763] | 33 / 1 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.6506 | [-3.0323, -0.7367] | 30 / 4 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.7235 | [+0.4348, +1.1885] | 1 / 49 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0480 | [+0.0290, +0.0718] | 30 / 4 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.9742 | [-2.0138, -0.2974] | 25 / 12 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.4144 | [+0.1885, +0.7323] | 13 / 37 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0251 | [+0.0070, +0.0479] | 25 / 12 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -5.4074 | [-8.4474, -3.3623] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.6490 | [+1.1263, +2.5038] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1910 | [+0.1662, +0.2186] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1185 of 1200 (7567 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/recovered/uncertain store 514 product 267: ZAAD minus base_stock = +34.388 (fill 0.923 vs 0.881, inventory 71.48 vs 22.81, retained incumbent on 2 reviews)
- val1/observed/uncertain_fill_only store 514 product 267: ZAAD minus base_stock = +12.269 (fill 0.922 vs 0.922, inventory 43.08 vs 20.54, retained incumbent on 3 reviews)
- val2/observed/uncertain store 514 product 267: ZAAD minus base_stock = +8.180 (fill 0.866 vs 0.877, inventory 18.98 vs 11.28, retained incumbent on 3 reviews)
- final/observed/uncertain store 514 product 267: ZAAD minus order_up_to = +6.063 (fill 0.898 vs 0.898, inventory 45.36 vs 17.53, retained incumbent on 4 reviews)
- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus order_up_to = +5.148 (fill 0.713 vs 0.705, inventory 4.05 vs 1.27, retained incumbent on 12 reviews)
- val2/observed/uncertain_fill_only store 102 product 467: ZAAD minus base_stock = +5.052 (fill 0.950 vs 0.991, inventory 4.63 vs 3.79, retained incumbent on 8 reviews)
- val1/observed/uncertain_fill_only store 712 product 836: ZAAD minus base_stock = +4.851 (fill 0.861 vs 0.940, inventory 3.65 vs 2.38, retained incumbent on 4 reviews)
- val1/observed/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +4.675 (fill 0.911 vs 0.883, inventory 5.45 vs 1.08, retained incumbent on 3 reviews)
- val2/recovered/uncertain store 855 product 647: ZAAD minus reorder_point = +4.527 (fill 0.879 vs 0.878, inventory 5.06 vs 2.86, retained incumbent on 11 reviews)
- val1/recovered/uncertain_fill_only store 712 product 836: ZAAD minus periodic:1 = +4.317 (fill 0.866 vs 0.924, inventory 3.53 vs 1.91, retained incumbent on 3 reviews)
