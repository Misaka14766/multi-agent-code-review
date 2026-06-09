"""Convert raw tool outputs to structured Issue objects."""

from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion
from src.tools.base import StructuredResult

_SEVERITY_MAP = {
    "ERROR": Severity.BLOCKER,
    "WARNING": Severity.WARNING,
    "INFO": Severity.INFO,
    "error": Severity.BLOCKER,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
}

_CATEGORY_TYPE_MAP = {
    "security": IssueType.SECURITY,
    "bug": IssueType.BUG,
    "performance": IssueType.PERFORMANCE,
    "maintainability": IssueType.MAINTAINABILITY,
    "style": IssueType.STYLE,
}

_RULE_TYPE_HINTS = {
    "sql": IssueType.SECURITY,
    "injection": IssueType.SECURITY,
    "xss": IssueType.SECURITY,
    "crypto": IssueType.SECURITY,
    "exception": IssueType.BUG,
    "null": IssueType.BUG,
    "overflow": IssueType.BUG,
    "complexity": IssueType.MAINTAINABILITY,
    "naming": IssueType.STYLE,
    "unused": IssueType.MAINTAINABILITY,
    "import": IssueType.STYLE,
}


def parse_semgrep_result(result: StructuredResult) -> list[Issue]:
    """Convert Semgrep StructuredResult to a list of Issues."""
    issues: list[Issue] = []
    for i, finding in enumerate(result.findings):
        rule_id = finding.get("rule_id", "")
        issue_type = _infer_issue_type(rule_id, finding.get("category", ""))
        severity = _SEVERITY_MAP.get(finding.get("severity", "WARNING"), Severity.WARNING)

        issues.append(Issue(
            issue_id=f"SA-SG-{i+1:03d}",
            issue_type=issue_type,
            severity=severity,
            title=finding.get("message", rule_id),
            description=f"Semgrep rule '{rule_id}' triggered at {finding.get('path', '?')}:{finding.get('start_line', '?')}",
            location=SourceLocation(
                file_path=finding.get("path", ""),
                start_line=finding.get("start_line", 0),
                end_line=finding.get("end_line", 0),
            ),
            root_cause=f"Pattern '{rule_id}' matched — {finding.get('message', '')}",
            evidence=Evidence(code_snippet=""),
            confidence=0.92,
            source_agent="static_analysis",
        ))
    return issues


def parse_linter_result(result: StructuredResult, linter: str = "pylint") -> list[Issue]:
    """Convert linter StructuredResult to a list of Issues."""
    issues: list[Issue] = []
    for i, finding in enumerate(result.findings):
        rule_id = finding.get("rule_id", "")
        msg = finding.get("message", "")
        ftype = finding.get("type", "")

        if ftype in ("convention", "refactor"):
            severity = Severity.INFO
        elif ftype == "warning":
            severity = Severity.WARNING
        elif ftype in ("error", "fatal"):
            severity = Severity.BLOCKER
        else:
            severity = Severity.WARNING

        issues.append(Issue(
            issue_id=f"SA-LT-{i+1:03d}",
            issue_type=IssueType.STYLE if ftype in ("convention", "refactor") else IssueType.MAINTAINABILITY,
            severity=severity,
            title=f"[{linter}] {msg[:100]}",
            description=f"{linter} rule '{rule_id}': {msg}",
            location=SourceLocation(
                file_path=finding.get("path", ""),
                start_line=finding.get("line", 0),
                end_line=finding.get("line", 0),
            ),
            root_cause=f"{linter} rule {rule_id}",
            evidence=Evidence(code_snippet=""),
            confidence=0.85,
            source_agent="static_analysis",
        ))
    return issues


def parse_ast_result(result: StructuredResult, file_path: str = "") -> list[Issue]:
    """Convert Tree-sitter AST result to structural Issues (complexity, function size)."""
    issues: list[Issue] = []
    for i, func in enumerate(result.findings):
        line_count = func.get("end_line", 0) - func.get("start_line", 0)
        if line_count > 50:
            issues.append(Issue(
                issue_id=f"SA-AST-{i+1:03d}",
                issue_type=IssueType.MAINTAINABILITY,
                severity=Severity.WARNING,
                title=f"函数 '{func.get('name', 'unknown')}' 过长 ({line_count} 行)",
                description=f"函数超过50行，建议拆分为更小的函数以提高可读性和可测试性。",
                location=SourceLocation(
                    file_path=file_path,
                    start_line=func.get("start_line", 0),
                    end_line=func.get("end_line", 0),
                ),
                root_cause=f"函数 {func.get('name', '')} 包含 {line_count} 行，超过 50 行阈值",
                evidence=Evidence(code_snippet=""),
                confidence=0.80,
                source_agent="static_analysis",
            ))
    return issues


def _infer_issue_type(rule_id: str, category: str = "") -> IssueType:
    """Heuristic to map rule IDs to IssueType."""
    if category in _CATEGORY_TYPE_MAP:
        return _CATEGORY_TYPE_MAP[category]
    rid_lower = rule_id.lower()
    for keyword, itype in _RULE_TYPE_HINTS.items():
        if keyword in rid_lower:
            return itype
    return IssueType.MAINTAINABILITY
