#!/usr/bin/env python3
"""Нормализация терминов в автосубтитрах по глоссарию.

Автосабы YouTube хорошо держат русскую речь и разваливают английские
термины: ONNX становится «он X», TensorRT — «TENZРТ», throughput —
«срупут». Исправляем это детерминированно, правилами из TSV, а не
переписыванием текста моделью: так замену можно пересчитать, оспорить
и откатить, а сырой .raw.md остаётся нетронутым.

Формат правила (TSV, колонки через таб):
    canonical <TAB> pattern <TAB> replacement <TAB> note

  canonical   — под каким термином правило попадёт в отчёт (группировка)
  pattern     — регулярка, применяется с re.IGNORECASE
  replacement — чем заменить; поддерживает группы \\1, \\2
  note        — комментарий для отчёта, может быть пустым

Спецформа replacement: если строка начинается с «??», совпадение НЕ
заменяется, а помечается — `текст ⟦?: пояснение⟧`. Это для мест, где
расшифровка реально неоднозначна: лучше оставить метку, чем угадать.

Строки-заголовки таймкодов (`## [`) и служебные комментарии (`<!--`) не
трогаются.

Регулярки пишет пользователь, и неудачная (`(a+)+$`) может откатываться
экспоненциально долго. Поэтому правила применяются в отдельном процессе: если
одно правило на одной строке работает дольше `--timeout-sec` секунд, процесс
останавливается, скрипт возвращает код 3 и называет правило, а `--out` и
`--report` не пишутся. Вход больше 20 МиБ — тоже код 3, до применения правил.

Вывод пишется атомарно: временный файл в той же папке и `os.replace`, так что
прежний файл по пути `--out` или `--report` не обрезается. Если путь вывода или
любая папка на пути к нему — символическая ссылка, скрипт возвращает код 2 и не
пишет ни одного файла. Ссылки разрешены только на пути до домашней папки: её путь
разрешается один раз, а всё ниже неё (или ниже `/` вне её) проходится без ссылок.

Порядок правил в файле = порядок применения. Частные правила должны
идти раньше общих.

Использование:

    normalize.py <вход.md> --rules glossary/common.tsv glossary/L11.tsv \\
        --out transcripts/L11-triton.md --report glossary/L11-report.md [--timeout-sec 10]
"""

import argparse
import multiprocessing
import os
import queue
import re
import stat
import sys
import time
from pathlib import Path

SKIP_LINE = re.compile(r"^(## \[|<!--)")
MAX_INPUT_BYTES = 20 * 2**20
POLL_SEC = 0.05


class LimitError(Exception):
    """Превышен предел времени: нормализованный текст не получен."""


class RuleError(Exception):
    """Замена правила не применяется или рабочий процесс упал."""


class OutputError(Exception):
    """Запись отклонена: в пути вывода символическая ссылка или нет папки."""


DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY


def trusted_start(absolute: Path) -> tuple[int, tuple[str, ...]]:
    """Дескриптор доверенного начала пути `absolute` и компоненты пути ниже него.

    Доверенное начало — домашняя папка, если путь лежит в ней (как она записана в `HOME`
    или после `realpath`): её путь разрешается один раз, и системные ссылки на пути к ней
    проходятся. Путь вне домашней папки начинается с `/`. Ниже начала ссылок нет.
    """
    home = Path(os.path.abspath(Path.home()))
    real = Path(os.path.realpath(home))
    for prefix in (home, real):
        if absolute.is_relative_to(prefix):
            return os.open(real, DIR_FLAGS), absolute.parts[len(prefix.parts) :]
    return os.open("/", DIR_FLAGS), absolute.parts[1:]


def enter(parent: int, name: str, where: Path, create: bool) -> int:
    """Дескриптор папки `name` внутри `parent` без следования по ссылке.

    Ссылка — `OutputError`. Нет папки и `create` — создаётся с правами 0700, иначе
    `OutputError`.
    """
    try:
        return os.open(name, DIR_FLAGS | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        if not create:
            raise OutputError(f"{where}: папки нет") from None
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
        except FileExistsError:
            pass
        return enter(parent, name, where, create=False)
    except OSError:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise OutputError(f"{where}: {name} — символическая ссылка, запись отклонена") from None
        if not stat.S_ISDIR(info.st_mode):
            raise OutputError(f"{where}: {name} — не папка") from None
        raise


def open_dir(path: Path, create: bool = False) -> int:
    """Дескриптор папки: от доверенного начала (`trusted_start`) по компонентам без ссылок."""
    absolute = Path(os.path.abspath(path))
    fd, names = trusted_start(absolute)
    try:
        for name in names:
            child = enter(fd, name, absolute, create)
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd


def open_parent(path: Path) -> int:
    """Дескриптор папки файла `path` (см. `open_dir`); сам файл не должен быть ссылкой."""
    absolute = Path(os.path.abspath(path))
    fd = open_dir(absolute.parent)
    try:
        info = os.stat(absolute.name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return fd
    except BaseException:
        os.close(fd)
        raise
    if stat.S_ISLNK(info.st_mode):
        os.close(fd)
        raise OutputError(f"{absolute}: символическая ссылка — запись отклонена")
    return fd


def replace_file(folder: int, name: str, text: str) -> None:
    """Записать текст во временный файл рядом и атомарно заменить им `name`."""
    temporary = f".{name}.{os.getpid()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(temporary, flags, 0o644, dir_fd=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, name, src_dir_fd=folder, dst_dir_fd=folder)
    except BaseException:
        os.unlink(temporary, dir_fd=folder)
        raise


def write_outputs(outputs: list[tuple[Path, str]]) -> None:
    """Проверить пути всех файлов вывода до первой записи, затем записать каждый."""
    folders = []
    try:
        for path, _ in outputs:
            folders.append(open_parent(path))
        for folder, (path, text) in zip(folders, outputs):
            replace_file(folder, path.name, text)
    finally:
        for folder in folders:
            os.close(folder)


def load_rules(paths: list[Path]) -> list[dict]:
    rules = []
    for path in paths:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                print(f"{path}:{lineno}: нужно минимум 3 колонки", file=sys.stderr)
                return []
            canonical, pattern, replacement = parts[0], parts[1], parts[2]
            note = parts[3] if len(parts) > 3 else ""
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                print(f"{path}:{lineno}: битая регулярка — {exc}", file=sys.stderr)
                return []
            rules.append(
                {
                    "canonical": canonical,
                    "pattern": pattern,
                    "re": compiled,
                    "replacement": replacement,
                    "note": note,
                    "src": f"{path.name}:{lineno}",
                    "hits": 0,
                    "samples": [],
                }
            )
    return rules


def apply_rules(text: str, rules: list[dict], progress) -> str:
    """Применяем правила к тексту, считая срабатывания по каждому.

    `progress` — общий с родителем массив: номер шага и индекс текущего правила.
    """
    for index, rule in enumerate(rules):
        progress[0] += 1
        progress[1] = index
        mark = rule["replacement"].startswith("??")

        def _sub(m: re.Match, rule=rule, mark=mark) -> str:
            rule["hits"] += 1
            if len(rule["samples"]) < 3 and m.group(0) not in rule["samples"]:
                rule["samples"].append(m.group(0))
            if mark:
                return f"{m.group(0)} ⟦?: {rule['replacement'][2:]}⟧"
            return m.expand(rule["replacement"])

        text = rule["re"].sub(_sub, text)
    return text


def normalize(text: str, rules: list[dict], progress) -> str:
    out = []
    for line in text.splitlines():
        out.append(line if SKIP_LINE.match(line) else apply_rules(line, rules, progress))
    return "\n".join(out) + "\n"


def worker(text: str, rules: list[dict], progress, results) -> None:
    """Рабочий процесс: нормализованный текст и счётчики правил — в очередь."""
    try:
        result = normalize(text, rules, progress)
    except re.error as exc:
        results.put(("error", f"{rules[progress[1]]['src']}: замена не применяется — {exc}"))
        return
    results.put(("ok", result, [(r["hits"], r["samples"]) for r in rules]))


def normalize_in_worker(text: str, rules: list[dict], timeout: float) -> str:
    """Нормализовать в отдельном процессе; шаг дольше `timeout` секунд — `LimitError`."""
    progress = multiprocessing.RawArray("q", 2)
    results = multiprocessing.Queue()
    proc = multiprocessing.Process(target=worker, args=(text, rules, progress, results))
    proc.start()
    seen, since = -1, time.monotonic()
    while True:
        try:
            outcome = results.get(timeout=POLL_SEC)
            break
        except queue.Empty:
            pass
        if not proc.is_alive():
            try:
                outcome = results.get(timeout=1)
                break
            except queue.Empty:
                raise RuleError(f"рабочий процесс завершился с кодом {proc.exitcode}") from None
        if progress[0] != seen:
            seen, since = progress[0], time.monotonic()
        elif time.monotonic() - since > timeout:
            proc.kill()
            proc.join()
            raise LimitError(
                f"{rules[progress[1]]['src']}: правило не уложилось в {timeout:g} с на одной "
                "строке — похоже на катастрофический откат регулярки; файлы не записаны"
            )
    proc.join()
    if outcome[0] == "error":
        raise RuleError(outcome[1])
    for rule, (hits, samples) in zip(rules, outcome[2]):
        rule["hits"], rule["samples"] = hits, samples
    return outcome[1]


def build_report(rules: list[dict], src: Path, dst: Path) -> str:
    by_term: dict[str, list[dict]] = {}
    for rule in rules:
        by_term.setdefault(rule["canonical"], []).append(rule)

    total = sum(r["hits"] for r in rules)
    dead = [r for r in rules if r["hits"] == 0]
    marked = sum(r["hits"] for r in rules if r["replacement"].startswith("??"))

    lines = [
        f"# Глоссарий замен — {src.name}",
        "",
        f"Источник: `{src}`  ",
        f"Результат: `{dst}`",
        "",
        f"Всего замен: **{total}** по {len(by_term)} терминам "
        f"({len([r for r in rules if r['hits']])} правил из {len(rules)} сработали).  ",
        f"Из них помечено как неоднозначное, без замены: **{marked}**.",
        "",
        "| Термин | Замен | Что встречалось в сабах | Примечание |",
        "|---|---:|---|---|",
    ]
    for term in sorted(by_term, key=lambda t: -sum(r["hits"] for r in by_term[t])):
        group = by_term[term]
        hits = sum(r["hits"] for r in group)
        if not hits:
            continue
        samples = []
        for rule in group:
            for s in rule["samples"]:
                if s not in samples:
                    samples.append(s)
        note = next((r["note"] for r in group if r["note"] and r["hits"]), "")
        shown = ", ".join(f"`{s}`" for s in samples[:6])
        lines.append(f"| {term} | {hits} | {shown} | {note} |")

    if dead:
        lines += [
            "",
            "## Правила без срабатываний",
            "",
            "Написаны на всякий случай или под другие лекции — в этой не встретились.",
            "",
            "| Термин | Правило | Файл |",
            "|---|---|---|",
        ]
        for rule in dead:
            lines.append(f"| {rule['canonical']} | `{rule['pattern']}` | {rule['src']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--rules", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--report", type=Path)
    ap.add_argument(
        "--timeout-sec",
        type=float,
        default=10,
        help="предел времени одного правила на одной строке",
    )
    args = ap.parse_args()

    rules = load_rules(args.rules)
    if not rules:
        return 1

    if args.src.stat().st_size > MAX_INPUT_BYTES:
        print(
            f"{args.src}: вход больше {MAX_INPUT_BYTES // 2**20} МиБ — правила не применялись",
            file=sys.stderr,
        )
        return 3
    text = args.src.read_text(encoding="utf-8")
    try:
        result = normalize_in_worker(text, rules, args.timeout_sec)
    except LimitError as exc:
        print(exc, file=sys.stderr)
        return 3
    except RuleError as exc:
        print(exc, file=sys.stderr)
        return 1
    outputs = [(args.out, result)]
    if args.report:
        outputs.append((args.report, build_report(rules, args.src, args.out)))
    try:
        write_outputs(outputs)
    except (OutputError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2

    total = sum(r["hits"] for r in rules)
    fired = len([r for r in rules if r["hits"]])
    print(f"замен: {total}, сработало правил: {fired}/{len(rules)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
