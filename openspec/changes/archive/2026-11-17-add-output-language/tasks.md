# Tasks

## 1. Тесты (красные)

- [x] 1.1 `test_ver5_english_card`, `test_ver7_unknown_language`, `test_ver7_broken_config` с метками; проверка — падают на текущем `verify_kb.py`, `test_ver5_card_format` зелёный

## 2. verify_kb.py

- [x] 2.1 Чтение `video-kb.json`, ошибки настройки; проверка — VER-7 зелёные
- [x] 2.2 Схемы карточек `ru`/`en`; проверка — VER-5 оба сценария зелёные

## 3. SKILL.md и README

- [x] 3.1 `init`: вопрос о языке базы, запись `video-kb.json`; правило «всё, что пишет агент, — на языке базы»; шаблон карточки `en` рядом с `ru`; проверка — grep: раздел init упоминает `video-kb.json`, шаблон `en` содержит все пять английских разделов
- [x] 3.2 README: строка про язык базы

## 4. Приёмка

- [x] 4.1 `uv run pytest` зелёный, `openspec validate add-output-language --strict`; `verify_kb.py` на реальной русской базе без `video-kb.json` даёт то же число ошибок карточек, что до изменения

## Workflow follow-up

- После 4.1 — архив.
