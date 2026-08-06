# Session 15 Assignment Report

**Routing, Agent Economics & Observability**  
Workload: systems / platform operations  
Branch: [`assignment/s15-policy-evidence`](https://github.com/varunsood189/S15Code/tree/assignment/s15-policy-evidence)

This report is the reader-friendly version of the assignment. Technical reproduce
commands and raw proof JSON live in the [README](../README.md) and under
[`docs/`](.).

---

## In one paragraph

We built a three-rung model ladder and a hard budget policy for short ops-style
questions (ports, CAP, Raft, SLO math, and similar). Against an always-frontier
baseline, a budget-aware cascade resolved **all 15 tasks** at about **$0.00021**
per resolved task — roughly **7.5× cheaper** than always using frontier, which
also failed two hard tasks. Under a denial-of-wallet attack, spend stopped under
the ceiling and every refusal showed up as a visible `BudgetRefused` failure.
The main lesson: **price does not rank competence** on your own traffic.

---

## What we built

### Workload (15 tasks)

File: [`proofs/tasks/my_domain.jsonl`](../proofs/tasks/my_domain.jsonl)

| Difficulty | Examples |
|---|---|
| Trivial (5) | HTTPS port, GB→MB, HTTP 404, CAP letters |
| Moderate (5) | `/28` usable IPs, SLO downtime, rolling-update finish time |
| Hard (5) | Request latency composition, Raft quorum, cost trade-off, dependency blast radius |

Success means a **short, exact** answer — not a long essay.

### Model ladder

| Rung | Provider | Model | Role |
|---|---|---|---|
| **Economy** | Groq | `openai/gpt-oss-120b` | Cheap first try |
| **Standard** | Gemini | `gemini-3.1-flash-lite` | Escalate if economy fails |
| **Frontier** | OpenRouter | `openai/gpt-4.1` | Last resort / baseline |

Each rung is a **different model on a different provider**. Budget pressure
changes the model, not only `max_tokens`.

### Budget policy

Config: [`config/budgets.yaml`](../config/budgets.yaml)

| Setting | Value | Intent |
|---|---|---|
| Default / principal ceiling | $0.05 | Enough for one frontier call or several cheap retries |
| Downgrade when spend ratio ≥ | 0.45 | Feel pressure earlier than the stock 0.50 |
| Refuse when spend ratio ≥ | 0.88 | Hard stop before total exhaustion |
| Max calls per run | 48 | Denial-of-wallet bound |
| Principal | `varun/s15-domain` | Named identity for reproducible proofs |

The answering role still *asks for* frontier; the controller may downgrade or
refuse **before** the provider is contacted.

### How we judged “resolved”

Generic rubric in `config/evals.yaml` (not an answer key):

- Overall score ≥ **0.75**
- No criterion below **0.5**
- Judge panel is **separate** from the answering ladder (no self-grading)

---

## Part 1 — Reproduce the floor

We ran both test suites and the five live proofs (`p1`–`p4`, `p7`).

**Shared prompt**

> In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt.

### Four captured runs

#### Run 1 — Budget holds (`p2`)

| Ceiling | What happened | Cost |
|---|---|---|
| Generous | Served **frontier** / `gpt-4.1` | $0.000880 |
| Declared $0.02 | Asked frontier → **downgraded** to standard / flash-lite | $0.000147 |
| Impossible | **Refused** — 0 provider calls | $0.000000 |

#### Run 2 — Trace in Jaeger (`p4`)

| Field | Value |
|---|---|
| Tier / model | standard / `gemini-3.1-flash-lite` |
| Span hierarchy | `run → agent_loop → plan → node → provider_call` |
| Jaeger trace ID | `8dc106ed11679e05139688a3e4b21b7b` |
| Ledger check | Span costs **exactly** match ledger (**$0.000147**, delta 0) |

#### Run 3 — Cross-model ladder (`p7`)

Every rung answered with a different model.  
List-price projected spread ≈ **84×**; **measured** bill spread ≈ **6.6×**.

#### Run 4 — Live agent answer

With a $0.02 ceiling, frontier was too expensive to project, so the controller
served standard. Final answer (abbreviated):

> Enforcing a budget in code ensures constraints are applied consistently…  
> Relying solely on a prompt is insufficient because natural language
> instructions can be overridden…

### Honest limitation

Traces hide prompt and completion text by default (PII). You can see **cost,
model, tokens, and hierarchy**, but not *why* an answer was wrong, unless you
keep the run response or turn content capture on deliberately.

Also: trusting the **price page** over **measured bills** mis-ranks the ladder —
84× on paper became ~6–8× on this prompt.

Full detail: [`part1_evidence.md`](part1_evidence.md)

---

## Part 2 — Policy and measurement

We compared three strategies on the **same 15 tasks** (live gateway):

| Strategy | Meaning |
|---|---|
| **A** | Always frontier |
| **B** | Always cheapest, retry up to 3 times |
| **C** | Our budget-aware cascade (start cheap, escalate if needed) |

### Results

| Strategy | Cost / call | Resolved | Cost / resolved task |
|---|---:|---:|---:|
| A — always frontier | $0.001458 | 13 / 15 | $0.001570 |
| B — always cheapest | $0.000187 | 14 / 15 | $0.000240 |
| **C — our policy** | **$0.000194** | **15 / 15** | **$0.000207** |

**Takeaway:** our policy finished every task and was about **7.5× cheaper per
resolved task** than always-frontier.

### Break-even resolution rate

For B vs A, the measured break-even rate **r\*** ≈ **0.288**.  
B actually resolved **93%** of tasks, so it sits **well above** the break-even
line (headroom ≈ +0.65). On this wide ladder, cheap calls stay economical
unless the cheap model fails most of the time.

Against the cascade (B vs C), the classic trap *does* appear: B is slightly
cheaper per call but **more expensive per resolved task**, because C finishes
the last hard task that B keeps failing.

### Where the policy / ladder went wrong

**Task:** `sys_14_logic_puzzle` (microservice dependency blast radius)

| Path | Outcome | Cost |
|---|---|---|
| Always frontier (A) | **Failed** | $0 (no usable resolution) |
| Economy / our cascade (C) | **Resolved** | **$0.000184** (1 call) |

So the expensive rung was the wrong choice. Price order ≠ competence order.

**Related:** on `sys_15_econ_tradeoff`, frontier spent **$0.007638** and still
failed; the cascade escalated economy → standard and resolved for **$0.001377**.

Full detail: [`part2_evidence.md`](part2_evidence.md) · policy notes: [`part2_policy.md`](part2_policy.md)

---

## Part 3 — Attack our budget

### Attack 1 — Runaway loop

200 loop rounds against principal `varun/s15-domain` with a **$0.001** ceiling.

| | Without a hard controller (extrapolated) | With our controller (measured) |
|---|---:|---:|
| Spend | ~$0.54 over 10k rounds | **$0.000591** (under ceiling) |
| Behaviour | Keeps calling forever | **11** calls admitted, **189** refused |
| Visibility | — | Each refusal is a **`BudgetRefused`** graph failure |

The loop never became careful. **The controller** stopped the spend.

### Attack 2 — Unaffordable request

Agent run with budget `$0.0000005`:

| Field | Result |
|---|---|
| Status | `failed` |
| Spent | **$0** |
| Provider calls | **0** |
| Refusals | **1** |
| Why | Even economy projected ~$0.000437 > remaining |

Refused **before** any provider call. Visible in `budget.refusal_log`.

Full detail: [`part3_evidence.md`](part3_evidence.md)

---

## How to reproduce

Start Jaeger, `glc_v4` on `:8111`, and `s15code` on `:8113`, then:

```bash
export GLC_BASE_URL=http://127.0.0.1:8111
export S15_OTEL_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces

# Part 1 proofs (example)
TASK="In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt."
uv run python proofs/p2_budget_holds.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1
uv run python proofs/p4_trace_export.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1 \
  --otel-endpoint http://localhost:4318/v1/traces
uv run python proofs/p7_cross_model_ladder.py --task "$TASK" --principal varun/part1 --label part1
uv run python proofs/p3_denial_of_wallet.py --task "$TASK" --budget 0.002 --principal varun/part1 --label part1

# Part 2 measurement
uv run python proofs/p1_cost_per_task.py \
  --tasks proofs/tasks/my_domain.jsonl \
  --budget 0.05 --principal varun/s15-domain --label my_domain_live

# Part 3 attack
uv run python proofs/p3_denial_of_wallet.py \
  --task "Calculate Raft quorum for 9 nodes and explain in one sentence." \
  --budget 0.001 --principal varun/s15-domain --label part3
```

More commands: [README → Assignment evidence](../README.md#assignment-evidence)

---

## Bottom line

1. **Cost per resolved task** is the number that matters — not cost per call.
2. A budget is real only when code can **refuse before** the provider call.
3. Traces + ledger must agree; refusals must be **visible**.
4. On our ops set, the cheapest rung often won; frontier failed tasks that
   economy solved. **Measure your own traffic.**

---

## Axiom submission links

| Part | Public link |
|---|---|
| 1 | https://github.com/varunsood189/S15Code/blob/assignment/s15-policy-evidence/README.md#part-1--reproduce-the-floor |
| 2 | https://github.com/varunsood189/S15Code/blob/assignment/s15-policy-evidence/README.md#part-2--policy-and-measurement |
| 3 | https://github.com/varunsood189/S15Code/blob/assignment/s15-policy-evidence/README.md#part-3--attack-our-budget |
| This report | https://github.com/varunsood189/S15Code/blob/assignment/s15-policy-evidence/docs/ASSIGNMENT_REPORT.md |
