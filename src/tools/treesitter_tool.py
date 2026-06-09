"""Tree-sitter tool — AST parsing for code structure analysis."""

from .base import ToolInterface, ToolPlan, ToolResult, StructuredResult


class TreeSitterTool(ToolInterface):
    """Parses source code into AST and provides structural analysis."""

    def __init__(self):
        super().__init__("treesitter")
        self._parser = None
        self._language = None

    def _ensure_parser(self, lang: str = "python"):
        """Lazy-load tree-sitter parser for the given language."""
        if self._parser is not None and self._language == lang:
            return True
        try:
            import tree_sitter_python
            from tree_sitter import Language, Parser
            self._language = lang
            py_lang = Language(tree_sitter_python.language())
            self._parser = Parser(py_lang)
            return True
        except ImportError:
            return False

    async def plan(self, context: dict) -> ToolPlan:
        target_file = context.get("target_file", "")
        return ToolPlan(
            tool_name="treesitter",
            parameters={"target_file": target_file, "language": context.get("language", "python")},
            reason="AST-based code structure analysis",
            timeout_seconds=30,
        )

    async def execute(self, plan: ToolPlan) -> ToolResult:
        import time
        start = time.time()
        target = plan.parameters.get("target_file", "")
        lang = plan.parameters.get("language", "python")

        if not target:
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name="treesitter", exit_code=-1, stderr="No target file specified", execution_time_ms=elapsed)

        try:
            with open(target, "r", encoding="utf-8") as f:
                source = f.read()
        except (FileNotFoundError, IOError) as e:
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name="treesitter", exit_code=-1, stderr=str(e), execution_time_ms=elapsed)

        # If source is passed directly in context (for in-memory review)
        if not source.strip() and "source_code" in plan.parameters:
            source = plan.parameters["source_code"]

        if not self._ensure_parser(lang):
            elapsed = (time.time() - start) * 1000
            return ToolResult(tool_name="treesitter", exit_code=-1, stderr="tree-sitter not installed. Install: pip install tree-sitter tree-sitter-python", execution_time_ms=elapsed)

        tree = self._parser.parse(bytes(source, "utf-8"))
        elapsed = (time.time() - start) * 1000

        # Collect function definitions and their line ranges
        functions = []
        self._walk_tree(tree.root_node, source, functions)

        import json
        stdout = json.dumps({"functions": functions, "total_lines": source.count('\n') + 1}, ensure_ascii=False)
        return ToolResult(tool_name="treesitter", exit_code=0, stdout=stdout, execution_time_ms=elapsed)

    def _walk_tree(self, node, source: str, functions: list, depth: int = 0):
        """Recursively walk the AST to find function/class definitions."""
        if node.type in ("function_definition", "method_definition", "class_definition"):
            name_node = node.child_by_field_name("name")
            name = source[name_node.start_byte:name_node.end_byte] if name_node else "unknown"
            functions.append({
                "type": node.type,
                "name": name,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })
        for child in node.children:
            self._walk_tree(child, source, functions, depth + 1)

    def parse(self, raw: ToolResult) -> StructuredResult:
        import json
        if raw.exit_code < 0:
            return StructuredResult(tool_name="treesitter", findings=[], summary=f"Tree-sitter unavailable: {raw.stderr}", raw=raw)
        try:
            data = json.loads(raw.stdout)
        except json.JSONDecodeError:
            return StructuredResult(tool_name="treesitter", findings=[], summary="Failed to parse AST output", raw=raw)

        functions = data.get("functions", [])
        findings = [
            {"type": f["type"], "name": f["name"], "start_line": f["start_line"], "end_line": f["end_line"]}
            for f in functions
        ]
        return StructuredResult(
            tool_name="treesitter",
            findings=findings,
            summary=f"Parsed {len(functions)} function(s)/class(es), {data.get('total_lines', 0)} total lines",
            raw=raw,
        )

    async def validate(self, result: StructuredResult) -> bool:
        return result.raw is not None
