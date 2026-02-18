pending_context = {}

def init_user(user_id):
    if user_id not in pending_context:
        pending_context[user_id] = {}

def needs_context(user_id):
    init_user(user_id)
    # We need context if we don't have mood
    # For day queries, we always want to ask for mood first
    return "mood" not in pending_context[user_id]

def update_context(user_id, message):
    init_user(user_id)
    msg = message.lower()

    # Expanded mood list
    moods = ["happy","sad","tired","peaceful","excited","angry","nostalgic","anxious",
             "dull","boring","energetic","calm","romantic","mysterious","professional",
             "creative","melancholic","subdued","weary","vibrant","joyful","somber",
             "tender","enigmatic","polished","imaginative","hectic","serene","inspiring",
             "uplifting","thoughtful", "frustrated", "relaxed", "contemplative", "motivated"]
    
    events = ["work","office","family","friends","home","personal","life","career",
              "morning","afternoon","evening","night","weekend","vacation","meeting",
              "day", "today", "yesterday", "tomorrow", "business", "company"]

    for m in moods:
        if m in msg:
            pending_context[user_id]["mood"] = m
            print(f"✅ Detected mood: {m}")  # For debugging

    for e in events:
        if e in msg:
            pending_context[user_id]["event"] = e
            print(f"✅ Detected event: {e}")  # For debugging

def get_context_prompt(user_id):
    init_user(user_id)

    mood = pending_context[user_id].get("mood", "")
    event = pending_context[user_id].get("event", "")

    if mood and event:
        return f"{mood} atmosphere related to {event}"
    elif mood:
        return f"{mood} atmosphere"
    elif event:
        return f"scene related to {event}"
    return ""

def clear_context(user_id):
    """Clear context for a user (useful for new conversations)"""
    if user_id in pending_context:
        pending_context[user_id] = {}