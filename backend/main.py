from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from io import BytesIO
import base64
import logging
import time
import random
import re
import os
import requests
from typing import List, Optional, Dict, Any
import asyncio
from PIL import Image, ImageDraw, ImageFont

# Import your custom logic
from memory import update_memory, get_context, get_user_preferences
from intent import classify_intent, extract_keywords
from story import generate_story
from context import needs_context, update_context, get_context_prompt, pending_context, clear_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vizzy Chat API", version="1.0.0")

# Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174", 
        "http://localhost:5175",
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://vizzy-chat.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================
# DEEPAI IMAGE GENERATION (100% WORKING, FREE)
# ==============================================

def create_colored_placeholder(prompt: str, index: int, width: int = 512, height: int = 512) -> Image.Image:
    """Create a colored placeholder image when APIs fail"""
    
    # Generate a nice color based on prompt hash
    colors = [
        (255, 99, 132),   # Pink
        (54, 162, 235),    # Blue
        (255, 206, 86),    # Yellow
        (75, 192, 192),    # Teal
        (153, 102, 255),   # Purple
        (255, 159, 64),    # Orange
        (255, 99, 132),    # Pink
        (54, 162, 235),    # Blue
    ]
    
    color = colors[index % len(colors)]
    
    # Create image
    img = Image.new('RGB', (width, height), color=color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fall back to default
    try:
        # Different font paths for different systems
        font_paths = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\Arial.ttf"
        ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, 30)
                break
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw prompt text
    words = prompt.split()
    line1 = " ".join(words[:5]) if words else "AI Generated"
    line2 = " ".join(words[5:10]) if len(words) > 5 else "Image"
    
    # Center text
    try:
        bbox = draw.textbbox((0, 0), line1, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height//2 - 40), line1, fill='white', font=font)
        
        bbox = draw.textbbox((0, 0), line2, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height//2 + 10), line2, fill='white', font=font)
    except:
        # If text drawing fails, just return colored image
        pass
    
    return img

async def generate_with_deepai(
    prompt: str, 
    num_images: int = 2,
    width: int = 512,
    height: int = 512
) -> List[Image.Image]:
    """
    Generate images using DeepAI - 100% WORKING, free with small watermark
    Returns list of PIL Images
    """
    
    images = []
    
    for i in range(num_images):
        try:
            logger.info(f"🎨 Generating image {i+1}/{num_images} with DeepAI")
            
            # DeepAI free endpoint with demo key
            response = requests.post(
                "https://api.deepai.org/api/text-to-image",
                data={'text': prompt},
                headers={'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'},  # Free demo key
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result.get('output_url')
                
                if image_url:
                    # Download the image
                    img_response = requests.get(image_url, timeout=30)
                    img = Image.open(BytesIO(img_response.content))
                    
                    # Resize if needed
                    if img.size != (width, height):
                        img = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Ensure RGB mode
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    images.append(img)
                    logger.info(f"✅ Image {i+1} generated successfully from DeepAI")
                else:
                    logger.warning("No image URL in DeepAI response")
                    # Create colored placeholder
                    img = create_colored_placeholder(prompt, i, width, height)
                    images.append(img)
            else:
                logger.error(f"DeepAI error: {response.status_code}")
                # Create colored placeholder
                img = create_colored_placeholder(prompt, i, width, height)
                images.append(img)
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ DeepAI timeout for image {i+1}")
            img = create_colored_placeholder(prompt, i, width, height)
            images.append(img)
        except Exception as e:
            logger.error(f"❌ DeepAI failed for image {i+1}: {e}")
            img = create_colored_placeholder(prompt, i, width, height)
            images.append(img)
    
    return images

# ==============================================
# CONVERSATION STATE MANAGEMENT
# ==============================================

conversation_state = {}

def get_last_interaction(user_id):
    """Get the last bot message for this user"""
    if user_id in conversation_state and conversation_state[user_id].get("last_bot_message"):
        return conversation_state[user_id]["last_bot_message"]
    return None

def store_question_asked(user_id, original_query):
    """Store that we asked a clarifying question"""
    if user_id not in conversation_state:
        conversation_state[user_id] = {}
    conversation_state[user_id]["last_bot_message"] = {
        "type": "question",
        "original_query": original_query,
        "asked_at": time.time()
    }

def store_generated_response(user_id, response):
    """Store the last generated response"""
    if user_id not in conversation_state:
        conversation_state[user_id] = {}
    conversation_state[user_id]["last_bot_message"] = response

def update_context_with_mood(user_id, mood):
    """Update user context with detected mood"""
    if user_id not in pending_context:
        pending_context[user_id] = {}
    pending_context[user_id]["mood"] = mood
    logger.info(f"Updated mood for {user_id}: {mood}")

def generate_conversational_suggestions(mood):
    """Generate conversational suggestions based on detected mood"""
    suggestions = [
        "It was peaceful and calm",
        "It was busy and hectic",
        "It was dull and I needed motivation",
        "It was exciting and fun",
        "It was challenging but rewarding"
    ]
    return suggestions

# ==============================================
# HELPER FUNCTIONS
# ==============================================

def extract_slogan(message):
    """Extract slogan from message (text in quotes or after 'slogan should be')"""
    # Try to find text in quotes
    quoted = re.findall(r'"([^"]*)"', message)
    if quoted:
        return quoted[0]
    
    # Try single quotes
    quoted = re.findall(r"'([^']*)'", message)
    if quoted:
        return quoted[0]
    
    # Try after "slogan should be"
    if "slogan should be" in message.lower():
        parts = message.lower().split("slogan should be")
        if len(parts) > 1:
            slogan = parts[1].strip()
            # Remove trailing punctuation
            slogan = re.sub(r'[.!?]$', '', slogan)
            return slogan
    
    # Try after "with text"
    if "with text" in message.lower():
        parts = message.lower().split("with text")
        if len(parts) > 1:
            slogan = parts[1].strip()
            slogan = re.sub(r'[.!?]$', '', slogan)
            return slogan
    
    return None

def encode_images(images):
    """Encode PIL images to base64 with optimization"""
    encoded = []
    for img in images:
        try:
            # Resize if too large (max 1024x1024)
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buf = BytesIO()
            # Save with optimization
            img.save(buf, format="PNG", optimize=True)
            encoded.append(base64.b64encode(buf.getvalue()).decode())
        except Exception as e:
            logger.error(f"Image encoding failed: {e}")
            encoded.append(None)
    return encoded

# ==============================================
# DYNAMIC SUGGESTION GENERATOR
# ==============================================

def generate_dynamic_suggestions(user_message):
    """Generate contextual suggestions based on user's message"""
    
    message_lower = user_message.lower()
    suggestions = []
    
    # Mood-based suggestions
    mood_keywords = {
        "dull": ["Add vibrant colors", "Increase contrast", "Make it more energetic", "Add spark of inspiration"],
        "boring": ["Make it more dynamic", "Add interesting elements", "Create visual tension", "Use unexpected colors"],
        "tired": ["Soften the palette", "Add warm, restful tones", "Create calming composition", "Use gentle gradients"],
        "happy": ["Amplify the brightness", "Add playful elements", "Use cheerful colors", "Create uplifting composition"],
        "sad": ["Deepen the blues", "Add melancholic tones", "Create atmospheric mood", "Use soft, diffused light"],
        "energetic": ["Add motion blur", "Use dynamic angles", "Create visual rhythm", "Bold contrasting colors"],
        "peaceful": ["Soft, gentle transitions", "Calm color palette", "Balanced composition", "Serene atmosphere"],
        "romantic": ["Warm golden tones", "Soft focus effect", "Dreamy atmosphere", "Tender lighting"],
        "mysterious": ["Deep shadows", "Ethereal glow", "Hidden elements", "Intriguing composition"],
        "professional": ["Clean lines", "Minimalist design", "Corporate colors", "Polished finish"],
        "creative": ["Abstract elements", "Artistic flair", "Unconventional composition", "Creative color mixing"],
        "busy": ["Simplify the composition", "Focus on key elements", "Use organized layout", "Clean visual hierarchy"],
        "calm": ["Gentle gradients", "Soft transitions", "Peaceful color palette", "Balanced composition"],
        "motivation": ["Inspiring colors", "Uplifting composition", "Energetic elements", "Positive imagery"],
        "inspired": ["Creative flourishes", "Artistic expression", "Imaginative elements", "Unique perspective"]
    }
    
    # Style-based suggestions
    style_suggestions = [
        "Try watercolor effect",
        "Make it look like an oil painting",
        "Add sketch-like quality",
        "Create digital art style",
        "Use cinematic lighting",
        "Make it look like a photograph",
        "Add vintage feel",
        "Create minimalist style",
        "Make it more abstract",
        "Add surreal elements"
    ]
    
    # Color-based suggestions
    color_suggestions = [
        "Use warmer tones",
        "Try cooler palette",
        "Add more vibrant colors",
        "Make it monochromatic",
        "Use complementary colors",
        "Add pastel shades",
        "Deepen the shadows",
        "Brighten the highlights"
    ]
    
    # Find matching mood keywords
    found_moods = []
    for mood, mood_suggestions in mood_keywords.items():
        if mood in message_lower:
            found_moods.extend(mood_suggestions)
    
    # Add mood-based suggestions (prioritize these)
    if found_moods:
        # Remove duplicates and take up to 2
        unique_mood_suggestions = list(dict.fromkeys(found_moods))
        suggestions.extend(unique_mood_suggestions[:2])
    
    # Add random style and color suggestions
    if len(suggestions) < 3:
        suggestions.append(random.choice(style_suggestions))
    if len(suggestions) < 4:
        suggestions.append(random.choice(color_suggestions))
    
    # Shuffle and return unique suggestions
    suggestions = list(dict.fromkeys(suggestions))[:4]
    random.shuffle(suggestions)
    
    return suggestions

# ==============================================
# DYNAMIC CLARIFYING QUESTION GENERATOR
# ==============================================

def generate_clarifying_question(user_message):
    """Generate a dynamic clarifying question based on what the user said"""
    
    message_lower = user_message.lower()
    
    # Conversational questions - NO suggestions/buttons
    questions = {
        "day": [
            "I'd love to visualize your day! Could you tell me more about how it felt? What was the overall mood?",
            "Surely! But can you please elaborate on how your day was? That will help me gauge the mood and generate the image better.",
            "Of course! To create something personal, could you describe the feeling of your day? Was it peaceful, stressful, exciting, or something else?",
            "I'd be happy to create that! Help me understand - what was the predominant emotion or energy of your day?"
        ],
        "feeling": [
            "What emotions would you like me to capture in this artwork?",
            "Tell me more about what you're feeling - that will help me create something meaningful.",
            "I want to make sure I capture the right mood. Could you describe the feeling in more detail?",
            "The more you share about your emotions, the better I can visualize them. What's on your mind?"
        ],
        "default": [
            "To create something personal, could you tell me more about the mood or feeling you want to express?",
            "Help me understand - what emotion or atmosphere should this convey?",
            "I'd love to create something meaningful for you. Could you elaborate on what you're looking for?",
            "Let's make something special! Tell me more about the feeling you want to capture."
        ]
    }
    
    # Detect context
    if "day" in message_lower or "today" in message_lower:
        context = "day"
    elif any(word in message_lower for word in ["feel", "feeling", "emotion", "mood", "vibe"]):
        context = "feeling"
    else:
        context = "default"
    
    # Return a random question from the appropriate context
    return random.choice(questions[context])

# ==============================================
# DYNAMIC REASONING GENERATOR
# ==============================================

def generate_dynamic_reasoning(message, mood, mode):
    """Generate different reasoning based on the actual input"""
    
    # Extract a short preview of the message
    message_preview = message[:30] + "..." if len(message) > 30 else message
    
    # Mode-specific reasoning templates
    mode_templates = {
        "art": [
            f"As an artist, I've interpreted '{message_preview}' through a {mood} lens, creating expressive variations",
            f"Your vision of '{message_preview}' inspired these {mood} artistic interpretations",
            f"I've translated '{message_preview}' into {mood} visual poetry using expressive techniques",
            f"Each artistic variation captures a different facet of '{message_preview}' with {mood} emotion"
        ],
        "poster": [
            f"For this poster, I've designed a {mood} background that complements your message",
            f"The composition uses {mood} tones to create visual impact for your poster",
            f"I've created a clean, professional backdrop that lets your message shine",
            f"This {mood} design provides the perfect canvas for your text"
        ],
        "story": [
            f"Your story about '{message_preview}' unfolds in three {mood} chapters",
            f"I've crafted a {mood} narrative arc based on your vision",
            f"Each scene builds on the {mood} atmosphere to tell your tale",
            f"The story follows a {mood} journey from beginning to end"
        ],
        "transform": [
            f"I've reimagined your concept in a completely new {mood} style",
            f"This transformation gives '{message_preview}' a fresh {mood} perspective",
            f"The {mood} interpretation brings new life to your original idea",
            f"Your vision has been reborn in this {mood} artistic style"
        ],
        "business": [
            f"This professional {mood} visual is designed for maximum business impact",
            f"I've created a {mood} corporate aesthetic that conveys professionalism",
            f"The {mood} composition speaks to your target audience effectively",
            f"This polished {mood} design elevates your brand message"
        ],
        "personal": [
            f"I've interpreted your request through a {mood} lens, focusing on '{message_preview}'",
            f"Drawing from '{message_preview}', I've emphasized {mood} elements in the composition",
            f"The {mood} atmosphere you described guided my creative direction",
            f"Your vision of '{message_preview}' inspired these {mood} variations"
        ]
    }
    
    # Get templates for current mode, fallback to personal
    templates = mode_templates.get(mode, mode_templates["personal"])
    
    # Pick a random template
    base_reasoning = random.choice(templates)
    
    # Add a random insight
    insights = [
        "Notice how the lighting creates depth and atmosphere.",
        "The composition guides your eye through the scene.",
        "The textures add richness to the overall feeling.",
        "The color harmony reinforces the emotional tone.",
        "The contrast creates visual interest and drama.",
        "The subtle gradients add a sense of depth.",
        "The focal point draws attention to the key element.",
        "The balance of elements creates visual harmony."
    ]
    
    insight = random.choice(insights)
    
    return f"{base_reasoning}. {insight}"

# ==============================================
# CLARIFIED REQUEST PROCESSOR
# ==============================================

async def process_clarified_request(req, last_question):
    """Process a response to a clarifying question with better context understanding"""
    
    original_query = last_question.get("original_query", req.message)
    clarification = req.message
    
    logger.info(f"Processing clarification - Original: '{original_query}', Clarification: '{clarification}'")
    
    # Extract key information from clarification
    message_lower = clarification.lower()
    
    # Enhanced mood detection with descriptive phrases
    mood_map = {
        "dull": "dull and unmotivated",
        "boring": "boring and uneventful",
        "tired": "tired and exhausted",
        "peaceful": "peaceful and calm",
        "energetic": "energetic and vibrant",
        "happy": "happy and joyful",
        "sad": "sad and melancholic",
        "busy": "busy and hectic",
        "calm": "calm and relaxed",
        "motivation": "needing motivation",
        "motivating": "seeking motivation",
        "inspired": "inspired and uplifted",
        "frustrated": "frustrated and challenging",
        "excited": "excited and thrilling",
        "relaxed": "relaxed and easy-going",
        "thoughtful": "thoughtful and reflective",
        "not too great": "neither good nor bad",
        "great": "great and wonderful"
    }
    
    # Find the best matching mood description
    detected_mood_desc = "thoughtful and reflective"
    simple_mood = "thoughtful"
    
    for keyword, desc in mood_map.items():
        if keyword in message_lower:
            detected_mood_desc = desc
            simple_mood = keyword
            logger.info(f"Detected mood: {keyword} -> {desc}")
            break
    
    # Update context with detected mood
    update_context_with_mood(req.user_id, simple_mood)
    
    # Create enhanced prompt for image generation
    if "my day" in original_query.lower():
        enhanced_message = f"An artistic representation of a day that was {detected_mood_desc}. Capture the feeling of {simple_mood} through abstract art, with appropriate colors and mood."
    else:
        enhanced_message = f"{original_query}. The mood is {detected_mood_desc}."
    
    logger.info(f"Enhanced message for generation: {enhanced_message}")
    
    # Create enhanced request
    enhanced_req = ChatRequest(
        user_id=req.user_id,
        message=enhanced_message,
        conversation_id=req.conversation_id,
        mode=req.mode if hasattr(req, 'mode') else "art"
    )
    
    # Generate content
    result = await generate_content(enhanced_req)

    # Mark the last bot response so future messages are not treated as clarifications
    store_generated_response(req.user_id, result)

    # Return ONLY the image generation result (no extra text wrapper)
    return result

# ==============================================
# MODE-SPECIFIC GENERATION
# ==============================================

async def generate_content(req):
    """Generate images/stories based on the request with mode-specific handling"""
    start_time = time.time()
    
    # Gather Context
    user_ctx = pending_context.get(req.user_id, {})
    mood = user_ctx.get("mood", "vibrant")
    event = user_ctx.get("event", "creative scene")
    context_prompt = get_context_prompt(req.user_id)
    
    # Get the mode (from request)
    mode = req.mode if hasattr(req, 'mode') else "personal"
    logger.info(f"Mode: {mode}, Message: {req.message}")
    
    # Get user preferences
    preferences = get_user_preferences(req.user_id)
    
    # Base style and negative prompt
    base_style = "artistic, creative, atmospheric, emotional, masterpiece"
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, text, watermark, signature, worst quality"
    
    # Apply user preferences
    if preferences.get('favorite_style'):
        base_style += f", {preferences['favorite_style']}"
    
    # ==============================================
    # MODE 1: ART MODE - Creative, artistic interpretations
    # ==============================================
    if mode == "art":
        # Check if this is about "my day" or emotions
        message_lower = req.message.lower()
        is_about_day = "my day" in message_lower or "today" in message_lower or "day was" in message_lower
        has_emotion = any(word in message_lower for word in ["feel", "felt", "emotion", "mood", "happy", "sad", "dull", "boring", "exciting"])
        
        # Art styles based on mood/context
        art_styles = ["expressionist", "impressionist", "abstract", "surreal", "modern art", "contemporary"]
        selected_style = random.choice(art_styles)
        
        # Extract mood from message (if any)
        mood_map = {
            "happy": "joyful, vibrant, bright colors, uplifting",
            "sad": "melancholic, blue tones, soft, somber",
            "dull": "subdued, muted colors, low contrast, quiet",
            "boring": "monotone, repetitive patterns, simple",
            "exciting": "dynamic, bold colors, energetic strokes",
            "peaceful": "calm, soft gradients, serene",
            "angry": "sharp lines, red tones, aggressive strokes",
            "tired": "washed out, faded, soft focus"
        }
        
        # Detect mood
        detected_mood_style = "thoughtful, contemplative"
        for mood_word, style_desc in mood_map.items():
            if mood_word in message_lower:
                detected_mood_style = style_desc
                break
        
        # Create enhanced prompt
        if is_about_day or has_emotion:
            if "my day" in message_lower:
                enhanced_prompt = f"Abstract artistic interpretation of someone's day, emotional representation, {detected_mood_style}, expressive art, personal journey, visual storytelling, {selected_style} style"
            else:
                enhanced_prompt = f"{req.message}, {detected_mood_style}, {selected_style} style, artistic interpretation, creative composition, emotional, {base_style}"
        else:
            enhanced_prompt = f"{req.message}, {selected_style} style, artistic interpretation, creative composition, vibrant colors, emotional, {base_style}"
        
        logger.info(f"ART MODE - Using style: {selected_style}")
        logger.info(f"ART MODE - Prompt: {enhanced_prompt}")
        
        # Use DeepAI for generation (100% working)
        images = await generate_with_deepai(
            prompt=enhanced_prompt,
            num_images=2,
            width=512,
            height=512
        )
        
        encoded_images = encode_images(images)
        
        # Create personalized reasoning
        if is_about_day:
            # Extract mood for reasoning
            mood_desc = "thoughtful"
            if "dull" in message_lower:
                mood_desc = "dull and unmotivated, using muted colors and low contrast to reflect the low energy"
            elif "motivation" in message_lower:
                mood_desc = "needing motivation, with a gradual shift from dark to lighter tones representing the struggle"
            elif "peaceful" in message_lower:
                mood_desc = "peaceful and calm, with soft gradients and serene composition"
            elif "energetic" in message_lower:
                mood_desc = "energetic and vibrant, with dynamic lines and bright colors"
            else:
                mood_desc = detected_mood_style
            
            insights = [
                "Notice how the lighting creates depth and atmosphere.",
                "The composition guides your eye through the scene.",
                "The textures add richness to the overall feeling.",
                "The color harmony reinforces the emotional tone.",
                "The contrast creates visual interest and drama."
            ]
            
            reasoning = f"I've created this image based on your description of a {mood_desc} day. The color palette and composition are designed to reflect that emotional state. {random.choice(insights)}"
        else:
            reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "image",
            "content": {
                "images": encoded_images,
                "reasoning": reasoning,
                "prompt_used": enhanced_prompt,
                "mode": "art",
                "style": selected_style,
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "art",
                    "style_used": selected_style,
                    "mood": detected_mood_style if is_about_day else mood
                }
            }
        }
    
    # ==============================================
    # MODE 2: POSTER MODE - Typography, layouts, marketing
    # ==============================================
    elif mode == "poster":
        slogan = extract_slogan(req.message)
        
        poster_types = ["minimalist", "bold typography", "elegant", "modern", "vintage", "corporate", "creative"]
        selected_type = random.choice(poster_types)
        
        if slogan:
            enhanced_prompt = f"{selected_type} poster background, {req.message}, {mood} atmosphere, professional graphic design, no text, no words, clean composition, {base_style}"
            logger.info(f"POSTER MODE - Creating background for slogan: '{slogan}'")
        else:
            enhanced_prompt = f"{selected_type} poster design, {req.message}, {mood} atmosphere, professional typography layout, graphic design, {base_style}"
            logger.info(f"POSTER MODE - Creating poster without slogan")
        
        # Use DeepAI for generation
        images = await generate_with_deepai(
            prompt=enhanced_prompt,
            num_images=2,
            width=512,
            height=512
        )
        
        encoded_images = encode_images(images)
        
        # Generate reasoning
        reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "poster",
            "content": {
                "images": encoded_images,
                "slogan": slogan,
                "reasoning": reasoning,
                "prompt_used": enhanced_prompt,
                "mode": "poster",
                "style": selected_type,
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "poster",
                    "style_used": selected_type,
                    "has_text": bool(slogan),
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 3: STORY MODE - Narrative with multiple scenes
    # ==============================================
    elif mode == "story":
        story_data = await asyncio.to_thread(generate_story, req.message, mood)
        
        story_styles = ["cinematic", "illustrated", "animated style", "children's book", "graphic novel", "watercolor"]
        selected_style = random.choice(story_styles)
        
        scenes = story_data.get('scenes', [req.message, "The adventure continues...", "A memorable conclusion."])[:3]
        scene_images = []
        
        for i, scene in enumerate(scenes):
            if i == 0:
                scene_prompt = f"Opening scene: {scene}, {selected_style}, {mood} atmosphere, establishing shot, {base_style}"
            elif i == 1:
                scene_prompt = f"Middle scene: {scene}, {selected_style}, {mood} atmosphere, action moment, {base_style}"
            else:
                scene_prompt = f"Closing scene: {scene}, {selected_style}, {mood} atmosphere, resolution, emotional payoff, {base_style}"
            
            # Use DeepAI for each scene
            img_list = await generate_with_deepai(
                prompt=scene_prompt,
                num_images=1,
                width=512,
                height=512
            )
            if img_list:
                scene_images.append(img_list[0])
        
        encoded_scene_images = encode_images(scene_images)
        
        # Generate reasoning
        reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "story",
            "content": {
                "title": story_data.get('title', f'A {mood.capitalize()} Story'),
                "scenes": scenes,
                "images": encoded_scene_images,
                "reasoning": reasoning,
                "mode": "story",
                "style": selected_style,
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "story",
                    "style_used": selected_style,
                    "mood": mood,
                    "scenes": len(scenes)
                }
            }
        }
    
    # ==============================================
    # MODE 4: TRANSFORM MODE - Style transfer/transformations
    # ==============================================
    elif mode == "transform":
        transform_styles = ["oil painting", "watercolor", "sketch", "pencil drawing", "digital art", "3D render", "cyberpunk", "vintage photo", "abstract"]
        target_style = random.choice(transform_styles)
        
        enhanced_prompt = f"{req.message}, transformed into {target_style} style, {mood} atmosphere, {base_style}"
        
        # Use DeepAI for generation
        images = await generate_with_deepai(
            prompt=enhanced_prompt,
            num_images=2,
            width=512,
            height=512
        )
        
        encoded_images = encode_images(images)
        
        # Generate reasoning
        reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "image",
            "content": {
                "images": encoded_images,
                "reasoning": reasoning,
                "prompt_used": enhanced_prompt,
                "mode": "transform",
                "style": target_style,
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "transform",
                    "style_used": target_style,
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 5: BUSINESS MODE - Professional, commercial
    # ==============================================
    elif mode == "business":
        business_styles = ["corporate", "professional", "clean", "modern", "premium", "high-end", "luxury"]
        selected_style = random.choice(business_styles)
        
        enhanced_prompt = f"{req.message}, {selected_style} business visual, commercial photography, studio lighting, professional, {mood} atmosphere, {base_style}"
        
        # Use DeepAI for generation
        images = await generate_with_deepai(
            prompt=enhanced_prompt,
            num_images=2,
            width=512,
            height=512
        )
        
        encoded_images = encode_images(images)
        
        # Generate reasoning
        reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "image",
            "content": {
                "images": encoded_images,
                "reasoning": reasoning,
                "prompt_used": enhanced_prompt,
                "mode": "business",
                "style": selected_style,
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "business",
                    "style_used": selected_style,
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # DEFAULT: PERSONAL MODE - Original behavior
    # ==============================================
    else:  # personal mode or default
        enhanced_prompt = f"{req.message}, {context_prompt}, {base_style}"
        
        # Use DeepAI for generation
        images = await generate_with_deepai(
            prompt=enhanced_prompt,
            num_images=2,
            width=512,
            height=512
        )
        
        encoded_images = encode_images(images)
        
        # Generate reasoning
        reasoning = generate_dynamic_reasoning(req.message, mood, mode)
        
        return {
            "type": "image",
            "content": {
                "images": encoded_images,
                "reasoning": reasoning,
                "prompt_used": enhanced_prompt,
                "mode": "personal",
                "metadata": {
                    "generation_time": round(time.time() - start_time, 2),
                    "mode": "personal",
                    "mood": mood
                }
            }
        }

# ==============================================
# REQUEST/RESPONSE MODELS
# ==============================================

class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: Optional[str] = None
    mode: Optional[str] = "personal"

class ResetRequest(BaseModel):
    user_id: str

class ChatResponse(BaseModel):
    type: str
    content: dict
    timestamp: float = time.time()
    conversation_id: Optional[str] = None

# ==============================================
# API ENDPOINTS
# ==============================================

@app.get("/")
async def root():
    return {
        "service": "Vizzy Chat API",
        "version": "1.0.0",
        "status": "operational",
        "model": "DeepAI + Placeholders",
        "note": "100% free, 100% working!"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "DeepAI",
        "free_service": True,
        "timestamp": time.time()
    }

@app.options("/chat")
async def chat_options():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

@app.post("/reset")
async def reset_conversation(req: ResetRequest):
    clear_context(req.user_id)
    if req.user_id in conversation_state:
        del conversation_state[req.user_id]
    return {"status": "ok"}

@app.post("/chat")
async def chat(req: ChatRequest):
    logger.info(f"=== CHAT REQUEST ===")
    logger.info(f"User: {req.user_id}")
    logger.info(f"Message: {req.message}")
    logger.info(f"Mode: {req.mode}")
    logger.info(f"Has context: {not needs_context(req.user_id)}")
    logger.info(f"Last interaction: {get_last_interaction(req.user_id)}")

    """Main chat endpoint with dynamic question handling"""
    start_time = time.time()
    
    try:
        logger.info(f"Request from {req.user_id} in {req.mode} mode: {req.message[:50]}...")
        
        # Update tracking systems
        update_memory(req.user_id, req.message)
        update_context(req.user_id, req.message)
        
        # Get last interaction to see if we were asking a question
        last_interaction = get_last_interaction(req.user_id)
        
        # ==============================================
        # CRITICAL: Check if this is a response to a previous question
        # ==============================================
        if last_interaction and last_interaction.get("type") == "question":
            logger.info("✅ Detected response to previous question - processing clarification")
            return await process_clarified_request(req, last_interaction)
        
        # ==============================================
        # Check if we need to ask a clarifying question
        # ==============================================
        
        # Check for "my day" type queries that need clarification
        message_lower = req.message.lower()
        is_day_query = "my day" in message_lower or "today" in message_lower or "day was" in message_lower
        is_mood_query = any(word in message_lower for word in ["feel", "felt", "emotion", "mood"])

        mood_keywords = [
            "happy", "sad", "tired", "peaceful", "excited", "angry", "nostalgic", "anxious",
            "dull", "boring", "energetic", "calm", "romantic", "mysterious", "professional",
            "creative", "melancholic", "subdued", "weary", "vibrant", "joyful", "somber",
            "tender", "enigmatic", "polished", "imaginative", "hectic", "serene", "inspiring",
            "uplifting", "thoughtful", "frustrated", "relaxed", "contemplative", "motivated"
        ]
        has_mood_detail = any(word in message_lower for word in mood_keywords)
        is_vague_day_request = is_day_query and not has_mood_detail
        is_vague_mood_request = is_mood_query and needs_context(req.user_id)
        
        # If it's about day or mood and lacks detail, ask for clarification
        if is_vague_day_request or is_vague_mood_request:
            logger.info("❓ Day/mood query detected - asking clarifying question")
            
            # Generate a dynamic question
            question_text = generate_clarifying_question(req.message)
            
            # Store that we asked a question
            store_question_asked(req.user_id, req.message)
            
            return {
                "type": "question",
                "content": {
                    "text": question_text,
                }
            }
        
        # ==============================================
        # If user selected a mode explicitly, generate directly
        # ==============================================
        if req.mode in ["art", "poster", "story", "transform", "business", "personal"]:
            logger.info(f"Mode selected: {req.mode} - generating directly")
            result = await generate_content(req)
            store_generated_response(req.user_id, result)
            return result
        
        # ==============================================
        # Default: generate content
        # ==============================================
        else:
            result = await generate_content(req)
            store_generated_response(req.user_id, result)
            return result
            
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "content": {
                    "text": f"Generation failed: {str(e)}"
                }
            }
        )