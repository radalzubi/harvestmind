# Codex: Agri-AI Dashboard Redesign — Radical Dark Command Center

## Your Mandate

This is a radical visual redesign of `dashboard_views.py`.

You are NOT patching problems.
You are NOT making incremental improvements.
You are REPLACING the entire visual system with a dark, high-contrast, analytically serious command center.

The result must look like a purpose-built supply planning instrument — not a Streamlit app.

---

## Required Reading — Complete Before Writing Any Code

1. `AGENTS.md`
2. `docs/product/dashboard_vision.md`
3. `docs/product/ui_principles.md`
4. `docs/product/information_architecture.md`
5. `docs/product/uiux_redesign_brief.md` ← the complete specification for this redesign
6. `dashboard_views.py` — the file you will rewrite
7. `dashboard_data.py` — read only; understand all data contracts
8. `dashboard.py` — read only; understand orchestration
9. `.claude/agents/design-system-enforcer.md` — use during implementation
10. `.claude/agents/analytics-dashboard-designer.md` — use for chart decisions
11. `.claude/agents/uiux-critic.md` — use for self-review before committing

---

## Branch Instructions

Create branch: `codex/dashboard-dark-v1`

Commit at the end of each phase. Do not push to main.

---

## Phase 1 — Gut the Current CSS System

Open `dashboard_views.py`. Find the `_CSS` string variable.

**Replace the entire contents of `_CSS`** with the new dark system below. Do not patch. Replace completely.

```css
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;500;700&family=DM+Sans:wght@400;500;600&display=swap');

:root {
    /* Backgrounds */
    --bg:           #080f0b;
    --surface:      #111a14;
    --surface-mid:  #182314;
    --surface-hi:   #1e2d1e;

    /* Signal colors */
    --green:        #00e676;
    --amber:        #ffab00;
    --red:          #ff5252;
    --blue:         #40c4ff;

    /* Signal backgrounds */
    --green-bg:     rgba(0, 230, 118, 0.08);
    --amber-bg:     rgba(255, 171, 0, 0.08);
    --red-bg:       rgba(255, 82, 82, 0.10);
    --blue-bg:      rgba(64, 196, 255, 0.08);

    /* Text */
    --ink:          #e8f0eb;
    --muted:        #7a9383;
    --faint:        #3d5446;

    /* Borders */
    --line:         rgba(0, 230, 118, 0.12);
    --line-bright:  rgba(0, 230, 118, 0.30);

    /* Typography */
    --font-display: 'Syne', sans-serif;
    --font-mono:    'IBM Plex Mono', monospace;
    --font-body:    'DM Sans', system-ui, sans-serif;
}

/* ── Reset ── */
html, body, [class*="css"] {
    font-family: var(--font-body);
    color: var(--ink);
}

/* ── Page ── */
.stApp,
[data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
}

[data-testid="stAppViewContainer"] > .main {
    background: var(--bg);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #040a06 !important;
    border-right: 1px solid var(--line) !important;
}

[data-testid="stSidebar"] section {
    padding-top: 1rem;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: var(--muted) !important;
    font-size: 0.82rem;
    font-family: var(--font-body);
}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select {
    background: rgba(0, 230, 118, 0.04) !important;
    color: var(--ink) !important;
    border: 1px solid var(--line) !important;
    border-radius: 6px !important;
}

/* ── Streamlit native dark overrides ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border-color: var(--line) !important;
}

[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
    overflow: hidden;
}

/* ── Page header ── */
.shell-title {
    font-family: var(--font-display);
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--ink);
    margin: 0 0 0.1rem 0;
}

.shell-subtitle {
    font-family: var(--font-body);
    font-size: 0.88rem;
    color: var(--muted);
    margin: 0 0 1rem 0;
}

/* ── KPI strip ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.65rem;
    margin-bottom: 1.1rem;
}

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.9rem 1rem 0.75rem 1rem;
    min-height: 88px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.kpi-value {
    font-family: var(--font-mono);
    font-size: 2.15rem;
    font-weight: 700;
    line-height: 1;
    margin-top: 0.4rem;
    letter-spacing: -0.02em;
}

.tone-green { color: var(--green) !important; }
.tone-amber { color: var(--amber) !important; }
.tone-red   { color: var(--red)   !important; }
.tone-blue  { color: var(--blue)  !important; }
.tone-dark  { color: var(--ink)   !important; }

.kpi-sub {
    font-family: var(--font-body);
    font-size: 0.73rem;
    color: var(--muted);
    margin-top: 0.35rem;
}

/* ── Micro-label ── */
.micro-label {
    font-family: var(--font-body);
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted);
}

/* ── Surface cards ── */
.surface-card,
.briefing-card,
.confidence-card,
.detail-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}

.briefing-card.dark {
    background: linear-gradient(180deg, #0d1a10 0%, #091209 100%);
    border-color: rgba(0, 230, 118, 0.18);
}

.briefing-card.dark p,
.briefing-card.dark li,
.briefing-card.dark span {
    color: #a8c9b0;
}

/* ── Context strip ── */
.context-strip {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.9rem 1rem 0.5rem 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}

/* ── Panel headers ── */
.panel-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.85rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid var(--line);
}

.panel-title {
    font-family: var(--font-display);
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--ink);
    margin: 0;
}

.panel-caption {
    font-family: var(--font-body);
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.1rem;
}

/* ── Action cards ── */
.action-card {
    border: 1px solid var(--line);
    border-left: 3px solid;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.1s;
}

.action-card.red {
    border-left-color: var(--red);
    background: var(--red-bg);
    box-shadow: 0 0 0 1px rgba(255, 82, 82, 0.12),
                0 4px 16px rgba(255, 82, 82, 0.12);
}

.action-card.amber {
    border-left-color: var(--amber);
    background: var(--amber-bg);
    box-shadow: 0 0 0 1px rgba(255, 171, 0, 0.10),
                0 4px 12px rgba(255, 171, 0, 0.10);
}

.action-card.blue {
    border-left-color: var(--blue);
    background: var(--blue-bg);
}

.action-card.green {
    border-left-color: var(--green);
    background: var(--green-bg);
}

.action-topline {
    display: flex;
    gap: 0.55rem;
    align-items: center;
    margin-bottom: 0.35rem;
}

.action-title {
    font-family: var(--font-body);
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--ink);
}

.action-meta {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--muted);
    margin-bottom: 0.32rem;
    letter-spacing: 0.01em;
}

.action-copy {
    font-family: var(--font-body);
    font-size: 0.83rem;
    color: var(--ink);
    line-height: 1.45;
    margin-bottom: 0.3rem;
}

.action-reco {
    font-family: var(--font-body);
    font-size: 0.77rem;
    color: var(--muted);
    line-height: 1.4;
}

/* ── Status pills ── */
.status-pill {
    display: inline-block;
    padding: 0.22rem 0.55rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    font-family: var(--font-mono);
    letter-spacing: 0.04em;
    border: 1px solid;
}

.status-pill.green { background: rgba(0,230,118,0.12); color: var(--green); border-color: rgba(0,230,118,0.30); }
.status-pill.amber { background: rgba(255,171,0,0.12); color: var(--amber); border-color: rgba(255,171,0,0.30); }
.status-pill.red   { background: rgba(255,82,82,0.12);  color: var(--red);   border-color: rgba(255,82,82,0.30); }
.status-pill.blue  { background: rgba(64,196,255,0.12); color: var(--blue);  border-color: rgba(64,196,255,0.30); }

/* ── Detail panel ── */
.detail-card {
    background: var(--surface-hi);
    border: 1px solid var(--line-bright);
    box-shadow: 0 0 0 1px rgba(0,230,118,0.08), 0 4px 20px rgba(0,0,0,0.35);
}

.detail-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.9rem;
}

.detail-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.9rem;
}

.detail-metric {
    background: var(--surface-mid);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.6rem 0.75rem;
}

.detail-metric .value {
    font-family: var(--font-mono);
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--ink);
    margin-top: 0.2rem;
}

/* ── Footer ── */
.dash-footer {
    text-align: center;
    font-family: var(--font-body);
    font-size: 0.72rem;
    color: var(--faint);
    padding: 1rem 0 1.5rem 0;
    margin-top: 2rem;
    border-top: 1px solid var(--line);
}
```

---

## Phase 2 — KPI Strip: Render as Single HTML Block

Replace the `render_kpi_strip()` function body.

The current version uses `st.columns(5)` which gives uneven card heights.
The new version renders all 5 KPI cards as one `st.markdown()` HTML block using the `.kpi-grid` CSS class.

```python
def render_kpi_strip(kpis: Dict[str, Any], confidence: Dict[str, Any]) -> None:
    coverage_tone = "green" if kpis["weighted_coverage"] >= 100 else "amber" if kpis["weighted_coverage"] >= 85 else "red"
    risk_tone = "red" if kpis["risk_weeks"] else "green"
    blocker_tone = confidence["state_tone"]

    cards = [
        ("Weighted Coverage",  f"{kpis['weighted_coverage']:.1f}%",     coverage_tone, "season-wide supply vs demand"),
        ("Demand At Risk",     f"{kpis['demand_at_risk']:,.0f}",         "red" if kpis["demand_at_risk"] > 0 else "green", "shortage lbs"),
        ("Overage Exposure",   f"{kpis['overage_exposure']:,.0f}",       "amber" if kpis["overage_exposure"] > 0 else "green", "overage lbs above watch"),
        ("Risk Weeks",         str(kpis["risk_weeks"]),                   risk_tone, "crop-weeks below threshold"),
        ("Trust Blockers",     str(kpis["trust_blockers"]),               blocker_tone, confidence["state_label"].lower()),
    ]

    cards_html = "".join([
        f"<div class='kpi-card'>"
        f"<div class='micro-label'>{label}</div>"
        f"<div class='kpi-value tone-{tone}'>{value}</div>"
        f"<div class='kpi-sub'>{sub}</div>"
        f"</div>"
        for label, value, tone, sub in cards
    ])

    st.markdown(f"<div class='kpi-grid'>{cards_html}</div>", unsafe_allow_html=True)
```

---

## Phase 3 — Charts: Dark Theme + Area Fills

### 3.1 — Python color constants at top of file

Replace the existing color constants:
```python
_BLUE  = "#40c4ff"
_GREEN = "#00e676"
_AMBER = "#ffab00"
_RED   = "#ff5252"
_INK   = "#e8f0eb"
_BG    = "#111a14"
```

### 3.2 — Weekly balance chart: area + line layers

Replace `render_weekly_balance_chart()` chart construction:

```python
base = alt.Chart(balance_df)

area = base.mark_area(opacity=0.10, interpolate="monotone").encode(
    x=alt.X("week_label:N", title=None, sort=None,
             axis=alt.Axis(labelAngle=-35, labelFontSize=11, labelColor="#7a9383")),
    y=alt.Y("pounds:Q", title="Pounds",
             axis=alt.Axis(labelFontSize=11, labelColor="#7a9383", titleColor="#e8f0eb")),
    color=alt.Color("series:N",
        scale=alt.Scale(domain=["Demand", "Supply"], range=[_BLUE, _GREEN]), title=None),
)

line = base.mark_line(strokeWidth=2, interpolate="monotone").encode(
    x="week_label:N",
    y="pounds:Q",
    color=alt.Color("series:N",
        scale=alt.Scale(domain=["Demand", "Supply"], range=[_BLUE, _GREEN])),
    tooltip=[
        alt.Tooltip("week_label:N", title="Week"),
        alt.Tooltip("series:N", title="Series"),
        alt.Tooltip("pounds:Q", title="Pounds", format=",.1f"),
    ],
)

chart = (
    (area + line)
    .properties(height=260, title=alt.TitleParams(
        text=title, fontSize=12, fontWeight=700, color="#e8f0eb", anchor="start"
    ))
    .configure_view(strokeWidth=0, fill=_BG)
    .configure_axis(gridColor="rgba(0,230,118,0.06)", domainColor="rgba(0,230,118,0.15)",
                    labelColor="#7a9383", titleColor="#e8f0eb")
    .configure_legend(labelColor="#e8f0eb", titleColor="#7a9383", labelFontSize=11)
)
st.altair_chart(chart, use_container_width=True)
```

Apply identical pattern to `render_crop_chart()`.

### 3.3 — Heatmap: dark-mode color scale

In `render_heatmap()`, update the color scale:

```python
color=alt.Color(
    "coverage_pct:Q",
    title="Coverage %",
    scale=alt.Scale(
        domain=[0, 75, 100, 150],
        range=["#4a1010", "#3a2600", "#0d2e1a", "#00e676"],
    ),
),
```

Set heatmap chart background:
```python
.configure_view(strokeWidth=0, fill=_BG)
.configure_axis(gridColor="rgba(0,230,118,0.06)", domainColor="rgba(0,230,118,0.12)",
                labelColor="#7a9383")
```

### 3.4 — Grouped bar chart (if used): dark mode bars

If there are any `mark_bar()` charts, add:
```python
.configure_view(strokeWidth=0, fill=_BG)
```
and update color ranges to `[_BLUE, _GREEN]`.

---

## Phase 4 — Sidebar Brand Mark

In `dashboard.py`, find the sidebar heading `st.sidebar.markdown(...)` block.

Replace with:
```python
st.sidebar.markdown(
    "<div style='padding:0.4rem 0 1.4rem 0; border-bottom:1px solid rgba(0,230,118,0.15); margin-bottom:1.2rem'>"
    "<div style=\"font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; "
    "color:#00e676; letter-spacing:-0.02em; line-height:1\">AGRI-AI</div>"
    "<div style='font-size:0.7rem; color:#3d5446; font-weight:500; margin-top:0.3rem; "
    "font-family:DM Sans,sans-serif; text-transform:uppercase; letter-spacing:0.08em'>"
    "Supply Planning Command Center</div>"
    "</div>",
    unsafe_allow_html=True,
)
```

---

## Phase 5 — Fix All Deprecated APIs

Search for and replace:
- `width="stretch"` → `use_container_width=True` in every `st.dataframe()` and `st.altair_chart()` call
- `st.dataframe(styled, width="stretch", hide_index=True)` → `st.dataframe(styled, use_container_width=True, hide_index=True)`

Verify: `grep -n 'width="stretch"' dashboard_views.py dashboard.py` must return nothing.

---

## Phase 6 — Self-Review Against Subagents

Before committing, use the `.claude/agents/uiux-critic.md` checklist mentally:

**Required passes:**
- [ ] No `width="stretch"` anywhere
- [ ] `@import` for Google Fonts present at top of CSS
- [ ] `.kpi-value` uses `var(--font-mono)` — IBM Plex Mono
- [ ] `.shell-title` uses `var(--font-display)` — Syne
- [ ] Page background is `#080f0b` (dark, not light)
- [ ] `.action-card.red` has `box-shadow` with red glow
- [ ] `.status-pill` uses monospace font
- [ ] Heatmap color scale includes `#4a1010` as the critical shortage color
- [ ] Weekly balance chart uses `mark_area` + `mark_line` layers
- [ ] `render_kpi_strip()` uses `st.markdown()` single block, not `st.columns()`
- [ ] Briefing card dark background is `#0d1a10` family (not `#203038`)

---

## Phase 7 — Test and Commit

```bash
source .venv/bin/activate
python3 -m src.main --data-dir data --output-dir output
streamlit run dashboard.py
```

Open http://localhost:8501 and verify visually:
1. Page background is dark — near-black forest green
2. AGRI-AI brand mark in Syne 800, green, visible at top of sidebar
3. KPI values render in IBM Plex Mono — the monospace feel should be obvious
4. At least one KPI value is in vivid `#ff5252` or `#00e676`
5. Action card with red left border has a visible red glow shadow
6. Weekly balance chart shows area fills, not just lines
7. Heatmap has dark red for critical shortage cells

Write final commit summary to `prompts/codex/dashboard_dark_v1_summary.md`.

---

## What Not To Do

- Do NOT keep the light green `#eef1ea` background
- Do NOT keep the light card borders — they belong to the old system
- Do NOT use `st.columns()` for the KPI strip
- Do NOT use `mark_line` alone without area fill layer
- Do NOT change `dashboard_data.py`
- Do NOT add new modules, panels, or features
- Do NOT add new Python packages

---

## Definition of Done

The redesign is complete when:
1. The page background is dark
2. Typography is Syne + IBM Plex Mono + DM Sans throughout
3. KPI values are monospace and vivid-colored
4. Action cards glow by severity in dark mode
5. Charts are dark-mode themed with area fills
6. All deprecated APIs removed
7. Dashboard runs cleanly: `streamlit run dashboard.py`
8. Branch `codex/dashboard-dark-v1` has clean commits by phase
