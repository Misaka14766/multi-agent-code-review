"""Tests for graph compilation and structure."""
from src.orchestrator.graph import build_review_graph


class TestGraphCompilation:
    def test_graph_compiles(self):
        graph = build_review_graph()
        assert graph is not None

    def test_graph_has_required_nodes(self):
        graph = build_review_graph()
        nodes = list(graph.get_graph().nodes.keys())
        required = [
            "__start__", "ingest_pr", "classify_changes",
            "static_analysis", "semantic_review", "test_regression",
            "arbitrate", "quality_gate", "repair", "verify_repair",
            "generate_report", "__end__",
        ]
        for node in required:
            assert node in nodes, f"Missing node: {node}"

    def test_entry_point(self):
        graph = build_review_graph()
        edges = list(graph.get_graph().edges)
        start_edges = [e for e in edges if e.source == "__start__"]
        assert len(start_edges) == 1
        assert start_edges[0].target == "ingest_pr"

    def test_report_ends(self):
        graph = build_review_graph()
        edges = list(graph.get_graph().edges)
        report_edges = [e for e in edges if e.source == "generate_report"]
        assert len(report_edges) == 1
        assert report_edges[0].target == "__end__"

    def test_all_edges_connect_known_nodes(self):
        graph = build_review_graph()
        nodes = set(graph.get_graph().nodes.keys())
        for edge in graph.get_graph().edges:
            assert edge.source in nodes, f"Unknown source: {edge.source}"
            assert edge.target in nodes, f"Unknown target: {edge.target}"
