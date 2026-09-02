# Dashboard Dark V1 Summary

## Branch

- `codex/dashboard-dark-v1`

## Scope Executed

- Replaced the legacy light dashboard CSS system with a dark command-center visual system.
- Rebuilt the KPI strip as a single HTML grid instead of `st.columns(5)`.
- Rethemed core charts for dark mode and added area-fill layering to weekly balance views.
- Replaced the sidebar brand mark with the AGRI-AI Syne treatment from the redesign brief.
- Removed remaining old-system inline surface colors from the memo copy control.

## Phase Outcomes

### Phase 1

- Replaced `_CSS` with the new dark token system.
- Removed the prior light background treatment.

### Phase 2

- Replaced `render_kpi_strip()` with a single `st.markdown()` KPI grid renderer.

### Phase 3

- Updated chart palette constants:
  - `_BLUE = "#40c4ff"`
  - `_GREEN = "#00e676"`
  - `_AMBER = "#ffab00"`
  - `_RED = "#ff5252"`
  - `_INK = "#e8f0eb"`
  - `_BG = "#111a14"`
- Rebuilt `render_weekly_balance_chart()` with `mark_area` + `mark_line`.
- Rebuilt `render_crop_chart()` with `mark_area` + `mark_line`.
- Updated `render_heatmap()` to the dark shortage-to-surplus scale.
- Removed remaining light table severity fills.

### Phase 4

- Replaced the sidebar heading block in `dashboard.py` with the AGRI-AI command-center brand mark.

### Phase 5

- Verified `width="stretch"` does not appear in `dashboard_views.py` or `dashboard.py`.
- Existing dataframe and chart calls already use `use_container_width=True`.

### Phase 6

- Completed the redesign checklist pass:
  - Google Fonts import present
  - Syne used for shell title
  - IBM Plex Mono used for KPI values and status pills
  - Page background is dark (`#080f0b`)
  - Red action cards include glow styling
  - Heatmap includes `#4a1010`
  - KPI strip uses one HTML block
  - Briefing card dark gradient is in the `#0d1a10` family

### Phase 7

- Ran module compilation successfully.
- Imported `dashboard.py` successfully.
- Attempted pipeline regeneration and Streamlit launch.

## Verification Results

### Passed

- `.venv/bin/python -m py_compile dashboard.py dashboard_data.py dashboard_views.py src/*.py`
- `.venv/bin/python -c "import dashboard; print('dashboard import ok')"`

### Blocked By Environment

- `.venv/bin/python -m src.main --data-dir data --output-dir output`
  - Failed because `data/order_history.csv` is missing in this workspace.
- `.venv/bin/streamlit run dashboard.py --server.headless true --server.port 8501`
  - Failed because the sandbox does not permit binding a local TCP port (`PermissionError: [Errno 1] Operation not permitted`).

## Commit Sequence

- `8501f88` `style(ui): Replace dashboard CSS with dark system`
- `4ecb5f1` `style(ui): Render KPI strip as unified grid`
- `512c6a0` `style(charts): Rebuild dashboard visuals for dark mode`
- `6e96496` `style(shell): Replace sidebar brand mark`
- `9a53b32` `style(ui): Finalize dark surface cleanup`

## Notes

- No changes were made to `dashboard_data.py`.
- No new packages were added.
- The redesign stays within the existing module structure and data contracts.
