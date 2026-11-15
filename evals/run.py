"""Score a folder of reports with the eval checks.

usage:
    uv run python -m evals.run --reports outputs/baseline

langfuse's run_experiment does the looping: one item per report, every check run on it,
scores collected. without langfuse keys it runs locally. the scores are printed as one table
(client x check) and saved to evals/results/<folder>.md, so every version leaves a record.
"""

# standard library
import argparse
import io
import json
import sys
from pathlib import Path

# third party
from dotenv import load_dotenv
from langfuse import get_client

# eval checks
from evals.checks import ALL_CHECKS

EVAL_VERSION = "eval-v0"  # bump when checks are added, then re-score the baseline with it
EXPECTED_DIR = Path("evals/expected")
RESULTS_DIR = Path("evals/results")


def results_table(item_results: list) -> str:
    """One row per client, one column per check, then the reason for every fail.

    ✅ pass, ❌ fail, - skipped (no answer key for that client).
    """
    # {client: {check name: score}}, sorted so the table reads the same every run
    scores = {
        r.item["input"]["client"]: {e.name: e for e in r.evaluations}
        for r in sorted(item_results, key=lambda r: r.item["input"]["client"])
    }
    checks = sorted({name for client in scores.values() for name in client})

    lines = ["| client | " + " | ".join(checks) + " |", "|---" * (len(checks) + 1) + "|"]
    for client, results in scores.items():
        cells = ["-" if c not in results else "✅" if results[c].value == 1.0 else "❌" for c in checks]
        lines.append(f"| {client} | " + " | ".join(cells) + " |")

    # bottom row: passes out of the clients the check ran on
    passed = [
        f"{sum(r[c].value for r in scores.values() if c in r):.0f}/{sum(c in r for r in scores.values())}"
        for c in checks
    ]
    lines.append("| **passed** | " + " | ".join(passed) + " |")

    # the why behind every red cell
    lines += ["", "**Fails**", ""]
    for client, results in scores.items():
        for name, e in results.items():
            if e.value != 1.0:
                lines.append(f"- {client} · {name}: {e.comment}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score reports with the eval checks.")
    parser.add_argument("--reports", type=Path, required=True, help="folder of <client>.md reports")
    args = parser.parse_args()

    # the table uses emoji, the windows console crashes on them without this.
    # the isinstance check is because stdout is not always a real text stream (e.g. in tests)
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()

    # one item per report. the answer key is attached if this client has one
    data = []
    for report in sorted(args.reports.glob("*.md")):
        expected_file = EXPECTED_DIR / f"{report.stem}.json"
        expected = json.loads(expected_file.read_text(encoding="utf-8")) if expected_file.exists() else None
        data.append({"input": {"client": report.stem}, "expected_output": expected})

    # scoring existing reports, so the task just reads the file (no model calls)
    def read_report(*, item, **kwargs) -> str:
        return (args.reports / f"{item['input']['client']}.md").read_text(encoding="utf-8")

    result = get_client().run_experiment(
        name=f"{EVAL_VERSION} {args.reports.as_posix()}",
        data=data,
        task=read_report,
        evaluators=ALL_CHECKS,
    )
    get_client().flush()

    # print and save the table, one file per reports folder (e.g. evals/results/baseline.md)
    table = f"# {EVAL_VERSION} · {args.reports.as_posix()}\n\n{results_table(result.item_results)}\n"
    print(table)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{args.reports.name}.md").write_text(table, encoding="utf-8")


if __name__ == "__main__":
    main()
