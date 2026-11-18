#!/usr/bin/env python3
"""Адрес цитаты: ищет дословный кусок в нормализованном транскрипте и печатает
владеющий блок `[H:MM:SS](url?t=N)`. Сравнение без регистра и с нормализацией
пробелов. Заголовки блоков `## [...]` не часть речи: цитата может
переходить через границу блока.

Использование: `locate.py transcripts/L06.md "цитата" ["цитата" ...]`"""

import re
import sys


def load(path):
    t = open(path, encoding="utf-8").read()
    heads = [
        (m.start(), m.group(1), m.group(2))
        for m in re.finditer(r"^## \[([\d:]+)\]\((\S+?)\)", t, flags=re.M)
    ]
    return t, heads


def norm(s):
    return re.sub(r"\s+", " ", s.replace("ё", "е").replace("Ё", "Е")).lower().strip()


def main():
    path, quotes = sys.argv[1], sys.argv[2:]
    t, heads = load(path)
    flat, back = [], []
    prev_space = False
    skip = set()
    for m in re.finditer(r"^## \[[^\n]*$", t, flags=re.M):
        skip.update(range(m.start(), m.end()))
    for i, ch in enumerate(t):
        if i in skip:
            continue
        c = ch.replace("ё", "е").replace("Ё", "Е").lower()
        if c.isspace():
            if prev_space:
                continue
            c, prev_space = " ", True
        else:
            prev_space = False
        flat.append(c)
        back.append(i)
    flat = "".join(flat)
    rc = 0
    for q in quotes:
        hits = [m.start() for m in re.finditer(re.escape(norm(q)), flat)]
        if not hits:
            print(f"MISS\t{q}")
            rc = 1
            continue
        for h in hits:
            off = back[h]
            own = max((x for x in heads if x[0] <= off), key=lambda x: x[0], default=None)
            print(f"[{own[1]}]({own[2]})\t{q}" if own else f"NOHEAD\t{q}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
