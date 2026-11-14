"""Score a folder of reports with the eval checks.

usage:
    uv run python -m evals.run --reports outputs/baseline

langfuse's run_experiment does the looping: one item per report, every check run on it,
scores collected and summarised. without langfuse keys it runs locally and just prints.
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

EXPECTED_DIR = Path("evals/expected")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score reports with the eval checks.")
    parser.add_argument("--reports", type=Path, required=True, help="folder of <client>.md reports")
    args = parser.parse_args()

    # langfuse prints emoji in its summary, the windows console crashes on them without this.
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
        name=f"eval-v0 {args.reports.as_posix()}",
        data=data,
        task=read_report,
        evaluators=ALL_CHECKS,
    )
    print(result.format(include_item_results=True))
    get_client().flush()


if __name__ == "__main__":
    main()
