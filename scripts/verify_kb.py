#!/usr/bin/env python3
"""Проверка базы знаний, собранной из видео: ссылки, таймкоды, формат карточек.

Три проверки, каждая ловит свой класс дефектов:

1. **Ссылки.** Относительная markdown-ссылка между конспектами, карточками и
   словарём должна вести в существующий файл. Ловит переименования и опечатки
   в слагах.
2. **Таймкоды.** Ссылка вида `[H:MM:SS](https://youtu.be/<id>?t=N)` проверяется
   дважды: подпись должна соответствовать N, а N — попадать рядом с реально
   существующим блоком транскрипта. Ловит цитату, приклеенную не к тому месту
   лекции, — глазами это не ловится вообще.
3. **Формат карточек.** Обязательные поля frontmatter и пять разделов.
   Ловит карточку без «Границ», то есть практику без честных ограничений.
   Схема полей и разделов зависит от языка базы: `<база>/video-kb.json`,
   поле `language` (`ru` или `en`); без файла — `ru`.

Папки-исходники (`transcripts`, `slides_text`, `normalization`, `scripts`, `.git`) —
инструмент и сырьё, а не знание: ссылки и формат в них не проверяются.

Использование:

    verify_kb.py <корень базы> [--tolerance-sec 80] [--quiet]

Код возврата 1, если есть хоть одна ошибка; 2 — битая настройка `video-kb.json`.
"""

import argparse
import json
import re
import sys
from pathlib import Path

CITE = re.compile(r"\[(\d{1,2}):(\d{2}):(\d{2})\]\(https://youtu\.be/([\w-]+)\?t=(\d+)\)")
HEADER = re.compile(r"^## \[\d{1,2}:\d{2}:\d{2}\]\(https://youtu\.be/([\w-]+)\?t=(\d+)\)")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

CONFIG_NAME = "video-kb.json"
CARD_SCHEMAS = {
    "ru": {
        "keys": ["id", "практика", "lecture", "теги", "уверенность"],
        "confidence_key": "уверенность",
        "confidence": {"высокая", "средняя", "низкая"},
        "sections": ["**Когда.**", "**Почему.**", "**Как.**", "**Границы.**", "**Источник.**"],
    },
    "en": {
        "keys": ["id", "practice", "lecture", "tags", "confidence"],
        "confidence_key": "confidence",
        "confidence": {"high", "medium", "low"},
        "sections": ["**When.**", "**Why.**", "**How.**", "**Limits.**", "**Source.**"],
    },
}

SKIP_DIRS = {"transcripts", "slides_text", "normalization", "scripts", ".git"}


def knowledge_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not (SKIP_DIRS & set(p.relative_to(root).parts)))


def check_links(root: Path, files: list[Path]) -> list[str]:
    errors = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK.findall(line):
                if re.match(r"^(https?:|mailto:|#)", target):
                    continue
                dest = (path.parent / target.split("#")[0]).resolve()
                if not dest.exists():
                    rel = path.relative_to(root)
                    errors.append(f"{rel}:{lineno}: битая ссылка -> {target}")
    return errors


def load_transcript_index(root: Path) -> dict[str, list[int]]:
    """video_id -> отсортированные секунды начала блоков."""
    index: dict[str, list[int]] = {}
    tdir = root / "transcripts"
    if not tdir.is_dir():
        return index
    for path in sorted(tdir.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = HEADER.match(line)
            if m:
                index.setdefault(m.group(1), []).append(int(m.group(2)))
    for vid in index:
        index[vid] = sorted(set(index[vid]))
    return index


def check_timecodes(root: Path, files: list[Path], tolerance: int) -> tuple[list[str], int]:
    index = load_transcript_index(root)
    errors, checked = [], 0
    for path in files:
        rel = path.relative_to(root)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for hh, mm, ss, vid, raw in CITE.findall(line):
                checked += 1
                secs = int(raw)
                label = int(hh) * 3600 + int(mm) * 60 + int(ss)
                if abs(label - secs) > 2:
                    errors.append(
                        f"{rel}:{lineno}: подпись {hh}:{mm}:{ss} ({label}s) не сходится с ?t={secs}"
                    )
                blocks = index.get(vid)
                if blocks is None:
                    errors.append(f"{rel}:{lineno}: нет нормализованного транскрипта для {vid}")
                    continue
                nearest = min(blocks, key=lambda b: abs(b - secs))
                if abs(nearest - secs) > tolerance:
                    errors.append(
                        f"{rel}:{lineno}: ?t={secs} ({hh}:{mm}:{ss}) не попадает ни в один "
                        f"блок транскрипта — ближайший на {nearest}s "
                        f"(разрыв {abs(nearest - secs)}s)"
                    )
    return errors, checked


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([\wа-яёА-ЯЁ_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm, text[end + 5 :]


class ConfigError(Exception):
    """Настройка базы не разбирается или называет неизвестный язык."""


def base_language(root: Path) -> str:
    """Язык базы из `video-kb.json`; без файла — `ru`."""
    path = root / CONFIG_NAME
    if not path.exists():
        return "ru"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{CONFIG_NAME}: не разбирается как JSON ({exc})") from exc
    if not isinstance(config, dict):
        raise ConfigError(f"{CONFIG_NAME}: ожидался JSON-объект")
    language = config.get("language", "ru")
    if language not in CARD_SCHEMAS:
        raise ConfigError(
            f"{CONFIG_NAME}: неизвестный язык `{language}` — ожидалось одно из {sorted(CARD_SCHEMAS)}"
        )
    return language


def check_cards(root: Path, schema: dict) -> tuple[list[str], dict[str, int]]:
    errors, counts = [], {}
    pdir = root / "practices"
    if not pdir.is_dir():
        return errors, counts
    for path in sorted(pdir.rglob("*.md")):
        rel = path.relative_to(root)
        theme = path.parent.name
        counts[theme] = counts.get(theme, 0) + 1
        fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
        if not fm:
            errors.append(f"{rel}: нет frontmatter")
            continue
        for key in schema["keys"]:
            if key not in fm:
                errors.append(f"{rel}: нет поля `{key}` во frontmatter")
        want_id = f"{theme}/{path.stem}"
        if fm.get("id") and fm["id"] != want_id:
            errors.append(f"{rel}: id `{fm['id']}` не совпадает с путём (ожидалось `{want_id}`)")
        conf_key = schema["confidence_key"]
        conf = fm.get(conf_key, "")
        if conf and conf not in schema["confidence"]:
            errors.append(
                f"{rel}: {conf_key} `{conf}` — ожидалось одно из {sorted(schema['confidence'])}"
            )
        for section in schema["sections"]:
            if section not in body:
                errors.append(f"{rel}: нет раздела {section}")
    return errors, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument(
        "--tolerance-sec",
        type=int,
        default=80,
        help="допустимый разрыв между цитатой и началом блока транскрипта",
    )
    ap.add_argument("--quiet", action="store_true", help="только ошибки и итог")
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"нет такой папки: {root}", file=sys.stderr)
        return 1

    try:
        language = base_language(root)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    files = knowledge_files(root)
    link_errors = check_links(root, files)
    time_errors, checked = check_timecodes(root, files, args.tolerance_sec)
    card_errors, counts = check_cards(root, CARD_SCHEMAS[language])

    blocks = [
        ("Ссылки", link_errors, f"проверено файлов: {len(files)}"),
        ("Таймкоды", time_errors, f"проверено цитат: {checked}"),
        (
            "Карточки",
            card_errors,
            "карточек: " + ", ".join(f"{t} {n}" for t, n in sorted(counts.items()))
            if counts
            else "карточек нет",
        ),
    ]
    for title, errs, note in blocks:
        if errs:
            print(f"## {title} — {len(errs)} ошибок ({note})")
            for e in errs:
                print(f"  - {e}")
        elif not args.quiet:
            print(f"## {title} — OK ({note})")

    total = len(link_errors) + len(time_errors) + len(card_errors)
    print(f"\nитого ошибок: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
