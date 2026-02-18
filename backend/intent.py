import re

def classify(prompt):
    p = prompt.lower()

    # Poster/print materials
    if any(word in p for word in ["poster", "quote", "signage", "sale", "ad", "advertisement", 
                                  "flyer", "banner", "sign", "billboard", "print"]):
        return "poster"

    # Stories/narratives
    if any(word in p for word in ["story", "tale", "narrative", "scene", "chapter", 
                                  "plot", "fairytale", "fable", "bedtime"]):
        return "story"
    
    # Transformations/style transfer
    if any(word in p for word in ["transform", "convert", "change", "turn into", "make it",
                                  "style transfer", "reimagine", "redesign"]):
        return "transform"
    
    # Mood/emotion based
    if any(word in p for word in ["mood", "feel", "emotion", "vibe", "atmosphere",
                                  "emotional", "feeling", "sentiment"]):
        return "mood"

    # Default to image
    return "image"

def classify_intent(message):
    """Enhanced intent classification (alias for classify)"""
    return classify(message)

def extract_keywords(message):
    """Extract keywords from message for better context"""
    message_lower = message.lower()
    words = message_lower.split()
    
    keywords = {
        "subjects": [],
        "styles": [],
        "moods": [],
        "business": [],
        "colors": []
    }
    
    # Style keywords
    style_keywords = {
        "cinematic": ["cinematic", "movie", "film", "dramatic"],
        "minimalist": ["minimal", "simple", "clean", "modern"],
        "abstract": ["abstract", "abstract art", "non-representational"],
        "realistic": ["realistic", "real", "photorealistic", "lifelike"],
        "vintage": ["vintage", "retro", "old school", "classic"],
        "watercolor": ["watercolor", "water colour", "aquarelle"],
        "oil": ["oil painting", "oil", "painterly"],
        "sketch": ["sketch", "drawing", "pencil", "line art"]
    }
    
    # Mood keywords
    mood_keywords = ["happy", "sad", "peaceful", "energetic", "calm", "dramatic", 
                     "romantic", "dark", "bright", "warm", "cool", "mysterious",
                     "dull", "boring", "exciting", "melancholic", "joyful", "motivated"]
    
    # Business keywords
    business_keywords = ["product", "brand", "sale", "business", "professional", 
                         "marketing", "commercial", "corporate", "premium", "campaign"]
    
    # Color keywords
    color_keywords = ["red", "blue", "green", "yellow", "purple", "orange", "pink", 
                      "brown", "black", "white", "gold", "silver", "pastel", "vibrant"]
    
    # Extract styles
    for style, terms in style_keywords.items():
        if any(term in message_lower for term in terms):
            keywords["styles"].append(style)
    
    # Extract moods
    for mood in mood_keywords:
        if mood in message_lower:
            keywords["moods"].append(mood)
    
    # Extract business terms
    for term in business_keywords:
        if term in message_lower:
            keywords["business"].append(term)
    
    # Extract colors
    for color in color_keywords:
        if color in message_lower:
            keywords["colors"].append(color)
    
    # Extract potential subjects (nouns that might be important)
    important_words = [w for w in words if len(w) > 3 and w not in mood_keywords + color_keywords]
    keywords["subjects"] = list(set(important_words))[:3]
    
    return keywords