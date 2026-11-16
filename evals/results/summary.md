# Results summary

Every run of the pipeline, scored with every version of the eval. The per-client tables
and the reason for each fail are in `eval-v0/` and `eval-v1/`, the reports in `outputs/<run>/`.

## The runs

| run | what changed | model |
|---|---|---|
| baseline | the untouched pipeline | gpt-4o-mini |
| v1 | rules into versioned prompts, only client files reach the model | gpt-4o-mini |
| v1-sol | v1 with a stronger model | gpt-6.1-sol |
| v2 | facts extracted once, verified in code; table rendered in code; writers read the case notes | gpt-6.1-sol |
| v2.1 | v2 plus one recommendation prompt line (state where the money comes from) | gpt-6.1-sol |

## How the eval evolved

| eval | checks | added |
|---|---|---|
| eval-v0 | C1 risk warning, C2 FCA line, C3 no leftover slots, F1 accounts in scope, F2 sections, F5 only approved figures | the first definition of correct: mandatory wording and the answer keys |
| eval-v1 | eval-v0 + F3 key amounts present | F5 catches a figure that should not be there, F3 one that is missing (e.g. a stale value) |

## Scores (checks passed, 4 clients)

| run | eval-v0 (6 checks) | eval-v1 (7 checks) | what failed |
|---|---|---|---|
| baseline | 18/24 | 20/28 | F1 1/4, F3 2/4, F5 1/4 |
| v1 | 21/24 | 23/28 | F3 2/4, F5 1/4 |
| v1-sol | 24/24 | 28/28 | none |
| v2 | 24/24 | 27/28 | F3: client 4 missing the source amount |
| v2.1 | | 28/28 in 3/3 runs | none |

eval-v0 saw no difference between v1-sol and v2. F3 found the gap in v2, and one generic
prompt line closed it (v2.1).

## Repeat runs (v2.1, the same code three times)

| client | run 1 | run 2 | run 3 |
|---|---|---|---|
| client_01_clean | 7/7 | 7/7 | 7/7 |
| client_02_medium | 7/7 | 7/7 | 7/7 |
| client_03_hard | 7/7 | 7/7 | 7/7 |
| client_04_stretch | 7/7 | 7/7 | 7/7 |

## Cost and time (4 reports, from the Langfuse traces)

| run | calls | tokens | cost | time |
|---|---|---|---|---|
| baseline | 31 | | $0.0107 | 101s |
| v1 | 27 | | $0.0069 | 61s |
| v1-sol | 27 | 54,732 | $0.1464 | 120s |
| v2 | 23 | 37,675 | $0.1161 | 155s |
| v2.1 (mean of 3 runs) | 23 | 37,339 | $0.1121 | 128s |

v2.1 against v1-sol: the same score, 23% lower cost, 32% fewer tokens, 4 fewer calls.
Time per run is the sum of the four reports, run one after the other; it varies with the
API (v2.1 runs: 141s, 125s, 118s). Cost per report ranges from $0.013 (client 1) to $0.051
(client 4), driven by the size of the client's files.
