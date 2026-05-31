import asyncio
import logging
from schema.state import PRReviewState
from graph.workflow import graph
from tools.github_tools import post_pr_comment

logger = logging.getLogger(__name__)

async def run_review(state: PRReviewState, config: dict):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, graph.invoke, state, config)
        logger.info(f"✅ Review completed: {state.repo_name} PR#{state.pr_number}")

    except Exception as e:
        logger.error(f"❌ Review failed: {e}")
        post_pr_comment(
            repo_name=state.repo_name,
            pr_number=state.pr_number,
            comment=f"## 🤖 AI PR Review\n\n❌ Review failed: {str(e)}"
        )