import pytest
from unittest.mock import patch, MagicMock, AsyncMock

class TestRunReview:
    """Tests for the async run_review function."""

    @pytest.mark.asyncio
    @patch("graph.background.post_pr_comment")
    @patch("graph.background.graph")
    async def test_successful_review(self, mock_graph, mock_post):
        """Should invoke the graph without errors on success."""
        mock_graph.invoke = MagicMock(return_value={"review_summary": "All good"})

        from schema.state import PRReviewState
        from graph.background import run_review

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
        )
        config = {"configurable": {"thread_id": "test/repo-pr-1"}}

        await run_review(state, config)

        # Comment should NOT be posted on success (success comment is handled by judge)
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    @patch("graph.background.post_pr_comment")
    @patch("graph.background.graph")
    async def test_failed_review_posts_error_comment(self, mock_graph, mock_post):
        """Should post an error comment to GitHub when review fails."""
        mock_graph.invoke = MagicMock(side_effect=Exception("LLM timeout"))

        from schema.state import PRReviewState
        from graph.background import run_review

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
        )
        config = {"configurable": {"thread_id": "test/repo-pr-1"}}

        await run_review(state, config)

        mock_post.assert_called_once()
        comment = mock_post.call_args.kwargs.get("comment", mock_post.call_args[1].get("comment", ""))
        assert "failed" in comment.lower() or "❌" in comment
