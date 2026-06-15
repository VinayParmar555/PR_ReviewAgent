import warnings
warnings.filterwarnings("ignore")
import time
import os
import logging
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client, traceable, evaluate
from evaluation.dataset import GOLDEN_EXAMPLES, EVAL_DATASET_NAME
from evaluation.evaluators import ALL_EVALUATORS
from agents.diff_analyzer import diff_analyzer
from agents.bug_detector import bug_detector
from agents.style_reviewer import style_reviewer
from agents.judge import judge as judge_agent
from openai import OpenAI
from schema.state import PRReviewState

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

ls_client = Client()

#  Step 1: Create or reuse the golden dataset in LangSmith

def setup_dataset() -> str:
    """Create the evaluation dataset in LangSmith if it doesn't exist."""

    # Check if dataset already exists
    existing_datasets = list(ls_client.list_datasets(dataset_name=EVAL_DATASET_NAME))
    
    if existing_datasets:
        dataset = existing_datasets[0]
        logger.info(f"Reusing existing dataset: '{EVAL_DATASET_NAME}' (id={dataset.id})")
        return EVAL_DATASET_NAME

    # Create new dataset
    dataset = ls_client.create_dataset(
        dataset_name=EVAL_DATASET_NAME,
        description="Golden test cases for evaluating the PR Review Agent pipeline. "
                    "Contains realistic PR diffs with known bugs, style issues, and expected verdicts."
    )

    ls_client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": example["inputs"],
                "outputs": example["outputs"],
            }
            for example in GOLDEN_EXAMPLES
        ]
    )

    logger.info(f"✅ Created dataset '{EVAL_DATASET_NAME}' with {len(GOLDEN_EXAMPLES)} examples")
    return EVAL_DATASET_NAME


#  Step 2: Define the target function (the system under test)

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

@traceable(name="pr_review_pipeline")
def target(inputs: dict) -> dict:
    """Run the full PR review pipeline on a synthetic PR diff.

    This simulates the agent pipeline without hitting the real GitHub API.
    Instead of fetching the diff from GitHub, we inject the diff directly.
    
    Args:
        inputs: Dict with 'pr_diff', 'pr_title', 'pr_description'
    
    Returns:
        Dict with 'bugs_found', 'style_issues', 'final_review', 'review_summary'
    """
    pr_diff = inputs["pr_diff"]
    pr_title = inputs.get("pr_title", "Test PR")
    pr_description = inputs.get("pr_description", "")

    #  Agent 1: Diff Analyzer (bypass GitHub API, inject diff directly)

    analysis_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": 
                """You are an expert code diff analyzer.
                Analyze:
                1. What files were changed
                2. What new functions/classes were added
                3. What was modified or deleted
                4. The overall purpose of this PR
                Be concise and technical."""
            },
            {"role": "user", "content": f"PR Title: {pr_title}\nPR Description: {pr_description}\nDiff:\n{pr_diff}"}
        ]
    )
    diff_analysis = analysis_response.choices[0].message.content
    time.sleep(4)

    #  Agent 2: Bug Detector
    state_for_bugs = PRReviewState(
        pr_url="https://github.com/eval/test/pull/1",
        pr_number=1,
        repo_name="eval/test",
        pr_diff=pr_diff,
        diff_analysis=diff_analysis,
    )
    bug_result = bug_detector(state_for_bugs)
    time.sleep(4)

    #  Agent 3: Style Reviewer
    state_for_style = state_for_bugs.model_copy(update=bug_result)
    style_result = style_reviewer(state_for_style)
    time.sleep(4)

    #  Agent 4: Judge (skip GitHub comment posting + DB saves)
    state_for_judge = state_for_style.model_copy(update=style_result)

    judge_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": """You are a senior software engineer doing a final PR review.
            You have received reports from 3 specialized agents:
            1. Diff Analyzer — what changed
            2. Bug Detector — bugs and security issues
            3. Style Reviewer — code quality issues

            Your job:
            1. Synthesize all reports into one clear, actionable review
            2. Prioritize issues by severity (Critical, Major, Minor)
            3. Give an overall verdict: APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION
            4. Keep the tone constructive and professional

            Format your review clearly with sections."""},
                        {"role": "user", "content": f"""
            === Diff Analysis ===
            {state_for_judge.diff_analysis}

            === Bugs Found ===
            {state_for_judge.bugs_found[0] if state_for_judge.bugs_found else "None"}

            === Style Issues ===
            {state_for_judge.style_issues[0] if state_for_judge.style_issues else "None"}"""}
        ]
    )

    final_review = judge_response.choices[0].message.content
    time.sleep(4)

    summary_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Summarize this PR review in 5-6 bullet points max. Keep it concise."},
            {"role": "user", "content": final_review}
        ]
    )
    review_summary = summary_response.choices[0].message.content
    time.sleep(4)

    return {
        "diff_analysis": diff_analysis,
        "bugs_found": bug_result["bugs_found"][0] if bug_result.get("bugs_found") else "",
        "style_issues": style_result["style_issues"][0] if style_result.get("style_issues") else "",
        "final_review": final_review,
        "review_summary": review_summary,
    }


#  Step 3: Run the evaluation

def run_evaluation():
    """Execute the full LangSmith evaluation pipeline."""

    logger.info("=" * 60)
    logger.info("  PR Review Agent — LangSmith Evaluation")
    logger.info("=" * 60)

    # Setup dataset
    dataset_name = setup_dataset()

    # Experiment metadata (shows in LangSmith UI)
    experiment_metadata = {
        "models": ["groq:llama-3.3-70b-versatile"],
        "prompts": ["diff_analyzer_v1", "bug_detector_v1", "style_reviewer_v1", "judge_v1"],
    }

    # Run evaluation
    logger.info(f"🚀 Starting evaluation on dataset '{dataset_name}'...")
    logger.info(f"   Evaluators: {len(ALL_EVALUATORS)}")
    logger.info(f"   Examples: {len(GOLDEN_EXAMPLES)}")

    results = evaluate(
        target,
        data=dataset_name,
        evaluators=ALL_EVALUATORS,
        experiment_prefix="pr-review-agent",
        description="Full pipeline evaluation: diff analysis → bug detection → style review → judge",
        max_concurrency=1,     # Conservative — each example makes 5 LLM calls
        metadata=experiment_metadata,
    )

    #  Print local summary
    logger.info("\n" + "=" * 60)
    logger.info("  EVALUATION RESULTS")
    logger.info("=" * 60)

    for result in results:
        # Access as attributes, not dict keys
        example = result.get("example")
        pr_title = example.inputs.get("pr_title", "Unknown") if example else "Unknown"
        logger.info(f"\n📄 PR: {pr_title}")

        eval_results = result.get("evaluation_results", {})
        if hasattr(eval_results, "results"):
            eval_results = eval_results.results
        else:
            eval_results = []

        for eval_result in eval_results:
            key = getattr(eval_result, "key", "unknown")
            score = getattr(eval_result, "score", "N/A")
            comment = getattr(eval_result, "comment", "")
            emoji = "✅" if (isinstance(score, (int, float)) and score >= 0.7) else "❌"
            logger.info(f"  {emoji} {key}: {score} — {comment}")

    logger.info("\n" + "=" * 60)
    logger.info("📊 View detailed results in LangSmith Dashboard:")
    logger.info(f"   https://smith.langchain.com → Project: {os.getenv('LANGCHAIN_PROJECT', 'default')}")
    logger.info("=" * 60)

    return results

if __name__ == "__main__":
    run_evaluation()
