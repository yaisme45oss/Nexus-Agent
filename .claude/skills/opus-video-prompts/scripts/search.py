#!/usr/bin/env python3
"""Search the Opus 5.5 video prompt library (data/videos.json).

Examples:
  search.py --stats
  search.py -q "lava lamp"
  search.py -c 3d -t threejs --full-only -n 10
  search.py --show ror-fly-880547
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "videos.json"
CATEGORIES = ("motion", "3d", "explainer", "interactive")


def load():
    with DATA.open(encoding="utf-8") as f:
        return json.load(f)


def title(entry):
    # Most entries with a remake have no title; fall back to the prompt's opening words.
    if entry.get("title"):
        return entry["title"]
    first = " ".join(entry["prompt"].split())
    return first if len(first) <= 70 else first[:67].rstrip() + "..."


def matches(entry, args):
    if args.category and entry["category"] != args.category:
        return False
    if args.tech and not set(args.tech) <= set(entry["tech_tags"]):
        return False
    if args.full_only and entry["prompt_partial"]:
        return False
    if args.remake and not entry["has_remake"]:
        return False
    if args.query:
        haystack = " ".join(
            [entry.get("title") or "", entry["author"], entry["prompt"], *entry["tech_tags"]]
        ).lower()
        return all(word in haystack for word in args.query.lower().split())
    return True


def show(entry):
    print(f"# {title(entry)}")
    print()
    print(f"- slug: {entry['slug']}")
    print(f"- author: @{entry['author']} ({entry['author_url']})")
    print(f"- original post: {entry['post_url']}")
    print(f"- category: {entry['category']}")
    print(f"- tech: {', '.join(entry['tech_tags']) or '-'}")
    if entry["has_remake"] and entry.get("skillry_url"):
        print(f"- live remake: {entry['skillry_url']}")
    if entry["prompt_partial"]:
        print("- NOTE: partial. The creator shared only part of the prompt or just described the result.")
    print()
    print("## Prompt")
    print()
    print(entry["prompt"])


def stats(entries):
    print(f"{len(entries)} entries, {sum(not e['prompt_partial'] for e in entries)} with a full prompt")
    print("categories:", ", ".join(f"{k} {v}" for k, v in Counter(e["category"] for e in entries).most_common()))
    print("tech:", ", ".join(f"{k} {v}" for k, v in Counter(t for e in entries for t in e["tech_tags"]).most_common()))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-q", "--query", help="words that must all appear in the title, author, tech tags or prompt")
    p.add_argument("-c", "--category", choices=CATEGORIES)
    p.add_argument("-t", "--tech", action="append", help="tech tag, e.g. canvas, svg, threejs, shader, gsap (repeatable)")
    p.add_argument("--full-only", action="store_true", help="skip entries whose prompt is partial")
    p.add_argument("--remake", action="store_true", help="only entries with a live remake on Skillry")
    p.add_argument("-n", "--limit", type=int, default=20)
    p.add_argument("--show", metavar="SLUG", help="print one entry's full prompt")
    p.add_argument("--stats", action="store_true", help="print category and tech counts")
    args = p.parse_args()

    entries = load()
    if args.stats:
        stats(entries)
        return
    if args.show:
        for entry in entries:
            if entry["slug"] == args.show:
                show(entry)
                return
        sys.exit(f"no entry with slug {args.show!r}")

    hits = [e for e in entries if matches(e, args)]
    # Full prompts first, then longer (more detailed) prompts.
    hits.sort(key=lambda e: (e["prompt_partial"], -len(e["prompt"])))
    for e in hits[: args.limit]:
        flag = " (partial)" if e["prompt_partial"] else ""
        print(f"{e['slug']}\t{e['category']}\t{','.join(e['tech_tags'])}\t{title(e)}{flag}")
    print(f"-- {len(hits)} match(es), showing {min(len(hits), args.limit)}", file=sys.stderr)


if __name__ == "__main__":
    main()
