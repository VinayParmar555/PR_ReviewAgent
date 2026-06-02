import os
from openai import OpenAI
from schema.state import PRReviewState
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def style_reviewer(state: PRReviewState):
    """Agent 3 — Reviews code style, best practices and clean code"""
    
    SYSTEM_PROMPT = """
    You are an expert code style and best practices reviewer.
    
    Analyze the code for:
    1. PEP 8 compliance (Python style guide)
    2. Type hints missing
    3. Docstrings missing
    4. Naming conventions
    5. Code readability and clarity
    6. DRY principle violations
    7. Function/class design issues
    
    For each issue:
    - Point out the problem
    - Show the improved version
    
    Be constructive and educational.
    """
    
    # response = client.chat.completions.create(
    #     model="llama-3.3-70b-versatile",
    #     messages=[
    #         {"role": "system", "content": SYSTEM_PROMPT},
    #         {"role": "user", "content": f"""
    #             Diff Analysis:
                {state.diff_analysis}
                Raw Diff:
                {state.pr_diff}"""
            }
        ]
    )
    
    # style_issues = response.choices[0].message.content
    
    return {
        "style_issues": [style_issues]
    }