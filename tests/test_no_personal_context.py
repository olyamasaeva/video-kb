"""Сторож приватности — capability publication (PUB-).

Публичный тест ищет только общие маркеры личного контекста: домашние пути с именем
пользователя, адреса e-mail, id чатов. Личные строки автора (имя, названия его баз и
чекаутов) в репозитории не лежат: их список — в неотслеживаемом файле, а проверяет его
локальный хук `private-denylist` (`hooks/denylist.py`, PUB-2…PUB-3). Примеры маркеров
ниже собираются склейкой, поэтому тест проверяет и сам себя.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MARKERS = {
    "домашний путь": re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/"),
    "e-mail": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "id чата": re.compile(r"\bthr_[a-z0-9]{8,}"),
}


def tracked_files():
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [ROOT / name for name in listed.split("\0") if name]


def markers_in(line):
    return [name for name, pattern in MARKERS.items() if pattern.search(line)]


@pytest.mark.contract("PUB-1")
def test_pub1_no_personal_context():
    found = []
    for path in tracked_files():
        if path.is_symlink() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            found += [f"{path.relative_to(ROOT)}:{lineno}: {m}" for m in markers_in(line)]
    assert not found, "личный контекст в отслеживаемых файлах:\n" + "\n".join(found)


@pytest.mark.contract("PUB-1")
def test_pub1_markers_on_synthetic_examples():
    personal = [
        "/ho" + "me/someone/x",
        "/Us" + "ers/someone/x",
        "someone" + "@" + "example.org",
        "th" + "r_abcd1234",
    ]
    neutral = ["~/kb/example-course", "/ho" + "me/", "th" + "r_x"]
    assert [line for line in personal if not markers_in(line)] == []
    assert [line for line in neutral if markers_in(line)] == []
