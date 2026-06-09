"""Real Semantic Review Agent — deep code analysis using RAG + LLM.

In mock mode (default): uses MockLLMClient + hash-based mock embeddings.
With DEEPSEEK_API_KEY set: uses real DeepSeek API for both LLM and embeddings.
"""

import json
import logging
import time

from src.agents.base import BaseAgent, AgentConfig, AgentCapability, AgentResult
from src.models.pr import PRInfo
from src.models.issue import Issue, IssueType, Severity, SourceLocation, Evidence, FixSuggestion, CodeReference
from src.knowledge.engine import RAGEngine
from src.knowledge.vector_store import ChromaVectorStore
from src.knowledge.embeddings import EmbeddingGenerator
from src.knowledge.schemas import SearchQuery, KnowledgeType
from src.llm.mock_client import MockLLMClient
from .context_builder import build_review_context

logger = logging.getLogger(__name__)

# Singleton RAG engine (initialized lazily)
_rag_engine: RAGEngine | None = None
_rag_initialized: bool = False


def _get_rag_engine() -> RAGEngine:
    """Get or create the RAG engine singleton."""
    global _rag_engine, _rag_initialized
    if _rag_engine is None:
        embedding_gen = EmbeddingGenerator()
        vector_store = ChromaVectorStore()
        _rag_engine = RAGEngine(vector_store, embedding_gen)
    return _rag_engine


async def _init_rag_if_needed() -> bool:
    """Seed the vector store with initial knowledge if empty. Returns True if ready."""
    global _rag_initialized
    if _rag_initialized:
        return True
    try:
        engine = _get_rag_engine()
        from src.knowledge.seed_data import get_seed_documents
        count = await engine.index_documents(get_seed_documents())
        logger.info("RAG initialized with %d seed documents", count)
        _rag_initialized = True
        return True
    except Exception as e:
        logger.warning("RAG initialization failed (ChromaDB may not be installed): %s", e)
        return False


class SemanticReviewAgent(BaseAgent):
    """Semantic code reviewer using RAG retrieval + LLM analysis.

    Pipeline:
      1. RAG retrieval → similar bugs + coding standards
      2. Build context (code + RAG results)
      3. LLM call → structured JSON response
      4. Parse response → list[Issue]
    """

    def __init__(self, config: AgentConfig | None = None, use_mock_llm: bool = True):
        cfg = config or AgentConfig(agent_id="semantic_review", agent_name="Semantic Review Agent", timeout_seconds=60)
        super().__init__(cfg)
        self.use_mock_llm = use_mock_llm
        self._llm = MockLLMClient() if use_mock_llm else None

    def get_capability(self) -> AgentCapability:
        return AgentCapability(
            change_types=["security", "logic", "architecture", "performance"],
            languages=["python", "javascript", "typescript", "java"],
            produces=["issues"],
        )

    async def analyze(self, pr_info: PRInfo, context: dict | None = None) -> AgentResult:
        start = time.time()

        # Step 1: RAG retrieval
        rag_results = []
        rag_ready = await _init_rag_if_needed()
        if rag_ready and pr_info.files_changed:
            engine = _get_rag_engine()
            for f in pr_info.files_changed:
                code = f.new_content or f.old_content or ""
                if code.strip():
                    try:
                        results = await engine.search_similar_bugs(code, top_k=3)
                        rag_results.extend(results)
                    except Exception as e:
                        logger.warning("RAG search failed for %s: %s", f.file_path, e)

        # Step 2: Build review context
        ctx = build_review_context(pr_info, rag_results)

        # Step 3: LLM call (mock or real)
        if self.use_mock_llm:
            issues = await self._mock_analyze(pr_info, ctx)
        else:
            issues = await self._llm_analyze(pr_info, ctx)

        elapsed = (time.time() - start) * 1000
        return AgentResult(
            agent_id=self.agent_id,
            status="success",
            issues=issues,
            execution_time_ms=elapsed,
            metadata={
                "rag_results_count": len(rag_results),
                "rag_ready": rag_ready,
                "llm_mode": "mock" if self.use_mock_llm else "deepseek",
            },
        )

    async def _mock_analyze(self, pr_info: PRInfo, ctx: dict) -> list[Issue]:
        """Use MockLLMClient to generate review (deterministic canned responses)."""
        code_text = "\n".join(
            f"// {s['file_path']}\n{s['content']}" for s in ctx.get("code_snippets", [])
        )
        messages = [
            {"role": "system", "content": "You are a code reviewer. Output JSON with 'issues' array."},
            {"role": "user", "content": f"Review this code:\n```\n{code_text[:3000]}\n```"},
        ]

        try:
            llm = MockLLMClient()
            response = await llm.complete(messages)
        except Exception:
            return self._hardcoded_issues(pr_info)

        return self._parse_llm_response(response.content, pr_info)

    async def _llm_analyze(self, pr_info: PRInfo, ctx: dict) -> list[Issue]:
        """Use real DeepSeek LLM for analysis (requires API key)."""
        if self._llm is None:
            from config.settings import settings
            from src.llm.deepseek_client import DeepSeekClient
            self._llm = DeepSeekClient(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
            )

        code_text = "\n".join(
            f"// {s['file_path']}\n{s['content']}" for s in ctx.get("code_snippets", [])
        )
        similar_bugs_text = "\n".join(
            f"- [{b['similarity']:.0%}] {b['title']}: {b['root_cause']}"
            for b in ctx.get("similar_bugs", [])
        )
        conventions_text = "\n".join(f"- {c}" for c in ctx.get("conventions", []))

        system_prompt = (
            "你是一位资深代码审查专家。请对以下代码变更进行深度语义审查。"
            "识别安全漏洞、逻辑错误、性能问题、架构违规。"
            "对每个问题提供根因分析、影响面评估和修复建议。"
            "仅输出JSON，格式：{\"issues\": [{...}]}"
        )
        user_prompt = (
            f"## 历史相似缺陷 (RAG)\n{similar_bugs_text or '无'}\n\n"
            f"## 编码规范\n{conventions_text or '无'}\n\n"
            f"## 待审查代码\n```\n{code_text[:6000]}\n```"
        )

        response = await self._llm.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return self._parse_llm_response(response.content, pr_info)

    @staticmethod
    def _normalize_severity(value: str) -> Severity:
        """Map LLM severity strings to our Severity enum."""
        v = value.strip().lower()
        mapping = {
            "critical": Severity.BLOCKER, "high": Severity.BLOCKER, "blocker": Severity.BLOCKER,
            "medium": Severity.WARNING, "warning": Severity.WARNING,
            "low": Severity.SUGGESTION, "suggestion": Severity.SUGGESTION,
            "info": Severity.INFO, "information": Severity.INFO, "note": Severity.INFO,
        }
        return mapping.get(v, Severity.WARNING)

    @staticmethod
    def _normalize_issue_type(value: str) -> IssueType:
        """Map LLM issue type strings to our IssueType enum."""
        v = value.strip().lower().replace(" ", "_").replace("-", "_")
        mapping = {
            "security": IssueType.SECURITY, "vulnerability": IssueType.SECURITY,
            "bug": IssueType.BUG, "logic_error": IssueType.BUG, "error": IssueType.BUG,
            "performance": IssueType.PERFORMANCE, "inefficiency": IssueType.PERFORMANCE,
            "maintainability": IssueType.MAINTAINABILITY, "code_quality": IssueType.MAINTAINABILITY,
            "style": IssueType.STYLE, "formatting": IssueType.STYLE,
            "architecture": IssueType.ARCHITECTURE, "design": IssueType.ARCHITECTURE,
            "test_coverage": IssueType.TEST_COVERAGE, "testing": IssueType.TEST_COVERAGE,
        }
        return mapping.get(v, IssueType.BUG)

    def _parse_llm_response(self, content: str, pr_info: PRInfo) -> list[Issue]:
        """Parse LLM JSON response into Issue objects. Tolerates type mismatches from the LLM."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            data = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse LLM response as JSON")
            return self._hardcoded_issues(pr_info)

        fallback_path = pr_info.files_changed[0].file_path if pr_info.files_changed else ""

        issues: list[Issue] = []
        for i, item in enumerate(data.get("issues", [])):
            try:
                # --- location: tolerate string or dict ---
                loc = item.get("location", {})
                if isinstance(loc, str):
                    loc = {"file_path": fallback_path, "start_line": 0, "end_line": 0}

                # --- evidence: tolerate string, dict, or missing ---
                evidence = item.get("evidence", {})
                if isinstance(evidence, str):
                    evidence = {"code_snippet": evidence}
                if not isinstance(evidence, dict):
                    evidence = {}

                # --- fix_suggestion: tolerate string or dict ---
                fix = item.get("fix_suggestion")
                if isinstance(fix, str):
                    fix = {"unified_diff": "", "explanation": fix}

                # --- references: tolerate list of strings ---
                refs_raw = fix.get("references", []) if isinstance(fix, dict) else []
                refs = []
                for r in refs_raw:
                    if isinstance(r, str):
                        refs.append(CodeReference(title=r))
                    elif isinstance(r, dict):
                        refs.append(CodeReference(**r))

                issues.append(Issue(
                    issue_id=f"SEM-LLM-{i+1:03d}",
                    issue_type=self._normalize_issue_type(item.get("issue_type", "bug")),
                    severity=self._normalize_severity(item.get("severity", "warning")),
                    title=str(item.get("title", "Untitled Issue")),
                    description=str(item.get("description", "")),
                    location=SourceLocation(
                        file_path=loc.get("file_path", fallback_path),
                        start_line=int(loc.get("start_line", 0)),
                        end_line=int(loc.get("end_line", 0)),
                    ),
                    root_cause=str(item.get("root_cause", "")),
                    evidence=Evidence(
                        code_snippet=str(evidence.get("code_snippet", "")),
                        similar_bug_refs=evidence.get("similar_bug_refs", []),
                    ),
                    fix_suggestion=FixSuggestion(
                        unified_diff=fix.get("unified_diff", ""),
                        explanation=fix.get("explanation", ""),
                        references=refs,
                    ) if fix else None,
                    confidence=float(item.get("confidence", 0.75)),
                    source_agent=self.agent_id,
                ))
            except Exception as e:
                logger.warning("Failed to parse issue %d: %s", i, e)
                continue

        return issues

    def _hardcoded_issues(self, pr_info: PRInfo) -> list[Issue]:
        """Fallback issues when LLM is unavailable."""
        file_path = pr_info.files_changed[0].file_path if pr_info.files_changed else "unknown"
        return [
            Issue(
                issue_id="SEM-FB-001",
                issue_type=IssueType.SECURITY,
                severity=Severity.WARNING,
                title="LLM不可用 — 建议手动审查",
                description="LLM服务暂不可用(Mock模式或API未配置)。请手动审查代码中的安全漏洞和逻辑错误。设置DEEPSEEK_API_KEY以启用AI审查。",
                location=SourceLocation(file_path=file_path, start_line=1, end_line=1),
                root_cause="LLM client not available",
                evidence=Evidence(code_snippet=""),
                confidence=0.5,
                source_agent=self.agent_id,
            )
        ]
