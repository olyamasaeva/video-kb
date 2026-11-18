# verify Specification

## Purpose
Проверка базы знаний, собранной из видео: относительные ссылки, таймкоды цитат против транскриптов и формат карточек практик. Где: `scripts/verify_kb.py <корень базы> [--tolerance-sec 80] [--quiet]`.

## Requirements

### Requirement: VER-1 Относительные ссылки ведут в существующие файлы
Для каждого `.md` базы вне каталогов `transcripts`, `slides_text`, `normalization`, `scripts`, `.git` скрипт SHALL проверять markdown-ссылки `[…](цель)`: цель без `http:`, `https:`, `mailto:` и не начинающаяся с `#` SHALL после отбрасывания `#якоря` существовать относительно файла, иначе ошибка `<путь>:<строка>: битая ссылка -> <цель>`.

#### Scenario: VER-1 ссылка на несуществующий файл
- **WHEN** в `lectures/L01.md` ссылки `missing.md` и `../practices/ops/good.md#a`
- **THEN** одна ошибка `lectures/L01.md:1: битая ссылка -> missing.md`, код возврата 1
- Тест: `tests/test_verify.py::test_ver1_broken_relative_link`

#### Scenario: VER-1 внешние ссылки, якоря и папки-исходники
- **WHEN** в конспекте ссылки `https:`, `http:`, `mailto:` и `#якорь`, а битые ссылки лежат в `slides_text/`, `normalization/`, `scripts/`, `.git/`
- **THEN** код возврата 0, `## Ссылки — OK (проверено файлов: 2)`
- Тест: `tests/test_verify.py::test_ver1_external_links_anchors_and_source_dirs_skipped`

### Requirement: VER-2 Подпись таймкода сходится с ?t
Для ссылки `[H:MM:SS](https://youtu.be/<id>?t=N)` подпись в секундах SHALL отличаться от N не больше чем на 2 с, иначе ошибка `<путь>:<строка>: подпись H:MM:SS (<сек>s) не сходится с ?t=N`.

#### Scenario: VER-2 разница 2 с и 3 с
- **WHEN** ссылки `[0:00:02](…?t=0)` и `[0:01:00](…?t=63)`
- **THEN** одна ошибка — `подпись 0:01:00 (60s) не сходится с ?t=63`
- Тест: `tests/test_verify.py::test_ver2_label_must_match_seconds`

### Requirement: VER-3 ?t рядом с началом блока транскрипта
N SHALL отстоять от ближайшего начала блока транскрипта этого видео (по заголовкам `## [H:MM:SS](https://youtu.be/<id>?t=N)` во всех `transcripts/*.md`) не больше чем на `--tolerance-sec` (по умолчанию 80), иначе ошибка `?t=N (H:MM:SS) не попадает ни в один блок транскрипта — ближайший на <сек>s (разрыв <сек>s)`. Сравнивается расстояние до начала блока, а не попадание внутрь блока.

#### Scenario: VER-3 середина длинного блока
- **WHEN** блоки начинаются на 0 и 300 с, ссылка `?t=120`
- **THEN** ошибка `… не попадает ни в один блок транскрипта — ближайший на 0s (разрыв 120s)`, код возврата 1
- Тест: `tests/test_verify.py::test_ver3_seconds_must_be_near_block_start`

#### Scenario: VER-3 допуск расширен
- **WHEN** та же ссылка и `--tolerance-sec 120`
- **THEN** код возврата 0
- Тест: `tests/test_verify.py::test_ver3_tolerance_option`

### Requirement: VER-4 Видео без транскрипта — ошибка
Ссылка на видео, для которого нет ни одного заголовка блока в `transcripts/`, SHALL давать ошибку `<путь>:<строка>: нет нормализованного транскрипта для <id>`.

#### Scenario: VER-4 чужое видео
- **WHEN** в конспекте ссылка на `vid9`, транскрипт есть только для `vid1`
- **THEN** ошибка `lectures/L01.md:1: нет нормализованного транскрипта для vid9`
- Тест: `tests/test_verify.py::test_ver4_unknown_video`

### Requirement: VER-5 Формат карточек практик
Каждый `practices/<тема>/**/*.md` SHALL иметь frontmatter с полями `id`, `lecture` и тремя полями схемы языка базы (VER-7) и пять разделов схемы в теле; `id` SHALL быть `<папка>/<имя файла без .md>`. Схема `ru`: `практика`, `теги`, `уверенность` (`высокая`/`средняя`/`низкая`), разделы `**Когда.**`, `**Почему.**`, `**Как.**`, `**Границы.**`, `**Источник.**`; схема `en`: `practice`, `tags`, `confidence` (`high`/`medium`/`low`), разделы — английские. Нарушения SHALL печататься по одному на строку.

#### Scenario: VER-5 плохая карточка и карточка без frontmatter
- **WHEN** в `practices/ops/` хорошая карточка, карточка с `id: ops/other`, `уверенность: железная`, без полей `практика` и `теги` и с одним разделом, и файл без frontmatter
- **THEN** заголовок `## Карточки — 9 ошибок (карточек: ops 3)` и девять ошибок в порядке: поля, id, уверенность, разделы, `нет frontmatter`
- Тест: `tests/test_verify.py::test_ver5_card_format`

#### Scenario: VER-5 английская карточка в английской базе
- **WHEN** в базе `video-kb.json` с `"language": "en"` и карточка с полями `practice`, `tags`, `confidence: high` и разделами `**When.**`, `**Why.**`, `**How.**`, `**Limits.**`, `**Source.**`
- **THEN** ошибок карточек 0; та же карточка в базе без `video-kb.json` даёт ошибки отсутствующих русских полей и разделов
- Тест: `tests/test_verify.py::test_ver5_english_card`

### Requirement: VER-6 Отчёт и код возврата
Скрипт SHALL печатать по разделу на проверку — `## Ссылки`, `## Таймкоды`, `## Карточки` — как `— OK (<счётчик>)` или `— N ошибок (<счётчик>)` со списком ошибок `  - …`; с `--quiet` разделы без ошибок SHALL NOT печататься. Последняя строка — `итого ошибок: N`; код возврата 1, если N > 0, иначе 0. Несуществующий корень SHALL давать в stderr `нет такой папки: <абсолютный путь>` и код 1.

#### Scenario: VER-6 зелёная база
- **WHEN** в базе одна правильная карточка со ссылкой на существующий блок
- **THEN** stdout — три строки `— OK`, пустая строка и `итого ошибок: 0`, код возврата 0
- Тест: `tests/test_verify.py::test_ver6_green_report`

#### Scenario: VER-6 тихий режим
- **WHEN** одна битая ссылка и `--quiet`
- **THEN** печатается только раздел ссылок с ошибкой и `итого ошибок: 1`, код возврата 1
- Тест: `tests/test_verify.py::test_ver6_quiet_prints_only_errors`

#### Scenario: VER-6 нет корня
- **WHEN** корень базы не существует
- **THEN** stdout пуст, stderr — `нет такой папки: <путь>`, код возврата 1
- Тест: `tests/test_verify.py::test_ver6_missing_root`

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
