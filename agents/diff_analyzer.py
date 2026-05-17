from dotenv import load_dotenv
load_dotenv()
import os
from openai import OpenAI
from tools.github_mcp import get_pr_diff, get_pr_info

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def diff_analyzer(state):
    """Agent 1 — Analyzes PR diff and understands what changed"""
    
    pr_diff = get_pr_diff(state.repo_name, state.pr_number)
    pr_info = get_pr_info(state.repo_name, state.pr_number)
    
    SYSTEM_PROMPT = """
    You are an expert code diff analyzer.
    Your job is to understand what changed in this PR and provide a clear summary.
    
    Analyze:
    1. What files were changed
    2. What new functions/classes were added
    3. What was modified or deleted
    4. The overall purpose of this PR
    
    Be concise and technical.
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
                    PR Title: {pr_info['title']}
                    PR Description: {pr_info['description']}
                    Author: {pr_info['author']}
                    Files Changed: {pr_info['files_changed']}
                    Diff: {pr_diff}"""
            }
        ]
    )
    
    analysis = response.choices[0].message.content
    
    return {
        "pr_diff": pr_diff,
        "diff_analysis": analysis
    }