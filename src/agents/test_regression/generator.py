"""LLM-powered test case generation for uncovered code paths."""

import json
import logging
from src.llm.mock_client import MockLLMClient

logger = logging.getLogger(__name__)

TEST_GENERATION_SYSTEM_PROMPT = """You are a senior test engineer. Generate pytest test cases for the given code.
Focus on: edge cases, error paths, security boundaries, and input validation.
Output ONLY valid JSON in this format:
{"test_cases": [{"test_name": "test_xxx", "test_code": "...", "target_issue": "optional issue id", "description": "what this tests"}]}"""


async def generate_tests(
    code: str,
    issues: list[dict] | None = None,
    use_mock: bool = True,
) -> list[dict]:
    """Generate test cases for the given code, optionally targeting specific issues."""
    if use_mock:
        return _mock_generate(code, issues or [])

    from config.settings import settings
    from src.llm.deepseek_client import DeepSeekClient
    client = DeepSeekClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
    )

    issues_text = ""
    if issues:
        issues_text = "## Issues to cover\n" + "\n".join(
            f"- {i.get('id', '?')}: {i.get('title', '')}" for i in issues
        )

    response = await client.complete(
        messages=[
            {"role": "system", "content": TEST_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate tests for this code:\n```python\n{code[:5000]}\n```\n{issues_text}"},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return _parse_response(response.content)


def _mock_generate(code: str, issues: list[dict]) -> list[dict]:
    """Mock test generation returning canned but useful test stubs."""
    func_name = "unknown_function"
    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("def "):
            func_name = line[4:].split("(")[0].strip()
            break

    tests = []

    # Always generate an edge case test
    tests.append({
        "test_name": f"test_{func_name}_empty_input",
        "test_code": f"def test_{func_name}_empty_input():\n    result = {func_name}('', '')\n    assert result is None or isinstance(result, dict)",
        "description": "Verify function handles empty input gracefully",
    })

    # If issues mention SQL/injection, generate security test
    issue_texts = " ".join(i.get("title", "") + i.get("description", "") for i in issues).lower()
    if "sql" in issue_texts or "injection" in issue_texts or "注入" in issue_texts:
        tests.append({
            "test_name": f"test_{func_name}_sql_injection_prevention",
            "test_code": (
                f"def test_{func_name}_sql_injection_prevention():\n"
                f'    malicious = "\' OR 1=1 --"\n'
                f"    result = {func_name}(malicious, 'any')\n"
                f"    # Should not authenticate or raise controlled error\n"
                f"    assert result is None or 'error' in str(result).lower()"
            ),
            "target_issue": next((i.get("id", "") for i in issues if "sql" in i.get("title", "").lower()), ""),
            "description": "Verify SQL injection payloads are properly handled",
        })

    # Always generate a type/validation test
    tests.append({
        "test_name": f"test_{func_name}_invalid_types",
        "test_code": f"def test_{func_name}_invalid_types():\n    try:\n        {func_name}(None, None)\n    except (TypeError, ValueError, AttributeError):\n        pass",
        "description": "Verify function handles None/invalid type inputs",
    })

    return tests


def _parse_response(content: str) -> list[dict]:
    """Parse LLM JSON response into test case dicts."""
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        data = json.loads(content.strip())
        return data.get("test_cases", [])
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse test generation response")
        return [{"test_name": "test_fallback", "test_code": "# Failed to generate tests", "description": "Parse error"}]
