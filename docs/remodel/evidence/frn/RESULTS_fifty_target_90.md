# FreshRetailNet pilot results: stage `fifty_target_90`

Commit `ae1b73c26a7e37b1483f569c2bf24e6af79179e7`, declaration `e2753f99642d`, selection `497bf5a8741a`; 6000 runs, 6000 complete, 0 not complete; wall 3677 s, peak RSS 221 MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; none is a realized saving.

## Policy table (mean over completed series)

| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | base_stock | 50/50 | 10.208 | 10.847 | 10.564 | 0.0055 | 0.369 | 0.980 | 0.246 | 1.597 | 0.5 | 6.6 |  | 0.15 |
| final | observed | stable | gated | 50/50 | 10.278 | 10.548 | 8.548 | 0.0046 | 0.594 | 0.960 | 0.396 | 1.337 | 0.8 | 5.2 | 0.09 | 0.58 |
| final | observed | stable | order_up_to | 50/50 | 10.699 | 11.052 | 8.089 | 0.0023 | 1.877 | 0.836 | 1.251 | 0.652 | 2.6 | 6.0 |  | 0.10 |
| final | observed | stable | periodic:1 | 50/50 | 10.269 | 10.844 | 10.106 | 0.0047 | 0.560 | 0.965 | 0.374 | 1.358 | 0.8 | 6.6 |  | 0.02 |
| final | observed | stable | reorder_point | 50/50 | 10.278 | 10.606 | 8.845 | 0.0047 | 0.591 | 0.960 | 0.394 | 1.351 | 0.8 | 5.4 |  | 0.02 |
| final | observed | uncertain | base_stock | 50/50 | 12.342 | 13.358 | 12.809 | 0.0053 | 2.166 | 0.888 | 1.444 | 1.521 | 1.4 | 6.3 |  | 0.12 |
| final | observed | uncertain | gated | 50/50 | 12.185 | 12.810 | 10.505 | 0.0062 | 2.359 | 0.868 | 1.573 | 1.787 | 1.6 | 3.8 | 0.37 | 0.67 |
| final | observed | uncertain | order_up_to | 50/50 | 12.460 | 13.150 | 9.724 | 0.0027 | 3.695 | 0.741 | 2.463 | 0.769 | 2.9 | 6.1 |  | 0.10 |
| final | observed | uncertain | periodic:1 | 50/50 | 12.190 | 12.877 | 10.651 | 0.0042 | 2.512 | 0.858 | 1.674 | 1.223 | 1.7 | 5.5 |  | 0.02 |
| final | observed | uncertain | reorder_point | 50/50 | 12.191 | 12.878 | 10.642 | 0.0042 | 2.517 | 0.857 | 1.678 | 1.221 | 1.7 | 5.3 |  | 0.03 |
| final | observed | uncertain_fill_only | base_stock | 50/50 | 11.704 | 12.703 | 13.134 | 0.0064 | 1.142 | 0.951 | 0.761 | 1.859 | 1.0 | 6.4 |  | 0.12 |
| final | observed | uncertain_fill_only | gated | 50/50 | 11.297 | 11.918 | 10.668 | 0.0076 | 1.327 | 0.937 | 0.884 | 2.205 | 1.1 | 4.0 | 0.42 | 0.84 |
| final | observed | uncertain_fill_only | order_up_to | 50/50 | 11.929 | 12.589 | 10.129 | 0.0033 | 2.608 | 0.816 | 1.738 | 0.962 | 2.5 | 6.3 |  | 0.10 |
| final | observed | uncertain_fill_only | periodic:1 | 50/50 | 11.505 | 12.145 | 10.814 | 0.0052 | 1.427 | 0.931 | 0.951 | 1.516 | 1.2 | 5.6 |  | 0.02 |
| final | observed | uncertain_fill_only | reorder_point | 50/50 | 11.507 | 12.147 | 10.805 | 0.0052 | 1.433 | 0.930 | 0.955 | 1.513 | 1.2 | 5.4 |  | 0.03 |
| final | observed | uncertain_lead_only | base_stock | 50/50 | 10.884 | 11.936 | 11.336 | 0.0050 | 2.373 | 0.896 | 1.582 | 1.451 | 1.3 | 6.3 |  | 0.11 |
| final | observed | uncertain_lead_only | gated | 50/50 | 10.897 | 11.476 | 8.878 | 0.0048 | 2.440 | 0.892 | 1.627 | 1.389 | 1.4 | 4.2 | 0.38 | 0.79 |
| final | observed | uncertain_lead_only | order_up_to | 50/50 | 11.365 | 12.079 | 8.578 | 0.0025 | 3.868 | 0.762 | 2.578 | 0.722 | 2.9 | 6.2 |  | 0.10 |
| final | observed | uncertain_lead_only | periodic:1 | 50/50 | 10.943 | 11.678 | 9.558 | 0.0043 | 2.583 | 0.881 | 1.722 | 1.253 | 1.5 | 5.4 |  | 0.02 |
| final | observed | uncertain_lead_only | reorder_point | 50/50 | 10.945 | 11.679 | 9.541 | 0.0043 | 2.592 | 0.881 | 1.728 | 1.249 | 1.5 | 5.1 |  | 0.02 |
| final | recovered | stable | base_stock | 50/50 | 11.358 | 12.144 | 11.939 | 0.0076 | 0.310 | 0.975 | 0.207 | 2.213 | 0.5 | 6.6 |  | 0.14 |
| final | recovered | stable | gated | 50/50 | 11.447 | 11.772 | 9.427 | 0.0064 | 0.592 | 0.959 | 0.394 | 1.845 | 0.7 | 5.0 | 0.12 | 0.57 |
| final | recovered | stable | order_up_to | 50/50 | 12.024 | 12.432 | 8.640 | 0.0030 | 2.350 | 0.819 | 1.567 | 0.870 | 2.3 | 6.0 |  | 0.09 |
| final | recovered | stable | periodic:1 | 50/50 | 11.444 | 12.145 | 11.323 | 0.0065 | 0.577 | 0.959 | 0.385 | 1.877 | 0.7 | 6.6 |  | 0.03 |
| final | recovered | stable | reorder_point | 50/50 | 11.457 | 11.887 | 9.931 | 0.0065 | 0.621 | 0.955 | 0.414 | 1.870 | 0.7 | 5.3 |  | 0.02 |
| final | recovered | uncertain | base_stock | 50/50 | 13.746 | 14.957 | 14.958 | 0.0069 | 1.855 | 0.896 | 1.237 | 1.994 | 1.3 | 6.2 |  | 0.12 |
| final | recovered | uncertain | gated | 50/50 | 13.641 | 14.410 | 12.409 | 0.0075 | 2.117 | 0.877 | 1.412 | 2.158 | 1.4 | 3.8 | 0.40 | 0.66 |
| final | recovered | uncertain | order_up_to | 50/50 | 13.814 | 14.586 | 10.883 | 0.0030 | 3.719 | 0.746 | 2.479 | 0.864 | 2.7 | 6.1 |  | 0.09 |
| final | recovered | uncertain | periodic:1 | 50/50 | 13.520 | 14.349 | 12.476 | 0.0054 | 2.157 | 0.871 | 1.438 | 1.562 | 1.5 | 5.5 |  | 0.02 |
| final | recovered | uncertain | reorder_point | 50/50 | 13.528 | 14.358 | 12.469 | 0.0054 | 2.175 | 0.871 | 1.450 | 1.556 | 1.5 | 5.1 |  | 0.03 |
| final | recovered | uncertain_fill_only | base_stock | 50/50 | 12.878 | 14.085 | 15.203 | 0.0085 | 0.730 | 0.959 | 0.486 | 2.468 | 0.8 | 6.2 |  | 0.12 |
| final | recovered | uncertain_fill_only | gated | 50/50 | 12.600 | 13.326 | 12.375 | 0.0100 | 0.942 | 0.943 | 0.628 | 2.891 | 1.0 | 3.8 | 0.42 | 0.81 |
| final | recovered | uncertain_fill_only | order_up_to | 50/50 | 13.158 | 13.908 | 11.255 | 0.0040 | 2.580 | 0.815 | 1.720 | 1.150 | 2.5 | 6.2 |  | 0.10 |
| final | recovered | uncertain_fill_only | periodic:1 | 50/50 | 12.664 | 13.465 | 12.605 | 0.0068 | 1.036 | 0.938 | 0.691 | 1.983 | 1.2 | 5.4 |  | 0.02 |
| final | recovered | uncertain_fill_only | reorder_point | 50/50 | 12.665 | 13.465 | 12.597 | 0.0068 | 1.043 | 0.937 | 0.696 | 1.980 | 1.2 | 5.1 |  | 0.03 |
| final | recovered | uncertain_lead_only | base_stock | 50/50 | 11.907 | 13.171 | 13.295 | 0.0067 | 1.931 | 0.910 | 1.287 | 1.940 | 1.2 | 6.2 |  | 0.11 |
| final | recovered | uncertain_lead_only | gated | 50/50 | 11.962 | 12.578 | 9.888 | 0.0060 | 2.121 | 0.900 | 1.414 | 1.744 | 1.3 | 3.9 | 0.39 | 0.75 |
| final | recovered | uncertain_lead_only | order_up_to | 50/50 | 12.531 | 13.337 | 9.627 | 0.0030 | 3.866 | 0.763 | 2.577 | 0.861 | 2.8 | 6.1 |  | 0.10 |
| final | recovered | uncertain_lead_only | periodic:1 | 50/50 | 11.999 | 12.896 | 11.226 | 0.0057 | 2.230 | 0.892 | 1.487 | 1.660 | 1.4 | 5.3 |  | 0.02 |
| final | recovered | uncertain_lead_only | reorder_point | 50/50 | 12.013 | 12.910 | 11.194 | 0.0057 | 2.275 | 0.889 | 1.516 | 1.658 | 1.4 | 4.8 |  | 0.02 |
| val1 | observed | stable | base_stock | 50/50 | 18.241 | 18.728 | 17.937 | 0.0125 | 0.717 | 0.957 | 0.478 | 1.369 | 1.2 | 12.5 |  | 0.55 |
| val1 | observed | stable | gated | 50/50 | 18.328 | 18.766 | 17.481 | 0.0109 | 1.020 | 0.942 | 0.680 | 1.169 | 1.7 | 11.3 | 0.08 | 3.44 |
| val1 | observed | stable | order_up_to | 50/50 | 19.352 | 19.639 | 14.512 | 0.0047 | 4.260 | 0.792 | 2.840 | 0.462 | 5.5 | 11.9 |  | 0.22 |
| val1 | observed | stable | periodic:1 | 50/50 | 18.335 | 18.774 | 17.454 | 0.0104 | 1.057 | 0.940 | 0.705 | 1.126 | 1.7 | 12.5 |  | 0.04 |
| val1 | observed | stable | reorder_point | 50/50 | 18.344 | 18.782 | 17.433 | 0.0103 | 1.084 | 0.938 | 0.723 | 1.114 | 1.8 | 11.3 |  | 0.04 |
| val1 | observed | uncertain | base_stock | 50/50 | 21.214 | 21.993 | 19.912 | 0.0144 | 3.244 | 0.894 | 2.163 | 1.558 | 2.5 | 11.8 |  | 0.42 |
| val1 | observed | uncertain | gated | 50/50 | 21.018 | 22.084 | 22.256 | 0.0271 | 2.162 | 0.921 | 1.441 | 2.792 | 1.8 | 9.6 | 0.56 | 2.90 |
| val1 | observed | uncertain | order_up_to | 50/50 | 22.165 | 22.764 | 15.839 | 0.0061 | 7.330 | 0.727 | 4.887 | 0.694 | 5.5 | 11.5 |  | 0.23 |
| val1 | observed | uncertain | periodic:1 | 50/50 | 21.423 | 22.139 | 18.804 | 0.0111 | 4.230 | 0.862 | 2.820 | 1.243 | 3.2 | 12.2 |  | 0.04 |
| val1 | observed | uncertain | reorder_point | 50/50 | 21.433 | 22.149 | 18.791 | 0.0111 | 4.253 | 0.861 | 2.835 | 1.240 | 3.2 | 11.5 |  | 0.04 |
| val1 | observed | uncertain_fill_only | base_stock | 50/50 | 20.705 | 21.519 | 20.968 | 0.0171 | 1.839 | 0.928 | 1.226 | 1.723 | 1.7 | 11.9 |  | 0.42 |
| val1 | observed | uncertain_fill_only | gated | 50/50 | 21.134 | 22.070 | 22.310 | 0.0351 | 1.713 | 0.935 | 1.142 | 2.894 | 1.4 | 8.9 | 0.59 | 3.44 |
| val1 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.251 | 21.819 | 17.195 | 0.0073 | 4.899 | 0.785 | 3.266 | 0.709 | 4.8 | 11.6 |  | 0.22 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50/50 | 20.759 | 21.486 | 20.125 | 0.0133 | 2.293 | 0.905 | 1.529 | 1.319 | 2.3 | 12.3 |  | 0.04 |
| val1 | observed | uncertain_fill_only | reorder_point | 50/50 | 20.772 | 21.500 | 20.089 | 0.0133 | 2.341 | 0.904 | 1.561 | 1.317 | 2.3 | 11.6 |  | 0.04 |
| val1 | observed | uncertain_lead_only | base_stock | 50/50 | 18.987 | 19.811 | 18.241 | 0.0151 | 2.899 | 0.875 | 1.933 | 1.494 | 2.7 | 11.7 |  | 0.42 |
| val1 | observed | uncertain_lead_only | gated | 50/50 | 18.971 | 19.857 | 18.924 | 0.0209 | 2.597 | 0.901 | 1.731 | 1.946 | 2.3 | 11.4 | 0.51 | 3.33 |
| val1 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.239 | 20.878 | 14.535 | 0.0062 | 6.896 | 0.714 | 4.597 | 0.652 | 5.7 | 11.2 |  | 0.22 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50/50 | 19.143 | 19.925 | 17.617 | 0.0123 | 3.457 | 0.851 | 2.305 | 1.262 | 3.2 | 11.6 |  | 0.04 |
| val1 | observed | uncertain_lead_only | reorder_point | 50/50 | 19.149 | 19.931 | 17.601 | 0.0123 | 3.477 | 0.850 | 2.318 | 1.258 | 3.2 | 10.9 |  | 0.04 |
| val1 | recovered | stable | base_stock | 50/50 | 22.087 | 22.687 | 21.249 | 0.0155 | 1.031 | 0.955 | 0.688 | 1.824 | 1.0 | 12.4 |  | 0.54 |
| val1 | recovered | stable | gated | 50/50 | 22.230 | 22.800 | 20.778 | 0.0136 | 1.493 | 0.938 | 0.995 | 1.539 | 1.5 | 11.0 | 0.07 | 3.48 |
| val1 | recovered | stable | order_up_to | 50/50 | 23.462 | 23.845 | 17.176 | 0.0057 | 5.398 | 0.782 | 3.599 | 0.599 | 4.8 | 11.7 |  | 0.22 |
| val1 | recovered | stable | periodic:1 | 50/50 | 22.225 | 22.778 | 20.680 | 0.0130 | 1.502 | 0.937 | 1.001 | 1.502 | 1.6 | 12.4 |  | 0.04 |
| val1 | recovered | stable | reorder_point | 50/50 | 22.229 | 22.781 | 20.666 | 0.0129 | 1.514 | 0.936 | 1.009 | 1.485 | 1.6 | 11.0 |  | 0.04 |
| val1 | recovered | uncertain | base_stock | 50/50 | 25.601 | 26.598 | 24.322 | 0.0170 | 3.536 | 0.911 | 2.357 | 2.021 | 2.1 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain | gated | 50/50 | 26.691 | 27.921 | 27.489 | 0.0652 | 2.740 | 0.933 | 1.827 | 3.895 | 1.5 | 8.6 | 0.57 | 2.75 |
| val1 | recovered | uncertain | order_up_to | 50/50 | 26.729 | 27.472 | 19.189 | 0.0071 | 8.484 | 0.734 | 5.656 | 0.824 | 5.4 | 11.3 |  | 0.22 |
| val1 | recovered | uncertain | periodic:1 | 50/50 | 25.847 | 26.758 | 22.947 | 0.0131 | 4.710 | 0.879 | 3.140 | 1.601 | 2.7 | 12.1 |  | 0.04 |
| val1 | recovered | uncertain | reorder_point | 50/50 | 25.853 | 26.764 | 22.926 | 0.0131 | 4.740 | 0.878 | 3.160 | 1.598 | 2.8 | 11.2 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | base_stock | 50/50 | 24.845 | 25.831 | 25.415 | 0.0202 | 1.614 | 0.937 | 1.076 | 2.216 | 1.5 | 11.7 |  | 0.40 |
| val1 | recovered | uncertain_fill_only | gated | 50/50 | 25.988 | 27.138 | 27.660 | 0.0601 | 1.503 | 0.939 | 1.002 | 4.051 | 1.4 | 8.8 | 0.54 | 3.31 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50/50 | 25.552 | 26.242 | 20.790 | 0.0082 | 5.432 | 0.787 | 3.621 | 0.832 | 4.6 | 11.4 |  | 0.23 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 24.854 | 25.718 | 24.294 | 0.0153 | 2.129 | 0.913 | 1.419 | 1.705 | 2.0 | 12.3 |  | 0.04 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50/50 | 24.860 | 25.725 | 24.290 | 0.0152 | 2.140 | 0.912 | 1.426 | 1.694 | 2.0 | 11.2 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | base_stock | 50/50 | 22.755 | 23.812 | 22.271 | 0.0175 | 3.035 | 0.899 | 2.023 | 1.960 | 2.0 | 11.5 |  | 0.39 |
| val1 | recovered | uncertain_lead_only | gated | 50/50 | 22.845 | 23.923 | 22.739 | 0.0296 | 2.775 | 0.915 | 1.850 | 2.561 | 1.7 | 10.4 | 0.51 | 3.25 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50/50 | 24.224 | 25.019 | 17.761 | 0.0070 | 7.654 | 0.727 | 5.102 | 0.761 | 5.2 | 11.1 |  | 0.23 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 22.921 | 23.923 | 21.551 | 0.0143 | 3.621 | 0.877 | 2.414 | 1.635 | 2.5 | 11.5 |  | 0.04 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50/50 | 22.929 | 23.928 | 21.526 | 0.0143 | 3.643 | 0.875 | 2.429 | 1.629 | 2.5 | 10.4 |  | 0.04 |
| val2 | observed | stable | base_stock | 50/50 | 18.210 | 18.722 | 17.975 | 0.0130 | 0.600 | 0.967 | 0.400 | 1.354 | 1.0 | 12.6 |  | 0.52 |
| val2 | observed | stable | gated | 50/50 | 18.314 | 18.788 | 17.523 | 0.0105 | 0.972 | 0.947 | 0.648 | 1.125 | 1.4 | 11.7 | 0.05 | 3.20 |
| val2 | observed | stable | order_up_to | 50/50 | 19.497 | 19.844 | 14.397 | 0.0047 | 4.632 | 0.802 | 3.088 | 0.471 | 4.8 | 12.1 |  | 0.23 |
| val2 | observed | stable | periodic:1 | 50/50 | 18.292 | 18.756 | 17.511 | 0.0103 | 0.911 | 0.951 | 0.607 | 1.106 | 1.4 | 12.6 |  | 0.05 |
| val2 | observed | stable | reorder_point | 50/50 | 18.314 | 18.783 | 17.473 | 0.0103 | 0.984 | 0.946 | 0.656 | 1.103 | 1.4 | 11.6 |  | 0.06 |
| val2 | observed | uncertain | base_stock | 50/50 | 21.384 | 22.252 | 20.616 | 0.0143 | 2.937 | 0.900 | 1.958 | 1.382 | 2.0 | 12.1 |  | 0.41 |
| val2 | observed | uncertain | gated | 50/50 | 21.564 | 22.634 | 23.432 | 0.0247 | 1.492 | 0.922 | 0.995 | 2.502 | 1.7 | 9.3 | 0.61 | 2.89 |
| val2 | observed | uncertain | order_up_to | 50/50 | 22.247 | 22.882 | 15.949 | 0.0055 | 7.279 | 0.736 | 4.853 | 0.587 | 5.1 | 11.7 |  | 0.24 |
| val2 | observed | uncertain | periodic:1 | 50/50 | 21.607 | 22.406 | 19.433 | 0.0106 | 3.981 | 0.871 | 2.654 | 1.061 | 2.8 | 12.3 |  | 0.05 |
| val2 | observed | uncertain | reorder_point | 50/50 | 21.617 | 22.415 | 19.407 | 0.0106 | 4.015 | 0.869 | 2.676 | 1.061 | 2.8 | 11.5 |  | 0.05 |
| val2 | observed | uncertain_fill_only | base_stock | 50/50 | 21.376 | 22.181 | 21.984 | 0.0153 | 1.255 | 0.940 | 0.837 | 1.571 | 1.2 | 12.4 |  | 0.44 |
| val2 | observed | uncertain_fill_only | gated | 50/50 | 21.772 | 22.810 | 23.893 | 0.0271 | 1.114 | 0.948 | 0.742 | 2.683 | 1.1 | 10.0 | 0.60 | 3.67 |
| val2 | observed | uncertain_fill_only | order_up_to | 50/50 | 21.676 | 22.223 | 17.687 | 0.0057 | 4.529 | 0.810 | 3.019 | 0.612 | 4.4 | 12.2 |  | 0.24 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50/50 | 21.355 | 22.072 | 20.946 | 0.0113 | 1.828 | 0.922 | 1.219 | 1.187 | 1.7 | 12.6 |  | 0.06 |
| val2 | observed | uncertain_fill_only | reorder_point | 50/50 | 21.344 | 22.060 | 20.882 | 0.0113 | 1.871 | 0.921 | 1.248 | 1.186 | 1.7 | 11.8 |  | 0.05 |
| val2 | observed | uncertain_lead_only | base_stock | 50/50 | 18.788 | 19.627 | 18.553 | 0.0141 | 2.276 | 0.888 | 1.518 | 1.457 | 2.2 | 12.1 |  | 0.44 |
| val2 | observed | uncertain_lead_only | gated | 50/50 | 18.765 | 19.683 | 19.126 | 0.0193 | 2.079 | 0.901 | 1.386 | 2.048 | 1.9 | 11.4 | 0.53 | 3.58 |
| val2 | observed | uncertain_lead_only | order_up_to | 50/50 | 20.083 | 20.658 | 14.388 | 0.0059 | 6.378 | 0.738 | 4.252 | 0.641 | 5.0 | 11.6 |  | 0.25 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50/50 | 18.944 | 19.725 | 17.860 | 0.0114 | 2.827 | 0.869 | 1.885 | 1.228 | 2.7 | 11.9 |  | 0.05 |
| val2 | observed | uncertain_lead_only | reorder_point | 50/50 | 18.946 | 19.729 | 17.844 | 0.0112 | 2.849 | 0.867 | 1.899 | 1.225 | 2.7 | 11.2 |  | 0.05 |
| val2 | recovered | stable | base_stock | 50/50 | 23.053 | 23.747 | 21.632 | 0.0172 | 2.016 | 0.947 | 1.344 | 1.984 | 1.2 | 12.4 |  | 0.54 |
| val2 | recovered | stable | gated | 50/50 | 23.229 | 23.886 | 21.067 | 0.0143 | 2.557 | 0.925 | 1.705 | 1.691 | 1.3 | 11.0 | 0.06 | 3.93 |
| val2 | recovered | stable | order_up_to | 50/50 | 24.427 | 24.833 | 17.222 | 0.0065 | 6.326 | 0.775 | 4.217 | 0.680 | 4.4 | 11.8 |  | 0.23 |
| val2 | recovered | stable | periodic:1 | 50/50 | 23.193 | 23.824 | 20.891 | 0.0141 | 2.544 | 0.926 | 1.696 | 1.656 | 1.4 | 12.4 |  | 0.05 |
| val2 | recovered | stable | reorder_point | 50/50 | 23.221 | 23.851 | 20.819 | 0.0139 | 2.633 | 0.919 | 1.755 | 1.639 | 1.4 | 11.0 |  | 0.05 |
| val2 | recovered | uncertain | base_stock | 50/50 | 26.668 | 27.674 | 24.888 | 0.0195 | 4.100 | 0.898 | 2.733 | 2.103 | 2.0 | 11.8 |  | 0.41 |
| val2 | recovered | uncertain | gated | 50/50 | 26.924 | 28.097 | 27.750 | 0.0343 | 2.521 | 0.920 | 1.681 | 2.955 | 1.5 | 9.0 | 0.57 | 2.87 |
| val2 | recovered | uncertain | order_up_to | 50/50 | 27.706 | 28.419 | 18.942 | 0.0081 | 9.425 | 0.723 | 6.283 | 0.921 | 4.7 | 11.4 |  | 0.23 |
| val2 | recovered | uncertain | periodic:1 | 50/50 | 26.832 | 27.741 | 23.242 | 0.0150 | 5.273 | 0.871 | 3.516 | 1.669 | 2.5 | 12.1 |  | 0.05 |
| val2 | recovered | uncertain | reorder_point | 50/50 | 26.843 | 27.754 | 23.186 | 0.0149 | 5.340 | 0.866 | 3.560 | 1.666 | 2.5 | 11.1 |  | 0.05 |
| val2 | recovered | uncertain_fill_only | base_stock | 50/50 | 26.760 | 27.808 | 26.642 | 0.0209 | 2.544 | 0.935 | 1.696 | 2.320 | 1.4 | 11.9 |  | 0.43 |
| val2 | recovered | uncertain_fill_only | gated | 50/50 | 27.165 | 28.467 | 28.889 | 0.0408 | 2.454 | 0.933 | 1.636 | 3.476 | 1.4 | 9.4 | 0.55 | 3.54 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50/50 | 27.143 | 27.815 | 21.195 | 0.0082 | 6.401 | 0.788 | 4.267 | 0.934 | 4.1 | 11.6 |  | 0.24 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50/50 | 26.743 | 27.660 | 25.212 | 0.0158 | 3.262 | 0.913 | 2.174 | 1.818 | 1.8 | 12.2 |  | 0.06 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50/50 | 26.719 | 27.633 | 25.160 | 0.0158 | 3.274 | 0.912 | 2.183 | 1.808 | 1.8 | 11.3 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | base_stock | 50/50 | 23.675 | 24.745 | 22.603 | 0.0206 | 3.672 | 0.883 | 2.448 | 2.187 | 2.2 | 11.8 |  | 0.43 |
| val2 | recovered | uncertain_lead_only | gated | 50/50 | 23.424 | 24.663 | 24.051 | 0.0253 | 2.771 | 0.895 | 1.848 | 2.558 | 1.8 | 11.2 | 0.50 | 3.64 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50/50 | 25.025 | 25.713 | 17.457 | 0.0083 | 8.105 | 0.718 | 5.403 | 0.953 | 4.7 | 11.3 |  | 0.23 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50/50 | 23.852 | 24.839 | 21.623 | 0.0170 | 4.348 | 0.860 | 2.899 | 1.878 | 2.6 | 11.7 |  | 0.05 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50/50 | 23.868 | 24.854 | 21.583 | 0.0170 | 4.398 | 0.857 | 2.932 | 1.873 | 2.6 | 10.5 |  | 0.05 |

## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)

| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | 50 | +0.001 | [-0.000, +0.002] | [-0.000, +0.003] | 14 / 4 / 32 | 0.031 |
| final | observed | stable | periodic:1 | 50 | +0.009 | [+0.004, +0.015] | [+0.002, +0.018] | 40 / 9 / 1 | 0.0 |
| final | observed | stable | base_stock | 50 | +0.070 | [+0.053, +0.090] | [+0.043, +0.102] | 24 / 26 / 0 | 0.888 |
| final | observed | stable | order_up_to | 50 | -0.421 | [-0.502, -0.347] | [-0.548, -0.312] | 46 / 4 / 0 | 0.0 |
| final | observed | uncertain | reorder_point | 50 | -0.006 | [-0.126, +0.124] | [-0.189, +0.200] | 26 / 21 / 3 | 0.56 |
| final | observed | uncertain | periodic:1 | 50 | -0.005 | [-0.118, +0.120] | [-0.179, +0.202] | 28 / 20 / 2 | 0.312 |
| final | observed | uncertain | base_stock | 50 | -0.156 | [-0.283, -0.026] | [-0.355, +0.058] | 36 / 14 / 0 | 0.003 |
| final | observed | uncertain | order_up_to | 50 | -0.274 | [-0.411, -0.130] | [-0.484, -0.047] | 37 / 13 / 0 | 0.001 |
| final | observed | uncertain_fill_only | reorder_point | 50 | -0.210 | [-0.398, -0.030] | [-0.542, +0.015] | 26 / 22 / 2 | 0.665 |
| final | observed | uncertain_fill_only | periodic:1 | 50 | -0.208 | [-0.402, -0.026] | [-0.558, +0.019] | 27 / 22 / 1 | 0.568 |
| final | observed | uncertain_fill_only | base_stock | 50 | -0.406 | [-0.717, -0.125] | [-0.961, -0.071] | 34 / 16 / 0 | 0.015 |
| final | observed | uncertain_fill_only | order_up_to | 50 | -0.632 | [-0.971, -0.343] | [-1.174, -0.264] | 37 / 13 / 0 | 0.001 |
| final | observed | uncertain_lead_only | reorder_point | 50 | -0.048 | [-0.086, -0.011] | [-0.108, +0.003] | 30 / 17 / 3 | 0.079 |
| final | observed | uncertain_lead_only | periodic:1 | 50 | -0.046 | [-0.084, -0.011] | [-0.108, +0.004] | 32 / 17 / 1 | 0.044 |
| final | observed | uncertain_lead_only | base_stock | 50 | +0.014 | [-0.023, +0.049] | [-0.040, +0.067] | 32 / 18 / 0 | 0.065 |
| final | observed | uncertain_lead_only | order_up_to | 50 | -0.467 | [-0.560, -0.377] | [-0.617, -0.334] | 44 / 6 / 0 | 0.0 |
| final | recovered | stable | reorder_point | 50 | -0.010 | [-0.028, +0.006] | [-0.040, +0.015] | 17 / 11 / 22 | 0.345 |
| final | recovered | stable | periodic:1 | 50 | +0.003 | [-0.013, +0.018] | [-0.023, +0.027] | 39 / 10 / 1 | 0.0 |
| final | recovered | stable | base_stock | 50 | +0.088 | [+0.052, +0.126] | [+0.035, +0.148] | 29 / 21 / 0 | 0.322 |
| final | recovered | stable | order_up_to | 50 | -0.577 | [-0.701, -0.463] | [-0.769, -0.412] | 45 / 5 / 0 | 0.0 |
| final | recovered | uncertain | reorder_point | 50 | +0.113 | [-0.008, +0.252] | [-0.041, +0.339] | 24 / 24 / 2 | 1.0 |
| final | recovered | uncertain | periodic:1 | 50 | +0.121 | [+0.002, +0.263] | [-0.038, +0.355] | 25 / 24 / 1 | 1.0 |
| final | recovered | uncertain | base_stock | 50 | -0.105 | [-0.193, -0.007] | [-0.237, +0.050] | 32 / 18 / 0 | 0.065 |
| final | recovered | uncertain | order_up_to | 50 | -0.173 | [-0.342, +0.014] | [-0.403, +0.137] | 35 / 15 / 0 | 0.007 |
| final | recovered | uncertain_fill_only | reorder_point | 50 | -0.064 | [-0.279, +0.129] | [-0.417, +0.204] | 24 / 23 / 3 | 1.0 |
| final | recovered | uncertain_fill_only | periodic:1 | 50 | -0.064 | [-0.280, +0.129] | [-0.427, +0.210] | 23 / 25 / 2 | 0.885 |
| final | recovered | uncertain_fill_only | base_stock | 50 | -0.278 | [-0.624, +0.036] | [-0.863, +0.145] | 26 / 24 / 0 | 0.888 |
| final | recovered | uncertain_fill_only | order_up_to | 50 | -0.558 | [-0.908, -0.247] | [-1.167, -0.149] | 36 / 14 / 0 | 0.003 |
| final | recovered | uncertain_lead_only | reorder_point | 50 | -0.051 | [-0.080, -0.023] | [-0.101, -0.012] | 33 / 13 / 4 | 0.005 |
| final | recovered | uncertain_lead_only | periodic:1 | 50 | -0.036 | [-0.059, -0.016] | [-0.074, -0.007] | 34 / 13 / 3 | 0.003 |
| final | recovered | uncertain_lead_only | base_stock | 50 | +0.055 | [+0.020, +0.095] | [+0.006, +0.117] | 33 / 17 / 0 | 0.033 |
| final | recovered | uncertain_lead_only | order_up_to | 50 | -0.569 | [-0.699, -0.443] | [-0.786, -0.390] | 42 / 8 / 0 | 0.0 |
| val1 | observed | stable | reorder_point | 50 | -0.016 | [-0.032, -0.002] | [-0.041, +0.003] | 8 / 19 / 23 | 0.052 |
| val1 | observed | stable | periodic:1 | 50 | -0.007 | [-0.024, +0.008] | [-0.033, +0.016] | 19 / 23 / 8 | 0.644 |
| val1 | observed | stable | base_stock | 50 | +0.087 | [+0.061, +0.112] | [+0.047, +0.126] | 14 / 36 / 0 | 0.003 |
| val1 | observed | stable | order_up_to | 50 | -1.024 | [-1.336, -0.748] | [-1.581, -0.680] | 49 / 1 / 0 | 0.0 |
| val1 | observed | uncertain | reorder_point | 50 | -0.415 | [-0.898, +0.030] | [-1.288, +0.110] | 28 / 21 / 1 | 0.392 |
| val1 | observed | uncertain | periodic:1 | 50 | -0.405 | [-0.904, +0.028] | [-1.304, +0.110] | 29 / 21 / 0 | 0.322 |
| val1 | observed | uncertain | base_stock | 50 | -0.196 | [-0.552, +0.125] | [-0.806, +0.210] | 24 / 26 / 0 | 0.888 |
| val1 | observed | uncertain | order_up_to | 50 | -1.147 | [-1.930, -0.444] | [-2.584, -0.342] | 42 / 8 / 0 | 0.0 |
| val1 | observed | uncertain_fill_only | reorder_point | 50 | +0.362 | [+0.180, +0.549] | [+0.094, +0.661] | 23 / 27 / 0 | 0.672 |
| val1 | observed | uncertain_fill_only | periodic:1 | 50 | +0.376 | [+0.186, +0.563] | [+0.097, +0.668] | 23 / 27 / 0 | 0.672 |
| val1 | observed | uncertain_fill_only | base_stock | 50 | +0.429 | [+0.229, +0.630] | [+0.136, +0.751] | 23 / 27 / 0 | 0.672 |
| val1 | observed | uncertain_fill_only | order_up_to | 50 | -0.117 | [-0.366, +0.136] | [-0.513, +0.265] | 30 / 20 / 0 | 0.203 |
| val1 | observed | uncertain_lead_only | reorder_point | 50 | -0.179 | [-0.282, -0.065] | [-0.331, +0.002] | 36 / 14 / 0 | 0.003 |
| val1 | observed | uncertain_lead_only | periodic:1 | 50 | -0.172 | [-0.276, -0.056] | [-0.326, +0.011] | 36 / 14 / 0 | 0.003 |
| val1 | observed | uncertain_lead_only | base_stock | 50 | -0.016 | [-0.133, +0.104] | [-0.186, +0.175] | 30 / 20 / 0 | 0.203 |
| val1 | observed | uncertain_lead_only | order_up_to | 50 | -1.268 | [-1.727, -0.866] | [-2.046, -0.751] | 45 / 5 / 0 | 0.0 |
| val1 | recovered | stable | reorder_point | 50 | +0.001 | [-0.010, +0.013] | [-0.016, +0.021] | 9 / 17 / 24 | 0.169 |
| val1 | recovered | stable | periodic:1 | 50 | +0.005 | [-0.006, +0.018] | [-0.012, +0.026] | 21 / 20 / 9 | 1.0 |
| val1 | recovered | stable | base_stock | 50 | +0.144 | [+0.095, +0.198] | [+0.078, +0.234] | 12 / 38 / 0 | 0.0 |
| val1 | recovered | stable | order_up_to | 50 | -1.232 | [-1.629, -0.902] | [-1.911, -0.832] | 48 / 2 / 0 | 0.0 |
| val1 | recovered | uncertain | reorder_point | 50 | +0.839 | [-0.021, +1.777] | [-0.137, +2.619] | 23 / 27 / 0 | 0.672 |
| val1 | recovered | uncertain | periodic:1 | 50 | +0.845 | [-0.013, +1.776] | [-0.129, +2.597] | 22 / 28 / 0 | 0.48 |
| val1 | recovered | uncertain | base_stock | 50 | +1.091 | [+0.114, +2.157] | [+0.005, +3.057] | 20 / 30 / 0 | 0.203 |
| val1 | recovered | uncertain | order_up_to | 50 | -0.037 | [-0.667, +0.661] | [-0.832, +1.190] | 34 / 16 / 0 | 0.015 |
| val1 | recovered | uncertain_fill_only | reorder_point | 50 | +1.128 | [+0.393, +2.004] | [+0.194, +2.569] | 20 / 29 / 1 | 0.253 |
| val1 | recovered | uncertain_fill_only | periodic:1 | 50 | +1.135 | [+0.430, +1.981] | [+0.241, +2.554] | 19 / 30 / 1 | 0.152 |
| val1 | recovered | uncertain_fill_only | base_stock | 50 | +1.143 | [+0.421, +1.959] | [+0.245, +2.510] | 17 / 33 / 0 | 0.033 |
| val1 | recovered | uncertain_fill_only | order_up_to | 50 | +0.436 | [-0.096, +1.013] | [-0.300, +1.395] | 29 / 21 / 0 | 0.322 |
| val1 | recovered | uncertain_lead_only | reorder_point | 50 | -0.084 | [-0.233, +0.075] | [-0.305, +0.162] | 30 / 20 / 0 | 0.203 |
| val1 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.077 | [-0.223, +0.083] | [-0.303, +0.172] | 30 / 20 / 0 | 0.203 |
| val1 | recovered | uncertain_lead_only | base_stock | 50 | +0.089 | [-0.062, +0.251] | [-0.137, +0.347] | 18 / 32 / 0 | 0.065 |
| val1 | recovered | uncertain_lead_only | order_up_to | 50 | -1.379 | [-1.818, -0.979] | [-2.140, -0.813] | 44 / 6 / 0 | 0.0 |
| val2 | observed | stable | reorder_point | 50 | +0.000 | [-0.005, +0.006] | [-0.008, +0.009] | 3 / 16 / 31 | 0.004 |
| val2 | observed | stable | periodic:1 | 50 | +0.022 | [+0.012, +0.032] | [+0.008, +0.038] | 16 / 22 / 12 | 0.418 |
| val2 | observed | stable | base_stock | 50 | +0.103 | [+0.073, +0.134] | [+0.058, +0.152] | 15 / 35 / 0 | 0.007 |
| val2 | observed | stable | order_up_to | 50 | -1.183 | [-1.701, -0.706] | [-2.154, -0.642] | 49 / 1 / 0 | 0.0 |
| val2 | observed | uncertain | reorder_point | 50 | -0.053 | [-0.475, +0.326] | [-0.764, +0.468] | 26 / 24 / 0 | 0.888 |
| val2 | observed | uncertain | periodic:1 | 50 | -0.043 | [-0.480, +0.345] | [-0.767, +0.496] | 23 / 27 / 0 | 0.672 |
| val2 | observed | uncertain | base_stock | 50 | +0.180 | [-0.088, +0.450] | [-0.230, +0.592] | 21 / 29 / 0 | 0.322 |
| val2 | observed | uncertain | order_up_to | 50 | -0.683 | [-1.352, -0.081] | [-1.850, +0.090] | 30 / 20 / 0 | 0.203 |
| val2 | observed | uncertain_fill_only | reorder_point | 50 | +0.428 | [+0.083, +0.822] | [-0.068, +1.102] | 21 / 28 / 1 | 0.392 |
| val2 | observed | uncertain_fill_only | periodic:1 | 50 | +0.417 | [+0.088, +0.783] | [-0.048, +1.000] | 21 / 29 / 0 | 0.322 |
| val2 | observed | uncertain_fill_only | base_stock | 50 | +0.396 | [+0.049, +0.774] | [-0.078, +1.019] | 20 / 30 / 0 | 0.203 |
| val2 | observed | uncertain_fill_only | order_up_to | 50 | +0.097 | [-0.256, +0.452] | [-0.407, +0.675] | 32 / 18 / 0 | 0.065 |
| val2 | observed | uncertain_lead_only | reorder_point | 50 | -0.181 | [-0.263, -0.098] | [-0.314, -0.062] | 30 / 20 / 0 | 0.203 |
| val2 | observed | uncertain_lead_only | periodic:1 | 50 | -0.179 | [-0.261, -0.102] | [-0.304, -0.067] | 30 / 20 / 0 | 0.203 |
| val2 | observed | uncertain_lead_only | base_stock | 50 | -0.023 | [-0.102, +0.057] | [-0.141, +0.102] | 26 / 24 / 0 | 0.888 |
| val2 | observed | uncertain_lead_only | order_up_to | 50 | -1.318 | [-1.888, -0.822] | [-2.309, -0.710] | 48 / 2 / 0 | 0.0 |
| val2 | recovered | stable | reorder_point | 50 | +0.008 | [-0.033, +0.055] | [-0.048, +0.088] | 11 / 13 / 26 | 0.839 |
| val2 | recovered | stable | periodic:1 | 50 | +0.037 | [-0.007, +0.085] | [-0.023, +0.126] | 24 / 21 / 5 | 0.766 |
| val2 | recovered | stable | base_stock | 50 | +0.177 | [+0.111, +0.249] | [+0.082, +0.292] | 17 / 33 / 0 | 0.033 |
| val2 | recovered | stable | order_up_to | 50 | -1.197 | [-1.577, -0.860] | [-1.848, -0.786] | 49 / 1 / 0 | 0.0 |
| val2 | recovered | uncertain | reorder_point | 50 | +0.081 | [-0.316, +0.461] | [-0.558, +0.645] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain | periodic:1 | 50 | +0.092 | [-0.322, +0.498] | [-0.574, +0.693] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain | base_stock | 50 | +0.256 | [-0.012, +0.528] | [-0.152, +0.681] | 23 / 27 / 0 | 0.672 |
| val2 | recovered | uncertain | order_up_to | 50 | -0.781 | [-1.677, -0.035] | [-2.251, +0.208] | 32 / 18 / 0 | 0.065 |
| val2 | recovered | uncertain_fill_only | reorder_point | 50 | +0.446 | [+0.227, +0.676] | [+0.113, +0.804] | 19 / 31 / 0 | 0.119 |
| val2 | recovered | uncertain_fill_only | periodic:1 | 50 | +0.422 | [+0.205, +0.653] | [+0.098, +0.789] | 19 / 31 / 0 | 0.119 |
| val2 | recovered | uncertain_fill_only | base_stock | 50 | +0.405 | [+0.202, +0.618] | [+0.095, +0.745] | 15 / 35 / 0 | 0.007 |
| val2 | recovered | uncertain_fill_only | order_up_to | 50 | +0.022 | [-0.242, +0.296] | [-0.377, +0.449] | 30 / 20 / 0 | 0.203 |
| val2 | recovered | uncertain_lead_only | reorder_point | 50 | -0.444 | [-0.732, -0.184] | [-0.937, -0.095] | 30 / 19 / 1 | 0.152 |
| val2 | recovered | uncertain_lead_only | periodic:1 | 50 | -0.427 | [-0.702, -0.174] | [-0.924, -0.086] | 28 / 21 / 1 | 0.392 |
| val2 | recovered | uncertain_lead_only | base_stock | 50 | -0.251 | [-0.472, -0.046] | [-0.631, +0.028] | 24 / 26 / 0 | 0.888 |
| val2 | recovered | uncertain_lead_only | order_up_to | 50 | -1.601 | [-2.240, -1.036] | [-2.689, -0.885] | 47 / 3 / 0 | 0.0 |

## Paired comparison on service and inventory (ZAAD minus baseline)

| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|---|
| final | observed | stable | reorder_point | shortage | 50 | +0.0028 | [+0.0000, +0.0083] | 0 / 1 |
| final | observed | stable | reorder_point | avg_inventory_units | 50 | -0.0140 | [-0.0541, +0.0301] | 11 / 3 |
| final | observed | stable | reorder_point | service_unit_fill | 50 | -0.0005 | [-0.0016, +0.0000] | 0 / 1 |
| final | observed | stable | periodic:1 | shortage | 50 | +0.0334 | [+0.0126, +0.0574] | 0 / 8 |
| final | observed | stable | periodic:1 | avg_inventory_units | 50 | -0.0212 | [-0.0604, +0.0211] | 21 / 8 |
| final | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0052 | [-0.0091, -0.0019] | 0 / 8 |
| final | observed | stable | base_stock | shortage | 50 | +0.2250 | [+0.1456, +0.3120] | 0 / 26 |
| final | observed | stable | base_stock | avg_inventory_units | 50 | -0.2605 | [-0.4075, -0.1638] | 48 / 2 |
| final | observed | stable | base_stock | service_unit_fill | 50 | -0.0198 | [-0.0262, -0.0138] | 0 / 26 |
| final | observed | stable | order_up_to | shortage | 50 | -1.2833 | [-1.6497, -0.9606] | 46 / 0 |
| final | observed | stable | order_up_to | avg_inventory_units | 50 | +0.6842 | [+0.4173, +1.1375] | 0 / 50 |
| final | observed | stable | order_up_to | service_unit_fill | 50 | +0.1238 | [+0.0993, +0.1467] | 46 / 0 |
| final | observed | uncertain | reorder_point | shortage | 50 | -0.1578 | [-0.4933, +0.1056] | 15 / 12 |
| final | observed | uncertain | reorder_point | avg_inventory_units | 50 | +0.5664 | [+0.1031, +1.4129] | 11 / 33 |
| final | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0108 | [-0.0078, +0.0291] | 15 / 12 |
| final | observed | uncertain | periodic:1 | shortage | 50 | -0.1521 | [-0.5007, +0.1043] | 15 / 12 |
| final | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5644 | [+0.1037, +1.4258] | 13 / 32 |
| final | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0099 | [-0.0082, +0.0279] | 15 / 12 |
| final | observed | uncertain | base_stock | shortage | 50 | +0.1932 | [-0.1239, +0.4878] | 8 / 20 |
| final | observed | uncertain | base_stock | avg_inventory_units | 50 | +0.2660 | [-0.0931, +0.9132] | 32 / 18 |
| final | observed | uncertain | base_stock | service_unit_fill | 50 | -0.0194 | [-0.0417, -0.0011] | 8 / 20 |
| final | observed | uncertain | order_up_to | shortage | 50 | -1.3352 | [-1.8482, -0.8991] | 41 / 1 |
| final | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.0183 | [+0.3910, +2.2010] | 0 / 50 |
| final | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1270 | [+0.1002, +0.1548] | 41 / 1 |
| final | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.1066 | [-0.2363, +0.0088] | 15 / 7 |
| final | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.6912 | [+0.2283, +1.5014] | 4 / 41 |
| final | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0070 | [-0.0033, +0.0174] | 15 / 7 |
| final | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.1001 | [-0.2303, +0.0124] | 14 / 8 |
| final | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.6886 | [+0.2232, +1.4947] | 6 / 41 |
| final | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0061 | [-0.0039, +0.0164] | 14 / 8 |
| final | observed | uncertain_fill_only | base_stock | shortage | 50 | +0.1846 | [+0.0591, +0.3248] | 4 / 20 |
| final | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.3452 | [-0.0240, +0.9999] | 28 / 22 |
| final | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0140 | [-0.0239, -0.0052] | 4 / 20 |
| final | observed | uncertain_fill_only | order_up_to | shortage | 50 | -1.2810 | [-1.6698, -0.9367] | 41 / 0 |
| final | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.2423 | [+0.5660, +2.4314] | 1 / 49 |
| final | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1210 | [+0.0956, +0.1475] | 41 / 0 |
| final | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.1520 | [-0.3347, +0.0066] | 12 / 10 |
| final | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.1398 | [+0.0568, +0.2492] | 10 / 32 |
| final | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0119 | [-0.0005, +0.0254] | 12 / 10 |
| final | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.1427 | [-0.3222, +0.0119] | 12 / 10 |
| final | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.1362 | [+0.0541, +0.2462] | 12 / 32 |
| final | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0112 | [-0.0006, +0.0246] | 12 / 10 |
| final | observed | uncertain_lead_only | base_stock | shortage | 50 | +0.0672 | [-0.0948, +0.2396] | 8 / 18 |
| final | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | -0.0618 | [-0.1300, +0.0227] | 36 / 14 |
| final | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | -0.0040 | [-0.0147, +0.0076] | 8 / 18 |
| final | observed | uncertain_lead_only | order_up_to | shortage | 50 | -1.4275 | [-1.8431, -1.0277] | 44 / 0 |
| final | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.6677 | [+0.4000, +1.1149] | 0 / 50 |
| final | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1306 | [+0.1047, +0.1566] | 44 / 0 |
| final | recovered | stable | reorder_point | shortage | 50 | -0.0297 | [-0.1159, +0.0411] | 3 / 4 |
| final | recovered | stable | reorder_point | avg_inventory_units | 50 | -0.0247 | [-0.1453, +0.0637] | 14 / 10 |
| final | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0042 | [-0.0024, +0.0148] | 3 / 4 |
| final | recovered | stable | periodic:1 | shortage | 50 | +0.0146 | [-0.0649, +0.0851] | 2 / 8 |
| final | recovered | stable | periodic:1 | avg_inventory_units | 50 | -0.0323 | [-0.1545, +0.0628] | 25 / 10 |
| final | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0005 | [-0.0058, +0.0092] | 2 / 8 |
| final | recovered | stable | base_stock | shortage | 50 | +0.2820 | [+0.1251, +0.4645] | 2 / 21 |
| final | recovered | stable | base_stock | avg_inventory_units | 50 | -0.3679 | [-0.6399, -0.1907] | 45 / 5 |
| final | recovered | stable | base_stock | service_unit_fill | 50 | -0.0155 | [-0.0250, -0.0060] | 2 / 21 |
| final | recovered | stable | order_up_to | shortage | 50 | -1.7587 | [-2.3344, -1.2797] | 45 / 0 |
| final | recovered | stable | order_up_to | avg_inventory_units | 50 | +0.9754 | [+0.6337, +1.5059] | 0 / 50 |
| final | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1397 | [+0.1186, +0.1606] | 45 / 0 |
| final | recovered | uncertain | reorder_point | shortage | 50 | -0.0577 | [-0.1851, +0.0757] | 15 / 9 |
| final | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +0.6027 | [+0.1363, +1.4349] | 13 / 32 |
| final | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0060 | [-0.0098, +0.0196] | 15 / 9 |
| final | recovered | uncertain | periodic:1 | shortage | 50 | -0.0396 | [-0.1599, +0.0974] | 14 / 9 |
| final | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +0.5958 | [+0.1305, +1.4525] | 15 / 31 |
| final | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0054 | [-0.0099, +0.0186] | 14 / 9 |
| final | recovered | uncertain | base_stock | shortage | 50 | +0.2625 | [+0.1039, +0.4442] | 5 / 18 |
| final | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.1641 | [-0.1915, +0.7795] | 35 / 15 |
| final | recovered | uncertain | base_stock | service_unit_fill | 50 | -0.0197 | [-0.0394, -0.0048] | 5 / 18 |
| final | recovered | uncertain | order_up_to | shortage | 50 | -1.6016 | [-2.1793, -1.1170] | 42 / 0 |
| final | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +1.2942 | [+0.5682, +2.5994] | 0 / 50 |
| final | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1305 | [+0.1044, +0.1575] | 42 / 0 |
| final | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.1018 | [-0.2764, +0.0872] | 9 / 10 |
| final | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +0.9115 | [+0.2919, +1.9403] | 8 / 38 |
| final | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0062 | [-0.0052, +0.0184] | 9 / 10 |
| final | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.0942 | [-0.2673, +0.0861] | 9 / 10 |
| final | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +0.9082 | [+0.2913, +1.9414] | 9 / 38 |
| final | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0049 | [-0.0060, +0.0158] | 9 / 10 |
| final | recovered | uncertain_fill_only | base_stock | shortage | 50 | +0.2120 | [+0.0424, +0.4517] | 3 / 16 |
| final | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +0.4229 | [-0.0434, +1.2072] | 28 / 22 |
| final | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0164 | [-0.0279, -0.0048] | 3 / 16 |
| final | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -1.6387 | [-2.2588, -1.1349] | 43 / 0 |
| final | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +1.7413 | [+0.8205, +3.2987] | 1 / 49 |
| final | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1280 | [+0.1017, +0.1561] | 43 / 0 |
| final | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.1541 | [-0.2966, -0.0357] | 11 / 5 |
| final | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.0856 | [-0.0012, +0.1809] | 16 / 23 |
| final | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0107 | [+0.0002, +0.0220] | 11 / 5 |
| final | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.1094 | [-0.2179, -0.0202] | 11 / 5 |
| final | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.0834 | [+0.0021, +0.1834] | 19 / 23 |
| final | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0084 | [-0.0009, +0.0185] | 11 / 5 |
| final | recovered | uncertain_lead_only | base_stock | shortage | 50 | +0.1897 | [+0.0381, +0.3811] | 6 / 16 |
| final | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | -0.1959 | [-0.3934, -0.0600] | 38 / 12 |
| final | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | -0.0100 | [-0.0194, -0.0006] | 6 / 16 |
| final | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -1.7452 | [-2.3638, -1.2168] | 43 / 0 |
| final | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +0.8825 | [+0.5632, +1.3939] | 0 / 50 |
| final | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1377 | [+0.1111, +0.1649] | 43 / 0 |
| val1 | observed | stable | reorder_point | shortage | 50 | -0.0639 | [-0.1366, -0.0104] | 8 / 1 |
| val1 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0554 | [+0.0257, +0.0913] | 1 / 25 |
| val1 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0039 | [+0.0007, +0.0082] | 8 / 1 |
| val1 | observed | stable | periodic:1 | shortage | 50 | -0.0370 | [-0.1109, +0.0184] | 5 / 8 |
| val1 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0428 | [+0.0140, +0.0775] | 18 / 24 |
| val1 | observed | stable | periodic:1 | service_unit_fill | 50 | +0.0021 | [-0.0015, +0.0066] | 5 / 8 |
| val1 | observed | stable | base_stock | shortage | 50 | +0.3027 | [+0.2071, +0.4012] | 2 / 38 |
| val1 | observed | stable | base_stock | avg_inventory_units | 50 | -0.1999 | [-0.3476, -0.1092] | 46 / 4 |
| val1 | observed | stable | base_stock | service_unit_fill | 50 | -0.0154 | [-0.0208, -0.0101] | 2 / 38 |
| val1 | observed | stable | order_up_to | shortage | 50 | -3.2400 | [-4.8789, -2.2479] | 50 / 0 |
| val1 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.7067 | [+0.4848, +1.0375] | 0 / 50 |
| val1 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1501 | [+0.1321, +0.1699] | 50 / 0 |
| val1 | observed | uncertain | reorder_point | shortage | 50 | -2.0911 | [-3.9451, -0.9351] | 41 / 1 |
| val1 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.5519 | [+0.7796, +2.8886] | 0 / 49 |
| val1 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0601 | [+0.0462, +0.0749] | 41 / 1 |
| val1 | observed | uncertain | periodic:1 | shortage | 50 | -2.0683 | [-3.9290, -0.9245] | 41 / 1 |
| val1 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.5484 | [+0.7737, +2.8957] | 0 / 49 |
| val1 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0592 | [+0.0455, +0.0735] | 41 / 1 |
| val1 | observed | uncertain | base_stock | shortage | 50 | -1.0823 | [-2.1631, -0.3607] | 30 / 11 |
| val1 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.2335 | [+0.5518, +2.3722] | 5 / 45 |
| val1 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0267 | [+0.0145, +0.0396] | 30 / 11 |
| val1 | observed | uncertain | order_up_to | shortage | 50 | -5.1688 | [-8.5912, -3.0426] | 50 / 0 |
| val1 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +2.0972 | [+1.1501, +3.7458] | 0 / 50 |
| val1 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1939 | [+0.1743, +0.2144] | 50 / 0 |
| val1 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.6282 | [-0.8574, -0.4180] | 31 / 3 |
| val1 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.5773 | [+0.9524, +2.4984] | 1 / 48 |
| val1 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0314 | [+0.0195, +0.0448] | 31 / 3 |
| val1 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.5797 | [-0.8099, -0.3688] | 29 / 3 |
| val1 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.5750 | [+0.9497, +2.5518] | 1 / 48 |
| val1 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0308 | [+0.0186, +0.0436] | 29 / 3 |
| val1 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1256 | [-0.3024, +0.0260] | 16 / 14 |
| val1 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.1710 | [+0.6802, +1.8496] | 7 / 43 |
| val1 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0071 | [-0.0029, +0.0189] | 16 / 14 |
| val1 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.1862 | [-4.6010, -2.2600] | 50 / 0 |
| val1 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.1851 | [+1.3798, +3.4436] | 0 / 50 |
| val1 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1507 | [+0.1293, +0.1731] | 50 / 0 |
| val1 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.8800 | [-1.2094, -0.6034] | 39 / 1 |
| val1 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.6878 | [+0.4390, +0.9973] | 0 / 50 |
| val1 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0505 | [+0.0342, +0.0707] | 39 / 1 |
| val1 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.8605 | [-1.1770, -0.5803] | 38 / 2 |
| val1 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.6838 | [+0.4418, +0.9855] | 0 / 50 |
| val1 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0492 | [+0.0334, +0.0695] | 38 / 2 |
| val1 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.3025 | [-0.6368, +0.0777] | 29 / 13 |
| val1 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.4513 | [+0.2752, +0.6587] | 8 / 42 |
| val1 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0253 | [+0.0089, +0.0474] | 29 / 13 |
| val1 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.2996 | [-6.5216, -2.8660] | 50 / 0 |
| val1 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.2938 | [+0.8689, +1.9156] | 0 / 50 |
| val1 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1869 | [+0.1680, +0.2063] | 50 / 0 |
| val1 | recovered | stable | reorder_point | shortage | 50 | -0.0209 | [-0.0600, +0.0122] | 6 / 4 |
| val1 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0540 | [+0.0206, +0.0983] | 8 / 17 |
| val1 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0020 | [-0.0000, +0.0048] | 6 / 4 |
| val1 | recovered | stable | periodic:1 | shortage | 50 | -0.0084 | [-0.0453, +0.0229] | 6 / 9 |
| val1 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0364 | [+0.0001, +0.0817] | 26 / 15 |
| val1 | recovered | stable | periodic:1 | service_unit_fill | 50 | +0.0011 | [-0.0011, +0.0038] | 6 / 9 |
| val1 | recovered | stable | base_stock | shortage | 50 | +0.4618 | [+0.2810, +0.7233] | 2 / 38 |
| val1 | recovered | stable | base_stock | avg_inventory_units | 50 | -0.2856 | [-0.4186, -0.1904] | 47 / 3 |
| val1 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0167 | [-0.0218, -0.0113] | 2 / 38 |
| val1 | recovered | stable | order_up_to | shortage | 50 | -3.9049 | [-5.8311, -2.7279] | 50 / 0 |
| val1 | recovered | stable | order_up_to | avg_inventory_units | 50 | +0.9402 | [+0.6884, +1.3589] | 0 / 50 |
| val1 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1567 | [+0.1379, +0.1774] | 50 / 0 |
| val1 | recovered | uncertain | reorder_point | shortage | 50 | -1.9992 | [-3.2180, -1.0697] | 40 / 0 |
| val1 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +2.2962 | [+0.9516, +4.5993] | 0 / 49 |
| val1 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0554 | [+0.0402, +0.0717] | 40 / 0 |
| val1 | recovered | uncertain | periodic:1 | shortage | 50 | -1.9701 | [-3.2551, -1.0618] | 40 / 0 |
| val1 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +2.2938 | [+0.9513, +4.6703] | 0 / 49 |
| val1 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0539 | [+0.0390, +0.0696] | 40 / 0 |
| val1 | recovered | uncertain | base_stock | shortage | 50 | -0.7954 | [-1.3197, -0.3441] | 27 / 8 |
| val1 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +1.8733 | [+0.6178, +4.0331] | 8 / 42 |
| val1 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0228 | [+0.0103, +0.0363] | 27 / 8 |
| val1 | recovered | uncertain | order_up_to | shortage | 50 | -5.7435 | [-8.8309, -3.6830] | 49 / 0 |
| val1 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +3.0702 | [+1.5527, +5.7934] | 0 / 50 |
| val1 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1990 | [+0.1771, +0.2232] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.6368 | [-1.0188, -0.2964] | 26 / 8 |
| val1 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +2.3568 | [+1.0520, +4.6886] | 0 / 48 |
| val1 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0265 | [+0.0137, +0.0406] | 26 / 8 |
| val1 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.6262 | [-0.9912, -0.2932] | 26 / 8 |
| val1 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +2.3462 | [+1.0631, +4.6434] | 0 / 48 |
| val1 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0258 | [+0.0133, +0.0405] | 26 / 8 |
| val1 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.1109 | [-0.4294, +0.1819] | 12 / 18 |
| val1 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.8347 | [+0.6901, +3.9332] | 7 / 43 |
| val1 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0017 | [-0.0098, +0.0136] | 12 / 18 |
| val1 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -3.9293 | [-5.8955, -2.6636] | 49 / 0 |
| val1 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +3.2194 | [+1.7414, +5.8160] | 0 / 50 |
| val1 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1517 | [+0.1290, +0.1748] | 49 / 0 |
| val1 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -0.8675 | [-1.2941, -0.5158] | 36 / 0 |
| val1 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.9316 | [+0.5903, +1.4167] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0397 | [+0.0240, +0.0610] | 36 / 0 |
| val1 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -0.8455 | [-1.2489, -0.4972] | 36 / 0 |
| val1 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.9257 | [+0.5788, +1.4283] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0385 | [+0.0229, +0.0590] | 36 / 0 |
| val1 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.2593 | [-0.6807, +0.1805] | 16 / 15 |
| val1 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.6008 | [+0.3295, +0.9444] | 13 / 37 |
| val1 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0166 | [-0.0001, +0.0387] | 16 / 15 |
| val1 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -4.8784 | [-6.9757, -3.4137] | 50 / 0 |
| val1 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.7993 | [+1.2206, +2.6854] | 0 / 50 |
| val1 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1884 | [+0.1676, +0.2104] | 50 / 0 |
| val2 | observed | stable | reorder_point | shortage | 50 | -0.0116 | [-0.0339, +0.0060] | 3 / 2 |
| val2 | observed | stable | reorder_point | avg_inventory_units | 50 | +0.0221 | [+0.0031, +0.0476] | 1 / 17 |
| val2 | observed | stable | reorder_point | service_unit_fill | 50 | +0.0008 | [-0.0003, +0.0021] | 3 / 2 |
| val2 | observed | stable | periodic:1 | shortage | 50 | +0.0614 | [+0.0179, +0.1131] | 3 / 12 |
| val2 | observed | stable | periodic:1 | avg_inventory_units | 50 | +0.0187 | [+0.0001, +0.0426] | 15 / 20 |
| val2 | observed | stable | periodic:1 | service_unit_fill | 50 | -0.0043 | [-0.0080, -0.0010] | 3 / 12 |
| val2 | observed | stable | base_stock | shortage | 50 | +0.3725 | [+0.2618, +0.4938] | 1 / 36 |
| val2 | observed | stable | base_stock | avg_inventory_units | 50 | -0.2292 | [-0.3728, -0.1417] | 49 / 1 |
| val2 | observed | stable | base_stock | service_unit_fill | 50 | -0.0208 | [-0.0281, -0.0146] | 1 / 36 |
| val2 | observed | stable | order_up_to | shortage | 50 | -3.6599 | [-6.5019, -2.0743] | 50 / 0 |
| val2 | observed | stable | order_up_to | avg_inventory_units | 50 | +0.6542 | [+0.4990, +0.8784] | 0 / 50 |
| val2 | observed | stable | order_up_to | service_unit_fill | 50 | +0.1450 | [+0.1259, +0.1662] | 50 / 0 |
| val2 | observed | uncertain | reorder_point | shortage | 50 | -2.5225 | [-5.4949, -0.8284] | 41 / 4 |
| val2 | observed | uncertain | reorder_point | avg_inventory_units | 50 | +1.4418 | [+0.8402, +2.3613] | 0 / 50 |
| val2 | observed | uncertain | reorder_point | service_unit_fill | 50 | +0.0525 | [+0.0382, +0.0674] | 41 / 4 |
| val2 | observed | uncertain | periodic:1 | shortage | 50 | -2.4891 | [-5.3923, -0.7797] | 42 / 4 |
| val2 | observed | uncertain | periodic:1 | avg_inventory_units | 50 | +1.4413 | [+0.8419, +2.3633] | 0 / 50 |
| val2 | observed | uncertain | periodic:1 | service_unit_fill | 50 | +0.0504 | [+0.0369, +0.0649] | 42 / 4 |
| val2 | observed | uncertain | base_stock | shortage | 50 | -1.4443 | [-3.3276, -0.3055] | 27 / 14 |
| val2 | observed | uncertain | base_stock | avg_inventory_units | 50 | +1.1203 | [+0.6092, +1.8512] | 4 / 46 |
| val2 | observed | uncertain | base_stock | service_unit_fill | 50 | +0.0212 | [+0.0083, +0.0346] | 27 / 14 |
| val2 | observed | uncertain | order_up_to | shortage | 50 | -5.7867 | [-10.9527, -2.8468] | 50 / 0 |
| val2 | observed | uncertain | order_up_to | avg_inventory_units | 50 | +1.9151 | [+1.2525, +2.9570] | 0 / 50 |
| val2 | observed | uncertain | order_up_to | service_unit_fill | 50 | +0.1855 | [+0.1674, +0.2056] | 50 / 0 |
| val2 | observed | uncertain_fill_only | reorder_point | shortage | 50 | -0.7578 | [-1.2921, -0.3548] | 25 / 3 |
| val2 | observed | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.4970 | [+0.8489, +2.4756] | 0 / 49 |
| val2 | observed | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0278 | [+0.0151, +0.0408] | 25 / 3 |
| val2 | observed | uncertain_fill_only | periodic:1 | shortage | 50 | -0.7147 | [-1.1974, -0.3308] | 24 / 5 |
| val2 | observed | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.4962 | [+0.8490, +2.4830] | 1 / 49 |
| val2 | observed | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0262 | [+0.0145, +0.0393] | 24 / 5 |
| val2 | observed | uncertain_fill_only | base_stock | shortage | 50 | -0.1413 | [-0.5399, +0.2846] | 17 / 13 |
| val2 | observed | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.1120 | [+0.5690, +1.9400] | 8 / 42 |
| val2 | observed | uncertain_fill_only | base_stock | service_unit_fill | 50 | +0.0086 | [-0.0013, +0.0199] | 17 / 13 |
| val2 | observed | uncertain_fill_only | order_up_to | shortage | 50 | -3.4153 | [-5.8724, -2.0069] | 50 / 0 |
| val2 | observed | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.0714 | [+1.3488, +3.1387] | 0 / 50 |
| val2 | observed | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1383 | [+0.1173, +0.1604] | 50 / 0 |
| val2 | observed | uncertain_lead_only | reorder_point | shortage | 50 | -0.7701 | [-1.1471, -0.4630] | 32 / 2 |
| val2 | observed | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.8234 | [+0.3963, +1.5620] | 3 / 47 |
| val2 | observed | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0339 | [+0.0216, +0.0489] | 32 / 2 |
| val2 | observed | uncertain_lead_only | periodic:1 | shortage | 50 | -0.7482 | [-1.1153, -0.4441] | 32 / 4 |
| val2 | observed | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.8201 | [+0.3950, +1.5630] | 2 / 48 |
| val2 | observed | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0318 | [+0.0200, +0.0456] | 32 / 4 |
| val2 | observed | uncertain_lead_only | base_stock | shortage | 50 | -0.1973 | [-0.5184, +0.1469] | 22 / 14 |
| val2 | observed | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.5918 | [+0.2207, +1.2232] | 13 / 37 |
| val2 | observed | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0123 | [+0.0007, +0.0267] | 22 / 14 |
| val2 | observed | uncertain_lead_only | order_up_to | shortage | 50 | -4.2987 | [-7.1192, -2.5260] | 50 / 0 |
| val2 | observed | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.4076 | [+0.8682, +2.3203] | 0 / 50 |
| val2 | observed | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1629 | [+0.1438, +0.1839] | 50 / 0 |
| val2 | recovered | stable | reorder_point | shortage | 50 | -0.0755 | [-0.1682, -0.0144] | 8 / 2 |
| val2 | recovered | stable | reorder_point | avg_inventory_units | 50 | +0.0521 | [+0.0233, +0.0867] | 4 / 19 |
| val2 | recovered | stable | reorder_point | service_unit_fill | 50 | +0.0055 | [+0.0009, +0.0116] | 8 / 2 |
| val2 | recovered | stable | periodic:1 | shortage | 50 | +0.0133 | [-0.0873, +0.0956] | 7 / 11 |
| val2 | recovered | stable | periodic:1 | avg_inventory_units | 50 | +0.0343 | [+0.0027, +0.0718] | 25 / 19 |
| val2 | recovered | stable | periodic:1 | service_unit_fill | 50 | -0.0011 | [-0.0066, +0.0053] | 7 / 11 |
| val2 | recovered | stable | base_stock | shortage | 50 | +0.5410 | [+0.3124, +0.8406] | 2 / 34 |
| val2 | recovered | stable | base_stock | avg_inventory_units | 50 | -0.2929 | [-0.4335, -0.1930] | 46 / 4 |
| val2 | recovered | stable | base_stock | service_unit_fill | 50 | -0.0217 | [-0.0301, -0.0134] | 2 / 34 |
| val2 | recovered | stable | order_up_to | shortage | 50 | -3.7689 | [-5.7456, -2.5627] | 50 / 0 |
| val2 | recovered | stable | order_up_to | avg_inventory_units | 50 | +1.0109 | [+0.7302, +1.4570] | 0 / 50 |
| val2 | recovered | stable | order_up_to | service_unit_fill | 50 | +0.1503 | [+0.1322, +0.1696] | 50 / 0 |
| val2 | recovered | uncertain | reorder_point | shortage | 50 | -2.8189 | [-6.4186, -0.8281] | 36 / 3 |
| val2 | recovered | uncertain | reorder_point | avg_inventory_units | 50 | +1.2888 | [+0.9457, +1.6967] | 2 / 48 |
| val2 | recovered | uncertain | reorder_point | service_unit_fill | 50 | +0.0535 | [+0.0376, +0.0705] | 36 / 3 |
| val2 | recovered | uncertain | periodic:1 | shortage | 50 | -2.7520 | [-6.2961, -0.7499] | 35 / 5 |
| val2 | recovered | uncertain | periodic:1 | avg_inventory_units | 50 | +1.2858 | [+0.9360, +1.6837] | 2 / 48 |
| val2 | recovered | uncertain | periodic:1 | service_unit_fill | 50 | +0.0494 | [+0.0336, +0.0666] | 35 / 5 |
| val2 | recovered | uncertain | base_stock | shortage | 50 | -1.5781 | [-3.9436, -0.2149] | 26 / 10 |
| val2 | recovered | uncertain | base_stock | avg_inventory_units | 50 | +0.8520 | [+0.5611, +1.1925] | 8 / 42 |
| val2 | recovered | uncertain | base_stock | service_unit_fill | 50 | +0.0217 | [+0.0080, +0.0353] | 26 / 10 |
| val2 | recovered | uncertain | order_up_to | shortage | 50 | -6.9036 | [-13.0465, -3.3811] | 50 / 0 |
| val2 | recovered | uncertain | order_up_to | avg_inventory_units | 50 | +2.0341 | [+1.5674, +2.6153] | 0 / 50 |
| val2 | recovered | uncertain | order_up_to | service_unit_fill | 50 | +0.1969 | [+0.1731, +0.2221] | 50 / 0 |
| val2 | recovered | uncertain_fill_only | reorder_point | shortage | 50 | -0.8200 | [-1.6026, -0.2661] | 27 / 5 |
| val2 | recovered | uncertain_fill_only | reorder_point | avg_inventory_units | 50 | +1.6688 | [+0.8991, +2.8249] | 1 / 49 |
| val2 | recovered | uncertain_fill_only | reorder_point | service_unit_fill | 50 | +0.0212 | [+0.0069, +0.0336] | 27 / 5 |
| val2 | recovered | uncertain_fill_only | periodic:1 | shortage | 50 | -0.8078 | [-1.5620, -0.2738] | 27 / 6 |
| val2 | recovered | uncertain_fill_only | periodic:1 | avg_inventory_units | 50 | +1.6584 | [+0.8903, +2.8695] | 1 / 49 |
| val2 | recovered | uncertain_fill_only | periodic:1 | service_unit_fill | 50 | +0.0205 | [+0.0067, +0.0331] | 27 / 6 |
| val2 | recovered | uncertain_fill_only | base_stock | shortage | 50 | -0.0903 | [-0.4451, +0.2451] | 16 / 17 |
| val2 | recovered | uncertain_fill_only | base_stock | avg_inventory_units | 50 | +1.1559 | [+0.5112, +2.0760] | 10 / 40 |
| val2 | recovered | uncertain_fill_only | base_stock | service_unit_fill | 50 | -0.0015 | [-0.0140, +0.0100] | 16 / 17 |
| val2 | recovered | uncertain_fill_only | order_up_to | shortage | 50 | -3.9472 | [-6.3202, -2.4604] | 48 / 0 |
| val2 | recovered | uncertain_fill_only | order_up_to | avg_inventory_units | 50 | +2.5420 | [+1.6043, +4.0256] | 0 / 50 |
| val2 | recovered | uncertain_fill_only | order_up_to | service_unit_fill | 50 | +0.1455 | [+0.1238, +0.1672] | 48 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | shortage | 50 | -1.6263 | [-3.0535, -0.6557] | 33 / 0 |
| val2 | recovered | uncertain_lead_only | reorder_point | avg_inventory_units | 50 | +0.6851 | [+0.3861, +1.1292] | 2 / 47 |
| val2 | recovered | uncertain_lead_only | reorder_point | service_unit_fill | 50 | +0.0376 | [+0.0249, +0.0528] | 33 / 0 |
| val2 | recovered | uncertain_lead_only | periodic:1 | shortage | 50 | -1.5769 | [-3.0528, -0.6020] | 30 / 3 |
| val2 | recovered | uncertain_lead_only | periodic:1 | avg_inventory_units | 50 | +0.6802 | [+0.3800, +1.1520] | 2 / 47 |
| val2 | recovered | uncertain_lead_only | periodic:1 | service_unit_fill | 50 | +0.0341 | [+0.0215, +0.0484] | 30 / 3 |
| val2 | recovered | uncertain_lead_only | base_stock | shortage | 50 | -0.9005 | [-1.9836, -0.1735] | 21 / 16 |
| val2 | recovered | uncertain_lead_only | base_stock | avg_inventory_units | 50 | +0.3711 | [+0.1320, +0.6931] | 16 / 34 |
| val2 | recovered | uncertain_lead_only | base_stock | service_unit_fill | 50 | +0.0112 | [-0.0012, +0.0258] | 21 / 16 |
| val2 | recovered | uncertain_lead_only | order_up_to | shortage | 50 | -5.3337 | [-8.4663, -3.2143] | 50 / 0 |
| val2 | recovered | uncertain_lead_only | order_up_to | avg_inventory_units | 50 | +1.6057 | [+1.0904, +2.4509] | 0 / 50 |
| val2 | recovered | uncertain_lead_only | order_up_to | service_unit_fill | 50 | +0.1770 | [+0.1588, +0.1948] | 50 / 0 |

## Failures, abstentions and the largest ZAAD losses

Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): base_stock: 1200/1200 complete, 0 infeasible, 0 abstained; gated: 1200/1200 complete, 0 infeasible, 0 abstained; order_up_to: 1200/1200 complete, 0 infeasible, 0 abstained; periodic:1: 1200/1200 complete, 0 infeasible, 0 abstained; reorder_point: 1200/1200 complete, 0 infeasible, 0 abstained

- Runs not COMPLETE: 0
- ZAAD runs that retained the incumbent proxy on at least one review: 1194 of 1200 (8267 reviews)
- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: 0

- val1/recovered/uncertain store 514 product 267: ZAAD minus base_stock = +45.608 (fill 0.888 vs 0.881, inventory 73.27 vs 22.81, retained incumbent on 3 reviews)
- val1/recovered/uncertain_fill_only store 514 product 267: ZAAD minus reorder_point = +29.844 (fill 0.974 vs 0.974, inventory 68.75 vs 15.25, retained incumbent on 3 reviews)
- val2/observed/uncertain_fill_only store 514 product 267: ZAAD minus reorder_point = +12.285 (fill 0.960 vs 0.943, inventory 28.37 vs 7.04, retained incumbent on 2 reviews)
- val1/recovered/uncertain_fill_only store 869 product 191: ZAAD minus order_up_to = +6.312 (fill 0.952 vs 0.938, inventory 7.09 vs 0.93, retained incumbent on 3 reviews)
- val2/recovered/uncertain store 230 product 580: ZAAD minus order_up_to = +5.807 (fill 0.701 vs 0.648, inventory 9.42 vs 5.30, retained incumbent on 10 reviews)
- final/recovered/uncertain store 514 product 267: ZAAD minus order_up_to = +5.798 (fill 0.954 vs 0.954, inventory 48.62 vs 17.32, retained incumbent on 4 reviews)
- val2/observed/uncertain store 102 product 467: ZAAD minus periodic:1 = +5.426 (fill 0.913 vs 0.868, inventory 3.55 vs 2.07, retained incumbent on 8 reviews)
- val2/recovered/uncertain store 102 product 467: ZAAD minus periodic:1 = +5.226 (fill 0.917 vs 0.869, inventory 3.48 vs 2.09, retained incumbent on 8 reviews)
- val2/recovered/uncertain_fill_only store 855 product 647: ZAAD minus order_up_to = +5.070 (fill 0.720 vs 0.705, inventory 4.08 vs 1.27, retained incumbent on 10 reviews)
- val1/recovered/uncertain_fill_only store 116 product 377: ZAAD minus base_stock = +5.054 (fill 0.759 vs 0.826, inventory 3.20 vs 1.23, retained incumbent on 7 reviews)
