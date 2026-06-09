"""LLM-powered patch generation for code fixes."""

import json
import logging
from src.llm.mock_client import MockLLMClient

logger = logging.getLogger(__name__)

REPAIR_SYSTEM_PROMPT = """You are a senior software engineer fixing code defects. Generate a unified diff patch.
Rules:
1. Minimal change — fix only the reported issue, don't refactor
2. Preserve existing code style
3. Use parameterized queries for SQL injection, add input validation, etc.
4. Output ONLY valid JSON:
{"patches": [{"patch_id": "PATCH-XXX", "issue_ids": ["..."], "unified_diff": "--- a/file\n+++ b/file\n@@ ...", "explanation": "...", "files_modified": ["file.py"]}]}"""


async def generate_patches(
    original_code: str,
    file_path: str,
    issues: list[dict],
    conventions: list[str] | None = None,
    use_mock: bool = True,
) -> list[dict]:
    """Generate fix patches for a list of issues in the given code."""
    if use_mock:
        return _mock_generate(original_code, file_path, issues)

    from config.settings import settings
    from src.llm.deepseek_client import DeepSeekClient
    client = DeepSeekClient(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
    )

    issues_text = "\n".join(
        f"## {i.get('id', '?')}: {i.get('title', '')}\n"
        f"Root cause: {i.get('root_cause', '')}\n"
        f"Location: {i.get('file_path', file_path)}:{i.get('line', '?')}\n"
        for i in issues
    )
    conventions_text = "\n".join(f"- {c}" for c in (conventions or []))

    response = await client.complete(
        messages=[
            {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"## Issues to fix\n{issues_text}\n\n"
                f"## Coding conventions\n{conventions_text or 'PEP 8'}\n\n"
                f"## Original code ({file_path})\n```python\n{original_code[:5000]}\n```"
            )},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return _parse_response(response.content)


def _mock_generate(code: str, file_path: str, issues: list[dict]) -> list[dict]:
    """Generate mock patches based on issue types."""
    patches = []
    for issue in issues:
        issue_id = issue.get("id", issue.get("issue_id", "UNKNOWN"))
        title = issue.get("title", "")
        title_lower = title.lower()

        if "sql" in title_lower or "注入" in title or "injection" in title_lower:
            # Replace f-string SQL with parameterized query
            if 'f"' in code or "f'" in code:
                fixed = code.replace('f"', '"').replace("f'", "'")
                # Replace {var} with ? placeholder (simplified)
                import re
                fixed = re.sub(r'\{(\w+)\}', '?', fixed)
                diff = f"--- a/{file_path}\n+++ b/{file_path}\n@@ -1 +1 @@\n-{code.split(chr(10))[0]}\n+{fixed.split(chr(10))[0]}"
                patches.append({
                    "patch_id": f"PATCH-{len(patches)+1:03d}",
                    "issue_ids": [issue_id],
                    "unified_diff": diff,
                    "explanation": "Replace f-string SQL concatenation with parameterized query placeholders",
                    "files_modified": [file_path],
                })

        elif "validation" in title_lower or "校验" in title or "input" in title_lower:
            func_match = None
            for line in code.split("\n"):
                if line.strip().startswith("def "):
                    func_match = line.strip()
                    break
            if func_match:
                indent = "    "
                validation = (
                    f"{indent}if not isinstance(username, str) or len(username) > 256:\n"
                    f"{indent}    raise ValueError('Invalid input')\n"
                )
                diff = f"--- a/{file_path}\n+++ b/{file_path}\n@@ -1,0 +1,2 @@\n+{validation}"
                patches.append({
                    "patch_id": f"PATCH-{len(patches)+1:03d}",
                    "issue_ids": [issue_id],
                    "unified_diff": diff,
                    "explanation": "Add input validation at function entry point",
                    "files_modified": [file_path],
                })

    if not patches:
        patches.append({
            "patch_id": f"PATCH-{len(patches)+1:03d}",
            "issue_ids": [i.get("id", i.get("issue_id", "UNKNOWN")) for i in issues],
            "unified_diff": f"--- a/{file_path}\n+++ b/{file_path}\n@@ -1,1 +1,1 @@\n-# TODO: fix reported issues\n+# Fixed (mock patch)",
            "explanation": "Generated placeholder patch — real fix requires LLM with API key",
            "files_modified": [file_path],
        })

    return patches


def _parse_response(content: str) -> list[dict]:
    """Parse LLM JSON response into patch dicts."""
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        data = json.loads(content.strip())
        return data.get("patches", [])
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse patch generation response")
        return []
