"""Condenses a source tree into a bounded chunk of text an LLM can read.

This is deliberately simple — a scaffold, not a real static-analysis pipeline.
It walks the tree, lists the file structure, then includes file contents
(truncated) up to a character budget, biggest-first-skipped so smaller,
more informative files (manifests, entry points) tend to survive the cut.
Local models have far smaller usable context than cloud ones, so this budget
is the main lever for "does this fit" — see README.md for why a real
implementation needs chunking/retrieval instead for anything but a small repo.
"""

from __future__ import annotations

from pathlib import Path

from app.config import settings

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".svelte-kit",
    ".idea",
    ".vscode",
}

INCLUDED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".svelte",
    ".go",
    ".java",
    ".rb",
    ".rs",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}

MAX_FILE_CHARS = 3000


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in INCLUDED_EXTENSIONS:
            yield path


def build_repo_context(repo_path: str, max_chars: int | None = None) -> str:
    """Return a bounded text summary of the repo: a file tree, then truncated
    file contents, stopping once the character budget is exhausted."""

    budget = max_chars or settings.max_context_chars
    root = Path(repo_path).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo_path does not exist: {root}")

    files = list(_iter_files(root))
    if not files:
        raise ValueError(
            f"No source files found under {root} (looked for {sorted(INCLUDED_EXTENSIONS)})"
        )

    tree_lines = [str(f.relative_to(root)) for f in files]
    tree_section = "## File tree\n" + "\n".join(tree_lines) + "\n\n## File contents\n"

    remaining = budget - len(tree_section)
    sections: list[str] = []
    for f in files:
        if remaining <= 0:
            sections.append(f"\n... ({len(files) - len(sections)} more files omitted, context budget reached)")
            break
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        truncated = text[:MAX_FILE_CHARS]
        suffix = "\n... (truncated)" if len(text) > MAX_FILE_CHARS else ""
        block = f"\n### {f.relative_to(root)}\n```\n{truncated}{suffix}\n```\n"
        if len(block) > remaining:
            break
        sections.append(block)
        remaining -= len(block)

    return tree_section + "".join(sections)
