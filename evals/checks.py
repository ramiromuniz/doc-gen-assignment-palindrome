"""Eval checks: each one takes a finished report and returns a pass (1.0) or fail (0.0).

tier 1 (generic): need no answer key, run on any client.
tier 2 (client facts): compare against evals/expected/<client>.json, skipped if there is none.

every check is plain python, no model calls, so running the eval is free and repeatable.
"""

# standard library
import re

# third party
from langfuse import Evaluation

# mandatory wording, word for word, from template_spec.md (Conclusion)
RISK_WARNING = (
    "The value of investments can fall as well as rise and you may get back less than you invest. "
    "Past performance is not a guide to future returns."
)


def _flatten(text: str) -> str:
    """Collapse line breaks and repeated spaces so wrapped text still matches."""
    return re.sub(r"\s+", " ", text)


# ---------------------------------------------------------------------------
# tier 1: generic
# ---------------------------------------------------------------------------

def risk_warning_verbatim(*, output: str, **kwargs) -> Evaluation:
    """C1 (critical): the risk warning appears exactly once, word for word."""
    count = _flatten(output).count(RISK_WARNING)
    return Evaluation(
        name="C1_risk_warning",
        value=1.0 if count == 1 else 0.0,
        comment=f"found {count} times, expected 1",
    )


# ---------------------------------------------------------------------------
# tier 2: client facts
# ---------------------------------------------------------------------------

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


ALL_CHECKS = [risk_warning_verbatim, sections_as_expected]
