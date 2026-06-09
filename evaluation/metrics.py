"""Evaluation metrics — Precision, Recall, F1-score for code review."""

from dataclasses import dataclass, field
from .dataset import EvalSample, get_dataset


@dataclass
class EvalResult:
    sample_id: str
    expected_count: int
    detected_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0


@dataclass
class EvalReport:
    results: list[EvalResult] = field(default_factory=list)
    total_samples: int = 0
    total_expected: int = 0
    total_detected: int = 0
    total_tp: int = 0
    total_fp: int = 0
    total_fn: int = 0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    avg_time_ms: float = 0.0


def match_issue(issue: dict, expected: dict) -> bool:
    """Check if a detected issue matches an expected ground-truth issue."""
    # Match by type
    if issue.get("issue_type") != expected.get("type"):
        return False
    # Match by keyword in title/description
    keyword = expected.get("keyword", "").lower()
    if keyword:
        title = issue.get("title", "").lower()
        desc = issue.get("description", "").lower()
        root = issue.get("root_cause", "").lower()
        if keyword not in title and keyword not in desc and keyword not in root:
            return False
    return True


def compute_metrics(detected_per_sample: dict[str, list[dict]], times_per_sample: dict[str, float]) -> EvalReport:
    """Compute Precision/Recall/F1 from detection results vs ground truth."""
    dataset = get_dataset()
    report = EvalReport()
    report.total_samples = len(dataset)

    for sample in dataset:
        detected = detected_per_sample.get(sample.id, [])
        expected = sample.expected_issues

        tp = 0
        matched_expected: set[int] = set()
        matched_detected: set[int] = set()

        for di, issue in enumerate(detected):
            for ei, exp in enumerate(expected):
                if ei not in matched_expected and di not in matched_detected and match_issue(issue, exp):
                    tp += 1
                    matched_expected.add(ei)
                    matched_detected.add(di)
                    break

        fp = len(detected) - len(matched_detected)
        fn = len(expected) - len(matched_expected)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0 if len(expected) == 0 and len(detected) == 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0 if len(expected) == 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        report.results.append(EvalResult(
            sample_id=sample.id,
            expected_count=len(expected),
            detected_count=len(detected),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1=f1,
        ))

        report.total_expected += len(expected)
        report.total_detected += len(detected)
        report.total_tp += tp
        report.total_fp += fp
        report.total_fn += fn

    # Macro-average
    n = len(report.results) if report.results else 1
    report.macro_precision = sum(r.precision for r in report.results) / n
    report.macro_recall = sum(r.recall for r in report.results) / n
    report.macro_f1 = sum(r.f1 for r in report.results) / n

    if times_per_sample:
        report.avg_time_ms = sum(times_per_sample.values()) / len(times_per_sample)

    return report
