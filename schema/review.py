from beanie import Document
from typing import Optional, List
from datetime import datetime
from pydantic import Field

class PRReview(Document):
    pr_url: str
    pr_number: int
    repo_name: str
    diff_analysis: Optional[str] = None
    bugs_found: Optional[List[str]] = None
    style_issues: Optional[List[str]] = None
    final_review: Optional[str] = None
    review_summary: Optional[str] = None
    comments_posted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reviews"