# Submission kit

## Checklist
- [ ] Registered on the hackathon page before **Oct 13, 00:00 UTC**; joined the Discord
- [ ] Keys added; `python -m evals.run_evals --depth quick` run; results copied into `docs/FAILURE_MODES.md`
- [ ] 2–3 real reports generated (one well-known, one mid-stage, one early-stage) and committed from `reports/`
- [ ] Public GitHub repo with README and architecture diagram
- [ ] Public Streamlit URL tested from another device and network
- [ ] 3–4 minute demo video recorded
- [ ] Form submitted before **Oct 20, 2026, 23:45 UTC** (aim for a day early)
- [ ] Team size 1–5 and eligibility rules re-read

## Demo video script (about 3:30)
| Time | Show | Say |
|---|---|---|
| 0:00 | Landing page | Founders and BD teams spend hours piecing together what a competitor is doing. Scout does the investigation in minutes. |
| 0:20 | Type a company you did not prepare, press Investigate | I picked this company just now, so nothing is pre-baked. |
| 0:30 | Pipeline lighting up, log scrolling | A planner splits the question; four researchers run in parallel; each query is visible. |
| 1:15 | Overview tab: summary, stats, evidence audit | Every claim carries a source and a quote. Scout checks the quote exists in the page it fetched, and drops what it cannot verify. |
| 1:50 | Timeline, open a citation | Each move links to the evidence, with date and confidence. |
| 2:20 | Conflicts tab | Two sources disagreed. Scout shows both and says which is more credible and why. |
| 2:50 | Strategy and SWOT | Strategy is inference, labelled with its evidence and confidence. |
| 3:10 | Evals and failure modes in the repo | Ten test cases including a fake company. Scout correctly reports "not enough evidence". |
| 3:25 | Close | Investigate. Connect. Recommend. |

## Form copy

**Problem.** Competitive research is scattered across news, job boards, changelogs and forums. Small teams either skip it or rely on a chatbot summary they cannot trust.

**Solution.** Scout is an autonomous multi-agent investigator. A planner breaks a company into research questions; four specialist researchers work in parallel over news, company data, product releases and public sentiment; a critic cross-checks the findings, flags conflicting evidence, and writes a report where every claim is cited and confidence-scored. A quote verifier rejects any citation that does not appear in the retrieved source.

**Track fit (Autonomous Intelligence).** Multi-step investigation over several data sources, parallel orchestration (LangGraph), conflict detection, evidence-backed synthesis, graceful error recovery, an evaluation suite, and documented failure modes.

**Stack.** LangGraph, Claude/OpenAI, Tavily/Brave/Serper, Streamlit, pytest.
