# Part 2 policy — systems / platform operations

## Workload

`proofs/tasks/my_domain.jsonl` — 15 tasks (5 trivial / 5 moderate / 5 hard):
ports, units, CAP, CIDR, SLO math, Raft quorum, latency composition, cost
trade-offs. Success is exact short answers, not long essays.

## Ladder (unchanged shape, OpenRouter frontier)

| Rung | Provider | Model | Intent |
|---|---|---|---|
| economy | groq | openai/gpt-oss-120b | Cheap first for short factual ops answers |
| standard | gemini | gemini-3.1-flash-lite | Mid rung when economy is unresolved |
| frontier | openrouter | openai/gpt-4.1 | Last resort / always-frontier baseline |

Each rung is a **different model on a different provider**. Budget pressure must
change the model, not only `max_tokens`.

## Budget thresholds (`config/budgets.yaml`)

| Knob | Value | Why for this workload |
|---|---|---|
| `default_budget` | 0.05 | Per-task ceiling for p1; enough for one frontier call or several economy retries |
| `downgrade_at` | 0.45 | Start walking the ladder earlier than the stock 0.50 so spend pressure bites mid-cascade |
| `refuse_at` | 0.88 | Hard stop before total exhaustion; leaves a little room for final ledger noise |
| `reserve_fraction` | 0.20 | Keep allowance for the answering node |
| `max_calls_per_run` | 48 | Denial-of-wallet bound tighter than the stock 60 for this FAQ-like set |
| `max_calls_per_node` | 6 | Cap retries on one node |
| principal `varun/s15-domain` | 0.05 | Named principal for reproducible Part 2/3 evidence |

## Role tiers (`config/tiers.yaml`)

Ops retrieval / formatting roles stay on **economy**. The answering role
`answer_with_evidence` still **requests frontier**; the controller may downgrade
when the projected frontier call no longer fits.

## What we will measure

Against always-frontier (strategy A):

1. cost per call and cost per resolved task (A / B / C)
2. break-even resolution rate \(r^*\) for B vs A from the measured price ratio
3. at least one task where the budget-aware cascade chose wrongly (escalated and
   overspent, or landed on a wrong expensive answer)

Judge: shipped generic rubric panel in `config/evals.yaml` (not self-judged).
