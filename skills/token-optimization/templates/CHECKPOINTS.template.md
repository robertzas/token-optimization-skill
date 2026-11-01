# Checkpoints: clear or keep

Read this at a checkpoint (see AGENTS.md, directive 2). Only the owner can clear context.

## Cost model

<Agent and model>, <1-hour> cache TTL. Relative to fresh input (1×):
- Cached context costs <0.05×> per request, and every request (each tool round trip) re-reads all of it.
- New tokens are written to the cache once at <2×>, then carried at the read price.
- Output, thinking included, costs 5×.
- After the TTL passes without a request, the next request re-writes the whole context.

## The test

Keeping costs read × D per request, where D is the context the next work won't use. Clearing costs write × R once, where R is what the next work must load again plus re-orientation (typically 20–30k tokens). **Clear when D × (requests ahead) > <ratio> × R.**

| Work ahead | Clear when the unused context exceeds about |
|---|---|
| A follow-up (~10 requests) | <100k> |
| A small WP (~50 requests) | <20k> |
| A full WP (100+ requests) | <10k> |

- When the next WP reuses most of what is loaded, D is small and keeping usually wins.
- Cold cache (idle longer than the TTL): clear unless most of the context is still needed.
- Quality outranks cost: keep when the next WP depends on details STATUS.md can't carry; clear when a long context starts to blur details.
- Mid-WP: apply the test only when quality slips or the owner will be away longer than the TTL. Make `docs/STATUS.md` carry the state before stopping.
- Keep R small: a tight `docs/STATUS.md` (≤ 40 lines), the doc map and one roadmap section make each clear cheap.
- Break the cache rarely, all at once: switch model/fast mode, change MCPs/plugins/skills, or edit entry files only right after a clear; each change re-writes the cache from that point on.

## Checkpoint lines

End the reply with one of these:
- `✅ Checkpoint — /clear recommended (<why>). Next: <WP id + title>. After clearing, say "continue".`
- `✅ Checkpoint — keep context (<why>). Next: <WP id + title>. Say "continue" within <TTL>; after that, /clear first.`
