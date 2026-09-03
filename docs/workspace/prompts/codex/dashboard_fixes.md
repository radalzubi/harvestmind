# Codex Prompt: Dashboard Bug Fixes

Four bugs were found during code review of `dashboard.py`. All fixes have already been applied to the repo. This document records what was changed and why, and describes how to verify each fix.

Before reading further, review:

- `AGENTS.md` — project rules
- `prompts/codex/dashboard_builder.md` — original dashboard spec
- `dashboard.py` — the file that was fixed

---

## Fix 1 — Remove duplicate `st.title()` in `render_missing_outputs`

**File:** `dashboard.py`

**Problem:** `render_missing_outputs()` called `st.title("Agri-AI Operator Dashboard")` at line 70. `main()` already calls `st.title(...)` at the top of the page (line 211). When the output directory is missing, the title rendered twice — once from `render_missing_outputs`, and once it never reached `main()` because `st.stop()` follows the missing-output path.

Actually the issue is simpler: `render_missing_outputs` called `st.title` unconditionally, then `main()` also calls `st.title`. On the error path, only `render_missing_outputs` runs (due to `st.stop()`), but the title was still duplicated within that function's own rendered output context if reached through `main()`. The right fix is for `render_missing_outputs` to not render the title — `main()` owns the page title.

**Fix:** Removed `st.title("Agri-AI Operator Dashboard")` from `render_missing_outputs()`.

**Verify:** Run `streamlit run dashboard.py` with a nonexistent output directory. The page should show exactly one "Agri-AI Operator Dashboard" heading, followed by the error message and missing file list.

---

## Fix 2 — Replace deprecated `applymap` with `map`

**File:** `dashboard.py`

**Problem:** `pandas.DataFrame.Styler.applymap` was deprecated in pandas 2.1 and removed in later releases. The dashboard used it to color the Risk column:

```python
risk_table_df.style.applymap(style_risk_column, subset=["Risk"])
```

This raises a `FutureWarning` on pandas 2.1 and an `AttributeError` on newer versions.

**Fix:** Replaced `applymap` with `map`:

```python
risk_table_df.style.map(style_risk_column, subset=["Risk"])
```

The API is identical — `map` accepts the same callable and `subset` argument. No logic change.

**Verify:** Run the dashboard with a valid output directory. The Risk column should show red-highlighted cells for rows where `risk_flag = True`. No warnings should appear in the terminal.

---

## Fix 3 — Add `altair` to `requirements.txt`

**File:** `requirements.txt`

**Problem:** `dashboard.py` explicitly imports `altair` and uses `alt.Chart`, `alt.X`, `alt.Y`, `alt.XOffset`, `alt.Color`, `alt.Scale`, `alt.Legend`, `alt.Tooltip`. Altair was not listed in `requirements.txt`.

Altair is installed transitively when you install Streamlit (Streamlit depends on it), so the dashboard ran without error. But the dependency was undeclared — any environment that installs only the listed requirements would break on the chart view. This also violates the constraint in `prompts/codex/dashboard_builder.md` that requirements be explicit.

**Fix:** Added `altair` to `requirements.txt`.

```
streamlit
pandas
altair
```

**Verify:** A fresh `pip install -r requirements.txt` in a clean virtualenv should install altair explicitly. `pip show altair` should return a result.

---

## Fix 4 — Collapse redundant memo text area label

**File:** `dashboard.py`

**Problem:** The memo section had both a `st.subheader("Weekly Memo")` and a visible `"Memo"` label on the text area directly below it:

```python
st.subheader("Weekly Memo")
render_copy_button(memo_text)
st.text_area("Memo", value=memo_text, height=360)
```

The label "Memo" rendered as a visible input label just below the subheader, creating redundant text in a cramped vertical stack.

**Fix:** Set `label_visibility="collapsed"` on the text area. The label string is kept (it is required by the Streamlit API for accessibility) but hidden from the rendered UI:

```python
st.text_area("Memo", value=memo_text, height=360, label_visibility="collapsed")
```

**Verify:** The memo section should show the subheader, then the copy button, then the text area — with no "Memo" label rendered between the button and the text area.

---

## What Was Not Changed

- No pipeline code was touched (`src/` is read-only)
- No new dependencies were added beyond `altair`
- No layout or logic changes were made — these are purely correctness fixes
- `render_copy_button` was not modified; the JS clipboard injection using `json.dumps(memo_text)` is correct as written

---

## After Reviewing

If you find any additional issues while reviewing these fixes, document them in a new prompt file at `prompts/codex/` following the same format: problem, fix, verify.

Do not modify `src/`.
