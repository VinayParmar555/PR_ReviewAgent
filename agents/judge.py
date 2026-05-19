from dotenv import load_dotenv
load_dotenv()
import os
from tools.github_mcp import post_pr_comment
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def judge(state):
    """Agent 4 — Combines all reports and generates final review"""
    
    SYSTEM_PROMPT = """
    You are a senior software engineer doing a final PR review.
    You have received reports from 3 specialized agents:
    1. Diff Analyzer — what changed
    2. Bug Detector — bugs and security issues
    3. Style Reviewer — code quality issues
    
    Your job:
    1. Synthesize all reports into one clear, actionable review
    2. Prioritize issues by severity (Critical, Major, Minor)
    3. Give an overall verdict: APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION
    4. Keep the tone constructive and professional
    
    Format your review clearly with sections.
    """
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
                === Diff Analysis ===
                {state.diff_analysis}

                === Bugs Found ===
                {state.bugs_found[0] if state.bugs_found else "None"}

                === Style Issues ===
                {state.style_issues[0] if state.style_issues else "None"}"""
            }
        ]
    )

    final_review = response.choices[0].message.content
    
    summary_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Summarize this PR review in 5-6 bullet points max. Keep it concise for GitHub comment."},
            {"role": "user", "content": final_review}
        ]
    )

    summary = summary_response.choices[0].message.content

    posted = post_pr_comment(
        repo_name=state.repo_name,
        pr_number=state.pr_number,
        comment=f"## 🤖 AI PR Review\n\n{summary}"
    )
    
    return {
        "final_review": final_review,
        "review_summary" : summary,
        "comments_posted": posted
    }