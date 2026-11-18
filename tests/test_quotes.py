"""Контракт `scripts/check_quotes.py` — capability quotes (QUO-)."""

import pytest

from conftest import write

TRANSCRIPT = """## [00:00:00](https://youtu.be/vid1?t=0)

Сегодня мы поговорим про ёлки и сервера. Модель ⟦?: термин⟧ надо версионировать всегда.

## [00:01:00](https://youtu.be/vid1?t=60)

Второй блок про деплой в прод без страха.

## [00:02:00](https://youtu.be/vid1?t=120)

Третий блок про мониторинг метрик качества.

## [00:03:00](https://youtu.be/vid1?t=180)

Четвёртый блок про откат релиза назад.
"""


def link(t):
    return f"[0:00:00](https://youtu.be/vid1?t={t})"


@pytest.fixture
def kb(tmp_path):
    write(tmp_path / "transcripts" / "L01.md", TRANSCRIPT)
    return tmp_path


def check(run, kb, doc, *, where="lectures/L01.md", args=()):
    write(kb / where, doc)
    return run("check_quotes", kb, *args)


@pytest.mark.contract("QUO-1")
def test_quo1_verbatim_quote_passes(kb, run):
    res = check(run, kb, f"Он сказал: «Мы поговорим про ЁЛКИ» ({link(0)}).\n")
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-1")
def test_quo1_inserts_marks_and_ellipsis_ignored(kb, run):
    doc = (
        f"«поговорим про елки … надо версионировать всегда» ({link(0)}).\n"
        f"«модель [ML] надо   версионировать» ({link(0)}).\n"
    )
    res = check(run, kb, doc)
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-2")
def test_quo2_missing_quote_is_miss(kb, run):
    res = check(run, kb, f"«этого никто не говорил» ({link(60)}).\n")
    assert res.returncode == 1
    assert res.stdout == "MISS\tlectures/L01.md\tL01\t«этого никто не говорил»\n"


@pytest.mark.contract("QUO-3")
def test_quo3_short_quote_is_short_not_error(kb, run):
    res = check(run, kb, f"Это «чушь собачья» ({link(0)}).\n")
    assert res.returncode == 0
    assert res.stdout == "SHORT\tlectures/L01.md\tL01\t«чушь собачья»\n"


@pytest.mark.contract("QUO-4")
def test_quo4_neighbour_block_accepted(kb, run):
    res = check(run, kb, f"«деплой в прод без страха» ({link(0)}).\n")
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-4")
def test_quo4_far_block_is_addr(kb, run):
    res = check(run, kb, f"«откат релиза назад» ({link(0)}).\n")
    assert res.returncode == 1
    assert res.stdout == (
        "ADDR\tlectures/L01.md\tL01\t«откат релиза назад»\tссылка t=0, цитата в блоках [180]\n"
    )


@pytest.mark.contract("QUO-4")
def test_quo4_link_inside_block_but_not_at_start_is_addr(kb, run):
    res = check(run, kb, f"«мониторинг метрик качества» ({link(125)}).\n")
    assert res.returncode == 1
    assert res.stdout.startswith("ADDR\tlectures/L01.md\tL01\t«мониторинг метрик качества»\t")


@pytest.mark.contract("QUO-4")
def test_quo4_link_after_quote_wins(kb, run):
    res = check(run, kb, f"{link(0)} «откат релиза назад» ({link(180)}).\n")
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-5")
def test_quo5_any_link_of_address_line(kb, run):
    doc = f"**мониторинг** — «мониторинг метрик качества» L01 {link(0)}, {link(180)}\n"
    res = check(run, kb, doc, where="glossary/terms.md")
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-6")
def test_quo6_frontmatter_lecture_without_link(kb, run):
    res = check(run, kb, "---\nlecture: L01\n---\nТекст «этого никто не говорил».\n")
    assert res.returncode == 1
    assert res.stdout == "MISS\tlectures/L01.md\tL01\t«этого никто не говорил»\n"


@pytest.mark.contract("QUO-6")
def test_quo6_unknown_transcript_skipped(kb, run):
    doc = (
        "Без ссылки: «этого никто не говорил».\n"
        "Чужое видео: «этого никто не говорил» ([0:00:00](https://youtu.be/other?t=0)).\n"
    )
    res = check(run, kb, doc)
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-6")
def test_quo6_only_lnn_transcripts_loaded(kb, run):
    (kb / "transcripts" / "L01.md").rename(kb / "transcripts" / "L01-intro.md")
    res = check(run, kb, f"«этого никто не говорил» ({link(0)}).\n")
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-7")
def test_quo7_default_files(kb, run):
    bad = f"«этого никто не говорил» ({link(0)}).\n"
    for where in [
        "practices/ops/a.md",
        "practices/ops/deep/b.md",
        "lectures/L01.md",
        "glossary/terms.md",
        "notes/x.md",
        "lectures/sub/c.md",
    ]:
        write(kb / where, bad)
    res = run("check_quotes", kb)
    assert [line.split("\t")[1] for line in res.stdout.splitlines()] == [
        "glossary/terms.md",
        "lectures/L01.md",
        "practices/ops/a.md",
        "practices/ops/deep/b.md",
    ]


@pytest.mark.contract("QUO-7")
def test_quo7_explicit_files_only(kb, run):
    bad = f"«этого никто не говорил» ({link(0)}).\n"
    write(kb / "lectures" / "L01.md", bad)
    one = write(kb / "notes" / "x.md", bad)
    res = run("check_quotes", kb, one)
    assert res.stdout == "MISS\tnotes/x.md\tL01\t«этого никто не говорил»\n"


@pytest.mark.contract("QUO-7")
def test_quo7_blockquote_markers_ignored(kb, run):
    doc = f"> «Четвёртый блок про\n> откат релиза» ({link(180)})\n"
    res = check(run, kb, doc)
    assert (res.returncode, res.stdout) == (0, "")


@pytest.mark.contract("QUO-8")
def test_quo8_fragments_order_not_checked(kb, run):
    res = check(run, kb, f"«надо версионировать всегда … поговорим про ёлки» ({link(0)}).\n")
    assert (res.returncode, res.stdout) == (0, "")
