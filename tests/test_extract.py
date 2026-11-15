"""Unit tests for check_facts: the code checks on the extracted facts, no model calls."""

# pipeline step under test
from agent_pipeline.extract import Account, Action, Facts, check_facts

# a tiny client database: one joint account (listed under both holders), one closed,
# one with no value
DB = {
    "holders": {
        "client": {
            "accounts": [
                {"account_id": "ISA-1", "status": "open", "value": 50000.0, "valuation_date": "2026-04-30"},
                {"account_id": "GIA-J", "status": "open", "value": 40000.0, "valuation_date": "2026-03-15"},
                {"account_id": "OLD-1", "status": "closed", "value": 0.0, "valuation_date": "2025-11-30"},
            ]
        },
        "partner": {
            "accounts": [
                {"account_id": "GIA-J", "status": "open", "value": 40000.0, "valuation_date": "2026-03-15"},
                {"account_id": "CASH-2", "status": "open", "value": None, "valuation_date": None},
            ]
        },
    }
}
# the source text: the db values plus a newer value seen at a meeting
SOURCES = "ISA 50000.0, joint GIA 40000.0. At the meeting the joint GIA showed £45,000. Initial charge 0%."


def account(account_id: str, value: float) -> Account:
    return Account(account_id=account_id, value=value, value_date="2026-05-14", value_source="meeting notes")


def facts(accounts: list[Account], actions: list[Action] | None = None) -> Facts:
    return Facts(
        accounts_in_scope=accounts,
        selling_investments=True,
        situation="",
        actions=actions or [],
        initial_charge="0%",
        to_confirm=[],
    )


def test_correct_facts_pass_unchanged():
    # newer value from the meeting is in the sources, so it is kept
    checked, notes = check_facts(facts([account("ISA-1", 50000), account("GIA-J", 45000)]), DB, SOURCES)
    assert [a.value for a in checked.accounts_in_scope] == [50000, 45000]
    assert notes == []


def test_unknown_closed_and_no_value_accounts_are_removed():
    proposed = [account("ISA-1", 50000), account("NEW-1", 1), account("OLD-1", 0), account("CASH-2", 0)]
    checked, notes = check_facts(facts(proposed), DB, SOURCES)
    assert [a.account_id for a in checked.accounts_in_scope] == ["ISA-1"]
    assert len(notes) == 3


def test_joint_account_kept_once():
    checked, _ = check_facts(facts([account("GIA-J", 45000), account("GIA-J", 45000)]), DB, SOURCES)
    assert [a.account_id for a in checked.accounts_in_scope] == ["GIA-J"]


def test_value_not_in_sources_falls_back_to_database():
    checked, notes = check_facts(facts([account("GIA-J", 41000)]), DB, SOURCES)
    assert checked.accounts_in_scope[0].value == 40000
    assert checked.accounts_in_scope[0].value_source == "client database"
    assert len(notes) == 1


def test_made_up_amount_becomes_null():
    actions = [Action(action="top up the ISA", amount="£20,000"), Action(action="sell the GIA", amount="£45,000")]
    checked, notes = check_facts(facts([], actions), DB, SOURCES)
    assert [a.amount for a in checked.actions] == [None, "£45,000"]
    assert len(notes) == 1
