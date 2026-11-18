"""Контракт `scripts/json3_to_text.py` — capability subtitles (SUB-)."""

import json

import pytest

from conftest import write


def json3(tmp_path, events, name="01-vid_ID-1.ru.json3"):
    return write(tmp_path / name, json.dumps({"events": events}, ensure_ascii=False))


def ev(ms, *segs):
    return {"tStartMs": ms, "segs": [{"utf8": s} for s in segs]}


def blocks(stdout):
    """Пары (заголовок, текст) из вывода скрипта."""
    out, head = [], None
    for line in stdout.splitlines():
        if line.startswith("## ["):
            head = line
        elif line and head and not line.startswith("<!--"):
            out.append((head, line))
            head = None
    return out


@pytest.mark.contract("SUB-1")
def test_sub1_segments_glued_into_block(tmp_path, run):
    src = json3(
        tmp_path,
        [
            ev(0, "Привет", " всем."),
            {"tStartMs": 500},
            ev(1000, "\n"),
            ev(2000, "Сегодня\nо деле."),
        ],
    )
    res = run("json3_to_text", src)
    assert res.returncode == 0
    assert blocks(res.stdout) == [
        ("## [00:00:00](https://youtu.be/vid_ID-1?t=0)", "Привет всем. Сегодня о деле.")
    ]


@pytest.mark.contract("SUB-2")
def test_sub2_block_closes_on_sentence_after_limit(tmp_path, run):
    src = json3(
        tmp_path,
        [
            ev(0, "Раз."),
            ev(30000, "Два."),
            ev(50000, "Три"),
            ev(65000, "четыре."),
            ev(70000, "Пять."),
        ],
    )
    res = run("json3_to_text", src, "--block-sec", 60)
    assert [text for _, text in blocks(res.stdout)] == ["Раз. Два. Три четыре.", "Пять."]


@pytest.mark.contract("SUB-3")
def test_sub3_next_header_is_time_of_closing_event(tmp_path, run):
    src = json3(
        tmp_path,
        [
            ev(0, "Раз."),
            ev(30000, "Два."),
            ev(65000, "Три."),
            ev(70000, "Четыре."),
            ev(80000, "Пять."),
        ],
    )
    res = run("json3_to_text", src)
    assert blocks(res.stdout) == [
        ("## [00:00:00](https://youtu.be/vid_ID-1?t=0)", "Раз. Два. Три."),
        ("## [00:01:05](https://youtu.be/vid_ID-1?t=65)", "Четыре. Пять."),
    ]


@pytest.mark.contract("SUB-4")
def test_sub4_unpunctuated_subs_cut_on_event(tmp_path, run):
    src = json3(
        tmp_path,
        [
            ev(0, "раз"),
            ev(30000, "два."),
            ev(61000, "три"),
            ev(62000, "четыре"),
            ev(130000, "пять"),
        ],
    )
    res = run("json3_to_text", src)
    assert [text for _, text in blocks(res.stdout)] == ["раз два. три", "четыре пять"]


@pytest.mark.contract("SUB-5")
def test_sub5_video_id_from_file_name(tmp_path, run):
    src = json3(tmp_path, [ev(3725000, "Финал.")], name="07-Ab-c_9.ru.json3")
    res = run("json3_to_text", src)
    assert "## [01:02:05](https://youtu.be/Ab-c_9?t=3725)" in res.stdout


@pytest.mark.contract("SUB-5")
def test_sub5_video_id_option_wins(tmp_path, run):
    src = json3(tmp_path, [ev(0, "Финал.")], name="07-Ab-c_9.ru.json3")
    res = run("json3_to_text", src, "--video-id", "ZZZ")
    assert "## [00:00:00](https://youtu.be/ZZZ?t=0)" in res.stdout
    assert "Ab-c_9" not in res.stdout


@pytest.mark.contract("SUB-6")
def test_sub6_summary_comment(tmp_path, run):
    src = json3(tmp_path, [ev(0, "Раз."), ev(30000, "Два."), ev(65000, "Три."), ev(3725000, "Х.")])
    res = run("json3_to_text", src)
    assert res.stdout.rstrip("\n").splitlines()[-1] == (
        "<!-- событий: 4, блоков: 2, символов: 16, длительность: 01:02:05 -->"
    )


@pytest.mark.contract("SUB-7")
def test_sub7_empty_subs_fail(tmp_path, run):
    src = json3(tmp_path, [{"tStartMs": 0}, ev(100, " \n ")], name="empty.json3")
    res = run("json3_to_text", src)
    assert res.returncode == 1
    assert res.stdout == ""
    assert res.stderr.strip() == f"пусто: {src}"
