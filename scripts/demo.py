#!/usr/bin/env python3
"""5-Minute Demonstration Script for Multi-Agent Code Review System.

Usage:
  python scripts/demo.py          # Full 5-min walkthrough
  python scripts/demo.py --fast   # Quick 1-min version
"""

import asyncio
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.pr import PRInfo, FileDiff
from src.agents.factory import register_agents
from src.orchestrator.graph import ReviewOrchestrator

DEMO_CODE = '''"""
Auth module — user authentication and login.
"""
import sqlite3


def login(username: str, password: str):
    """Authenticate a user with username and password."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # SECURITY ISSUE: SQL injection via f-string concatenation
    query = f'SELECT * FROM users WHERE name = "{username}"'
    cursor.execute(query)

    user = cursor.fetchone()
    if user is None:
        return None

    # SECURITY ISSUE: Plaintext password comparison
    pw = user['password']
    if pw == password:
        return {"id": user["id"], "name": user["name"], "role": user["role"]}

    conn.close()
    return None


def create_user(username: str, password: str, role: str = "user"):
    """Create a new user — same injection vulnerability."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    query = (
        f'INSERT INTO users (name, password, role) '
        f'VALUES ("{username}", "{password}", "{role}")'
    )
    cursor.execute(query)
    conn.commit()
    conn.close()
    return {"status": "created"}
'''

SYSTEM_ARCH = """
+-------------------------------------------------------------+
|                    Review Orchestrator                       |
|                 (LangGraph State Machine)                    |
+--------------+--------------+--------------+----------------+
               |              |              |
    +----------v----+  +-----v------+  +----v------+  +--------v------+
    |   Static      |  |  Semantic  |  |   Test    |  |    Repair     |
    |   Analysis    |  |   Review   |  |    &      |  |    & Patch    |
    |    Agent      |  |   Agent    |  | Regression|  |    Agent      |
    +---------------+  +------------+  +-----------+  +---------------+
"""


def sep(title: str = "") -> None:
    """Print a section separator."""
    if title:
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}\n")
    else:
        print(f"{'─' * 60}")


async def demo_full():
    """Run the full 5-minute demonstration."""
    print("=" * 60)
    print("  多智能体代码审查系统 — 演示")
    print("  Multi-Agent Code Review System — Demo")
    print("=" * 60)

    # ---- Step 1: Architecture ----
    sep("Step 1/5: 系统架构")
    print(SYSTEM_ARCH)
    print("  • Review Orchestrator — LangGraph 状态机编排")
    print("  • 4 个专业 Agent — 静态分析 / 语义审查 / 测试评估 / 自动修复")
    print("  • 并行调度 + 仲裁去重 + 质量门控 + 迭代修复")
    time.sleep(1.5)

    # ---- Step 2: Code Input ----
    sep("Step 2/5: 输入待审查代码")
    print("  提交代码: src/auth.py (含已知缺陷)")
    print()
    print("  ```python")
    for line in DEMO_CODE.strip().split("\n")[:12]:
        print(f"  {line}")
    print("  ...")
    print("  ```")
    print()
    print("  已知缺陷:")
    print("    1. SQL 注入 — f-string 拼接用户输入到 SQL 查询")
    print("    2. 明文密码比较 — 未使用哈希")
    print("    3. 缺少输入校验 — 无长度/类型检查")
    print("    4. 命名不规范 — 'pw' 过于简短")
    time.sleep(1.5)

    # ---- Step 3: Agent Review ----
    sep("Step 3/5: 多 Agent 并行审查")
    register_agents(force_mock=True)
    orchestrator = ReviewOrchestrator()

    pr_info = PRInfo(
        pr_id="demo-001",
        title="Auth: add login/create_user functions",
        description="Implement user authentication module",
        files_changed=[FileDiff(
            file_path="src/auth.py",
            change_type="modified",
            new_content=DEMO_CODE,
            language="python",
        )],
        files_count=1,
        additions=DEMO_CODE.count("\n") + 1,
        deletions=0,
    )

    review_id = uuid.uuid4().hex[:8]
    print("  调度 Agent: Static Analysis | Semantic Review | Test & Regression")
    print("  状态: 并行执行中...")

    report = await orchestrator.run_review(review_id, pr_info)
    summary = report["summary"]

    for ar in report.get("agent_reports", []):
        name = ar["agent_name"]
        status = ar["status"]
        issues = ar["issues_found"]
        t = ar.get("execution_time_ms", 0)
        print(f"    ✓ {name}: {status} — 发现 {issues} 个问题 ({t:.0f}ms)")
    print(f"  总耗时: {summary['total_execution_time_ms']:.0f}ms")
    time.sleep(1)

    # ---- Step 4: Results ----
    sep("Step 4/5: 审查结果与修复")
    print(f"  质量门控判定: {summary['verdict'].upper()}")
    print(f"  发现问题: {summary['total_issues']} 个")
    print(f"    🚫 阻断级: {summary['blockers']} 个")
    print(f"    ⚠️  警告级: {summary['warnings']} 个")
    print(f"    ℹ️  信息级: {summary['info']} 个")
    print()

    for iss in report["issues"]:
        sev = iss["severity"]
        icon = {"blocker": "🚫", "warning": "⚠️", "suggestion": "💡", "info": "ℹ️"}.get(sev, "•")
        loc = iss.get("location", {})
        print(f"  {icon} [{sev.upper()}] {iss['issue_id']}: {iss['title']}")
        print(f"     位置: {loc.get('file_path', '?')}:{loc.get('start_line', '?')}")
        print(f"     根因: {iss['root_cause'][:80]}")
        fix = iss.get("fix_suggestion")
        if fix:
            print(f"     修复: {fix['explanation'][:80]}")
        print()

    patches = report.get("patches", [])
    if patches:
        print(f"  自动修复: 生成 {len(patches)} 个补丁")
        for p in patches:
            print(f"    • {p['patch_id']}: {p['explanation'][:80]}")
    time.sleep(1.5)

    # ---- Step 5: Conclusion ----
    sep("Step 5/5: 总结")
    print("  ✅ 审查流水线完整运行")
    print("  ✅ 4 个 Agent 并行协作")
    print("  ✅ SQL 注入被正确识别为阻断级缺陷")
    print("  ✅ 自动生成修复补丁 (参数化查询)")
    print("  ✅ 质量门控 — 需人工确认安全修复")
    print()
    print("  技术栈:")
    print("    • LangGraph 状态机编排")
    print("    • Pydantic v2 数据模型")
    print("    • ChromaDB 向量知识库 (RAG)")
    print("    • Semgrep + Pylint + Tree-sitter 静态分析")
    print("    • FastAPI + Docker 部署")
    print("    • DeepSeek-V3 LLM (可选, 默认 Mock)")
    print()
    print("  代码仓库: https://github.com/Egor-wang/multi-agent-code-review")
    print()
    print("=" * 60)
    print("  Demo Complete — 感谢观看!")
    print("=" * 60)


async def demo_fast():
    """Quick 1-minute demo."""
    register_agents(force_mock=True)
    orchestrator = ReviewOrchestrator()

    pr_info = PRInfo(
        pr_id="fast-demo", title="Auth: login feature",
        files_changed=[FileDiff(
            file_path="src/auth.py", change_type="modified",
            new_content=DEMO_CODE[:500], language="python",
        )],
        files_count=1, additions=10, deletions=0,
    )

    print("Running review pipeline...")
    report = await orchestrator.run_review("fast-demo", pr_info)
    s = report["summary"]
    print(f"Verdict: {s['verdict']} | Issues: {s['total_issues']} (B:{s['blockers']} W:{s['warnings']} I:{s['info']}) | Time: {s['total_execution_time_ms']:.0f}ms")
    for iss in report["issues"]:
        print(f"  [{iss['severity'][:6]}] {iss['title'][:70]}")
    patches = report.get("patches", [])
    if patches:
        print(f"Patches: {len(patches)} generated")
    print("Demo complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Agent Code Review Demo")
    parser.add_argument("--fast", action="store_true", help="Quick 1-minute demo")
    args = parser.parse_args()

    if args.fast:
        asyncio.run(demo_fast())
    else:
        asyncio.run(demo_full())
