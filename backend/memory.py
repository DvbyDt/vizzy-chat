import json
import os
import time
from datetime import datetime
from collections import Counter

user_memory = {}
user_sessions = {}

def update_memory(user_id, msg):
    if user_id not in user_memory:
        user_memory[user_id] = []
    user_memory[user_id].append({
        "message": msg,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 50 messages
    if len(user_memory[user_id]) > 50:
        user_memory[user_id] = user_memory[user_id][-50:]

def get_context(user_id):
    history = user_memory.get(user_id, [])
    return history[-5:]   # last 5 messages for context

def get_user_preferences(user_id):
    """Get user preferences from memory"""
    if user_id not in user_memory:
        return {
            "favorite_style": None,
            "interaction_count": 0,
            "common_themes": []
        }
    
    # Analyze user history to determine preferences
    history = user_memory[user_id]
    
    preferences = {
        "favorite_style": detect_favorite_style(history),
        "interaction_count": len(history),
        "common_themes": detect_common_themes(history)
    }
    
    return preferences

def detect_favorite_style(history):
    """Detect user's favorite style from history"""
    styles = []
    style_keywords = {
        "cinematic": ["cinematic", "movie", "film"],
        "minimalist": ["minimal", "simple", "clean"],
        "abstract": ["abstract", "artistic"],
        "realistic": ["realistic", "real", "photograph"],
        "vintage": ["vintage", "retro", "old"],
        "modern": ["modern", "contemporary"],
        "art": ["art", "artistic", "creative"],
        "poster": ["poster", "sign", "ad"],
        "story": ["story", "narrative", "tale"]
    }
    
    for entry in history[-10:]:  # Look at last 10 messages
        msg = entry["message"].lower()
        for style, keywords in style_keywords.items():
            if any(k in msg for k in keywords):
                styles.append(style)
    
    # Return most common style
    if styles:
        return max(set(styles), key=styles.count)
    return None

def detect_common_themes(history):
    """Detect common themes in user's messages"""
    themes = []
    for entry in history[-5:]:
        words = entry["message"].lower().split()
        themes.extend([w for w in words if len(w) > 4])
    
    # Return unique themes
    return list(set(themes))[:3]

def start_session(user_id):
    """Start a new conversation session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "session_id": datetime.now().isoformat(),
            "message_count": 0,
            "start_time": time.time()
        }
    user_sessions[user_id]["message_count"] += 1
    return user_sessions[user_id]

def end_session(user_id):
    """End current session"""
    if user_id in user_sessions:
        session_data = user_sessions[user_id]
        session_data["end_time"] = time.time()
        session_data["duration"] = session_data["end_time"] - session_data["start_time"]
        del user_sessions[user_id]
        return session_data
    return None

def get_session_context(user_id):
    """Get current session info"""
    return user_sessions.get(user_id, {})