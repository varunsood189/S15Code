#!/usr/bin/env python3
"""Build Part 2 evidence markdown from a live p1 JSON under proofs/out/.

Usage:
  uv run python proofs/extract_part2.py --label my_domain_live
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proofs" / "out"


def write_evidence(*, label: str, out_path: Path) -> str:
    data = json.loads((OUT / f"p1_cost_per_task_{label}.json").read_text())
    assert data.get("ok"), "refusing to document a failed proof"
    assert data.get("mode") == "live", (
        f"Part 2 evidence requires live mode, got {data.get('mode')}: {data.get('mode_detail')}"
    )

    facts = data["facts"]
    summaries = data["detail"]["summaries"]
    finding = data["detail"]["finding"]
    divergences = data["detail"].get("divergences", {})
    per_task_c = data["detail"]["per_task"]["C"]

    # Prefer honest "policy got wrong" cases from this session's lessons:
    # 1) frontier failed while a cheaper rung resolved (ladder ≠ competence)
    # 2) always-cheapest burned retries and still failed while cascade escalated
    # 3) cascade overspent vs always-frontier on the same resolved task
    per_task_a = {row["task_id"]: row for row in data["detail"]["per_task"]["A"]}
    per_task_b = {row["task_id"]: row for row in data["detail"]["per_task"]["B"]}
    wrong_cases = []
    for row in per_task_c:
        tid = row["task_id"]
        a = per_task_a.get(tid)
        b = per_task_b.get(tid)
        if a and row.get("resolved") and not a.get("resolved"):
            wrong_cases.append(
                {
                    "task_id": tid,
                    "c_cost": row.get("cost"),
                    "a_cost": a.get("cost"),
                    "c_tiers": row.get("tiers_charged"),
                    "c_calls": row.get("calls"),
                    "reason": (
                        "always-frontier failed while the budget-aware path resolved — "
                        "the price ladder is not a competence ranking on this task"
                    ),
                }
            )
        if b and row.get("resolved") and not b.get("resolved") and b.get("calls", 0) >= 2:
            wrong_cases.append(
                {
                    "task_id": tid,
                    "c_cost": row.get("cost"),
                    "a_cost": b.get("cost"),
                    "c_tiers": row.get("tiers_charged"),
                    "c_calls": row.get("calls"),
                    "reason": (
                        "always-cheapest retried on economy and still failed; "
                        "refusing to escalate was the wrong policy for this task"
                    ),
                }
            )
        if (
            a
            and row.get("resolved")
            and a.get("resolved")
            and row.get("cost", 0) > (a.get("cost") or 0) * 1.5
        ):
            wrong_cases.append(
                {
                    "task_id": tid,
                    "c_cost": row.get("cost"),
                    "a_cost": a.get("cost"),
                    "c_tiers": row.get("tiers_charged"),
                    "c_calls": row.get("calls"),
                    "reason": "cascade spent ≥1.5× always-frontier for the same resolved task",
                }
            )

    wrong = wrong_cases[0] if wrong_cases else None
    b_vs_a = finding["comparisons"]["B_vs_A"]
    b_vs_c = finding["comparisons"].get("B_vs_C", {})

    lines = [
        "# Part 2 — Policy measurement (systems/ops domain)",
        "",
        f"Source: `proofs/out/p1_cost_per_task_{label}.json` (**live**).",
        "Policy: [`docs/part2_policy.md`](part2_policy.md). "
        "Tasks: `proofs/tasks/my_domain.jsonl` (15).",
        "",
        "## Cost per call and cost per resolved task",
        "",
        "| Strategy | Spend | Calls | Cost/call | Resolved | Cost/resolved |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, name in [
        ("A", "always_frontier"),
        ("B", "always_cheapest"),
        ("C", "budget_aware"),
    ]:
        s = summaries[key]
        lines.append(
            f"| {key}: {name} | ${s['spend']:.8f} | {s['calls']} | "
            f"${s['cost_per_call']:.8f} | {s['resolved']}/15 | "
            f"${s['cost_per_resolved_task']:.8f} |"
        )

    lines += [
        "",
        "### Raw facts",
        "",
        f"- A: {facts['A always_frontier']}",
        f"- B: {facts['B always_cheapest']}",
        f"- C: {facts['C budget_aware']}",
        f"- Judge meta-cost: {facts['judge meta-cost']}",
        f"- Signature failure mode: {facts['signature failure mode'][:180]}...",
        "",
        "## Break-even resolution rate",
        "",
        f"- Measured B vs A break-even resolution rate r*: "
        f"**{b_vs_a['break_even_resolution_rate']:.4f}**",
        f"- B resolution rate: **{b_vs_a['resolution_rate']['B']:.4f}**",
        f"- Headroom above break-even: **{b_vs_a['headroom_above_break_even']:.4f}**",
        f"- Cheaper per call: {b_vs_a['cheaper_per_call']}; "
        f"dearer per resolved task: {b_vs_a['dearer_per_resolved_task']}",
        "",
        "Interpretation: if B's resolution rate falls below r*, its cost per "
        "resolved task exceeds always-frontier despite cheaper calls.",
        "",
    ]
    if b_vs_c:
        lines += [
            "### B vs C (cascade)",
            "",
            f"- Signature failure mode (cheaper/call, dearer/resolved): "
            f"**{b_vs_c.get('signature_failure_mode')}**",
            f"- Break-even r* B vs C: **{b_vs_c.get('break_even_resolution_rate', 0):.4f}**",
            f"- B resolution {b_vs_c.get('resolution_rate', {}).get('B')} vs "
            f"C {b_vs_c.get('resolution_rate', {}).get('C')}",
            "",
        ]
    lines += [
        "## A case the policy got wrong",
        "",
    ]
    if wrong:
        a_cost = (
            f"${wrong['a_cost']:.8f}"
            if wrong.get("a_cost") is not None
            else "n/a"
        )
        lines += [
            f"- **Task:** `{wrong['task_id']}`",
            f"- **Why wrong:** {wrong['reason']}",
            f"- **Budget-aware path:** ${wrong['c_cost']:.8f} / "
            f"{wrong['c_calls']} calls / tiers {wrong['c_tiers']}",
            f"- **Compared strategy cost:** {a_cost}",
            "",
        ]
    else:
        lines += [
            "No automatic wrong-policy case matched the heuristics; inspect "
            f"`detail.divergences` in the JSON ({len(divergences)} groups).",
            "",
        ]

    a_vs_b = divergences.get("A_vs_B") or []
    lines += [
        f"Strategy disagreements A vs B (count={len(a_vs_b)}): first three:",
        "",
    ]
    for item in a_vs_b[:3]:
        lines.append(f"- {item if isinstance(item, str) else json.dumps(item)[:200]}")

    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "export GLC_BASE_URL=http://127.0.0.1:8111",
        "uv run python proofs/p1_cost_per_task.py \\",
        "  --tasks proofs/tasks/my_domain.jsonl \\",
        "  --budget 0.05 --principal varun/s15-domain \\",
        f"  --label {label}",
        f"uv run python proofs/extract_part2.py --label {label}",
        "```",
        "",
    ]
    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="my_domain_live")
    parser.add_argument("--out", default=str(ROOT / "docs" / "part2_evidence.md"))
    args = parser.parse_args()
    write_evidence(label=args.label, out_path=Path(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
