import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a FastAPI test client with mocked graph imports."""
    with patch("graph.workflow.build_graph") as mock_build, \
         patch("graph.workflow.conn"), \
         patch("main.graph") as mock_graph, \
         patch("main.run_review", new_callable=AsyncMock) as mock_run:
        # Prevent real graph compilation and SQLite connection
        mock_build.return_value = MagicMock()
        from main import app
        yield TestClient(app)

class TestRootEndpoint:
    """Tests for the GET / health check endpoint."""

    def test_root_returns_status(self, client):
        """Should return a JSON status message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "running" in data["status"].lower()

class TestWebhookEndpoint:
    """Tests for the POST /webhook/github endpoint."""

    def test_opened_pr_queues_review(self, client, webhook_payload_opened):
        """Opened PR should be accepted and review queued."""
        response = client.post("/webhook/github", json=webhook_payload_opened)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "review_queued"
        assert data["pr_number"] == 42

    def test_synchronize_pr_queues_review(self, client, webhook_payload_synchronize):
        """Synchronize event should also queue a review."""
        response = client.post("/webhook/github", json=webhook_payload_synchronize)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "review_queued"

    def test_closed_pr_is_ignored(self, client, webhook_payload_closed):
        """Closed PR events should be ignored."""
        response = client.post("/webhook/github", json=webhook_payload_closed)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_labeled_action_is_ignored(self, client):
        """Non-relevant actions like 'labeled' should be ignored."""
        payload = {
            "action": "labeled",
            "pull_request": {"number": 1, "html_url": "https://github.com/o/r/pull/1"},
            "repository": {"full_name": "o/r"},
        }
        response = client.post("/webhook/github", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_missing_pull_request_field(self, client):
        """Should return 400 when pull_request is missing."""
        payload = {
            "action": "opened",
            "repository": {"full_name": "o/r"},
        }
        response = client.post("/webhook/github", json=payload)
        assert response.status_code == 400

    def test_missing_repository_field(self, client):
        """Should return 400 when repository is missing."""
        payload = {
            "action": "opened",
            "pull_request": {"number": 1, "html_url": "https://github.com/o/r/pull/1"},
        }
        response = client.post("/webhook/github", json=payload)
        assert response.status_code == 400

    def test_missing_pr_number(self, client):
        """Should return 400 when pr number is missing."""
        payload = {
            "action": "opened",
            "pull_request": {"html_url": "https://github.com/o/r/pull/1"},
            "repository": {"full_name": "o/r"},
        }
        response = client.post("/webhook/github", json=payload)
        assert response.status_code == 400

    def test_invalid_json_body(self, client):
        """Should return 400 for non-JSON body."""
        response = client.post(
            "/webhook/github",
            content="not-json",
            headers={"Content-Type": "application/json"},
        )
        # FastAPI returns 422 for body parse errors
        assert response.status_code in [400, 422]

    def test_response_includes_message(self, client, webhook_payload_opened):
        """Response should include a human-readable message."""
        response = client.post("/webhook/github", json=webhook_payload_opened)
        data = response.json()
        assert "message" in data
        assert "Background" in data["message"] or "background" in data["message"].lower()

class TestManualReviewEndpoint:
    """Tests for the GET /review/{owner}/{repo}/{pr} endpoint."""

    @patch("main.graph")
    def test_successful_manual_review(self, mock_graph, client):
        """Should return completed status with review data."""
        mock_graph.invoke.return_value = {
            "review_summary": "All good!",
            "comments_posted": True,
        }

        response = client.get("/review/owner/repo/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "summary" in data

    @patch("main.graph")
    def test_manual_review_graph_failure(self, mock_graph, client):
        """Should return 500 when graph invocation fails."""
        mock_graph.invoke.side_effect = Exception("LLM timeout")

        response = client.get("/review/owner/repo/1")
        assert response.status_code == 500

    @patch("main.graph")
    def test_manual_review_constructs_correct_repo_name(self, mock_graph, client):
        """Should join owner/repo into full_repo correctly."""
        mock_graph.invoke.return_value = {
            "review_summary": "Summary",
            "comments_posted": True,
        }

        client.get("/review/myorg/myproject/42")

        call_args = mock_graph.invoke.call_args
        state_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("state")
        # The state should have the full repo name
        assert state_arg.repo_name == "myorg/myproject"
        assert state_arg.pr_number == 42


class TestStatsEndpoint:
    """Tests for the GET /stats endpoint."""

    @patch("main.MongoClient")
    def test_stats_returns_data(self, mock_mongo_cls, client):
        """Should return total_reviews, comments_posted, and success_rate."""
        mock_collection = MagicMock()
        mock_collection.count_documents.side_effect = lambda q: 10 if q == {} else 8
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client_inst = MagicMock()
        mock_client_inst.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_cls.return_value = mock_client_inst

        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_reviews"] == 10
        assert data["comments_posted"] == 8
        assert data["success_rate"] == "80.0%"

    @patch("main.MongoClient")
    def test_stats_empty_database(self, mock_mongo_cls, client):
        """Should return 0% success_rate when no reviews exist."""
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = 0
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        mock_client_inst = MagicMock()
        mock_client_inst.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_cls.return_value = mock_client_inst

        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_reviews"] == 0
        assert data["success_rate"] == "0%"

    @patch("main.MongoClient")
    def test_stats_database_failure(self, mock_mongo_cls, client):
        """Should return 500 when MongoDB is unreachable."""
        mock_mongo_cls.side_effect = Exception("Connection refused")

        response = client.get("/stats")
        assert response.status_code == 500


class TestWebhookSignatureVerification:
    """Tests for HMAC-SHA256 webhook signature verification."""

    def _sign_payload(self, payload: dict, secret: str) -> str:
        """Helper to compute GitHub-style HMAC signature."""
        body = json.dumps(payload).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_accepted(self, webhook_payload_opened):
        """Webhook with valid HMAC signature should be accepted."""
        secret = "test-webhook-secret"
        # Compute signature over the exact bytes that will be sent
        body = json.dumps(webhook_payload_opened).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        sig = f"sha256={digest}"

        with patch("graph.workflow.build_graph") as mock_build, \
             patch("graph.workflow.conn"), \
             patch("main.graph"), \
             patch("main.run_review", new_callable=AsyncMock), \
             patch("main.WEBHOOK_SECRET", secret):
            mock_build.return_value = MagicMock()
            from main import app
            test_client = TestClient(app)
            response = test_client.post(
                "/webhook/github",
                content=body,
                headers={
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
            assert response.status_code == 200
            assert response.json()["status"] == "review_queued"

    def test_invalid_signature_rejected(self, webhook_payload_opened):
        """Webhook with wrong signature should return 401."""
        with patch("graph.workflow.build_graph") as mock_build, \
             patch("graph.workflow.conn"), \
             patch("main.graph"), \
             patch("main.run_review", new_callable=AsyncMock), \
             patch("main.WEBHOOK_SECRET", "real-secret"):
            mock_build.return_value = MagicMock()
            from main import app
            test_client = TestClient(app)
            response = test_client.post(
                "/webhook/github",
                json=webhook_payload_opened,
                headers={"X-Hub-Signature-256": "sha256=badsignature"},
            )
            assert response.status_code == 401

    def test_no_secret_skips_verification(self, client, webhook_payload_opened):
        """When GITHUB_WEBHOOK_SECRET is not set, signature check is skipped."""
        with patch("main.WEBHOOK_SECRET", None):
            response = client.post("/webhook/github", json=webhook_payload_opened)
            assert response.status_code == 200
            assert response.json()["status"] == "review_queued"
