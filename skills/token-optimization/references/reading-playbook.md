# Reading and command playbook

Every line of output lands in context once at the write price and is then carried by every later request. Ask for the smallest output that answers the question.

## Finding things

| Need | Command |
|---|---|
| The sections of a long doc | `grep -n '^## ' docs/ROADMAP.md`, then read one section by line range |
| Where a symbol is defined | `git grep -n 'fn parse_uci'` or `grep -rn --include='*.rs' 'fn parse_uci' crates/` |
| Only the matching file names | `grep -rl 'TODO' src/` or `git ls-files 'crates/*/src/lib.rs'` |
| What a file is for | the code map (`docs/MAP.md`), or `head -20 FILE` for its contract |
| How big a file is before reading it | `wc -l FILE` (about 10 tokens per line of code) |
| Long lines in any output | append `\| cut -c1-200` |
| Counts instead of lists | `grep -c PATTERN FILE`, or `... \| sort \| uniq -c \| sort -rn \| head` |

## Reading

- Read the contract (the module's header comment) before the implementation.
- Once you know where to look, read a line range: the Read tool's offset and limit, or `sed -n '120,180p' FILE`.
- Reuse what is already in context. After an edit, trust the edit result instead of re-reading the file.
- When a tool saves a large output to a file, run `grep -n PATTERN that-file | head` instead of reading the whole file.
- Combine several small read-only lookups into one shell call. Separate them with `echo '=== name ==='` so each result stays labelled.

## Git

`git status --short` · `git diff --stat` · `git diff -U1 FILE` · `git log --oneline -10` · `git show --stat HEAD`

## Builds and tests: failures only

| Ecosystem | Quiet form |
|---|---|
| Rust | `cargo build -q` · `cargo clippy -q -- -D warnings` · `cargo nextest run --status-level fail --final-status-level fail` · `cargo test -q` |
| Python | `pytest -q -x --tb=short` · `python3 -m unittest discover -q` |
| JS/TS | `vitest run --reporter=dot` · `jest --silent` · `tsc --noEmit --pretty false` |
| Go | `go vet ./...` · `go test ./... 2>&1 \| grep -Ev '^(ok\|\?) '` |
| Anything noisy | `CMD > /tmp/out.log 2>&1; echo "exit $?"; tail -20 /tmp/out.log`, then grep the log only if needed |
| GitHub CI | `gh run list -L 3` · `gh run watch --exit-status` · `gh run view RUN_ID --log-failed` |
| JSON | `jq '.field'` · `gh ... --json name,status --jq '.[] \| ...'` |

The best single investment is a repo-level `check` command that runs everything CI gates on and prints only a summary and the failures: one call, one short output.

## The web

- Fetch with a prompt that names exactly the facts to extract.
- Prefer machine-friendly sources. Many docs sites serve a `.md` version of each page, and an `llms.txt` index.
- Record what you learned with the date and the source URL, so nobody fetches it again.

## Asking the user

- One question with 2–4 options and a recommended default costs less than a wrong guess plus the rework that follows.
- Record the answer (in DECISIONS.md, or wherever the repo keeps decisions) so the question is never asked again.
