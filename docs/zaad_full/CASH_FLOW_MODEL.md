# Dated cash flow and economic accounting

Payment terms specify currency/contracted FX, deposit fraction, balance trigger
(order/shipment/arrival), net days, financing fee and letter-of-credit fraction.
Each source quote separates procurement, freight, handling and fixed fees.

`cash_t - debt_t = cash_(t-1) - debt_(t-1) + known_receivables_t
 - other_obligations_t - contractual_payments_t - interest*debt_(t-1)`.

Cash stays above minimum liquidity and outstanding debt below the facility limit.
Letters of credit reserve cash until receipt without also becoming an expense.
Forecast sales are **not** automatically treated as collected cash. Missing critical
financial fields cause schema refusal rather than cost imputation.

Procurement expense/commitment is recognized in the economic ledger even when the
invoice is paid later. Existing prepaid amounts remain sunk; contractual cancellation
fees and remaining invoices specify the actual change. Inventory release is reported
separately from economic cost. Holding is a storage/carry accrual excluding the explicit
financing component; including interest again in its rate would double count.

Important boundary: these liquidity constraints cover the supplied planning horizon.
The evaluator reports unpaid obligations after that horizon. It does not certify that
the operator can meet all later invoices or unknown future operating obligations.
Full AP/AR reconciliation, beyond-horizon cash stress and real finance approval remain
requirements for an operator pilot; a Net90 term is not free money.
