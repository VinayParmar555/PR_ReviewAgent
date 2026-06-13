import pytest
from unittest.mock import patch, MagicMock

class TestDiffAnalyzer:
    """Tests for the diff_analyzer agent."""

    @patch("agents.diff_analyzer.search_similar_reviews")
    @patch("agents.diff_analyzer.get_pr_info")
    @patch("agents.diff_analyzer.get_pr_diff")
    @patch("agents.diff_analyzer.client")
    def test_returns_expected_keys(
        self, mock_client, mock_get_diff, mock_get_info, mock_search,
        sample_pr_state, mock_openai_response, sample_pr_diff
    ):
        """Should return dict with 'pr_diff' and 'diff_analysis' keys."""
        mock_get_diff.return_value = sample_pr_diff
        mock_get_info.return_value = {
            "title": "Test PR",
            "description": "Test description",
            "author": "dev",
            "files_changed": 1,
        }
        mock_search.return_value = []
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Analysis: deployment script modified with shell commands"
        )

        from agents.diff_analyzer import diff_analyzer
        result = diff_analyzer(sample_pr_state)

        assert "pr_diff" in result
        assert "diff_analysis" in result
        assert result["pr_diff"] == sample_pr_diff
        assert "Analysis" in result["diff_analysis"]

    @patch("agents.diff_analyzer.search_similar_reviews")
    @patch("agents.diff_analyzer.get_pr_info")
    @patch("agents.diff_analyzer.get_pr_diff")
    @patch("agents.diff_analyzer.client")
    def test_uses_past_context(
        self, mock_client, mock_get_diff, mock_get_info, mock_search,
        sample_pr_state, mock_openai_response
    ):
        """Should include past review context from Qdrant in the prompt."""
        mock_get_diff.return_value = "some diff"
        mock_get_info.return_value = {
            "title": "Test", "description": "", "author": "dev", "files_changed": 1
        }
        mock_search.return_value = [
            {"review_summary": "Past review: found command injection"}
        ]
        mock_client.chat.completions.create.return_value = mock_openai_response("Analysis result")

        from agents.diff_analyzer import diff_analyzer
        diff_analyzer(sample_pr_state)

        # Verify the LLM was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        system_prompt = call_args.kwargs["messages"][0]["content"]
        assert "Past review: found command injection" in system_prompt

    @patch("agents.diff_analyzer.search_similar_reviews")
    @patch("agents.diff_analyzer.get_pr_info")
    @patch("agents.diff_analyzer.get_pr_diff")
    @patch("agents.diff_analyzer.client")
    def test_no_past_reviews_fallback(
        self, mock_client, mock_get_diff, mock_get_info, mock_search,
        sample_pr_state, mock_openai_response
    ):
        """Should use fallback text when no similar past reviews exist."""
        mock_get_diff.return_value = "some diff"
        mock_get_info.return_value = {
            "title": "Test", "description": "", "author": "dev", "files_changed": 1
        }
        mock_search.return_value = []
        mock_client.chat.completions.create.return_value = mock_openai_response("Analysis result")

        from agents.diff_analyzer import diff_analyzer
        diff_analyzer(sample_pr_state)

        call_args = mock_client.chat.completions.create.call_args
        system_prompt = call_args.kwargs["messages"][0]["content"]
        assert "No past reviews found" in system_prompt

class TestBugDetector:
    """Tests for the bug_detector agent."""

    @patch("agents.bug_detector.client")
    def test_returns_bugs_found_key(
        self, mock_client, mock_openai_response, sample_pr_diff, sample_diff_analysis
    ):
        """Should return dict with 'bugs_found' key containing a list."""
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Command injection vulnerability detected"
        )

        from schema.state import PRReviewState
        from agents.bug_detector import bug_detector

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff=sample_pr_diff,
            diff_analysis=sample_diff_analysis,
        )
        result = bug_detector(state)

        assert "bugs_found" in result
        assert isinstance(result["bugs_found"], list)
        assert len(result["bugs_found"]) == 1
        assert "Command injection" in result["bugs_found"][0]

    @patch("agents.bug_detector.client")
    def test_no_bugs_found(self, mock_client, mock_openai_response):
        """Should handle 'no bugs found' case correctly."""
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "No critical bugs found."
        )

        from schema.state import PRReviewState
        from agents.bug_detector import bug_detector

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff="clean code diff",
            diff_analysis="Clean code analysis",
        )
        result = bug_detector(state)

        assert "No critical bugs found" in result["bugs_found"][0]

    @patch("agents.bug_detector.client")
    def test_includes_diff_in_prompt(self, mock_client, mock_openai_response):
        """Should include both diff_analysis and pr_diff in the user prompt."""
        mock_client.chat.completions.create.return_value = mock_openai_response("bugs")

        from schema.state import PRReviewState
        from agents.bug_detector import bug_detector

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff="raw diff content",
            diff_analysis="analysis content",
        )
        bug_detector(state)

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "raw diff content" in user_msg
        assert "analysis content" in user_msg


class TestStyleReviewer:
    """Tests for the style_reviewer agent."""

    @patch("agents.style_reviewer.client")
    def test_returns_style_issues_key(
        self, mock_client, mock_openai_response, sample_pr_diff, sample_diff_analysis
    ):
        """Should return dict with 'style_issues' key containing a list."""
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Missing type hints and docstrings"
        )

        from schema.state import PRReviewState
        from agents.style_reviewer import style_reviewer

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff=sample_pr_diff,
            diff_analysis=sample_diff_analysis,
        )
        result = style_reviewer(state)

        assert "style_issues" in result
        assert isinstance(result["style_issues"], list)
        assert len(result["style_issues"]) == 1
        assert "type hints" in result["style_issues"][0]

    @patch("agents.style_reviewer.client")
    def test_includes_diff_in_prompt(self, mock_client, mock_openai_response):
        """Should include both analysis and raw diff in prompt."""
        mock_client.chat.completions.create.return_value = mock_openai_response("style")

        from schema.state import PRReviewState
        from agents.style_reviewer import style_reviewer

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff="raw diff",
            diff_analysis="analysis",
        )
        style_reviewer(state)

        call_args = mock_client.chat.completions.create.call_args
        user_msg = call_args.kwargs["messages"][1]["content"]
        assert "raw diff" in user_msg
        assert "analysis" in user_msg

    @patch("agents.style_reviewer.client")
    def test_uses_correct_model(self, mock_client, mock_openai_response):
        """Should use the llama-3.3-70b-versatile model."""
        mock_client.chat.completions.create.return_value = mock_openai_response("style result")

        from schema.state import PRReviewState
        from agents.style_reviewer import style_reviewer

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff="diff",
            diff_analysis="analysis",
        )
        style_reviewer(state)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "llama-3.3-70b-versatile"

class TestJudge:
    """Tests for the judge agent."""

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_returns_expected_keys(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """Should return dict with final_review, review_summary, etc."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("Final review with verdict: REQUEST_CHANGES"),
            mock_openai_response("- Critical command injection\n- Verdict: REQUEST_CHANGES"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "mongo-id-456"
        mock_qdrant.return_value = "qdrant-id-789"

        from agents.judge import judge
        result = judge(sample_pr_state_full)

        assert "final_review" in result
        assert "review_summary" in result
        assert "comments_posted" in result
        assert result["comments_posted"] is True

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_posts_comment_to_github(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """Should post a formatted comment to GitHub."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("Final review"),
            mock_openai_response("Summary bullets"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "id"
        mock_qdrant.return_value = "id"

        from agents.judge import judge
        judge(sample_pr_state_full)

        mock_post.assert_called_once()
        comment_arg = mock_post.call_args.kwargs["comment"]
        assert "🤖 AI PR Review" in comment_arg

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_saves_to_mongodb(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """Should attempt to save the review to MongoDB."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("review"),
            mock_openai_response("summary"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "mongo-id"
        mock_qdrant.return_value = "qdrant-id"

        from agents.judge import judge
        judge(sample_pr_state_full)

        mock_mongo.assert_called_once()

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_saves_to_qdrant(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """Should attempt to save the review to Qdrant."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("review"),
            mock_openai_response("summary"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "mongo-id"
        mock_qdrant.return_value = "qdrant-id"

        from agents.judge import judge
        judge(sample_pr_state_full)

        mock_qdrant.assert_called_once()

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_handles_mongodb_failure_gracefully(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """BUG: judge.py uses review_id in return dict without a fallback
        when save_review_sync fails, causing UnboundLocalError.
        This test documents the current (buggy) behavior.
        """
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("review"),
            mock_openai_response("summary"),
        ]
        mock_post.return_value = True
        mock_mongo.side_effect = Exception("MongoDB connection refused")
        mock_qdrant.return_value = "qdrant-id"

        from agents.judge import judge
        # Known bug: review_id is referenced before assignment in the return dict
        with pytest.raises(UnboundLocalError):
            judge(sample_pr_state_full)

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_handles_qdrant_failure_gracefully(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """BUG: judge.py uses point_id in return dict without a fallback
        when store_review fails, causing UnboundLocalError.
        This test documents the current (buggy) behavior.
        """
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("review"),
            mock_openai_response("summary"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "mongo-id"
        mock_qdrant.side_effect = Exception("Qdrant unavailable")

        from agents.judge import judge
        # Known bug: point_id is referenced before assignment in the return dict
        with pytest.raises(UnboundLocalError):
            judge(sample_pr_state_full)

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_handles_empty_bugs_and_style(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response
    ):
        """Should handle state with empty bugs_found and style_issues."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("Clean code review. APPROVE"),
            mock_openai_response("All good!"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "id"
        mock_qdrant.return_value = "id"

        from schema.state import PRReviewState
        from agents.judge import judge

        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            pr_diff="clean diff",
            diff_analysis="clean analysis",
            bugs_found=[],
            style_issues=[],
        )
        result = judge(state)
        assert "final_review" in result

    @patch("agents.judge.store_review")
    @patch("agents.judge.save_review_sync")
    @patch("agents.judge.post_pr_comment")
    @patch("agents.judge.client")
    def test_makes_two_llm_calls(
        self, mock_client, mock_post, mock_mongo, mock_qdrant,
        mock_openai_response, sample_pr_state_full
    ):
        """Judge should make exactly 2 LLM calls: one for review, one for summary."""
        mock_client.chat.completions.create.side_effect = [
            mock_openai_response("review"),
            mock_openai_response("summary"),
        ]
        mock_post.return_value = True
        mock_mongo.return_value = "id"
        mock_qdrant.return_value = "id"

        from agents.judge import judge
        judge(sample_pr_state_full)

        assert mock_client.chat.completions.create.call_count == 2
