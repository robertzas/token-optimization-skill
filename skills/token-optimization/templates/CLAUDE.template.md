@AGENTS.md

## Claude Code specifics

- `/clear` can only be run by the user. When the checkpoint directive says stop, make the checkpoint line the last thing in your reply, then stop. When it says continue, note in one line that the WP is done, then start the next one.
- Present options with AskUserQuestion: 2–4 choices, the recommended one first, labelled "(Recommended)".
- Read big docs one section at a time: run `grep -n '^## ' <file>`, then Read with offset and limit.
- After pushing, follow CI with `gh run watch`. On failure, use `gh run view --log-failed`.
- Switching `/model` or `/fast` mid-session re-writes the whole context at the write price. Switch right after a `/clear`.
- Prefer `/clear` with `docs/STATUS.md` as the handoff over `/compact`.
