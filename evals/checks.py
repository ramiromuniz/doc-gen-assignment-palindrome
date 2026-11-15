"""Eval checks: each one takes a finished report and returns a pass (1.0) or fail (0.0).

tier 1 (generic): need no answer key, run on any client.
tier 2 (client facts): compare against evals/expected/<client>.json, skipped if there is none.

every check is plain python, no model calls, so running the eval is free and repeatable.
"""

# standard library
import re

# third party
from langfuse import Evaluation

# mandatory wording, must appear word for word
# risk warning: from template_spec.md (Conclusion)
RISK_WARNING = (
    "The value of investments can fall as well as rise and you may get back less than you invest. "
    "Past performance is not a guide to future returns."
)
# fca line: static text in config/template_config.json (Introduction), fde_notes: never paraphrased
FCA_LINE = "This firm is authorised and regulated by the Financial Conduct Authority."

# figures in a report: money and rates, e.g. £52,000 / 0.5% / 6.4 per cent
NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"  # 52,000 or 0.5
FIGURE = re.compile(rf"£\s?{NUMBER}|{NUMBER}\s?(?:%|per cent)")

# a template slot the model was meant to fill, e.g. <<scope>>
SLOT = re.compile(r"<<[^<>]+>>")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _flatten(text: str) -> str:
    """Collapse line breaks and repeated spaces so wrapped text still matches."""
    return re.sub(r"\s+", " ", text)


def _verbatim_once(output: str, wording: str, name: str) -> Evaluation:
    """Pass if the exact wording appears once: missing, paraphrased or repeated all fail."""
    count = _flatten(output).count(wording)
    return Evaluation(
        name=name,
        value=1.0 if count == 1 else 0.0,
        comment=f"found {count} times, expected 1",
    )


def _numbers(text: str) -> set[float]:
    """Every number in the text as a value, so £52,000, GBP 52,000 and 52000.0 all match."""
    return {float(n.replace(",", "")) for n in re.findall(NUMBER, text)}


def _tables(report: str) -> list[list[list[str]]]:
    """Every markdown table in the report: its data rows, each row a list of cell texts."""
    tables, rows = [], []
    for line in report.splitlines() + [""]:  # the empty line closes a table at the very end
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif rows:
            tables.append(rows[2:])  # skip the header row and the |---| divider
            rows = []
    return tables


# ---------------------------------------------------------------------------
# tier 1: generic
# ---------------------------------------------------------------------------


def risk_warning_verbatim(*, output: str, **kwargs) -> Evaluation:
    """C1 (critical): the risk warning appears exactly once, word for word."""
    return _verbatim_once(output, RISK_WARNING, "C1_risk_warning")


def fca_line_verbatim(*, output: str, **kwargs) -> Evaluation:
    """C2 (critical): the FCA line appears exactly once, word for word."""
    return _verbatim_once(output, FCA_LINE, "C2_fca_line")


def no_leftover_slots(*, output: str, **kwargs) -> Evaluation:
    """C3 (critical): no <<slot>> is left unfilled, so the client never sees template residue."""
    leftovers = SLOT.findall(output)
    return Evaluation(
        name="C3_no_leftover_slots",
        value=0.0 if leftovers else 1.0,
        comment=f"left unfilled: {leftovers}" if leftovers else "all slots filled",
    )


# ---------------------------------------------------------------------------
# tier 2: client facts
# ---------------------------------------------------------------------------


def accounts_in_scope(
    *, output: str, expected_output: dict | None, **kwargs
) -> Evaluation | list:
    """F1 (critical): every holdings table lists exactly the accounts in scope, each once.

    catches out-of-scope accounts (e.g. the cash account that only funds the top-up) and
    joint accounts counted twice because the db lists them under each holder.
    the account id can sit in any column: we look for it as a whole cell in each row.
    """
    if not expected_output:
        return []  # no answer key for this client, skip
    expected = expected_output["accounts_in_scope"]
    tables = _tables(output)
    if not tables:
        return Evaluation(name="F1_accounts_in_scope", value=0.0, comment="no holdings table")

    problems = []
    for number, rows in enumerate(tables, start=1):
        # how many rows of this table each in-scope account appears in
        counts = {account: sum(account in row for row in rows) for account in expected}
        missing = [account for account, count in counts.items() if count == 0]
        repeated = [account for account, count in counts.items() if count > 1]
        other_rows = len(rows) - sum(counts.values())  # rows for accounts not in scope
        if missing or repeated or other_rows:
            problems.append(f"table {number}: missing {missing}, repeated {repeated}, {other_rows} other rows")
    return Evaluation(
        name="F1_accounts_in_scope",
        value=0.0 if problems else 1.0,
        comment="; ".join(problems) if problems else "as expected",
    )


def sections_as_expected(
    *, output: str, expected_output: dict | None, **kwargs
) -> Evaluation | list:
    """F2 (critical): the report has exactly the expected sections, in order."""
    if not expected_output:
        return []  # no answer key for this client, skip
    found = re.findall(r"^## (.+)$", output, flags=re.MULTILINE)
    expected = expected_output["sections"]
    return Evaluation(
        name="F2_sections",
        value=1.0 if found == expected else 0.0,
        comment=f"found {found}" if found != expected else "as expected",
    )


def only_approved_figures(
    *, output: str, expected_output: dict | None, **kwargs
) -> Evaluation | list:
    """F5 (critical): every £ or % figure in the report is one a person approved for this client.

    catches any made-up number, e.g. an estimated gain or a fee rate. fee and cgt figures are
    never on the approved list because a person fills them in (fde_notes).
    """
    if not expected_output:
        return []  # no answer key for this client, skip
    approved = _numbers(" ".join(expected_output["approved_figures"]))
    # dict.fromkeys drops repeats but keeps the order they appear in
    unapproved = list(
        dict.fromkeys(f for f in FIGURE.findall(output) if not _numbers(f) <= approved)
    )
    return Evaluation(
        name="F5_only_approved_figures",
        value=0.0 if unapproved else 1.0,
        comment=f"not approved: {unapproved}" if unapproved else "all figures approved",
    )


# all the checks, so the eval runner can call them all in one go.
# the tier 2 ones are skipped if there is no answer key for this client.
ALL_CHECKS = [
    risk_warning_verbatim,
    fca_line_verbatim,
    no_leftover_slots,
    accounts_in_scope,
    sections_as_expected,
    only_approved_figures,
]
