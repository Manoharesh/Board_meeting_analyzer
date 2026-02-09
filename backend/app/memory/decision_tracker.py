decisions = []

def add_decision(meeting_id, decision):
    decisions.append({
        "meeting_id": meeting_id,
        "decision": decision,
        "status": "pending"
    })

def get_decisions():
    return decisions
