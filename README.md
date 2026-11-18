<p align="center"><b>English</b> · <a href="README.ru.md">Русский</a></p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/banner-dark.png">
    <img src="docs/img/banner-light.png" alt="video-kb: a YouTube course, turned into notes you can check" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/olyamasaeva/video-kb/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/olyamasaeva/video-kb/tests.yml?branch=main&style=flat-square&logo=github&logoColor=white&label=tests" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-e0679a?style=flat-square" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B%20%C2%B7%20stdlib%20only-e0679a?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+, standard library only">
  <img src="https://img.shields.io/badge/Claude%20Code-skill-e0679a?style=flat-square&logo=claude&logoColor=white" alt="Claude Code skill">
  <img src="https://img.shields.io/badge/Codex-skill-e0679a?style=flat-square" alt="Codex skill">
</p>

<p align="center"><a href="SKILL.md"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/btn-skill-dark.png"><img src="docs/img/btn-skill-light.png" height="34" alt="SKILL.md" /></picture></a>&nbsp;<a href="#quick-start"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/btn-start-dark.png"><img src="docs/img/btn-start-light.png" height="34" alt="Quick start" /></picture></a>&nbsp;<a href="#manual"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/btn-manual-dark.png"><img src="docs/img/btn-manual-light.png" height="34" alt="The manual" /></picture></a></p>

> [!NOTE]
> **Auto-subtitles are fixed by counted rules, not rewritten by a model, and every quote and timecode in the base is checked by scripts.** On the public Stanford CS329Z lectures: 93 practice cards and 4060 timecodes, 0 errors from `verify_kb.py`. New: `/video-kb skills <base>` tells you whether a base deserves agent skills at all.

<h3 align="center">You watched the course. Can you find the minute that said it?</h3>

<p align="center"><b>video-kb</b> is a skill for Claude Code and Codex that turns a YouTube course<br>into practice cards with honest limits, lecture summaries with clickable timecodes and a glossary.</p>

<p align="center"><a href="#quick-start">Quick start</a> · <a href="#why">Why</a> · <a href="#what-you-get">What you get</a> · <a href="#not-yet">What it doesn't do yet</a> · <a href="#faq">Questions</a> · <a href="#manual">The manual</a></p>

<a id="quick-start"></a>

## 🚀 Running in two minutes

```bash
git clone https://github.com/olyamasaeva/video-kb ~/.claude/skills/video-kb
```

For Codex, clone into `~/.agents/skills/video-kb` instead. You need Python 3.10+ (standard
library only), `yt-dlp` for subtitles and, for slides, `pdftotext` from poppler-utils.

Then ask the agent:

```text
/video-kb init ~/kb/<course>     # with a playlist link: language, subtitles, layout, scripts
/video-kb add L03                # one lecture end to end
/video-kb verify                 # red verify means the work is not done
```

or just "build a knowledge base from this YouTube course". The workflow the agent follows
is in [SKILL.md](SKILL.md).

<a id="why"></a>

## 💡 Why I built it

A model asked to "summarize the course" writes a confident retelling. It fixes the
subtitles silently, so a misheard term and a real correction look the same. Its quotes
drift: the words are close to what the lecturer said, the minute is somewhere nearby. After
a week you cannot tell what the lecture said from what the summary added.

I wanted a base where every claim has an address I can open, a minute of the video, a
slide or a file in the course repository, and where a wrong address is an error a script
finds, not something I notice on a reread.

So the model does the reading and the writing, and plain Python does the counting: which
subtitle rule fired how many times, whether a quote is verbatim, whether its timecode
points to the block where it stands. On an early lecture the check earned its place: after
a full read-through it still found four quotes attached to the wrong part of the lecture
and one paraphrase in quotation marks.

<a id="what-you-get"></a>

## 🎬 A course in, a base you can check out

Each lecture becomes a summary with a timecode on every claim, and the practices in it
become cards: when to use it, why, how, where it stops working, and the source. Quotes
stay verbatim in the language of the lecture; the base itself is written in Russian or
English.

<picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/shot-hero-dark.png"><img src="docs/img/shot-hero-light.png" width="100%" alt="A lecture summary with clickable timecodes next to the practice card extracted from it, Stanford CS329Z lecture 6" /></picture>

| | |
|---|---|
| 🃏 **Practice cards** | When, Why, How, Limits, Source. Limits are mandatory, with a confidence level. |
| ⏱️ **Timecodes** | Every claim links to the second of the video where it is said. |
| 🔧 **Subtitle rules** | TSV rules with a hit count per rule; ambiguous places are marked `??`, not guessed. |
| 📚 **Glossary** | One per course, each term with its addresses and cards. |
| ✅ **Verify** | Links, timecodes against transcripts, card format, verbatim quotes. Exit code 1 on any error. |
| 🧩 **Skills mode** | Checks your own sessions before turning cards into an agent skill. "The cards are enough" is a normal answer. |

<details>
<summary><b>See the rest of a real base</b></summary>

<table>
<tr>
<td width="50%" valign="top"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/shot-glossary-dark.png"><img src="docs/img/shot-glossary-light.png" width="100%" alt="Glossary" /></picture><br><b>Glossary</b> · <sub>Terms with timecodes and links to cards.</sub></td>
<td width="50%" valign="top"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/shot-normalization-dark.png"><img src="docs/img/shot-normalization-light.png" width="100%" alt="Normalization report" /></picture><br><b>Normalization report</b> · <sub>What the subtitles said and how many times each rule fired.</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/shot-verify-dark.png"><img src="docs/img/shot-verify-light.png" width="100%" alt="verify_kb.py and check_quotes.py output" /></picture><br><b>Verify</b> · <sub>134 files, 4060 timecodes, 93 cards, 0 errors.</sub></td>
<td width="50%" valign="top"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/img/shot-skills-dark.png"><img src="docs/img/shot-skills-light.png" width="100%" alt="Skills mode report" /></picture><br><b>Skills mode</b> · <sub>Phrase matches, then reading: none of the candidates needed a skill.</sub></td>
</tr>
</table>

<sub>All screenshots are from the base built on the public lectures of Stanford CS329Z, output language Russian. The skills report is condensed and has no session ids.</sub>

</details>

<a id="not-yet"></a>

## 🧭 What it doesn't do yet

- **It does not judge the cards.** Verify proves that every claim has a correct address,
  not that the right practices were extracted. Card quality is not measured.
- **YouTube subtitles only.** The input is `json3` subtitles from `yt-dlp`. There is no
  speech recognition of its own, so a video without subtitles is out of reach.
- **Two output languages.** A base is written in `ru` or `en`. The course language is
  independent: an English course can go into a Russian base and the other way round.
- **Slides only as text.** Slides come in through `pdftotext`; diagrams and images on
  slides are not read. Without `pdftotext` the skill works and says the slides are left
  out.
- **Skills mode skips huge logs.** A session log with a line longer than 1,000,000
  characters or a file over 256 MiB is not read, and the scan is reported as incomplete.

<a id="faq"></a>

## ❓ Questions people ask first

**Does it rewrite the subtitles with a model?**
No. The model proposes rules; `normalize.py` applies them and counts every hit. The raw
transcript stays next to the normalized one, so any replacement can be recounted or rolled
back.

**What happens when a quote is wrong?**
`check_quotes.py` fails if a «quote» is not verbatim in the transcript or its timecode is
more than one block away. `locate.py` computes the address of a new quote, so the agent
does not recall it from memory.

**Do I need the course slides or repository?**
No. They make the base better: a claim can then point to a slide or a file. Without them
the base relies on the video alone.

**Does it read my agent sessions?**
Only `/video-kb skills`, and only after you agree. The report keeps opaque ids, dates and
matched phrases, not message text or project paths. See [Security and privacy](#security-and-privacy).

**Does it need packages or a network at run time?**
The scripts use only the Python standard library. The network is needed for `yt-dlp` to
download subtitles.

<a id="manual"></a>

## 📖 The manual

### Example: one passage, two layers

From a base built on the public lectures of Stanford
[CS329Z Engineering AI Agents](https://cs329z.stanford.edu/), output language Russian.
Lecture 6, *AI Agent Design Patterns*, a fragment of the summary
(`lectures/L06-design-patterns.md`, section 2). Quotes stay verbatim in the language of
the lecture, each timecode opens the video at that second:

```markdown
**Prompt chaining.** Задачу раскладывают на последовательность вызовов; между ними может
стоять gate — «this is like an if-else sort of thing» [00:07:31](https://youtu.be/JC_pLC5EX_w?t=451).
В примере с письмом вместо одного промпта “извлеки события, выбери эмодзи, добавь в календарь” —
отдельные вызовы [00:07:31](https://youtu.be/JC_pLC5EX_w?t=451). Цена названа прямо: «you're
trading off latency for accuracy because two language model calls is going to likely be slower
than one» (исключение — два вызова без рассуждения против одного с рассуждением); паттерн
«especially useful when the task is complicated and can benefit from this decomposition», хотя
пример с календарём лектор сам называет не лучшим [00:08:32](https://youtu.be/JC_pLC5EX_w?t=512).
```

The practice card extracted from the same passage
(`practices/design-patterns/prompt-chaining-for-accuracy.md`):

```markdown
---
id: design-patterns/prompt-chaining-for-accuracy
практика: Сложную задачу для LLM разбивать на цепочку отдельных вызовов с проверками-gate между ними, сознательно платя задержкой за точность
lecture: L06
теги: [workflow, prompt-chaining, decomposition, latency]
уверенность: средняя
---

# Prompt chaining: менять задержку на точность

**Когда.** Задача в одном промпте делает несколько разных вещей (извлечь, выбрать, оформить), шаги известны заранее, и качество важнее времени ответа.

**Почему.** Вместо одного промпта “извлеки события из письма, выбери эмодзи, добавь в календарь” — отдельные вызовы; между ними может стоять gate — «this is like an if-else sort of thing» [00:07:31](https://youtu.be/JC_pLC5EX_w?t=451). Лектор прямо называет цену: «you're trading off latency for accuracy because two language model calls is going to likely be slower than one» (исключение — два вызова без рассуждения против одного с рассуждением), зато задачу проще разложить; паттерн «especially useful when the task is complicated and can benefit from this decomposition» [00:08:32](https://youtu.be/JC_pLC5EX_w?t=512). В реальных системах цепочка — один из кирпичей: в STORM тема → обзор → план идут цепочкой [00:18:14](https://youtu.be/JC_pLC5EX_w?t=1094).

**Как.**
1. Выписать шаги задачи; каждый, у которого свой вход и выход, — отдельный вызов со своим промптом.
2. Между шагами ставить программные gate: проверка формата или условия, ветвление, ранний выход.
3. Сравнить цепочку с одним промптом на своём наборе — по точности и по задержке.

**Границы.** Лектор сам признаёт: «maybe the calendar example isn't the best example of a complicated task» [00:08:32](https://youtu.be/JC_pLC5EX_w?t=512); для простых задач цепочка добавит только задержку и цену. Цифр в лекции нет. Цепочка годится, только когда шаги одинаковы для всех входов — иначе см. [routing](route-by-input-class.md) и [orchestrator-workers](orchestrator-workers-for-unknown-subtasks.md); общий выбор workflow против агента — [workflow, если шаги известны](workflow-before-agent.md). Ошибка раннего шага каскадом идёт дальше, поэтому gate и промежуточная оценка важнее, чем в одном вызове (вывод базы).

**Источник.** L06 [00:06:26](https://youtu.be/JC_pLC5EX_w?t=386)–[00:08:32](https://youtu.be/JC_pLC5EX_w?t=512); [конспект](../../lectures/L06-design-patterns.md), раздел 2.
```

### What you get

A base per course, in a folder you choose:

```text
practices/<topic>/   best-practice cards: When, Why, How, Limits, Source   ← the main layer
lectures/            one summary per lecture, timecodes on every claim
glossary/terms.md    one glossary per course
transcripts/         <L>.raw.md (never edited) and <L>.md (normalized)
normalization/       common.tsv, <L>.tsv and a report with counts per rule
README.md            course passport, video ↔ slides table, status per lecture
```

- **Subtitles fixed by rules.** `normalize.py` applies TSV rules (course-wide and
  per-lecture) and writes a report with the number of hits for each rule. Ambiguous
  places are marked `??` instead of guessed. The raw transcript stays next to the
  normalized one.
- **Cards with limits.** A card records where the practice does not work and what it
  costs, and a confidence level. If the lecturer did not state a rule and the base
  inferred it, the card says so.
- **Addresses everywhere.** A quote without a timecode, or a timecode that points to the
  wrong minute, is an error, not a style issue.

### Modes

- `/video-kb init <path>`: a new base for a course. Asks for the output language,
  downloads subtitles with `yt-dlp` into the base, creates the layout and copies the
  scripts.
- `/video-kb add <lecture>`: one lecture end to end: transcript, slides, normalization
  rules, summary, cards, glossary, README of the base, verification.
- `/video-kb verify`: `verify_kb.py` and `check_quotes.py` over the base. A red verify
  means the work is not done.
- `/video-kb finalize`: when the lectures are over, rerun all of them through the final
  `common.tsv`, reread the diff, verify.
- `/video-kb skills <base>`: decides whether the base deserves agent skills at all.
  Groups cards into candidates, looks for the situations in your own Claude Code and Codex
  sessions (with consent, see below), checks overlap with installed skills and rules, and
  gives a verdict per candidate. "The cards are enough" is a normal outcome. Builds only
  the skills you name.

### Output language

The base is written in `ru` or `en`, independent of the course language: an English
course can go into a Russian base and the other way round. The language is set in
`<base>/video-kb.json`, field `language`; without the file the base is Russian.
Summaries, cards, glossary and README are written in that language, quotes stay verbatim
in the language of the lecture, and `verify_kb.py` checks card fields and sections against
the schema of that language.

### Evaluation and validation

What is checked by scripts, not by reading:

- `verify_kb.py`: every relative link leads to an existing file; the label `[H:MM:SS]`
  matches `?t=N` and N falls into a real block of the transcript; every card has the
  required frontmatter fields, an `id` that matches its path, a confidence value from the
  vocabulary and all five sections. Exit code 1 on any error.
- `check_quotes.py`: every «quote» is verbatim in the normalized transcript (case,
  whitespace and inserted brackets ignored), and the nearest timecode points to the block
  where the quote stands, ±1 block. `locate.py` computes the address of a new quote
  instead of the agent recalling it.
- `skill_lint.py`: a generated skill has valid frontmatter and every card link resolves.

On the CS329Z base above (8 lectures, about 10 hours of video): 93 cards in 15 topics,
4060 timecodes checked against the transcripts, 131 files with links, **0 errors** from
`verify_kb.py` and no MISS or ADDR from `check_quotes.py`. The check earned its place on
an early lecture: after a full read-through it still found four quotes attached to the
wrong part of the lecture and one paraphrase in quotation marks.

The scripts themselves are specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec), as
requirements in `openspec/specs/` (subtitles, normalize, locate, quotes, verify,
skills, prompt, publication). Every requirement has an ID and a contract test marked
`@pytest.mark.contract("<ID>")`; `tests/test_openspec_contract.py` fails the suite if a
requirement has no test or a test points to no requirement. The tests run the scripts as
subprocesses on synthetic inputs.

```bash
uv sync
uv run pytest                              # contract and meta tests, also run by CI
openspec validate --specs --strict
```

What is not measured: the quality of the cards themselves. Verify proves that every claim
has a correct address, not that the right practices were extracted.

### Security and privacy

- **Course material is data, not instructions.** Subtitles, slides, the course repository
  and the cards derived from them are recorded as content with an address. A command the
  material suggests (install a package, run a script, go online, write outside the base)
  runs only after a separate "yes" from the user.
- **Session logs only with consent.** The `skills` mode reads your Claude Code and Codex
  session logs to find whether a situation really comes up. It explains what will be read
  and asks first; without consent the step is skipped and verdicts are marked as not
  confirmed. The report keeps session ids, dates and matched phrases, not message text or
  project paths; the id → log mapping lives in a private cache outside the base. Showing
  matched messages needs a second consent.
- **Secrets are redacted on a best-effort basis.** Keys and passwords in shown fragments
  are masked, but tokens of an unusual shape can survive, so the fragments go to the
  terminal only and are never written into the base.
- **Symbolic links.** A log that is a symlink, or resolves outside the log folder, is not
  read. Output paths are walked from the home folder, and a symlink anywhere below it
  stops the script with code 2 before anything is written. Files are written to a
  temporary file and replaced atomically.

### Layout

```text
SKILL.md                     the skill: modes, invariants, known rough edges
scripts/json3_to_text.py     YouTube json3 subtitles → raw transcript in timecoded blocks
scripts/normalize.py         TSV rules → normalized transcript and a report per rule
scripts/locate.py            verbatim quote → timecode of its block
scripts/check_quotes.py      every quote in the base: verbatim and address ±1 block
scripts/verify_kb.py         links, timecodes against transcripts, card format
scripts/skill_evidence.py    skills mode: matches in session logs, coverage by skills and rules
scripts/skill_lint.py        frontmatter and card links of a generated skill
templates/                   skill.md and kb-pointer.md for the skills mode
openspec/specs/              behaviour of the scripts, one requirement = one test
tests/                       contract tests
```

### License

MIT, see [LICENSE](LICENSE). The example above quotes the public lectures of Stanford
CS329Z; the repository contains no course material.
