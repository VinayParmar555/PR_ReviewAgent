#  Golden test cases - realistic PR diffs with known issues

EVAL_DATASET_NAME = "pr-review-agent-eval"

GOLDEN_EXAMPLES = [
    #  Case 1: Clear security bug - Command injection
    {
        "inputs": {
            "pr_diff": """
            File: services/deploy.py
            Status: modified
            Additions: 5
            Deletions: 1
            Diff:
            - subprocess.run(["git", "clone", repo_url], check=True)
            + os.system(f"git clone {repo_url} && cd {repo_name} && pip install -r requirements.txt")
            + subprocess.run(f"curl {user_provided_url} | bash", shell=True)
            """,
            "pr_title": "Simplify deployment script commands",
            "pr_description": "Consolidated deployment steps into single shell commands for simplicity.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["command injection", "security vulnerability"],
            "must_detect_style": [],
            "severity": "critical",
            "min_bug_count": 1,
        },
    },

    #  Case 2: Missing error handling + style issues
    {
        "inputs": {
            "pr_diff": """
            File: services/payment.py
            Status: added
            Additions: 22
            Deletions: 0
            Diff:
            +import requests
            +
            +def processPayment(amount, card_number):
            +    r = requests.post("https://api.payments.com/charge", json={
            +        "amount": amount,
            +        "card": card_number
            +    })
            +    data = r.json()
            +    return data["transaction_id"]
            +
            +def refundPayment(txn_id):
            +    r = requests.post("https://api.payments.com/refund", json={"txn": txn_id})
            +    return r.json()
            """,
            "pr_title": "Add payment processing service",
            "pr_description": "New payment service with charge and refund support.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["error handling", "no exception handling", "no timeout"],
            "must_detect_style": ["naming convention", "camelCase", "type hint", "docstring"],
            "severity": "major",
            "min_bug_count": 1,
        },
    },

    #  Case 3: Clean, well-written code - should APPROVE
    {
        "inputs": {
            "pr_diff": """
            File: utils/validators.py
            Status: added
            Additions: 18
            Deletions: 0
            Diff:
            +from typing import Optional
            +import re
            +
            +
            +def validate_email(email: str) -> bool:
            +    \"\"\"Validate email format using regex pattern.
            +
            +    Args:
            +        email: The email address string to validate.
            +
            +    Returns:
            +        True if the email format is valid, False otherwise.
            +    \"\"\"
            +    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
            +    return bool(re.match(pattern, email))
            """,
            "pr_title": "Add email validation utility",
            "pr_description": "Added a well-documented email validator with type hints.",
        },
        "outputs": {
            "expected_verdict": "APPROVE",
            "must_detect_bugs": [],
            "must_detect_style": [],
            "severity": "none",
            "min_bug_count": 0,
        },
    },

    #  Case 4: Resource leak + race condition
    {
        "inputs": {
            "pr_diff": """
            File: services/file_processor.py
            Status: modified
            Additions: 12
            Deletions: 3
            Diff:
            -with open(filepath, 'r') as f:
            -    data = json.load(f)
            -    return process(data)
            +f = open(filepath, 'r')
            +data = json.load(f)
            +results = []
            +for item in data:
            +    results.append(transform(item))
            +shared_cache[filepath] = results
            +return results
            """,
            "pr_title": "Optimize file processing with caching",
            "pr_description": "Added caching layer for processed files to avoid re-reading.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["resource leak", "file not closed"],
            "must_detect_style": ["context manager"],
            "severity": "major",
            "min_bug_count": 1,
        },
    },

    #  Case 5: Hardcoded secrets
    {
        "inputs": {
            "pr_diff": """
            File: config/settings.py
            Status: modified
            Additions: 6
            Deletions: 2
            Diff:
            -API_KEY = os.getenv("API_KEY")
            -DB_PASSWORD = os.getenv("DB_PASSWORD")
            +API_KEY = "sk-proj-abc123def456ghi789"
            +DB_PASSWORD = "super_secret_password_123"
            +AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"
            +STRIPE_SECRET = "sk_live_51ABC123"
            """,
            "pr_title": "Fix configuration loading issues",
            "pr_description": "Resolved issues with environment variable loading by setting defaults.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["hardcoded secret", "credential", "security"],
            "must_detect_style": [],
            "severity": "critical",
            "min_bug_count": 1,
        },
    },

    #  Case 6: Off-by-one + missing edge case
    {
        "inputs": {
            "pr_diff": """
            File: utils/pagination.py
            Status: added
            Additions: 10
            Deletions: 0
            Diff:
            +def paginate(items, page, page_size):
            +    start = page * page_size
            +    end = start + page_size
            +    return items[start:end]
            +
            +def get_total_pages(total_items, page_size):
            +    return total_items // page_size
            """,
            "pr_title": "Add pagination utilities",
            "pr_description": "Simple pagination helper functions for list data.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["off-by-one", "division by zero", "zero page_size"],
            "must_detect_style": ["type hint", "docstring"],
            "severity": "major",
            "min_bug_count": 1,
        },
    },

    #  Case 7: Minor style issues only - should be APPROVE or NEEDS_DISCUSSION
    {
        "inputs": {
            "pr_diff": """
            File: models/user.py
            Status: modified
            Additions: 8
            Deletions: 4
            Diff:
            -class user:
            -    def __init__(self, name, email):
            -        self.name = name
            -        self.email = email
            +class user:
            +    def __init__(self,name,email,age):
            +        self.name=name
            +        self.email=email
            +        self.age=age
            +    def getAge(self):
            +        return self.age
            """,
            "pr_title": "Add age field to user model",
            "pr_description": "Extended user model with age attribute and getter.",
        },
        "outputs": {
            "expected_verdict": "NEEDS_DISCUSSION",
            "must_detect_bugs": [],
            "must_detect_style": ["PEP 8", "naming", "class name", "camelCase"],
            "severity": "minor",
            "min_bug_count": 0,
        },
    },

    #  Case 8: Infinite loop potential + no input validation
    {
        "inputs": {
            "pr_diff": """
            File: workers/retry_handler.py
            Status: added
            Additions: 14
            Deletions: 0
            Diff:
            +import time
            +import requests
            +
            +def fetch_with_retry(url):
            +    while True:
            +        try:
            +            response = requests.get(url)
            +            if response.status_code == 200:
            +                return response.json()
            +        except:
            +            pass
            +        time.sleep(1)
            """,
            "pr_title": "Add retry logic for API calls",
            "pr_description": "Implemented retry mechanism for unreliable external API calls.",
        },
        "outputs": {
            "expected_verdict": "REQUEST_CHANGES",
            "must_detect_bugs": ["infinite loop", "bare except", "no max retries"],
            "must_detect_style": ["type hint", "docstring"],
            "severity": "critical",
            "min_bug_count": 2,
        },
    },
]
