#!/usr/bin/env python3
"""Проверка цитат «…» в базе: (1) дословность — цитата (без учёта регистра,
пробелов, ё/е, вставок [..], разрезанная по «…») есть в нормализованном
транскрипте; (2) адрес — ближайшая к цитате ссылка ?t=N (±420 символов) указывает
на блок, где цитата стоит, с допуском ±1 блок.
Транскрипт выбирается по video id ближайшей ссылки, иначе по `lecture:` во
frontmatter. Короткие (<3 слов) «…» без совпадения считаются терминами и
выводятся отдельно как SHORT. Код возврата 1 при MISS или ADDR.
Заголовки блоков `## [...]` не часть речи: цитата может переходить через границу
блока. Конвенция `«цитата» ([таймкод](…))`: сначала берётся ближайшая ссылка
после цитаты, потом до неё. Если ссылка стоит в строке адресов (формат словаря:
`L05 [a](…), [b](…)`), годится любая ссылка этой строки.
Использование: `check_quotes.py <KB_ROOT> [файлы...]`"""

import re
import sys
import glob
import os


def norm(s):
    s = s.replace("ё", "е").replace("Ё", "Е")
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r" ?⟦[^⟧]*⟧", "", s)
    return re.sub(r"\s+", " ", s).lower().strip(" ,.")


def load_transcripts(root):
    out = {}
    for p in glob.glob(os.path.join(root, "transcripts", "L??.md")):
        L = os.path.basename(p)[:3]
        t = open(p, encoding="utf-8").read()
        t = re.sub(r" ?⟦[^⟧]*⟧", "", t)
        heads, vid = [], None
        for m in re.finditer(
            r"^## \[[\d:]+\]\(https://youtu\.be/([\w-]+)\?t=(\d+)\)", t, flags=re.M
        ):
            heads.append((m.start(), int(m.group(2))))
            vid = m.group(1)
        skip = set()
        for m in re.finditer(r"^## \[[^\n]*$", t, flags=re.M):
            skip.update(range(m.start(), m.end()))
        flat, back, prev = [], [], False
        for i, ch in enumerate(t):
            if i in skip:
                continue
            c = ch.replace("ё", "е").replace("Ё", "Е").lower()
            if c.isspace():
                if prev:
                    continue
                c, prev = " ", True
            else:
                prev = False
            flat.append(c)
            back.append(i)
        out[L] = dict(flat="".join(flat), back=back, heads=heads, vid=vid)
    return out


def block_of(tr, flat_off):
    off = tr["back"][flat_off]
    secs = [s for (o, s) in tr["heads"] if o <= off]
    return secs[-1] if secs else None


def main():
    root = sys.argv[1]
    files = sys.argv[2:] or sorted(
        glob.glob(os.path.join(root, "practices/**/*.md"), recursive=True)
        + glob.glob(os.path.join(root, "lectures/*.md"))
        + glob.glob(os.path.join(root, "glossary/*.md"))
    )
    trs = load_transcripts(root)
    by_vid = {v["vid"]: L for L, v in trs.items()}
    bad = 0
    for f in files:
        doc = open(f, encoding="utf-8").read()
        fm = re.search(r"^lecture:\s*(L\d\d)", doc, flags=re.M)
        default_L = fm.group(1) if fm else None
        body = re.sub(r"^> ?", "", doc, flags=re.M)
        links = [
            (m.start(), m.group(1), int(m.group(2)))
            for m in re.finditer(r"https://youtu\.be/([\w-]+)\?t=(\d+)", body)
        ]
        for m in re.finditer(r"«([^«»]+)»", body):
            q = m.group(1)
            after = sorted(
                [link for link in links if 0 <= link[0] - m.end() <= 420], key=lambda link: link[0]
            )
            before = sorted(
                [link for link in links if 0 <= m.start() - link[0] <= 420],
                key=lambda link: -link[0],
            )
            near = after + before
            L = by_vid.get(near[0][1]) if near else default_L
            if L is None or L not in trs:
                continue
            tr = trs[L]
            frags = [norm(x) for x in re.split(r"…|\.\.\.", q) if norm(x)]
            hits = []
            ok = True
            for fr in frags:
                pos = [x.start() for x in re.finditer(re.escape(fr), tr["flat"])]
                if not pos:
                    ok = False
                    break
                hits.append(pos)
            rel = os.path.relpath(f, root)
            if not ok:
                if len(q.split()) < 3:
                    print(f"SHORT\t{rel}\t{L}\t«{q}»")
                else:
                    print(f"MISS\t{rel}\t{L}\t«{q}»")
                    bad += 1
                continue
            blocks = sorted({block_of(tr, p) for p in hits[0]})
            near_same = [link for link in near if by_vid.get(link[1]) == L]
            if near_same and len(q.split()) >= 3:
                t = near_same[0][2]
                ls = body.rfind("\n", 0, near_same[0][0]) + 1
                le = body.find("\n", near_same[0][0])
                le = len(body) if le < 0 else le
                cands = [
                    link[2] for link in links if ls <= link[0] < le and by_vid.get(link[1]) == L
                ] or [t]
                secs = [s for (_, s) in tr["heads"]]

                def idx(s):
                    return secs.index(s) if s in secs else None

                def close(t):
                    it = idx(t)
                    return it is not None and any(
                        abs(idx(b) - it) <= 1 for b in blocks if b is not None
                    )

                if not any(close(c) for c in cands):
                    print(f"ADDR\t{rel}\t{L}\t«{q}»\tссылка t={t}, цитата в блоках {blocks}")
                    bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
