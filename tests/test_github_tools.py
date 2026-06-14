import pytest
from unittest.mock import patch, MagicMock

class TestGetPrDiff:
    """Tests for the get_pr_diff function."""

    @patch("tools.github_tools.github_client")
    def test_returns_formatted_diff(self, mock_client, mock_github_repo):
        """Should return a formatted string with file diff details."""
        mock_client.get_repo.return_value = mock_github_repo

        from tools.github_tools import get_pr_diff
        result = get_pr_diff("owner/repo", 1)

        assert "services/deploy.py" in result
        assert "modified" in result
        mock_client.get_repo.assert_called_once_with("owner/repo")
        mock_github_repo.get_pull.assert_called_once_with(1)

    @patch("tools.github_tools.github_client")
    def test_multi_file_diff(self, mock_client):
        """Should handle PRs with multiple changed files."""
        mock_file_1 = MagicMock()
        mock_file_1.filename = "file1.py"
        mock_file_1.status = "modified"
        mock_file_1.additions = 3
        mock_file_1.deletions = 1
        mock_file_1.patch = "+ new line"

        mock_file_2 = MagicMock()
        mock_file_2.filename = "file2.py"
        mock_file_2.status = "added"
        mock_file_2.additions = 10
        mock_file_2.deletions = 0
        mock_file_2.patch = "+ another line"

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file_1, mock_file_2]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        from tools.github_tools import get_pr_diff
        result = get_pr_diff("owner/repo", 1)

        assert "file1.py" in result
        assert "file2.py" in result
        # Multiple files joined with separator
        assert "---" in result

    @patch("tools.github_tools.github_client")
    def test_empty_diff(self, mock_client):
        """Should handle PRs with no file changes."""
        mock_pr = MagicMock()
        mock_pr.get_files.return_value = []
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        from tools.github_tools import get_pr_diff
        result = get_pr_diff("owner/repo", 1)

        assert result == ""

class TestPostPrComment:
    """Tests for the post_pr_comment function."""

    @patch("tools.github_tools.github_client")
    def test_successful_comment(self, mock_client, mock_github_repo, mock_github_pr):
        """Should return True when comment is posted successfully."""
        mock_client.get_repo.return_value = mock_github_repo

        from tools.github_tools import post_pr_comment
        result = post_pr_comment("owner/repo", 1, "Test comment")

        assert result is True
        mock_github_pr.create_issue_comment.assert_called_once_with("Test comment")

    @patch("tools.github_tools.github_client")
    def test_failed_comment(self, mock_client):
        """Should return False when comment posting fails."""
        mock_pr = MagicMock()
        mock_pr.create_issue_comment.side_effect = Exception("API error")
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        from tools.github_tools import post_pr_comment
        result = post_pr_comment("owner/repo", 1, "Test comment")

        assert result is False

    @patch("tools.github_tools.github_client")
    def test_comment_with_markdown(self, mock_client, mock_github_repo, mock_github_pr):
        """Should handle markdown-formatted comments."""
        mock_client.get_repo.return_value = mock_github_repo

        from tools.github_tools import post_pr_comment
        markdown_comment = "## 🤖 AI PR Review\n\n- Critical issue found\n- Verdict: REQUEST_CHANGES"
        result = post_pr_comment("owner/repo", 1, markdown_comment)

        assert result is True
        mock_github_pr.create_issue_comment.assert_called_once_with(markdown_comment)

class TestGetPrInfo:
    """Tests for the get_pr_info function."""

    @patch("tools.github_tools.github_client")
    def test_returns_correct_info(self, mock_client, mock_github_repo, mock_github_pr):
        """Should return a dict with all expected PR metadata fields."""
        mock_client.get_repo.return_value = mock_github_repo

        from tools.github_tools import get_pr_info
        info = get_pr_info("owner/repo", 1)

        assert info["title"] == "Simplify deployment script"
        assert info["description"] == "Consolidated deployment steps into single shell commands"
        assert info["author"] == "testuser"
        assert info["base_branch"] == "main"
        assert info["head_branch"] == "feature/deploy-simplify"
        assert info["files_changed"] == 1
        assert info["additions"] == 5
        assert info["deletions"] == 1

    @patch("tools.github_tools.github_client")
    def test_returns_dict_type(self, mock_client, mock_github_repo):
        """Should return a dictionary."""
        mock_client.get_repo.return_value = mock_github_repo

        from tools.github_tools import get_pr_info
        info = get_pr_info("owner/repo", 1)

        assert isinstance(info, dict)
        assert "title" in info
        assert "author" in info

    @patch("tools.github_tools.github_client")
    def test_null_pr_body(self, mock_client):
        """Should handle PRs with no description (body=None)."""
        mock_pr = MagicMock()
        mock_pr.title = "Quick fix"
        mock_pr.body = None
        mock_pr.user.login = "dev"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "fix/bug"
        mock_pr.changed_files = 1
        mock_pr.additions = 1
        mock_pr.deletions = 0

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        from tools.github_tools import get_pr_info
        info = get_pr_info("owner/repo", 1)

        assert info["description"] is None
        assert info["title"] == "Quick fix"
