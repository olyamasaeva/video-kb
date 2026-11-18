"""Контракт `scripts/skill_evidence.py` — capability skills (SKL-)."""

import hashlib
import json
import os
import resource
import subprocess
import sys

import pytest

from conftest import (
    SCRIPTS,
    claude_assistant,
    claude_tool_result,
    claude_user,
    codex_records,
    write,
)

CANDIDATES = "кандидат\tкарточки\tкогда\neval-агента\tpractices/eval/a.md\tпишу eval для агента\n"
QUERIES = "кандидат\tфраза\neval-агента\tнапишу eval агенту\n"


@pytest.fixture
def kb(tmp_path):
    base = tmp_path / "kb"
    write(base / "skills" / "кандидаты.tsv", CANDIDATES)
    write(base / "skills" / "запросы.tsv", QUERIES)
    return base


@pytest.fixture
def evidence(run, kb, logs, tmp_path):
    """Запуск скрипта с журналами, скиллами, правилами и кешем только во `tmp_path`."""

    def call(*extra):
        return run(
            "skill_evidence",
            kb,
            "--журналы-claude",
            logs.claude_root,
            "--журналы-codex",
            logs.codex_root,
            "--скиллы",
            tmp_path / "skills",
            "--правила",
            tmp_path / "rules",
            "--кеш",
            tmp_path / "cache",
            *extra,
            cwd=tmp_path,
        )

    return call


def report(kb):
    return json.loads((kb / "skills" / "доказательства.json").read_text(encoding="utf-8"))


def candidate(kb, name="eval-агента"):
    return next(c for c in report(kb)["кандидаты"] if c["кандидат"] == name)


def cache_dir(cache_root, kb):
    return cache_root / hashlib.sha256(str(kb.resolve()).encode("utf-8")).hexdigest()[:16]


def cached(tmp_path, kb):
    return json.loads((cache_dir(tmp_path / "cache", kb) / "sessions.json").read_text("utf-8"))


@pytest.mark.contract("SKL-1")
def test_skl1_unknown_candidate(kb, logs, evidence):
    write(kb / "skills" / "запросы.tsv", QUERIES + "чужой\tкакая-то фраза\n")
    logs.claude("s1", [claude_user("напиши eval агенту")])
    res = evidence()
    assert res.returncode == 2
    assert "запросы.tsv:3" in res.stderr


@pytest.mark.contract("SKL-1")
def test_skl1_missing_file(kb, logs, evidence):
    (kb / "skills" / "кандидаты.tsv").unlink()
    logs.claude("s1", [claude_user("напиши eval агенту")])
    res = evidence()
    assert res.returncode == 2
    assert "кандидаты.tsv" in res.stderr


@pytest.mark.contract("SKL-2")
def test_skl2_only_user_turns(kb, logs, evidence):
    logs.claude(
        "s1",
        [
            claude_user("привет"),
            claude_assistant("напишу eval агенту"),
            claude_tool_result("напишу eval агенту"),
            claude_user("напишу eval агенту", isMeta=True),
            claude_user("напишу eval агенту", isSidechain=True),
        ],
    )
    logs.codex("c1", codex_records("/work/proj", ["привет"], agent=["напишу eval агенту"]))
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0


@pytest.mark.contract("SKL-2")
def test_skl2_compact_summary_and_codex_subagent(kb, logs, evidence):
    logs.claude(
        "s1",
        [
            claude_user("привет"),
            claude_user("напишу eval агенту", isCompactSummary=True),
            claude_user("[bb system] @thread:x completed: напишу eval агенту"),
            claude_user("You are continuing an earlier session: напишу eval агенту"),
            claude_user("<command-message>напишу eval агенту</command-message>"),
        ],
    )
    records = codex_records("/work/proj", ["напишу eval агенту"])
    records[0]["payload"]["source"] = {"subagent": {"other": "guardian"}}
    logs.codex("c1", records)
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0


@pytest.mark.contract("SKL-2")
def test_skl2_both_engines(kb, logs, evidence):
    logs.claude("s1", [claude_user([{"type": "text", "text": "напишу eval агенту"}])])
    logs.codex("c1", codex_records("/work/proj", ["напишу eval агенту"]))
    res = evidence()
    assert res.returncode == 0, res.stderr
    found = candidate(kb)
    assert found["сессий"] == 2
    assert sorted(s["движок"] for s in found["сессии"]) == ["claude", "codex"]


@pytest.mark.contract("SKL-3")
def test_skl3_word_forms(kb, logs, evidence):
    logs.claude("s1", [claude_user("Напиши евал… нет, eval для агентов"), claude_user("ещё eval")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    found = candidate(kb)
    assert found["сессий"] == 1
    assert found["сессии"][0]["фразы"] == ["напишу eval агенту"]


@pytest.mark.contract("SKL-3")
def test_skl3_words_must_share_one_turn(kb, logs, evidence):
    logs.claude("s1", [claude_user("напиши eval"), claude_user("для агентов")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0


@pytest.mark.contract("SKL-3")
def test_skl3_window(kb, logs, evidence):
    logs.claude("s1", [claude_user("напишу eval агенту", days=45), claude_user("ок", days=1)])
    res = evidence("--дней", 30)
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0


@pytest.mark.contract("SKL-4")
def test_skl4_build_sessions_excluded(kb, logs, evidence):
    logs.claude("s1", [claude_user("напишу eval агенту", cwd=str(kb / "lectures"))])
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0
    assert "исключено сессий сборки: 1" in (kb / "skills" / "доказательства.md").read_text()
    res = evidence("--включить-сборку")
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 1


@pytest.mark.contract("SKL-4")
def test_skl4_video_kb_call_excluded(kb, logs, evidence):
    logs.codex("c1", codex_records("/work/proj", ["/video-kb add L01", "напишу eval агенту"]))
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 0
    assert report(kb)["исключено_сборки"] == 1


@pytest.mark.contract("SKL-5")
def test_skl5_no_text_no_paths(kb, logs, evidence, tmp_path):
    turn = "напишу eval агенту МАРКЕРТЕКСТА42"
    path = logs.claude("s1", [claude_user(turn)], project="-work-МАРКЕРПАПКИ42")
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 1
    for f in (kb / "skills").iterdir():
        text = f.read_text(encoding="utf-8")
        assert "МАРКЕРТЕКСТА42" not in text, f.name
        assert "МАРКЕРПАПКИ42" not in text, f.name
    session_id = candidate(kb)["сессии"][0]["id"]
    assert len(session_id) == 16 and int(session_id, 16) >= 0
    cache = cached(tmp_path, kb)
    assert cache["база"] == str(kb.resolve())
    assert cache["сессии"][session_id]["путь"] == str(path)
    assert "МАРКЕРТЕКСТА42" not in res.stdout and "МАРКЕРПАПКИ42" not in res.stdout


@pytest.mark.contract("SKL-6")
def test_skl6_coverage_and_budget(kb, logs, evidence, tmp_path):
    description = "Напишет eval агенту по шагам."
    write(
        tmp_path / "skills" / "agent-eval" / "SKILL.md",
        f"---\nname: agent-eval\ndescription: {description}\n---\nтело\n",
    )
    write(
        tmp_path / "skills" / "other" / "SKILL.md",
        "---\nname: other\ndescription: x\n---\nнапишу eval агенту\n",
    )
    logs.claude("s1", [claude_user("привет")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    covered = candidate(kb)["покрытие"]["скиллы"]
    assert len(covered) == 1 and covered[0].startswith("скилл-")
    assert report(kb)["бюджет"] == {"скиллов": 2, "знаков_описаний": len(description) + 1}


@pytest.mark.contract("SKL-6")
def test_skl6_rules(kb, logs, evidence, tmp_path):
    write(tmp_path / "rules" / "AGENTS.md", "# Правила\n\nКогда напишешь eval для агента — X.\n")
    logs.claude("s1", [claude_user("привет")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    covered = candidate(kb)["покрытие"]["правила"]
    assert len(covered) == 1 and covered[0].startswith("правило-")


@pytest.mark.contract("SKL-6")
def test_skl6_cwd_not_default(kb, logs, tmp_path):
    project = tmp_path / "project"
    write(project / "AGENTS.md", "напишу eval агенту\n")
    write(
        project / ".claude" / "skills" / "x" / "SKILL.md",
        "---\nname: x\ndescription: напишу eval агенту\n---\n",
    )
    home = tmp_path / "home"
    home.mkdir()
    logs.claude("s1", [claude_user("привет")])
    args = [
        sys.executable,
        str(SCRIPTS / "skill_evidence.py"),
        str(kb),
        "--журналы-claude",
        str(logs.claude_root),
        "--журналы-codex",
        str(logs.codex_root),
        "--кеш",
        str(tmp_path / "cache"),
    ]
    env = {**os.environ, "HOME": str(home)}
    res = subprocess.run(args, capture_output=True, text=True, cwd=project, env=env, check=False)
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["покрытие"] == {"скиллы": [], "правила": []}
    assert report(kb)["бюджет"]["скиллов"] == 0


@pytest.mark.contract("SKL-7")
def test_skl7_no_logs(kb, evidence):
    res = evidence()
    assert res.returncode == 3
    assert "журналов нет" in (kb / "skills" / "доказательства.md").read_text(encoding="utf-8")


@pytest.mark.contract("SKL-7")
def test_skl7_logs_per_engine(kb, logs, evidence):
    logs.claude("s1", [claude_user("привет", days=10), claude_user("ещё", days=2)])
    logs.claude("s2", [claude_user("привет", days=3)])
    logs.claude("old", [claude_user("привет", days=90)])
    res = evidence()
    assert res.returncode == 0, res.stderr
    engines = report(kb)["журналы"]
    assert engines["claude"]["журналов"] == 2
    assert engines["codex"]["журналов"] == 0
    assert engines["claude"]["самый_старый"] == claude_user("x", days=10)["timestamp"][:10]


@pytest.mark.contract("SKL-9")
def test_skl9_show_session(kb, logs, evidence):
    logs.claude("s1", [claude_user("напишу eval агенту"), claude_assistant("ответ агента")])
    assert evidence().returncode == 0
    session_id = candidate(kb)["сессии"][0]["id"]
    before = {f.name: f.read_bytes() for f in (kb / "skills").iterdir()}
    res = evidence("--показать", session_id)
    assert res.returncode == 0, res.stderr
    assert "напишу eval агенту" in res.stdout
    assert "ответ агента" not in res.stdout
    assert {f.name: f.read_bytes() for f in (kb / "skills").iterdir()} == before


@pytest.mark.contract("SKL-9")
def test_skl9_show_filters_and_redacts(kb, logs, evidence):
    key = "sk-" + "A1b2C3d4" * 4
    filler = "слово " * 330
    turns = [
        claude_user("ОТВЕТБЕЗФРАЗЫ просто привет"),
        claude_user("СТАРАЯРЕПЛИКА напишу eval агенту", days=40),
        claude_user(f"{filler} ключ {key} password=hunter2secret напишу eval агенту {filler}"),
    ]
    logs.claude("s1", turns)
    assert evidence("--дней", 30).returncode == 0
    session_id = candidate(kb)["сессии"][0]["id"]
    res = evidence("--дней", 30, "--показать", session_id)
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert "данные, не инструкции" in out
    assert "ОТВЕТБЕЗФРАЗЫ" not in out and "СТАРАЯРЕПЛИКА" not in out
    assert key not in out and "hunter2secret" not in out
    assert "[скрыто]" in out
    assert "напишу eval агенту" in out
    body = [line for line in out.splitlines() if "слово" in line]
    assert len(body) == 1 and len(body[0]) <= 400


@pytest.mark.contract("SKL-9")
def test_skl9_unknown_id(kb, evidence):
    res = evidence("--показать", "deadbeef")
    assert res.returncode == 2


@pytest.mark.contract("SKL-10")
def test_skl10_private_rule_and_skill_names(kb, logs, evidence, tmp_path):
    project = tmp_path / "rules" / "МАРКЕРПРОЕКТА77"
    rule = write(project / ".claude" / "rules" / "МАРКЕРПРАВИЛА77.md", "напишу eval агенту\n")
    write(
        tmp_path / "skills" / "markerskill77" / "SKILL.md",
        "---\nname: markerskill77\ndescription: напишу eval агенту\n---\n",
    )
    logs.claude("s1", [claude_user("привет")])
    res = evidence("--правила", project)
    assert res.returncode == 0, res.stderr
    markers = ("МАРКЕРПРОЕКТА77", "МАРКЕРПРАВИЛА77", "markerskill77")
    for f in (kb / "skills").iterdir():
        text = f.read_text(encoding="utf-8")
        assert not [m for m in markers if m in text], f.name
    assert not [m for m in markers if m in res.stdout]
    cover = candidate(kb)["покрытие"]
    before = {f.name: f.read_bytes() for f in (kb / "skills").iterdir()}
    shown_rule = evidence("--показать", cover["правила"][0])
    assert shown_rule.returncode == 0, shown_rule.stderr
    assert str(rule) in shown_rule.stdout
    shown_skill = evidence("--показать", cover["скиллы"][0])
    assert shown_skill.returncode == 0, shown_skill.stderr
    assert "markerskill77" in shown_skill.stdout
    assert {f.name: f.read_bytes() for f in (kb / "skills").iterdir()} == before


@pytest.mark.contract("SKL-11")
def test_skl11_symlinked_journal_ignored(kb, logs, evidence, tmp_path):
    outside = jsonl_outside(tmp_path)
    project = logs.claude_root / "-work-proj"
    project.mkdir(parents=True)
    (project / "s1.jsonl").symlink_to(outside)
    res = evidence()
    assert candidate(kb)["сессий"] == 0
    assert report(kb)["журналы"]["claude"]["журналов"] == 0
    assert res.returncode == 3


def jsonl_outside(tmp_path):
    line = json.dumps(claude_user("напишу eval агенту"), ensure_ascii=False)
    return write(tmp_path / "outside" / "secret.jsonl", line + "\n")


@pytest.mark.contract("SKL-11")
def test_skl11_symlinked_output_rejected(kb, logs, evidence, tmp_path):
    victim = write(tmp_path / "victim.txt", "не трогать\n")
    (kb / "skills" / "доказательства.md").symlink_to(victim)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = evidence()
    assert res.returncode == 2
    assert "доказательства.md" in res.stderr
    assert victim.read_text(encoding="utf-8") == "не трогать\n"


@pytest.mark.contract("SKL-11")
def test_skl11_symlinked_cache_rejected(kb, logs, evidence, tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    link = cache_dir(tmp_path / "cache", kb)
    link.parent.mkdir(parents=True)
    link.symlink_to(victim)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = evidence()
    assert res.returncode == 2
    assert list(victim.iterdir()) == []


@pytest.mark.contract("SKL-12")
def test_skl12_wrong_shapes_skipped(kb, logs, evidence):
    logs.claude(
        "s1",
        [
            ["user"],
            {"type": "user", "message": "напишу eval агенту"},
            {"type": "user", "message": {"content": 5}},
            {"type": "user", "message": {"content": [5, {"type": "text", "text": 7}]}},
            {"type": "user", "cwd": 5, "timestamp": 7, "message": {"content": "x"}},
            claude_user("напишу eval агенту"),
        ],
    )
    records = codex_records("/work/proj", ["напишу eval агенту"])
    records[1:1] = [
        {"type": "event_msg", "payload": [1]},
        {"type": "session_meta", "payload": {"cwd": 5, "source": "cli"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": 5}},
        "строка",
    ]
    logs.codex("c1", records)
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert candidate(kb)["сессий"] == 2


@pytest.mark.contract("SKL-12")
def test_skl12_oversized_line_incomplete(kb, logs, evidence):
    big = logs.claude("big", [claude_user("привет")])
    with big.open("a", encoding="utf-8") as f:
        f.write("x" * 1_000_001 + "\n")
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = evidence()
    assert res.returncode == 4, res.stderr
    assert "скан неполный" in (kb / "skills" / "доказательства.md").read_text(encoding="utf-8")
    assert candidate(kb)["сессий"] == 1


@pytest.mark.skipif(os.geteuid() == 0, reason="root читает файл без прав")
@pytest.mark.contract("SKL-12")
def test_skl12_unreadable_journal_incomplete(kb, logs, evidence):
    locked = logs.claude("locked", [claude_user("напишу eval агенту")])
    locked.chmod(0)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    try:
        res = evidence()
    finally:
        locked.chmod(0o600)
    assert res.returncode == 4, res.stderr
    assert "locked.jsonl" in res.stderr
    assert "скан неполный" in (kb / "skills" / "доказательства.md").read_text(encoding="utf-8")


def limit_memory():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))


@pytest.mark.contract("SKL-13")
def test_skl13_long_word_bounded_memory(kb, logs, tmp_path):
    logs.claude("s1", [claude_user("а" * 60_000)])
    args = [
        sys.executable,
        str(SCRIPTS / "skill_evidence.py"),
        str(kb),
        "--журналы-claude",
        str(logs.claude_root),
        "--журналы-codex",
        str(logs.codex_root),
        "--скиллы",
        str(tmp_path / "skills"),
        "--правила",
        str(tmp_path / "rules"),
        "--кеш",
        str(tmp_path / "cache"),
    ]
    res = subprocess.run(
        args, capture_output=True, text=True, preexec_fn=limit_memory, timeout=60, check=False
    )
    assert res.returncode == 0, res.stderr[-500:]
    assert candidate(kb)["сессий"] == 0


@pytest.mark.contract("SKL-14")
def test_skl14_cache_private_and_minimal(kb, logs, evidence, tmp_path):
    logs.claude("s1", [claude_user("напишу eval агенту")])
    logs.claude("s2", [claude_user("про другое")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    folder = cache_dir(tmp_path / "cache", kb)
    assert folder.stat().st_mode & 0o777 == 0o700
    assert (folder / "sessions.json").stat().st_mode & 0o777 == 0o600
    assert set(cached(tmp_path, kb)["сессии"]) == {candidate(kb)["сессии"][0]["id"]}


@pytest.mark.contract("SKL-15")
def test_skl15_cache_namespaced_by_path(logs, run, tmp_path):
    bases = []
    for side in ("a", "b"):
        base = tmp_path / side / "kb"
        write(base / "skills" / "кандидаты.tsv", CANDIDATES)
        write(base / "skills" / "запросы.tsv", QUERIES)
        bases.append(base)
    logs.claude("s1", [claude_user("напишу eval агенту")])

    def call(base, *extra):
        return run(
            "skill_evidence",
            base,
            "--журналы-claude",
            logs.claude_root,
            "--журналы-codex",
            logs.codex_root,
            "--скиллы",
            tmp_path / "skills",
            "--правила",
            tmp_path / "rules",
            "--кеш",
            tmp_path / "cache",
            *extra,
        )

    assert call(bases[0]).returncode == 0
    session_id = candidate(bases[0])["сессии"][0]["id"]
    assert cache_dir(tmp_path / "cache", bases[0]) != cache_dir(tmp_path / "cache", bases[1])
    assert call(bases[0], "--показать", session_id).returncode == 0
    assert call(bases[1], "--показать", session_id).returncode == 2


def load_module():
    """`skill_evidence.py` как модуль: для сценариев, которые подменяют функции внутри."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("skill_evidence", SCRIPTS / "skill_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def in_process_args(kb, logs, tmp_path):
    return [
        str(kb),
        "--журналы-claude",
        str(logs.claude_root),
        "--журналы-codex",
        str(logs.codex_root),
        "--скиллы",
        str(tmp_path / "skills"),
        "--правила",
        str(tmp_path / "rules"),
        "--кеш",
        str(tmp_path / "cache"),
    ]


@pytest.mark.contract("SKL-9")
def test_skl9_redacts_quoted_secrets(kb, logs, evidence):
    reply = 'напишу eval агенту {"password": "hunter2"} и token="ДВАСЛОВА ТРИСЛОВА" дальше'
    logs.claude("s1", [claude_user(reply)])
    assert evidence().returncode == 0
    res = evidence("--показать", candidate(kb)["сессии"][0]["id"])
    assert res.returncode == 0, res.stderr
    for secret in ("hunter2", "ДВАСЛОВА", "ТРИСЛОВА"):
        assert secret not in res.stdout
    assert "[скрыто]" in res.stdout


@pytest.mark.contract("SKL-11")
def test_skl11_journal_swapped_after_check(kb, logs, tmp_path, monkeypatch, capsys):
    import io

    journal = logs.claude("s1", [claude_user("привет")])
    outside = jsonl_outside(tmp_path)
    module = load_module()
    swapped = []

    def swapping(opener):
        def wrapper(file, *args, **kwargs):
            if not swapped and isinstance(file, (str, os.PathLike)):
                if os.fspath(file) == str(journal):
                    journal.unlink()
                    journal.symlink_to(outside)
                    swapped.append(True)
            return opener(file, *args, **kwargs)

        return wrapper

    monkeypatch.setattr(io, "open", swapping(io.open))
    monkeypatch.setattr(os, "open", swapping(os.open))
    code = module.main(in_process_args(kb, logs, tmp_path))
    capsys.readouterr()
    assert swapped
    assert candidate(kb)["сессий"] == 0
    assert code in (3, 4)


@pytest.mark.contract("SKL-11")
def test_skl11_symlinked_cache_ancestor_rejected(kb, logs, run, tmp_path):
    victim = tmp_path / "victim"
    victim.mkdir()
    (tmp_path / "via").symlink_to(victim)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = run(
        "skill_evidence",
        kb,
        "--журналы-claude",
        logs.claude_root,
        "--журналы-codex",
        logs.codex_root,
        "--скиллы",
        tmp_path / "skills",
        "--правила",
        tmp_path / "rules",
        "--кеш",
        tmp_path / "via" / "cache",
    )
    assert res.returncode == 2
    assert list(victim.iterdir()) == []


@pytest.mark.contract("SKL-15")
def test_skl15_foreign_namespace_not_overwritten(kb, logs, evidence, tmp_path):
    folder = cache_dir(tmp_path / "cache", kb)
    foreign = '{"база": "/elsewhere/kb", "сессии": {}, "покрытие": {}}\n'
    write(folder / "sessions.json", foreign)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = evidence()
    assert res.returncode == 2
    assert (folder / "sessions.json").read_text(encoding="utf-8") == foreign


@pytest.mark.contract("SKL-16")
def test_skl16_coverage_id_collision(kb, logs, tmp_path, capsys):
    for name in ("first", "second"):
        write(
            tmp_path / "skills" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: про другое\n---\n",
        )
    logs.claude("s1", [claude_user("напишу eval агенту")])
    module = load_module()
    module.coverage_id = lambda kind, path: f"{kind}-000000000000"
    code = module.main(in_process_args(kb, logs, tmp_path))
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err.strip()
    assert not (kb / "skills" / "доказательства.json").exists()


@pytest.mark.contract("SKL-9")
def test_skl9_redacts_escaped_and_multiline_quotes(kb, logs, evidence):
    turns = [
        claude_user('напишу eval агенту {"password":"first\\" ХВОСТОДИН"} конец'),
        claude_user("напишу eval агенту token = 'abc\\' ХВОСТДВА' конец"),
        claude_user('напишу eval агенту secret: "строка\nХВОСТТРИ" конец'),
        claude_user('напишу eval агенту api_key="незакрытая\nХВОСТЧЕТЫРЕ'),
    ]
    logs.claude("s1", turns)
    assert evidence().returncode == 0
    session_id = candidate(kb)["сессии"][0]["id"]
    res = evidence("--показать", session_id)
    assert res.returncode == 0, res.stderr
    for leak in ("first", "ХВОСТОДИН", "abc", "ХВОСТДВА", "строка", "ХВОСТТРИ", "ХВОСТЧЕТЫРЕ"):
        assert leak not in res.stdout, leak
    assert res.stdout.count("[скрыто]") >= 4
    assert res.stdout.count("конец") == 3


def system_link_to_shared_dir():
    """Ссылка root вне домашней папки, ведущая в общую записываемую папку (`/var/lock`)."""
    from pathlib import Path

    link = Path("/var/lock")
    if not link.is_symlink() or link.lstat().st_uid != 0:
        return None
    target = link.resolve()
    if not os.access(target, os.W_OK) or Path.home().resolve() in target.parents:
        return None
    return link


@pytest.mark.contract("SKL-11")
def test_skl11_root_link_outside_home_rejected(kb, logs, run, tmp_path):
    link = system_link_to_shared_dir()
    if link is None:
        pytest.skip("нет ссылки root на общую записываемую папку")
    shared = link.resolve() / f"video-kb-test-{os.getpid()}-{tmp_path.name}"
    shared.mkdir()
    logs.claude("s1", [claude_user("напишу eval агенту")])
    try:
        args = in_process_args(kb, logs, tmp_path)
        args[-1] = str(link / shared.name / "cache")
        res = run("skill_evidence", *args)
        assert res.returncode == 2, res.stdout
        assert "символическая ссылка" in res.stderr
        assert list(shared.iterdir()) == []
    finally:
        for folder in sorted(shared.rglob("*"), reverse=True):
            folder.unlink() if folder.is_file() else folder.rmdir()
        shared.rmdir()


@pytest.mark.contract("SKL-11")
def test_skl11_links_allowed_only_up_to_home(kb, logs, run, tmp_path):
    real_home = tmp_path / "disk" / "someone"
    real_home.mkdir(parents=True)
    home = tmp_path / "home"
    home.symlink_to(real_home)
    logs.claude("s1", [claude_user("напишу eval агенту")])
    args = in_process_args(kb, logs, tmp_path)
    args[-1] = str(home / ".cache" / "video-kb")
    res = run("skill_evidence", *args, env={"HOME": str(home)})
    assert res.returncode == 0, res.stderr
    assert (cache_dir(real_home / ".cache" / "video-kb", kb) / "sessions.json").is_file()
    victim = tmp_path / "victim"
    victim.mkdir()
    (real_home / "via").symlink_to(victim)
    args[-1] = str(home / "via" / "cache")
    res = run("skill_evidence", *args, env={"HOME": str(home)})
    assert res.returncode == 2
    assert list(victim.iterdir()) == []


@pytest.mark.contract("SKL-17")
def test_skl17_hard_links_untouched(kb, logs, evidence, tmp_path):
    victim = write(tmp_path / "victim.md", "не трогать\n")
    os.link(victim, kb / "skills" / "доказательства.md")
    folder = cache_dir(tmp_path / "cache", kb)
    own = json.dumps({"база": str(kb.resolve()), "сессии": {}, "покрытие": {}}) + "\n"
    shared = write(tmp_path / "shared.json", own)
    shared.chmod(0o644)
    folder.mkdir(parents=True)
    os.link(shared, folder / "sessions.json")
    logs.claude("s1", [claude_user("напишу eval агенту")])
    res = evidence()
    assert res.returncode == 0, res.stderr
    assert victim.read_text(encoding="utf-8") == "не трогать\n"
    assert shared.read_text(encoding="utf-8") == own
    assert shared.stat().st_mode & 0o777 == 0o644
    assert "| eval-агента | 1 |" in (kb / "skills" / "доказательства.md").read_text(
        encoding="utf-8"
    )
    cache = folder / "sessions.json"
    assert cache.stat().st_mode & 0o777 == 0o600
    assert json.loads(cache.read_text(encoding="utf-8"))["сессии"]
