"""Evaluation runner — run all samples through the review pipeline and compute metrics."""

import asyncio
import time
from .dataset import get_dataset, EvalSample
from .metrics import compute_metrics, EvalReport
from src.models.pr import PRInfo, FileDiff
from src.orchestrator.graph import ReviewOrchestrator


async def run_evaluation(use_mock: bool = True) -> EvalReport:
    """Run the full evaluation pipeline and return a metrics report."""
    from src.agents.factory import register_agents
    register_agents(force_mock=use_mock)

    orchestrator = ReviewOrchestrator()
    dataset = get_dataset()

    detected: dict[str, list[dict]] = {}
    times: dict[str, float] = {}

    for i, sample in enumerate(dataset):
        pr_info = PRInfo(
            pr_id=f"eval-{sample.id}",
            title=f"Eval: {sample.description}",
            description="Evaluation sample",
            files_changed=[
                FileDiff(
                    file_path=sample.file_path,
                    change_type="modified",
                    new_content=sample.code,
                    language="python",
                )
            ],
            files_count=1,
            additions=sample.code.count("\n") + 1,
            deletions=0,
        )

        start = time.time()
        report = await orchestrator.run_review(f"eval-{sample.id}", pr_info)
        elapsed = (time.time() - start) * 1000

        detected[sample.id] = report.get("issues", [])
        times[sample.id] = elapsed
        print(f"  [{i+1:2d}/{len(dataset)}] {sample.id}: {len(detected[sample.id])} issues in {elapsed:.0f}ms — {sample.description}")

    return compute_metrics(detected, times)


def print_report(report: EvalReport) -> None:
    """Print a formatted evaluation report."""
    print()
    print("=" * 70)
    print("  EVALUATION REPORT")
    print("=" * 70)
    print(f"  Samples:        {report.total_samples}")
    print(f"  Expected issues: {report.total_expected}")
    print(f"  Detected issues: {report.total_detected}")
    print(f"  True positives:  {report.total_tp}")
    print(f"  False positives: {report.total_fp}")
    print(f"  False negatives: {report.total_fn}")
    print()
    print(f"  Macro Precision: {report.macro_precision:.1%}")
    print(f"  Macro Recall:    {report.macro_recall:.1%}")
    print(f"  Macro F1-score:  {report.macro_f1:.1%}")
    print(f"  Avg. Time:       {report.avg_time_ms:.0f}ms")
    print("=" * 70)
    print()
    print("  Per-sample breakdown:")
    print(f"  {'ID':<6} {'Exp':>3} {'Det':>3} {'TP':>3} {'FP':>3} {'FN':>3} {'Prec':>6} {'Rec':>6} {'F1':>6}")
    for r in report.results:
        print(f"  {r.sample_id:<6} {r.expected_count:3d} {r.detected_count:3d} {r.true_positives:3d} {r.false_positives:3d} {r.false_negatives:3d} {r.precision:6.1%} {r.recall:6.1%} {r.f1:6.1%}")
