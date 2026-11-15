"""Tracing is optional: with no langfuse keys the pipeline must still run.

reviewers will run the repo from a clean checkout without our langfuse keys,
so this checks the report still gets built when tracing has nothing to send to.
"""

from types import SimpleNamespace
from typing import Any

from agent_pipeline.extract import Facts
from agent_pipeline.generate import ReportGenerator


class FakeCompletions:
    """Stands in for openai, records each request and answers 'no' (no network)."""

    def __init__(self):
        self.requests = []

    # same shape as openai's chat.completions.create, so the pipeline can't tell the difference
    def create(self, **kwargs):
        self.requests.append(kwargs)
        message = SimpleNamespace(content="no")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_pipeline_runs_without_tracing_keys(monkeypatch):
    # remove the langfuse keys for this test only, like a reviewer's machine
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    # fake openai client: client.chat.completions.create(...) goes to FakeCompletions.
    # typed as Any because it only mimics the bits of openai.OpenAI the pipeline uses
    client: Any = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    # smallest config that exercises both paths:
    # intro is always included, tax only if the facts say something is sold
    config = {
        "document_title": "Report",
        "sections": [
            {"id": "intro", "title": "Intro", "use_if": "always", "template": "Hello."},
            {"id": "tax", "title": "Tax", "use_if": "selling_investments", "template": "Tax."},
        ],
    }
    # nothing is sold in this case
    facts = Facts(
        accounts_in_scope=[],
        selling_investments=False,
        situation="",
        actions=[],
        initial_charge=None,
        to_confirm=[],
    )

    report = ReportGenerator(client, "gpt-4o-mini").generate(config, "CONTEXT", facts)

    # intro always included, tax dropped because nothing is sold
    assert "## Intro" in report
    assert "## Tax" not in report
    # no model calls: the gate reads the facts, and these sections have no slots to fill
    assert len(client.chat.completions.requests) == 0
