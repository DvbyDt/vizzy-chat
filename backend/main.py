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
# MULTI-API IMAGE GENERATION (FAST & RELIABLE)
# ==============================================

# List of fast, free APIs to try
# List of fast, free APIs to try
FAST_APIS = [
    {
        "name": "DeepAI",
        "url": "https://api.deepai.org/api/text-to-image",
        "headers": {'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'},
        "type": "post",
        "data": "text",
        "timeout": 15
    },
    {
        "name": "Pollinations",
        "url": "https://image.pollinations.ai/prompt/{prompt}?width=512&height=512&nologo=true&model=flux",
        "type": "get",
        "timeout": 10
    },
    {
        "name": "Stable Diffusion API",
        "url": "https://stablediffusionapi.com/api/v3/text2img",
        "type": "post",
        "json": {
            "key": "",  # Free tier doesn't need key
            "prompt": "{prompt}",
            "width": "512",
            "height": "512",
            "samples": "1"
        },
        "timeout": 15
    }
]

async def try_api(api_config, prompt):
    """Try a single API and return image if successful"""
    try:
        start_time = time.time()
        logger.info(f"🔄 Trying {api_config['name']}...")
        
        if api_config["type"] == "get":
            # GET request
            url = api_config["url"].replace("{prompt}", prompt.replace(' ', '%20'))
            response = requests.get(url, timeout=api_config.get("timeout", 15))
            
            if response.status_code == 200:
                # Check if response is an image
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    img = Image.open(BytesIO(response.content))
                    elapsed = time.time() - start_time
                    logger.info(f"✅ {api_config['name']} succeeded in {elapsed:.2f}s")
                    return img
                else:
                    logger.warning(f"⚠️ {api_config['name']} returned non-image content: {content_type}")
            else:
                logger.warning(f"⚠️ {api_config['name']} returned status {response.status_code}")
                
        elif api_config["type"] == "post":
            # POST request
            headers = api_config.get("headers", {})
            json_data = api_config.get("json", {})
            json_data["prompt"] = json_data.get("prompt", "{prompt}").replace("{prompt}", prompt)
            
            response = requests.post(
                api_config["url"],
                json=json_data,
                headers=headers,
                timeout=api_config.get("timeout", 15)
            )
            
            if response.status_code == 200:
                try:
                    # Try to get image URL from response
                    resp_json = response.json()
                    if "url" in resp_json:
                        img_response = requests.get(resp_json["url"], timeout=10)
                        if img_response.status_code == 200:
                            img = Image.open(BytesIO(img_response.content))
                            elapsed = time.time() - start_time
                            logger.info(f"✅ {api_config['name']} succeeded in {elapsed:.2f}s")
                            return img
                    elif "image" in resp_json:
                        # Handle base64 image response
                        img_data = base64.b64decode(resp_json["image"])
                        img = Image.open(BytesIO(img_data))
                        elapsed = time.time() - start_time
                        logger.info(f"✅ {api_config['name']} succeeded in {elapsed:.2f}s")
                        return img
                except Exception as parse_err:
                    logger.warning(f"⚠️ {api_config['name']} response parsing failed: {str(parse_err)}")
            else:
                logger.warning(f"⚠️ {api_config['name']} returned status {response.status_code}")
            
    except Exception as e:
        logger.warning(f"❌ {api_config['name']} failed: {str(e)}")
        return None
    
    return None


async def generate_image_fast(prompt: str) -> Image.Image:
    """
    Try multiple APIs in sequence, return first successful result
    Usually returns in 2-5 seconds!
    """
    # Try each API in order of speed/reliability
    for api in FAST_APIS:
        result = await try_api(api, prompt)
        if result is not None:
            return result
    
    # If all APIs fail, create a styled placeholder
    logger.warning("⚠️ All APIs failed, creating placeholder")
    return create_styled_placeholder(prompt)

def create_styled_placeholder(prompt: str) -> Image.Image:
    """Create a nice-looking placeholder with the prompt text - RETURNS REAL IMAGE"""
    width, height = 512, 512
    
    # Create a gradient background
    img = Image.new('RGB', (width, height), color='#2b2b2b')
    draw = ImageDraw.Draw(img)
    
    # Add some colored circles for visual interest
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9']
    for i in range(5):
        x = random.randint(50, width-50)
        y = random.randint(50, height-50)
        r = random.randint(40, 80)
        color = random.choice(colors)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=color, outline=None)
    
    # Try to load a font
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
                font = ImageFont.truetype(path, 24)
                break
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw "AI Generated" text
    try:
        text = "✨ AI Generated ✨"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height//2 - 40), text, fill='white', font=font)
        
        # Draw prompt preview
        words = prompt.split()
        preview = " ".join(words[:4]) + "..." if len(words) > 4 else prompt
        bbox = draw.textbbox((0, 0), preview, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height//2 + 20), preview, fill='white', font=font)
        
        # Draw small note
        note = "(API temporarily unavailable)"
        small_font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), note, font=small_font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height - 50), note, fill='white', font=small_font)
    except:
        pass
    
    return img

async def generate_images_fast(prompt: str, num_images: int = 2) -> List[Image.Image]:
    """Generate multiple images in parallel"""
    tasks = [generate_image_fast(f"{prompt} (variation {i+1})") for i in range(num_images)]
    images = await asyncio.gather(*tasks)
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
            slogan = re.sub(r'[.!?]$', '', slogan)
            return slogan
    
    return None

def encode_images(images):
    """Encode PIL images to base64 with optimization"""
    encoded = []
    for img in images:
        try:
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buf = BytesIO()
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
    
    mood_keywords = {
        "dull": ["Add vibrant colors", "Increase contrast", "Make it more energetic"],
        "boring": ["Make it more dynamic", "Add interesting elements", "Create visual tension"],
        "tired": ["Soften the palette", "Add warm tones", "Create calming composition"],
        "happy": ["Amplify the brightness", "Add playful elements", "Use cheerful colors"],
        "sad": ["Deepen the blues", "Add melancholic tones", "Use soft, diffused light"],
        "energetic": ["Add motion blur", "Use dynamic angles", "Bold contrasting colors"],
        "peaceful": ["Soft gradients", "Calm color palette", "Balanced composition"],
        "romantic": ["Warm golden tones", "Soft focus effect", "Dreamy atmosphere"],
        "mysterious": ["Deep shadows", "Ethereal glow", "Hidden elements"],
        "professional": ["Clean lines", "Minimalist design", "Corporate colors"],
        "creative": ["Abstract elements", "Artistic flair", "Unconventional composition"]
    }
    
    style_suggestions = [
        "Try watercolor effect", "Oil painting style", "Sketch-like quality",
        "Digital art style", "Cinematic lighting", "Vintage feel", "Minimalist style"
    ]
    
    color_suggestions = [
        "Use warmer tones", "Try cooler palette", "Add vibrant colors",
        "Make it monochromatic", "Add pastel shades", "Deepen the shadows"
    ]
    
    # Find matching mood keywords
    found_moods = []
    for mood, mood_suggestions in mood_keywords.items():
        if mood in message_lower:
            found_moods.extend(mood_suggestions)
    
    if found_moods:
        unique_mood_suggestions = list(dict.fromkeys(found_moods))
        suggestions.extend(unique_mood_suggestions[:2])
    
    if len(suggestions) < 3:
        suggestions.append(random.choice(style_suggestions))
    if len(suggestions) < 4:
        suggestions.append(random.choice(color_suggestions))
    
    suggestions = list(dict.fromkeys(suggestions))[:4]
    random.shuffle(suggestions)
    
    return suggestions

# ==============================================
# DYNAMIC CLARIFYING QUESTION GENERATOR
# ==============================================

def generate_clarifying_question(user_message):
    """Generate a dynamic clarifying question based on what the user said"""
    message_lower = user_message.lower()
    
    questions = {
        "day": [
            "I'd love to visualize your day! Could you tell me more about how it felt?",
            "What was the predominant feeling during your day?",
            "How would you describe the energy of your day?"
        ],
        "feeling": [
            "What emotions would you like me to capture in this artwork?",
            "Tell me more about what you're feeling - that will help me create something meaningful.",
            "What emotional tone should I emphasize?"
        ],
        "default": [
            "To create something personal, could you tell me more about the mood you want to express?",
            "What feeling should this artwork capture?",
            "Let's make something special! Tell me more about the feeling you want to capture."
        ]
    }
    
    if "day" in message_lower or "today" in message_lower:
        context = "day"
    elif any(word in message_lower for word in ["feel", "feeling", "emotion", "mood"]):
        context = "feeling"
    else:
        context = "default"
    
    return random.choice(questions[context])

# ==============================================
# DYNAMIC REASONING GENERATOR
# ==============================================

def generate_dynamic_reasoning(message, mood, mode):
    """Generate different reasoning based on the actual input"""
    message_preview = message[:30] + "..." if len(message) > 30 else message
    
    mode_templates = {
        "art": [
            f"As an artist, I've interpreted '{message_preview}' through a {mood} lens",
            f"Your vision of '{message_preview}' inspired these {mood} artistic interpretations",
            f"I've translated '{message_preview}' into {mood} visual poetry"
        ],
        "poster": [
            f"For this poster, I've designed a {mood} background that complements your message",
            f"The composition uses {mood} tones to create visual impact",
            f"This {mood} design provides the perfect canvas for your text"
        ],
        "story": [
            f"Your story about '{message_preview}' unfolds in three {mood} chapters",
            f"I've crafted a {mood} narrative arc based on your vision",
            f"Each scene builds on the {mood} atmosphere to tell your tale"
        ],
        "personal": [
            f"I've interpreted your request through a {mood} lens, focusing on '{message_preview}'",
            f"Drawing from '{message_preview}', I've emphasized {mood} elements",
            f"The {mood} atmosphere you described guided my creative direction"
        ]
    }
    
    templates = mode_templates.get(mode, mode_templates["personal"])
    base_reasoning = random.choice(templates)
    
    insights = [
        "Notice how the lighting creates depth and atmosphere.",
        "The composition guides your eye through the scene.",
        "The color harmony reinforces the emotional tone.",
        "The contrast creates visual interest and drama."
    ]
    
    return f"{base_reasoning}. {random.choice(insights)}"

# ==============================================
# CLARIFIED REQUEST PROCESSOR
# ==============================================

async def process_clarified_request(req, last_question):
    """Process a response to a clarifying question"""
    original_query = last_question.get("original_query", req.message)
    clarification = req.message
    
    logger.info(f"Processing clarification - Original: '{original_query}', Clarification: '{clarification}'")
    
    message_lower = clarification.lower()
    
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
        "motivation": "needing motivation"
    }
    
    detected_mood_desc = "thoughtful and reflective"
    simple_mood = "thoughtful"
    
    for keyword, desc in mood_map.items():
        if keyword in message_lower:
            detected_mood_desc = desc
            simple_mood = keyword
            break
    
    update_context_with_mood(req.user_id, simple_mood)
    
    enhanced_message = f"{original_query}. The mood is {detected_mood_desc}."
    
    enhanced_req = ChatRequest(
        user_id=req.user_id,
        message=enhanced_message,
        conversation_id=req.conversation_id,
        mode=req.mode if hasattr(req, 'mode') else "art"
    )
    
    result = await generate_content(enhanced_req)
    store_generated_response(req.user_id, result)
    return result

# ==============================================
# MODE-SPECIFIC GENERATION
# ==============================================

async def generate_content(req):
    """Generate images/stories based on the request"""
    start_time = time.time()
    
    user_ctx = pending_context.get(req.user_id, {})
    mood = user_ctx.get("mood", "vibrant")
    context_prompt = get_context_prompt(req.user_id)
    
    mode = req.mode if hasattr(req, 'mode') else "personal"
    logger.info(f"Mode: {mode}, Message: {req.message}")
    
    preferences = get_user_preferences(req.user_id)
    
    base_style = "artistic, creative, atmospheric, emotional"
    negative_prompt = "blurry, low quality, distorted, ugly, text, watermark"
    
    if preferences.get('favorite_style'):
        base_style += f", {preferences['favorite_style']}"
    
    # ==============================================
    # MODE 1: ART MODE
    # ==============================================
    if mode == "art":
        message_lower = req.message.lower()
        is_about_day = "my day" in message_lower or "today" in message_lower
        
        art_styles = ["expressionist", "impressionist", "abstract", "surreal"]
        selected_style = random.choice(art_styles)
        
        if is_about_day:
            enhanced_prompt = f"Artistic interpretation of a day, {mood} mood, {selected_style} style"
        else:
            enhanced_prompt = f"{req.message}, {selected_style} style, {base_style}"
        
        images = await generate_images_fast(enhanced_prompt, 2)
        encoded_images = encode_images(images)
        
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
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 2: POSTER MODE
    # ==============================================
    elif mode == "poster":
        slogan = extract_slogan(req.message)
        
        poster_types = ["minimalist", "bold typography", "elegant", "modern"]
        selected_type = random.choice(poster_types)
        
        enhanced_prompt = f"{selected_type} poster background, {req.message}, {mood} atmosphere, no text"
        
        images = await generate_images_fast(enhanced_prompt, 2)
        encoded_images = encode_images(images)
        
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
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 3: STORY MODE
    # ==============================================
    elif mode == "story":
        story_data = await asyncio.to_thread(generate_story, req.message, mood)
        
        story_styles = ["cinematic", "illustrated", "children's book"]
        selected_style = random.choice(story_styles)
        
        scenes = story_data.get('scenes', [req.message, "The adventure continues...", "A memorable conclusion."])[:3]
        scene_images = []
        
        for i, scene in enumerate(scenes):
            scene_prompt = f"{scene}, {selected_style}, {mood} atmosphere"
            img_list = await generate_images_fast(scene_prompt, 1)
            if img_list:
                scene_images.append(img_list[0])
        
        encoded_scene_images = encode_images(scene_images)
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
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 4: TRANSFORM MODE
    # ==============================================
    elif mode == "transform":
        transform_styles = ["oil painting", "watercolor", "sketch", "cyberpunk"]
        target_style = random.choice(transform_styles)
        
        enhanced_prompt = f"{req.message}, transformed into {target_style} style, {mood} atmosphere"
        
        images = await generate_images_fast(enhanced_prompt, 2)
        encoded_images = encode_images(images)
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
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # MODE 5: BUSINESS MODE
    # ==============================================
    elif mode == "business":
        business_styles = ["corporate", "professional", "clean", "modern"]
        selected_style = random.choice(business_styles)
        
        enhanced_prompt = f"{req.message}, {selected_style} business visual, professional, {mood} atmosphere"
        
        images = await generate_images_fast(enhanced_prompt, 2)
        encoded_images = encode_images(images)
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
                    "mood": mood
                }
            }
        }
    
    # ==============================================
    # DEFAULT: PERSONAL MODE
    # ==============================================
    else:
        enhanced_prompt = f"{req.message}, {context_prompt}, {base_style}"
        
        images = await generate_images_fast(enhanced_prompt, 2)
        encoded_images = encode_images(images)
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
        "model": "Multi-API (Fast & Reliable)",
        "note": "Uses multiple free APIs with fallback"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "apis_available": len(FAST_APIS),
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
    
    start_time = time.time()
    
    try:
        update_memory(req.user_id, req.message)
        update_context(req.user_id, req.message)
        
        last_interaction = get_last_interaction(req.user_id)
        
        if last_interaction and last_interaction.get("type") == "question":
            logger.info("✅ Detected response to previous question")
            return await process_clarified_request(req, last_interaction)
        
        message_lower = req.message.lower()
        is_day_query = "my day" in message_lower or "today" in message_lower
        is_mood_query = any(word in message_lower for word in ["feel", "emotion", "mood"])
        
        mood_keywords = ["happy", "sad", "dull", "boring", "energetic", "calm"]
        has_mood_detail = any(word in message_lower for word in mood_keywords)
        is_vague_day_request = is_day_query and not has_mood_detail
        
        if is_vague_day_request:
            logger.info("❓ Day query detected - asking clarifying question")
            question_text = generate_clarifying_question(req.message)
            store_question_asked(req.user_id, req.message)
            return {
                "type": "question",
                "content": {"text": question_text}
            }
        
        if req.mode in ["art", "poster", "story", "transform", "business", "personal"]:
            logger.info(f"Mode selected: {req.mode} - generating directly")
            result = await generate_content(req)
            store_generated_response(req.user_id, result)
            return result
        
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
                "content": {"text": f"Generation failed: {str(e)}"}
            }
        )
    
@app.get("/test-deepai")
async def test_deepai():
    """Test DeepAI API directly"""
    try:
        response = requests.post(
            "https://api.deepai.org/api/text-to-image",
            data={'text': 'a beautiful sunset'},
            headers={'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'},
            timeout=10
        )
        return {
            "status": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text[:200]
        }
    except Exception as e:
        return {"error": str(e)}