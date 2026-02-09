meetings = {}

def store_chunk(meeting_id, chunk):
    meetings.setdefault(meeting_id, []).append(chunk)

def get_meeting(meeting_id):
    return meetings.get(meeting_id, [])
