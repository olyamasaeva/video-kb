"""Контракт `scripts/skill_lint.py` — capability skills (SKL-8)."""

from pathlib import Path

import pytest

from conftest import write

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def skill(folder, name, description, body):
    return write(
        folder / "SKILL.md", f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"
    )


@pytest.fixture
def card(tmp_path):
    return write(tmp_path / "kb" / "practices" / "eval" / "a.md", "карточка\n")


@pytest.mark.contract("SKL-8")
def test_skl8_missing_card(tmp_path, card, run):
    missing = tmp_path / "kb" / "practices" / "eval" / "нет.md"
    folder = tmp_path / "agent-eval"
    skill(folder, "agent-eval", "Когда пишу eval.", f"- [есть]({card})\n- [нет]({missing}#a)")
    res = run("skill_lint", folder)
    assert res.returncode == 1
    lines = res.stdout.strip().splitlines()
    assert len(lines) == 1 and str(missing) in lines[0]


@pytest.mark.contract("SKL-8")
def test_skl8_ok(tmp_path, card, run):
    folder = tmp_path / "agent-eval"
    skill(folder, "agent-eval", "Когда пишу eval.", f"[a](<{card}>) и `{card}`")
    res = run("skill_lint", folder)
    assert res.returncode == 0, res.stdout
    assert res.stdout == ""


@pytest.mark.contract("SKL-8")
def test_skl8_frontmatter_violations(tmp_path, run):
    folder = tmp_path / "agent-eval"
    skill(folder, "Agent_Eval", "x" * 1025, "тело")
    res = run("skill_lint", folder)
    assert res.returncode == 1
    assert len(res.stdout.strip().splitlines()) == 3
    write(folder / "SKILL.md", "без frontmatter\n")
    res = run("skill_lint", folder)
    assert res.returncode == 1 and res.stdout.strip()


@pytest.mark.contract("SKL-8")
def test_skl8_block_description(tmp_path, run):
    folder = tmp_path / "agent-eval"
    write(folder / "SKILL.md", "---\nname: agent-eval\ndescription: >\n  строка один\n  два\n---\n")
    res = run("skill_lint", folder)
    assert res.returncode == 0, res.stdout


@pytest.mark.contract("SKL-8")
def test_skl8_templates_pass_after_substitution(tmp_path, card, run):
    values = {
        "{{имя}}": "agent-eval",
        "{{курс}}": "Курс X",
        "{{описание}}": "Когда пишу eval для агента.",
        "{{база}}": str(card.parents[2]),
        "{{карточка}}": str(card),
        "{{таймкод}}": "[0:01:00](https://youtu.be/vid1?t=60)",
    }
    for template in ["skill.md", "kb-pointer.md"]:
        text = (TEMPLATES / template).read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace(key, value)
        assert "{{" not in text, template
        write(card.parents[2] / "README.md", "readme\n")
        write(card.parents[2] / "glossary" / "terms.md", "словарь\n")
        folder = tmp_path / "out" / template / "agent-eval"
        write(folder / "SKILL.md", text)
        res = run("skill_lint", folder)
        assert res.returncode == 0, (template, res.stdout)
