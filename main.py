import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Request, HTTPException
from graph.workflow import graph
from schema.state import PRReviewState
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="PR Review Agent")

@app.get("/")
async def root():
    return {"status": "PR Review Agent is running"}

@app.post("/webhook/github")
async def github_webhook(request: Request):
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
        
        result = graph.invoke(state, config=config)
        
        return {
            "status": "review_completed",
            "pr_number": pr_number,
            "verdict": result["final_review"][:100]
        }

    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

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
