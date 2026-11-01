# Walmart M5 Experiment B (coupled purchasing) results: `coupled_coupled`

Commit `1bb1915f37e75e72845de52f791cf326cc00864c`, coupling `coupled` (hash `5fdfecaa4a23`), selection `8b6067be83a4`; 360 runs over 10 store groups, 360 complete, 0 not complete; wall 4567 s. Every figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms (fixed order cost, minimum order value, pallet cap, case lots) on OBSERVED Walmart sales; none is a realized saving. Groups are the replication unit (at most ten), so the intervals are wide by construction.

## Group table (mean over completed groups)

| window | scenario | policy | complete/runs | physical failures | abstained | continuation | realized | purchase | ordering | carrying | shortage | fill | items < target | min item fill | order-weeks | lines/order-week | end stock | cancelled OW | cut OW | ZAAD own share | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 10/10 | 0 | 0 | 2420.04 | 2536.41 | 2038.94 | 380.00 | 22.36 | 405.17 | 0.894 | 2.6 | 0.558 | 9.5 | 1.96 | 202.6 | 0.6 | 18.5 |  | 0.1 |
| final | fill_only | gated | 10/10 | 0 | 0 | 2362.42 | 2482.19 | 2167.56 | 368.00 | 25.88 | 243.84 | 0.905 | 2.4 | 0.596 | 9.2 | 2.20 | 210.0 | 0.0 | 0.0 | 0.15 | 69.9 |
| final | fill_only | periodic:1 | 10/10 | 0 | 0 | 2465.68 | 2530.56 | 1664.17 | 492.00 | 9.12 | 411.43 | 0.848 | 3.6 | 0.603 | 12.3 | 2.52 | 76.2 | 0.0 | 8.5 |  | 0.1 |
| final | fill_only | reorder_point | 10/10 | 0 | 0 | 2461.45 | 2525.52 | 1657.53 | 484.00 | 8.83 | 417.62 | 0.831 | 3.7 | 0.595 | 12.1 | 2.46 | 75.3 | 0.0 | 8.3 |  | 0.1 |
| final | mild_lead | economic_lot | 10/10 | 0 | 0 | 2180.55 | 2300.84 | 1777.47 | 336.00 | 25.15 | 484.80 | 0.852 | 3.7 | 0.509 | 8.4 | 1.85 | 225.5 | 0.4 | 18.4 |  | 0.1 |
| final | mild_lead | gated | 10/10 | 0 | 0 | 2154.88 | 2304.43 | 2071.89 | 348.00 | 29.54 | 321.86 | 0.879 | 3.7 | 0.645 | 8.7 | 2.11 | 247.8 | 0.0 | 0.0 | 0.25 | 29.3 |
| final | mild_lead | periodic:1 | 10/10 | 0 | 0 | 2303.50 | 2374.26 | 1441.50 | 476.00 | 9.70 | 521.31 | 0.803 | 4.2 | 0.556 | 11.9 | 2.28 | 83.6 | 0.0 | 7.5 |  | 0.1 |
| final | mild_lead | reorder_point | 10/10 | 0 | 0 | 2292.96 | 2362.26 | 1438.51 | 468.00 | 9.76 | 513.45 | 0.797 | 4.3 | 0.556 | 11.7 | 2.27 | 84.8 | 0.0 | 7.1 |  | 0.1 |
| final | stable | economic_lot | 10/10 | 0 | 0 | 2160.62 | 2271.19 | 1792.96 | 352.00 | 26.04 | 371.99 | 0.900 | 2.5 | 0.564 | 8.8 | 1.87 | 230.5 | 0.5 | 18.4 |  | 0.1 |
| final | stable | gated | 10/10 | 0 | 0 | 2098.18 | 2224.06 | 2039.06 | 348.00 | 33.19 | 145.85 | 0.939 | 2.3 | 0.772 | 8.7 | 2.28 | 264.5 | 0.0 | 0.0 | 0.29 | 63.3 |
| final | stable | periodic:1 | 10/10 | 0 | 0 | 2267.23 | 2334.81 | 1535.97 | 488.00 | 9.90 | 360.98 | 0.864 | 3.2 | 0.596 | 12.2 | 2.40 | 84.8 | 0.0 | 7.8 |  | 0.1 |
| final | stable | reorder_point | 10/10 | 0 | 0 | 2258.94 | 2326.57 | 1536.49 | 480.00 | 10.04 | 359.90 | 0.852 | 3.4 | 0.608 | 12.0 | 2.39 | 87.2 | 0.0 | 7.6 |  | 0.1 |
| val1 | fill_only | economic_lot | 10/10 | 0 | 0 | 1587.87 | 1668.02 | 1315.95 | 296.00 | 24.86 | 208.38 | 0.854 | 2.1 | 0.509 | 7.4 | 1.78 | 210.4 | 2.1 | 18.8 |  | 0.1 |
| val1 | fill_only | gated | 10/10 | 0 | 0 | 1619.74 | 1706.03 | 1384.61 | 320.00 | 25.25 | 201.92 | 0.862 | 2.2 | 0.610 | 8.0 | 1.87 | 196.9 | 0.0 | 0.0 | 0.18 | 57.2 |
| val1 | fill_only | periodic:1 | 10/10 | 0 | 0 | 1719.18 | 1773.19 | 1051.71 | 444.00 | 12.97 | 311.74 | 0.822 | 2.8 | 0.578 | 11.1 | 2.14 | 90.4 | 1.2 | 6.6 |  | 0.1 |
| val1 | fill_only | reorder_point | 10/10 | 0 | 0 | 1715.71 | 1768.90 | 1044.35 | 440.00 | 12.63 | 315.17 | 0.820 | 2.8 | 0.573 | 11.0 | 2.08 | 88.0 | 1.4 | 6.4 |  | 0.1 |
| val1 | mild_lead | economic_lot | 10/10 | 0 | 0 | 1464.02 | 1557.52 | 1239.00 | 272.00 | 25.21 | 273.89 | 0.825 | 2.8 | 0.482 | 6.8 | 1.70 | 204.7 | 1.5 | 18.7 |  | 0.1 |
| val1 | mild_lead | gated | 10/10 | 0 | 0 | 1477.55 | 1572.80 | 1279.31 | 288.00 | 27.91 | 247.79 | 0.845 | 2.7 | 0.560 | 7.2 | 2.00 | 217.3 | 0.0 | 0.0 | 0.25 | 22.1 |
| val1 | mild_lead | periodic:1 | 10/10 | 0 | 0 | 1609.84 | 1666.77 | 950.41 | 420.00 | 12.74 | 345.33 | 0.811 | 3.1 | 0.569 | 10.5 | 2.05 | 86.6 | 1.4 | 5.1 |  | 0.1 |
| val1 | mild_lead | reorder_point | 10/10 | 0 | 0 | 1609.51 | 1664.83 | 937.97 | 420.00 | 12.01 | 348.24 | 0.808 | 3.3 | 0.568 | 10.5 | 1.97 | 84.8 | 1.3 | 5.3 |  | 0.1 |
| val1 | stable | economic_lot | 10/10 | 0 | 0 | 1463.19 | 1560.96 | 1304.13 | 284.00 | 27.75 | 219.04 | 0.852 | 2.3 | 0.529 | 7.1 | 1.64 | 225.1 | 1.6 | 18.9 |  | 0.1 |
| val1 | stable | gated | 10/10 | 0 | 0 | 1479.23 | 1582.92 | 1374.08 | 300.00 | 27.63 | 201.08 | 0.862 | 2.3 | 0.616 | 7.5 | 1.90 | 216.0 | 0.0 | 0.0 | 0.18 | 35.1 |
| val1 | stable | periodic:1 | 10/10 | 0 | 0 | 1601.46 | 1657.24 | 999.85 | 436.00 | 14.11 | 261.74 | 0.855 | 2.8 | 0.611 | 10.9 | 2.12 | 97.7 | 1.4 | 5.1 |  | 0.1 |
| val1 | stable | reorder_point | 10/10 | 0 | 0 | 1590.91 | 1642.08 | 975.84 | 428.00 | 13.56 | 257.61 | 0.857 | 2.8 | 0.626 | 10.7 | 2.03 | 96.6 | 1.4 | 5.1 |  | 0.1 |
| val2 | fill_only | economic_lot | 10/10 | 0 | 0 | 1900.83 | 2006.89 | 1719.88 | 376.00 | 25.25 | 182.62 | 0.897 | 2.6 | 0.531 | 9.4 | 1.90 | 228.3 | 2.8 | 17.2 |  | 0.1 |
| val2 | fill_only | gated | 10/10 | 0 | 0 | 1903.94 | 2007.11 | 1721.83 | 384.00 | 24.11 | 160.21 | 0.908 | 2.5 | 0.596 | 9.6 | 2.06 | 220.2 | 0.0 | 0.0 | 0.15 | 94.7 |
| val2 | fill_only | periodic:1 | 10/10 | 0 | 0 | 2015.50 | 2069.10 | 1276.16 | 496.00 | 8.54 | 330.57 | 0.836 | 3.6 | 0.548 | 12.4 | 2.37 | 71.4 | 0.1 | 9.8 |  | 0.1 |
| val2 | fill_only | reorder_point | 10/10 | 0 | 0 | 2003.90 | 2056.48 | 1264.20 | 484.00 | 8.10 | 337.96 | 0.828 | 3.8 | 0.510 | 12.1 | 2.33 | 69.7 | 0.0 | 10.0 |  | 0.1 |
| val2 | mild_lead | economic_lot | 10/10 | 0 | 0 | 1748.57 | 1864.99 | 1598.61 | 340.00 | 27.52 | 248.51 | 0.868 | 3.4 | 0.552 | 8.5 | 1.85 | 207.7 | 3.1 | 17.4 |  | 0.1 |
| val2 | mild_lead | gated | 10/10 | 0 | 0 | 1759.88 | 1868.77 | 1560.32 | 360.00 | 27.80 | 228.40 | 0.880 | 3.3 | 0.602 | 9.0 | 2.02 | 199.0 | 0.0 | 0.0 | 0.28 | 32.6 |
| val2 | mild_lead | periodic:1 | 10/10 | 0 | 0 | 1917.56 | 1980.90 | 1136.11 | 484.00 | 8.48 | 438.17 | 0.769 | 4.0 | 0.475 | 12.1 | 2.28 | 71.4 | 0.1 | 9.8 |  | 0.1 |
| val2 | mild_lead | reorder_point | 10/10 | 0 | 0 | 1905.41 | 1967.28 | 1127.33 | 472.00 | 8.41 | 438.62 | 0.770 | 4.0 | 0.475 | 11.8 | 2.18 | 71.3 | 0.1 | 9.5 |  | 0.1 |
| val2 | stable | economic_lot | 10/10 | 0 | 0 | 1722.72 | 1825.96 | 1572.37 | 344.00 | 27.19 | 163.38 | 0.901 | 2.6 | 0.562 | 8.6 | 1.91 | 215.5 | 3.2 | 17.1 |  | 0.1 |
| val2 | stable | gated | 10/10 | 0 | 0 | 1755.41 | 1876.89 | 1697.82 | 372.00 | 27.05 | 158.78 | 0.910 | 2.7 | 0.610 | 9.3 | 2.08 | 203.9 | 0.0 | 0.0 | 0.26 | 49.0 |
| val2 | stable | periodic:1 | 10/10 | 0 | 0 | 1877.93 | 1934.78 | 1211.85 | 492.00 | 9.49 | 278.43 | 0.854 | 3.7 | 0.556 | 12.3 | 2.31 | 80.4 | 0.1 | 9.3 |  | 0.1 |
| val2 | stable | reorder_point | 10/10 | 0 | 0 | 1853.20 | 1909.70 | 1209.71 | 468.00 | 9.08 | 277.89 | 0.855 | 3.8 | 0.545 | 11.7 | 2.28 | 78.3 | 0.1 | 9.2 |  | 0.1 |

## Paired comparison, ZAAD minus baseline per group (continuation cost; negative favours ZAAD; groups where both completed)

| window | scenario | baseline | groups | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |
|---|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | 10 | -57.63 | [-101.40, -15.07] | [-136.80, -9.67] | 5 / 0 / 5 | 0.062 |
| final | fill_only | reorder_point | 10 | -99.03 | [-139.85, -56.27] | [-160.87, -33.95] | 7 / 3 / 0 | 0.344 |
| final | fill_only | periodic:1 | 10 | -103.26 | [-147.82, -59.17] | [-168.41, -33.69] | 7 / 3 / 0 | 0.344 |
| final | mild_lead | economic_lot | 10 | -25.67 | [-77.78, +20.31] | [-113.48, +36.33] | 5 / 4 / 1 | 1.0 |
| final | mild_lead | reorder_point | 10 | -138.09 | [-158.17, -117.96] | [-167.42, -108.08] | 10 / 0 / 0 | 0.002 |
| final | mild_lead | periodic:1 | 10 | -148.62 | [-168.57, -128.76] | [-178.05, -117.36] | 10 / 0 / 0 | 0.002 |
| final | stable | economic_lot | 10 | -62.44 | [-119.78, -8.11] | [-162.70, +5.69] | 6 / 3 / 1 | 0.508 |
| final | stable | reorder_point | 10 | -160.75 | [-183.32, -137.79] | [-193.72, -124.21] | 10 / 0 / 0 | 0.002 |
| final | stable | periodic:1 | 10 | -169.05 | [-192.42, -145.44] | [-202.75, -132.12] | 10 / 0 / 0 | 0.002 |
| val1 | fill_only | economic_lot | 10 | +31.87 | [+5.20, +61.34] | [-2.57, +81.91] | 2 / 7 / 1 | 0.18 |
| val1 | fill_only | reorder_point | 10 | -95.97 | [-140.61, -50.58] | [-165.59, -26.99] | 9 / 1 / 0 | 0.021 |
| val1 | fill_only | periodic:1 | 10 | -99.45 | [-145.09, -52.86] | [-167.21, -29.63] | 9 / 1 / 0 | 0.021 |
| val1 | mild_lead | economic_lot | 10 | +13.52 | [+4.38, +22.40] | [-0.11, +27.19] | 3 / 4 / 3 | 1.0 |
| val1 | mild_lead | reorder_point | 10 | -131.97 | [-154.61, -108.86] | [-167.22, -96.97] | 10 / 0 / 0 | 0.002 |
| val1 | mild_lead | periodic:1 | 10 | -132.30 | [-154.63, -109.67] | [-165.80, -97.29] | 10 / 0 / 0 | 0.002 |
| val1 | stable | economic_lot | 10 | +16.05 | [-5.17, +36.86] | [-15.82, +46.12] | 3 / 6 / 1 | 0.508 |
| val1 | stable | reorder_point | 10 | -111.68 | [-142.95, -80.21] | [-159.50, -66.25] | 10 / 0 / 0 | 0.002 |
| val1 | stable | periodic:1 | 10 | -122.23 | [-153.95, -90.92] | [-173.20, -75.47] | 10 / 0 / 0 | 0.002 |
| val2 | fill_only | economic_lot | 10 | +3.11 | [-12.94, +19.25] | [-22.20, +27.40] | 4 / 4 / 2 | 1.0 |
| val2 | fill_only | reorder_point | 10 | -99.96 | [-142.32, -60.35] | [-165.97, -39.65] | 9 / 1 / 0 | 0.021 |
| val2 | fill_only | periodic:1 | 10 | -111.56 | [-151.42, -72.82] | [-173.09, -54.44] | 10 / 0 / 0 | 0.002 |
| val2 | mild_lead | economic_lot | 10 | +11.32 | [-0.44, +21.82] | [-6.45, +27.04] | 3 / 6 / 1 | 0.508 |
| val2 | mild_lead | reorder_point | 10 | -145.53 | [-164.48, -126.43] | [-175.62, -116.97] | 10 / 0 / 0 | 0.002 |
| val2 | mild_lead | periodic:1 | 10 | -157.68 | [-184.29, -133.42] | [-199.69, -121.94] | 10 / 0 / 0 | 0.002 |
| val2 | stable | economic_lot | 10 | +32.68 | [+17.30, +48.00] | [+10.16, +56.36] | 3 / 6 / 1 | 0.508 |
| val2 | stable | reorder_point | 10 | -97.80 | [-113.26, -82.30] | [-121.42, -74.53] | 10 / 0 / 0 | 0.002 |
| val2 | stable | periodic:1 | 10 | -122.52 | [-146.96, -100.05] | [-161.08, -90.31] | 10 / 0 / 0 | 0.002 |

## Paired comparison on fill and inventory (ZAAD minus baseline)

| window | scenario | baseline | metric | groups | mean diff | 95 % bootstrap | ZAAD better / worse |
|---|---|---|---|---|---|---|---|
| final | fill_only | economic_lot | shortage | 10 | -161.3313 | [-482.7293, +0.0000] | 2 / 0 |
| final | fill_only | economic_lot | avg_inventory_units | 10 | +7.4422 | [-2.7029, +19.8946] | 1 / 3 |
| final | fill_only | economic_lot | service_unit_fill | 10 | +0.0107 | [+0.0000, +0.0304] | 2 / 0 |
| final | fill_only | reorder_point | shortage | 10 | -173.7790 | [-325.2048, -53.7595] | 9 / 1 |
| final | fill_only | reorder_point | avg_inventory_units | 10 | +134.6929 | [+60.3286, +248.1821] | 0 / 10 |
| final | fill_only | reorder_point | service_unit_fill | 10 | +0.0741 | [+0.0324, +0.1254] | 10 / 0 |
| final | fill_only | periodic:1 | shortage | 10 | -167.5865 | [-320.2592, -45.0729] | 9 / 1 |
| final | fill_only | periodic:1 | avg_inventory_units | 10 | +133.8036 | [+59.8235, +244.6771] | 0 / 10 |
| final | fill_only | periodic:1 | service_unit_fill | 10 | +0.0570 | [+0.0200, +0.1097] | 10 / 0 |
| final | mild_lead | economic_lot | shortage | 10 | -162.9435 | [-421.5920, -5.0890] | 5 / 0 |
| final | mild_lead | economic_lot | avg_inventory_units | 10 | +22.2811 | [-0.8542, +59.6915] | 2 / 6 |
| final | mild_lead | economic_lot | service_unit_fill | 10 | +0.0270 | [+0.0016, +0.0598] | 4 / 1 |
| final | mild_lead | reorder_point | shortage | 10 | -191.5882 | [-313.8067, -80.4414] | 9 / 0 |
| final | mild_lead | reorder_point | avg_inventory_units | 10 | +162.9447 | [+66.8985, +309.2719] | 0 / 10 |
| final | mild_lead | reorder_point | service_unit_fill | 10 | +0.0824 | [+0.0395, +0.1337] | 9 / 0 |
| final | mild_lead | periodic:1 | shortage | 10 | -199.4522 | [-318.1679, -88.5658] | 9 / 0 |
| final | mild_lead | periodic:1 | avg_inventory_units | 10 | +164.1754 | [+68.1987, +306.9298] | 0 / 10 |
| final | mild_lead | periodic:1 | service_unit_fill | 10 | +0.0765 | [+0.0361, +0.1267] | 9 / 0 |
| final | stable | economic_lot | shortage | 10 | -226.1426 | [-537.4178, -14.1045] | 6 / 2 |
| final | stable | economic_lot | avg_inventory_units | 10 | +33.9240 | [+8.6034, +60.4912] | 2 / 6 |
| final | stable | economic_lot | service_unit_fill | 10 | +0.0399 | [+0.0005, +0.0926] | 5 / 3 |
| final | stable | reorder_point | shortage | 10 | -214.0492 | [-385.3579, -73.6199] | 9 / 1 |
| final | stable | reorder_point | avg_inventory_units | 10 | +177.2692 | [+92.5243, +308.6800] | 0 / 10 |
| final | stable | reorder_point | service_unit_fill | 10 | +0.0874 | [+0.0394, +0.1408] | 9 / 1 |
| final | stable | periodic:1 | shortage | 10 | -215.1282 | [-381.4169, -67.7284] | 9 / 1 |
| final | stable | periodic:1 | avg_inventory_units | 10 | +179.6538 | [+92.3201, +310.9884] | 0 / 10 |
| final | stable | periodic:1 | service_unit_fill | 10 | +0.0760 | [+0.0272, +0.1330] | 8 / 2 |
| val1 | fill_only | economic_lot | shortage | 10 | -6.4567 | [-27.8970, +19.9611] | 5 / 1 |
| val1 | fill_only | economic_lot | avg_inventory_units | 10 | -13.4708 | [-46.0990, +7.8737] | 5 / 4 |
| val1 | fill_only | economic_lot | service_unit_fill | 10 | +0.0077 | [-0.0173, +0.0335] | 5 / 1 |
| val1 | fill_only | reorder_point | shortage | 10 | -113.2488 | [-196.6860, -39.0917] | 8 / 1 |
| val1 | fill_only | reorder_point | avg_inventory_units | 10 | +108.9390 | [+50.7159, +190.6608] | 0 / 10 |
| val1 | fill_only | reorder_point | service_unit_fill | 10 | +0.0412 | [+0.0063, +0.0802] | 7 / 2 |
| val1 | fill_only | periodic:1 | shortage | 10 | -109.8186 | [-191.9119, -37.0286] | 7 / 1 |
| val1 | fill_only | periodic:1 | avg_inventory_units | 10 | +106.4963 | [+49.5913, +189.2234] | 0 / 10 |
| val1 | fill_only | periodic:1 | service_unit_fill | 10 | +0.0398 | [+0.0060, +0.0811] | 6 / 2 |
| val1 | mild_lead | economic_lot | shortage | 10 | -26.1001 | [-52.8191, -4.6227] | 5 / 0 |
| val1 | mild_lead | economic_lot | avg_inventory_units | 10 | +12.5672 | [-7.4695, +35.3722] | 3 / 4 |
| val1 | mild_lead | economic_lot | service_unit_fill | 10 | +0.0199 | [+0.0011, +0.0527] | 5 / 0 |
| val1 | mild_lead | reorder_point | shortage | 10 | -100.4441 | [-181.6283, -25.7647] | 7 / 2 |
| val1 | mild_lead | reorder_point | avg_inventory_units | 10 | +132.5488 | [+57.3765, +228.8222] | 1 / 9 |
| val1 | mild_lead | reorder_point | service_unit_fill | 10 | +0.0369 | [-0.0021, +0.0793] | 8 / 1 |
| val1 | mild_lead | periodic:1 | shortage | 10 | -97.5400 | [-181.1824, -22.3538] | 6 / 3 |
| val1 | mild_lead | periodic:1 | avg_inventory_units | 10 | +130.6861 | [+53.4442, +230.8653] | 1 / 9 |
| val1 | mild_lead | periodic:1 | service_unit_fill | 10 | +0.0344 | [-0.0074, +0.0799] | 7 / 2 |
| val1 | stable | economic_lot | shortage | 10 | -17.9592 | [-36.5083, -2.0591] | 5 / 0 |
| val1 | stable | economic_lot | avg_inventory_units | 10 | -9.0675 | [-27.4909, +4.8710] | 5 / 3 |
| val1 | stable | economic_lot | service_unit_fill | 10 | +0.0104 | [+0.0017, +0.0207] | 5 / 0 |
| val1 | stable | reorder_point | shortage | 10 | -56.5350 | [-144.3512, +17.1398] | 6 / 2 |
| val1 | stable | reorder_point | avg_inventory_units | 10 | +119.4858 | [+59.4188, +195.4662] | 0 / 10 |
| val1 | stable | reorder_point | service_unit_fill | 10 | +0.0053 | [-0.0576, +0.0573] | 6 / 2 |
| val1 | stable | periodic:1 | shortage | 10 | -60.6569 | [-147.4711, +16.6323] | 5 / 3 |
| val1 | stable | periodic:1 | avg_inventory_units | 10 | +118.3154 | [+57.3613, +192.3989] | 0 / 10 |
| val1 | stable | periodic:1 | service_unit_fill | 10 | +0.0072 | [-0.0557, +0.0608] | 5 / 3 |
| val2 | fill_only | economic_lot | shortage | 10 | -22.4137 | [-48.5395, -3.0235] | 5 / 1 |
| val2 | fill_only | economic_lot | avg_inventory_units | 10 | -8.1687 | [-22.1634, +3.0571] | 5 / 3 |
| val2 | fill_only | economic_lot | service_unit_fill | 10 | +0.0112 | [-0.0006, +0.0272] | 5 / 1 |
| val2 | fill_only | reorder_point | shortage | 10 | -177.7438 | [-294.4533, -66.4163] | 8 / 2 |
| val2 | fill_only | reorder_point | avg_inventory_units | 10 | +150.4987 | [+67.1339, +271.7126] | 0 / 10 |
| val2 | fill_only | reorder_point | service_unit_fill | 10 | +0.0799 | [+0.0382, +0.1256] | 8 / 2 |
| val2 | fill_only | periodic:1 | shortage | 10 | -170.3603 | [-297.6226, -57.0204] | 7 / 3 |
| val2 | fill_only | periodic:1 | avg_inventory_units | 10 | +148.7384 | [+64.9786, +272.0101] | 0 / 10 |
| val2 | fill_only | periodic:1 | service_unit_fill | 10 | +0.0715 | [+0.0299, +0.1183] | 8 / 2 |
| val2 | mild_lead | economic_lot | shortage | 10 | -20.1030 | [-49.4919, +0.4830] | 4 / 1 |
| val2 | mild_lead | economic_lot | avg_inventory_units | 10 | -8.7077 | [-37.5846, +12.1700] | 2 / 5 |
| val2 | mild_lead | economic_lot | service_unit_fill | 10 | +0.0113 | [-0.0011, +0.0281] | 4 / 1 |
| val2 | mild_lead | reorder_point | shortage | 10 | -210.2167 | [-337.4924, -91.0236] | 8 / 2 |
| val2 | mild_lead | reorder_point | avg_inventory_units | 10 | +127.7065 | [+81.1729, +176.1323] | 0 / 10 |
| val2 | mild_lead | reorder_point | service_unit_fill | 10 | +0.1097 | [+0.0542, +0.1694] | 8 / 2 |
| val2 | mild_lead | periodic:1 | shortage | 10 | -209.7607 | [-334.1910, -95.8559] | 8 / 2 |
| val2 | mild_lead | periodic:1 | avg_inventory_units | 10 | +127.5734 | [+81.4905, +175.2109] | 0 / 10 |
| val2 | mild_lead | periodic:1 | service_unit_fill | 10 | +0.1104 | [+0.0540, +0.1708] | 8 / 2 |
| val2 | stable | economic_lot | shortage | 10 | -4.5989 | [-19.2572, +9.8390] | 3 / 2 |
| val2 | stable | economic_lot | avg_inventory_units | 10 | -11.6172 | [-43.8907, +11.7707] | 4 / 5 |
| val2 | stable | economic_lot | service_unit_fill | 10 | +0.0090 | [-0.0011, +0.0221] | 3 / 2 |
| val2 | stable | reorder_point | shortage | 10 | -119.1008 | [-239.3693, -29.1996] | 7 / 2 |
| val2 | stable | reorder_point | avg_inventory_units | 10 | +125.5396 | [+80.7426, +172.1248] | 0 / 10 |
| val2 | stable | reorder_point | service_unit_fill | 10 | +0.0550 | [+0.0160, +0.1014] | 7 / 1 |
| val2 | stable | periodic:1 | shortage | 10 | -119.6412 | [-241.4019, -25.1708] | 7 / 3 |
| val2 | stable | periodic:1 | avg_inventory_units | 10 | +123.4704 | [+79.2897, +168.8464] | 0 / 10 |
| val2 | stable | periodic:1 | service_unit_fill | 10 | +0.0563 | [+0.0181, +0.1020] | 7 / 2 |

## Completion and constraint breaches

Completion by policy (a run stops at the first review whose order breaks a shared constraint in settlement, PHYSICAL_FAILURE, or on which ZAAD abstains): economic_lot: 90/90 complete, 0 physical failures, 0 abstained, 0 infeasible; gated: 90/90 complete, 0 physical failures, 0 abstained, 0 infeasible; periodic:1: 90/90 complete, 0 physical failures, 0 abstained, 0 infeasible; reorder_point: 90/90 complete, 0 physical failures, 0 abstained, 0 infeasible

