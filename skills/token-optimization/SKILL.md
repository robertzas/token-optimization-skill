---
name: token-optimization
description: Cuts tokens and cost per task in Claude Code without losing quality - progressive loading, quiet tool output, batching, prompt-cache-aware /clear-or-keep checkpoints, STATUS.md handoffs, and a repo setup that keeps sessions cheap. Use when asked to save tokens or cost, when context grows long, at the end of a task, when choosing between /clear, /compact and continuing, or when setting up or auditing a repo for agent work.
license: MIT OR Apache-2.0
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/clear_or_keep.py *)
---

# Token optimization

Goal: fewer tokens per *completed* task. Correctness, safety and UX come first; rework is never cheaper.

Read only what the task needs:

| Task | Also read |
|---|---|
| Working rules, checkpoints | nothing: both are below |
| Exact prices, cache invalidation, /compact, subagent maths | [references/cost-model.md](references/cost-model.md) |
| Quiet commands per ecosystem | [references/reading-playbook.md](references/reading-playbook.md) |
| Set up or audit a repo | [references/repo-setup.md](references/repo-setup.md), then the [templates/](templates/) it names |

## Why

Every request (each tool round trip) re-sends the whole context. Relative to fresh input: cached context costs 0.025–0.1× on *every* request, new context (tool output, replies, re-reads) costs 1.25× (5-min TTL) or 2× (1-hour TTL) once, and output, thinking included, costs 5×. After an idle gap longer than the TTL, everything is written again. So: keep what enters context small, make fewer round trips, write less, and don't reload what you already carry.

## Rules

1. **Load progressively:** entry file (automatic) → `STATUS.md` → the current roadmap section → only the docs it names.
2. **Locate before reading:** code map → module contract (header comment) → `grep -n` → a line range. For a long doc, `grep -n '^## ' FILE` and read one section.
3. **Skip bulky files:** lockfiles, generated code, build output, vendored data, snapshots (unless reviewing them).
4. **Quiet commands:** failures-only tests, summarized checks, `gh run view --log-failed`; cap with `head`, `tail`, `cut -c1-200`, `--stat`, `jq`. Grep a saved large output instead of reading it. Check paths and quoting *before* running a command: a failed call's error enters context at the write price, and so does the retry.
5. **Batch** independent tool calls in one message.
6. **Don't re-read** what is in context and unchanged, including files you just wrote or edited.
7. **Write less:** new files in one pass, targeted edits to existing ones, short replies that don't echo tool output, diffs or file contents. Match thinking effort to the task.
8. **Look facts up once:** fetch with an extraction prompt or a page's `.md` version, record the result with date and source (e.g. DECISIONS.md), and cite the record afterwards.
9. **Decide once, ask once:** put every open question in one batched message (2–4 options, recommended default first); record the outcome; never reopen it without the owner. Each round trip re-reads the whole context.
10. **Subagents start cold:** use one only when it keeps far more out of the main context than its run costs (a sweeping search), on a cheaper model when the work is mechanical.
11. **Break the cache rarely, and all at once:** switching model, fast mode or effort, changing MCP servers, plugins or skills, or editing an entry file each re-writes the cache from that point on. Make all of them right after a `/clear`, never mid-session.
12. **No idle burn:** scheduled loops, cross-session messages, goal check-ins, prompt suggestions and idle compaction each re-send the full context on a timer while the session sits idle. Turn off what you don't use.
13. **Avoid rework:** on complex tasks, plan first (plan mode), state verification targets, and stop (`Esc`) or rewind at the first wrong turn. A wrong direction costs its whole exploration at the write price plus every later read.

## Checkpoints: clear or keep

Only the user can run `/clear`. At a natural boundary (task done, docs updated, committed and pushed):

- **D** = context the next work won't use. **R** = what it must reload after a clear plus re-orientation. **c** = requests ahead (a full work package is 100+).
- **Keep R small:** a tight `STATUS.md` (≤ 40 lines), the doc map and one roadmap section make the reload cheap, so clearing stays cheap.
- **Clear when D × c > ratio × R.** Ratio (write ÷ read) with a 1-hour TTL: 40 on Opus 5.5 and Sonnet 5.5, 80 on Fable 5.1, 20 on most others; × 0.625 for a 5-minute TTL. At ratio 40 and R ≈ 25k: clear above ~100k unused before a ~10-request follow-up, ~20k before a small task, ~10k before a full package.
- Exact numbers and the checkpoint line: `python3 ${CLAUDE_SKILL_DIR}/scripts/clear_or_keep.py --unused 60k --reload 25k --requests 100 [--model M] [--ttl 5m] [--cold] [--next "<task>"]`.
- **Cold cache** (idle longer than the TTL): clear unless most of the context is still needed.
- **Quality outranks cost:** keep when the next task needs details a handoff can't carry; clear when a long context blurs details.
- **Before any clear,** rewrite `STATUS.md`, commit and push. Prefer `/clear` + `STATUS.md` to `/compact`.
- **Switch model or fast mode right after a clear;** either change re-writes the cache.
- **Mid-task,** apply the test only when quality slips or the user will be away longer than the TTL.
- **Measure at every checkpoint:** run `/usage` and act on its recommendations (it names rows like "trim CLAUDE.md · 49k tokens per request"); the prompt-cache line shows your hit rate and miss causes. Cap a session with `--max-budget-usd`. `/insights` audits your session history for waste.

End the reply with one of these. When keeping and the repo's directives say to continue, carry on instead.
- `✅ Checkpoint — /clear recommended (<why>). Next: <task>. After clearing, say "continue".`
- `✅ Checkpoint — keep context (<why>). Next: <task>. Say "continue" within <TTL>; after that, /clear first.`
