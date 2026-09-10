# Multi-echelon planning

The live model jointly balances SKU/lot cohorts at central DCs, regional DCs,
branches and warehouses. Purchases may arrive at an upstream DC, then move on
approved transfer arcs. Destination-specific holding, receiving limits, loss,
lead and transport cost influence placement. All sites share resource/cash
constraints; they are not optimized as independent unconstrained suppliers.

This is direct multi-echelon network MPC, not an implementation of the strategic
guaranteed-service safety-stock algorithm. A standard independent base-stock
benchmark is supplied, but a separately calibrated commercial GS-MEIO benchmark
has not been run. [Graves and Willems](https://pubsonline.informs.org/doi/abs/10.1287/msom.2.1.68.23267)
assume bounded demand and guaranteed interstage service; those are consequential
assumptions during a route outage.

The transfer fixture demonstrates repositioning existing upstream excess instead
of buying externally. That is one mechanism; do not add “MEIO value” and “transfer
value” from the same fixture as two independent savings. Broader risk-pooling
value needs diverse customer locations, correlated demand and real operating data.
