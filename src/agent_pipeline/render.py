"""Parts of the report written by code, not the model.

the facts are already checked, so a fixed format needs no model call: the same input
always gives the same output, and nothing can drift into the wrong cell.
"""

# pipeline steps
from agent_pipeline.extract import Facts

# currency symbols for the codes in the client database. any other code is written as is
SYMBOLS = {"GBP": "£", "EUR": "€", "USD": "$"}


def money(value: float, currency: str = "GBP") -> str:
    """45000.0, 'GBP' -> '£45,000'. pence are kept if there are any, never rounded away."""
    symbol = SYMBOLS.get(currency, f"{currency} ")
    return symbol + f"{value:,.2f}".removesuffix(".00")


def holdings_table(facts: Facts, db: dict) -> str:
    """The accounts in scope as a markdown table: Account | Owner | Type | Value.

    id, owner and type come from the client database, the value from the checked facts.
    """
    rows = ["| Account | Owner | Type | Value |", "|---|---|---|---|"]
    for account in facts.accounts_in_scope:
        # every holder the database lists this account under: two for a joint account
        holders = [
            holder
            for holder in db["holders"].values()
            if any(a["account_id"] == account.account_id for a in holder["accounts"])
        ]
        record = next(a for a in holders[0]["accounts"] if a["account_id"] == account.account_id)
        # a joint account is owned by "Joint" in the database: name the people instead
        owner = record["owner"]
        if owner == "Joint":
            owner = " and ".join(holder["name"] for holder in holders)
        value = money(account.value, record.get("currency", "GBP"))
        rows.append(f"| {account.account_id} | {owner} | {record['type']} | {value} |")
    return "\n".join(rows)


# slots filled by code: the name used in config -> the function that fills it
RENDERERS = {"holdings_table": holdings_table}
