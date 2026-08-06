# S15Code — the budget-aware agent runtime

Session 15 of EAGV3. Hand a run a **ceiling** and a **principal**, and the agent
plans against them: every node declares the capability tier it needs, the
allowance is re-divided across the live frontier on every planning round, and a
controller admits, downgrades, branches or refuses each call before it is made.
The same durable event journal the graph already writes is then exported as
OpenTelemetry spans, with token usage and cost per span.

Two things are true no matter what the model does with its tokens:

- **No call is made without being metered.** The controller owns the transport;
  there is no code path to a provider that skips the ledger.
- **No run spends past its ceiling.** Enforcement is deterministic code. A budget
  asked for in a prompt leaks — models are token-elastic (TALE, 2026), so they
  sail past a tight ceiling while sincerely agreeing to it.

## One package

`S14Code` shipped two packages side by side, with the session's own work hidden
inside the previous session's namespace. This repo has **exactly one importable
package**, and nothing is nested inside a prior session's name.

```
S15Code/
├── s15code/
│   ├── main.py            FastAPI app factory
│   ├── cli.py             `s15code serve`
│   ├── routes.py          runs, facts, documents, memory search, trace
│   ├── a2a_routes.py      agent card + JSON-RPC
│   ├── gateway.py         the gateway client (never holds a credential)
│   ├── planner.py         the constrained GraphPatch proposal boundary
│   ├── runtime.py         one request through the live graph
│   ├── tools.py           the small non-browser skill surface
│   ├── core/
│   │   ├── live_graph/    executor, durable event journal, patches   (from S13)
│   │   ├── memory/        typed scoped memory, semantic chunking     (from S13)
│   │   └── a2a/           the agent-to-agent boundary                (from S13)
│   ├── ui/                catalog, validator, surface, AG-UI, HITL   (from S14)
│   ├── economics/         NEW — budget-aware planning
│   │   ├── config.py        loads the three YAML files
│   │   ├── pricing.py       per-model prices
│   │   ├── tiers.py         the capability ladder; a node declares a tier
│   │   ├── budget.py        allowance, spend, reservations, allocation
│   │   ├── policy.py        proceed / downgrade / branch / refuse
│   │   └── controller.py    the hard controller at the call seam
│   ├── telemetry/         NEW — the same journal, as OTel spans
│   │   └── spans.py         run → agent loop → plan → node → provider call
│   └── evals/             NEW — did the answer RESOLVE the task?
│       ├── config.py        the rubric, the bar and the judge panel, from YAML
│       ├── judge.py         LLM-as-judge on a generic, task-agnostic rubric
│       └── tasks.py         reads a task set; never contains one
├── config/                tiers.yaml · pricing.yaml · budgets.yaml · evals.yaml
├── proofs/                the generic proof harness
│   └── tasks/               task sets, as DATA a reviewer can replace
└── tests/
```

## The elegant reuse

The graph writes **one** durable journal. It now has three consumers, and no
parallel event system exists:

| Consumer | Reads the journal as |
|---|---|
| the executor | graph replay and crash recovery (S13) |
| `s15code.ui.agui` | AG-UI events for a browser (S14) |
| `s15code.telemetry.spans` | OpenTelemetry spans for a collector (S15) |

The controller writes each metered call into the node's own result, so the
journal carries tokens, cost, tier and the budget decision. Delete the
materialised graph and the trace still builds from the tape alone — `p4` checks
exactly that.

## Nothing is hardcoded

No tier name, model, provider, price, threshold or budget appears in Python.

| Decision | Lives in |
|---|---|
| what tiers exist, and what each expands to on the wire | `config/tiers.yaml` |
| which tier a graph role asks for | `config/tiers.yaml` → `role_tiers` |
| what a model costs, and cache-read discounts | `config/pricing.yaml` |
| default allowance, per-principal caps | `config/budgets.yaml` |
| downgrade / refuse ratios, reserve, call ceilings, token estimation | `config/budgets.yaml` |

`config/` is resolved from `S15_CONFIG_DIR` when set, otherwise from beside the
package. The unit tests build their **own** ladder with invented tier names, which
is the real check that the library never depends on the shipped ones.

## Run it

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run s15code serve            # http://127.0.0.1:8113
```

The gateway is a separate process on `http://127.0.0.1:8111` (`GLC_BASE_URL`).
S15Code holds no provider credential; copy `.env.example` to `.env` and set paths,
never keys.

A budgeted run over HTTP:

```bash
curl -s localhost:8113/v1/agent/runs -H 'content-type: application/json' -d '{
  "tenant_id": "acme", "project_id": "research", "user_id": "rohan",
  "prompt": "<any task>", "budget": 0.02
}' | jq '.budget'
```

The response carries a `budget` ledger (total, spent, remaining, pressure, every
charge, every refusal), the `allocations` the planner made each round, and the
`tier` each node declared. `GET /v1/agent/runs/{id}/trace` returns the same run as
a span tree.

Omit `budget` and the run behaves exactly as it did before economics existed —
the layer is additive.

## Assignment evidence

Session 15 assignment for a **systems / platform operations** workload.
Full write-ups also live under [`docs/`](docs/); the sections below are the
submission summary. Branch: `assignment/s15-policy-evidence`.

| Artifact | Path |
|---|---|
| Task file (15) | [`proofs/tasks/my_domain.jsonl`](proofs/tasks/my_domain.jsonl) |
| Ladder + roles | [`config/tiers.yaml`](config/tiers.yaml) |
| Budget policy | [`config/budgets.yaml`](config/budgets.yaml) |
| Part 1 detail | [`docs/part1_evidence.md`](docs/part1_evidence.md) |
| Part 2 detail | [`docs/part2_evidence.md`](docs/part2_evidence.md) |
| Part 3 detail | [`docs/part3_evidence.md`](docs/part3_evidence.md) |

### Part 1 — Reproduce the floor

Suites: S15Code pytest **277 passed**; glc_v4 **448 passed / 8 skipped**.
Five live proofs: `p1` (mixed), `p2`, `p3`, `p4`, `p7`.

Shared prompt for the four captured runs:

> In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt.

| Run | Tier / model | Event / span trace | Jaeger | Ledger | Final answer |
|---|---|---|---|---|---|
| 1 · p2 generous | `frontier` / `openai/gpt-4.1` | admit → call → charge (`run-fc4def9c17e7`) | (see run 2) | spent **$0.000880** | N/A (ledger proof) |
| 1b · p2 declared $0.02 | requested frontier → **downgraded** `standard` / `gemini-3.1-flash-lite` | same | (see run 2) | spent **$0.000147**; impossible ceiling → **1 refusal, $0** | N/A |
| 2 · p4 | `standard` / `gemini-3.1-flash-lite` | `run → agent_loop → plan → node → provider_call` | **`8dc106ed11679e05139688a3e4b21b7b`** | span cost **==** ledger **$0.000147** (delta 0) | content off in spans |
| 3 · p7 | economy groq/`gpt-oss-120b`; standard gemini/`flash-lite`; frontier openrouter/`gpt-4.1` | pin each rung + downgrade under budget | N/A in harness | projected spread **84.1×**; measured **6.60×** | non-empty on every rung |
| 4 · HTTP agent | role asks frontier; `$0.02` serves **standard** / flash-lite | `run_started` → recall → answer | same hierarchy as p4 | spent **$0.000147**, 1 downgrade | *“Enforcing a budget in code ensures… Relying solely on a prompt is insufficient…”* |

**Honest limitation:** content capture is off by default — Jaeger shows model,
tokens, cost, and hierarchy, but not the prompt/completion, so a wrong answer
cannot be diagnosed from the trace alone. Also, list-price ladder spread
(~84×) is far wider than measured charge spread (~6–8×) on this prompt.

### Part 2 — Policy and measurement

**Workload:** systems/ops FAQ-style tasks (ports, CAP, CIDR, SLO, Raft, latency,
cost trade-offs) — [`proofs/tasks/my_domain.jsonl`](proofs/tasks/my_domain.jsonl).

**Ladder:** economy `groq/openai/gpt-oss-120b` → standard `gemini/gemini-3.1-flash-lite`
→ frontier `openrouter/openai/gpt-4.1`. Budget: `downgrade_at=0.45`,
`refuse_at=0.88`, `max_calls_per_run=48`, principal `varun/s15-domain` @ $0.05
([`docs/part2_policy.md`](docs/part2_policy.md)).

**Judge:** shipped generic rubric in `config/evals.yaml` (panel separate from the
answering ladder; overall ≥ 0.75, per-criterion floor 0.5; not self-judged).

Live `p1` (`--label my_domain_live`):

| Strategy | Cost/call | Resolved | Cost/resolved |
|---|---:|---:|---:|
| A always_frontier | $0.001458 | 13/15 | $0.001570 |
| B always_cheapest | $0.000187 | 14/15 | $0.000240 |
| C budget_aware (our policy) | $0.000194 | **15/15** | **$0.000207** |

**Break-even r\* (B vs A)** from measured spread: **0.288**. B resolution **0.933**
→ headroom **+0.645** (B stays cheaper per resolved task on this ladder).
B vs C shows the signature trap vs the cascade: cheaper/call but dearer/resolved
(r\* ≈ 0.965; B is below it).

**Policy got wrong — `sys_14_logic_puzzle`:** always-frontier **failed** (no usable
resolution) while economy / budget-aware resolved in **1 call for $0.000184**.
The price ladder is not a competence ranking on this task. Related: on
`sys_15_econ_tradeoff`, frontier spent **$0.007638** and still failed; cascade
escalated economy→standard and resolved for **$0.001377**.

### Part 3 — Attack our budget

**Attack 1 — runaway loop** (`p3`, principal `varun/s15-domain`, ceiling $0.001):

| | Before control (extrapolated) | After control (measured) |
|---|---:|---:|
| Spend | ~$0.54 / 10k rounds | **$0.000591** ≤ $0.001 |
| Calls | unbounded | **11** admitted / **189** refused |
| Visibility | n/a | refusals are **`BudgetRefused`** graph failures |

Detail log narrative: [`docs/part3_evidence.md`](docs/part3_evidence.md)
(proof JSON locally at `proofs/out/p3_denial_of_wallet_part3.json`, gitignored).

**Attack 2 — unaffordable tier** (`POST /v1/agent/runs` with `budget=5e-7`):
status `failed`, spent **$0**, calls **0**, refusals **1**, reason: cheapest
economy projects ~$0.000437 > remaining — refused **before** any provider call;
visible in `budget.refusal_log`.

### Reproduce from a fresh checkout

```bash
# terminals: Jaeger, glc_v4 on :8111, s15code on :8113
export GLC_BASE_URL=http://127.0.0.1:8111
export S15_OTEL_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces

TASK="In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt."
uv run python proofs/p2_budget_holds.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1
uv run python proofs/p4_trace_export.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1 --otel-endpoint http://localhost:4318/v1/traces
uv run python proofs/p7_cross_model_ladder.py --task "$TASK" --principal varun/part1 --label part1
uv run python proofs/p3_denial_of_wallet.py --task "$TASK" --budget 0.002 --principal varun/part1 --label part1
uv run python proofs/extract_part1.py --label part1

uv run python proofs/p1_cost_per_task.py --tasks proofs/tasks/my_domain.jsonl \
  --budget 0.05 --principal varun/s15-domain --label my_domain_live
uv run python proofs/extract_part2.py --label my_domain_live

uv run python proofs/p3_denial_of_wallet.py \
  --task "Calculate Raft quorum for 9 nodes and explain in one sentence." \
  --budget 0.001 --principal varun/s15-domain --label part3
```

## Proofs

One harness, one code path, six proofs. Each takes the **task (or task set, or
pair set), budget and principal as arguments**, asserts real invariants, exits
non-zero on failure, and writes JSON to `proofs/out/`.

```bash
uv run python proofs/p1_cost_per_task.py    --tasks proofs/tasks/mixed.jsonl
uv run python proofs/p2_budget_holds.py     --task "<any task>" --budget 0.02
uv run python proofs/p3_denial_of_wallet.py --task "<any task>" --budget 0.002
uv run python proofs/p4_trace_export.py     --task "<any task>" --budget 0.02
uv run python proofs/p6_cache_savings.py    --pairs proofs/pairs/paraphrases.jsonl
uv run python proofs/p7_cross_model_ladder.py --task "<any task>"
```

| Proof | Proves |
|---|---|
| `p1_cost_per_task` | The same task set through always-frontier, always-cheapest-with-retries and the budget-aware cascade, on one ledger. Reports spend, calls, cost per call and **cost per resolved task** per strategy, with "resolved" decided by a generic rubric judge (`s15code.evals`) and never by a per-task answer key. Whether the cheapest rung shows the signature failure mode — lower cost per call, higher cost per resolved task — is reported as a finding, not asserted. |
| `p2_budget_holds` | A run given a ceiling stays under it at every ceiling; a tight allowance downgrades the tier a node asked for; an unaffordable ceiling refuses instead of overspending; provider calls and ledger entries agree exactly. |
| `p3_denial_of_wallet` | An adversarial planner that earns one more node from every outcome, forever, cannot spend past the ceiling. Refusals are visible graph failures. Reports the bill the same loop would have run up uncontrolled. |
| `p4_trace_export` | The journal exports as `run → agent loop → plan → node → provider call`, with `gen_ai.usage.*` and cost on every provider-call span, summing exactly to the ledger. Content capture off. Works with no collector. |
| `p6_cache_savings` | The gateway's semantic cache, against the **real** embedder. A 768-dim nomic vector is confirmed to be neither a stub nor a constant; the similarity the gateway acts on is checked against a cosine computed independently; a hit is billed $0 and its saving is read off the cold call it replaced. Then the threshold is **swept** over a labelled pair set (`proofs/pairs/`), reporting true- and false-positive rates per threshold and per negative family. Whether a collision-free threshold exists is a finding, not an assertion — and on the shipped set it does not. |
| `p7_cross_model_ladder` | Every rung is a different model on a different provider; budget pressure walks the whole ladder down, one model at a time; projected cost is monotone; the measured top-to-bottom spread is reported as a multiple. |

**Two modes, one code path.** If the gateway at `--base-url` answers, the proofs
make real calls and meter real money. Otherwise (or with `--offline`) a
deterministic transport stands in — the policy, ladder, budget, journal and span
export are all the real implementation, only the network is replaced. That is what
lets CI run the same proof with no key and no collector.

The ceilings `p2` uses to force a downgrade and a refusal are **derived from the
configured ladder**, not written down, so editing `config/tiers.yaml` changes the
numbers rather than breaking the proof.

Useful flags: `--offline`, `--respond-as ui`, `--principal tenant/project/user`,
`--otel-endpoint http://127.0.0.1:4318/v1/traces`, `--config-dir`, `--label`,
`--live-embeddings`.

## Observability

`s15code.telemetry.export_run` turns a journal into spans through the real OTel
SDK. Attributes follow the GenAI semantic conventions —
`gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`. Those conventions are
pre-stable and moved to their own repository in June 2026 with no tagged release,
so **cost has no blessed attribute yet**: it is emitted as `s15.cost` with
`s15.currency`, clearly marked as a vendor extension rather than pretending to be
standard.

Set `S15_OTEL_EXPORTER_ENDPOINT` (or `--otel-endpoint`) to send the spans to
Jaeger or any OTLP receiver; Jaeger ingests OTLP natively. Leave it unset and the
span tree is still built and assertable in memory while nothing goes over the
wire, so tests need no collector.

**Content capture is off by default.** Prompts and completions are PII. They are
attached only when a caller passes `capture_content=True` or sets
`S15_OTEL_CAPTURE_CONTENT=1`.

## What the meter covers, honestly

The ledger covers **gateway model calls** — the paid ones. Semantic-memory
embeddings run locally against Ollama and never touch the gateway, so they cost
nothing per token and are not in the ledger.

Admission prices the **worst case**: output is bounded by the tier's `max_tokens`,
which the provider honours, and input by an over-estimate of the prompt actually
being sent (`chars_per_token` and `input_estimate_safety` in `budgets.yaml`). That
makes the projection a real upper bound rather than an average. If a provider
ignored `max_tokens` the call already in flight could overshoot — so the ledger is
also an absolute stop, and `max_calls_per_run` / `max_calls_per_node` bound the
loop even when every price estimate is wrong. A test drives exactly that case.

## Carried forward vs new

**Carried forward** (imports renamed to `s15code.*`, behaviour unchanged): the
live graph and its journal, scoped memory and semantic chunking, the A2A boundary
and gRPC binding, the A2UI catalog/validator/surface/AG-UI/HITL layer, the
gateway boundary, the deterministic and LLM planners, the non-browser skills.

**New in this session**: `s15code/economics/` (six modules), `s15code/telemetry/`,
`config/` (three files), the `budget`/`principal` arguments on a run, the
`/trace` route, and a rewritten `proofs/` harness.

**Deliberately dropped**: S14's `showcase.py` and its `/dashboard` route hardcoded
one use case (a five-paper research corpus, with its title in the code). The
`/v1/harness/surface` route depended on one specific S14 proof artefact. Both
would have violated the no-hardcoding rule this session is built around.

The generated protobuf modules under `s15code/core/a2a/` keep their original
filenames. They are reproduced verbatim because the serialized descriptor is
keyed on the `.proto` file name, and hand-editing generated gencode is worse than
a stale name.
