"""Контракт `scripts/locate.py` — capability locate (LOC-)."""

import pytest

from conftest import write

TRANSCRIPT = """Вступление без заголовка.

## [0:00:00](https://youtu.be/v?t=0)

Мы  ЗАПУСКАЕМ ёлку на сервере. Конец

## [0:01:00](https://youtu.be/v?t=60)

блока и снова запускаем ёлку.
"""


@pytest.fixture
def transcript(tmp_path):
    return write(tmp_path / "transcripts" / "L01.md", TRANSCRIPT)


@pytest.mark.contract("LOC-1")
def test_loc1_prints_owning_block(transcript, run):
    res = run("locate", transcript, "на сервере")
    assert res.returncode == 0
    assert res.stdout == "[0:00:00](https://youtu.be/v?t=0)\tна сервере\n"


@pytest.mark.contract("LOC-2")
def test_loc2_case_yo_and_spaces_ignored(transcript, run):
    res = run("locate", transcript, "мы запускаем   елку")
    assert res.stdout == "[0:00:00](https://youtu.be/v?t=0)\tмы запускаем   елку\n"


@pytest.mark.contract("LOC-2")
def test_loc2_quote_spans_block_header(transcript, run):
    res = run("locate", transcript, "Конец блока и снова")
    assert res.returncode == 0
    assert res.stdout == "[0:00:00](https://youtu.be/v?t=0)\tКонец блока и снова\n"


@pytest.mark.contract("LOC-3")
def test_loc3_every_occurrence_printed(transcript, run):
    res = run("locate", transcript, "запускаем ёлку")
    assert res.stdout.splitlines() == [
        "[0:00:00](https://youtu.be/v?t=0)\tзапускаем ёлку",
        "[0:01:00](https://youtu.be/v?t=60)\tзапускаем ёлку",
    ]


@pytest.mark.contract("LOC-4")
def test_loc4_miss_sets_exit_code(transcript, run):
    res = run("locate", transcript, "нет такого", "на сервере")
    assert res.returncode == 1
    assert res.stdout.splitlines() == [
        "MISS\tнет такого",
        "[0:00:00](https://youtu.be/v?t=0)\tна сервере",
    ]


@pytest.mark.contract("LOC-5")
def test_loc5_before_first_header(transcript, run):
    res = run("locate", transcript, "вступление без")
    assert res.returncode == 0
    assert res.stdout == "NOHEAD\tвступление без\n"


@pytest.mark.contract("LOC-6")
def test_loc6_empty_quote_crashes(transcript, run):
    res = run("locate", transcript, "")
    assert res.returncode == 1
    assert "IndexError" in res.stderr
