# Contributing

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python3 scripts/setup_db.py
python3 -m pytest tests/ -q
```

Frontend: `cd web && npm install && npm run build`. Streamlit:
`streamlit run dashboard/app.py`.

## The gate

`./scripts/commercial_validate.sh` runs lint on the files this work owns,
mypy (reported), bandit (must be zero at medium+), pip-audit, a secret
scan, the full test suite with coverage, the frontend build, and the
real-data calibration checks, then writes `artifacts/commercial_readiness.json`.
`--full` adds the simulation matrices. `make commercial-validate` is the
same thing.

## Rules that are not negotiable

- A policy is credited with what arrives, never with what it ordered.
- One settlement function for every policy in a comparison.
- No outcome-based fold filtering. Stratify; do not remove.
- Scenarios come from the training window only. Realised values enter
  settlement only.
- Baselines must be competent. A straw man proves nothing.
- Synthetic data is labelled `SYNTHETIC CALIBRATED` or `SYNTHETIC
  ILLUSTRATIVE`. A backtest is a "backtested" or "simulated" improvement,
  never "savings".
- A test that asserts `True` is deleted on sight.
- String-built SQL carries a per-line `nosec B608` with its justification,
  or it does not merge.

## Commits

`type(scope): what changed and why`, with the reasoning in the body. See
`git log` for the house style.
