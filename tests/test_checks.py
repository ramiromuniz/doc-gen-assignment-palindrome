"""The checks are the eval: if a check is wrong, every score built on it is wrong.

each test feeds a tiny made-up report into one check and confirms pass or fail.
"""

from evals.checks import (
    FCA_LINE,
    RISK_WARNING,
    fca_line_verbatim,
    only_approved_figures,
    risk_warning_verbatim,
    sections_as_expected,
)


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


# C2 FCA line

def test_fca_line_passes_when_present_once():
    assert fca_line_verbatim(output=f"Intro.\n\n{FCA_LINE}").value == 1.0


def test_fca_line_fails_when_paraphrased():
    assert fca_line_verbatim(output="We are regulated by the FCA.").value == 0.0


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


# F5 approved figures

KEY = {"approved_figures": ["£40,000", "0.5%"]}


def test_figures_pass_when_all_approved():
    # both figures in the report are on the approved list
    report = "Selling the GIA (£40,000) has an initial charge of 0.5%."
    assert only_approved_figures(output=report, expected_output=KEY).value == 1.0


def test_figures_fail_on_a_made_up_number():
    report = "We estimate the gain to be approximately £5,000."
    result = only_approved_figures(output=report, expected_output=KEY)
    assert result.value == 0.0
    assert "£5,000" in result.comment


def test_figures_skipped_without_answer_key():
    assert only_approved_figures(output="£5,000", expected_output=None) == []
