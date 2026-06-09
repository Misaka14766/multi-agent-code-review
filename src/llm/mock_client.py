import json
import hashlib
from .base import LLMClient, LLMResponse


MOCK_RESPONSES = {
    "semantic_review": {
        "content": json.dumps({
            "issues": [
                {
                    "issue_id": "SEM-001",
                    "issue_type": "security",
                    "severity": "blocker",
                    "title": "SQL注入漏洞：用户输入未经过滤直接拼接到SQL查询",
                    "description": "在login函数中，username参数通过f-string直接拼接到SQL语句中，攻击者可通过构造恶意username实现SQL注入攻击。",
                    "location": {
                        "file_path": "src/auth.py",
                        "start_line": 45,
                        "end_line": 45,
                        "ast_path": "FunctionDef:login -> Assign:query -> JoinedStr"
                    },
                    "root_cause": "使用f-string拼接用户输入到SQL查询，未使用参数化查询。违反了OWASP SQL注入防护规范。",
                    "evidence": {
                        "code_snippet": "query = f'SELECT * FROM users WHERE name = \\\"{username}\\\"'",
                        "ast_path": "FunctionDef:login -> Assign:query -> JoinedStr",
                        "similar_bug_refs": ["CVE-2023-XXXX", "OWASP-SQL-Injection"]
                    },
                    "fix_suggestion": {
                        "unified_diff": "@@ -45,3 +45,3 @@\n-query = f'SELECT * FROM users WHERE name = \\\"{username}\\\"'\n+query = 'SELECT * FROM users WHERE name = ?'\n+cursor.execute(query, (username,))",
                        "explanation": "使用参数化查询替代字符串拼接，将用户输入与SQL逻辑分离",
                        "references": [{"title": "OWASP SQL Injection Prevention Cheat Sheet", "url": "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"}]
                    },
                    "confidence": 0.95,
                    "source_agent": "semantic_review",
                    "verification_status": "unverified"
                },
                {
                    "issue_id": "SEM-002",
                    "issue_type": "bug",
                    "severity": "warning",
                    "title": "缺少输入长度校验",
                    "description": "username参数未进行长度校验，超长输入可能导致缓冲区溢出或数据库错误。",
                    "location": {
                        "file_path": "src/auth.py",
                        "start_line": 42,
                        "end_line": 42
                    },
                    "root_cause": "函数入口缺少对用户输入的基础合法性校验（长度、格式）。",
                    "evidence": {
                        "code_snippet": "def login(username: str, password: str):",
                        "similar_bug_refs": []
                    },
                    "confidence": 0.82,
                    "source_agent": "semantic_review",
                    "verification_status": "unverified"
                },
                {
                    "issue_id": "SEM-003",
                    "issue_type": "performance",
                    "severity": "suggestion",
                    "title": "建议对密码字段使用哈希后比较",
                    "description": "密码明文直接比较存在安全隐患，且数据库查询未使用索引优化。",
                    "location": {
                        "file_path": "src/auth.py",
                        "start_line": 48,
                        "end_line": 50
                    },
                    "root_cause": "密码存储与比较未遵循安全最佳实践。",
                    "evidence": {
                        "code_snippet": "if user['password'] == password:",
                        "similar_bug_refs": []
                    },
                    "confidence": 0.78,
                    "source_agent": "semantic_review",
                    "verification_status": "unverified"
                }
            ]
        }, ensure_ascii=False),
        "model": "mock",
        "tokens": {"prompt": 500, "completion": 300}
    },
    "repair_patch": {
        "content": json.dumps({
            "patches": [
                {
                    "patch_id": "PATCH-001",
                    "issue_ids": ["SA-001", "SEM-001"],
                    "unified_diff": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -42,7 +42,10 @@ def login(username: str, password: str)\n-    query = f'SELECT * FROM users WHERE name = \"{username}\"'\n-    cursor.execute(query)\n+    if len(username) > 256:\n+        raise ValueError(\"Username too long\")\n+    query = 'SELECT * FROM users WHERE name = ?'\n+    cursor.execute(query, (username,))",
                    "explanation": "1. 将f-string拼接改为参数化查询(?); 2. 添加输入长度校验(256字符上限)",
                    "files_modified": ["src/auth.py"]
                }
            ]
        }, ensure_ascii=False),
        "model": "mock",
        "tokens": {"prompt": 400, "completion": 200}
    },
    "test_generation": {
        "content": json.dumps({
            "test_cases": [
                {
                    "test_name": "test_sql_injection_prevention",
                    "test_code": "def test_sql_injection_prevention():\n    malicious_input = \"' OR 1=1 --\"\n    result = login(malicious_input, 'password')\n    assert result is None  # Should not authenticate",
                    "target_issue": "SA-001"
                },
                {
                    "test_name": "test_username_length_validation",
                    "test_code": "def test_username_length_validation():\n    long_name = 'A' * 500\n    with pytest.raises(ValueError):\n        login(long_name, 'password')",
                    "target_issue": "SEM-002"
                }
            ]
        }, ensure_ascii=False),
        "model": "mock",
        "tokens": {"prompt": 300, "completion": 200}
    },
    "classification": {
        "content": json.dumps({
            "primary_type": "security",
            "secondary_types": ["logic"],
            "affected_modules": ["auth", "database"],
            "risk_score": 0.85,
            "recommended_agents": ["static_analysis", "semantic_review", "test_regression"]
        }, ensure_ascii=False),
        "model": "mock",
        "tokens": {"prompt": 100, "completion": 50}
    },
    "default": {
        "content": "{}",
        "model": "mock",
        "tokens": {"prompt": 0, "completion": 0}
    }
}


class MockLLMClient(LLMClient):
    def __init__(self):
        self._responses = MOCK_RESPONSES

    def _fingerprint(self, messages: list[dict]) -> str:
        text = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        for key in ["semantic_review", "repair_patch", "test_generation", "classification"]:
            if key in text:
                return key
        return "default"

    async def complete(self, messages: list[dict], **kwargs) -> LLMResponse:
        key = self._fingerprint(messages)
        canned = self._responses.get(key, self._responses["default"])
        return LLMResponse(
            content=canned["content"],
            model=canned["model"],
            prompt_tokens=canned["tokens"]["prompt"],
            completion_tokens=canned["tokens"]["completion"],
        )
