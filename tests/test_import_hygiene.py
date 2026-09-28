"""Import-hygiene guards (package-level import rules, enforced not documented).

Two rules, both checked statically (no DB, no import of nylium itself):

1. Cross-package file imports are forbidden. ``from nylium.Pkg.Mod import X``
   is only legal when ``Mod`` is in *our own* package or one of its ancestors
   (the granular intra-tree links that keep each package acyclic). Importing
   a file from another package must go through that package's public ``__all__``:
   ``from nylium.Pkg import X``.

2. Every ``from nylium.Pkg import X`` must resolve: either ``X`` is in
   ``Pkg.__all__``, or ``X`` is a subpackage of ``Pkg``.

These are what make renaming/moving a class a one-file change instead of a
40-file ripple, and they stop the two silent failure modes that bite hardest:
``name == submodule`` shadowing and a forgotten ``__all__`` re-export.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "nylium"


def _cur_pkg(path: Path) -> str:
    rel = path.parent.relative_to(SRC)
    return "nylium" if str(rel) == "." else "nylium." + str(rel).replace("/", ".")


def _module_kind(dotted: str) -> str | None:
    rel = dotted.replace(".", "/")
    if (SRC / f"{rel}.py").exists():
        return "file"
    if (SRC / rel / "__init__.py").exists():
        return "pkg"
    return None


def _pkg_path(pkg: str) -> Path:
    rel = pkg.removeprefix("nylium").strip(".")
    return SRC / rel / "__init__.py" if rel else SRC / "__init__.py"


def _all_names(pkg: str) -> set[str]:
    path = _pkg_path(pkg)
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    try:
                        return set(ast.literal_eval(node.value))
                    except Exception:
                        return set()
    return set()


def _top_level_imports(path: Path) -> list[ast.ImportFrom]:
    """ImportFrom nodes at module top level, skipping `if TYPE_CHECKING:`."""
    tree = ast.parse(path.read_text())
    out: list[ast.ImportFrom] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            out.append(node)
        elif isinstance(node, ast.If):
            # skip `if TYPE_CHECKING:` blocks — type-only links, no runtime edge
            test = ast.unparse(node.test)
            if test in {"TYPE_CHECKING", "typing.TYPE_CHECKING"}:
                continue
            out.extend(n for n in node.body if isinstance(n, ast.ImportFrom))
    return out


def test_cross_package_imports_go_through_all() -> None:
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        cur = _cur_pkg(path)
        for node in _top_level_imports(path):
            mod = node.module
            if not mod or not mod.startswith("nylium"):
                continue
            if _module_kind(mod) != "file":
                continue
            parent = ".".join(mod.split(".")[:-1])
            if parent == cur or cur.startswith(parent + "."):
                continue  # own package or ancestor — granular link allowed
            for alias in node.names:
                violations.append(
                    f"{path.relative_to(SRC.parent.parent)}: `from {mod} import {alias.name}` crosses package boundary; use `from {parent} import {alias.name}`"
                )
    assert not violations, "cross-package file imports:\n" + "\n".join(violations)


def test_package_imports_resolve_to_all() -> None:
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in _top_level_imports(path):
            mod = node.module
            if not mod or not mod.startswith("nylium"):
                continue
            if _module_kind(mod) != "pkg":
                continue
            exported = _all_names(mod)
            for alias in node.names:
                if alias.name in exported:
                    continue
                if _module_kind(f"{mod}.{alias.name}") == "pkg":
                    continue  # importing a subpackage
                violations.append(
                    f"{path.relative_to(SRC.parent.parent)}: `from {mod} import {alias.name}` — {alias.name!r} is not in {mod}.__all__"
                )
    assert not violations, "unresolved package imports:\n" + "\n".join(violations)
