"""Extract the facts of a client's case once, as structured data.

one model call reads the client files and fills a fixed schema. the sections are then
written from these facts, so every section uses the same accounts, values and amounts.
"""

# standard library
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
