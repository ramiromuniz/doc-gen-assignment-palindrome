# Decisions

Short log of the key calls, why, and what we traded off. Detail lives in the linked issues and PRs.

**How the work is tracked:** one goal (#1) → phases per client (#2–#7) → tickets. Each ticket is a
pain point turned into a requirement with acceptance criteria.

---

## D-001 · Work client by client, fix generically
- Start with the simplest client, move up. Each client surfaces new pain points → new tickets.
- Fixes solve the class of problem, never one client's data. A held-out set will be run.
- The eval runs on all clients after every change, so regressions show up straight away.

## D-002 · Measure before changing anything
- Tracing first, then a baseline run of the untouched pipeline on all four clients.
- Every later change is judged against that baseline.

## D-003 · Model access
- Provided key returned `401 account_deactivated`. Using my own key, same model (`gpt-4o-mini`),
  so results stay comparable.

## D-004 · Tracing with Langfuse
- **Why:** nothing recorded what the model was sent, what it returned, or the cost. No way to audit
  a report or measure improvement.
- **What:** Langfuse's OpenAI drop-in plus two `@observe` steps. One trace per report, tagged by
  client: `generate-report` → section steps → each model call with prompt, output, tokens, cost.
- **Optional:** no keys, no tracing. The run still completes (tested).
- **Production:** traces hold client data. Synthetic here, so Langfuse Cloud is fine. For a real
  firm, self-host in their Azure tenant or mask personal data, and tag each trace with the release
  that produced it.

## D-005 · Eval v0: "correct" written down as code checks
- **Why:** the baseline reports look plausible. Without a scorecard there is no way to prove a fix
  worked, or that it broke nothing else.
- **What:** 6 critical checks in plain Python, no model calls, so free and the same answer every
  run. Langfuse experiments run them and keep the history.
  - Generic, any client including held-out: risk warning and FCA line word for word once, no
    unfilled `<<slots>>`.
  - Against a hand-written answer key per client: the right sections, exactly the accounts in
    scope in the table, no figure outside the approved list.
- **Invented figures:** checked against figures a person approved, since fee and CGT figures are
  set by a person anyway (fde_notes). Keyword rules were too brittle.
- **Left out on purpose:** a "must not contain" word list only catches what you predicted.
  Irrelevant files get fixed at ingestion, irrelevant content goes to an LLM judge later.
  Quality checks (repetition, structure) wait until the pipeline outputs JSON.
- **Gap:** clients without an answer key only get the generic checks. An LLM judge for
  groundedness and relevance closes that later.

## D-006 · v1: instructions out of the data, into versioned prompts
- **Why:** every call got every file as one user message, rules included. Engineer notes, the
  spec and a market update full of unrelated figures reached the model as if they were client
  facts, and the prompts were vague (one asked for a "best approximate estimate" of the tax).
- **What:** rules as the system message; only client files sent (skip list in config, unknown
  files still read); rules from the notes and spec rewritten as prompts; one commit per prompt;
  the risk warning made static text. Prompts describe only their own output: quoting the text
  around a slot made the model repeat it.
- **Result** (`evals/results/v1.md`): accounts in scope 1/4 → 4/4. Invented tax and fee figures
  gone, flagged as `[TO CONFIRM: ...]`. Cost -35%, time -39%.
- **What prompting did not fix:** each section is still a separate call that decides the facts
  on its own. So the model invents amounts where the sources give none (an "equal split" became
  £20,000 each), and sections disagree: one report's table used the newer value, its
  recommendation the older one. That is the case for v2: extract the facts once, as structured
  JSON, and write every section from them.

---

## Taking it further
*To be completed at the end.*
