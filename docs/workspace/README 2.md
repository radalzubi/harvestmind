# Workspace: agent definitions, prompts and process assets

Migrated 2026-09-01 from the `Agri-AI` repository (`~/Desktop/wg2`), which
is an **earlier superseded prototype** of this project. Its `src/` pipeline
(14 files, ~535 lines: aggregate, gap, ingest, memo, normalize) was replaced
by the ingestion and diagnostic layers here and was not migrated. These
process assets were the only content not duplicated anywhere in harvestmind.

## What is here

**`agents/`** — four custom Claude Code agent definitions:
`analytics-dashboard-designer`, `design-system-enforcer`,
`information-architect`, `uiux-critic`. These were registered agent types in
the Agri-AI working directory. Registering them here may require pointing
Claude Code's agent configuration at this path; copying the files alone does
not necessarily re-register them.

**`prompts/claude/`** and **`prompts/codex/`** — 15 orchestration prompts
covering the loop controller, code writer, reviewer, review-and-reprompt
cycle, issue-to-repo flow, idea stress test, and the dashboard redesign
series. This is the multi-agent process, which is not reconstructable from
the code.

**`linear/`** — board structure and follow-on issue definitions.

## Provenance

The Agri-AI repository remains on GitHub at `radalzubi/Agri-AI` with all
eight branches pushed. Two branches carried unpushed commits at migration
time (a 611-line dashboard redesign and 181 lines of ingest tests); both
were pushed before anything was moved, so nothing existed only on local
disk.

Treat these files as historical process assets. Several reference the older
Agri-AI structure and the retired Streamlit dashboard, so read them for
method rather than for accurate paths.
