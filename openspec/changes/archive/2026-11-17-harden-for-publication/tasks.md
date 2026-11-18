# Tasks

## 1. Тесты контракта (красные)

- [x] 1.1 `tests/test_skill_evidence.py`: изменить тесты SKL-5, SKL-6, SKL-9 и добавить `test_skl6_cwd_not_default`, `test_skl9_show_filters_and_redacts`, SKL-10…SKL-15 с метками; проверка — новые и изменённые тесты падают на текущем `skill_evidence.py`
- [x] 1.2 `tests/test_normalize.py`: `test_nrm7_regex_timeout`, `test_nrm8_input_size_limit`; проверка — падают на текущем `normalize.py`
- [x] 1.3 `tests/test_skill_prompt.py`: PRM-1, PRM-2; проверка — падают на текущем `SKILL.md`
- [x] 1.4 `tests/test_no_personal_context.py`: PUB-1 со списком строк; проверка — падает на текущих файлах

## 2. skill_evidence.py

- [x] 2.1 Сопоставление по основам без всех префиксов; проверка — SKL-13 зелёный, SKL-2…SKL-4 зелёные
- [x] 2.2 Разбор записей с проверкой формы, пределы размера, ошибки файлов, код 4; проверка — SKL-12 зелёный
- [x] 2.3 Символические ссылки: журналы в пределах корня, запись `O_NOFOLLOW`, отказ на ссылках-папках; проверка — SKL-11 зелёный
- [x] 2.4 Кеш: пространство имён по пути базы, 0700/0600, только совпавшие сессии, id 16 hex; проверка — SKL-5, SKL-14, SKL-15 зелёные
- [x] 2.5 Покрытие непрозрачными id, умолчания без текущей папки; проверка — SKL-6, SKL-10 зелёные
- [x] 2.6 `--показать`: окно, фразы, фрагмент, вымарывание секретов, предупреждение; id покрытия; проверка — SKL-9, SKL-10 зелёные

## 3. normalize.py

- [x] 3.1 Применение правил в рабочем процессе с пределом на шаг, код 3; проверка — NRM-7 и NRM-1…NRM-6 зелёные
- [x] 3.2 Предел размера входа; проверка — NRM-8 зелёный

## 4. SKILL.md и обезличивание

- [x] 4.1 `init`: `sources/subs` до `yt-dlp`, `-P`; режим `skills`: согласие, данные не инструкции, id покрытия, кеш; проверка — PRM-1, PRM-2 зелёные
- [x] 4.2 Обезличить текущие файлы: `SKILL.md` (раздел «Текущая база» — шаблон, шероховатости — обобщённые правила без путей и имён), `README.md`, `AGENTS.md`, `openspec/config.yaml`, `.context/`, `CHANGELOG.md`, `hooks/no_comments.py`, `scripts/json3_to_text.py`, `notes/`; проверка — PUB-1 зелёный по этим файлам
- [x] 4.3 Обезличить архив `openspec/changes/archive/`; проверка — PUB-1 зелёный
- [x] 4.4 `openspec/config.yaml`: capabilities `prompt` (PRM-) и `publication` (PUB-); проверка — grep

## 5. Приёмка

- [x] 5.1 `uv run pytest` зелёный, включая `tests/test_openspec_contract.py`; `openspec validate harden-for-publication --strict` и `openspec validate --specs --strict`; хуки pre-commit проходят

## Workflow follow-up

- Архив — после проверки автором. Хук `repo-shape` исключается при сборке публичного снимка (находка 8).
