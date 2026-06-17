import pytest
import json
from unittest.mock import patch, MagicMock

class TestVerdictCorrectness:
    """Tests for the verdict_correctness evaluator."""

    def test_correct_request_changes_verdict(self):
        """Should detect REQUEST_CHANGES correctly."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": "Verdict: REQUEST_CHANGES"},
            reference_outputs={"expected_verdict": "REQUEST_CHANGES"},
        )
        assert result["key"] == "verdict_correctness"
        assert result["score"] is True

    def test_correct_approve_verdict(self):
        """Should detect APPROVE correctly."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": "Overall verdict: APPROVE. Great work!"},
            reference_outputs={"expected_verdict": "APPROVE"},
        )
        assert result["score"] is True

    def test_correct_needs_discussion_verdict(self):
        """Should detect NEEDS_DISCUSSION correctly."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": "Verdict: NEEDS_DISCUSSION"},
            reference_outputs={"expected_verdict": "NEEDS_DISCUSSION"},
        )
        assert result["score"] is True

    def test_incorrect_verdict(self):
        """Should return False when verdict doesn't match."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": "APPROVE"},
            reference_outputs={"expected_verdict": "REQUEST_CHANGES"},
        )
        assert result["score"] is False

    def test_no_verdict_in_review(self):
        """Should return False when no verdict is found in review."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": "This code looks fine overall."},
            reference_outputs={"expected_verdict": "APPROVE"},
        )
        assert result["score"] is False

    def test_empty_review(self):
        """Should handle empty review gracefully."""
        from evaluation.evaluators import verdict_correctness
        result = verdict_correctness(
            inputs={},
            outputs={"final_review": ""},
            reference_outputs={"expected_verdict": "APPROVE"},
        )
        assert result["score"] is False

class TestBugDetectionRecall:
    """Tests for the bug_detection_recall evaluator."""

    def test_full_recall(self):
        """Should return 1.0 when all bugs are detected."""
        from evaluation.evaluators import bug_detection_recall
        result = bug_detection_recall(
            inputs={},
            outputs={"bugs_found": "Found command injection and security vulnerability in the code"},
            reference_outputs={"must_detect_bugs": ["command injection", "security vulnerability"]},
        )
        assert result["key"] == "bug_detection_recall"
        assert result["score"] == 1.0

    def test_partial_recall(self):
        """Should return partial score when only some bugs detected."""
        from evaluation.evaluators import bug_detection_recall
        result = bug_detection_recall(
            inputs={},
            outputs={"bugs_found": "Found command injection vulnerability"},
            reference_outputs={"must_detect_bugs": ["command injection", "security vulnerability", "race condition"]},
        )
        # Only "command injection" found, "security vulnerability" is in the text too
        assert 0 < result["score"] < 1.0

    def test_zero_recall(self):
        """Should return 0.0 when no expected bugs are found."""
        from evaluation.evaluators import bug_detection_recall
        result = bug_detection_recall(
            inputs={},
            outputs={"bugs_found": "No issues found"},
            reference_outputs={"must_detect_bugs": ["command injection", "buffer overflow"]},
        )
        assert result["score"] == 0.0

    def test_no_bugs_expected(self):
        """Should return 1.0 when no bugs are expected."""
        from evaluation.evaluators import bug_detection_recall
        result = bug_detection_recall(
            inputs={},
            outputs={"bugs_found": ""},
            reference_outputs={"must_detect_bugs": []},
        )
        assert result["score"] == 1.0
        assert "correctly skipped" in result["comment"]

    def test_empty_bugs_report(self):
        """Should handle empty bugs_found output."""
        from evaluation.evaluators import bug_detection_recall
        result = bug_detection_recall(
            inputs={},
            outputs={"bugs_found": ""},
            reference_outputs={"must_detect_bugs": ["command injection"]},
        )
        assert result["score"] == 0.0

class TestStyleDetectionRecall:
    """Tests for the style_detection_recall evaluator."""

    def test_full_style_recall(self):
        """Should return 1.0 when all style issues detected."""
        from evaluation.evaluators import style_detection_recall
        result = style_detection_recall(
            inputs={},
            outputs={"style_issues": "Missing type hint and docstring throughout the code"},
            reference_outputs={"must_detect_style": ["type hint", "docstring"]},
        )
        assert result["score"] == 1.0

    def test_no_style_issues_expected(self):
        """Should return 1.0 when no style issues expected."""
        from evaluation.evaluators import style_detection_recall
        result = style_detection_recall(
            inputs={},
            outputs={"style_issues": ""},
            reference_outputs={"must_detect_style": []},
        )
        assert result["score"] == 1.0

    def test_partial_style_recall(self):
        """Should return partial score for partial detection."""
        from evaluation.evaluators import style_detection_recall
        result = style_detection_recall(
            inputs={},
            outputs={"style_issues": "Missing type hint in functions"},
            reference_outputs={"must_detect_style": ["type hint", "docstring", "naming convention"]},
        )
        assert 0 < result["score"] < 1.0

class TestFalsePositiveCheck:
    """Tests for the false_positive_check evaluator."""

    def test_no_false_positives_on_clean_code(self):
        """Clean code with APPROVE expected should score 1.0 if no flags."""
        from evaluation.evaluators import false_positive_check
        result = false_positive_check(
            inputs={},
            outputs={"final_review": "Great code! All looks good. APPROVE"},
            reference_outputs={"expected_verdict": "APPROVE", "severity": "none"},
        )
        assert result["score"] == 1.0

    def test_false_positive_detected(self):
        """Should score 0.0 when agent flags critical issues on clean code."""
        from evaluation.evaluators import false_positive_check
        result = false_positive_check(
            inputs={},
            outputs={"final_review": "Found critical security vulnerability. REQUEST_CHANGES"},
            reference_outputs={"expected_verdict": "APPROVE", "severity": "none"},
        )
        assert result["score"] == 0.0

    def test_skips_for_non_approve_expected(self):
        """Should return 1.0 (N/A) when the PR is expected to have real issues."""
        from evaluation.evaluators import false_positive_check
        result = false_positive_check(
            inputs={},
            outputs={"final_review": "Critical bug found. REQUEST_CHANGES"},
            reference_outputs={"expected_verdict": "REQUEST_CHANGES", "severity": "critical"},
        )
        assert result["score"] == 1.0
        assert "N/A" in result["comment"]

class TestReviewHasStructure:
    """Tests for the review_has_structure evaluator."""

    def test_well_structured_review(self):
        """Should score 1.0 for a review with all structural elements."""
        from evaluation.evaluators import review_has_structure
        review = (
            "# PR Review\n\n"
            "## Critical Issues\n"
            "- Command injection found\n"
            "- Missing error handling\n\n"
            "## Verdict: REQUEST_CHANGES\n"
            "This PR has critical issues that need to be resolved.\n"
            "The code quality is below standards."
        )
        result = review_has_structure(
            inputs={},
            outputs={"final_review": review},
            reference_outputs={},
        )
        assert result["score"] == 1.0

    def test_unstructured_review(self):
        """Should score low for a review without structure."""
        from evaluation.evaluators import review_has_structure
        result = review_has_structure(
            inputs={},
            outputs={"final_review": "ok"},
            reference_outputs={},
        )
        assert result["score"] < 0.5

    def test_empty_review(self):
        """Should handle empty review."""
        from evaluation.evaluators import review_has_structure
        result = review_has_structure(
            inputs={},
            outputs={"final_review": ""},
            reference_outputs={},
        )
        assert result["score"] == 0.0

    def test_partial_structure(self):
        """Should give partial score for partially structured review."""
        from evaluation.evaluators import review_has_structure
        # Has bullet points and length but no sections or verdict
        review = (
            "This code has some issues:\n"
            "- Missing error handling in the payment function\n"
            "- No input validation for card numbers\n"
            "- The refund function doesn't check status codes\n"
            "Overall the code needs improvement."
        )
        result = review_has_structure(
            inputs={},
            outputs={"final_review": review},
            reference_outputs={},
        )
        assert 0.25 <= result["score"] <= 0.75

class TestReviewQualityLLMJudge:
    """Tests for the LLM-as-judge review quality evaluator."""

    @patch("evaluation.evaluators.judge_llm")
    def test_high_quality_review(self, mock_llm, mock_openai_response):
        """Should return high score for quality review."""
        mock_llm.chat.completions.create.return_value = mock_openai_response(
            json.dumps({
                "relevance": 0.9,
                "accuracy": 0.85,
                "actionability": 0.9,
                "completeness": 0.8,
                "professionalism": 0.95,
                "overall": 0.88,
                "reasoning": "Comprehensive and actionable review"
            })
        )

        from evaluation.evaluators import review_quality_llm_judge
        result = review_quality_llm_judge(
            inputs={"pr_diff": "some diff"},
            outputs={"final_review": "Detailed review content"},
            reference_outputs={"expected_verdict": "REQUEST_CHANGES", "must_detect_bugs": ["command injection"]},
        )

        assert result["key"] == "review_quality"
        assert result["score"] == 0.88

    @patch("evaluation.evaluators.judge_llm")
    def test_llm_failure_returns_zero(self, mock_llm):
        """Should return 0.0 when LLM call fails."""
        mock_llm.chat.completions.create.side_effect = Exception("API timeout")

        from evaluation.evaluators import review_quality_llm_judge
        result = review_quality_llm_judge(
            inputs={"pr_diff": "diff"},
            outputs={"final_review": "review"},
            reference_outputs={"expected_verdict": "APPROVE", "must_detect_bugs": []},
        )

        assert result["score"] == 0.0
        assert "failed" in result["comment"]

class TestHallucinationCheck:
    """Tests for the LLM-based hallucination detector."""

    @patch("evaluation.evaluators.judge_llm")
    def test_no_hallucination(self, mock_llm, mock_openai_response):
        """Should return 1.0 when all reported bugs are grounded."""
        mock_llm.chat.completions.create.return_value = mock_openai_response(
            json.dumps({
                "total_bugs_mentioned": 2,
                "grounded_bugs": 2,
                "hallucinated_bugs": 0,
                "hallucination_rate": 0.0,
                "details": "All bugs are in the diff"
            })
        )

        from evaluation.evaluators import hallucination_check
        result = hallucination_check(
            inputs={"pr_diff": "diff"},
            outputs={"bugs_found": "Bug 1, Bug 2"},
            reference_outputs={},
        )

        assert result["score"] == 1.0

    @patch("evaluation.evaluators.judge_llm")
    def test_hallucination_detected(self, mock_llm, mock_openai_response):
        """Should return low score when hallucinations detected."""
        mock_llm.chat.completions.create.return_value = mock_openai_response(
            json.dumps({
                "total_bugs_mentioned": 3,
                "grounded_bugs": 1,
                "hallucinated_bugs": 2,
                "hallucination_rate": 0.67,
                "details": "2 bugs were not in the diff"
            })
        )

        from evaluation.evaluators import hallucination_check
        result = hallucination_check(
            inputs={"pr_diff": "diff"},
            outputs={"bugs_found": "Bug 1, Bug 2, Fake Bug"},
            reference_outputs={},
        )

        assert result["score"] == pytest.approx(0.33, abs=0.01)

    def test_no_bugs_reported_skips_check(self):
        """Should return 1.0 when no bugs are reported."""
        from evaluation.evaluators import hallucination_check
        result = hallucination_check(
            inputs={"pr_diff": "diff"},
            outputs={"bugs_found": "No critical bugs found."},
            reference_outputs={},
        )

        assert result["score"] == 1.0
        assert "no hallucination possible" in result["comment"].lower()

    def test_empty_bugs_skips_check(self):
        """Should handle empty bugs_found output."""
        from evaluation.evaluators import hallucination_check
        result = hallucination_check(
            inputs={"pr_diff": "diff"},
            outputs={"bugs_found": ""},
            reference_outputs={},
        )

        assert result["score"] == 1.0

    @patch("evaluation.evaluators.judge_llm")
    def test_llm_failure_returns_zero(self, mock_llm):
        """Should return 0.0 when hallucination check LLM fails."""
        mock_llm.chat.completions.create.side_effect = Exception("API error")

        from evaluation.evaluators import hallucination_check
        result = hallucination_check(
            inputs={"pr_diff": "diff"},
            outputs={"bugs_found": "Some bugs found"},
            reference_outputs={},
        )

        assert result["score"] == 0.0

class TestAllEvaluators:
    """Tests for the evaluator registry."""

    def test_all_evaluators_count(self):
        """Should have exactly 7 evaluators."""
        from evaluation.evaluators import ALL_EVALUATORS
        assert len(ALL_EVALUATORS) == 7

    def test_all_evaluators_are_callable(self):
        """All evaluators should be callable functions."""
        from evaluation.evaluators import ALL_EVALUATORS
        for evaluator in ALL_EVALUATORS:
            assert callable(evaluator)

class TestGoldenDataset:
    """Tests for the evaluation dataset structure and integrity."""

    def test_dataset_not_empty(self):
        """Dataset should contain test cases."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        assert len(GOLDEN_EXAMPLES) > 0

    def test_dataset_has_8_examples(self):
        """Dataset should contain exactly 8 golden examples."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        assert len(GOLDEN_EXAMPLES) == 8

    def test_each_example_has_inputs_and_outputs(self):
        """Each example should have 'inputs' and 'outputs' keys."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        for i, example in enumerate(GOLDEN_EXAMPLES):
            assert "inputs" in example, f"Example {i} missing 'inputs'"
            assert "outputs" in example, f"Example {i} missing 'outputs'"

    def test_inputs_have_pr_diff(self):
        """Each input should have a pr_diff field."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        for i, example in enumerate(GOLDEN_EXAMPLES):
            assert "pr_diff" in example["inputs"], f"Example {i} missing 'pr_diff'"
            assert len(example["inputs"]["pr_diff"]) > 0, f"Example {i} has empty pr_diff"

    def test_outputs_have_expected_verdict(self):
        """Each output should have an expected_verdict."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        valid_verdicts = {"APPROVE", "REQUEST_CHANGES", "NEEDS_DISCUSSION"}
        for i, example in enumerate(GOLDEN_EXAMPLES):
            verdict = example["outputs"].get("expected_verdict", "")
            assert verdict in valid_verdicts, f"Example {i} has invalid verdict: {verdict}"

    def test_outputs_have_must_detect_bugs(self):
        """Each output should have must_detect_bugs list."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        for i, example in enumerate(GOLDEN_EXAMPLES):
            assert "must_detect_bugs" in example["outputs"], f"Example {i} missing 'must_detect_bugs'"
            assert isinstance(example["outputs"]["must_detect_bugs"], list)

    def test_dataset_name_constant(self):
        """Dataset name constant should be defined."""
        from evaluation.dataset import EVAL_DATASET_NAME
        assert EVAL_DATASET_NAME == "pr-review-agent-eval"

    def test_dataset_has_severity_field(self):
        """Each output should have a severity field."""
        from evaluation.dataset import GOLDEN_EXAMPLES
        valid_severities = {"critical", "major", "minor", "none"}
        for i, example in enumerate(GOLDEN_EXAMPLES):
            severity = example["outputs"].get("severity", "")
            assert severity in valid_severities, f"Example {i} has invalid severity: {severity}"
