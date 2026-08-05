# Part 2 — Policy measurement (systems/ops domain)

Source: `proofs/out/p1_cost_per_task_my_domain_live.json` (**live**).
Policy: [`docs/part2_policy.md`](part2_policy.md). Tasks: `proofs/tasks/my_domain.jsonl` (15).

## Cost per call and cost per resolved task

| Strategy | Spend | Calls | Cost/call | Resolved | Cost/resolved |
|---|---:|---:|---:|---:|---:|
| A: always_frontier | $0.02041600 | 14 | $0.00145829 | 13/15 | $0.00157046 |
| B: always_cheapest | $0.00335985 | 18 | $0.00018666 | 14/15 | $0.00023999 |
| C: budget_aware | $0.00310545 | 16 | $0.00019409 | 15/15 | $0.00020703 |

### Raw facts

- A: spend 0.02041600 USD  calls 14  cost/call 0.00145829  resolved 13/15  cost/resolved 0.00157046  tiers frontier
- B: spend 0.00335985 USD  calls 18  cost/call 0.00018666  resolved 14/15  cost/resolved 0.00023999  tiers economy
- C: spend 0.00310545 USD  calls 16  cost/call 0.00019409  resolved 15/15  cost/resolved 0.00020703  tiers economy,standard
- Judge meta-cost: 53 calls, 0.01601790 USD, 7 unusable, 58 transport retries, 18 verdicts reused
- Signature failure mode: OBSERVED — {"B_vs_A": {"cost_per_call_delta_pct": -87.20015347439917, "cost_per_resolved_task_delta_pct": -84.7185505765786, "resolution_rate": {"B": 0.9333333333333333, "A": 0.866...

## Break-even resolution rate

- Measured B vs A break-even resolution rate r*: **0.2881**
- B resolution rate: **0.9333**
- Headroom above break-even: **0.6452**
- Cheaper per call: True; dearer per resolved task: False

Interpretation: if B's resolution rate falls below r*, its cost per resolved task exceeds always-frontier despite cheaper calls.

### B vs C (cascade)

- Signature failure mode (cheaper/call, dearer/resolved): **True**
- Break-even r* B vs C: **0.9649**
- B resolution 0.9333333333333333 vs C 1.0

## A case the policy got wrong

- **Task:** `sys_14_logic_puzzle`
- **Why wrong:** always-frontier failed while the budget-aware path resolved — the price ladder is not a competence ranking on this task
- **Budget-aware path:** $0.00018375 / 1 calls / tiers ['economy']
- **Compared strategy cost:** $0.00000000

Strategy disagreements A vs B (count=1): first three:

- {"task_id": "sys_14_logic_puzzle", "difficulty": "hard", "resolved_by": "B", "failed_for": "A", "winner": {"tiers": ["economy"], "attempts": 1, "cost": 0.00018375000000000002, "overall": 1.0}, "loser"

## Reproduce

```bash
export GLC_BASE_URL=http://127.0.0.1:8111
uv run python proofs/p1_cost_per_task.py \
  --tasks proofs/tasks/my_domain.jsonl \
  --budget 0.05 --principal varun/s15-domain \
  --label my_domain_live
uv run python proofs/extract_part2.py --label my_domain_live
```
