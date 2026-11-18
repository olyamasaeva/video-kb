"""Спеки исполняемы: у каждого требования `openspec/specs` есть тест, у каждой метки — требование.

Требование — `### Requirement: <ID> …`, тест — `@pytest.mark.contract("<ID>")`.
Изменение в работе (`openspec/changes/<имя>/specs`) может добавить метку раньше,
чем дельта уедет в `openspec/specs` при архивации, и снять требование из REMOVED.
Строка «- Тест: tests/<файл>::<функция>» под сценарием должна называть
существующий тест с меткой того же требования.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "openspec" / "specs"
CHANGES = ROOT / "openspec" / "changes"
REQUIREMENT = re.compile(r"^### Requirement: (\S+)", re.MULTILINE)
SECTION = re.compile(r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements\s*$", re.MULTILINE)
NAMED_TEST = re.compile(r"^- Тест: `(tests/[^`:]+::\w+)`", re.MULTILINE)


def spec_ids():
    return {m for f in SPECS.glob("*/spec.md") for m in REQUIREMENT.findall(f.read_text())}


def change_ids():
    touched, removed = set(), set()
    for f in CHANGES.glob("*/specs/*/spec.md"):
        text = f.read_text()
        heads = list(SECTION.finditer(text))
        for i, head in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            ids = set(REQUIREMENT.findall(text[head.end() : end]))
            (removed if head.group(1) == "REMOVED" else touched).update(ids)
    return touched, removed


def marked_tests():
    """{'tests/<файл>::<функция>': [ID, …]} по меткам `contract`."""
    found = {}
    for f in sorted((ROOT / "tests").glob("*.py")):
        for node in ast.walk(ast.parse(f.read_text())):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Attribute)
                    and dec.func.attr == "contract"
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                ):
                    found.setdefault(f"tests/{f.name}::{node.name}", []).append(dec.args[0].value)
    return found


def marker_ids():
    found = {}
    for where, ids in marked_tests().items():
        for i in ids:
            found.setdefault(i, []).append(where)
    return found


def named_tests():
    """[(ID требования, названный тест)] по строкам `- Тест:` в openspec/specs."""
    pairs = []
    for f in sorted(SPECS.glob("*/spec.md")):
        text = f.read_text()
        heads = list(REQUIREMENT.finditer(text))
        for i, head in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            pairs += [(head.group(1), t) for t in NAMED_TEST.findall(text[head.end() : end])]
    return pairs


def test_specs_are_not_empty():
    assert spec_ids(), "в openspec/specs нет ни одного требования — сверять не с чем"


def test_every_requirement_has_a_test():
    _, removed = change_ids()
    missing = sorted(spec_ids() - removed - set(marker_ids()))
    assert not missing, f"требования без теста с @pytest.mark.contract: {missing}"


def test_every_marker_has_a_requirement():
    touched, _ = change_ids()
    known = spec_ids() | touched
    orphans = {i: where for i, where in marker_ids().items() if i not in known}
    assert not orphans, f"метки без требования в openspec/specs и changes: {orphans}"


def test_named_tests_exist_and_carry_the_marker():
    marked = marked_tests()
    wrong = [(rid, t) for rid, t in named_tests() if rid not in marked.get(t, [])]
    assert not wrong, f"строка «Тест:» называет тест без метки этого требования: {wrong}"
