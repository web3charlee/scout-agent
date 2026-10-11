from __future__ import annotations


def _cites(ids, fmap) -> str:
    return " ".join(f"[{i}]" for i in ids if i in fmap)


def to_markdown(r: dict) -> str:
    fmap = {f["id"]: f for f in r.get("findings", [])}
    s = r.get("stats", {})
    L = [f"# Scout report: {r['company']}", "",
         f"*Generated {r['generated_at']} · mode: {r['mode']} · {s.get('findings', 0)} cited findings from "
         f"{s.get('sources', 0)} sources · {s.get('grounded_pct', 0)}% citations verified in source text*", ""]
    if r.get("mode") == "demo":
        L += ["> **Synthetic demo data about a fictional company. Not real intelligence.**", ""]
    L += ["## Executive summary", "", r.get("executive_summary", ""), ""]
    L += ["## Timeline of recent moves", ""]
    for t in r.get("timeline", []):
        L.append(f"- **{t.get('date') or 'undated'}: {t['title']}** ({t['confidence']}, {round(t['score']*100)}%). "
                 f"{t.get('description', '')} {_cites(t['evidence_ids'], fmap)}")
    L += ["", "## Inferred current strategy", ""]
    for x in r.get("strategy", []):
        L.append(f"- {x['statement']} ({x['confidence']}, {round(x['score']*100)}%) {_cites(x['evidence_ids'], fmap)}")
    L += ["", "## SWOT", ""]
    for k, title in (("strengths", "Strengths"), ("weaknesses", "Weaknesses"),
                     ("opportunities", "Opportunities"), ("threats", "Threats")):
        L.append(f"### {title}")
        for x in r.get("swot", {}).get(k, []):
            L.append(f"- {x['point']} ({x['confidence']}) {_cites(x['evidence_ids'], fmap)}")
        L.append("")
    L += ["## Competitors and threat landscape", ""]
    for c in r.get("competitors", []):
        L.append(f"- **{c['name']}**, threat: {c.get('threat_level', 'n/a')}. {c.get('rationale', '')} {_cites(c['evidence_ids'], fmap)}")
    L += ["", "## Conflicting evidence", ""]
    if not r.get("contradictions"):
        L.append("- None detected.")
    for c in r.get("contradictions", []):
        L.append(f"- **{c['topic']}** ({c['status']}). {c.get('resolution', '')} {_cites(c['evidence_ids'], fmap)}")
    L += ["", "## Gaps", ""] + [f"- {g}" for g in r.get("gaps", [])] + ["", "## Sources", ""]
    for f in r.get("findings", []):
        L.append(f"- **[{f['id']}]** {f['claim']} ({f['confidence']}, {f['date'] or 'undated'}) "
                 f"<{f['source_url']}> > \"{f['snippet']}\"")
    return "\n".join(L) + "\n"
