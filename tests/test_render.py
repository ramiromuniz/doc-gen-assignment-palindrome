"""Unit tests for the parts of the report written by code, no model calls."""

# standard library
import json
from types import SimpleNamespace
from typing import Any

# pipeline steps under test
from agent_pipeline.extract import Account, Facts
from agent_pipeline.generate import ReportGenerator
from agent_pipeline.render import case_notes, holdings_table, money

# a tiny client database: one own account, one joint account listed under both holders
DB = {
    "holders": {
        "client": {
            "name": "Ann Smith",
            "accounts": [
                {"account_id": "ISA-1", "owner": "Ann Smith", "type": "Stocks & Shares ISA", "currency": "GBP"},
                {"account_id": "GIA-J", "owner": "Joint", "type": "General Investment Account", "currency": "GBP"},
            ],
        },
        "partner": {
            "name": "Ben Smith",
            "accounts": [
                {"account_id": "GIA-J", "owner": "Joint", "type": "General Investment Account", "currency": "GBP"},
            ],
        },
    }
}
# checked facts: the joint value is the newer one from the meeting
FACTS = Facts(
    accounts_in_scope=[
        Account(account_id="ISA-1", value=50000, value_date="2026-04-30", value_source="client database"),
        Account(account_id="GIA-J", value=45000, value_date="2026-05-14", value_source="meeting notes"),
    ],
    selling_investments=True,
    situation="",
    actions=[],
    initial_charge=None,
    to_confirm=[],
)


def test_money_keeps_pence_and_uses_the_currency_symbol():
    assert money(45000.0) == "£45,000"
    assert money(1234.5, "EUR") == "€1,234.50"
    assert money(1000.0, "CHF") == "CHF 1,000"


def test_holdings_table_one_row_per_account_with_checked_value():
    assert holdings_table(FACTS, DB).splitlines() == [
        "| Account | Owner | Type | Value |",
        "|---|---|---|---|",
        "| ISA-1 | Ann Smith | Stocks & Shares ISA | £50,000 |",
        "| GIA-J | Ann Smith and Ben Smith | General Investment Account | £45,000 |",
    ]


def test_case_notes_add_database_details_and_the_table_value():
    notes = json.loads(case_notes(FACTS, DB))
    joint = notes["accounts_in_scope"][1]
    # the same value string as in the table, plus who owns it and what it is
    assert joint["value"] == "£45,000"
    assert joint["owner"] == "Ann Smith and Ben Smith"
    assert joint["type"] == "General Investment Account"
    # the rest of the facts pass through unchanged
    assert notes["selling_investments"] is True


def test_render_slot_is_filled_by_code_without_a_model_call():
    # a fake openai client that fails the test if the model is ever called
    def no_call(**kwargs):
        raise AssertionError("the model was called for a slot filled by code")

    client: Any = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=no_call)))
    config = {
        "document_title": "Report",
        "sections": [
            {
                "id": "holdings",
                "title": "Holdings",
                "use_if": "always",
                "template": "The accounts:\n\n<<holdings_table>>",
                "placeholders": {"holdings_table": {"render": "holdings_table"}},
            }
        ],
    }

    report = ReportGenerator(client, "test-model").generate(config, FACTS, DB)

    # the table is in the report and no slot is left unfilled
    assert "| GIA-J | Ann Smith and Ben Smith | General Investment Account | £45,000 |" in report
    assert "<<" not in report
