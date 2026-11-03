"""Tests for language-aware code reference documentation generation."""

from __future__ import annotations

from pathlib import Path

from app.reference_docs import detect_doc_style, generate_reference_docs


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_detect_sphinx_for_python_repo(tmp_path: Path) -> None:
    for name in ("a.py", "b.py", "c.py", "d.py"):
        _write(tmp_path / name, "def f():\n    pass\n")
    style, counts = detect_doc_style(list(tmp_path.glob("*.py")))
    assert style == "sphinx"
    assert counts["python"] == 4


def test_generate_sphinx_and_markdown(tmp_path: Path) -> None:
    _write(
        tmp_path / "pkg" / "service.py",
        '"""Service module."""\n\nclass Greeter:\n    """Says hello."""\n\n    def hello(self, name: str) -> str:\n        """Greet someone."""\n        return f"hi {name}"\n\ndef run():\n    """Entry."""\n    return Greeter().hello("world")\n',
    )
    out = tmp_path / "docs-out"
    result = generate_reference_docs(tmp_path, output_folder=out, style="auto")
    assert result["style"] == "sphinx"
    assert result["symbol_count"] >= 2
    assert Path(result["index_file"]).exists()
    assert (out / "sphinx" / "conf.py").exists()
    assert (out / "sphinx" / "index.rst").exists()


def test_generate_typedoc_style(tmp_path: Path) -> None:
    for name in ("one.ts", "two.ts", "three.ts", "four.ts"):
        _write(tmp_path / "src" / name, f"export function {name[:-3]}() {{ return 1; }}\n")
    out = tmp_path / "ref"
    result = generate_reference_docs(tmp_path, output_folder=out, style="auto")
    assert result["style"] == "typedoc"
    assert (out / "typedoc" / "README.md").exists()
    assert Path(result["index_file"]).exists()
