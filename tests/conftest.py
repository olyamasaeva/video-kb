"""Общие помощники контрактных тестов: скрипты скилла запускаются как подпроцессы.

Скрипты зовутся по пути, как их зовёт агент (`python3 scripts/<имя>.py …`), поэтому
тест видит то же, что агент: stdout, stderr, код возврата и записанные файлы.
Все входы синтетические и создаются в `tmp_path`.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def run_script(name, *args, cwd=None, env=None):
    """Запустить `scripts/<name>.py` с аргументами и вернуть CompletedProcess.

    `env` дополняет окружение текущего процесса (например, другой `HOME`).
    """
    return subprocess.run(
        [sys.executable, str(SCRIPTS / f"{name}.py"), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        env={**os.environ, **env} if env else None,
        check=False,
    )


def write(path, text):
    """Записать текст в файл, создав каталоги."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def run():
    return run_script


def iso_days_ago(days):
    """Метка времени журнала `days` дней назад в формате ISO с `Z`."""
    from datetime import datetime, timedelta, timezone

    moment = datetime.now(timezone.utc) - timedelta(days=days)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def jsonl(path, records):
    """Записать записи журнала построчно в JSON."""
    import json

    return write(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def claude_user(text, days=1, cwd="/work/proj", **extra):
    """Реплика пользователя Claude Code; `text` — строка или список частей content."""
    return {
        "type": "user",
        "isSidechain": False,
        "message": {"role": "user", "content": text},
        "timestamp": iso_days_ago(days),
        "cwd": cwd,
        **extra,
    }


def claude_assistant(text, days=1):
    """Ответ ассистента Claude Code с текстом."""
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        "timestamp": iso_days_ago(days),
    }


def claude_tool_result(text, days=1):
    """Вывод инструмента: запись `type: user` с частью `tool_result`."""
    part = {"type": "tool_result", "tool_use_id": "t1", "content": text}
    return claude_user([part], days=days)


def codex_records(cwd, replies, days=1, agent=()):
    """Журнал Codex: `session_meta` с cwd, реплики пользователя и ответы агента."""
    records = [{"timestamp": iso_days_ago(days), "type": "session_meta", "payload": {"cwd": cwd}}]
    for text in replies:
        payload = {"type": "user_message", "message": text}
        records.append({"timestamp": iso_days_ago(days), "type": "event_msg", "payload": payload})
    for text in agent:
        payload = {"type": "agent_message", "message": text}
        records.append({"timestamp": iso_days_ago(days), "type": "event_msg", "payload": payload})
    return records


@pytest.fixture
def logs(tmp_path):
    """Пустые папки журналов обоих движков во `tmp_path` и функции наполнения."""
    claude_dir = tmp_path / "logs" / "claude"
    codex_dir = tmp_path / "logs" / "codex"
    claude_dir.mkdir(parents=True)
    codex_dir.mkdir(parents=True)

    class Logs:
        claude_root = claude_dir
        codex_root = codex_dir

        @staticmethod
        def claude(session, records, project="-work-proj"):
            return jsonl(claude_dir / project / f"{session}.jsonl", records)

        @staticmethod
        def codex(session, records, day="2026/11/01"):
            return jsonl(codex_dir / day / f"rollout-{session}.jsonl", records)

    return Logs
