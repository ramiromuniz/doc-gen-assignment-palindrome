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

---

## Taking it further
*To be completed at the end.*
