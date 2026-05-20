from dotenv import load_dotenv
load_dotenv()
import os
from github import Github

github_client = Github(os.getenv("GITHUB_TOKEN"))

def get_pr_diff(repo_name: str, pr_number: int) -> str:
    """Fetch PR diff from GitHub"""
    repo = github_client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    files_changed = []
    for file in pr.get_files():
        files_changed.append(
            f"""
                File: {file.filename}
                Status: {file.status}
                Additions: {file.additions}
                Deletions: {file.deletions}
                Diff: {file.patch}
            """
        )
    
    return "\n---\n".join(files_changed)

def post_pr_comment(repo_name: str, pr_number: int, comment: str) -> bool:
    """Post review comment on PR"""
    try:
        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(comment)
        return True
    except Exception as e:
        print(f"Error posting comment: {e}")
        return False

def get_pr_info(repo_name: str, pr_number: int) -> dict:
    """Get basic PR information"""
    repo = github_client.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    print(pr)
    return {
        "title": pr.title,
        "description": pr.body,
        "author": pr.user.login,
        "base_branch": pr.base.ref,
        "head_branch": pr.head.ref,
        "files_changed": pr.changed_files,
        "additions": pr.additions,
        "deletions": pr.deletions
    }