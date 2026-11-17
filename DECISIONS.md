# Decisions

The key calls in the order they were made: what, why, and what it cost. Results are in
`evals/results/summary.md`; the detail is in the linked issues and pull requests.

## D-001 · Plan client by client, fix generically (#1)
Each client exposed new problems. Every fix targets the class of problem, never one client's data,
and the eval runs on all clients after every change.

## D-002 · Measure before changing anything (#9)
A baseline run of the untouched pipeline on all clients first, so every change is a before and
after on the same clients.

## D-003 · Model access
The provided key was deactivated, so I used my own key with the same model to keep results
comparable.

## D-004 · Tracing with Langfuse (#8)
One trace per report: every step and model call, with its input, output, cost and latency, tagged by
client. Optional: without keys the pipeline runs the same.

## D-005 · Write "correct" down as code (#10)
Plain Python checks, no model calls, so free and repeatable: generic checks (mandatory wording, no
unfilled slots) plus an answer key per client (sections, accounts, figures).
**Trade-off:** a client with no answer key only gets the generic checks.

## D-006 · v1: rules out of the data, into versioned prompts (#25)
Only client files reach the model. The spec and the engineer notes are written for whoever
configures the report, so their rules became config instead of model input. Fixed wording is
template text, never generated.
**Limit:** each section still decided the facts on its own, so sections could disagree.

## D-007 · The model is config (#25)
`OPENAI_MODEL`, not code. The switch to a stronger model was measured separately from the code
changes, because what was left was judgement (which value is newer, what is uncertain).

## D-008 · v2: the model proposes, code verifies (#26)
One call extracts the facts as structured output. Code checks them against the database and the
client's files, corrects or removes what it cannot trust, and logs each change as a review note.
The tax gate and the holdings table are code; the writers read only the verified facts. The facts
and review notes are saved with each report for audit.
**Trade-offs:** slower, because extraction runs first; writers only know what the facts give them;
values are checked by number, not by citation.

## D-009 · Workflow, not an agent
The task is the same every time, so a fixed flow: predictable, cheaper and auditable. The model
makes only the judgement calls. A loop or tools only where the eval shows a fixed step failing.

## D-010 · Eval v1: check for what is missing (#26)
A new check that every key amount appears. It found a gap in v2 (one client's source of funds was
never stated), fixed with one generic prompt line (`v2.1`). Eval versions are kept side by side.

## D-011 · Prove it holds (#28, #31)
Three repeat runs on all clients, then a synthetic held-out client written after the freeze: answer
key first, one run, no tuning.
**Limit:** one client I wrote is evidence, not proof.

## D-012 · Scope
The time box went to the agent flow and its evaluation, not software hardening. Retries, typed
ingestion, validation before writing and a failure policy are deferred (#18 to #21). Unit tests run
in CI on every pull request; the eval runs on demand.

---

## Taking it further
- **Next:** repeat runs as a standard metric; an LLM groundedness judge for clients with no answer
  key, calibrated on human labels; a synthetic client generator; citations in the facts; reading
  the statement images; a cheaper writer model if the eval allows it.
- **More agentic:** one bounded retry where review notes go back to the extractor; runtime checks
  that regenerate a failing section once; the adviser approves the facts before the report is
  written.
- **Production:** a DPIA, risk assessment and adviser sign-off, with facts and review notes as the
  audit record; prompt changes gated by the eval in CI; personal data masked in traces and UK or EU
  data residency; Key Vault for secrets, Postgres for records, a queue and workers for volume;
  dashboards and online evals, with every adviser correction becoming an eval case.
