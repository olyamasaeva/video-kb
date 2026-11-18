#!/usr/bin/env python3
"""Хук pre-commit: строк из личного списка нет в отслеживаемых файлах.

Список лежит вне репозитория (строка на строку; пустые и `#`-строки пропускаются).
Каждая строка ищется во всех файлах `git ls-files` текущей папки без учёта регистра и
как отдельное слово: если строка начинается (кончается) буквой или цифрой, соседний знак
с этой стороны не буква и не цифра. Так имя не находится внутри другого слова, а строка с
краевым `_` остаётся префиксом.

Найденная строка не печатается — только `путь:номер строки`: вывод хука попадает в
журналы, а список и есть то, что прячем.

Использование:

    denylist.py <файл-списка>

Коды возврата: 0 — совпадений нет; 1 — есть совпадения; 2 — список недоступен или пуст,
или `git ls-files` не сработал.
"""

import re
import subprocess
import sys
from pathlib import Path

LETTER_OR_DIGIT = r"[^\W_]"


class ListError(Exception):
    """Список недоступен: сообщение уже содержит путь к нему."""


def load_entries(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ListError(f"{path}: список не читается — {error.__class__.__name__}") from None
    entries = [line.strip() for line in lines]
    entries = [e for e in entries if e and not e.startswith("#")]
    if not entries:
        raise ListError(f"{path}: в списке нет ни одной строки")
    return entries


def pattern_for(entries: list[str]) -> re.Pattern:
    """Одна регулярка на весь список: каждая строка — отдельное слово, без учёта регистра."""
    parts = []
    for entry in entries:
        left = f"(?<!{LETTER_OR_DIGIT})" if entry[0].isalnum() else ""
        right = f"(?!{LETTER_OR_DIGIT})" if entry[-1].isalnum() else ""
        parts.append(left + re.escape(entry) + right)
    return re.compile("|".join(parts), re.IGNORECASE)


def tracked_files() -> list[Path]:
    listed = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=False)
    if listed.returncode != 0:
        raise ListError("git ls-files не сработал: " + listed.stderr.decode(errors="replace"))
    return [Path(name) for name in listed.stdout.decode("utf-8").split("\0") if name]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("использование: denylist.py <файл-списка>", file=sys.stderr)
        return 2
    try:
        pattern = pattern_for(load_entries(Path(argv[0]).expanduser()))
        files = tracked_files()
    except ListError as error:
        print(error, file=sys.stderr)
        return 2
    found = []
    for path in files:
        if path.is_symlink() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                found.append(f"{path}:{lineno}")
    for place in found:
        print(place)
    if found:
        print(f"строки из личного списка: {len(found)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
