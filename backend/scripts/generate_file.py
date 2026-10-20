#!/usr/bin/env python3
"""Generate or update one file from an instruction file, using the local
model via LM Studio.

The instruction lives in its own text file rather than on the command line —
easier to write/edit multi-line briefs, no shell quoting headaches, and the
instruction is kept around for reference/reuse.

If the target file already exists, its current content is sent to the model
as context so it can edit/extend it rather than starting from scratch — so
this also works as a simple "develop this file further" tool, not just
one-shot creation.

Examples:
  python scripts/generate_file.py notes/plan.md instructions/plan_brief.txt

  python scripts/generate_file.py src/utils.py instructions/add_validator.txt -y

  python scripts/generate_file.py src/big_module.py instructions/big_module.txt --model prism-ml/bonsai-27b
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import llm_client  # noqa: E402
from app.config import settings  # noqa: E402

SYSTEM_PROMPT_TEMPLATE = """You are a precise file-content generator.

Output ONLY the complete, final content of the target file — no markdown code \
fences, no explanations, no commentary before or after. Your entire response \
becomes the literal contents of the file on disk.

Target file: {filename}
{existing_section}"""

EXISTING_FILE_TEMPLATE = """
This file already exists. Its current content is below. Update or extend it \
according to the instruction below rather than starting from scratch, unless \
the instruction clearly asks for a full rewrite.

--- current content of {filename} ---
{content}
--- end current content ---
"""


def build_system_prompt(path: Path, existing_content: str | None) -> str:
    existing_section = ""
    if existing_content is not None:
        existing_section = EXISTING_FILE_TEMPLATE.format(filename=path.name, content=existing_content)
    return SYSTEM_PROMPT_TEMPLATE.format(filename=path.name, existing_section=existing_section)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_path", help="Path to the file to create or update")
    parser.add_argument("instruction_file", help="Path to a text file containing the instruction")
    parser.add_argument(
        "--model", default=None, help=f"Override the model to use (default: {settings.lm_studio_model})"
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Overwrite an existing file without asking")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    instruction_file = Path(args.instruction_file).expanduser().resolve()
    if not instruction_file.exists():
        print(f"[FAIL] Instruction file not found: {instruction_file}")
        return 1
    instruction = instruction_file.read_text()
    if not instruction.strip():
        print(f"[FAIL] Instruction file is empty: {instruction_file}")
        return 1

    output_path = Path(args.output_path).expanduser().resolve()
    existing_content = output_path.read_text() if output_path.exists() else None
    system_prompt = build_system_prompt(output_path, existing_content)

    model = args.model or settings.lm_studio_model
    mode = "Updating" if existing_content is not None else "Generating"
    print(f"{mode} {output_path} with model '{model}'...\n")

    try:
        content = llm_client.chat_text(system_prompt, instruction, model=model)
    except Exception as exc:  # noqa: BLE001 — surface any failure (connection, model error) directly
        print(f"[FAIL] Generation failed: {exc}")
        print("  -> Is LM Studio's server running with this model loaded? Try scripts/check_lmstudio.py")
        return 1

    print("----- Generated content -----")
    print(content)
    print("------------------------------\n")

    if output_path.exists() and not args.yes:
        answer = input(f"'{output_path}' already exists. Overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted — nothing written.")
            return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    print(f"[OK] Wrote {len(content)} chars to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
