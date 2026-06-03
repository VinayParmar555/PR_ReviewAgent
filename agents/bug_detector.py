import os
from openai import OpenAI
from dotenv import load_dotenv
from schema.state import PRReviewState
load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def bug_detector(state: PRReviewState):
    """Agent 2 — Detects bugs, security issues and code smells"""
    
    SYSTEM_PROMPT = """
    You are an expert bug detection and security analysis agent.
    
    Analyze the code diff for:
    1. Logical bugs and errors
    2. Security vulnerabilities
    3. Edge cases not handled
    4. Potential runtime errors
    5. Memory leaks or resource issues
    
    For each issue found:
    - Describe the bug clearly
    - Explain why it is a problem
    - Suggest a fix
    
    If no bugs found, say "No critical bugs found."
    Be specific and technical.
    """
    

    # response = client.chat.completions.create(
    #     model="llama-3.3-70b-versatile",
    #     messages=[
    #         {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "user", "content": f"""
    #             Diff Analysis:
    #             {state.diff_analysis}
    #             Raw Diff:
    #             {state.pr_diff}
    #         """}
    #     ]
    )
    
    # bugs = response.choices[0].message.content
    
    return {
        "bugs_found": [bugs]
    }