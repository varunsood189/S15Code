# Part 1 — Reproduce the floor

Live gateway at `http://127.0.0.1:8111`, agent at `:8113`, Jaeger at `:16686`.
Shared prompt for runs 1–4:

> In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt.

## Run 1 — Budget holds (p2)

- **Prompt:** same as above
- **Tier & model (generous ceiling):** `frontier` / `openai/gpt-4.1`
- **Tier & model (declared $0.02):** `standard` / `gemini-3.1-flash-lite` (requested frontier → downgraded under pressure)
- **Ordered event trace:** budget admission → provider call → ledger charge (run ids `run-fc4def9c17e7`, `run-10aa1c2db96f`)
- **Jaeger trace ID:** see Run 2 (p2 does not export OTel; p4 does)
- **Ledger:** generous spent $0.00088000 in 1 call; declared spent $0.00014700; impossible ceiling spent $0.00000000 with 1 refusal(s) and 0 provider calls
- **Final answer:** N/A for the proof harness (ledger assertions only)

## Run 2 — Trace export (p4)

- **Prompt:** same as above
- **Tier & model:** `standard` / `gemini-3.1-flash-lite` (charge $0.00014700)
- **Ordered event / span hierarchy:** `run → agent_loop → plan → node → provider_call (verified against Jaeger; see p4 checks)`
- **Jaeger trace ID:** `8dc106ed11679e05139688a3e4b21b7b`
- **Jaeger URL:** http://localhost:16686/api/traces/8dc106ed11679e05139688a3e4b21b7b
- **Ledger rows:** span cost total 0.00014700 == ledger spent 0.00014700 (delta 0)
- **Final answer:** omitted from spans (`capture_content=False`); see Run 4

## Run 3 — Cross-model ladder (p7)

- **Prompt:** same as above
- **Tier & model:** each rung served its configured model:
  - economy → `groq / openai/gpt-oss-120b  projected 0.00039045  charged 0.00007395  103in/78out  342 chars`
  - standard → `gemini_1 / gemini-3.1-flash-lite  projected 0.00154675  charged 0.00007600  28in/46out  275 chars`
  - frontier → `openrouter / openai/gpt-4.1  projected 0.03285400  charged 0.00048800  40in/51out  270 chars`
- **Ordered event trace:** pin each rung, then ask frontier under economy/standard allowances and record downgrades
- **Jaeger trace ID:** N/A for this harness (no OTel export in p7)
- **Ledger:** projected spread 84.1x  (0.00039045 -> 0.03285400); measured spread 6.60x  (0.00007395 -> 0.00048800)
- **Final answer:** every rung returned non-empty text

## Run 4 — Live agent run (HTTP)

- **Prompt:** same as above
- **Tier & model:** role `answer_with_evidence` requests `frontier`; with `$0.02` ceiling the controller downgrades to `standard` / `gemini-3.1-flash-lite` (frontier projected ≈ $0.033 > remaining)
- **Ordered event trace:** `run_started` → `graph_patched` → `task_started/succeeded` (recall) → `graph_patched` → `task_started/succeeded` (answer) → `graph_patched`
- **Jaeger:** enable `S15_OTEL_EXPORTER_ENDPOINT` and look up by run; p4 proves the same hierarchy lands in Jaeger
- **Ledger:** spent `$0.000147`, 1 call, 1 downgrade, 0 refusals
- **Final answer:** Enforcing a budget in code ensures that constraints are applied consistently and programmatically, preventing the model from bypassing limits through adversarial prompting or hallucination. Relying solely on a prompt is insufficient because natural language instructions are inherently flexible and can be overridden by the model's internal weights or complex user inputs.

## Denial-of-wallet floor check (p3)

- Ceiling `$0.002`; spent `0.00157770`; admitted `23`; refusals `177` over `200` rounds
- Refusals surfaced as visible `BudgetRefused` graph failures

## Honest limitation the traces exposed

Content capture is off by default: Jaeger shows model, tokens, cost, and
hierarchy, but not the prompt or completion. That protects PII, and it also
means a failed or wrong answer cannot be diagnosed from the trace alone —
you need the run response or an explicit `S15_OTEL_CAPTURE_CONTENT=1`
session. Separately, list-price ladder spread (~84× projected) is far wider
than measured charge spread (~6–8× on this prompt), so routing decisions that
trust the price page over measured bills will mis-rank rungs.

## Reproduce

```bash
export GLC_BASE_URL=http://127.0.0.1:8111
export S15_OTEL_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces
TASK="In exactly two sentences, explain why a budget must be enforced in code rather than in a prompt."
uv run python proofs/p2_budget_holds.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1
uv run python proofs/p4_trace_export.py --task "$TASK" --budget 0.02 --principal varun/part1 --label part1 --otel-endpoint http://localhost:4318/v1/traces
uv run python proofs/p7_cross_model_ladder.py --task "$TASK" --principal varun/part1 --label part1
uv run python proofs/p3_denial_of_wallet.py --task "$TASK" --budget 0.002 --principal varun/part1 --label part1
uv run python proofs/extract_part1.py --label part1
```
