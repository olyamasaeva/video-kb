"""Контракт `hooks/denylist.py` — capability publication (PUB-2…PUB-3).

Хук ищет строки личного списка автора в отслеживаемых файлах. Список и репозиторий
здесь синтетические и создаются в `tmp_path`.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import write

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "denylist.py"


def git_repo(folder, tracked, untracked=()):
    """Git-репозиторий в `folder`: файлы `tracked` в индексе, `untracked` — нет."""
    subprocess.run(["git", "init", "-q", str(folder)], check=True)
    for name, text in tracked.items():
        write(folder / name, text)
    for name, text in untracked:
        write(folder / name, text)
    subprocess.run(["git", "add", *tracked], cwd=folder, check=True)
    return folder


def denylist(folder, list_path):
    return subprocess.run(
        [sys.executable, str(HOOK), str(list_path)],
        cwd=folder,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


@pytest.mark.contract("PUB-2")
def test_pub2_finds_without_echo(tmp_path):
    repo = git_repo(
        tmp_path / "repo",
        {"a.md": "первая\nтут секретик есть\n", "b.md": "old_ACME_corp\n"},
        untracked=[("c.md", "Секретик\n")],
    )
    entries = write(tmp_path / "list.txt", "# личное\nСекретик\nacme_\n")
    res = denylist(repo, entries)
    assert res.returncode == 1
    assert res.stdout.splitlines() == ["a.md:2", "b.md:1"]
    output = (res.stdout + res.stderr).casefold()
    assert "секретик" not in output and "acme_" not in output


@pytest.mark.contract("PUB-2")
def test_pub2_word_boundaries(tmp_path):
    repo = git_repo(tmp_path / "repo", {"a.md": "лира и Пальмира, иранский\n"})
    res = denylist(repo, write(tmp_path / "list.txt", "Ира\n"))
    assert res.returncode == 0, res.stdout + res.stderr
    assert res.stdout == ""


@pytest.mark.contract("PUB-3")
def test_pub3_missing_or_empty_list_fails(tmp_path):
    repo = git_repo(tmp_path / "repo", {"a.md": "текст\n"})
    for entries in (tmp_path / "нет.txt", write(tmp_path / "empty.txt", "# только\n\n")):
        res = denylist(repo, entries)
        assert res.returncode == 2
        assert str(entries) in res.stderr
        assert res.stdout == ""
