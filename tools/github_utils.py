import hmac
import hashlib
import os
from dotenv import load_dotenv
load_dotenv()

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature_header:
        return False
    
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    
    expected_signature = f"sha256={expected}"
    return hmac.compare_digest(expected_signature, signature_header)