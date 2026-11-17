# Advice report generator

This pipeline writes a client advice report from the client's files: a database extract, meeting
notes, a report request and statements. An adviser reviews and signs the report before it goes to
the client, so it must be correct and every figure must be traceable to a source.

The starting pipeline produced reports that read well but were not reliably correct: it included
accounts that were out of scope, counted joint accounts twice, used old values and invented
figures. This version fixes that, and an evaluation shows it.

The task is described in `PROJECT_GUIDANCE.md`. The decisions, and why they were made, are in
`DECISIONS.md`.

## Results at a glance

Seven checks per report, four clients (28 checks). Full details in
[`evals/results/summary.md`](evals/results/summary.md).

| Version | What changed | Checks passed | Cost for 4 reports |
|---|---|---|---|
| baseline | The pipeline as given | 20/28 | $0.011 |
| v1 | Rules moved into versioned prompts, only client files reach the model | 23/28 (gpt-4o-mini), 28/28 (gpt-6.1-sol) | $0.007, $0.146 |
| v2.1 | Facts decided once and checked in code, every section written from them | 28/28 in 3 out of 3 runs | $0.112 |

A held-out client, written after the pipeline was frozen and run once with no changes, passed
7/7 (see [`heldout/README.md`](heldout/README.md)).

## How it works

The model proposes, code verifies, and the report is written from the verified facts.

1. **Read the client's files.** Notes meant for engineers and general market material are
   skipped (listed in the config), so only client data reaches the model.
2. **Extract the facts, once.** One model call returns the facts of the case in a fixed format:
   the accounts in scope and their values, whether investments are being sold, the actions, the
   charges, and what a person still has to confirm.
3. **Verify the facts in code.** Every account is checked against the client database (it
   exists, it is open, a joint account is counted once). Every value and amount must appear in the
   client's files. What can be corrected is corrected, the rest is removed, and each change is
   recorded as a review note for the adviser.
4. **Write the report.** Code decides which sections apply and builds the holdings table. The
   model writes the text sections, reading only the verified facts, so the table and the text
   always agree. Fixed wording (the regulatory line, the risk warning) is never generated.
5. **Save for review.** The report is saved with the facts and the review notes next to it, and
   every step is traced in Langfuse.

Figures a person must finalise (fees, tax) are never invented: they appear as `[TO CONFIRM: ...]`.

## Run it

You need [uv](https://docs.astral.sh/uv/) and an OpenAI key.

```bash
cp .env.example .env              # add your OpenAI key
uv sync --extra dev               # install, including the test tools
```

**One client** (about 30 seconds, a few pence):

```bash
uv run python -m agent_pipeline.generate --client client_01_clean
```

The report and its facts are written to `outputs/client_01_clean.md` and
`outputs/client_01_clean.facts.json`.

**Only the facts** (one model call, to see what was decided and what code corrected):

```bash
uv run python -m agent_pipeline.generate --client client_04_stretch --facts-only
```

**A new client:** put its files in a folder and point to it.

```bash
uv run python -m agent_pipeline.generate --client <folder name> --data-dir <parent folder>
```

Use `--output-dir` to choose where reports are written, and `--help` for all options.

### Score the reports

The checks are plain Python with no model calls, so scoring is free and gives the same result
every time.

```bash
uv run python -m evals.run --reports outputs/v2.1
```

It prints one row per client and one column per check, with the reason for every fail, and saves
the table to `evals/results/`.

### Run the tests

```bash
uv run pytest
```

The tests never call a model. They run on every pull request (GitHub Actions).

### Tracing is optional

With Langfuse keys in `.env`, every report is traced to your own Langfuse project: each step,
model call, cost and latency, tagged with the client. To get keys:

1. Sign in at [cloud.langfuse.com](https://cloud.langfuse.com) and create a project.
2. In the project settings, open API keys and create a key pair.
3. Put the public key (`pk-lf-...`) and the secret key (`sk-lf-...`) in `.env`. For a project in
   the US region, also set `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com`.

Without keys the pipeline runs the same. Langfuse then prints
`Authentication error: Langfuse client initialized without public_key`, which is expected and
can be ignored.

## Run an earlier version

Each version is a git tag: `baseline`, `v1`, `v2`, `v2.1`. The tag `submission` marks the
version that was handed in.

```bash
git checkout v1                   # the code as it was at v1
git checkout main                 # back to the latest
```

The saved reports from every version are in `outputs/<version>/`.

## Where things are

| Folder | What is in it |
|---|---|
| `config/template_config.json` | The report: sections, fixed wording, and every prompt, versioned in git |
| `src/agent_pipeline/` | The pipeline: `generate.py` (the steps), `extract.py`, `verify.py`, `render.py` |
| `src/document_formatter/` | Reads the source files and assembles the final document |
| `data/` | The four clients' files |
| `heldout/` | A synthetic client used only to test that the fixes generalise |
| `evals/` | The checks (`checks.py`), the runner (`run.py`), the answer keys (`expected/`) and the results (`results/`) |
| `outputs/` | The reports from every version |
| `tests/` | Unit tests |
| `DECISIONS.md` | Every decision, the alternatives and the trade-offs |
