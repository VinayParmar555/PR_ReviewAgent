import warnings
warnings.filterwarnings("ignore")
import os
import logging
from dotenv import load_dotenv
load_dotenv()
from tools.github_utils import verify_webhook_signature
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from graph.workflow import graph
from graph.background import run_review
from schema.state import PRReviewState
from pymongo import MongoClient

logger = logging.getLogger(__name__)

app = FastAPI(title="PR Review Agent")

@app.get("/")
async def root():
    return {"status": "PR Review Agent is running"}

@app.get("/stats")
async def stats():
    """Return aggregate review statistics from MongoDB."""
    try:
        sync_client = MongoClient(os.getenv("MONGO_URI"))
        db = sync_client["pr_review_agent"]
        collection = db["reviews"]

        total = collection.count_documents({})
        posted = collection.count_documents({"comments_posted": True})
        success_rate = f"{(posted / total * 100):.1f}%" if total > 0 else "0%"

        sync_client.close()

        return {
            "total_reviews": total,
            "comments_posted": posted,
            "success_rate": success_rate,
        }
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # --- HMAC signature verification ---
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    if payload.get("action") not in ["opened", "synchronize"]:
        return {"status": "ignored"}
    
    try:
        pr_number = payload["pull_request"]["number"]
        repo_name = payload["repository"]["full_name"]
        pr_url = payload["pull_request"]["html_url"]

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field in payload: {e}")
    
    try:
        state = PRReviewState(
            pr_url=pr_url,
            pr_number=pr_number,
            repo_name=repo_name
        )
        
        config = {
            "configurable": {
                "thread_id": f"{repo_name}-pr-{pr_number}"
            }
        }
        
        background_tasks.add_task(run_review, state, config)

        return {
            "status": "review_queued",
            "pr_number": pr_number,
            "message": "Background review process started"
        }

    except Exception as e:
        logger.error(f"Failed to queue review: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue review: {str(e)}")

@app.get("/review/{repo_owner}/{repo_name}/{pr_number}")
async def manual_review(repo_owner: str, repo_name: str, pr_number: int):
    full_repo = f"{repo_owner}/{repo_name}"
    
    try:
        state = PRReviewState(
            pr_url=f"https://github.com/{full_repo}/pull/{pr_number}",
            pr_number=pr_number,
            repo_name=full_repo
        )
        
        config = {
            "configurable": {
                "thread_id": f"{full_repo}-pr-{pr_number}"
            }
        }
        
        result = graph.invoke(state, config=config)
        
        return {
            "status": "completed",
            "summary": result["review_summary"],
            "comments_posted": result["comments_posted"]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        logger.error(f"Review failed for {full_repo} PR#{pr_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")