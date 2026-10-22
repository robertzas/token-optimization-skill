#!/usr/bin/env python3
"""Decide whether to /clear or keep an agent's context, using prompt-cache prices.

Keeping carries the context the next work won't use (D) through the requests
ahead (c) at the cache-read price. Clearing reloads what the next work needs,
plus re-orientation (R), at the cache-write price, once. Costs are in
fresh-input-token equivalents so they compare across models; dollar figures
use the model's base input price.

    clear_or_keep.py --unused 60k --reload 25k --requests 100 --next "M0.3 Web skeleton"
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass

# model: (cache-read multiplier, base input USD per million tokens). Checked 2026-10-22 at
# https://platform.claude.com/docs/en/about-claude/pricing; keep in step with references/cost-model.md.
MODELS = {
    "fable-5.1": (0.025, 10.0),
    "opus-5.5": (0.05, 4.0),
    "opus-5": (0.1, 5.0),
    "opus-4.8": (0.1, 5.0),
    "sonnet-5.5": (0.05, 2.0),
    "sonnet-5": (0.1, 2.0),
    "sonnet-4.6": (0.1, 3.0),
    "haiku-5.5": (0.1, 0.10),
    "haiku-4.5": (0.1, 1.0),
}
WRITE_MULTIPLIERS = {"5m": 1.25, "1h": 2.0}
TTL_LABELS = {"5m": "5 min", "1h": "1 h"}
DEFAULT_REORIENT = 10_000

_TOKENS = re.compile(r"^([0-9][0-9_,]*(?:\.[0-9]+)?)([km]?)$", re.IGNORECASE)


@dataclass(frozen=True)
class Verdict:
    keep_cost: float  # fresh-input-token equivalents
    clear_cost: float
    ratio: float  # write multiplier / read multiplier
    break_even_requests: float | None  # None when the cache is cold or nothing is unused
    clear: bool


def parse_tokens(text: str) -> int:
    """Parse '60k', '1.5M', '25,000' or '25000' into a token count."""
    match = _TOKENS.match(text.strip())
    if not match:
        raise ValueError(f"not a token count: {text!r} (use e.g. 60k, 1.5M or 25000)")
    number = float(match.group(1).replace("_", "").replace(",", ""))
    return round(number * {"": 1, "k": 1_000, "m": 1_000_000}[match.group(2).lower()])


def fmt_tokens(n: float) -> str:
    """Format a token count compactly: 950, 7.5k, 350k, 1.5M."""
    if n >= 999_500:
        value, suffix = n / 1_000_000, "M"
    elif n >= 1_000:
        value, suffix = n / 1_000, "k"
    else:
        return str(round(n))
    text = f"{value:.0f}" if value >= 100 else f"{value:.1f}".rstrip("0").rstrip(".")
    return text + suffix


def fmt_usd(amount: float) -> str:
    return "<$0.01" if amount < 0.01 else f"${amount:.2f}"


def decide(unused, reload, requests, read_mult, write_mult, cold=False, reorient=DEFAULT_REORIENT) -> Verdict:
    """Compare carrying `unused` tokens for `requests` more requests with reloading `reload` tokens."""
    for name, value in (("unused", unused), ("reload", reload), ("requests", requests), ("reorient", reorient)):
        if value < 0:
            raise ValueError(f"{name} must not be negative")
    if read_mult <= 0 or write_mult <= 0:
        raise ValueError("price multipliers must be positive")
    carry = read_mult * unused * requests
    if cold:
        # Everything is re-written either way; only the unused part and re-orientation differ.
        keep, clear, break_even = write_mult * unused + carry, write_mult * min(reorient, reload), None
    else:
        keep, clear = carry, write_mult * reload
        break_even = clear / (read_mult * unused) if unused else None
    return Verdict(keep, clear, write_mult / read_mult, break_even, clear < keep)


def checkpoint_line(verdict: Verdict, unused, requests, ttl, cold, next_task, usd) -> str:
    scope = "cache expired" if cold else f"~{requests} requests ahead"
    if verdict.clear:
        saving = fmt_usd(usd(verdict.keep_cost - verdict.clear_cost))
        why = f"~{fmt_tokens(unused)} unused, {scope}; saves ~{saving}"
        return f'✅ Checkpoint — /clear recommended ({why}). Next: {next_task}. After clearing, say "continue".'
    extra = fmt_usd(usd(verdict.clear_cost - verdict.keep_cost))
    why = f"~{fmt_tokens(unused)} unused, {scope}; clearing costs ~{extra} more"
    return (f"✅ Checkpoint — keep context ({why}). Next: {next_task}. "
            f'Say "continue" within {TTL_LABELS[ttl]}; after that, /clear first.')


def report(args, verdict: Verdict, read_mult, write_mult, usd) -> str:
    def cost(equivalents):
        return f"{fmt_tokens(equivalents)} input-token equivalents ({fmt_usd(usd(equivalents))})"

    unused = fmt_tokens(args.unused)
    lines = [f"Model {args.model} · TTL {TTL_LABELS[args.ttl]}{' (expired)' if args.cold else ''} · "
             f"cache read {read_mult:g}× · write {write_mult:g}× · ratio {verdict.ratio:g}"]
    if args.cold:
        lines.append(f"Keep:  {write_mult:g} × {unused} unused re-written + "
                     f"{read_mult:g} × {unused} × {args.requests} requests = {cost(verdict.keep_cost)}")
        reorient = fmt_tokens(min(args.reorient, args.reload))
        lines.append(f"Clear: {write_mult:g} × {reorient} re-orientation = {cost(verdict.clear_cost)}")
    else:
        lines.append(f"Keep:  {read_mult:g} × {unused} unused × {args.requests} requests = {cost(verdict.keep_cost)}")
        lines.append(f"Clear: {write_mult:g} × {fmt_tokens(args.reload)} reload = {cost(verdict.clear_cost)}")
        if verdict.break_even_requests is not None:
            lines.append(f"Break-even: {math.ceil(verdict.break_even_requests)} requests")
    saving = abs(verdict.keep_cost - verdict.clear_cost)
    lines.append(f"Verdict: {'/clear' if verdict.clear else 'keep'}, saving ~{cost(saving)}")
    lines.append("Quality outranks cost: keep if the next work depends on details the handoff can't carry.")
    return "\n".join(lines)


def _tokens_arg(text: str) -> int:
    try:
        return parse_tokens(text)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decide whether to /clear or keep an agent's context, using prompt-cache prices.")
    add = parser.add_argument
    add("--unused", required=True, type=_tokens_arg, help="context the next work won't use (D), e.g. 60k")
    add("--reload", type=_tokens_arg, default=25_000,
        help="tokens to load again after a clear, plus re-orientation (R); default 25k")
    add("--requests", type=int, default=100, help="requests ahead (c); a full work package takes 100+; default 100")
    add("--model", choices=sorted(MODELS), default="opus-5.5", help="price preset; default opus-5.5")
    add("--ttl", choices=sorted(WRITE_MULTIPLIERS), default="1h", help="cache TTL; default 1h")
    add("--read-mult", type=float, help="override the cache-read multiplier")
    add("--write-mult", type=float, help="override the cache-write multiplier")
    add("--cold", action="store_true", help="the cache has expired (idle longer than the TTL)")
    add("--reorient", type=_tokens_arg, default=DEFAULT_REORIENT,
        help="re-orientation share of --reload, used with --cold; default 10k")
    add("--next", dest="next_task", default="<task>", help="the next task, for the checkpoint line")
    add("--json", action="store_true", help="print JSON instead of text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    default_read, input_price = MODELS[args.model]
    read_mult = default_read if args.read_mult is None else args.read_mult
    write_mult = WRITE_MULTIPLIERS[args.ttl] if args.write_mult is None else args.write_mult
    try:
        verdict = decide(args.unused, args.reload, args.requests, read_mult, write_mult, args.cold, args.reorient)
    except ValueError as err:
        parser.error(str(err))

    def usd(equivalents: float) -> float:
        return equivalents * input_price / 1_000_000

    line = checkpoint_line(verdict, args.unused, args.requests, args.ttl, args.cold, args.next_task, usd)
    if args.json:
        print(json.dumps({
            "verdict": "clear" if verdict.clear else "keep",
            "model": args.model,
            "ttl": args.ttl,
            "cold": args.cold,
            "read_multiplier": read_mult,
            "write_multiplier": write_mult,
            "ratio": verdict.ratio,
            "unused": args.unused,
            "reload": args.reload,
            "requests": args.requests,
            "keep_cost": verdict.keep_cost,
            "clear_cost": verdict.clear_cost,
            "keep_usd": round(usd(verdict.keep_cost), 4),
            "clear_usd": round(usd(verdict.clear_cost), 4),
            "break_even_requests": verdict.break_even_requests,
            "checkpoint_line": line,
        }, ensure_ascii=False, indent=2))
    else:
        print(report(args, verdict, read_mult, write_mult, usd))
        print()
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
