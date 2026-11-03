"""Generate language-aware API / reference documentation from the code layer.

Chooses a documentation *style* based on the repository's dominant languages:

- Python-heavy  → Sphinx-ready reStructuredText project (``sphinx``)
- JS/TS-heavy   → TypeDoc-oriented Markdown reference (``typedoc``)
- Mixed / other → Portable Markdown API reference (``markdown``)

Does not require Sphinx/TypeDoc to be installed — it writes source trees the
user can build locally (``sphinx-build``, ``npx typedoc``, or open the Markdown).
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.repo_scanner import IGNORED_DIRS, INCLUDED_EXTENSIONS

DocStyle = Literal["sphinx", "typedoc", "markdown"]

_PY_EXTS = {".py"}
_JS_EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
_CODE_EXTS = _PY_EXTS | _JS_EXTS | {".go", ".java", ".rb", ".rs", ".svelte"}


@dataclass
class SymbolRef:
    name: str
    kind: str  # class | function | interface | type | const | method
    file_path: str
    lineno: int | None = None
    signature: str = ""
    docstring: str = ""
    language: str = ""


@dataclass
class ReferenceDocResult:
    style: DocStyle
    style_label: str
    output_dir: str
    index_file: str
    files_written: list[str] = field(default_factory=list)
    symbol_count: int = 0
    language_counts: dict[str, int] = field(default_factory=dict)
    build_hint: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style,
            "style_label": self.style_label,
            "output_dir": self.output_dir,
            "index_file": self.index_file,
            "files_written": self.files_written,
            "symbol_count": self.symbol_count,
            "language_counts": self.language_counts,
            "build_hint": self.build_hint,
            "summary": self.summary,
        }


def _symbols_payload(symbols: list[SymbolRef]) -> list[dict[str, Any]]:
    return [
        {
            "name": s.name,
            "kind": s.kind,
            "file_path": s.file_path,
            "lineno": s.lineno,
            "signature": s.signature,
            "docstring": s.docstring,
            "language": s.language,
        }
        for s in symbols
    ]


def _modules_payload(symbols: list[SymbolRef]) -> list[dict[str, Any]]:
    grouped = _group_by_module(symbols)
    return [
        {
            "module": module,
            "symbol_count": len(syms),
            "symbols": _symbols_payload(syms),
        }
        for module, syms in grouped.items()
    ]


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in INCLUDED_EXTENSIONS and path.suffix in _CODE_EXTS:
            files.append(path)
    return files


def detect_doc_style(files: list[Path]) -> tuple[DocStyle, dict[str, int]]:
    counts: Counter[str] = Counter()
    for f in files:
        if f.suffix in _PY_EXTS:
            counts["python"] += 1
        elif f.suffix in _JS_EXTS or f.suffix == ".svelte":
            counts["javascript"] += 1
        elif f.suffix == ".go":
            counts["go"] += 1
        elif f.suffix == ".java":
            counts["java"] += 1
        elif f.suffix == ".rs":
            counts["rust"] += 1
        else:
            counts["other"] += 1
    lang_counts = dict(counts)
    if not counts:
        return "markdown", lang_counts
    top, top_n = counts.most_common(1)[0]
    total = sum(counts.values())
    # Prefer Sphinx/TypeDoc when that language is the plurality (≥35%, or sole language).
    share = top_n / max(total, 1)
    if top == "python" and (share >= 0.35 or len(counts) == 1):
        return "sphinx", lang_counts
    if top == "javascript" and (share >= 0.35 or len(counts) == 1):
        return "typedoc", lang_counts
    return "markdown", lang_counts


def _py_symbols(path: Path, root: Path) -> list[SymbolRef]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    try:
        source = path.read_text(errors="ignore")
        tree = ast.parse(source)
    except Exception:
        return []
    out: list[SymbolRef] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            out.append(
                SymbolRef(
                    name=node.name,
                    kind="class",
                    file_path=rel,
                    lineno=getattr(node, "lineno", None),
                    signature=f"class {node.name}",
                    docstring=doc.strip().splitlines()[0] if doc.strip() else "",
                    language="python",
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    cdoc = ast.get_docstring(child) or ""
                    args = ", ".join(a.arg for a in child.args.args if a.arg != "self")
                    out.append(
                        SymbolRef(
                            name=f"{node.name}.{child.name}",
                            kind="method",
                            file_path=rel,
                            lineno=getattr(child, "lineno", None),
                            signature=f"def {child.name}({args})",
                            docstring=cdoc.strip().splitlines()[0] if cdoc.strip() else "",
                            language="python",
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            args = ", ".join(a.arg for a in node.args.args)
            out.append(
                SymbolRef(
                    name=node.name,
                    kind="function",
                    file_path=rel,
                    lineno=getattr(node, "lineno", None),
                    signature=f"def {node.name}({args})",
                    docstring=doc.strip().splitlines()[0] if doc.strip() else "",
                    language="python",
                )
            )
    return out


def _js_symbols(path: Path, root: Path) -> list[SymbolRef]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return []
    lang = "typescript" if path.suffix in {".ts", ".tsx"} else "javascript"
    out: list[SymbolRef] = []
    patterns = [
        (r"export\s+(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)", "function"),
        (r"export\s+(?:abstract\s+)?class\s+([A-Za-z0-9_]+)", "class"),
        (r"export\s+(?:interface|type)\s+([A-Za-z0-9_]+)", "interface"),
        (r"export\s+const\s+([A-Za-z0-9_]+)", "const"),
    ]
    for pattern, kind in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            out.append(
                SymbolRef(
                    name=name,
                    kind=kind,
                    file_path=rel,
                    lineno=text[: match.start()].count("\n") + 1,
                    signature=match.group(0)[:120],
                    docstring="",
                    language=lang,
                )
            )
    if path.suffix == ".svelte":
        out.append(
            SymbolRef(
                name=path.stem,
                kind="component",
                file_path=rel,
                signature=f"<{path.stem} />",
                docstring=f"Svelte component `{path.name}`",
                language="svelte",
            )
        )
    return out


def extract_symbols(root: Path, files: list[Path], limit: int = 400) -> list[SymbolRef]:
    symbols: list[SymbolRef] = []
    for path in files:
        if len(symbols) >= limit:
            break
        if path.suffix in _PY_EXTS:
            symbols.extend(_py_symbols(path, root))
        elif path.suffix in _JS_EXTS or path.suffix == ".svelte":
            symbols.extend(_js_symbols(path, root))
    return symbols[:limit]


def _group_by_module(symbols: list[SymbolRef]) -> dict[str, list[SymbolRef]]:
    grouped: dict[str, list[SymbolRef]] = {}
    for sym in symbols:
        module = sym.file_path.rsplit("/", 1)[0] if "/" in sym.file_path else "(root)"
        grouped.setdefault(module, []).append(sym)
    return dict(sorted(grouped.items(), key=lambda kv: kv[0]))


def _write_markdown_reference(
    out_dir: Path,
    repo_name: str,
    style: DocStyle,
    symbols: list[SymbolRef],
    lang_counts: dict[str, int],
) -> tuple[str, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    index = out_dir / "API_REFERENCE.md"
    grouped = _group_by_module(symbols)
    lines = [
        f"# {repo_name} — API Reference",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"from the C4 **code** layer ({style} style).",
        "",
        "## Language mix",
        "",
    ]
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- **{lang}**: {count} source files")
    lines += ["", f"**Symbols indexed:** {len(symbols)}", "", "## Modules", ""]
    for module, syms in grouped.items():
        lines.append(f"### `{module}`")
        lines.append("")
        for sym in syms:
            loc = f"{sym.file_path}:{sym.lineno}" if sym.lineno else sym.file_path
            desc = sym.docstring or sym.signature or sym.kind
            lines.append(f"- **`{sym.name}`** _{sym.kind}_ — {desc} (`{loc}`)")
        lines.append("")
    index.write_text("\n".join(lines), encoding="utf-8")
    written.append(str(index))
    return str(index), written


def _write_sphinx_project(
    out_dir: Path,
    repo_name: str,
    symbols: list[SymbolRef],
    lang_counts: dict[str, int],
    project_root: Path,
) -> tuple[str, list[str], str]:
    sphinx_dir = out_dir / "sphinx"
    sphinx_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    conf = f'''# Autogenerated Sphinx conf for {repo_name}
project = "{repo_name}"
copyright = "{datetime.now(timezone.utc).year}"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
templates_path = ["_templates"]
exclude_patterns = ["_build"]
html_theme = "alabaster"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"{project_root}").resolve()))
'''
    conf_path = sphinx_dir / "conf.py"
    conf_path.write_text(conf, encoding="utf-8")
    written.append(str(conf_path))

    # Module RST pages from discovered python files
    py_modules = sorted({s.file_path for s in symbols if s.language == "python"})
    toctree: list[str] = []
    api_dir = sphinx_dir / "api"
    api_dir.mkdir(exist_ok=True)
    for rel in py_modules[:80]:
        if not rel.endswith(".py"):
            continue
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", mod)
        page = api_dir / f"{safe}.rst"
        page.write_text(
            f"{mod}\n{'=' * len(mod)}\n\n.. automodule:: {mod}\n   :members:\n   :undoc-members:\n   :show-inheritance:\n",
            encoding="utf-8",
        )
        written.append(str(page))
        toctree.append(f"api/{safe}")

    index_rst = sphinx_dir / "index.rst"
    toc_block = "\n   ".join(toctree) if toctree else "(no python modules discovered)"
    index_rst.write_text(
        f"""{repo_name} Reference
{'=' * (len(repo_name) + 10)}

Sphinx reference generated from the C4 code layer.

.. toctree::
   :maxdepth: 2
   :caption: API

   {toc_block}

Symbol inventory
----------------

See also the portable Markdown companion ``../API_REFERENCE.md``.
""",
        encoding="utf-8",
    )
    written.append(str(index_rst))

    md_index, md_files = _write_markdown_reference(
        out_dir, repo_name, "sphinx", symbols, lang_counts
    )
    written.extend(md_files)
    hint = (
        f"cd {sphinx_dir} && pip install sphinx && "
        f"sphinx-build -b html . _build/html"
    )
    return md_index, written, hint


def _write_typedoc_project(
    out_dir: Path,
    repo_name: str,
    symbols: list[SymbolRef],
    lang_counts: dict[str, int],
) -> tuple[str, list[str], str]:
    td_dir = out_dir / "typedoc"
    td_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    readme = td_dir / "README.md"
    readme.write_text(
        f"""# {repo_name} — TypeDoc / JSDoc reference

This folder was generated from the C4 **code** layer for a JavaScript/TypeScript-dominant repo.

## Build with TypeDoc

```bash
npx --yes typedoc --out docs --entryPointStrategy expand src
```

Or open the portable Markdown inventory at ``../API_REFERENCE.md``.
""",
        encoding="utf-8",
    )
    written.append(str(readme))
    md_index, md_files = _write_markdown_reference(
        out_dir, repo_name, "typedoc", symbols, lang_counts
    )
    written.extend(md_files)
    hint = "npx --yes typedoc --out docs --entryPointStrategy expand <entry>"
    return md_index, written, hint


_STYLE_LABELS = {
    "sphinx": "Sphinx (reStructuredText / autodoc)",
    "typedoc": "TypeDoc / JSDoc (TypeScript & JavaScript)",
    "markdown": "Portable Markdown API reference",
}


def preview_reference_docs(
    project_path: str | Path,
    style: DocStyle | Literal["auto"] = "auto",
) -> dict[str, Any]:
    """Inspect the code layer and return a browseable symbol inventory (no files written)."""
    root = Path(project_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Project path does not exist: {root}")

    files = _iter_source_files(root)
    detected, lang_counts = detect_doc_style(files)
    chosen: DocStyle = detected if style == "auto" else style  # type: ignore[assignment]
    if chosen not in {"sphinx", "typedoc", "markdown"}:
        chosen = detected

    symbols = extract_symbols(root, files)
    return {
        "source": str(root),
        "repo_name": root.name,
        "style": chosen,
        "style_label": _STYLE_LABELS[chosen],
        "detected_style": detected,
        "symbol_count": len(symbols),
        "language_counts": lang_counts,
        "file_count": len(files),
        "modules": _modules_payload(symbols),
        "summary": (
            f"{_STYLE_LABELS[chosen]} recommended for '{root.name}' — "
            f"{len(symbols)} symbols across {len(files)} source files."
        ),
    }


def generate_reference_docs(
    project_path: str | Path,
    output_folder: str | Path | None = None,
    style: DocStyle | Literal["auto"] = "auto",
) -> dict[str, Any]:
    root = Path(project_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Project path does not exist: {root}")

    files = _iter_source_files(root)
    detected, lang_counts = detect_doc_style(files)
    chosen: DocStyle = detected if style == "auto" else style  # type: ignore[assignment]
    if chosen not in {"sphinx", "typedoc", "markdown"}:
        chosen = detected

    symbols = extract_symbols(root, files)
    out_dir = (
        Path(output_folder).expanduser().resolve()
        if output_folder
        else (root / "documentation" / "reference")
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    if chosen == "sphinx":
        index_file, written, hint = _write_sphinx_project(
            out_dir, root.name, symbols, lang_counts, root
        )
    elif chosen == "typedoc":
        index_file, written, hint = _write_typedoc_project(
            out_dir, root.name, symbols, lang_counts
        )
    else:
        index_file, written = _write_markdown_reference(
            out_dir, root.name, "markdown", symbols, lang_counts
        )
        hint = f"Open {index_file} in any Markdown viewer."

    result = ReferenceDocResult(
        style=chosen,
        style_label=_STYLE_LABELS[chosen],
        output_dir=str(out_dir),
        index_file=index_file,
        files_written=written,
        symbol_count=len(symbols),
        language_counts=lang_counts,
        build_hint=hint,
        summary=(
            f"Generated {_STYLE_LABELS[chosen]} for '{root.name}' with {len(symbols)} symbols "
            f"across {sum(lang_counts.values())} source files → {out_dir}"
        ),
    )
    payload = result.to_dict()
    payload["repo_name"] = root.name
    payload["detected_style"] = detected
    payload["file_count"] = len(files)
    payload["modules"] = _modules_payload(symbols)
    return payload
