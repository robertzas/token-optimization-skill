# AGENTS.md

This is the entry point for AI coding agents working on **<project>**. It is in every session's context, so it stays short; everything else is read on demand.

<One paragraph: what the project is, its stack, and the repo URL.>

## Standing directives (from the owner; always apply)

1. **Quality first, tokens second.** Never trade correctness, safety, UX or runtime efficiency for fewer tokens.
2. **Checkpoints (prompt-cache aware).** A checkpoint is reached when the work package is done, docs are updated, everything is committed and pushed, and CI is green. Only the owner can clear context, so decide with "Clear or keep" below:
   - **Clearing pays off:** stop, and end the reply with
     `✅ Checkpoint — /clear recommended (<why>). Next: <WP id + title>. After clearing, say "continue".`
   - **Keeping is cheaper:** <continue into the next WP without stopping | stop and end the reply with:>
     `✅ Checkpoint — keep context (<why>). Next: <WP id + title>. Say "continue" within <TTL>; after that, /clear first.`
   - **Mid-WP:** apply the same test only when a long context starts to hurt quality, or when the owner will be away longer than the cache TTL. Make `docs/STATUS.md` carry the state before you stop.
3. **Offer options.** For any good idea or recommendation, give the owner 2–4 options with a recommended default, then record the outcome in `docs/DECISIONS.md`. For small, reversible details, decide and note it.
4. **Keep the docs true.** Update docs in the same commit as the change that would make them stale.
5. **Commit every significant change** using Conventional Commits, and keep `main` green.

## Session protocol

1. **Start:** read `docs/STATUS.md`. In `docs/ROADMAP.md`, read only the current milestone: run `grep -n '^## M' docs/ROADMAP.md`, then read that line range.
2. **Locate** code with `docs/MAP.md` and grep. Read a module's contract (its header comment) before its implementation.
3. **Work** on one WP at a time, and write tests alongside the code. If the WP outgrows the session, split it in ROADMAP.md and checkpoint.
4. **Finish:** run `<check command>` → tick the WP in ROADMAP.md → rewrite `docs/STATUS.md` (≤ 40 lines) → commit → push → confirm CI is green → make the checkpoint decision (directive 2).

## Token economy rules

- Load docs progressively: this file (automatic) → STATUS.md → the WP's section → only the docs the WP lists.
- Prefer contracts, maps and specs over implementation. Grep for symbols, and read line ranges instead of whole large files.
- Never read generated or bulky files: <lockfiles, generated code, build output, data files, snapshots unless reviewing them>.
- Use quiet commands: `<check command>` (summarized output), `<failures-only test command>`, `gh run view --log-failed`.
- Don't re-read what is already in context and unchanged, including files you just wrote. Batch independent tool calls. Write new files in one pass, and edit existing ones.
- Keep source files to about 400 lines or fewer, one concept per file.
- Extend through data where possible: each addition is one small file.
- Record a decision once, in DECISIONS.md. Never reopen an accepted decision without the owner.

### Prompt-cache cost model

<Agent and model> with a <1-hour> cache TTL. Relative to fresh input (1×):
- Cached context costs <0.05×> per request, and every request (each tool round trip) re-reads all of it.
- New tokens are written to the cache once at <2×>, then carried at the read price.
- Output, thinking included, costs 5×.
- When the TTL passes without a request, the next request re-writes the whole context at the write price.

### Clear or keep

Keeping costs read × D per request, where D is the context the next work won't use. Clearing costs write × R once, where R is what the next work must load again, plus re-orientation (typically 20–30k tokens). Clear when D × (requests ahead) > <ratio> × R.

| Work ahead | Clear when the unused context exceeds about |
|---|---|
| A follow-up (~10 requests) | <100k> |
| A small WP (~50 requests) | <20k> |
| A full WP (100+ requests) | <10k> |

- When the next WP reuses most of what is loaded, D is small and keeping usually wins.
- After an idle gap longer than the TTL the cache is cold: clear unless most of the context is still needed.
- Quality outranks cost (directive 1). Keep when the next WP depends on details STATUS.md can't carry. Clear when a long context starts to blur details.

## Doc map (read on demand)

| Need | Read |
|---|---|
| Where we are and what's next | `docs/STATUS.md` |
| Work packages and acceptance criteria | `docs/ROADMAP.md` (one milestone section) |
| Decisions and open options | `docs/DECISIONS.md` |
| Where code lives | `docs/MAP.md` (generated) |
| <need> | <doc> |

## Definition of done (per WP)

Acceptance criteria are met · tests are added and `<check command>` is green · docs are updated (ROADMAP tick, STATUS) · decisions are recorded · the work is committed and pushed · CI is green · the checkpoint decision is made.
