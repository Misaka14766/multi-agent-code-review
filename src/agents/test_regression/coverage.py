"""Coverage report parsing and gap analysis."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class CoverageGap:
    file: str
    line: int
    reason: str = ""


@dataclass
class CoverageReport:
    files_covered: int = 0
    total_lines: int = 0
    covered_lines: int = 0
    coverage_pct: float = 0.0
    gaps: list[CoverageGap] = field(default_factory=list)


def parse_coverage_xml(xml_path: str) -> CoverageReport:
    """Parse a coverage.py XML report and extract coverage gaps."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError):
        return CoverageReport()

    report = CoverageReport()
    for pkg in root.findall(".//package"):
        for cls in pkg.findall("classes/class"):
            filename = cls.get("filename", "")
            for line in cls.findall("lines/line"):
                hits = int(line.get("hits", "0"))
                line_num = int(line.get("number", "0"))
                report.total_lines += 1
                if hits > 0:
                    report.covered_lines += 1
                else:
                    report.gaps.append(CoverageGap(file=filename, line=line_num, reason="Not covered by tests"))

    if report.total_lines > 0:
        report.coverage_pct = (report.covered_lines / report.total_lines) * 100
    return report


def analyze_coverage_for_changes(
    coverage_path: str | None,
    changed_files: list[str],
) -> CoverageReport:
    """Analyze coverage for a set of changed files."""
    report = parse_coverage_xml(coverage_path) if coverage_path else CoverageReport()

    # Filter gaps to only changed files
    changed_set = set(changed_files)
    relevant_gaps = [g for g in report.gaps if any(cf in g.file for cf in changed_set)]
    report.gaps = relevant_gaps
    return report
