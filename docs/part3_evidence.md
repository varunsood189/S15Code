# Part 3 — Attack the budget policy

Principal under test: `varun/s15-domain` (see `config/budgets.yaml` and
`docs/part2_policy.md`). Call ceiling from policy: `max_calls_per_run: 48`.

## Attack 1 — Unbounded planner loop (p3)

```bash
export GLC_BASE_URL=http://127.0.0.1:8111
uv run python proofs/p3_denial_of_wallet.py \
  --task "Calculate Raft quorum for 9 nodes and explain in one sentence." \
  --budget 0.001 \
  --principal varun/s15-domain \
  --label part3
```

| Metric | With controller |
|---|---:|
| Ceiling | $0.001 |
| Spent | $0.00059070 |
| Admitted calls | 11 |
| Refusals | 189 |
| Loop rounds that kept asking | 200 |
| Visible refusal type | `BudgetRefused` graph failures |
| Uncontrolled bill (extrapolated) | ~$0.537 over 10k rounds |

**Before control (counterfactual):** the same loop would keep calling; extrapolated
uncontrolled bill ≈ $0.54 over 10k rounds at the measured cost/call.

**After control:** spend flattened at $0.00059 ≤ $0.001; 189 requests refused;
the loop itself never became careful — the controller stopped the spend.

Source: `proofs/out/p3_denial_of_wallet_part3.json` (live, `ok: true`).

## Attack 2 — Unaffordable run (agent HTTP)

```bash
curl -s -X POST http://127.0.0.1:8113/v1/agent/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Explain Raft quorum for 9 nodes in one sentence.",
    "budget":0.0000005,
    "tenant_id":"varun","project_id":"s15-domain",
    "user_id":"part3","agent_id":"assistant"
  }'
```

Observed:

| Field | Value |
|---|---|
| status | `failed` |
| spent | `$0.00` |
| calls | `0` |
| refusals | `1` |
| refusal reason | cheapest tier `economy` projects ~`$0.000437`, run holds ~`$0.0000005` |
| requested tier | `frontier` (role `answer_with_evidence`) → refused before any provider call |

The refusal is visible in the run budget ledger (`refusal_log`), not a silent
empty answer.

## What this proves

1. A runaway loop against our principal cannot breach the dollar ceiling.
2. An explicitly unaffordable request is refused **before** the provider is
   contacted (`spent = 0`, `calls = 0`).
3. Refusals are observable outcomes (`BudgetRefused` / `refusal_log`), matching
   the session rule that a control which prevents work must still leave a trace
   of the prevention.
