# LLM Extraction Layer — Activation Checklist

## Current state

The LLM extraction layer is **BUILT and TESTED in mock mode**.
`USE_REAL_LLM=false` (the default). **No API calls are being made.**
The mock responder — a deterministic alias/fuzzy mapper with the same
interface as the real path — exercises the full pipeline (extraction →
safeguards → confirmation UI → Layer-1 validation → staging insert →
training corpus) with realistic synthetic results: confidence spreads,
review flags, derived fields, ambiguous-date warnings.

## What the layer does

An operator uploads whatever they have — messy Excel, QuickBooks
exports, PDF invoices, CSVs, WhatsApp/email text. The extraction engine
reads it, maps it to HarvestMind's 5 staging tables (the real
migration-010 schema), infers missed fulfillments with the arithmetic
stated, flags every uncertainty, and shows everything in a confirmation
screen. **Nothing flows downstream unconfirmed**, and confirmed rows
still pass the existing hard validators. Every confirmed session is
logged immutably (PII-scrubbed) and its operator corrections accumulate
as gold-label training data.

## To activate for the pilot

1. Go to **console.anthropic.com** — create an account if needed
2. **API Keys → Create Key** → copy immediately (shown once only)
3. **Billing → set a Monthly Spend Limit BEFORE activating**
   (suggested: $50 to start)
4. Set a spend-alert email at a lower threshold (suggested: $20)
5. Add to `.env`:
   ```
   USE_REAL_LLM=true
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
6. **NEVER commit `.env` to GitHub** — verify it is in `.gitignore`
   before step 5 (it is, as of this writing: `.gitignore` lines 17–18)
7. Install the SDK if not present: `pip install anthropic`
   (it is in `pyproject.toml`; the code imports it lazily, so mock-mode
   installs never need it)
8. Restart the backend server
9. Upload a small test file first — check `training/audit_log/<session>/`
   to confirm a real API call was made (`mock_mode: false` in
   `meta.json`) and that tokens + cost were logged
10. Expected cost: **~$0.01–0.05 per operator file upload** (model and
    pricing are set in `config/llm_config.py`, never hardcoded
    elsewhere)

If `USE_REAL_LLM=true` is set without a key, the backend **fails loudly
at startup** with instructions — it never silently runs mock while you
believe it is live.

## What changes when activated

- The yellow mock-mode banner disappears from the confirmation UI
  (replaced by a LIVE chip)
- Real Claude API calls (`EXTRACTION_MODEL`, prompt version
  `EXTRACTION_PROMPT_V1`) normalize operator data
- Token usage and cost are logged per session at
  `training/audit_log/<session_id>/meta.json`; sessions above 2× the
  median token count are flagged
- If a real API call fails mid-session, the deterministic fallback
  mapper runs instead and the UI shows "Smart mapping temporarily
  unavailable" — never a silent degradation
- Operator confirmations keep accumulating as training data in
  `training/corpus/`

## Cost traceability

Every session's `meta.json` carries `api_tokens` and `api_cost_usd`
(input × $3/M + output × $15/M for Sonnet; rates configurable via
`LLM_INPUT_COST_PER_MTOK` / `LLM_OUTPUT_COST_PER_MTOK`). Mock sessions
log zero. Sum over `training/audit_log/*/meta.json` for total spend.

## Fine-tuning timeline

- Corpus accumulates automatically from every **confirmed** session;
  mock sessions are recorded but **never train a model**
- Check progress: `GET /training/corpus/stats`
- At **50 usable real sessions** the fine-tuning gate opens
  (`training/finetune_pipeline.py` — the dispatch is deliberately
  stubbed until then, and the quality checker excludes duplicates and
  contradictory labels first)
- A fine-tuned model is promoted only if it beats the incumbent
  prompt-based extractor on **all** metrics on a held-out split, via the
  shared model registry (family `extraction`) with one-call rollback
- At 500+ sessions: a domain-specific extraction model trained on your
  operators' own corrections — the data moat
