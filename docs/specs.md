# Исполняемые спеки

Поведение скриптов описано в `openspec/specs/<capability>/spec.md`. Каждое требование
начинается с ID, у каждого сценария есть строка `- Тест:` с именем теста, а тест несёт
метку `@pytest.mark.contract("<ID>")`.

| Capability | Что | Префикс | Требований | Сценариев |
|---|---|---|---:|---:|
| subtitles | `json3_to_text.py` | SUB- | 7 | 8 |
| normalize | `normalize.py` | NRM- | 6 | 9 |
| locate | `locate.py` | LOC- | 6 | 7 |
| quotes | `check_quotes.py` | QUO- | 8 | 16 |
| verify | `verify_kb.py` | VER- | 7 | 13 |
| skills | `skill_evidence.py`, `skill_lint.py` | SKL- | 9 | 15 |

Изменение `harden-for-publication` (в работе) меняет SKL-5, SKL-6, SKL-9, добавляет
SKL-10…15 и NRM-7…8 и две новые capability: `prompt` (PRM-, проверяемые инварианты
`SKILL.md`) и `publication` (PUB-, в отслеживаемых файлах нет личного контекста).

`tests/test_openspec_contract.py` роняет сьют, если у требования нет теста, у метки нет
требования (с учётом дельт в `openspec/changes/`) или строка `- Тест:` называет тест
без метки этого требования.

## Похоже на дефекты — зафиксировано как есть

| ID | Что |
|---|---|
| SUB-3 | заголовок блока берёт время события, закрывшего предыдущий блок |
| NRM-6 | файл правил без правил — код 1 без сообщения |
| LOC-6 | пустая цитата — трейсбэк `IndexError` |
| QUO-4 | ссылка внутрь блока, но не на его начало, — ADDR |
| QUO-6 | транскрипты не по маске `L??.md` не загружаются, цитаты к ним молча проходят |

Чинить — изменением в `openspec/changes/` с MODIFIED-требованием: сначала тест, потом
код.

## Проверка

```bash
uv run pytest
~/.local/bin/openspec validate --specs --strict
```
