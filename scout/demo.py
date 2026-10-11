"""Offline demo mode.

Everything here is SYNTHETIC: a fictional company ("Northwind Labs") and `.example` URLs (a reserved TLD).
It exists so the UI, the pipeline and the tests run without API keys, and so judges can see the full
investigation flow (including a deliberate funding conflict) even if live APIs are down.
"""
from __future__ import annotations

import time

from .llm import BaseLLM
from .search import SearchResult

COMPANY = "Northwind Labs"

# role -> list of (title, url, date, content, claim, snippet, confidence, category)
DOCS: dict[str, list[tuple]] = {
    "news": [
        ("Northwind Labs raises $15M Series A to bring AI routing to mid-market freight",
         "https://newsroom.northwindlabs.example/series-a", "2026-02-10",
         "Northwind Labs today announced a $15 million Series A round led by Cobalt Ridge Ventures, with participation from existing seed investors. The company will use the funds to expand its AI routing platform to mid-market freight forwarders and double its engineering team.",
         "Northwind announced a $15M Series A led by Cobalt Ridge Ventures in February 2026, earmarked for mid-market expansion and doubling engineering.",
         "a $15 million Series A round led by Cobalt Ridge Ventures", "high", "funding"),
        ("Northwind Labs acquires route-planning startup Routely",
         "https://freightweekly.example/northwind-acquires-routely", "2025-11-18",
         "Northwind Labs has acquired Routely, a seven-person route-planning startup, in an all-stock deal. Routely's founders will join Northwind's optimisation team, and the deal gives Northwind a multi-stop planning engine it had been building in-house.",
         "Northwind acquired the seven-person startup Routely in an all-stock deal, gaining a multi-stop planning engine.",
         "Northwind Labs has acquired Routely, a seven-person route-planning startup, in an all-stock deal", "medium", "acquisition"),
        ("Northwind launches Copilot, a natural-language dispatcher assistant",
         "https://logisticstechdaily.example/northwind-copilot", "2026-04-22",
         "Northwind Labs launched Northwind Copilot on Tuesday, an assistant that lets dispatchers reassign loads and re-route trucks using plain English. The launch positions the company directly against Parcelmind, which introduced a similar assistant last year, and incumbent Fleetwise.",
         "Northwind launched Copilot, a plain-English dispatcher assistant, putting it in direct competition with Parcelmind and Fleetwise.",
         "lets dispatchers reassign loads and re-route trucks using plain English", "medium", "product"),
        ("Harborline Freight picks Northwind for network-wide route optimisation",
         "https://harborline.example/press/northwind-partnership", "2026-06-05",
         "Harborline Freight will deploy Northwind's platform across its 40 regional terminals, replacing a legacy planning tool. The multi-year agreement is Northwind's largest enterprise contract to date.",
         "Harborline Freight is rolling Northwind out across 40 terminals in a multi-year deal described as Northwind's largest enterprise contract.",
         "across its 40 regional terminals, replacing a legacy planning tool", "high", "partnership"),
    ],
    "company": [
        ("Northwind Labs company profile",
         "https://startupledger.example/companies/northwind-labs", "2026-02-12",
         "Northwind Labs closed an $18 million Series A in February 2026. Founded in 2023 and headquartered in Rotterdam, the company reports 62 employees.",
         "A company-profile database lists Northwind's February 2026 Series A at $18M.",
         "closed an $18 million Series A in February 2026", "medium", "funding"),
        ("Careers at Northwind Labs",
         "https://northwindlabs.example/careers", "2026-09-15",
         "We have 14 open roles: nine in machine learning and platform engineering, three in enterprise sales, and two in customer success. Two of the sales roles are based in Chicago and Atlanta.",
         "Northwind has 14 open roles: 9 in ML/platform engineering, 3 in enterprise sales (two of them in Chicago and Atlanta) and 2 in customer success.",
         "nine in machine learning and platform engineering, three in enterprise sales, and two in customer success. Two of the sales roles are based in Chicago and Atlanta", "high", "hiring"),
        ("About Northwind Labs",
         "https://northwindlabs.example/about", None,
         "Northwind Labs was founded in 2023 by Maya Okafor and Daan Visser. Its platform optimises routes and load assignments for freight forwarders in Europe.",
         "Northwind was founded in 2023 by Maya Okafor and Daan Visser and currently serves European freight forwarders.",
         "was founded in 2023 by Maya Okafor and Daan Visser", "high", "leadership"),
        ("Northwind Labs pricing",
         "https://northwindlabs.example/pricing", "2026-07-14",
         "Starting 14 July 2026, Northwind moves from per-seat licences to usage-based pricing, billed per optimised route. Existing customers keep per-seat terms until renewal.",
         "From 14 July 2026 Northwind switched from per-seat licences to usage-based pricing billed per optimised route.",
         "moves from per-seat licences to usage-based pricing, billed per optimised route", "high", "pricing"),
    ],
    "product": [
        ("Northwind Labs changelog: v3.2",
         "https://docs.northwindlabs.example/changelog", "2026-08-30",
         "v3.2 adds a multi-carrier routing API and EU data-residency controls in beta. Copilot now supports voice input for dispatchers.",
         "Release v3.2 added a multi-carrier routing API, EU data-residency controls (beta) and voice input for Copilot.",
         "v3.2 adds a multi-carrier routing API and EU data-residency controls in beta", "high", "product"),
        ("northwind-sdk releases",
         "https://github.example/northwind-labs/northwind-sdk/releases", "2026-05-12",
         "northwind-sdk 1.0 is now open source under the Apache 2.0 licence. The release includes Python and TypeScript clients and a sandbox simulator for testing routing logic.",
         "Northwind open-sourced northwind-sdk 1.0 (Apache 2.0) with Python and TypeScript clients and a routing simulator.",
         "northwind-sdk 1.0 is now open source under the Apache 2.0 licence", "high", "product"),
        ("Northwind Copilot on Product Hunt",
         "https://producthunt.example/posts/northwind-copilot", "2026-04-23",
         "Northwind Copilot finished the day at #3 with 412 upvotes. Commenters liked the plain-English dispatching but asked about integrations with older TMS software.",
         "Copilot's Product Hunt launch drew positive reaction, with requests for legacy TMS integrations.",
         "Commenters liked the plain-English dispatching but asked about integrations with older TMS software", "medium", "product"),
    ],
    "social": [
        ("Onboarding with Northwind took 6 weeks, anyone else?",
         "https://reddit.example/r/logistics/comments/x1", "2026-07-02",
         "We signed with Northwind in May and onboarding took six weeks, mostly because of data cleanup on our side and slow support replies. Routing quality has been great since go-live.",
         "One customer reports a six-week onboarding, partly blamed on slow support replies, but praises routing quality.",
         "onboarding took six weeks, mostly because of data cleanup on our side and slow support replies", "low", "sentiment"),
        ("Northwind Labs reviews",
         "https://g2.example/products/northwind-labs/reviews", "2026-09-01",
         "Northwind Labs holds a 4.6 out of 5 rating across 87 reviews. Reviewers praise route accuracy and say it beats Fleetwise on setup flexibility but trails Parcelmind on reporting.",
         "Northwind averages 4.6/5 across 87 reviews; reviewers rank it above Fleetwise on flexibility but below Parcelmind on reporting.",
         "holds a 4.6 out of 5 rating across 87 reviews", "medium", "sentiment"),
        ("Thread: anyone using EU-only data residency?",
         "https://x.example/logisticsops/status/123", "2026-08-11",
         "Several dispatch managers on the thread say they would switch to Northwind if EU-only data residency became generally available.",
         "Dispatch managers say EU-only data residency being generally available would trigger switching to Northwind.",
         "would switch to Northwind if EU-only data residency became generally available", "low", "sentiment"),
    ],
}

PLAN = {
    "company": COMPANY,
    "questions": [
        {"id": "q1", "role": "news", "priority": 1, "question": "What announcements, partnerships or acquisitions has Northwind Labs made in the last 18 months?"},
        {"id": "q2", "role": "news", "priority": 1, "question": "Which competitors does Northwind Labs face and how is it positioned against them?"},
        {"id": "q3", "role": "company", "priority": 1, "question": "How much has Northwind Labs raised, from whom, and when?"},
        {"id": "q4", "role": "company", "priority": 2, "question": "What do open roles and pricing changes reveal about Northwind's priorities?"},
        {"id": "q5", "role": "product", "priority": 1, "question": "What has Northwind shipped recently and what direction does it signal?"},
        {"id": "q6", "role": "product", "priority": 3, "question": "What is Northwind's developer and open-source footprint?"},
        {"id": "q7", "role": "social", "priority": 2, "question": "How do customers perceive Northwind and what do they complain about?"},
    ],
}

REPORT = {
    "executive_summary": "Northwind Labs is a young European AI routing vendor that is moving upmarket. Since late 2025 it has acquired a planning startup, raised a Series A, shipped a natural-language Copilot, and landed its largest enterprise deal. Hiring for US enterprise sales and a switch to usage-based pricing suggest an expansion push beyond Europe. Customer sentiment is strong on routing quality but shows friction in onboarding and reporting. Reports of the Series A size conflict ($15M vs $18M); the company's own press release is the more credible figure.",
    "timeline": [
        {"date": "2025-11-18", "title": "Acquires Routely", "description": "All-stock acquisition of a seven-person route-planning team, adding a multi-stop planning engine.", "category": "acquisition", "evidence_ids": ["N2"]},
        {"date": "2026-02-10", "title": "Announces Series A", "description": "Round led by Cobalt Ridge Ventures to expand to mid-market forwarders and double engineering.", "category": "funding", "evidence_ids": ["N1", "C1"]},
        {"date": "2026-04-22", "title": "Launches Northwind Copilot", "description": "Plain-English dispatcher assistant, directly challenging Parcelmind and Fleetwise; well received on Product Hunt.", "category": "product", "evidence_ids": ["N3", "P3"]},
        {"date": "2026-05-12", "title": "Open-sources northwind-sdk 1.0", "description": "Apache 2.0 SDK with Python and TypeScript clients and a routing simulator.", "category": "product", "evidence_ids": ["P2"]},
        {"date": "2026-06-05", "title": "Signs Harborline Freight", "description": "Multi-year deployment across 40 terminals, its largest enterprise contract so far.", "category": "partnership", "evidence_ids": ["N4"]},
        {"date": "2026-07-14", "title": "Moves to usage-based pricing", "description": "Per-seat licences replaced by per-optimised-route billing; existing customers grandfathered until renewal.", "category": "pricing", "evidence_ids": ["C4"]},
        {"date": "2026-08-30", "title": "Ships v3.2", "description": "Multi-carrier routing API, EU data-residency controls (beta) and voice input for Copilot.", "category": "product", "evidence_ids": ["P1"]},
    ],
    "strategy": [
        {"statement": "Moving upmarket from European mid-market forwarders to large enterprise networks.", "evidence_ids": ["N1", "N4", "C3"]},
        {"statement": "Building a defensible AI layer by combining an acquired planning engine, Copilot, and an open SDK that seeds an ecosystem.", "evidence_ids": ["N2", "N3", "P2"]},
        {"statement": "Aligning revenue with customer value through usage-based pricing (inferred; no revenue data available).", "evidence_ids": ["C4"]},
        {"statement": "Likely preparing a US push: enterprise sales roles in Chicago and Atlanta alongside fresh funding (inference, not announced).", "evidence_ids": ["C2", "N1"]},
    ],
    "swot": {
        "strengths": [
            {"point": "Strong routing accuracy reputation and a 4.6/5 review average.", "evidence_ids": ["S2", "S1"]},
            {"point": "Marquee enterprise reference in Harborline Freight.", "evidence_ids": ["N4"]},
            {"point": "Fast shipping cadence across API, SDK and Copilot.", "evidence_ids": ["P1", "P2", "N3"]},
        ],
        "weaknesses": [
            {"point": "Onboarding can take weeks and support replies are described as slow.", "evidence_ids": ["S1"]},
            {"point": "Reviewers rate reporting below Parcelmind.", "evidence_ids": ["S2"]},
            {"point": "Limited legacy TMS integrations, raised at the Copilot launch.", "evidence_ids": ["P3"]},
        ],
        "opportunities": [
            {"point": "EU data residency, once generally available, could unlock switching demand.", "evidence_ids": ["S3", "P1"]},
            {"point": "Open SDK and multi-carrier API can attract partners and integrators.", "evidence_ids": ["P1", "P2"]},
        ],
        "threats": [
            {"point": "AI-first rival Parcelmind already ships a comparable assistant.", "evidence_ids": ["N3", "S2"]},
            {"point": "Incumbent Fleetwise competes on installed base.", "evidence_ids": ["N3", "S2"]},
            {"point": "Pricing change may create churn risk at renewal for per-seat customers.", "evidence_ids": ["C4"]},
        ],
    },
    "competitors": [
        {"name": "Parcelmind", "threat_level": "high", "rationale": "AI-first rival with a comparable assistant released a year earlier and stronger reporting per reviewers.", "evidence_ids": ["N3", "S2"]},
        {"name": "Fleetwise", "threat_level": "medium", "rationale": "Incumbent with installed base; reviewers say Northwind is more flexible to set up.", "evidence_ids": ["N3", "S2"]},
    ],
    "contradictions": [
        {"topic": "Series A amount ($15M vs $18M)", "evidence_ids": ["N1", "C1"],
         "claims": [{"evidence_id": "N1", "claim": "Company press release: $15M Series A."},
                    {"evidence_id": "C1", "claim": "Database profile: $18M Series A."}],
         "resolution": "Treat $15M as the working figure: it comes from the company's own dated release (primary source), while the $18M profile is a secondary aggregator two days later. A later extension cannot be ruled out.",
         "status": "resolved"},
        {"topic": "Customer experience: high ratings vs slow onboarding", "evidence_ids": ["S1", "S2"],
         "claims": [{"evidence_id": "S2", "claim": "4.6/5 across 87 reviews."}, {"evidence_id": "S1", "claim": "Six-week onboarding with slow support."}],
         "resolution": "Not strictly incompatible, but one anecdote cannot be weighed against 87 reviews. Needs more onboarding data.",
         "status": "unresolved"},
    ],
    "gaps": ["No verified revenue, customer count or churn data.", "Harborline contract value and terms are not disclosed.", "No independent confirmation of the planned US expansion."],
}


def _sleep(a: float) -> None:
    time.sleep(a)


class DemoSearch:
    """Drop-in for MultiSearch returning the synthetic corpus."""

    def __init__(self, delay: float = 0.35):
        self.delay = delay
        self.errors: list[str] = []
        self.providers = []

    def search(self, query: str, *, topic: str = "general", max_results: int = 6, hint: str = "") -> list[SearchResult]:
        _sleep(self.delay)
        return [SearchResult(title=t, url=u, content=c, date=d, provider="demo")
                for (t, u, d, c, *_rest) in DOCS.get(hint, [])]


class DemoLLM(BaseLLM):
    name = "demo"

    def __init__(self, delay: float = 1.0):
        self.delay = delay

    def complete_json(self, *, task, system, user, fast=False, max_tokens=4000):
        _sleep(self.delay * (1.8 if task == "critic" else 1.0))
        if task == "plan":
            return PLAN
        if task.startswith("research:"):
            role = task.split(":", 1)[1]
            return {
                "findings": [
                    {"question_id": "", "source": i + 1, "claim": claim, "snippet": snip, "date": date,
                     "confidence": conf, "category": cat}
                    for i, (_t, _u, date, _c, claim, snip, conf, cat) in enumerate(DOCS.get(role, []))
                ],
                "gaps": [],
            }
        if task == "critic":
            return REPORT
        return {}
