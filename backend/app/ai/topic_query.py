def query_by_topic(chunks, topic: str):
    return [c for c in chunks if topic.lower() in c["text"].lower()]
