import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

class TestPRReviewState:
    """Tests for the LangGraph state schema."""

    def test_minimal_state_creation(self):
        """State should be creatable with only required fields."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        assert state.pr_url == "https://github.com/owner/repo/pull/1"
        assert state.pr_number == 1
        assert state.repo_name == "owner/repo"

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/5",
            pr_number=5,
            repo_name="test/repo",
        )
        assert state.pr_diff is None
        assert state.diff_analysis is None
        assert state.bugs_found is None
        assert state.style_issues is None
        assert state.final_review is None
        assert state.review_summary is None
        assert state.review_id is None

    def test_comments_posted_defaults_false(self):
        """comments_posted should default to False."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
        )
        assert state.comments_posted is False

    def test_messages_defaults_empty(self):
        """messages field should default to empty list."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
        )
        assert state.messages == []

    def test_full_state_creation(self, sample_pr_state_full):
        """State should accept all fields populated."""
        state = sample_pr_state_full
        assert state.pr_diff is not None
        assert state.diff_analysis is not None
        assert state.bugs_found is not None
        assert len(state.bugs_found) == 1
        assert state.style_issues is not None
        assert len(state.style_issues) == 1
        assert state.final_review is not None
        assert state.review_summary is not None
        assert state.comments_posted is True
        assert state.review_id == "mongo-id-123"

    def test_model_copy_update(self, sample_pr_state):
        """model_copy should create a new state with updated fields."""
        updated = sample_pr_state.model_copy(
            update={"pr_diff": "new diff content", "diff_analysis": "analysis result"}
        )
        assert updated.pr_diff == "new diff content"
        assert updated.diff_analysis == "analysis result"
        # Original should be unchanged
        assert sample_pr_state.pr_diff is None

    def test_missing_required_fields_raises_error(self):
        """Missing required fields should raise ValidationError."""
        from schema.state import PRReviewState
        with pytest.raises(ValidationError):
            PRReviewState(pr_url="https://github.com/test/repo/pull/1")

    def test_pr_number_must_be_int(self):
        """pr_number should reject non-integer values."""
        from schema.state import PRReviewState
        with pytest.raises(ValidationError):
            PRReviewState(
                pr_url="https://github.com/test/repo/pull/1",
                pr_number="not-a-number",
                repo_name="test/repo",
            )

    def test_bugs_found_accepts_list(self):
        """bugs_found should accept a list of strings."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            bugs_found=["Bug 1", "Bug 2"],
        )
        assert len(state.bugs_found) == 2
        assert "Bug 1" in state.bugs_found

    def test_state_serialization(self, sample_pr_state_full):
        """State should be serializable to dict via model_dump."""
        data = sample_pr_state_full.model_dump()
        assert isinstance(data, dict)
        assert data["pr_number"] == 1
        assert data["repo_name"] == "test/repo"
        assert data["comments_posted"] is True

    def test_empty_lists_for_optional_lists(self):
        """Empty lists should be valid for optional list fields."""
        from schema.state import PRReviewState
        state = PRReviewState(
            pr_url="https://github.com/test/repo/pull/1",
            pr_number=1,
            repo_name="test/repo",
            bugs_found=[],
            style_issues=[],
        )
        assert state.bugs_found == []
        assert state.style_issues == []

class TestPRReview:
    """Tests for the Beanie document model used for MongoDB storage."""

    @patch("schema.review.PRReview.get_settings")
    def test_review_creation_with_required_fields(self, mock_settings):
        """PRReview should be creatable with required fields."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        assert review.pr_url == "https://github.com/owner/repo/pull/1"
        assert review.pr_number == 1
        assert review.repo_name == "owner/repo"

    @patch("schema.review.PRReview.get_settings")
    def test_review_optional_fields_default_none(self, mock_settings):
        """Optional fields should default to None."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        assert review.diff_analysis is None
        assert review.bugs_found is None
        assert review.style_issues is None
        assert review.final_review is None
        assert review.review_summary is None

    @patch("schema.review.PRReview.get_settings")
    def test_review_comments_posted_default_false(self, mock_settings):
        """comments_posted should default to False."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        assert review.comments_posted is False

    @patch("schema.review.PRReview.get_settings")
    def test_review_created_at_is_datetime(self, mock_settings):
        """created_at should default to a datetime instance."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        assert isinstance(review.created_at, datetime)

    def test_review_settings_collection_name(self):
        """The MongoDB collection should be named 'reviews'."""
        from schema.review import PRReview
        assert PRReview.Settings.name == "reviews"

    @patch("schema.review.PRReview.get_settings")
    def test_review_full_creation(self, mock_settings):
        """PRReview should accept all fields."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
            diff_analysis="Analysis text",
            bugs_found=["Bug 1"],
            style_issues=["Style issue 1"],
            final_review="Final review text",
            review_summary="Summary text",
            comments_posted=True,
        )
        assert review.diff_analysis == "Analysis text"
        assert review.bugs_found == ["Bug 1"]
        assert review.comments_posted is True

    @patch("schema.review.PRReview.get_settings")
    def test_review_serialization(self, mock_settings):
        """PRReview should be serializable to dict."""
        mock_settings.return_value = MagicMock()
        from schema.review import PRReview
        review = PRReview(
            pr_url="https://github.com/owner/repo/pull/1",
            pr_number=1,
            repo_name="owner/repo",
        )
        data = review.model_dump()
        assert isinstance(data, dict)
        assert data["pr_number"] == 1
