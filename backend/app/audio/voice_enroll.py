"""
Maps speaker embeddings to real names.
Simplified for hackathon.
"""

speaker_registry = {}

def enroll_voice(speaker_id: str, name: str):
    speaker_registry[speaker_id] = name

def resolve_speaker(speaker_id: str):
    return speaker_registry.get(speaker_id, speaker_id)
