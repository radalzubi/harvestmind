.PHONY: setup test backtest serve dashboard roi-report demo clean lint

PYTHON := python3
PIP    := python3 -m pip

setup:
	@echo "── Installing dependencies ───────────────────────────────"
	$(PIP) install -e ".[dev]"
	@echo "── Setting up database ───────────────────────────────────"
	$(PYTHON) scripts/setup_db.py --seeds
	@echo "── Generating synthetic demo data ────────────────────────"
	$(PYTHON) synthetic/generate_pilot_dataset.py
	@echo "── Setup complete. Run 'make demo' to verify. ────────────"

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov:
	$(PYTHON) -m pytest tests/ --tb=short --cov=. --cov-report=term-missing

backtest:
	$(PYTHON) scripts/run_backtest.py --train-weeks 52 --horizon 4 --step 4 --scenarios 30

serve:
	uvicorn api.main:app --reload --port 8000 --log-level info

dashboard:
	streamlit run dashboard/app.py --server.port 8501

roi-report:
	$(PYTHON) scripts/generate_roi_report.py

demo:
	$(PYTHON) scripts/demo_run.py

lint:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m black . --check

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f harvestmind.duckdb harvestmind.duckdb.wal
	rm -rf outputs/demo_backtest_*

help:
	@echo "HarvestMind — Available commands:"
	@echo "  make setup       Install deps, init DB, generate synthetic data"
	@echo "  make test        Run full test suite with coverage"
	@echo "  make backtest    Run rolling-origin backtest on synthetic_indiana_hub"
	@echo "  make serve       Start FastAPI server on :8000"
	@echo "  make dashboard   Start Streamlit dashboard on :8501"
	@echo "  make roi-report  Generate PDF partner ROI report"
	@echo "  make demo        Full end-to-end demo (< 90s)"
	@echo "  make lint        Run ruff + black checks"
	@echo "  make clean       Remove generated files and DB"
