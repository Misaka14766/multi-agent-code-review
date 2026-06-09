import asyncio
from .base import BaseAgent, AgentConfig, AgentCapability, AgentResult
from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion, CodeReference
from src.models.pr import PRInfo


class MockStaticAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(agent_id="static_analysis", agent_name="Static Analysis Agent"))

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "style", "maintainability", "bug"],
            languages=["python", "javascript", "typescript"],
            produces=["issues"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        await asyncio.sleep(0.05)
        issues = [
            Issue(
                issue_id="SA-001",
                issue_type=IssueType.SECURITY,
                severity=Severity.BLOCKER,
                title="检测到潜在的SQL注入漏洞（模式匹配）",
                description="Semgrep规则 'python-sql-string-concatenation' 在第45行触发：用户输入通过f-string拼接到SQL查询中。",
                location=SourceLocation(file_path="src/auth.py", start_line=45, end_line=45,
                    ast_path="FunctionDef:login -> Assign:query -> JoinedStr"),
                root_cause="字符串插值方式构建SQL语句，用户输入未经过滤直接嵌入查询字符串。",
                evidence=Evidence(
                    code_snippet='query = f\'SELECT * FROM users WHERE name = "{username}"\'',
                    ast_path="FunctionDef:login -> Assign:query -> JoinedStr",
                ),
                fix_suggestion=FixSuggestion(
                    unified_diff="@@ -45 +45 @@\n-query = f'SELECT * FROM users WHERE name = \"{username}\"'\n+query = 'SELECT * FROM users WHERE name = ?'\n+cursor.execute(query, (username,))",
                    explanation="使用参数化查询(占位符?)替代字符串拼接。",
                    references=[CodeReference(title="Semgrep Rule: python-sql-string-concatenation", url="")],
                ),
                confidence=0.97,
                source_agent=self.agent_id,
            ),
            Issue(
                issue_id="SA-002",
                issue_type=IssueType.MAINTAINABILITY,
                severity=Severity.WARNING,
                title="函数圈复杂度过高",
                description="函数 `login` 圈复杂度为12，超过阈值10。建议拆分为更小的函数。",
                location=SourceLocation(file_path="src/auth.py", start_line=40, end_line=70),
                root_cause="登录函数中包含过多条件分支和异常处理逻辑。",
                evidence=Evidence(
                    code_snippet="def login(username: str, password: str):\n    if ...\n    elif ...\n    try ...\n    except ...",
                ),
                confidence=0.88,
                source_agent=self.agent_id,
            ),
            Issue(
                issue_id="SA-003",
                issue_type=IssueType.STYLE,
                severity=Severity.INFO,
                title="命名规范违规",
                description="变量名 'pw' 过于简短，建议使用 'password' 或 'password_hash'。",
                location=SourceLocation(file_path="src/auth.py", start_line=48, end_line=48),
                root_cause="变量命名不符合PEP 8可读性要求。",
                evidence=Evidence(code_snippet="pw = user['password']"),
                confidence=0.92,
                source_agent=self.agent_id,
            ),
        ]
        return AgentResult(agent_id=self.agent_id, status="success", issues=issues, execution_time_ms=120.0)


class MockSemanticReviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(agent_id="semantic_review", agent_name="Semantic Review Agent", timeout_seconds=60))

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "logic", "architecture", "performance"],
            languages=["python", "javascript", "typescript", "java"],
            produces=["issues"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        await asyncio.sleep(0.08)
        issues = [
            Issue(
                issue_id="SEM-001",
                issue_type=IssueType.SECURITY,
                severity=Severity.BLOCKER,
                title="SQL注入漏洞：用户输入未经过滤直接拼接到SQL查询（语义确认）",
                description="经数据流分析，username参数从HTTP请求体直接流向SQL执行点，中间无任何过滤或参数化处理。与历史Issue #234（2023-08生产环境SQL注入事件）模式高度一致。",
                location=SourceLocation(file_path="src/auth.py", start_line=45, end_line=45,
                    ast_path="FunctionDef:login -> Assign:query -> JoinedStr"),
                root_cause="用户输入`username`直接拼接至SQL语句，未经过参数化处理。RAG检索到历史同类缺陷Issue#234。",
                evidence=Evidence(
                    code_snippet='query = f\'SELECT * FROM users WHERE name = "{username}"\'',
                    ast_path="FunctionDef:login -> Assign:query -> JoinedStr",
                    similar_bug_refs=["Issue#234: 2023-08 生产环境SQL注入事件"],
                ),
                fix_suggestion=FixSuggestion(
                    unified_diff="@@ -42,7 +42,10 @@\n def login(username: str, password: str):\n+    if not isinstance(username, str) or len(username) > 256:\n+        raise ValueError('Invalid username')\n-    query = f'SELECT * FROM users WHERE name = \"{username}\"'\n-    cursor.execute(query)\n+    query = 'SELECT * FROM users WHERE name = ?'\n+    cursor.execute(query, (username,))",
                    explanation="1) 使用参数化查询(?); 2) 添加输入校验; 3) 建议密码加盐哈希存储",
                    references=[
                        CodeReference(title="OWASP SQL Injection Prevention", url="https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"),
                    ],
                ),
                confidence=0.95,
                source_agent=self.agent_id,
            ),
            Issue(
                issue_id="SEM-002",
                issue_type=IssueType.BUG,
                severity=Severity.WARNING,
                title="缺少输入校验导致潜在异常",
                description="username和password参数未做类型检查和长度限制，可能导致AttributeError或数据库层异常。",
                location=SourceLocation(file_path="src/auth.py", start_line=42, end_line=42),
                root_cause="函数入口缺少防御性编程必需的输入合法性校验。",
                evidence=Evidence(code_snippet="def login(username: str, password: str):"),
                confidence=0.82,
                source_agent=self.agent_id,
            ),
            Issue(
                issue_id="SEM-003",
                issue_type=IssueType.ARCHITECTURE,
                severity=Severity.SUGGESTION,
                title="建议将认证逻辑与数据库访问层分离",
                description="当前login函数混合了HTTP请求处理、SQL执行和业务逻辑，违反单一职责原则。建议抽取DataMapper层。",
                location=SourceLocation(file_path="src/auth.py", start_line=40, end_line=75),
                root_cause="分层架构未明确分离，认证逻辑与数据访问耦合。",
                evidence=Evidence(code_snippet="def login(username, password):\n    # HTTP parsing + SQL + business logic in one function"),
                confidence=0.71,
                source_agent=self.agent_id,
            ),
        ]
        return AgentResult(agent_id=self.agent_id, status="success", issues=issues, execution_time_ms=350.0)


class MockTestRegressionAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(agent_id="test_regression", agent_name="Test & Regression Agent", timeout_seconds=45))

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["test", "logic", "security", "bug"],
            languages=["python", "javascript", "typescript"],
            produces=["issues", "tests"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        await asyncio.sleep(0.06)
        issues = [
            Issue(
                issue_id="TEST-001",
                issue_type=IssueType.TEST_COVERAGE,
                severity=Severity.WARNING,
                title="变更代码缺少对应的安全测试用例",
                description="auth.py:login函数新增/修改了认证逻辑，但未发现对应的SQL注入防御测试和输入边界测试。",
                location=SourceLocation(file_path="src/auth.py", start_line=40, end_line=75),
                root_cause="代码变更未伴随测试用例更新，测试覆盖率从78%降至71%。",
                evidence=Evidence(
                    code_snippet="# 缺失的测试用例:\n# def test_sql_injection_prevention():\n# def test_login_edge_cases():",
                    similar_bug_refs=[],
                ),
                fix_suggestion=FixSuggestion(
                    unified_diff="+# 建议新增测试:\n+def test_sql_injection_prevention():\n+    malicious = \"' OR 1=1 --\"\n+    assert login(malicious, 'any') is None\n+\n+def test_empty_username():\n+    assert login('', 'password') is None",
                    explanation="为login函数新增SQL注入防御测试和边界条件测试。",
                    references=[],
                ),
                confidence=0.89,
                source_agent=self.agent_id,
            ),
            Issue(
                issue_id="TEST-002",
                issue_type=IssueType.TEST_COVERAGE,
                severity=Severity.SUGGESTION,
                title="建议添加密码哈希相关的回归测试",
                description="密码比较逻辑的修改需要回归测试确保不会破坏现有用户认证流程。",
                location=SourceLocation(file_path="src/auth.py", start_line=48, end_line=50),
                root_cause="认证流程变更属于高风险区域，需回归测试保障。",
                evidence=Evidence(code_snippet="if user['password'] == password:"),
                confidence=0.75,
                source_agent=self.agent_id,
            ),
        ]
        return AgentResult(
            agent_id=self.agent_id, status="success", issues=issues, execution_time_ms=200.0,
            metadata={"coverage_before": 0.78, "coverage_after": 0.71, "regression_risk": "medium"},
        )


class MockRepairPatchAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentConfig(agent_id="repair_patch", agent_name="Repair & Patch Agent", timeout_seconds=60))

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "bug", "performance", "style"],
            languages=["python", "javascript", "typescript"],
            produces=["patches"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        await asyncio.sleep(0.1)
        target_issues = context.get("target_issues", []) if context else []
        patches = [
            {
                "patch_id": "PATCH-001",
                "issue_ids": ["SA-001", "SEM-001"],
                "unified_diff": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -42,7 +42,10 @@ def login(username: str, password: str):\n+    if not isinstance(username, str) or len(username) > 256:\n+        raise ValueError('Invalid username')\n-    query = f'SELECT * FROM users WHERE name = \"{username}\"'\n-    cursor.execute(query)\n+    query = 'SELECT * FROM users WHERE name = ?'\n+    cursor.execute(query, (username,))",
                "explanation": "修复SQL注入：f-string拼接 -> 参数化查询; 新增输入长度校验",
                "files_modified": ["src/auth.py"],
            }
        ]
        return AgentResult(
            agent_id=self.agent_id, status="success", issues=[], execution_time_ms=500.0,
            metadata={"patches": patches, "files_modified": ["src/auth.py"]},
        )


def register_mock_agents():
    from .base import agent_registry
    agent_registry.register(MockStaticAnalysisAgent())
    agent_registry.register(MockSemanticReviewAgent())
    agent_registry.register(MockTestRegressionAgent())
    agent_registry.register(MockRepairPatchAgent())
    return agent_registry
