# token-optimization-skill

A Claude Code skill, packaged as a plugin, that makes cost the objective for each completed task. Correctness and safety are constraints, not competing goals. It collects the practices used to build [uniwrt](https://github.com/robertzas/uniwrt) with Claude Code on Opus 5.5.

- **Cost model first.** Every request re-sends the whole context. Cached context costs 0.025–0.1× fresh input on every request, new context costs 1.25–2× once, and output costs 5×. The rules follow from that.
- **Session rules.** Load docs progressively, locate before reading, run quiet commands, batch tool calls, don't re-read, edit rather than rewrite, look facts up once, decide once.
- **Prompt-cache-aware checkpoints.** A clear-or-keep test: clear when unused context × requests ahead > (write ÷ read price) × reload. It comes with a calculator, handles a cold cache, and produces ready-made checkpoint lines.
- **Measure and audit.** A per-WP cost ledger tracks dollars per completed task; `cost_report.py` prints median, p75, trend and outliers; `audit_transcript.py` shows the files read most, re-reads and the cache split; `lint_context.py` enforces entry-file, STATUS, section-size, dead-link and duplicate-prose budgets in CI; `/usage` shows cache hit rate, miss causes and per-behavior recommendations; `--max-budget-usd` caps a session; the cost model documents the cache mechanics that bite (20-block lookback, minimum cacheable length, invalidation triggers).
- **Enforced, not just advised.** One `prices.json` drives the calculator and the generated price table, and a `PreToolUse` guard denies whole-file reads of large files unless a line range is requested.
- **Repo setup.** A guide and templates for a short AGENTS.md, a STATUS.md handoff, a roadmap read one section at a time, a decision index, a doc map, module contracts and a generated code map that also indexes each doc's sections. A one-call start script makes the reload after a clear cheap.

Once installed, the skill costs about 80 tokens per session (its listing entry) and about 1.7k tokens when invoked (SKILL.md is ~6.8k characters). References load only on demand.

## Install

As a plugin (recommended, because it receives updates):

```bash
claude plugin marketplace add robertzas/token-optimization-skill
claude plugin install token-optimization@token-optimization-skill
```

Inside a session, run `/plugin marketplace add robertzas/token-optimization-skill`, then `/plugin install token-optimization@token-optimization-skill`.

As a personal skill, without the plugin:

```bash
git clone https://github.com/robertzas/token-optimization-skill
cp -r token-optimization-skill/skills/token-optimization ~/.claude/skills/
```

## Use

Claude loads the skill when a task matches its description:
- you ask to save tokens or cost
- the context has grown long
- a task or work package has just finished
- you're choosing between `/clear`, `/compact` and carrying on
- you're setting up or auditing a repo for agent work

To load it explicitly, run `/token-optimization:token-optimization` (plugin) or `/token-optimization` (personal skill).

Examples:
- "Set this repo up for token-efficient agent work." Claude adapts the templates (AGENTS.md, CLAUDE.md, STATUS.md, DECISIONS.md, ROADMAP.md, CHECKPOINTS.md, COST.md) and generates a code map.
- "Audit this repo for token waste." Claude reports a table of findings, fixes and their rough impact.
- "Should I clear now?" Claude applies the clear-or-keep test and ends with a checkpoint line.

### Scripts (Python 3.10+, standard library only)

```bash
# Clear or keep? Uses opus-5.5 prices by default; see --help for other models, --ttl 5m and --cold.
python3 skills/token-optimization/scripts/clear_or_keep.py --unused 60k --requests 100
#   Verdict: /clear, saving ~250k input-token equivalents ($1.00)
#   ✅ Checkpoint — /clear recommended (~60k unused, ~100 requests ahead; saves ~$1.00). Next: <task>. ...

# Measure the reload from the real files and add the session's measured cost
python3 skills/token-optimization/scripts/clear_or_keep.py --unused 60k --requests 100 \
  --measure docs/STATUS.md docs/ROADMAP.md:M3 --session '61 requests, 58% cached, $1.84'

# Code map: file, size, token estimate, header summary and Markdown sections
python3 skills/token-optimization/scripts/gen_map.py --out docs/MAP.md
python3 skills/token-optimization/scripts/gen_map.py --out docs/MAP.md --check   # in CI: exit 1 if stale

# One call to re-orient: STATUS.md, the current roadmap section and the doc map
python3 skills/token-optimization/scripts/start.py

# Context lint: entry budget, STATUS length, dead paths, links, section size, stale map
python3 skills/token-optimization/scripts/lint_context.py --root . --strict

# Ledger trend, with a CI budget
python3 skills/token-optimization/scripts/cost_report.py --path docs/COST.md --max-median 2.50

# One session's leaks: cache split, top files, re-reads, largest turn
python3 skills/token-optimization/scripts/audit_transcript.py session.jsonl

# Prices: edit prices.json, regenerate the table, verify in CI
python3 skills/token-optimization/scripts/prices.py --doc
python3 skills/token-optimization/scripts/prices.py --check
```

## What's inside

```
.claude-plugin/              plugin.json and marketplace.json (this repo is both)
skills/token-optimization/
  SKILL.md                   session rules, the clear-or-keep checkpoint test, links to the references
  references/                cost-model.md · reading-playbook.md · prompt-patterns.md · repo-setup.md
  templates/                 AGENTS, CLAUDE, CHECKPOINTS, COST, STATUS, DECISIONS and ROADMAP (*.template.md), settings.template.json
  scripts/                   clear_or_keep.py · gen_map.py · start.py · lint_context.py · cost_report.py · audit_transcript.py · prices.py · guard_read.py
tests/                       unit tests for the scripts
```

The skill follows its own advice on progressive disclosure:
- Only its description is always in context.
- `SKILL.md` loads when the skill fires.
- Reference files load only when a task needs them.
- Scripts run without being read.
- `tests/test_budgets.py` fails CI when any of those files exceeds its token budget, so the skill cannot quietly grow.

The templates are named `*.template.md` so that Claude Code never loads them as live `CLAUDE.md` or `AGENTS.md` instructions.

## Keeping prices current

Prices live in `skills/token-optimization/scripts/prices.json`, the single source for the calculator and the table. Checked 2026-10-22 against the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing).
1. Edit `prices.json`.
2. Run `python3 skills/token-optimization/scripts/prices.py --doc`.
3. Bump `version` in `.claude-plugin/plugin.json`, so installed copies update.

CI runs `prices.py --check`; a stale table fails the build.

## Development

```bash
python3 -m unittest discover -s tests -q
python3 -m compileall -q skills/token-optimization/scripts tests
python3 skills/token-optimization/scripts/prices.py --check
claude plugin validate . --strict
```

CI runs the tests on Python 3.10 and the latest 3.x.

## License

Licensed under either the [Apache License 2.0](LICENSE-APACHE) or the [MIT license](LICENSE-MIT), at your option.
