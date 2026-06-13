import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set dummy environment variables for all tests to avoid hitting real APIs."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key")
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-langchain-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")


@pytest.fixture
def sample_pr_diff():
    """A realistic PR diff for testing agents."""
    return """
    File: services/deploy.py
    Status: modified
    Additions: 5
    Deletions: 1
    Diff:
    - subprocess.run(["git", "clone", repo_url], check=True)
    + os.system(f"git clone {repo_url} && cd {repo_name} && pip install -r requirements.txt")
    + subprocess.run(f"curl {user_provided_url} | bash", shell=True)
    """


@pytest.fixture
def sample_diff_analysis():
    """Sample output from Agent 1 (diff analyzer)."""
    return (
        "## Changes Summary\n"
        "- Modified `services/deploy.py`\n"
        "- Replaced safe subprocess list-args with shell=True and os.system\n"
        "- Added piping of untrusted URL content directly to bash\n"
        "- **Purpose**: Simplifying deployment commands (introduces command injection risk)"
    )


@pytest.fixture
def sample_bugs_report():
    """Sample output from Agent 2 (bug detector)."""
    return (
        "### Bug 1: Command Injection Vulnerability\n"
        "The code uses os.system() and shell=True with unsanitized user input "
        "which is a critical security vulnerability. Attacker-controlled input is directly interpolated into shell commands.\n"
        "**Fix**: Use subprocess.run() with list arguments and avoid shell=True."
    )


@pytest.fixture
def sample_style_report():
    """Sample output from Agent 3 (style reviewer)."""
    return (
        "### Style Issue 1: Missing Type Hints\n"
        "Functions lack type annotations.\n"
        "### Style Issue 2: Missing Docstrings\n"
        "No docstrings on public functions."
    )


@pytest.fixture
def sample_final_review():
    """Sample output from Agent 4 (judge)."""
    return (
        "## PR Review Summary\n\n"
        "### Critical Issues\n"
        "- Command injection vulnerability in deploy.py\n\n"
        "### Minor Issues\n"
        "- Missing type hints and docstrings\n\n"
        "### Verdict: REQUEST_CHANGES\n"
        "This PR introduces a critical security vulnerability that must be fixed."
    )


@pytest.fixture
def sample_review_summary():
    """Sample review summary for GitHub comment."""
    return (
        "- 🔴 Critical command injection vulnerability found\n"
        "- Missing type hints\n"
        "- Missing docstrings\n"
        "- Verdict: REQUEST_CHANGES"
    )

@pytest.fixture
def mock_openai_response():
    """Factory fixture to create mock OpenAI API responses."""
    def _create(content: str):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        return mock_response
    return _create


@pytest.fixture
def mock_openai_client(mock_openai_response):
    """Create a fully mocked OpenAI client."""
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client


@pytest.fixture
def mock_github_pr():
    """Create a mock GitHub PR object with realistic attributes."""
    mock_pr = MagicMock()
    mock_pr.title = "Simplify deployment script"
    mock_pr.body = "Consolidated deployment steps into single shell commands"
    mock_pr.user.login = "testuser"
    mock_pr.base.ref = "main"
    mock_pr.head.ref = "feature/deploy-simplify"
    mock_pr.changed_files = 1
    mock_pr.additions = 5
    mock_pr.deletions = 1

    # Mock file in the PR
    mock_file = MagicMock()
    mock_file.filename = "services/deploy.py"
    mock_file.status = "modified"
    mock_file.additions = 5
    mock_file.deletions = 1
    mock_file.patch = '- old line\n+ new line'
    mock_pr.get_files.return_value = [mock_file]

    mock_pr.create_issue_comment = MagicMock()
    return mock_pr


@pytest.fixture
def mock_github_repo(mock_github_pr):
    """Create a mock GitHub repo that returns our mock PR."""
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_github_pr
    return mock_repo


@pytest.fixture
def sample_pr_state():
    """Create a sample PRReviewState for testing."""
    from schema.state import PRReviewState
    return PRReviewState(
        pr_url="https://github.com/test/repo/pull/1",
        pr_number=1,
        repo_name="test/repo",
    )


@pytest.fixture
def sample_pr_state_full(
    sample_pr_diff,
    sample_diff_analysis,
    sample_bugs_report,
    sample_style_report,
    sample_final_review,
    sample_review_summary,
):
    """Create a fully populated PRReviewState."""
    from schema.state import PRReviewState
    return PRReviewState(
        pr_url="https://github.com/test/repo/pull/1",
        pr_number=1,
        repo_name="test/repo",
        pr_diff=sample_pr_diff,
        diff_analysis=sample_diff_analysis,
        bugs_found=[sample_bugs_report],
        style_issues=[sample_style_report],
        final_review=sample_final_review,
        review_summary=sample_review_summary,
        comments_posted=True,
        review_id="mongo-id-123",
    )

@pytest.fixture
def webhook_payload_opened():
    """Valid GitHub webhook payload for a newly opened PR."""
    return {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        },
        "repository": {
            "full_name": "owner/repo",
        },
    }


@pytest.fixture
def webhook_payload_synchronize():
    """Valid GitHub webhook payload for a PR synchronize event."""
    return {
        "action": "synchronize",
        "pull_request": {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        },
        "repository": {
            "full_name": "owner/repo",
        },
    }


@pytest.fixture
def webhook_payload_closed():
    """Webhook payload for a closed PR (should be ignored)."""
    return {
        "action": "closed",
        "pull_request": {
            "number": 42,
            "html_url": "https://github.com/owner/repo/pull/42",
        },
        "repository": {
            "full_name": "owner/repo",
        },
    }
