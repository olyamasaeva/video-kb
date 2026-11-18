#!/usr/bin/env python3
"""Проверка собранного скилла: frontmatter `SKILL.md` и ссылки на карточки базы.

Скилл из базы ссылается на карточки абсолютными путями, а не копирует их, поэтому
битая ссылка — это скилл, который ведёт агента в пустоту. Проверяется:

- у `SKILL.md` есть frontmatter с `name` — совпадает с именем папки, только
  строчные латинские буквы, цифры и дефис;
- `description` непустой и не длиннее 1024 знаков;
- каждая ссылка на `.md`-файл с абсолютным путём (markdown-ссылка или путь в
  обратных кавычках) ведёт в существующий файл.

Использование:

    skill_lint.py <папка скилла>

Код 0 и пустой вывод, если нарушений нет; иначе код 1 и по строке на нарушение.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_DESCRIPTION = 1024
LINK = re.compile(r"\]\(<([^>]+)>\)|\]\(([^)\s]+)\)|`([^`\s]+)`")


def frontmatter(lines: list[str]) -> tuple[dict[str, str], int] | None:
    """Поля frontmatter (включая блоки `>` и `|`) и номер строки после него."""
    if not lines or lines[0].strip() != "---":
        return None
    fields, key, block = {}, None, []
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            if key and block:
                fields[key] = " ".join(block)
            return fields, index + 1
        head = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if head and not line.startswith((" ", "\t")):
            if key and block:
                fields[key] = " ".join(block)
            key, value = head.group(1), head.group(2).strip()
            block = []
            if value in (">", "|", ">-", "|-", ">+", "|+"):
                fields[key] = ""
            else:
                fields[key] = value.strip("\"'")
                key = None
        elif key and line.strip():
            block.append(line.strip())
    return None


def absolute_md_targets(line: str) -> list[str]:
    targets = []
    for match in LINK.finditer(line):
        target = unquote(next(g for g in match.groups() if g)).split("#")[0]
        if target.endswith(".md") and (target.startswith("/") or target.startswith("~/")):
            targets.append(target)
    return targets


def lint(folder: Path) -> list[str]:
    skill = folder / "SKILL.md"
    if not skill.is_file():
        return [f"{skill}: файла нет"]
    lines = skill.read_text(encoding="utf-8").splitlines()
    parsed = frontmatter(lines)
    if parsed is None:
        return [f"{skill}:1: нет frontmatter между строками ---"]
    fields, body_start = parsed
    problems = []
    name = fields.get("name", "")
    if not NAME.match(name):
        problems.append(f"{skill}: name «{name}» — нужны строчные латинские буквы, цифры и дефис")
    if name != folder.name:
        problems.append(f"{skill}: name «{name}» не совпадает с папкой «{folder.name}»")
    description = fields.get("description", "")
    if not description:
        problems.append(f"{skill}: description пустой")
    elif len(description) > MAX_DESCRIPTION:
        problems.append(f"{skill}: description {len(description)} знаков, больше {MAX_DESCRIPTION}")
    for lineno, line in enumerate(lines[body_start:], body_start + 1):
        for target in absolute_md_targets(line):
            if not Path(target).expanduser().is_file():
                problems.append(f"{skill}:{lineno}: ссылка на несуществующий файл -> {target}")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("папка", type=Path)
    args = ap.parse_args(argv)
    problems = lint(args.папка.resolve())
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
