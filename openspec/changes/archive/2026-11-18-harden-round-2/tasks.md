# Tasks

## 1. Тесты контракта (красные)

- [x] 1.1 `tests/test_no_personal_context.py`: PUB-1 на общих маркерах без исключения себя и `test_pub1_markers_on_synthetic_examples`; проверка — синтетический тест падает на текущем файле
- [x] 1.2 `tests/test_denylist.py`: PUB-2…PUB-4 на синтетическом списке и синтетическом git-репозитории в `tmp_path`; проверка — падают: `hooks/denylist.py` и хука нет
- [x] 1.3 `tests/test_skill_evidence.py`: `test_skl9_redacts_quoted_secrets`, `test_skl11_journal_swapped_after_check`, `test_skl11_symlinked_cache_ancestor_rejected`, `test_skl15_foreign_namespace_not_overwritten`, `test_skl16_coverage_id_collision`; проверка — падают на текущем `skill_evidence.py`
- [x] 1.4 `tests/test_normalize.py`: NRM-9; проверка — падают на текущем `normalize.py`
- [x] 1.5 `tests/test_skill_prompt.py`: `test_prm2_redaction_best_effort`, `test_prm3_course_material_untrusted`; проверка — падают на текущем `SKILL.md`

## 2. Личный список (A)

- [x] 2.1 `~/.config/video-kb/denylist.txt` (папка 0700, файл 0600): все личные строки прежнего списка теста; общие (`/home/`, `thr_`) — маркерами в публичном тесте
- [x] 2.2 `hooks/denylist.py`; проверка — PUB-2, PUB-3 зелёные
- [x] 2.3 Хук `private-denylist` в `.pre-commit-config.yaml` с комментарием про публичный снимок; проверка — `test_pub4_hook_configured`, `pre-commit run private-denylist --all-files`
- [x] 2.4 Публичный тест без личных строк; проверка — PUB-1 зелёный, `git grep -F -f ~/.config/video-kb/denylist.txt` пусто
- [x] 2.5 `AGENTS.md`, `README.md`, `openspec/config.yaml`, `CHANGELOG.md`: где теперь личный список; проверка — PUB-1…PUB-4 зелёные

## 3. skill_evidence.py (B, C, F)

- [x] 3.1 Вымарывание ключей и значений в кавычках; проверка — SKL-9 зелёный
- [x] 3.2 Обход пути записи по дескрипторам папок без ссылок; проверка — SKL-11 и SKL-14 зелёные
- [x] 3.3 Открытие журнала с `O_NOFOLLOW` и проверка после открытия; проверка — SKL-11, SKL-12 зелёные
- [x] 3.4 Проверка владельца `sessions.json` перед записью; проверка — SKL-15 зелёный
- [x] 3.5 Регистрация id покрытия с проверкой совпадений; проверка — SKL-16, SKL-6, SKL-10 зелёные

## 4. normalize.py (D)

- [x] 4.1 Проверка путей вывода и атомарная запись; проверка — NRM-9 и NRM-1…NRM-8 зелёные

## 5. SKILL.md (B, E)

- [x] 5.1 Раздел «Недоверенный материал», запрет переносить инструкции дословно, вымарывание «по возможности, не гарантия»; проверка — PRM-2, PRM-3 зелёные

## 6. Приёмка

- [x] 6.1 `uv run pytest` зелёный, включая `tests/test_openspec_contract.py`; `openspec validate harden-round-2 --strict`, `openspec validate --specs --strict`; `pre-commit run --all-files` проходит

## 7. Третья проверка (H–K)

- [x] 7.1 Красные тесты: `test_nrm9_root_link_outside_home_rejected`, `test_nrm9_links_allowed_only_up_to_home`, `test_skl11_root_link_outside_home_rejected`, `test_skl11_links_allowed_only_up_to_home`, `test_skl17_hard_links_untouched`, `test_skl9_redacts_escaped_and_multiline_quotes`, `test_prm4_templates_keep_trust_boundary`, `test_path_walk_same_in_both_scripts`; проверка — падают на a3df444
- [x] 7.2 Доверенное начало пути — домашняя папка, исключение «ссылка root» снято, `trusted_start`/`enter`/`open_dir` одинаковы в обоих скриптах; проверка — SKL-11, NRM-9 и сверка копий зелёные
- [x] 7.3 `skill_evidence.py` пишет через временный файл и `os.replace`; проверка — SKL-17, SKL-14 зелёные
- [x] 7.4 Вымарывание: экранирование и перевод строки внутри кавычек; проверка — SKL-9 зелёный
- [x] 7.5 Правило о недоверенном материале в `templates/skill.md` и `templates/kb-pointer.md`; проверка — PRM-4, SKL-8 зелёные
- [x] 7.6 Приёмка: `uv run pytest`, `openspec validate harden-round-2 --strict`, `openspec validate --specs --strict`, `pre-commit run --all-files`, `hooks/denylist.py` по личному списку

## Workflow follow-up

- Архив — после проверки автором. Хуки `repo-shape` и `private-denylist` исключаются при сборке публичного снимка (находка G).
