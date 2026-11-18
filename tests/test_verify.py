"""Контракт `scripts/verify_kb.py` — capability verify (VER-)."""

import pytest

from conftest import write

TRANSCRIPT = """## [00:00:00](https://youtu.be/vid1?t=0)
текст [битая](nope.md)
## [00:05:00](https://youtu.be/vid1?t=300)
"""

CARD = """---
id: ops/good
практика: Версионировать модели
lecture: L01
теги: [mlops]
уверенность: высокая
---
**Когда.** a
**Почему.** b
**Как.** c
**Границы.** d
**Источник.** [0:05:10](https://youtu.be/vid1?t=310)
"""


@pytest.fixture
def kb(tmp_path):
    write(tmp_path / "transcripts" / "L01.md", TRANSCRIPT)
    write(tmp_path / "practices" / "ops" / "good.md", CARD)
    return tmp_path


def errors(stdout):
    return [line.strip()[2:] for line in stdout.splitlines() if line.startswith("  - ")]


@pytest.mark.contract("VER-1")
def test_ver1_broken_relative_link(kb, run):
    write(kb / "lectures" / "L01.md", "[x](missing.md)\n\n[ok](../practices/ops/good.md#a)\n")
    res = run("verify_kb", kb)
    assert res.returncode == 1
    assert errors(res.stdout) == ["lectures/L01.md:1: битая ссылка -> missing.md"]


@pytest.mark.contract("VER-1")
def test_ver1_external_links_anchors_and_source_dirs_skipped(kb, run):
    write(
        kb / "lectures" / "L01.md",
        "[w](https://x.y/a.md) [h](http://x.y/b.md) [m](mailto:a@b.c) [a](#якорь)\n",
    )
    for d in ["slides_text", "normalization", "scripts", ".git"]:
        write(kb / d / "x.md", "[x](missing.md)\n")
    res = run("verify_kb", kb)
    assert res.returncode == 0
    assert "## Ссылки — OK (проверено файлов: 2)" in res.stdout


@pytest.mark.contract("VER-2")
def test_ver2_label_must_match_seconds(kb, run):
    write(
        kb / "lectures" / "L01.md",
        "[0:00:02](https://youtu.be/vid1?t=0) [0:01:00](https://youtu.be/vid1?t=63)\n",
    )
    res = run("verify_kb", kb, "--tolerance-sec", 100)
    assert errors(res.stdout) == ["lectures/L01.md:1: подпись 0:01:00 (60s) не сходится с ?t=63"]


@pytest.mark.contract("VER-3")
def test_ver3_seconds_must_be_near_block_start(kb, run):
    write(kb / "lectures" / "L01.md", "[0:02:00](https://youtu.be/vid1?t=120)\n")
    res = run("verify_kb", kb)
    assert res.returncode == 1
    assert errors(res.stdout) == [
        "lectures/L01.md:1: ?t=120 (0:02:00) не попадает ни в один блок транскрипта — "
        "ближайший на 0s (разрыв 120s)"
    ]


@pytest.mark.contract("VER-3")
def test_ver3_tolerance_option(kb, run):
    write(kb / "lectures" / "L01.md", "[0:02:00](https://youtu.be/vid1?t=120)\n")
    res = run("verify_kb", kb, "--tolerance-sec", 120)
    assert res.returncode == 0


@pytest.mark.contract("VER-4")
def test_ver4_unknown_video(kb, run):
    write(kb / "lectures" / "L01.md", "[0:00:00](https://youtu.be/vid9?t=0)\n")
    res = run("verify_kb", kb)
    assert errors(res.stdout) == ["lectures/L01.md:1: нет нормализованного транскрипта для vid9"]


@pytest.mark.contract("VER-5")
def test_ver5_card_format(kb, run):
    write(
        kb / "practices" / "ops" / "bad.md",
        "---\nid: ops/other\nlecture: L01\nуверенность: железная\n---\n**Когда.** a\n",
    )
    write(kb / "practices" / "ops" / "nofm.md", "Текст без frontmatter\n")
    res = run("verify_kb", kb)
    assert res.returncode == 1
    assert "## Карточки — 9 ошибок (карточек: ops 3)" in res.stdout
    assert errors(res.stdout) == [
        "practices/ops/bad.md: нет поля `практика` во frontmatter",
        "practices/ops/bad.md: нет поля `теги` во frontmatter",
        "practices/ops/bad.md: id `ops/other` не совпадает с путём (ожидалось `ops/bad`)",
        "practices/ops/bad.md: уверенность `железная` — ожидалось одно из "
        "['высокая', 'низкая', 'средняя']",
        "practices/ops/bad.md: нет раздела **Почему.**",
        "practices/ops/bad.md: нет раздела **Как.**",
        "practices/ops/bad.md: нет раздела **Границы.**",
        "practices/ops/bad.md: нет раздела **Источник.**",
        "practices/ops/nofm.md: нет frontmatter",
    ]


@pytest.mark.contract("VER-6")
def test_ver6_green_report(kb, run):
    res = run("verify_kb", kb)
    assert res.returncode == 0
    assert res.stdout.splitlines() == [
        "## Ссылки — OK (проверено файлов: 1)",
        "## Таймкоды — OK (проверено цитат: 1)",
        "## Карточки — OK (карточек: ops 1)",
        "",
        "итого ошибок: 0",
    ]


@pytest.mark.contract("VER-6")
def test_ver6_quiet_prints_only_errors(kb, run):
    write(kb / "lectures" / "L01.md", "[x](missing.md)\n")
    res = run("verify_kb", kb, "--quiet")
    assert res.returncode == 1
    assert res.stdout.splitlines() == [
        "## Ссылки — 1 ошибок (проверено файлов: 2)",
        "  - lectures/L01.md:1: битая ссылка -> missing.md",
        "",
        "итого ошибок: 1",
    ]


@pytest.mark.contract("VER-6")
def test_ver6_missing_root(tmp_path, run):
    res = run("verify_kb", tmp_path / "nope")
    assert res.returncode == 1
    assert res.stdout == ""
    assert res.stderr.strip() == f"нет такой папки: {tmp_path / 'nope'}"


EN_CARD = """---
id: ops/good
practice: Version models
lecture: L01
tags: [mlops]
confidence: high
---
**When.** a
**Why.** b
**How.** c
**Limits.** d
**Source.** [0:05:10](https://youtu.be/vid1?t=310)
"""


def card_errors(stdout):
    return [e for e in errors(stdout) if e.startswith("practices/")]


@pytest.mark.contract("VER-5")
def test_ver5_english_card(tmp_path, run):
    write(tmp_path / "transcripts" / "L01.md", TRANSCRIPT.replace(" [битая](nope.md)", ""))
    write(tmp_path / "practices" / "ops" / "good.md", EN_CARD)
    russian = run("verify_kb", tmp_path)
    assert "practices/ops/good.md: нет поля `практика` во frontmatter" in card_errors(
        russian.stdout
    )
    assert "practices/ops/good.md: нет раздела **Границы.**" in card_errors(russian.stdout)
    write(tmp_path / "video-kb.json", '{"language": "en"}\n')
    english = run("verify_kb", tmp_path)
    assert card_errors(english.stdout) == []
    assert "## Карточки — OK (карточек: ops 1)" in english.stdout


@pytest.mark.contract("VER-7")
def test_ver7_unknown_language(kb, run):
    write(kb / "video-kb.json", '{"language": "de"}\n')
    res = run("verify_kb", kb)
    assert res.returncode == 2
    assert res.stdout == ""
    assert "video-kb.json" in res.stderr
    assert "de" in res.stderr


@pytest.mark.contract("VER-7")
def test_ver7_broken_config(kb, run):
    write(kb / "video-kb.json", "не json\n")
    res = run("verify_kb", kb)
    assert res.returncode == 2
    assert res.stdout == ""
    assert "video-kb.json" in res.stderr
