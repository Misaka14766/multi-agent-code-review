#!/usr/bin/env python3
"""CLI tool for Multi-Agent Code Review System.

Usage:
  python scripts/run_cli.py --mock          # Demo with built-in sample code
  python scripts/run_cli.py --file auth.py  # Review a single file
  python scripts/run_cli.py --diff changes.diff  # Review a diff file
"""

import argparse
import asyncio
import json
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.pr import PRInfo, FileDiff
from src.agents.factory import register_agents
from src.orchestrator.graph import ReviewOrchestrator

def _load_sample_code() -> str:
    """Load the demo sample code from fixtures."""
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "sample_code_with_bugs.py")
    if os.path.exists(fixture_path):
        with open(fixture_path, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback for development
    return "def login(u, p): pass  # demo stub"


def build_pr_info_from_code(code: str, file_path: str, language: str = "python") -> PRInfo:
    lines = code.strip().split("\n")
    return PRInfo(
        pr_id=str(uuid.uuid4())[:8],
        title=f"Review: {file_path}",
        description=f"Automated code review for {file_path}",
        repo_url="",
        base_branch="main",
        head_branch="feature/review",
        author="cli-user",
        files_changed=[
            FileDiff(
                file_path=file_path,
                change_type="modified",
                new_content=code,
                diff_text="",
                language=language,
            )
        ],
        files_count=1,
        additions=len(lines),
        deletions=0,
        labels=[],
    )


def format_report_markdown(report: dict) -> str:
    """Convert a review report dict to formatted Markdown."""
    summary = report.get("summary", {})
    issues = report.get("issues", [])
    agent_reports = report.get("agent_reports", [])
    errors = report.get("errors", [])

    lines = []
    lines.append("# 代码审查报告")
    lines.append("")
    lines.append(f"**Review ID**: `{report.get('review_id', 'N/A')}`")
    lines.append(f"**PR**: {report.get('pr_title', 'N/A')}")
    lines.append(f"**Status**: {report.get('status', 'N/A')}")
    lines.append("")

    # Summary
    lines.append("## 审查摘要")
    lines.append("")
    verdict = summary.get("verdict", "unknown")
    verdict_icon = {"pass": "[PASS]", "needs_fix": "[WARN]", "blocked": "[BLOCK]"}.get(verdict, "[????]")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 审查结论 | {verdict_icon} **{verdict}** |")
    lines.append(f"| 总问题数 | {summary.get('total_issues', 0)} |")
    lines.append(f"| [BLOCK] 阻断级 | {summary.get('blockers', 0)} |")
    lines.append(f"| [WARN] 警告级 | {summary.get('warnings', 0)} |")
    lines.append(f"| [SUGG] 建议级 | {summary.get('suggestions', 0)} |")
    lines.append(f"| [INFO] 信息级 | {summary.get('info', 0)} |")
    lines.append(f"| 修复尝试 | {summary.get('repair_attempts', 0)} 次 |")
    lines.append(f"| 总耗时 | {summary.get('total_execution_time_ms', 0):.0f}ms |")
    lines.append("")

    if summary.get("verdict_summary"):
        lines.append(f"> {summary['verdict_summary']}")
        lines.append("")

    # Quality gate details
    qg = report.get("quality_gate", {})
    if qg:
        lines.append("### 质量门控详情")
        lines.append("")
        lines.append(f"- **判定**: {qg.get('verdict', 'N/A')}")
        lines.append(f"- **需人工介入**: {'是' if qg.get('requires_human') else '否'}")
        human_qs = qg.get("human_questions", [])
        if human_qs:
            for q in human_qs:
                lines.append(f"  - {q}")
        lines.append("")

    # Issues
    if issues:
        lines.append("## 发现的问题")
        lines.append("")
        severity_icon = {
            "blocker": "[BLOCK]", "warning": "[WARN]", "suggestion": "[SUGG]", "info": "[INFO]",
        }
        for i, issue in enumerate(issues, 1):
            icon = severity_icon.get(issue.get("severity", ""), "[????]")
            lines.append(f"### {icon} #{i}: {issue.get('title', 'Unknown')}")
            lines.append("")
            lines.append(f"- **ID**: `{issue.get('issue_id', 'N/A')}`")
            lines.append(f"- **严重程度**: {issue.get('severity', 'N/A')}")
            lines.append(f"- **类型**: {issue.get('issue_type', 'N/A')}")
            lines.append(f"- **位置**: `{issue.get('location', {}).get('file_path', '?')}:{issue.get('location', {}).get('start_line', '?')}`")
            lines.append(f"- **置信度**: {issue.get('confidence', 0):.0%}")
            lines.append(f"- **来源Agent**: {issue.get('source_agent', 'N/A')}")
            lines.append("")
            lines.append(f"**描述**: {issue.get('description', '')}")
            lines.append("")
            lines.append(f"**根因分析**: {issue.get('root_cause', '')}")
            lines.append("")

            evidence = issue.get("evidence", {})
            if evidence.get("code_snippet"):
                lines.append("**证据代码**:")
                lines.append("```python")
                lines.append(evidence["code_snippet"])
                lines.append("```")
                lines.append("")

            fix = issue.get("fix_suggestion")
            if fix:
                lines.append("**修复建议**:")
                lines.append(f"> {fix.get('explanation', '')}")
                lines.append("")
                if fix.get("unified_diff"):
                    lines.append("```diff")
                    lines.append(fix["unified_diff"])
                    lines.append("```")
                    lines.append("")
            lines.append("---")
            lines.append("")

    # Agent execution details
    if agent_reports:
        lines.append("## Agent 执行详情")
        lines.append("")
        lines.append("| Agent | 状态 | 发现问题 | 耗时 |")
        lines.append("|-------|------|----------|------|")
        for ar in agent_reports:
            status_icon = {"success": "[OK]", "timeout": "[T/O]", "error": "[ERR]"}.get(ar.get("status", ""), "[???]")
            lines.append(
                f"| {status_icon} {ar.get('agent_name', ar.get('agent_id', '?'))} "
                f"| {ar.get('status', '?')} "
                f"| {ar.get('issues_found', 0)} "
                f"| {ar.get('execution_time_ms', 0):.0f}ms |"
            )
        lines.append("")

    # Errors
    if errors:
        lines.append("## 系统警告/错误")
        lines.append("")
        for e in errors:
            lines.append(f"- [WARN] {e}")
        lines.append("")

    lines.append("---")
    lines.append("*Report generated by Multi-Agent Code Review System v0.1.0*")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Code Review CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--mock", action="store_true", help="Run demo with built-in sample code containing known bugs")
    parser.add_argument("--file", help="Path to a source file to review")
    parser.add_argument("--diff", help="Path to a unified diff file to review")
    parser.add_argument("--output", default="", help="Output report file path (default: stdout)")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Report format")
    args = parser.parse_args()

    # Build PRInfo
    if args.mock:
        pr_info = build_pr_info_from_code(_load_sample_code(), "src/auth.py", "python")
        print("=" * 60)
        print("  多智能体代码审查系统 - Mock Demo")
        print("=" * 60)
        print()
        print(f"[*] 加载Mock智能体...")
    elif args.file:
        file_path = args.file
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        ext = os.path.splitext(file_path)[1].lstrip(".")
        lang_map = {"py": "python", "js": "javascript", "ts": "typescript", "java": "java", "go": "go"}
        lang = lang_map.get(ext, ext)
        pr_info = build_pr_info_from_code(code, file_path, lang)
        print(f"[*] Reviewing file: {file_path}")
    elif args.diff:
        if not os.path.exists(args.diff):
            print(f"Error: Diff file not found: {args.diff}", file=sys.stderr)
            sys.exit(1)
        with open(args.diff, "r", encoding="utf-8") as f:
            diff_text = f.read()
        pr_info = PRInfo(
            pr_id=str(uuid.uuid4())[:8],
            title=f"Diff Review: {args.diff}",
            files_changed=[FileDiff(file_path=args.diff, diff_text=diff_text)],
            files_count=1,
            additions=0, deletions=0,
        )
        print(f"[*] Reviewing diff: {args.diff}")
    else:
        print("Error: Use --mock, --file, or --diff to specify what to review.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Initialize
    register_agents(force_mock=args.mock)
    orchestrator = ReviewOrchestrator()
    review_id = str(uuid.uuid4())[:8]

    # Run review
    print(f"[*] Review ID: {review_id}")
    print(f"[*] Dispatching agents: Static Analysis, Semantic Review, Test & Regression")
    print(f"[*] Running review pipeline...")
    print()

    report = await orchestrator.run_review(review_id, pr_info)

    # Output
    if args.format == "json":
        output = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        output = format_report_markdown(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[OK] Report saved to: {args.output}")
    else:
        print(output)

    # Summary line
    summary = report.get("summary", {})
    verdict = summary.get("verdict", "unknown")
    print(f"\n[DONE] Review complete | Verdict: {verdict} | Issues: {summary.get('total_issues', 0)} | Time: {summary.get('total_execution_time_ms', 0):.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
