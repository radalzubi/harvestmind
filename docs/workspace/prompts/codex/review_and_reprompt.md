# Codex Prompt: Review Claude Edits and Reprompt

Use this prompt after a Claude editing session to:

1. Evaluate whether the changes improved rigor and decision quality
2. Identify what is still weak, missing, or unvalidated
3. Generate a structured follow-on prompt to send back to Claude

---

## Step 1: Read the Changed Files

Start by reading these four files that Claude most recently updated:

- `docs/research/competitor_landscape.md`
- `docs/research/market_reality.md`
- `docs/pilot/indiana_pilot.md`
- `docs/business/business_analysis.md`

Also read for full context:

- `docs/business/venture_overview.md`
- `docs/product/mvp_scope.md`
- `AGENTS.md`

---

## Step 2: Evaluate Each Change

For each updated file, answer these questions:

1. Did the change make the business thesis sharper or just longer?
2. Is every claim supported by evidence or clearly labeled as an assumption?
3. Is the writing concise and operator-style, or does it drift into analysis padding?
4. Is the content placed in the correct file, or does it bleed across boundaries?
5. Did Claude introduce any unsupported certainty, inflated claims, or startup clichés?
6. What is still missing that a serious investor or operator would immediately ask for?

---

## Step 3: Score Each File

Score each file on three dimensions, 1–3:

- **Rigor** — are claims grounded, assumptions labeled, logic sound?
- **Utility** — does this improve an actual decision the operator or founder needs to make?
- **Completeness** — are the most important gaps now addressed, or are major holes still present?

Flag any section that scores below 2 on any dimension for rewrite or removal.

---

## Step 4: Identify What Claude Still Needs to Do

After evaluating the changes, identify the highest-leverage research and refinement tasks that remain.

Good follow-on tasks look like:

- a specific claim that needs source validation
- a competitor that needs deeper analysis
- a pricing assumption that needs a market comparable
- a pilot target that needs verification of fit
- a section that exists in the wrong file
- a risk or objection that is not yet addressed anywhere

Bad follow-on tasks look like:

- "add more detail to X" without specifying what detail
- "research the market" without specifying the question
- "improve the writing" without identifying what is weak

---

## Step 5: Write the Claude Reprompt

Based on your evaluation, write a structured prompt to send back to Claude.

Use this format:

---

### Claude Follow-On Prompt: [Short Title]

**Context**

One paragraph summarizing what Claude already did and what the repo currently reflects.

**What Is Still Weak**

Compact bullet list. Be specific. Do not repeat what Claude already addressed.

**Research Tasks**

For each task:

- **Task**: one clear sentence describing what to find or resolve
- **Target file**: where the output belongs
- **Why it matters**: one sentence on what decision this improves

**Editing Tasks**

For each task:

- **File**: which file to edit
- **Section**: which section to revise
- **Problem**: what is wrong or missing
- **Expected fix**: what a good revision looks like

**Quality Standard**

Remind Claude:

- write for execution, not completeness
- label assumptions explicitly
- cite or caveat every market number
- do not add content that already exists elsewhere in the repo
- leave each file more decision-useful than you found it

---

## Codex Operating Rules for This Prompt

- do not approve weak work just because Claude produced it
- do not let market sizing numbers stand without a source or caveat
- do not let competitor entries stand without clarity on what each tool actually does
- do not let pilot targets stand without noting what still needs verification
- if a section is weaker after Claude's edit than before, flag it and send it back
- if Claude's changes introduced repetition across files, consolidate before sending new tasks

## Output

Produce two things:

1. A short evaluation summary (one paragraph per file, flagged items called out)
2. The full Claude reprompt ready to paste into a new Claude session
