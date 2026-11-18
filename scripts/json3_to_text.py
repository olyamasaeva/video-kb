#!/usr/bin/env python3
"""json3 (YouTube auto-captions) -> текст с таймкодами.

Автосабы приходят как поток мелких событий без структуры. Склеиваем их
в блоки фиксированной длины, каждый блок помечаем таймкодом [HH:MM:SS] —
так на любое место в транскрипте можно сослаться из карточки практики
и проверить по видео.

Использование:

    json3_to_text.py <файл.json3> [--block-sec 60] [--video-id ID]
"""

import argparse
import json
import re
import sys
from pathlib import Path


def hhmmss(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def load_events(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for ev in data.get("events", []):
        if "segs" not in ev:
            continue
        text = "".join(s.get("utf8", "") for s in ev["segs"])
        text = text.replace("\n", " ").strip()
        if text:
            out.append({"t": ev.get("tStartMs", 0), "text": text})
    return out


def has_punctuation(events: list[dict]) -> bool:
    """Бывают автосабы совсем без знаков препинания (встречалось у целых
    лекций подряд). Тогда граница предложения не наступает никогда, и вся лекция
    молча уходит в один блок — таймкод перестаёт быть адресом."""
    ends = sum(1 for ev in events if re.search(r"[.!?]\s*$", ev["text"]))
    return ends >= max(3, len(events) // 200)


def to_blocks(events: list[dict], block_ms: int) -> list[dict]:
    """Режем на блоки по времени, но не рвём предложение посередине:
    блок закрывается на первой границе предложения после лимита.
    Если пунктуации в сабах нет — на первой границе события после лимита."""
    punct = has_punctuation(events)
    blocks: list[dict] = []
    cur: list[str] = []
    start = events[0]["t"] if events else 0
    for ev in events:
        cur.append(ev["text"])
        elapsed = ev["t"] - start
        ends_sentence = (not punct) or re.search(r"[.!?]\s*$", ev["text"]) is not None
        if elapsed >= block_ms and ends_sentence:
            blocks.append({"t": start, "text": " ".join(cur)})
            cur, start = [], ev["t"]
    if cur:
        blocks.append({"t": start, "text": " ".join(cur)})
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("--block-sec", type=int, default=60)
    ap.add_argument("--video-id", default=None)
    args = ap.parse_args()

    events = load_events(args.src)
    if not events:
        print(f"пусто: {args.src}", file=sys.stderr)
        return 1

    blocks = to_blocks(events, args.block_sec * 1000)
    vid = args.video_id or args.src.name.split("-", 1)[-1].split(".")[0]

    for b in blocks:
        stamp = hhmmss(b["t"])
        link = f"https://youtu.be/{vid}?t={b['t'] // 1000}"
        print(f"\n## [{stamp}]({link})\n")
        print(b["text"])

    total = sum(len(b["text"]) for b in blocks)
    print(
        f"\n<!-- событий: {len(events)}, блоков: {len(blocks)}, "
        f"символов: {total}, длительность: {hhmmss(events[-1]['t'])} -->"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
