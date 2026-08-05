"""Smoke test for the Part 1 evidence extractor."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_extract_module():
    path = ROOT / "proofs" / "extract_part1.py"
    spec = importlib.util.spec_from_file_location("extract_part1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_minimal_proofs(tmp_out: Path, label: str) -> None:
    tmp_out.mkdir(parents=True, exist_ok=True)
    prompt = "why enforce budget in code"
    (tmp_out / f"p2_budget_holds_{label}.json").write_text(
        json.dumps(
            {
                "arguments": {"task": prompt},
                "detail": {
                    "runs": {
                        "generous": {
                            "tiers_charged": ["frontier"],
                            "models": ["openai/gpt-4.1"],
                            "spent": 0.001,
                            "calls": 1,
                            "run_id": "run-g",
                        },
                        "declared": {
                            "tiers_charged": ["standard"],
                            "models": ["gemini-3.1-flash-lite"],
                            "spent": 0.0001,
                            "calls": 1,
                            "run_id": "run-d",
                        },
                        "impossible": {"spent": 0.0, "refusals": 1},
                    }
                },
            }
        )
    )
    (tmp_out / f"p4_trace_export_{label}.json").write_text(
        json.dumps(
            {
                "facts": {
                    "trace ids": ["abc123"],
                    "backend query": "http://localhost:16686/api/traces/abc123",
                    "span cost total": "0.00010000",
                    "ledger spent": "0.00010000",
                },
                "detail": {"budget": {"spent": 0.0001}},
            }
        )
    )
    (tmp_out / f"p7_cross_model_ladder_{label}.json").write_text(
        json.dumps(
            {
                "facts": {
                    "rung economy": "groq / openai/gpt-oss-120b",
                    "rung standard": "gemini / flash",
                    "rung frontier": "openrouter / gpt-4.1",
                    "projected spread": "84x",
                    "measured spread": "7x",
                }
            }
        )
    )
    (tmp_out / f"p3_denial_of_wallet_{label}.json").write_text(
        json.dumps(
            {
                "facts": {
                    "spent": "0.001",
                    "admitted calls": "10",
                    "refusals": "190",
                    "loop rounds": "200",
                }
            }
        )
    )


def test_extract_part1_writes_required_sections(tmp_path, monkeypatch):
    extract_part1 = _load_extract_module()
    label = "unit"
    monkeypatch.setattr(extract_part1, "OUT", tmp_path)
    _write_minimal_proofs(tmp_path, label)
    out = tmp_path / "evidence.md"
    text = extract_part1.write_evidence(
        label=label,
        out_path=out,
        agent_answer="Budget belongs in code.",
    )
    assert out.exists()
    assert "Run 1 — Budget holds" in text
    assert "Run 2 — Trace export" in text
    assert "Run 3 — Cross-model ladder" in text
    assert "Run 4 — Live agent run" in text
    assert "Honest limitation" in text
    assert "abc123" in text
    assert "Budget belongs in code." in text
