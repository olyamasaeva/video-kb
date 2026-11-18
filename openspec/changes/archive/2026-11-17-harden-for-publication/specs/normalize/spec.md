## ADDED Requirements

### Requirement: NRM-7 Предел времени на правило
Правила SHALL применяться в отдельном процессе. Если одно правило на одной строке работает дольше `--timeout-sec` (по умолчанию 10), `normalize.py` MUST остановить процесс, вернуть код 3 и напечатать в stderr файл и номер строки правила и предел; `--out` и `--report` MUST NOT записываться.

#### Scenario: NRM-7 катастрофический откат
- **WHEN** правило `(a+)+$` применяется к строке из 40 `a` и `!` с `--timeout-sec 1`
- **THEN** код 3 за время меньше 10 с, в stderr `rules.tsv:1` и `1 с`, файлов `--out` и `--report` нет
- Тест: `tests/test_normalize.py::test_nrm7_regex_timeout`

### Requirement: NRM-8 Предел размера входа
Вход больше 20 МиБ MUST давать код 3 и сообщение в stderr с именем файла и пределом до применения правил; `--out` MUST NOT записываться.

#### Scenario: NRM-8 слишком большой вход
- **WHEN** вход — 21 МиБ текста
- **THEN** код 3, в stderr имя входа и `20 МиБ`, файла `--out` нет
- Тест: `tests/test_normalize.py::test_nrm8_input_size_limit`
