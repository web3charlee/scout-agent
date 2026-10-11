# Failure modes

Status key: **Mitigated** (code handles it, covered by a test), **Known** (still happens, documented).
Replace the "Observed" column with your own numbers after running `python -m evals.run_evals`.

| # | Failure | Why it happens | Status | What Scout does |
|---|---|---|---|---|
| 1 | Model invents a quote | LLMs paraphrase while claiming to quote | Mitigated (`test_hallucinated_quotes_and_ids_are_rejected`) | Quote must be present in the retrieved text or the finding is dropped. |
| 2 | Model cites a source or ID that does not exist | Index slips | Mitigated (same test, `test_critic_drops_unsupported_items`) | Source numbers map to real URLs; unknown IDs are removed and counted in the audit. |
| 3 | Same fact, different numbers across sources | Aggregators lag, round extensions | Mitigated (`test_numeric_conflict_safety_net`) | Shown on the Conflicts tab; Critic explains which source is more credible, or marks it unresolved. |
| 4 | Search APIs fail or rate-limit | Outages, free-tier limits | Mitigated | Retries, fallback provider, circuit breaker, cache. |
| 5 | Whole LLM provider down | Outage | Mitigated (`test_total_llm_outage_degrades_gracefully`) | Fallback provider; otherwise a report that states nothing could be established. |
| 6 | Unknown company | Nothing to find | Mitigated (eval e10 negative control) | Sparse report with gaps; no invented findings. |
| 7 | Name collision (e.g. "Linear", "Notion") | Search returns other entities | **Known** | Pass a website URL to anchor the company. Planner adds the domain for company-data queries. |
| 8 | Stale or undated sources | Many pages carry no date | **Known** | Findings show "undated"; recency only nudges score slightly. |
| 9 | Snippet-level evidence only | Search results are short extracts, not full pages | **Known** | Quotes are verified against what was retrieved, so a true claim can be missed. A page-fetch step is the obvious next improvement. |
| 10 | Strategy is inference | Critic connects dots | **Known** | Strategy items are labelled with the evidence behind them and a confidence; no revenue or private data is claimed. |
| 11 | Social sentiment is anecdotal | Few posts retrievable via web search | **Known** | Social findings are usually low or medium confidence by design. |
| 12 | English, tech-company bias | Scope was kept narrow on purpose | **Known** | Quality drops for non-English or non-tech companies. |
