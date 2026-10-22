# token-optimization-skill

A Claude Code skill, packaged as a plugin, that cuts the tokens and cost of each completed task without trading away quality. It collects the practices used to build [uniwrt](https://github.com/robertzas/uniwrt) with Claude Code on Opus 5.5.

- **Cost model first.** Every request re-sends the whole context. Cached context costs 0.025–0.1× fresh input on every request, new context costs 1.25–2× once, and output costs 5×. The rules follow from that.
- **Session rules.** Load docs progressively, locate before reading, run quiet commands, batch tool calls, don't re-read, edit rather than rewrite, look facts up once, decide once.
- **Prompt-cache-aware checkpoints.** A clear-or-keep test: clear when unused context × requests ahead > (write ÷ read price) × reload. It comes with a calculator, handles a cold cache, and produces ready-made checkpoint lines.
- **Repo setup.** A guide and templates for a short AGENTS.md, a STATUS.md handoff, a roadmap read one section at a time, a decision index, a doc map, module contracts and a generated code map.

Once installed, the skill costs about 150 tokens per session (its listing entry) and about 1.4k tokens when it's invoked, as measured by `claude plugin details`.

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
- "Set this repo up for token-efficient agent work." Claude adapts the templates (AGENTS.md, CLAUDE.md, STATUS.md, DECISIONS.md, ROADMAP.md) and generates a code map.
- "Audit this repo for token waste." Claude reports a table of findings, fixes and their rough impact.
- "Should I clear now?" Claude applies the clear-or-keep test and ends with a checkpoint line.

### Scripts (Python 3.10+, standard library only)

```bash
# Clear or keep? Uses opus-5.5 prices by default; see --help for other models, --ttl 5m and --cold.
python3 skills/token-optimization/scripts/clear_or_keep.py --unused 60k --reload 25k --requests 100
#   Verdict: /clear, saving ~250k input-token equivalents ($1.00)
#   ✅ Checkpoint — /clear recommended (~60k unused, ~100 requests ahead; saves ~$1.00). Next: <task>. ...

# Code map: each file with its size and the summary from its header comment
python3 skills/token-optimization/scripts/gen_map.py --out docs/MAP.md
python3 skills/token-optimization/scripts/gen_map.py --out docs/MAP.md --check   # in CI: exit 1 if stale
```

## What's inside

```
.claude-plugin/              plugin.json and marketplace.json (this repo is both)
skills/token-optimization/
  SKILL.md                   cost model, session rules, clear-or-keep checkpoints
  references/                cost-model.md · reading-playbook.md · repo-setup.md
  templates/                 AGENTS, CLAUDE, STATUS, DECISIONS and ROADMAP (*.template.md)
  scripts/                   clear_or_keep.py · gen_map.py
tests/                       unit tests for the scripts
```

The skill follows its own advice on progressive disclosure:
- Only its description is always in context.
- `SKILL.md` loads when the skill fires.
- Reference files load only when a task needs them.
- Scripts run without being read.

The templates are named `*.template.md` so that Claude Code never loads them as live `CLAUDE.md` or `AGENTS.md` instructions.

## Keeping prices current

Prices were checked on 2026-10-22 against the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing). When they change:
1. Update `references/cost-model.md`.
2. Update the ratio line and the threshold table in `SKILL.md`.
3. Update `MODELS` in `scripts/clear_or_keep.py`.
4. Bump `version` in `.claude-plugin/plugin.json`, so installed copies update.

## Development

```bash
python3 -m unittest discover -s tests -q
claude plugin validate . --strict
```

CI runs the tests on Python 3.10 and the latest 3.x.

## License

Licensed under either the [Apache License 2.0](LICENSE-APACHE) or the [MIT license](LICENSE-MIT), at your option.
