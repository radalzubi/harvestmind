#!/bin/sh
# Workspace-adapter age-at-receipt production check (section 41): new workspace, minimal CSVs, physics on the SKU master.
BASE=https://api.zaadsupply.com; D=$(dirname "$0")
TOKEN=$(curl -s -X POST $BASE/access/start -H 'Content-Type: application/json' -d '{"sector":"produce","company":"P3 age-at-receipt check"}')
echo "start: $TOKEN" | cut -c1-160
T=$(echo "$TOKEN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
for pair in "stg_fmcg_skus:skus.csv" "stg_fmcg_suppliers:suppliers.csv" "stg_fmcg_orders:orders.csv" "stg_fmcg_purchase_orders:pos.csv" "stg_fmcg_receipts:receipts.csv" "stg_fmcg_inventory:inventory.csv"; do
  t=${pair%%:*}; f=${pair##*:}
  echo "upload $t: $(curl -s -X POST "$BASE/intake/upload/$t?anonymize=false" -H "Authorization: Bearer $T" -F "file=@$D/$f" | cut -c1-220)"
done
echo "--- request (workspace adapter, sector_mode=PRODUCE)"
curl -s "$BASE/api/zaad/network/request/from-workspace?skus=PRD-AGE-1&max_solve_seconds=5&sector_mode=PRODUCE" -H "Authorization: Bearer $T" > $D/request.json
python3 - <<'PY'
import json,sys
D=sys.argv[0] if False else None
r=json.load(open("/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/p3/agecheck/request.json"))
req=r.get("request",{}); print("skus", [(s["id"], s["shelf_life"]) for s in req.get("skus",[])], "sku_physics", req.get("sku_physics"), "warnings", r.get("build",{}).get("warnings"), "detail", r.get("detail"))
PY
echo "--- plan"
curl -s -X POST "$BASE/api/zaad/network/plan/from-workspace?skus=PRD-AGE-1&max_solve_seconds=5&sector_mode=PRODUCE&shape=network" -H "Authorization: Bearer $T" --max-time 300 > $D/plan.json
python3 - <<'PY'
import json
r=json.load(open("/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/p3/agecheck/plan.json"))
rep=r.get("report",{}); ph=rep.get("physics",{})
print("status", rep.get("status"), "approval", rep.get("approval_required"), "epo", r.get("executable_purchase_order"))
print("profiles", [(p["sku"], p["shelf_life_periods"], p["age_at_receipt_periods"], p["minimum_remaining_life_at_sale"], p["provenance"]) for p in ph.get("profiles",[])])
print("explanations", ph.get("explanations")); print("p0 purchases", [(a["source"], round(a["quantity"],1)) for a in rep.get("actions",[]) if a.get("action")=="purchase" and a.get("period")==0]); print("detail", r.get("detail"))
PY
