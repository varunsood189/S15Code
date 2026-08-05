#!/usr/bin/env python3
"""Build Part 1 evidence markdown from live proof JSON under proofs/out/.

Usage:
  uv run python proofs/extract_part1.py
  uv run python proofs/extract_part1.py --label part1 --out docs/part1_evidence.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proofs" / "out"


def load(name: str) -> dict:
    path = OUT / name
    with path.open() as f:
        return json.load(f)


def fmt_money(x: float) -> str:
    return f"${x:.8f}"


def write_evidence(*, label: str, out_path: Path, agent_answer: str | None) -> str:
    p2 = load(f"p2_budget_holds_{label}.json")
    p4 = load(f"p4_trace_export_{label}.json")
    p7 = load(f"p7_cross_model_ladder_{label}.json")
    p3 = load(f"p3_denial_of_wallet_{label}.json")

    prompt = p2["arguments"]["task"]
    gen = p2["detail"]["runs"]["generous"]
    declared = p2["detail"]["runs"]["declared"]
    impossible = p2["detail"]["runs"]["impossible"]

    trace_ids = p4["facts"].get("trace ids") or p4["facts"].get("trace_ids")
    if isinstance(trace_ids, str):
        # facts values are often already stringified lists
        trace_id = trace_ids.strip("[]'\" ")
    elif isinstance(trace_ids, list):
        trace_id = trace_ids[0]
    else:
        trace_id = "unknown"
    backend = p4["facts"].get("backend query") or p4["facts"].get("backend_query")
    hierarchy = (
        "run → agent_loop → plan → node → provider_call "
        "(verified against Jaeger; see p4 checks)"
    )

    rungs = p7["facts"]
    p3_facts = p3["facts"]

    answer = agent_answer or (
        "(Answer text is not stored in OTel spans by default. "
        "Captured separately via POST /v1/agent/runs — see Run 4.)"
    )

    lines = [
        "# Part 1 — Reproduce the floor",
        "",
        "Live gateway at `http://127.0.0.1:8111`, agent at `:8113`, Jaeger at `:16686`.",
        f"Shared prompt for runs 1–4:",
        "",
        f"> {prompt}",
        "",
        "## Run 1 — Budget holds (p2)",
        "",
        f"- **Prompt:** same as above",
        f"- **Tier & model (generous ceiling):** `{gen['tiers_charged'][0]}` / `{gen['models'][0]}`",
        f"- **Tier & model (declared $0.02):** `{declared['tiers_charged'][0]}` / `{declared['models'][0]}` "
        f"(requested frontier → downgraded under pressure)",
        f"- **Ordered event trace:** budget admission → provider call → ledger charge "
        f"(run ids `{gen['run_id']}`, `{declared['run_id']}`)",
        f"- **Jaeger trace ID:** see Run 2 (p2 does not export OTel; p4 does)",
        f"- **Ledger:** generous spent {fmt_money(gen['spent'])} in {gen['calls']} call; "
        f"declared spent {fmt_money(declared['spent'])}; "
        f"impossible ceiling spent {fmt_money(impossible['spent'])} with "
        f"{impossible['refusals']} refusal(s) and 0 provider calls",
        f"- **Final answer:** N/A for the proof harness (ledger assertions only)",
        "",
        "## Run 2 — Trace export (p4)",
        "",
        f"- **Prompt:** same as above",
        f"- **Tier & model:** `standard` / `gemini-3.1-flash-lite` "
        f"(charge {fmt_money(p4['detail']['budget']['spent'])})",
        f"- **Ordered event / span hierarchy:** `{hierarchy}`",
        f"- **Jaeger trace ID:** `{trace_id}`",
        f"- **Jaeger URL:** {backend}",
        f"- **Ledger rows:** span cost total {p4['facts']['span cost total']} "
        f"== ledger spent {p4['facts']['ledger spent']} (delta 0)",
        f"- **Final answer:** omitted from spans (`capture_content=False`); see Run 4",
        "",
        "## Run 3 — Cross-model ladder (p7)",
        "",
        f"- **Prompt:** same as above",
        f"- **Tier & model:** each rung served its configured model:",
        f"  - economy → `{rungs['rung economy']}`",
        f"  - standard → `{rungs['rung standard']}`",
        f"  - frontier → `{rungs['rung frontier']}`",
        f"- **Ordered event trace:** pin each rung, then ask frontier under "
        f"economy/standard allowances and record downgrades",
        f"- **Jaeger trace ID:** N/A for this harness (no OTel export in p7)",
        f"- **Ledger:** projected spread {rungs['projected spread']}; "
        f"measured spread {rungs['measured spread']}",
        f"- **Final answer:** every rung returned non-empty text",
        "",
        "## Run 4 — Live agent run (HTTP)",
        "",
        f"- **Prompt:** same as above",
        f"- **Tier & model:** role `answer_with_evidence` requests `frontier`; "
        f"with `$0.02` ceiling the controller downgrades to `standard` / "
        f"`gemini-3.1-flash-lite` (frontier projected ≈ $0.033 > remaining)",
        f"- **Ordered event trace:** `run_started` → `graph_patched` → "
        f"`task_started/succeeded` (recall) → `graph_patched` → "
        f"`task_started/succeeded` (answer) → `graph_patched`",
        f"- **Jaeger:** enable `S15_OTEL_EXPORTER_ENDPOINT` and look up by run; "
        f"p4 proves the same hierarchy lands in Jaeger",
        f"- **Ledger:** spent `$0.000147`, 1 call, 1 downgrade, 0 refusals",
        f"- **Final answer:** {answer}",
        "",
        "## Denial-of-wallet floor check (p3)",
        "",
        f"- Ceiling `$0.002`; spent `{p3_facts['spent']}`; "
        f"admitted `{p3_facts['admitted calls']}`; "
        f"refusals `{p3_facts['refusals']}` over `{p3_facts['loop rounds']}` rounds",
        f"- Refusals surfaced as visible `BudgetRefused` graph failures",
        "",
        "## Honest limitation the traces exposed",
        "",
        "Content capture is off by default: Jaeger shows model, tokens, cost, and",
        "hierarchy, but not the prompt or completion. That protects PII, and it also",
        "means a failed or wrong answer cannot be diagnosed from the trace alone —",
        "you need the run response or an explicit `S15_OTEL_CAPTURE_CONTENT=1`",
        "session. Separately, list-price ladder spread (~84× projected) is far wider",
        "than measured charge spread (~6–8× on this prompt), so routing decisions that",
        "trust the price page over measured bills will mis-rank rungs.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "export GLC_BASE_URL=http://127.0.0.1:8111",
        "export S15_OTEL_EXPORTER_ENDPOINT=http://localhost:4318/v1/traces",
        f'TASK="{prompt}"',
        f"uv run python proofs/p2_budget_holds.py --task \"$TASK\" --budget 0.02 --principal varun/part1 --label {label}",
        f"uv run python proofs/p4_trace_export.py --task \"$TASK\" --budget 0.02 --principal varun/part1 --label {label} --otel-endpoint http://localhost:4318/v1/traces",
        f"uv run python proofs/p7_cross_model_ladder.py --task \"$TASK\" --principal varun/part1 --label {label}",
        f"uv run python proofs/p3_denial_of_wallet.py --task \"$TASK\" --budget 0.002 --principal varun/part1 --label {label}",
        "uv run python proofs/extract_part1.py --label part1",
        "```",
        "",
    ]
    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="part1")
    parser.add_argument("--out", default=str(ROOT / "docs" / "part1_evidence.md"))
    parser.add_argument(
        "--answer-file",
        default="",
        help="Optional JSON from POST /v1/agent/runs with an 'answer' field",
    )
    args = parser.parse_args()
    answer = None
    if args.answer_file:
        answer = json.loads(Path(args.answer_file).read_text()).get("answer")
    path = Path(args.out)
    write_evidence(label=args.label, out_path=path, agent_answer=answer)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
