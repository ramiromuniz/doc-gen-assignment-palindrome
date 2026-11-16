"""The checks are the eval: if a check is wrong, every score built on it is wrong.

each test feeds a tiny made-up report into one check and confirms pass or fail.
"""

from evals.checks import (
    FCA_LINE,
    RISK_WARNING,
    accounts_in_scope,
    fca_line_verbatim,
    key_amounts_present,
    no_leftover_slots,
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


# C3 leftover slots

def test_slots_pass_when_all_filled():
    assert no_leftover_slots(output="Advice in relation to your ISA.").value == 1.0


def test_slots_fail_when_one_is_left():
    result = no_leftover_slots(output="Advice in relation to <<scope>>.")
    assert result.value == 0.0
    assert "<<scope>>" in result.comment


# F1 accounts in scope

SCOPE = {"accounts_in_scope": ["ISA-1", "GIA-J"]}
HEADER = "| Account | Value |\n|---|---|\n"


def test_accounts_pass_when_table_matches():
    # same accounts in a different order still match
    report = HEADER + "| GIA-J | £40,000 |\n| ISA-1 | £61,000 |"
    assert accounts_in_scope(output=report, expected_output=SCOPE).value == 1.0


def test_accounts_found_in_any_column():
    report = "| Owner | Account |\n|---|---|\n| Joint | GIA-J |\n| David | ISA-1 |"
    assert accounts_in_scope(output=report, expected_output=SCOPE).value == 1.0


def test_accounts_fail_on_out_of_scope_or_duplicate():
    extra = HEADER + "| ISA-1 | x |\n| GIA-J | x |\n| CASH-1 | x |"
    twice = HEADER + "| ISA-1 | x |\n| GIA-J | x |\n| GIA-J | x |"
    assert accounts_in_scope(output=extra, expected_output=SCOPE).value == 0.0
    assert accounts_in_scope(output=twice, expected_output=SCOPE).value == 0.0


def test_accounts_fail_without_a_table():
    assert accounts_in_scope(output="No table here.", expected_output=SCOPE).value == 0.0


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


# F3 key amounts

AMOUNTS = {"key_amounts": ["£52,000", "£45,000"]}


def test_amounts_pass_when_all_present():
    report = "Your ISA is worth £52,000 and the joint GIA was a little over £45,000."
    assert key_amounts_present(output=report, expected_output=AMOUNTS).value == 1.0


def test_amounts_fail_on_a_stale_value():
    # the database value used instead of the newer one seen at the meeting
    report = "Your ISA is worth £52,000 and the joint GIA £40,000."
    result = key_amounts_present(output=report, expected_output=AMOUNTS)
    assert result.value == 0.0
    assert "£45,000" in result.comment


def test_amounts_skipped_without_answer_key():
    assert key_amounts_present(output="£45,000", expected_output=None) == []


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
