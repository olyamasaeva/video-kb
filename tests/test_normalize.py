"""Контракт `scripts/normalize.py` — capability normalize (NRM-)."""

import os
from pathlib import Path

import pytest

from conftest import SCRIPTS, write

HEAD = "## [00:00:00](https://youtu.be/v?t=0)"


def rules(tmp_path, *rows, name="rules.tsv"):
    return write(tmp_path / name, "".join(r + "\n" for r in rows))


def normalize(run, tmp_path, text, *rule_files, report=False):
    src = write(tmp_path / "L01.raw.md", text)
    out = tmp_path / "L01.md"
    args = [src, "--rules", *rule_files, "--out", out]
    if report:
        args += ["--report", tmp_path / "report.md"]
    return run("normalize", *args), out


@pytest.mark.contract("NRM-1")
def test_nrm1_rules_case_insensitive_with_groups(tmp_path, run):
    r = rules(tmp_path, "ONNX\tон\\s+икс\tONNX", "TensorRT\t(тензор)\\s*рт\tTensorRT[\\1]")
    res, out = normalize(run, tmp_path, "он икс и Он  Икс, тензор рт", r)
    assert res.returncode == 0
    assert out.read_text(encoding="utf-8") == "ONNX и ONNX, TensorRT[тензор]\n"
    assert res.stdout.strip() == f"замен: 3, сработало правил: 2/2 -> {out}"


@pytest.mark.contract("NRM-1")
def test_nrm1_rules_apply_in_file_order(tmp_path, run):
    first = rules(tmp_path, "a\tальфа\tбета", name="common.tsv")
    second = rules(tmp_path, "b\tбета\tгамма", name="L01.tsv")
    res, out = normalize(run, tmp_path, "альфа", first, second)
    assert out.read_text(encoding="utf-8") == "гамма\n"
    res, out = normalize(run, tmp_path, "альфа", second, first)
    assert out.read_text(encoding="utf-8") == "бета\n"


@pytest.mark.contract("NRM-2")
def test_nrm2_headers_and_comments_untouched(tmp_path, run):
    r = rules(tmp_path, "ONNX\tон икс\tONNX")
    text = f"{HEAD}\n\nон икс\n<!-- он икс -->\n## [он икс]\n"
    res, out = normalize(run, tmp_path, text, r)
    assert out.read_text(encoding="utf-8") == f"{HEAD}\n\nONNX\n<!-- он икс -->\n## [он икс]\n"


@pytest.mark.contract("NRM-3")
def test_nrm3_double_question_marks_instead_of_replacing(tmp_path, run):
    r = rules(tmp_path, "throughput\tсрупут\t??throughput или «сплит»?")
    res, out = normalize(run, tmp_path, "Срупут растёт", r)
    assert out.read_text(encoding="utf-8") == "Срупут ⟦?: throughput или «сплит»?⟧ растёт\n"
    assert "замен: 1," in res.stdout


@pytest.mark.contract("NRM-4")
def test_nrm4_blank_and_hash_lines_skipped(tmp_path, run):
    r = rules(tmp_path, "# заголовок", "", "   # с отступом", "x\tикс\tX")
    res, out = normalize(run, tmp_path, "икс", r)
    assert res.returncode == 0
    assert "сработало правил: 1/1" in res.stdout


@pytest.mark.contract("NRM-4")
def test_nrm4_short_row_fails_without_output(tmp_path, run):
    good = rules(tmp_path, "x\tикс\tX", name="good.tsv")
    bad = rules(tmp_path, "x\tикс\tX", "y\tигрек", name="bad.tsv")
    res, out = normalize(run, tmp_path, "икс", good, bad)
    assert res.returncode == 1
    assert res.stderr.strip() == f"{bad}:2: нужно минимум 3 колонки"
    assert not out.exists()


@pytest.mark.contract("NRM-4")
def test_nrm4_broken_regex_fails_without_output(tmp_path, run):
    bad = rules(tmp_path, "x\t(икс\tX")
    res, out = normalize(run, tmp_path, "икс", bad)
    assert res.returncode == 1
    assert res.stderr.startswith(f"{bad}:1: битая регулярка — ")
    assert not out.exists()


@pytest.mark.contract("NRM-5")
def test_nrm5_report(tmp_path, run):
    r = rules(
        tmp_path,
        "ONNX\tон\\s+икс\tONNX\tASR ломает",
        "ONNX\tонникс\tONNX",
        "TensorRT\tтензор рт\tTensorRT",
        "throughput\tсрупут\t??throughput?",
        "дохлое\tникогда\tX",
    )
    text = "он икс, Он Икс, ОН  ИКС, онникс, тензор рт, срупут"
    res, out = normalize(run, tmp_path, text, r, report=True)
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Всего замен: **6** по 4 терминам (4 правил из 5 сработали)." in report
    assert "Из них помечено как неоднозначное, без замены: **1**." in report
    table = [line for line in report.splitlines() if line.startswith("| ")]
    assert table[1:4] == [
        "| ONNX | 4 | `он икс`, `Он Икс`, `ОН  ИКС`, `онникс` | ASR ломает |",
        "| TensorRT | 1 | `тензор рт` |  |",
        "| throughput | 1 | `срупут` |  |",
    ]
    assert "## Правила без срабатываний" in report
    assert "| дохлое | `никогда` | rules.tsv:5 |" in report


@pytest.mark.contract("NRM-6")
def test_nrm6_no_rules_fails_silently(tmp_path, run):
    r = rules(tmp_path, "# только комментарий")
    res, out = normalize(run, tmp_path, "икс", r)
    assert res.returncode == 1
    assert res.stdout == "" and res.stderr == ""
    assert not out.exists()


@pytest.mark.contract("NRM-7")
def test_nrm7_regex_timeout(tmp_path):
    import subprocess
    import sys
    import time

    from conftest import SCRIPTS

    r = rules(tmp_path, "X\t(a+)+$\tb")
    src = write(tmp_path / "L01.raw.md", "a" * 40 + "!\n")
    out, report = tmp_path / "L01.md", tmp_path / "report.md"
    args = [sys.executable, str(SCRIPTS / "normalize.py"), str(src), "--rules", str(r)]
    args += ["--out", str(out), "--report", str(report), "--timeout-sec", "1"]
    started = time.monotonic()
    res = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    assert time.monotonic() - started < 10
    assert res.returncode == 3, res.stderr
    assert "rules.tsv:1" in res.stderr and "1 с" in res.stderr
    assert not out.exists() and not report.exists()


@pytest.mark.contract("NRM-8")
def test_nrm8_input_size_limit(tmp_path, run):
    r = rules(tmp_path, "X\tzzz\ty")
    big = ("слово " * 1000 + "\n") * 2000
    res, out = normalize(run, tmp_path, big, r)
    assert res.returncode == 3
    assert "L01.raw.md" in res.stderr and "20 МиБ" in res.stderr
    assert not out.exists()


@pytest.mark.contract("NRM-9")
def test_nrm9_symlinked_output_rejected(tmp_path, run):
    r = rules(tmp_path, "x\tикс\tX")
    src = write(tmp_path / "L01.raw.md", "икс\n")
    victim = write(tmp_path / "victim.txt", "не трогать\n")
    out, report = tmp_path / "L01.md", tmp_path / "report.md"
    out.symlink_to(victim)
    res = run("normalize", src, "--rules", r, "--out", out, "--report", report)
    assert res.returncode == 2
    assert str(out) in res.stderr
    assert victim.read_text(encoding="utf-8") == "не трогать\n"
    assert not report.exists()
    out.unlink()
    report.symlink_to(victim)
    res = run("normalize", src, "--rules", r, "--out", out, "--report", report)
    assert res.returncode == 2
    assert victim.read_text(encoding="utf-8") == "не трогать\n"
    assert not out.exists()


@pytest.mark.contract("NRM-9")
def test_nrm9_symlinked_parent_rejected(tmp_path, run):
    r = rules(tmp_path, "x\tикс\tX")
    src = write(tmp_path / "L01.raw.md", "икс\n")
    victim = tmp_path / "victim"
    victim.mkdir()
    (tmp_path / "out").symlink_to(victim)
    res = run("normalize", src, "--rules", r, "--out", tmp_path / "out" / "L01.md")
    assert res.returncode == 2
    assert list(victim.iterdir()) == []


@pytest.mark.contract("NRM-9")
def test_nrm9_atomic_replace(tmp_path, run):
    r = rules(tmp_path, "x\tикс\tX")
    src = write(tmp_path / "L01.raw.md", "икс\n")
    victim = write(tmp_path / "victim.txt", "не трогать\n")
    out = tmp_path / "L01.md"
    os.link(victim, out)
    res = run("normalize", src, "--rules", r, "--out", out)
    assert res.returncode == 0, res.stderr
    assert out.read_text(encoding="utf-8") == "X\n"
    assert victim.read_text(encoding="utf-8") == "не трогать\n"


def system_link_to_shared_dir():
    """Ссылка root вне домашней папки, ведущая в общую записываемую папку (`/var/lock`)."""
    link = Path("/var/lock")
    if not link.is_symlink() or link.lstat().st_uid != 0:
        return None
    target = link.resolve()
    if not os.access(target, os.W_OK) or Path.home().resolve() in target.parents:
        return None
    return link


@pytest.mark.contract("NRM-9")
def test_nrm9_root_link_outside_home_rejected(tmp_path, run):
    link = system_link_to_shared_dir()
    if link is None:
        pytest.skip("нет ссылки root на общую записываемую папку")
    r = rules(tmp_path, "x\tикс\tX")
    src = write(tmp_path / "L01.raw.md", "икс\n")
    shared = link.resolve() / f"video-kb-test-{os.getpid()}-{tmp_path.name}"
    shared.mkdir()
    try:
        res = run("normalize", src, "--rules", r, "--out", link / shared.name / "L01.md")
        assert res.returncode == 2, res.stdout
        assert "символическая ссылка" in res.stderr
        assert list(shared.iterdir()) == []
    finally:
        for item in shared.iterdir():
            item.unlink()
        shared.rmdir()


@pytest.mark.contract("NRM-9")
def test_nrm9_links_allowed_only_up_to_home(tmp_path, run):
    r = rules(tmp_path, "x\tикс\tX")
    src = write(tmp_path / "L01.raw.md", "икс\n")
    real_home = tmp_path / "disk" / "someone"
    (real_home / "kb").mkdir(parents=True)
    home = tmp_path / "home"
    home.symlink_to(real_home)
    res = run(
        "normalize", src, "--rules", r, "--out", home / "kb" / "L01.md", env={"HOME": str(home)}
    )
    assert res.returncode == 0, res.stderr
    assert (real_home / "kb" / "L01.md").read_text(encoding="utf-8") == "X\n"
    victim = tmp_path / "victim"
    victim.mkdir()
    (real_home / "kb" / "via").symlink_to(victim)
    res = run(
        "normalize",
        src,
        "--rules",
        r,
        "--out",
        home / "kb" / "via" / "L01.md",
        env={"HOME": str(home)},
    )
    assert res.returncode == 2
    assert list(victim.iterdir()) == []


WALK = ("trusted_start", "enter", "open_dir")


def test_path_walk_same_in_both_scripts():
    """Обход пути повторён в двух скриптах (общего модуля нет): копии не расходятся."""
    import ast

    sources = {}
    for name in ("normalize", "skill_evidence"):
        text = (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        found = {
            node.name: ast.get_source_segment(text, node)
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in WALK
        }
        assert set(found) == set(WALK), name
        sources[name] = found
    assert sources["normalize"] == sources["skill_evidence"]
