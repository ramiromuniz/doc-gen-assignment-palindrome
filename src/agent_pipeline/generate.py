"""Generate an advice report for a client from the template config.

Usage:
    python -m agent_pipeline.generate --client client_01_clean
"""

# standard library
import argparse
import json
import os
from pathlib import Path

# third party
from dotenv import load_dotenv

# langfuse tracing. without keys it does nothing and the pipeline runs the same
from langfuse import get_client, observe, propagate_attributes
# drop in for the openai module that logs every call. langfuse patches it at runtime,
# which the type checker cannot see, hence the ignore
from langfuse.openai import openai  # type: ignore[attr-defined]

# document helpers: reading source files and rendering the final markdown
from document_formatter.formatting import format_document
from document_formatter.loading import read_file

# pipeline steps
from agent_pipeline.extract import Facts, check_facts, extract_facts
from agent_pipeline.render import RENDERERS

# the system of record for which accounts exist, who holds them and their values (fde_notes)
DATABASE_FILE = "client_data_db.json"


class ReportGenerator:
    """Builds a report one section at a time from the template config."""

    def __init__(self, openai_client: openai.OpenAI, model: str) -> None:
        self._openai = openai_client
        self._model = model

    def generate(self, config: dict, context: str, facts: Facts, db: dict) -> str:
        # writers get the shared rules plus how to write for the client
        instructions = (
            prompt_text(config.get("global_instructions", ""))
            + "\n\n"
            + prompt_text(config.get("writing_instructions", ""))
        )
        sections = []
        for section in config["sections"]:
            if not self._section_applies(section, facts):
                continue
            sections.append(
                {
                    "title": section.get("title", ""),
                    "content": self._build_section(section, context, instructions, facts, db),
                }
            )
        return format_document(config, sections)

    # a step in the trace, its output is the yes/no decision
    @observe(name="check-section-applies", capture_input=False)
    def _section_applies(self, section: dict, facts: Facts) -> bool:
        rule = section.get("use_if", "always")
        get_client().update_current_span(input={"section": section.get("id"), "use_if": rule})
        if rule == "always":
            return True
        # the rule names a yes/no fact, e.g. "selling_investments", decided once at
        # extraction. no model call here; a rule naming no fact fails loudly
        return bool(getattr(facts, rule))

    # a step in the trace, the model calls for its placeholders nest inside it
    @observe(name="build-section", capture_input=False)
    def _build_section(
        self, section: dict, context: str, instructions: str, facts: Facts, db: dict
    ) -> str:
        get_client().update_current_span(
            input={"section": section.get("id"), "template": section["template"]}
        )
        content = section["template"]
        for name, spec in section.get("placeholders", {}).items():
            if "render" in spec:
                # a fixed format filled by code from the checked facts, no model call
                content = content.replace(f"<<{name}>>", RENDERERS[spec["render"]](facts, db))
                continue
            value = self._ask(
                instructions,
                prompt_text(spec["prompt"]),
                context,
                call_name="fill-placeholder",
                call_metadata={"section": section.get("id"), "placeholder": name},
            )
            content = content.replace(f"<<{name}>>", value)
        return content

    def _ask(
        self,
        instructions: str,  # the standing rules, same for every call
        task: str,  # what this call must produce
        context: str,  # the client's source files
        *,
        call_name: str = "llm-call",  # label for this call in the trace
        call_metadata: dict | None = None,  # e.g. which section and placeholder it fills
    ) -> str:
        response = self._openai.chat.completions.create(  # type: ignore[call-overload]
            model=self._model,
            # rules as the system message, kept apart from the client data and the task
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"{context}\n\n---\n\n{task}"},
            ],
            # name and metadata are read by langfuse and removed before the request
            # goes to openai, so what the model receives does not change
            name=call_name,
            metadata=call_metadata or {},
        )
        return response.choices[0].message.content.strip()


def prompt_text(prompt: str | list[str]) -> str:
    """Prompts in config can be one string or a list of lines (one rule per line reads better in a diff)."""
    return "\n".join(prompt) if isinstance(prompt, list) else prompt


def read_client_context(client_dir: Path, filenames: list[str]) -> str:
    """Read the named files from the client folder and concatenate them into one context string."""
    parts = []
    for name in filenames:
        parts.append(f"=== {name} ===\n{read_file(client_dir / name)}")
    return "\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an advice report for a client."
    )
    parser.add_argument("--client", required=True, help="folder name under data/")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--config", type=Path, default=Path("config/template_config.json")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--facts-only", action="store_true", help="stop after extracting the facts")
    args = parser.parse_args()

    load_dotenv()
    openai_client = openai.OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-6.1-sol")
    generator = ReportGenerator(openai_client, model)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    client_dir = args.data_dir / args.client
    # only client data reaches the model. guidance for engineers and general material
    # (listed in config) is skipped; any other file is read, so a new source is never lost
    skipped = set(config.get("non_client_files", []))
    filenames = sorted(p.name for p in client_dir.iterdir() if p.is_file() and p.name not in skipped)
    print(f"Sources used: {filenames}")
    context = read_client_context(client_dir, filenames)

    # root of the trace: one per report, every step and model call nests under it.
    # tagged with the client so runs can be filtered per client
    with get_client().start_as_current_observation(
        name="generate-report",
        as_type="chain",
        input={"client": args.client, "sources": filenames},
    ) as run, propagate_attributes(trace_name="generate-report", tags=[args.client]):
        # step 1: decide the facts of the case once. only the shared rules: facts are
        # neutral notes, how to write for the client is the writers' job
        facts = extract_facts(
            openai_client,
            model,
            prompt_text(config["global_instructions"]),
            prompt_text(config["extraction_prompt"]),
            context,
        )
        # step 2: check the facts against the client database and the sources, in code
        db = json.loads((client_dir / DATABASE_FILE).read_text(encoding="utf-8"))
        facts, review_notes = check_facts(facts, db, context)
        for note in review_notes:
            print(f"Review: {note}")
        # step 3: write the report. the sections still read the raw files for now
        report = None if args.facts_only else generator.generate(config, context, facts, db)
        run.update(output=report or facts.model_dump(), metadata={"review_notes": review_notes})
    # traces are sent in the background, flush so they are not lost when the script exits
    get_client().flush()

    # the facts are saved next to the report with what code corrected: for audit
    args.output_dir.mkdir(parents=True, exist_ok=True)
    facts_path = args.output_dir / f"{args.client}.facts.json"
    saved = {"facts": facts.model_dump(), "review_notes": review_notes}
    facts_path.write_text(json.dumps(saved, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {facts_path}")
    if report is None:
        return

    out_path = args.output_dir / f"{args.client}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
