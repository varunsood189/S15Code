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
- [x] Five proofs live: p1 (prior run1), p2/p3/p4/p7 (`--label part1`)
- [x] Four runs documented in `docs/part1_evidence.md`
- [x] One honest limitation (content-off traces + projected vs measured spread)
- [x] Evidence draft committed + pushed

### Step 2 — Part 2: policy + measure
- [x] Own task file (≥15), not shipped `mixed.jsonl`
- [x] Policy edits in `config/tiers.yaml` + `config/budgets.yaml`
- [x] Live `p1_cost_per_task.py --tasks proofs/tasks/my_domain.jsonl`
- [x] Report cost/call, cost/resolved vs always-frontier
- [x] Break-even resolution rate r*
- [x] One wrong policy choice + cost analysis
- [x] Commit + push

### Step 3 — Part 3: attack the budget
- [x] Adversarial run against our principal/policy
- [x] Spend before control vs refusal after
- [x] Refusal visible in telemetry
- [x] Commit + push

### Step 4 — Package
- [x] README Evidence section complete with reproduce commands
- [x] No secrets in PR
- [ ] Open PR (branch pushed; `gh` needs auth — open via
  https://github.com/varunsood189/S15Code/pull/new/assignment/s15-policy-evidence )

## Push cadence

Each step ends with a focused commit and `git push` so reviewers can see incremental work.
