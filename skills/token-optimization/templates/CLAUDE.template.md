@AGENTS.md

## Claude Code specifics

- When a checkpoint says stop, make the checkpoint line the last thing in the reply. When it says continue, note the finished WP in one line and start the next.
- Present options with AskUserQuestion: 2–4 choices, the recommended one first, labelled "(Recommended)".
- Read big docs by section: `grep -n '^## ' <file>`, then Read with offset and limit.
- After pushing, `gh run watch --exit-status`; on failure, `gh run view --log-failed`.
- Prefer `/clear` with `docs/STATUS.md` as the handoff over `/compact`.
