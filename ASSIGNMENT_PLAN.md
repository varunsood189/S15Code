# Session 15 Assignment Plan

Build a routing + budget policy for a chosen workload and prove what it costs.
Submit a PR to this fork with policy, task file, and an Evidence section in the README.

## Scoring targets

| Area | Points |
|---|---|
| Measured cost per resolved task | 25 |
| Proof quality / reproducibility | 25 |
| Budget enforcement under attack | 20 |
| Observability (traces, refusals) | 15 |
| A case the policy got wrong | 10 |
| Simple enough to operate | 5 |

## Workload

Domain: **systems / platform operations** (`proofs/tasks/my_domain.jsonl`, 15 tasks).
Ladder: economy (Groq gpt-oss-120b) → standard (Gemini flash-lite) → frontier (gpt-4.1 via OpenRouter).

## Step checklist

### Step 0 — Hygiene
- [x] Clone / workspace ready (`glc_v4` + `S15Code`)
- [x] Both pytest suites green (S15Code 277; glc_v4 448 passed / 8 skipped)
- [x] Jaeger + gateway `:8111` + agent `:8113` up (OTEL → `:4318`)
- [x] `GLC_BASE_URL=http://127.0.0.1:8111` (never 8112)
- [x] Frontier provider decision documented (OpenRouter for gpt-4.1)

### Step 1 — Part 1: reproduce the floor
- [ ] Five proofs live: p1, p2, p3, p4, p7
- [ ] Four runs documented: prompt, tier/model, event trace, Jaeger ID, ledger, answer
- [ ] One honest limitation
- [ ] Evidence draft committed + pushed

### Step 2 — Part 2: policy + measure
- [x] Own task file (≥15), not shipped `mixed.jsonl`
- [ ] Policy edits in `config/tiers.yaml` + `config/budgets.yaml`
- [ ] Live `p1_cost_per_task.py --tasks proofs/tasks/my_domain.jsonl`
- [ ] Report cost/call, cost/resolved vs always-frontier
- [ ] Break-even resolution rate \(r^*\)
- [ ] One wrong policy choice + cost analysis
- [ ] Commit + push

### Step 3 — Part 3: attack the budget
- [ ] Adversarial run against our principal/policy
- [ ] Spend before control vs refusal after
- [ ] Refusal visible in telemetry
- [ ] Commit + push

### Step 4 — Package
- [ ] README Evidence section complete with reproduce commands
- [ ] No secrets in PR
- [ ] Open PR

## Push cadence

Each step ends with a focused commit and `git push` so reviewers can see incremental work.
