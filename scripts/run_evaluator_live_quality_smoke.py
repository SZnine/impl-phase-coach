from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from review_gate.evaluator_agent_assessment_client import EvaluatorAgentAssessmentClient
from review_gate.evaluator_agent_prompt_builder import EvaluatorAgentPromptBuilder
from review_gate.evaluator_agent_response_normalizer import EvaluatorAgentResponseNormalizer
from review_gate.evaluator_live_quality_smoke import (
    default_evaluator_live_quality_samples,
    format_live_quality_report,
    run_evaluator_live_quality_smoke,
)


def main() -> int:
    args = _parse_args()
    repo_root = REPO_ROOT
    root_dir = Path(args.root_dir) if args.root_dir else repo_root

    client = EvaluatorAgentAssessmentClient.from_local_config(
        root_dir=root_dir,
        model=args.model,
    )
    results = run_evaluator_live_quality_smoke(
        samples=default_evaluator_live_quality_samples(),
        builder=EvaluatorAgentPromptBuilder(),
        client=client,
        normalizer=EvaluatorAgentResponseNormalizer(),
        project_context=(
            "Current project is migrating from transition review flow to durable "
            "Workflow -> Question -> Answer -> Evaluation -> Facts chain."
        ),
        stage_context="Current stage is evaluator-agent llm assessment integration. Keep Graph and Maintenance out.",
        current_decisions=[
            "PromptBuilder / Client / Normalizer / Service split",
            "Keep Evaluation -> Facts shape stable",
        ],
        boundary_focus=[
            "provider contract vs service boundary",
            "normalization before checkpoint writes",
            "malformed SSE regression",
        ],
    )

    report = format_live_quality_report(results)
    print(report)

    output_dir = repo_root / "artifacts" / "evaluator-live-quality-smoke"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"{timestamp}.txt"
    output_path.write_text(report + "\n", encoding="utf-8")
    print(f"\nSaved report to: {output_path}")

    if args.strict and any(result.issues for result in results):
        return 1
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run opt-in live evaluator quality smoke.")
    parser.add_argument("--root-dir", help="Repository root or config root that contains .env/api_key.md or key/api_key.md")
    parser.add_argument("--model", default="gpt-5.4-mini", help="Evaluator provider model to use")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when any sample reports quality issues",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
