"""Tests for PR-related models."""
from src.models.pr import PRInfo, FileDiff, ChangeType


class TestFileDiff:
    def test_basic_file_diff(self):
        fd = FileDiff(file_path="src/auth.py", change_type="modified", language="python")
        assert fd.file_path == "src/auth.py"
        assert fd.language == "python"

    def test_file_diff_with_content(self):
        fd = FileDiff(
            file_path="src/new.py", change_type="added",
            new_content="print(1)", language="python",
        )
        assert fd.new_content == "print(1)"
        assert fd.old_content is None


class TestPRInfo:
    def test_pr_info_basic(self, sample_file_diff):
        pr = PRInfo(
            pr_id="test", title="Test PR",
            files_changed=[sample_file_diff], files_count=1,
            additions=5, deletions=2,
        )
        assert pr.pr_id == "test"
        assert len(pr.files_changed) == 1
        assert pr.additions == 5

    def test_pr_info_serialization(self, sample_pr_info):
        data = sample_pr_info.model_dump()
        restored = PRInfo(**data)
        assert restored.pr_id == sample_pr_info.pr_id
        assert restored.files_count == sample_pr_info.files_count

    def test_all_change_types(self):
        for ct in ChangeType:
            assert ct.value in ("security", "logic", "config", "ui", "test", "docs", "refactor", "dependency")
