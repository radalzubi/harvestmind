# Codex Prompt: Dashboard Bug Fixes Round 2

Additional issues were found while verifying `dashboard.py` end-to-end. This document records what was changed, why it mattered, and how to verify each correction.

Before reading further, review:

- `AGENTS.md` — project rules
- `prompts/codex/dashboard_builder.md` — original dashboard spec
- `prompts/codex/dashboard_fixes.md` — first review pass
- `dashboard.py` — current dashboard implementation
- `requirements.txt` — allowed dependencies

---

## Fix 5 — Remove deprecated `use_container_width`

**File:** `dashboard.py`

**Problem:** The dashboard still used `use_container_width=True` on `st.dataframe` and `st.altair_chart`. Streamlit 1.55 emits a deprecation warning for this argument and recommends `width="stretch"` instead. The app rendered, but every run printed warnings to the terminal. That means the dashboard did not run cleanly end-to-end.

**Fix:** Replaced all `use_container_width=True` calls with `width="stretch"`.

Examples:

```python
st.dataframe(..., width="stretch", hide_index=True)
st.altair_chart(chart, width="stretch")
```

**Verify:** Run the dashboard with a valid output directory. The app should render normally and the terminal should no longer print:

```text
Please replace `use_container_width` with `width`.
```

---

## Fix 6 — Restore the original dependency contract

**File:** `requirements.txt`

**Problem:** The first review pass added `altair` explicitly to `requirements.txt`. That conflicts with `prompts/codex/dashboard_builder.md`, which says the file should contain only `streamlit` and `pandas`.

This is not a runtime blocker because Streamlit already installs Altair transitively, but it is still a contract violation. The dashboard brief was explicit about dependency scope, and verification should enforce that scope.

**Fix:** Removed `altair` from `requirements.txt`.

Final file:

```text
streamlit
pandas
```

**Verify:** Create a clean virtual environment and run:

```bash
pip install -r requirements.txt
python -c "import streamlit, pandas, altair"
```

The import should still succeed because Streamlit brings Altair as a dependency, while the repo now matches the original two-dependency requirement.

---

## What Was Not Changed

- No code in `src/` was modified
- No dashboard restructuring was introduced
- No pages directory was added
- No new dependencies were added

---

## After Reviewing

If further dashboard issues appear, document them in another prompt file in `prompts/codex/` using the same format: problem, fix, verify.
