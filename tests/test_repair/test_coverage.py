"""Tests for coverage analysis module."""
from src.agents.test_regression.coverage import CoverageReport, CoverageGap, parse_coverage_xml


class TestCoverageGap:
    def test_create(self):
        gap = CoverageGap(file="test.py", line=10, reason="Not covered")
        assert gap.file == "test.py"
        assert gap.line == 10


class TestCoverageReport:
    def test_default_empty(self):
        report = CoverageReport()
        assert report.coverage_pct == 0.0
        assert report.gaps == []

    def test_with_data(self):
        gaps = [CoverageGap(file="a.py", line=1), CoverageGap(file="a.py", line=2)]
        report = CoverageReport(
            files_covered=1, total_lines=10, covered_lines=8,
            coverage_pct=80.0, gaps=gaps,
        )
        assert len(report.gaps) == 2
        assert report.coverage_pct == 80.0


class TestParseCoverageXML:
    def test_missing_file_returns_empty(self):
        report = parse_coverage_xml("nonexistent.xml")
        assert report.coverage_pct == 0.0

    def test_invalid_xml_returns_empty(self, tmp_path):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("not xml")
        report = parse_coverage_xml(str(bad_xml))
        assert report.coverage_pct == 0.0
