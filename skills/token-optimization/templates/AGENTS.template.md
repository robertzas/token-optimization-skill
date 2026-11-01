# AGENTS.md

Entry point for AI agents working on **<project>**. Every request carries this file, so it stays short; read everything else on demand.

<One paragraph: what the project is, its stack, and the repo URL.>

## Standing directives (from the owner; always apply)

1. **Quality first, tokens second.** Never trade correctness, safety, UX or runtime efficiency for fewer tokens.
2. **Checkpoint after each WP** (done, docs updated, committed, pushed, CI green). Decide clear or keep with `docs/CHECKPOINTS.md`, then <continue into the next WP if keeping wins | stop either way> and end with its checkpoint line. Only the owner can clear.
3. **Offer options:** 2–4 with a recommended default; record the outcome in `docs/DECISIONS.md`. Decide small, reversible details yourself and note them.
4. **Keep docs true:** update them in the same commit as the change that would make them stale.
5. **Commit every significant change** (Conventional Commits) and keep `main` green.

## Session protocol

1. **Start:** read `docs/STATUS.md`, then only the current milestone of `docs/ROADMAP.md` (`grep -n '^## M'`, then that line range), then only the docs the WP lists.
2. **Locate** with `docs/MAP.md` and grep; read a module's contract (header comment) before its code, and large files by line range.
3. **Work** on one WP at a time, tests alongside the code. If it outgrows the session, split it in ROADMAP.md and checkpoint.
4. **Finish:** `<check command>` → tick ROADMAP.md → rewrite `docs/STATUS.md` (≤ 40 lines) → commit → push → CI green → checkpoint (directive 2).

## Token rules

- Never read <lockfiles, generated code, build output, data files, snapshots unless reviewing them>.
- Quiet commands: `<check command>`, `<failures-only test command>`, `gh run view --log-failed`.
- Batch independent tool calls. Don't re-read what is in context and unchanged. Write new files in one pass; edit existing ones.
- Source files ≤ ~400 lines, one concept each; extend through data (one small file per addition).

## Doc map (read on demand)

| Need | Read |
|---|---|
| Where we are, what's next | `docs/STATUS.md` |
| Work packages, acceptance criteria | `docs/ROADMAP.md` (one milestone) |
| Decisions, open options | `docs/DECISIONS.md` |
| Clear or keep at a checkpoint | `docs/CHECKPOINTS.md` |
| Where code lives | `docs/MAP.md` (generated) |
| <need> | <doc> |

## Definition of done (per WP)

Acceptance criteria met · tests added, `<check command>` green · ROADMAP ticked, STATUS rewritten · decisions recorded · committed and pushed · CI green · checkpoint made.
