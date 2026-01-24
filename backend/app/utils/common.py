import random
import string
from datetime import datetime

def generate_request_id(counter: int) -> str:
    """Generates a request ID in the format CST-YYYY-XXXX"""
    year = datetime.now().year
    return f"CST-{year}-{counter:04d}"

def get_allowed_transitions(current_status: str) -> list:
    """Returns allowed next states based on current state (Simple State Machine)"""
    transitions = {
        "new": ["triaged", "closed"], # Can be rejected/closed directly
        "triaged": ["assigned", "closed"],
        "assigned": ["in_progress", "triaged"], # Can be sent back to triage
        "in_progress": ["resolved", "assigned"], # Can be reassigned
        "resolved": ["closed", "in_progress"], # Can be reopened
        "closed": [] # Terminal state
    }
    return transitions.get(current_status, [])
