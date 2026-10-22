---
name: token-optimization
description: Reduces tokens and cost per task in Claude Code sessions without losing quality. Covers progressive doc loading, quiet tool output, batching, prompt-cache-aware decisions on when to /clear or keep context, STATUS.md handoffs, and a repo setup (AGENTS.md, STATUS.md, DECISIONS.md, roadmap sections, code map) that keeps every session cheap. Use when asked to save tokens or cost, when the context grows long, at the end of a task or work package, when choosing between /clear, /compact and continuing, or when setting up or auditing a repo for agent work.
license: MIT OR Apache-2.0
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/clear_or_keep.py *)
---

# Token optimization

Goal: fewer tokens per *completed* task. Correctness, safety and UX come first; never trade them for tokens. A cheaper request that causes rework is not cheaper.

## Cost model

Every request (each tool round trip) re-sends the whole context. With prompt caching, relative to fresh input (1×):

| Tokens | Cost | When |
|---|---|---|
| Context already cached | 0.1× (0.05× Opus 5.5 and Sonnet 5.5, 0.025× Fable 5.1) | on every request |
| New context: tool output, replies, re-reads | 1.25× with a 5-minute TTL, 2× with a 1-hour TTL | once, then cached |
| Output, thinking included | 5× | once |
| All of it, after an idle gap longer than the TTL | the write price again | on the next request |

What follows:
- Whatever lands in context is paid at the write price, then again on every later request. Keep tool output small.
- Each round trip re-reads everything, so batch independent calls, more so as the context grows.
- A re-read is a new write. Use the copy already in context.
- Output is the most expensive token. Edit instead of rewriting files, keep replies tight, and don't re-derive settled facts.
- Carrying context is cheap and reloading it is not. Clear only when the test below says so.

Prices, derivations and what invalidates the cache: [references/cost-model.md](references/cost-model.md).

## Rules for every session

1. **Load progressively.** Entry file (AGENTS.md or CLAUDE.md, loaded automatically) → `STATUS.md` → the current task's roadmap section → only the docs that section names.
2. **Locate before reading.** Code map, then module contracts (header comments), then `grep -n`, then line ranges. For a long doc, run `grep -n '^## ' FILE` and read one section.
3. **Skip bulky and generated files:** lockfiles, generated code, build output, vendored data, and snapshots unless you are reviewing them.
4. **Run quiet commands:** summarized checks, failures-only test output, `gh run view --log-failed`. Cap output with `head`, `tail`, `cut -c1-200`, `--stat`, `--name-only` or `jq`. When a tool saves a large output to a file, grep that file instead of reading it.
5. **Batch** independent tool calls in one message.
6. **Don't re-read** what is in context and unchanged, including files you just wrote or edited.
7. **Write new files in one pass; change existing ones with targeted edits.**
8. **Look facts up once.** Fetch only what you need (an extraction prompt, the `.md` version of a docs page), record the result with its date and source (for example in DECISIONS.md), and cite the record afterwards.
9. **Decide once.** Offer 2–4 options with a recommended default, record the outcome once, and never reopen it without the owner.
10. **Subagents start cold.** Use one only when it keeps far more out of the main context than its own run costs, such as a sweeping search.

Command cookbook by ecosystem: [references/reading-playbook.md](references/reading-playbook.md).

## Checkpoints: clear or keep

Only the user can run `/clear`. At a natural boundary (the task is done, docs are updated, everything is committed and pushed), decide:

- **D** is the context the next work won't use. **R** is what it must load again after a clear: status, roadmap section, specs, code and re-orientation, typically 20–30k tokens. **c** is the number of requests ahead; a full work package takes 100 or more.
- Keeping costs read × D × c. Clearing costs write × R, once.
- **Clear when D × c > (write ÷ read) × R.** With a 1-hour TTL the ratio is 40 on Opus 5.5 and Sonnet 5.5, 80 on Fable 5.1 and 20 on most other models. Multiply by 0.625 for a 5-minute TTL.

| Work ahead (ratio 40, R ≈ 25k) | Clear when the unused context exceeds about |
|---|---|
| A follow-up (~10 requests) | 100k |
| A small task (~50 requests) | 20k |
| A full work package (100+ requests) | 10k |

For exact numbers, run `python3 ${CLAUDE_SKILL_DIR}/scripts/clear_or_keep.py --unused 60k --reload 25k --requests 100`. Add `--model`, `--ttl 5m`, `--cold` or `--next "<task>"` as needed. It prints the comparison and the checkpoint line.

- **Cold cache** (idle longer than the TTL): keeping re-writes the whole context, so clear unless most of it is still needed.
- **Quality outranks cost.** Keep when the next task depends on details the handoff can't carry. Clear when a long context starts to blur details.
- **Make the handoff durable before any clear:** rewrite `STATUS.md`, then commit and push.
- **Prefer `/clear` plus `STATUS.md` to `/compact`.** A compact summary is billed as output and nobody reviews it.
- **Switching model or fast mode re-writes the cache,** because caches are per model and per speed. Switch right after a `/clear`.
- **Mid-task,** apply the same test only when quality starts to suffer or the user will be away longer than the TTL.

When clearing pays off, stop and end the reply with:
`✅ Checkpoint — /clear recommended (<why>). Next: <task>. After clearing, say "continue".`

When keeping wins, carry on if the repo's directives allow it. Otherwise end with:
`✅ Checkpoint — keep context (<why>). Next: <task>. Say "continue" within <TTL>; after that, /clear first.`

## Set up or audit a repo

When asked to make a repo token-efficient, or when a repo has no agent docs, follow [references/repo-setup.md](references/repo-setup.md) and adapt the files in [templates/](templates/). Generate a code map with `python3 ${CLAUDE_SKILL_DIR}/scripts/gen_map.py --out docs/MAP.md`.
