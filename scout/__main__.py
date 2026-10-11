"""CLI: python -m scout "Stripe" [--demo] [--depth quick|standard|deep] [--out report.md]"""
from __future__ import annotations

import argparse
import queue
import sys

from .export import to_markdown
from .runner import ScoutRunner


def main() -> int:
    ap = argparse.ArgumentParser(prog="scout", description="Scout: competitive intelligence agent")
    ap.add_argument("company", nargs="?", default="", help="Company name, website or LinkedIn URL")
    ap.add_argument("--demo", action="store_true", help="Offline synthetic demo (no API keys)")
    ap.add_argument("--depth", choices=["quick", "standard", "deep"], default="standard")
    ap.add_argument("--out", help="Write the Markdown report to this path")
    a = ap.parse_args()
    if not a.company and not a.demo:
        ap.error("company is required unless --demo is set")
    r = ScoutRunner(a.company, "demo" if a.demo else "live", a.depth).start()
    while not r.finished or not r.events.empty():
        try:
            ev = r.events.get(timeout=0.3)
        except queue.Empty:
            continue
        if ev["status"] != "finished":
            print(f"[{ev['node']:<8}] {ev['status']:<8} {ev['msg']}", file=sys.stderr)
    if r.error:
        print(f"Error: {r.error}", file=sys.stderr)
        return 1
    md = to_markdown(r.report)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(md)
        print(f"Saved {a.out}", file=sys.stderr)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
