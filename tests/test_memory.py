import pytest
from unittest.mock import patch, MagicMock, AsyncMock

class TestMongoStore:
    """Tests for MongoDB CRUD operations."""

    @patch("memory.mongo_store.MongoClient")
    def test_save_review_sync_returns_id(self, mock_mongo_class, sample_pr_state_full):
        """Should insert a document and return the inserted_id as string."""
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = "abc123"
        mock_collection.insert_one.return_value = mock_result

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_class.return_value = mock_client

        from memory.mongo_store import save_review_sync
        result = save_review_sync(sample_pr_state_full)

        assert result == "abc123"
        mock_collection.insert_one.assert_called_once()

    @patch("memory.mongo_store.MongoClient")
    def test_save_review_sync_document_fields(self, mock_mongo_class, sample_pr_state_full):
        """Should include all required fields in the saved document."""
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = "id"
        mock_collection.insert_one.return_value = mock_result

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_class.return_value = mock_client

        from memory.mongo_store import save_review_sync
        save_review_sync(sample_pr_state_full)

        saved_doc = mock_collection.insert_one.call_args[0][0]
        assert saved_doc["pr_url"] == sample_pr_state_full.pr_url
        assert saved_doc["pr_number"] == sample_pr_state_full.pr_number
        assert saved_doc["repo_name"] == sample_pr_state_full.repo_name
        assert saved_doc["diff_analysis"] == sample_pr_state_full.diff_analysis
        assert "created_at" in saved_doc

    @patch("memory.mongo_store.MongoClient")
    def test_save_review_sync_closes_connection(self, mock_mongo_class, sample_pr_state_full):
        """Should close the MongoDB connection after saving."""
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = "id"
        mock_collection.insert_one.return_value = mock_result

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_mongo_class.return_value = mock_client

        from memory.mongo_store import save_review_sync
        save_review_sync(sample_pr_state_full)

        mock_client.close.assert_called_once()

class TestQdrantStore:
    """Tests for Qdrant vector store operations."""

    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_init_qdrant_creates_collection_if_not_exists(self, mock_embed, mock_qdrant):
        """Should create collection when it doesn't exist."""
        mock_qdrant.collection_exists.return_value = False

        from memory.qdrant_store import init_qdrant
        init_qdrant()

        mock_qdrant.create_collection.assert_called_once()

    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_init_qdrant_skips_if_exists(self, mock_embed, mock_qdrant):
        """Should not create collection when it already exists."""
        mock_qdrant.collection_exists.return_value = True

        from memory.qdrant_store import init_qdrant
        init_qdrant()

        mock_qdrant.create_collection.assert_not_called()

    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_store_review_returns_point_id(self, mock_embed, mock_qdrant, sample_pr_state_full):
        """Should embed the review and store in Qdrant, returning a UUID point_id."""
        mock_qdrant.collection_exists.return_value = True
        mock_embed.embed_query.return_value = [0.1] * 3072

        from memory.qdrant_store import store_review
        point_id = store_review(sample_pr_state_full)

        assert isinstance(point_id, str)
        assert len(point_id) > 0
        mock_qdrant.upsert.assert_called_once()

    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_store_review_includes_payload(self, mock_embed, mock_qdrant, sample_pr_state_full):
        """Should include correct payload fields in the stored point."""
        mock_qdrant.collection_exists.return_value = True
        mock_embed.embed_query.return_value = [0.1] * 3072

        from memory.qdrant_store import store_review
        store_review(sample_pr_state_full)

        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        payload = points[0].payload
        assert payload["pr_url"] == sample_pr_state_full.pr_url
        assert payload["pr_number"] == sample_pr_state_full.pr_number
        assert payload["repo_name"] == sample_pr_state_full.repo_name

    @patch("memory.qdrant_store.co")
    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_search_similar_reviews_with_results(self, mock_embed, mock_qdrant, mock_cohere):
        """Should return reranked results from Qdrant search."""
        mock_qdrant.collection_exists.return_value = True
        mock_embed.embed_query.return_value = [0.1] * 3072

        # Mock Qdrant search results
        mock_point_1 = MagicMock()
        mock_point_1.payload = {
            "review_summary": "Found command injection",
            "pr_url": "https://github.com/test/repo/pull/1",
        }
        mock_point_2 = MagicMock()
        mock_point_2.payload = {
            "review_summary": "Missing error handling",
            "pr_url": "https://github.com/test/repo/pull/2",
        }

        mock_query_result = MagicMock()
        mock_query_result.points = [mock_point_1, mock_point_2]
        mock_qdrant.query_points.return_value = mock_query_result

        # Mock Cohere reranking
        mock_rerank_result_1 = MagicMock()
        mock_rerank_result_1.index = 0
        mock_rerank_result_2 = MagicMock()
        mock_rerank_result_2.index = 1
        mock_cohere.rerank.return_value = MagicMock(
            results=[mock_rerank_result_1, mock_rerank_result_2]
        )

        from memory.qdrant_store import search_similar_reviews
        results = search_similar_reviews("shell command injection bug")

        assert len(results) == 2
        assert results[0]["review_summary"] == "Found command injection"

    @patch("memory.qdrant_store.qdrant")
    @patch("memory.qdrant_store.embedding_model")
    def test_search_similar_reviews_empty(self, mock_embed, mock_qdrant):
        """Should return empty list when no results found."""
        mock_qdrant.collection_exists.return_value = True
        mock_embed.embed_query.return_value = [0.1] * 3072

        mock_query_result = MagicMock()
        mock_query_result.points = []
        mock_qdrant.query_points.return_value = mock_query_result

        from memory.qdrant_store import search_similar_reviews
        results = search_similar_reviews("some query")

        assert results == []
