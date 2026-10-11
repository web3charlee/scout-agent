"""Evaluation harness.  python -m evals.run_evals [--demo] [--depth quick] [--only e1,e3]

Measures, per case:
  structure    all required report sections present (negative control: sparse report with gaps is correct)
  citations    share of timeline/strategy/SWOT/competitor items that cite >=1 valid finding   (target 100%)
  grounded     share of findings whose quoted snippet is verbatim-present in the retrieved page (target >=90%)
  sources      distinct URLs behind the report
  keyword      report mentions at least one expected term (cheap proxy for factual relevance)
  conflicts    number of conflicts flagged
  seconds      wall-clock latency
The negative control passes only if Scout makes no unsupported claims.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from scout.runner import ScoutRunner

HERE = Path(__file__).parent


def items_of(r: dict) -> list[dict]:
    return r["timeline"] + r["strategy"] + r["competitors"] + [x for v in r["swot"].values() for x in v]


def score_case(case: dict, r: dict, secs: float, demo: bool) -> dict:
    ids = {f["id"] for f in r["findings"]}
    items = items_of(r)
    cited = sum(1 for i in items if i["evidence_ids"] and set(i["evidence_ids"]) <= ids)
    text = json.dumps(r, ensure_ascii=False).lower()
    f = r["findings"]
    out = {
        "id": case["id"], "company": case["company"], "tier": case["tier"],
        "findings": len(f), "sources": len({x["source_url"] for x in f}),
        "citations_pct": round(100 * cited / len(items)) if items else 100,
        "grounded_pct": round(100 * sum(1 for x in f if x["grounding"] >= 0.8) / len(f)) if f else 100,
        "conflicts": len(r["contradictions"]), "seconds": round(secs, 1),
    }
    if case.get("expect_empty"):
        out["structure"] = bool(r["gaps"]) and bool(r["executive_summary"])
        out["keyword"] = "n/a"
        out["pass"] = out["structure"] and out["citations_pct"] == 100 and out["findings"] <= 3
    else:
        out["structure"] = all(r[k] for k in ("executive_summary", "timeline", "strategy", "competitors")) and all(r["swot"].values())
        out["keyword"] = "n/a" if demo else any(k in text for k in case["expect_any"])
        out["pass"] = out["structure"] and out["citations_pct"] == 100 and out["grounded_pct"] >= 90 and out["keyword"] in (True, "n/a")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="harness check on synthetic data (no keys)")
    ap.add_argument("--depth", default="quick", choices=["quick", "standard", "deep"])
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cases = json.loads((HERE / "cases.json").read_text())
    if a.only:
        cases = [c for c in cases if c["id"] in a.only.split(",")]
    if a.demo:
        cases = cases[:1]
    rows = []
    for c in cases:
        t0 = time.time()
        try:
            r = ScoutRunner(c["company"], "demo" if a.demo else "live", a.depth, persist=not a.demo).run_blocking()
            rows.append(score_case(c, r, time.time() - t0, a.demo))
        except Exception as e:
            rows.append({"id": c["id"], "company": c["company"], "tier": c["tier"], "pass": False, "error": str(e)[:120]})
        print(rows[-1], file=sys.stderr)
    done = [r for r in rows if "error" not in r]
    summary = {
        "cases": len(rows), "passed": sum(1 for r in rows if r["pass"]),
        "avg_grounded_pct": round(sum(r["grounded_pct"] for r in done) / len(done)) if done else 0,
        "avg_seconds": round(sum(r["seconds"] for r in done) / len(done), 1) if done else 0,
    }
    (HERE / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    md = ["# Scout evaluation results", "", f"Mode: {'demo (harness check only)' if a.demo else 'live'} · depth: {a.depth}", "",
          f"**{summary['passed']}/{summary['cases']} passed** · avg grounded {summary['avg_grounded_pct']}% · avg {summary['avg_seconds']}s", "",
          "| id | company | tier | findings | sources | citations | grounded | keyword | conflicts | s | pass |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            md.append(f"| {r['id']} | {r['company']} | {r['tier']} | error: {r['error']} | | | | | | | ❌ |")
        else:
            md.append(f"| {r['id']} | {r['company']} | {r['tier']} | {r['findings']} | {r['sources']} | {r['citations_pct']}% | "
                      f"{r['grounded_pct']}% | {r['keyword']} | {r['conflicts']} | {r['seconds']} | {'✅' if r['pass'] else '❌'} |")
    (HERE / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0 if summary["passed"] == summary["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
