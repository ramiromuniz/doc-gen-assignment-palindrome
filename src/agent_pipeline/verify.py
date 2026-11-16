"""Verify the extracted facts in code, before anything is written.

the model proposes, code verifies: every account, value and amount is checked against the
client database and the context. what can be corrected safely is corrected, the rest is
removed, and every change is returned as a review note for the adviser.
"""

# standard library
import re

# pipeline steps
from agent_pipeline.extract import Facts

# a number in a text, e.g. 45,000 or 0.5
NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _numbers(text: str) -> set[float]:
    """Every number in a text: '£45,000 and 0.5%' -> {45000.0, 0.5}."""
    return {float(n.replace(",", "")) for n in NUMBER.findall(text)}


def verify_facts(facts: Facts, db: dict, context: str) -> tuple[Facts, list[str]]:
    """Check the facts against the client database and the context.

    what can be corrected safely is corrected, the rest is removed. every change is
    returned as a review note, so a person can see what the model got wrong.
    """
    # every account in the db by id. a joint account listed under both holders is one entry
    db_accounts = {
        account["account_id"]: account
        for holder in db["holders"].values()
        for account in holder["accounts"]
    }
    context_numbers = _numbers(context)
    notes = []

    # accounts: 4 checks: must exist, be open, have a value, appear once
    accounts = []
    for account in facts.accounts_in_scope:
        record = db_accounts.get(account.account_id)
        # 1: the account id must exist in the db
        if record is None:
            notes.append(f"{account.account_id}: not in the client database, removed")
            continue
        # 2: the account must be open and have a value
        if record.get("status") != "open" or record.get("value") is None:
            notes.append(
                f"{account.account_id}: closed or no value in the client database, removed"
            )
            continue
        # 3: joint accounts are listed under both holders, but only one copy is kept
        if account.account_id in {kept.account_id for kept in accounts}:
            continue  # joint account returned twice, already kept once
        # 4: the value must be the db value or appear in the context, otherwise use the db value
        if account.value != record["value"] and account.value not in context_numbers:
            notes.append(
                f"{account.account_id}: value {account.value:,.0f} not in the sources, database value used"
            )
            # keep the model's account, with the db value, date and source
            account = account.model_copy(
                update={
                    "value": record["value"],
                    "value_date": record["valuation_date"],
                    "value_source": "client database",
                }
            )
        # the account passed all checks, keep it
        accounts.append(account)

    # amounts: every number in an amount must appear in the context, otherwise null
    actions = []
    for action in facts.actions:
        if action.amount and not _numbers(action.amount) <= context_numbers:
            notes.append(
                f"amount '{action.amount}' not in the sources, set to null: {action.action}"
            )
            action = action.model_copy(update={"amount": None})
        actions.append(action)

    # the initial charge, same rule
    initial_charge = facts.initial_charge
    if initial_charge and not _numbers(initial_charge) <= context_numbers:
        notes.append(
            f"initial charge '{initial_charge}' not in the sources, set to null"
        )
        initial_charge = None

    verified = facts.model_copy(
        update={
            "accounts_in_scope": accounts,
            "actions": actions,
            "initial_charge": initial_charge,
        }
    )
    return verified, notes
