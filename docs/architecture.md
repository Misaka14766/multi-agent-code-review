# Architecture Decision Record (ADR)

## ADR-001: LangGraph for Workflow Orchestration

**Decision**: Use LangGraph StateGraph for the review workflow.

**Rationale**:
- State machine model naturally maps to the review pipeline (ingest → classify → parallel dispatch → arbitrate → gate → repair → report)
- Native `Send()` API for parallel agent fan-out
- Support for cycles (repair → re-review loop)
- Strong LangChain ecosystem integration
- Active community and academic recognition

**Alternatives considered**:
- CrewAI: sequential agent model, doesn't support parallel dispatch natively
- Custom state machine: more code to maintain, less flexibility for future changes
- Prefect/Airflow: overkill for a single-machine pipeline, adds deployment complexity

## ADR-002: ChromaDB for Vector Storage (Initial)

**Decision**: Use ChromaDB in-process for the RAG vector store (Phase 4). Migrate to Milvus if scaling needed.

**Rationale**:
- Zero-configuration — runs in-process without separate server
- Persistent storage to disk
- Supports hybrid retrieval (vector + metadata filtering)
- Works on Windows without Docker

**Future**: The `ChromaVectorStore` wrapper uses the same interface we would replace with Milvus.

## ADR-003: Mock LLM as First-Class Citizen

**Decision**: All LLM interactions go through `LLMClient` ABC. Default is `MockLLMClient`.

**Rationale**:
- Enables full development and testing without API keys
- Switch to DeepSeek by setting `LLM_PROVIDER=deepseek` in `.env`
- Mock responses are deterministic, enabling reproducible demos
- Real DeepSeek client has retry/rate-limit/streaming support built in

## ADR-004: Uniform `list[Issue]` Output from All Agents

**Decision**: All agents produce `AgentResult` containing `list[Issue]`, regardless of source (Semgrep, LLM, coverage report).

**Rationale**:
- Simplifies arbitration node — merge/dedup/conflict pipeline works on one type
- `Issue` model includes source_agent field for traceability
- Standardized severity (blocker/warning/suggestion/info) and confidence scoring

## ADR-005: Single-Pass Repair for M1

**Decision**: Repair → Verify → Report in linear flow. Re-review cycle (repair → re-classify → re-review) is built but disabled.

**Rationale**:
- Mock agents produce identical results on re-review, causing infinite loops
- Real LLM-based agents will produce different results after repair (making the cycle meaningful)
- The `repair_loop_decision` function has a one-line change to enable the full cycle

## ADR-006: Tool Graceful Degradation

**Decision**: All tools (Semgrep, Pylint, Tree-sitter) fail gracefully if not installed — returning empty results.

**Rationale**:
- Development on Windows without native tool dependencies
- Pipeline never crashes due to missing external tools
- Users install tools incrementally as needed

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│  CLI (run_cli.py)  |  API (FastAPI)  |  Dashboard (HTML)   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                   Orchestration Layer                       │
│  ReviewOrchestrator  →  LangGraph StateGraph                │
│  Nodes: ingest → classify → [SA ‖ SR ‖ TR] → arbitrate     │
│         → quality_gate → [repair → verify] → report        │
└─────────────────────────────┼───────────────────────────────┘
              ┌───────────────┼───────────────┐
┌─────────────┴──────┐ ┌──────┴──────┐ ┌─────┴──────────────┐
│   Agent Layer       │ │ Knowledge   │ │   Tool Layer       │
│ • Static Analysis   │ │ • RAG Engine│ │ • Semgrep          │
│ • Semantic Review   │ │ • ChromaDB  │ │ • Pylint/ESLint    │
│ • Test & Regression │ │ • Embeddings│ │ • Tree-sitter      │
│ • Repair & Patch    │ │ • Seed Data │ │ • Sandbox          │
└─────────────────────┘ └─────────────┘ └────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                      Data Layer                             │
│  Code Repos  |  Chroma Vector Store  |  Review History      │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
PR/Code Input
  → PRInfo (Pydantic model)
    → ReviewState (LangGraph TypedDict)
      → [Agent 1..N] → list[Issue]
        → Arbitration (dedup + merge)
          → QualityGateDecision
            → RepairResult (Patch + Verification)
              → ReviewReport (JSON/Markdown)
```
