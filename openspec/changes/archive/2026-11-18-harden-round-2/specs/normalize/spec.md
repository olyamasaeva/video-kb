## ADDED Requirements

### Requirement: NRM-9 Вывод не идёт по ссылкам и пишется атомарно
Путь вывода SHALL проходиться от домашней папки (её путь разрешается один раз), если он лежит в ней, иначе от `/`. Если `--out`, `--report` или папка ниже этого начала — символическая ссылка, кто бы ей ни владел, `normalize.py` MUST вернуть код 2 с путём в stderr, не записав ни одного файла. Каждый файл вывода SHALL писаться во временный файл в той же папке и заменяться через `os.replace`; прежний файл MUST NOT меняться на месте.

#### Scenario: NRM-9 файл вывода — ссылка
- **WHEN** `--out` — ссылка на чужой файл; в другом прогоне `--report` — ссылка на чужой файл
- **THEN** код 2, чужие файлы не изменились, ни `--out`, ни `--report` не записаны
- Тест: `tests/test_normalize.py::test_nrm9_symlinked_output_rejected`

#### Scenario: NRM-9 папка вывода — ссылка
- **WHEN** папка `--out` — ссылка на чужую папку
- **THEN** код 2, в чужой папке нет файлов
- Тест: `tests/test_normalize.py::test_nrm9_symlinked_parent_rejected`

#### Scenario: NRM-9 жёсткая ссылка не обрезается
- **WHEN** `--out` — жёсткая ссылка на чужой файл
- **THEN** код 0, `--out` содержит результат, чужой файл не изменился
- Тест: `tests/test_normalize.py::test_nrm9_atomic_replace`

#### Scenario: NRM-9 ссылка root вне домашней папки
- **WHEN** `--out /var/lock/<папка>/L01.md`, где `/var/lock` — ссылка root на общую записываемую `/run/lock`
- **THEN** код 2, в stderr «символическая ссылка», в общей папке нет файлов
- Тест: `tests/test_normalize.py::test_nrm9_root_link_outside_home_rejected`

#### Scenario: NRM-9 ссылки только до домашней папки
- **WHEN** `HOME` — ссылка на настоящую домашнюю папку и `--out $HOME/kb/L01.md`; в другом прогоне `--out $HOME/kb/via/L01.md`, где `via` — ссылка на чужую папку
- **THEN** первый прогон — код 0, файл в настоящей домашней папке; второй — код 2, в чужой папке нет файлов
- Тест: `tests/test_normalize.py::test_nrm9_links_allowed_only_up_to_home`
