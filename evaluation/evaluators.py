import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

judge_llm = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# CODE-BASED EVALUATORS (deterministic, fast)

def verdict_correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Check if the agent's verdict matches the expected verdict.
    
    Returns:
        dict with 'score' (bool) and 'reason' (str)
    """
    expected = reference_outputs.get("expected_verdict", "").upper()
    review = outputs.get("final_review", "")

    # Extract verdict from the review text
    detected_verdict = None
    for verdict in ["REQUEST_CHANGES", "NEEDS_DISCUSSION", "APPROVE"]:
        if verdict in review.upper().replace(" ", "_"):
            detected_verdict = verdict
            break

    is_correct = detected_verdict == expected

    return {
        "key": "verdict_correctness",
        "score": is_correct,
        "comment": (
            f"Expected: {expected}, Detected: {detected_verdict or 'NONE'}. "
            f"{'✅ Correct' if is_correct else '❌ Incorrect verdict'}"
        ),
    }


def bug_detection_recall(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Measures what fraction of known bugs the agent actually detected.
    
    Checks if must-detect keywords appear in the bug report.
    Recall = (bugs found) / (bugs expected)
    """
    must_detect = reference_outputs.get("must_detect_bugs", [])

    if not must_detect:
        return {
            "key": "bug_detection_recall",
            "score": 1.0,
            "comment": "No bugs expected — correctly skipped.",
        }

    bugs_report = outputs.get("bugs_found", "").lower()

    found = []
    missed = []
    for bug_keyword in must_detect:
        if bug_keyword.lower() in bugs_report:
            found.append(bug_keyword)
        else:
            missed.append(bug_keyword)

    recall = len(found) / len(must_detect)

    return {
        "key": "bug_detection_recall",
        "score": recall,
        "comment": (
            f"Recall: {recall:.0%} — Found: {found or 'none'}, "
            f"Missed: {missed or 'none'}"
        ),
    }


def style_detection_recall(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Measures what fraction of known style issues the agent detected.
    
    Checks if must-detect style keywords appear in the style report.
    """
    must_detect = reference_outputs.get("must_detect_style", [])

    if not must_detect:
        return {
            "key": "style_detection_recall",
            "score": 1.0,
            "comment": "No style issues expected — correctly skipped.",
        }

    style_report = outputs.get("style_issues", "").lower()

    found = []
    missed = []
    for keyword in must_detect:
        if keyword.lower() in style_report:
            found.append(keyword)
        else:
            missed.append(keyword)

    recall = len(found) / len(must_detect)

    return {
        "key": "style_detection_recall",
        "score": recall,
        "comment": (
            f"Recall: {recall:.0%} — Found: {found or 'none'}, "
            f"Missed: {missed or 'none'}"
        ),
    }


def false_positive_check(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """For clean-code PRs (APPROVE expected), checks if the agent falsely flagged issues.
    
    A false positive = agent reports critical/major bugs on clean code.
    """
    expected_verdict = reference_outputs.get("expected_verdict", "")
    expected_severity = reference_outputs.get("severity", "")

    if expected_verdict != "APPROVE":
        return {
            "key": "false_positive_rate",
            "score": 1.0,
            "comment": "N/A — this PR has real issues, skipping false positive check.",
        }

    review = outputs.get("final_review", "").lower()

    # Check if the agent incorrectly flagged critical/major issues
    critical_flags = ["critical", "security vulnerability", "major bug", "request_changes"]
    false_flags = [flag for flag in critical_flags if flag in review]

    is_clean = len(false_flags) == 0

    return {
        "key": "false_positive_rate",
        "score": 1.0 if is_clean else 0.0,
        "comment": (
            f"{'✅ No false positives' if is_clean else '❌ False positives detected: ' + str(false_flags)}"
        ),
    }


def review_has_structure(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Checks if the final review has proper structure (sections, formatting).
    
    Looks for markdown headers, bullet points, and a verdict section.
    """
    review = outputs.get("final_review", "")

    checks = {
        "has_sections": bool(re.search(r'#{1,3}\s', review)),
        "has_bullet_points": bool(re.search(r'[-*]\s', review)),
        "has_verdict": any(
            v in review.upper() for v in ["APPROVE", "REQUEST_CHANGES", "NEEDS_DISCUSSION"]
        ),
        "min_length": len(review) > 100,
    }

    score = sum(checks.values()) / len(checks)

    return {
        "key": "review_structure",
        "score": score,
        "comment": (
            f"Structure score: {score:.0%} — "
            + ", ".join(f"{k}: {'✅' if v else '❌'}" for k, v in checks.items())
        ),
    }


#  LLM-AS-JUDGE EVALUATORS (semantic, using Groq)

def review_quality_llm_judge(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Uses an LLM to holistically score the review quality.
    
    Evaluates: relevance, actionability, accuracy, professionalism.
    Returns a score from 0.0 to 1.0.
    """
    pr_diff = inputs.get("pr_diff", "")
    final_review = outputs.get("final_review", "")
    expected_verdict = reference_outputs.get("expected_verdict", "")
    must_detect = reference_outputs.get("must_detect_bugs", [])

    judge_prompt = f"""You are an expert evaluator scoring the quality of an AI-generated PR code review.

    The PR diff being reviewed:
    {pr_diff[:2000]}

    The AI-generated review:
    {final_review[:3000]}

    Known ground truth:
    - Expected verdict: {expected_verdict}
    - Known issues that MUST be detected: {must_detect}

    Score this review on a scale of 0.0 to 1.0 across these criteria:
    1. **Relevance** (0.0-1.0): Does the review address the actual changes in the diff?
    2. **Accuracy** (0.0-1.0): Are the identified bugs/issues real (not hallucinated)?
    3. **Actionability** (0.0-1.0): Are suggestions specific and implementable?
    4. **Completeness** (0.0-1.0): Does it catch the known issues listed above?
    5. **Professionalism** (0.0-1.0): Is the tone constructive and clear?

    Respond ONLY with valid JSON in this exact format:
    {{
        "relevance": 0.0,
        "accuracy": 0.0,
        "actionability": 0.0,
        "completeness": 0.0,
        "professionalism": 0.0,
        "overall": 0.0,
        "reasoning": "Brief explanation"
    }}"""

    try:
        response = judge_llm.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise evaluation judge. Respond ONLY with valid JSON."},
                {"role": "user", "content": judge_prompt}
            ],
            temperature=0,
        )

        result_text = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            scores = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in judge response")

        overall = scores.get("overall", 0.0)

        return {
            "key": "review_quality",
            "score": float(overall),
            "comment": (
                f"Overall: {overall:.2f} | "
                f"Relevance: {scores.get('relevance', 'N/A')} | "
                f"Accuracy: {scores.get('accuracy', 'N/A')} | "
                f"Actionability: {scores.get('actionability', 'N/A')} | "
                f"Completeness: {scores.get('completeness', 'N/A')} | "
                f"Professionalism: {scores.get('professionalism', 'N/A')} | "
                f"Reasoning: {scores.get('reasoning', 'N/A')}"
            ),
        }

    except Exception as e:
        return {
            "key": "review_quality",
            "score": 0.0,
            "comment": f"❌ LLM judge failed: {str(e)}",
        }


def hallucination_check(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Uses an LLM to detect if the review hallucinates bugs not in the diff.
    
    A hallucination = the agent reports a specific bug or file that doesn't
    exist in the provided diff.
    """
    pr_diff = inputs.get("pr_diff", "")
    bugs_report = outputs.get("bugs_found", "")

    if not bugs_report or bugs_report.strip() in ["None", "No critical bugs found."]:
        return {
            "key": "hallucination_score",
            "score": 1.0,
            "comment": "No bugs reported — no hallucination possible.",
        }

    judge_prompt = f"""You are a hallucination detector. Your job is to check if an AI code reviewer 
    invented bugs that DO NOT actually exist in the provided code diff.

    The ACTUAL code diff:
    {pr_diff[:2000]}

    The AI's bug report:
    {bugs_report[:2000]}

    For each bug mentioned:
    1. Is it actually present in the diff? (grounded)
    2. Or did the AI make it up? (hallucinated)

    Respond ONLY with valid JSON:
    {{
        "total_bugs_mentioned": 0,
        "grounded_bugs": 0,
        "hallucinated_bugs": 0,
        "hallucination_rate": 0.0,
        "details": "Brief explanation"
    }}"""

    try:
        response = judge_llm.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise hallucination detector. Respond ONLY with valid JSON."},
                {"role": "user", "content": judge_prompt}
            ],
            temperature=0,
        )

        result_text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in judge response")

        hallucination_rate = result.get("hallucination_rate", 0.0)
        # Score = 1 - hallucination_rate (higher is better)
        score = max(0.0, 1.0 - float(hallucination_rate))

        return {
            "key": "hallucination_score",
            "score": score,
            "comment": (
                f"Grounded: {result.get('grounded_bugs', 'N/A')}, "
                f"Hallucinated: {result.get('hallucinated_bugs', 'N/A')}, "
                f"Rate: {hallucination_rate} | {result.get('details', '')}"
            ),
        }

    except Exception as e:
        return {
            "key": "hallucination_score",
            "score": 0.0,
            "comment": f"❌ Hallucination check failed: {str(e)}",
        }

# Export all evaluators

ALL_EVALUATORS = [
    verdict_correctness,
    bug_detection_recall,
    style_detection_recall,
    false_positive_check,
    review_has_structure,
    review_quality_llm_judge,
    hallucination_check,
]
