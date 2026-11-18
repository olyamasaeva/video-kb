## MODIFIED Requirements

### Requirement: VER-5 Формат карточек практик
Каждый `practices/<тема>/**/*.md` SHALL иметь frontmatter между `---` с полями схемы языка базы (VER-7) и разделы этой схемы в теле; `id` SHALL быть `<папка>/<имя файла без .md>`. Схема `ru`: поля `id`, `практика`, `lecture`, `теги`, `уверенность` ∈ {`высокая`, `средняя`, `низкая`}, разделы `**Когда.**`, `**Почему.**`, `**Как.**`, `**Границы.**`, `**Источник.**`. Схема `en`: поля `id`, `practice`, `lecture`, `tags`, `confidence` ∈ {`high`, `medium`, `low`}, разделы `**When.**`, `**Why.**`, `**How.**`, `**Limits.**`, `**Source.**`. Нарушения SHALL печататься по одному на строку; файл без frontmatter даёт только `нет frontmatter`.

#### Scenario: VER-5 плохая карточка и карточка без frontmatter
- **WHEN** в `practices/ops/` хорошая карточка, карточка с `id: ops/other`, `уверенность: железная`, без полей `практика` и `теги` и с одним разделом, и файл без frontmatter
- **THEN** заголовок `## Карточки — 9 ошибок (карточек: ops 3)` и девять ошибок в порядке: поля, id, уверенность, разделы, `нет frontmatter`
- Тест: `tests/test_verify.py::test_ver5_card_format`

#### Scenario: VER-5 английская карточка в английской базе
- **WHEN** в базе `video-kb.json` с `"language": "en"` и карточка с полями `practice`, `tags`, `confidence: high` и английскими разделами
- **THEN** ошибок карточек 0; та же карточка в базе без `video-kb.json` даёт ошибки отсутствующих русских полей и разделов
- Тест: `tests/test_verify.py::test_ver5_english_card`

## ADDED Requirements

### Requirement: VER-7 Язык базы из video-kb.json
`verify_kb.py` SHALL читать язык базы из `<база>/video-kb.json`, поле `language`; без файла язык SHALL быть `ru`. Неизвестный язык или файл, который не разбирается как JSON-объект, MUST давать код 2 и сообщение в stderr с именем файла, без проверки базы.

#### Scenario: VER-7 неизвестный язык
- **WHEN** `video-kb.json` содержит `{"language": "de"}`
- **THEN** код 2, в stderr `video-kb.json` и `de`
- Тест: `tests/test_verify.py::test_ver7_unknown_language`

#### Scenario: VER-7 битый файл настройки
- **WHEN** `video-kb.json` содержит `не json`
- **THEN** код 2, в stderr `video-kb.json`
- Тест: `tests/test_verify.py::test_ver7_broken_config`
