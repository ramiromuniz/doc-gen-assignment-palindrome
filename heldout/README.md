# Held-out client

A synthetic client the pipeline was never developed on, used to test that the fixes generalise.
It was written after the pipeline was frozen (tag `v2.1`), with its answer key
(`evals/expected/client_05_synthetic.json`) written before the first run, and it is run once
with no change to code or prompts.

It uses the same kinds of problem as the four development clients, in new forms:

| Trap | Correct report | Check |
|---|---|---|
| A joint account listed under both people | in the holdings table once | F1 |
| An old ISA, closed in the database | not in the report | F1 |
| A cash account that only funds the top-up | not in the holdings table | F1 |
| A newer value seen at the meeting than in the database | the newer value is used | F3 |
| Selling was discussed but the clients decided against it | no Tax Implications section | F2 |

Run and score it:

```bash
uv run python -m agent_pipeline.generate --client client_05_synthetic --data-dir heldout --output-dir outputs/heldout
uv run python -m evals.run --reports outputs/heldout
```
