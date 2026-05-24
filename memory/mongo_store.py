from dotenv import load_dotenv
load_dotenv()
import os
from beanie import init_beanie
from typing import Optional, List
from datetime import datetime
import motor.motor_asyncio
from pymongo import MongoClient
from schema.review import PRReview

async def init_db():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
    await init_beanie(
        database=client["pr_review_agent"],
        document_models=[PRReview]
    )

def save_review_sync(state) -> str:
    """Synchronous version for use in sync functions"""
    
    sync_client = MongoClient(os.getenv("MONGO_URI"))
    db = sync_client["pr_review_agent"]
    collection = db["reviews"]
    
    doc = {
        "pr_url": state.pr_url,
        "pr_number": state.pr_number,
        "repo_name": state.repo_name,
        "diff_analysis": state.diff_analysis,
        "bugs_found": state.bugs_found,
        "style_issues": state.style_issues,
        "final_review": state.final_review,
        "review_summary": state.review_summary,
        "review_id": state.review_id,
        "comments_posted": state.comments_posted,
        "created_at": datetime.utcnow()
    }
    
    result = collection.insert_one(doc)
    sync_client.close()
    return str(result.inserted_id)

async def get_review_by_pr(repo_name: str, pr_number: int) -> Optional[PRReview]:
    return await PRReview.find_one(
        PRReview.repo_name == repo_name,
        PRReview.pr_number == pr_number
    )

async def get_all_reviews(repo_name: str) -> List[PRReview]:
    return await PRReview.find(
        PRReview.repo_name == repo_name
    ).sort(-PRReview.created_at).to_list()

async def get_acceptance_rate(repo_name: str) -> dict:
    total = await PRReview.find(
        PRReview.repo_name == repo_name
    ).count()
    
    posted = await PRReview.find(
        PRReview.repo_name == repo_name,
        PRReview.comments_posted == True
    ).count()
    
    return {
        "total_reviews": total,
        "comments_posted": posted,
        "success_rate": f"{(posted/total*100):.1f}%" if total > 0 else "0%"
    }