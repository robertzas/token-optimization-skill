# Cost model

Prices were checked on 2026-10-22 at https://platform.claude.com/docs/en/about-claude/pricing. When they change, update the tables here, the "Why" paragraph and ratio line in SKILL.md, `templates/CHECKPOINTS.template.md`, and `MODELS` in `scripts/clear_or_keep.py`.

## Contents
- Prices
- How a session is billed
- What invalidates the cache
- The clear-or-keep test
- Worked example
- /compact versus /clear
- Subagents
- Fixed per-request overhead

## Prices (USD per million tokens)

| Model | Input | 5-min cache write | 1-hour cache write | Cache read | Output | Read ÷ input |
|---|---|---|---|---|---|---|
| Fable 5.1 | 10 | 12.50 | 20 | 0.25 | 50 | 0.025 |
| Opus 5.5 | 4 | 5 | 8 | 0.20 | 20 | 0.05 |
| Opus 5, 4.8, 4.7, 4.6, 4.5 | 5 | 6.25 | 10 | 0.50 | 25 | 0.1 |
| Sonnet 5.5 | 2 | 2.50 | 4 | 0.10 | 10 | 0.05 |
| Sonnet 5 | 2 | 2.50 | 4 | 0.20 | 10 | 0.1 |
| Sonnet 4.6, 4.5 | 3 | 3.75 | 6 | 0.30 | 15 | 0.1 |
| Haiku 5.5 (prompts up to 100k) | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 | 0.1 |
| Haiku 4.5 | 1 | 1.25 | 2 | 0.10 | 5 | 0.1 |

- On every model listed, a 5-minute cache write costs 1.25× input, a 1-hour write costs 2× and output costs 5×.
- Haiku 5.5 prompts over 100k tokens cost 5× the rates above.
- Fast mode (Opus 5.5: $8 input, $40 output) doubles the price. Cache multipliers apply on top of it.

## How a session is billed

- Each request re-sends the whole context. The prefix that hits the cache costs the read price. Everything after the last hit is written to the cache at the write price, or billed as plain input if it isn't cached.
- A cache hit refreshes the entry's TTL for free. The TTL counts from the *start* of a request, so a long generation uses up part of it. Work in bursts inside the TTL window: keep requests flowing, and if a pause longer than the TTL is coming, checkpoint (clear) first.
- Claude Code caches automatically. The sessions this skill was built in (Claude Code on a subscription plan) used the 1-hour TTL, falling back to 5 minutes during usage overage. Check what your setup uses: on the API, `usage.cache_creation` splits writes by TTL.
- Thinking is billed as output. Recent models keep earlier turns' thinking blocks in the prompt, so long thinking is also carried forward like any other context.
- Totals: `input_tokens` is only the uncached remainder. The full prompt is `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.
- **Measure, don't assume.** In Claude Code, `/context` shows the cache breakdown; on the API, watch the `cache_read` share of the full prompt. If it drops mid-session, something in the prefix changed (see the invalidation table) — find and fix it before it compounds across every later request.

## What invalidates the cache

The cache is a prefix in the order tools → system → messages. A change invalidates its own level and everything after it.

| Change | What is re-written |
|---|---|
| Switching model | everything (caches are per model) |
| Toggling fast mode (speed) | system and messages |
| Changing thinking or effort settings | messages, and more on some models |
| Changing tool definitions (adding/removing an MCP server, plugin or skill) | everything |
| Editing the system prompt or an entry file (AGENTS.md, CLAUDE.md, `@` imports) | system and messages |
| Idling longer than the TTL | everything |

Each change re-writes the cache from its point onward, so bundle every prefix-breaking change — model, speed, effort, tools, entry files — into one burst right after a `/clear`. Never make them one by one partway through a long session: each one makes everything after it a cache miss.

## The clear-or-keep test

Symbols:
- D: tokens in context that the next work won't use.
- R: tokens the next work must load again after a clear, plus re-orientation.
- c: requests ahead (each tool round trip is one request).
- r: the read multiplier.
- w: the write multiplier.

The calculation, while the cache is warm:
- Keeping carries D through c requests and costs r·D·c. The part the next work needs is carried either way, so it cancels out.
- Clearing reloads R once and costs w·R.
- Clear when r·D·c > w·R, which is the same as D·c > (w ÷ r)·R.

**Keep R small.** R is the reload after a clear: a tight STATUS.md (≤ 40 lines), the doc map and one roadmap section. The smaller R is, the cheaper every clear is, so clear more readily. A bloated handoff makes keeping look artificially cheap.

| Read multiplier | w ÷ r, 1-hour TTL (w = 2) | w ÷ r, 5-minute TTL (w = 1.25) |
|---|---|---|
| 0.1 (most models) | 20 | 12.5 |
| 0.05 (Opus 5.5, Sonnet 5.5) | 40 | 25 |
| 0.025 (Fable 5.1) | 80 | 50 |

The break-even number of requests is c* = (w ÷ r)·R ÷ D. With a ratio of 40 and R = 25k:

| D | c* |
|---|---|
| 10k | 100 requests |
| 50k | 20 requests |
| 100k | 10 requests |

Read the other way, as a threshold on D (ratio 40, R ≈ 25k):

| Work ahead | Clear when the unused context exceeds about |
|---|---|
| A follow-up (~10 requests) | 100k |
| A small task (~50 requests) | 20k |
| A full work package (100+ requests) | 10k |

**Cold cache.** After an idle gap longer than the TTL, keeping re-writes the whole context, D included, and costs w·D + r·D·c. The needed part is written either way, so clearing costs only the re-orientation share of R. Clear unless D is small.

**Estimating sizes.** English and code run about 4 characters per token, and 100 lines of code is roughly 1k tokens. For a file, use `wc -c FILE` ÷ 4. In Claude Code, `/context` shows the actual total.

## Worked example (Opus 5.5, 1-hour TTL)

At the end of a work package the context holds 120k tokens: 30k of base prompt, 20k the next package needs, and 70k it won't use. The next package will take about 100 requests.

- Keeping costs 0.05 × 70k × 100 = 350k input-token equivalents ($1.40).
- Clearing costs 2 × 25k = 50k equivalents ($0.20). **Clear.**

If the next step were a 10-request follow-up instead, keeping would cost 35k against 50k for clearing. **Keep.**

## /compact versus /clear

`/compact` reads the whole context once (at the read price if the cache is warm), writes a summary as output (5×), and starts a new context from that summary at the write price. With 150k of context and an 8k summary on Opus 5.5 (1-hour TTL), that is 0.05 × 150k + 5 × 8k + 2 × 8k ≈ 63k equivalents. A clear plus a 25k reload costs about 50k.

The costs are similar, but the compact summary is ad hoc and nobody reviews it. Prefer a maintained `STATUS.md` with `/clear`, and leave auto-compact as the safety net.

## Subagents

A subagent starts with a fresh context. It pays for its own base prompt and everything it reads at the write price, and hands back only its final report. That saves tokens when the main session would otherwise carry the raw material through many requests.

Example: a search reads 60k tokens to produce a 2k answer, and the main session has 100 requests ahead. Done inline, it costs about 2 × 60k + 0.05 × 58k × 100 ≈ 410k equivalents. In a subagent it costs about 2 × (60k + its base prompt), well under that. For small lookups, work inline.

A mechanical subagent (search, bulk rename, log triage) can run on a cheaper model: the same tokens on Haiku 4.5 cost a fifth of Opus 4.8, and Sonnet 5.5 half of Opus 5.5. Keep judgment-heavy work on the main model.

## Fixed per-request overhead

Some tokens ride on every request before any work happens: the system prompt, tool definitions (including every enabled MCP server's tools), the listing of installed skills, and the entry files (CLAUDE.md, AGENTS.md and their `@` imports). They are cheap per request because they are cached, but they are paid on every request of every session, and a change to any of them re-writes the cache from that point on.

- An entry file of 1k tokens costs 0.05 × 1k × 100 = 5k equivalents per 100-request session on Opus 5.5, plus 2k for writing it into the cache. Every line has to earn that.
- Disable MCP servers and plugins a project doesn't use (`/mcp`, `/plugin`). Claude Code defers many tool schemas until they're searched for, but their names and descriptions still load.
- `/context` shows the breakdown for the current session.
