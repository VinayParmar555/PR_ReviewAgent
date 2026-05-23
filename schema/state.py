from pydantic import BaseModel, Field
from typing import List, Optional
from langgraph.graph.message import add_messages
from typing import Annotated

class PRReviewState(BaseModel):
    pr_url: str = Field(description="GitHub PR URL")
    pr_number: int = Field(description="PR number")
    repo_name: str = Field(description="Repository name e.g. owner/repo")
    
    pr_diff: Optional[str] = Field(default=None, description="Raw diff from GitHub")
    diff_analysis: Optional[str] = Field(default=None, description="Agent 1 output")
    bugs_found: Optional[List[str]] = Field(default=None, description="Agent 2 output")
    style_issues: Optional[List[str]] = Field(default=None, description="Agent 3 output")
    final_review: Optional[str] = Field(default=None, description="Agent 4 output")
    review_summary: Optional[str] = Field(default=None, description="Summary of the final_review")
    review_id: Optional[str] = Field(default=None)
    comments_posted: bool = Field(default=False)
    
    messages: Annotated[List, add_messages] = Field(default=[])