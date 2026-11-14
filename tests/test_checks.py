"""The checks are the eval: if a check is wrong, every score built on it is wrong.

each test feeds a tiny made-up report into one check and confirms pass or fail.
"""

from evals.checks import RISK_WARNING, risk_warning_verbatim, sections_as_expected


# C1 risk warning

def test_risk_warning_passes_when_present_once():
    assert risk_warning_verbatim(output=f"Intro.\n\n{RISK_WARNING}").value == 1.0


def test_risk_warning_passes_when_wrapped_across_lines():
    # same words, line break in the middle: still word for word
    wrapped = RISK_WARNING.replace(" Past", "\nPast")
    assert risk_warning_verbatim(output=wrapped).value == 1.0


def test_risk_warning_fails_when_missing_or_repeated():
    assert risk_warning_verbatim(output="No warning here.").value == 0.0
    assert risk_warning_verbatim(output=f"{RISK_WARNING} {RISK_WARNING}").value == 0.0


# F2 sections

REPORT = "# Report\n\n## Introduction\n\ntext\n\n## Conclusion\n\ntext"


def test_sections_pass_when_they_match():
    expected = {"sections": ["Introduction", "Conclusion"]}
    assert sections_as_expected(output=REPORT, expected_output=expected).value == 1.0


def test_sections_fail_when_one_is_missing():
    expected = {"sections": ["Introduction", "Tax Implications", "Conclusion"]}
    assert sections_as_expected(output=REPORT, expected_output=expected).value == 0.0


def test_sections_skipped_without_answer_key():
    assert sections_as_expected(output=REPORT, expected_output=None) == []
