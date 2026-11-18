# Стек и домен — video-kb

## Стек

| Слой | Чем |
|---|---|
| окружение и зависимости | uv (`pyproject.toml` + `uv.lock`); рантайм — только stdlib Python ≥3.10 |
| конфиг | нет: аргументы командной строки скриптов, правила — TSV в базе (`notes/не-код.md`) |
| данные | нет своих; DVC не нужен (`notes/не-код.md`) |
| логирование прогонов | нет; итог — отчёты нормализации и verify в самой базе |
| проверки | pytest: контрактные тесты + мета-тест OpenSpec; pre-commit: ruff, ruff-format, 500 КБ, секреты, ноутбуки, без комментариев, repo-shape |
| спеки | OpenSpec 2.0 (`openspec/`), скиллы `openspec-*` для claude и codex в `.agents/skills/` |
| документация | mkdocs + material + mkdocstrings по докстрингам `scripts/` |

## Домен

- **json3** — формат автосубтитров YouTube: поток событий `tStartMs` + `segs[].utf8`.
- **Блок** — кусок транскрипта под заголовком `## [HH:MM:SS](https://youtu.be/<id>?t=N)`;
  адрес цитаты — блок, где она стоит.
- **`.raw.md` / `.md`** — сырой и нормализованный транскрипт лекции `<L>` (L01, L02…).
- **Правило нормализации** — строка TSV `canonical⇥pattern⇥replacement⇥note`;
  `??` в замене — метка `⟦?: …⟧` вместо замены.
- **Карточка практики** — `practices/<тема>/<слаг>.md`: frontmatter (`id`, `практика`,
  `lecture`, `теги`, `уверенность`) и разделы Когда / Почему / Как / Границы / Источник.
- **MISS / SHORT / ADDR** — вердикты `check_quotes.py`: нет цитаты, короткая без
  совпадения, ссылка не на тот блок.

## Внешние зависимости

- `yt-dlp` — скачать субтитры json3; `pdftotext` (poppler-utils) — текст слайдов.
- `~/.local/bin/openspec` — CLI OpenSpec для `validate` и `archive`.
- `~/.claude/skills/repo-shape/scripts/audit_repo.py` — локальный хук формы репозитория
  автора; в публичный снимок не входит.
- `~/.config/video-kb/denylist.txt` — личный список строк для хука `private-denylist`
  (`hooks/denylist.py`); без файла хук падает с кодом 2. В публичный снимок хук не входит.
