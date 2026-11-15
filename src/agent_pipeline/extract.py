"""Extract the facts of a client's case once, as structured data.

one model call reads the client files and fills a fixed schema. the sections are then
written from these facts, so every section uses the same accounts, values and amounts.
"""

# standard library
import re
from typing import Literal

# third party
from langfuse.openai import openai  # type: ignore[attr-defined]
from pydantic import BaseModel, Field

# the schema: what the model must return.
# the field descriptions are sent with it, so they are part of the prompt


class Account(BaseModel):
    """An account the report covers, with the value to report."""

    account_id: str = Field(
        description="the account id exactly as in the client database"
    )
    value: float = Field(
        description="the most recent value of the account in the sources"
    )
    value_date: str = Field(description="the date of that value, YYYY-MM-DD")
    # a fixed choice, not free text: code reads this field, so the schema limits its values
    value_source: Literal["client database", "meeting notes", "other source"] = Field(
        description="where that value comes from"
    )


class Action(BaseModel):
    """One thing agreed with the client."""

    action: str = Field(description="what happens, to which account")
    amount: str | None = Field(
        description="the amount exactly as stated in the sources, or null if none is stated"
    )


class Facts(BaseModel):
    """The facts of the case. Every section is written from these."""

    accounts_in_scope: list[Account]
    selling_investments: bool = Field(
        description="true if existing investments are being sold or disposed of"
    )
    situation: str = Field(
        description="objectives, circumstances, risk approach, and anything to handle with care"
    )
    actions: list[Action]
    initial_charge: str | None = Field(
        description="the initial charge stated in the report request, or null"
    )
    to_confirm: list[str] = Field(
        description="everything a person must confirm before the report is final"
    )


def extract_facts(
    openai_client: openai.OpenAI,
    model: str,
    instructions: str,  # the standing rules, same system message as the writing calls
    task: str,  # the extraction prompt from config
    context: str,  # the client's source files
) -> Facts:
    """One model call, its answer parsed into Facts."""
    response = openai_client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"{context}\n\n---\n\n{task}"},
        ],
        # structured output: the answer must match the Facts schema, or the call fails
        response_format=Facts,
        # label for this call in the trace. langfuse reads it and removes it before the
        # request goes to openai, the type checker cannot see that, hence the ignore
        name="extract-facts",  # type: ignore[call-arg]
    )
    message = response.choices[0].message
    # no facts, no report: a refusal stops the run instead of passing on silently
    if message.parsed is None:
        raise ValueError(f"fact extraction failed: {message.refusal}")
    return message.parsed


# checking the facts: the model proposes, code verifies before anything is written

# a number in a text, e.g. 45,000 or 0.5
NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def _numbers(text: str) -> set[float]:
    """Every number in a text: '£45,000 and 0.5%' -> {45000.0, 0.5}."""
    return {float(n.replace(",", "")) for n in NUMBER.findall(text)}


def check_facts(facts: Facts, db: dict, sources: str) -> tuple[Facts, list[str]]:
    """Check the facts against the client database and the source text.

    what can be corrected safely is corrected, the rest is removed. every change is
    returned as a review note, so a person can see what the model got wrong.
    """
    # every account in the db by id. a joint account listed under both holders is one entry
    db_accounts = {
        account["account_id"]: account
        for holder in db["holders"].values()
        for account in holder["accounts"]
    }
    source_numbers = _numbers(sources)
    notes = []

    # accounts: must exist, be open, have a value, appear once
    accounts = []
    for account in facts.accounts_in_scope:
        record = db_accounts.get(account.account_id)
        if record is None:
            notes.append(f"{account.account_id}: not in the client database, removed")
            continue
        if record.get("status") != "open" or record.get("value") is None:
            notes.append(f"{account.account_id}: closed or no value in the client database, removed")
            continue
        if account.account_id in {kept.account_id for kept in accounts}:
            continue  # joint account returned twice, already kept once
        # the value must be the db value or appear in a source, otherwise use the db value
        if account.value != record["value"] and account.value not in source_numbers:
            notes.append(f"{account.account_id}: value {account.value:,.0f} not in the sources, database value used")
            account = account.model_copy(
                update={
                    "value": record["value"],
                    "value_date": record["valuation_date"],
                    "value_source": "client database",
                }
            )
        accounts.append(account)

    # amounts: every number in an amount must appear in a source, otherwise null
    actions = []
    for action in facts.actions:
        if action.amount and not _numbers(action.amount) <= source_numbers:
            notes.append(f"amount '{action.amount}' not in the sources, set to null: {action.action}")
            action = action.model_copy(update={"amount": None})
        actions.append(action)

    # the initial charge, same rule
    initial_charge = facts.initial_charge
    if initial_charge and not _numbers(initial_charge) <= source_numbers:
        notes.append(f"initial charge '{initial_charge}' not in the sources, set to null")
        initial_charge = None

    checked = facts.model_copy(
        update={"accounts_in_scope": accounts, "actions": actions, "initial_charge": initial_charge}
    )
    return checked, notes
