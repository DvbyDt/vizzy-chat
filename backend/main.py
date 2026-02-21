from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from io import BytesIO
import base64
import logging
import time
import os
import requests
from typing import List, Optional
import asyncio
import random
import re
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

from memory import update_memory, get_user_preferences
from story import generate_story
from context import update_context, get_context_prompt, pending_context

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verify HF token is configured before startup; fail fast if not provided
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
if not HF_API_TOKEN:
    raise RuntimeError("HF_API_TOKEN not configured")

HF_MODEL_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

async def generate_images_hf(prompt: str, num_images: int = 2) -> List[Image.Image]:
    """Generate images via Hugging Face Stable Diffusion XL.
    
    This is the primary fallback when the custom HF Space is unavailable.
    Returns exactly num_images, using placeholders if generation fails.
    Each image is generated at 768x768 with consistent quality settings.
    """
    images = []
    for _ in range(num_images):
        try:
            # Run HTTP request on thread pool to avoid blocking async loop
            response = await asyncio.to_thread(
                requests.post,
                HF_MODEL_URL,
                headers=HF_HEADERS,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "width": 768,
                        "height": 768,
                        "num_inference_steps": 30,
                        "guidance_scale": 7.5
                    }
                },
                timeout=120  # HF can be slow, allow up to 2 minutes
            )
            if response.status_code != 200:
                raise ValueError(response.text)
            images.append(Image.open(BytesIO(response.content)).convert("RGB"))
        except Exception as e:
            logger.warning(f"Generation failed: {e}")
            # Fall back to placeholder instead of breaking user experience
            images.append(_create_placeholder(prompt))
    return images

def _create_placeholder(prompt: str) -> Image.Image:
    """Quick fallback image when HF API fails for a single image.
    
    Creates a simple solid-color image with truncated prompt text.
    This is fast and reliable - used when generate_images_hf hits API errors.
    """
    width, height = 512, 512
    colors = [(52, 152, 219), (155, 89, 182), (52, 73, 94), (243, 156, 18)]
    img = Image.new('RGB', (width, height), color=colors[0])
    try:
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        text = f"{prompt[:30]}..."
        bbox = draw.textbbox((0, 0), text, font=font)
        draw.text(
            ((width - (bbox[2] - bbox[0])) // 2, height // 2),
            text,
            fill='white',
            font=font
        )
    except Exception:
        pass
    return img

app = FastAPI(title="Vizzy Chat API", version="1.0.0")

# Configure CORS to allow requests from frontend development and production URLs
# Required because frontend runs on different origin (Vercel or localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://localhost:5174",  # Alternative Vite ports
        "http://localhost:5175",
        "http://localhost:3000",  # React dev server
        "https://*.vercel.app",   # Any Vercel deployment
        "https://vizzy-chat.vercel.app",  # Specific production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================
# HUGGING FACE IMAGE GENERATION
# ==============================================

# Custom HF Space URL - our own model deployed for consistent performance
# Points to Dvbydt-VizzyAPICHAT which wraps SDXL with custom optimizations
HF_API_URL = "https://Dvbydt-VizzyAPICHAT.hf.space"

async def generate_with_hf(prompt: str, num_images: int = 2) -> List[Image.Image]:
    """Generate images using our custom Hugging Face Space.
    
    Implements exponential backoff retry strategy because HF Spaces can
    become unresponsive during high load. After 3 total attempts, falls back
    to placeholder generation rather than returning an error.
    """
    images = []
    HF_API_URL = "https://Dvbydt-VizzyAPICHAT.hf.space"
    
    # Retry up to 3 times - HF Spaces sometimes need a moment to respond
    for attempt in range(3):
        try:
            logger.info(f"🎨 Attempt {attempt + 1}/3: Generating {num_images} image(s) with HF")
            
            response = requests.post(
                f"{HF_API_URL}/generate",
                json={
                    "prompt": prompt,
                    "num_images": num_images
                },
                timeout=120  # 2 minutes - HF Spaces can be slow to wake up
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    # Decode base64 images returned from the API
                    for img_base64 in data.get("images", []):
                        img_data = base64.b64decode(img_base64)
                        img = Image.open(BytesIO(img_data))
                        # Ensure consistent RGB format for all images
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        images.append(img)
                    logger.info(f"✅ Got {len(images)} images from Hugging Face")
                    return images
                else:
                    logger.error(f"❌ HF error: {data.get('status')}")
            else:
                # Non-200 response, log but continue to retry
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Attempt {attempt + 1} timed out, retrying...")
            # Brief pause before retry to give HF Space time to recover
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(5)
    
    # All retries exhausted - generate decorative placeholders
    # This ensures the frontend always gets valid images, never an error
    logger.warning("⚠️ All HF attempts failed, using placeholders")
    for i in range(num_images):
        img = create_emergency_placeholder(prompt, i)
        images.append(img)
    
    return images

def generate_high_quality_placeholders(prompt: str, num_images: int) -> List[Image.Image]:
    """Generate aesthetically pleasing fallback images with gradient backgrounds.
    
    Used when HF Spaces are completely unavailable. These look much better than
    solid colors and include decorative elements so users don't lose confidence
    in the service. Contains prompt preview text for context.
    """
    images = []
    
    for i in range(num_images):
        width, height = 512, 512
        
        # Create gradient backgrounds that look intentional and polished
        from PIL import ImageColor
        
        # Professional color pairs that evoke different moods
        color_pairs = [
            ('#4158D0', '#C850C0'),  # Purple to Pink
            ('#0093E9', '#80D0C7'),  # Blue to Teal
            ('#08AEEA', '#2AF598'),  # Blue to Green
            ('#FA8BFF', '#2BD2FF'),  # Pink to Blue
            ('#FF9A8B', '#FF6A88'),  # Peach to Pink
        ]
        
        color1, color2 = random.choice(color_pairs)
        
        # Create gradient background
        img = Image.new('RGB', (width, height), color=color1)
        draw = ImageDraw.Draw(img)
        
        # Add some design elements
        for j in range(10):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(50, 150)
            opacity = random.randint(30, 100)
            draw.ellipse([x-size, y-size, x+size, y+size], 
                        fill=color2, outline=None)
        
        # Add text
        try:
            font = ImageFont.load_default()
            
            # Title
            title = "✨ Vizzy AI"
            bbox = draw.textbbox((0, 0), title, font=font)
            title_width = bbox[2] - bbox[0]
            draw.text(((width - title_width) // 2, 50), title, fill='white', font=font)
            
            # Prompt preview
            words = prompt.split()
            line1 = " ".join(words[:4]) if words else "Creative"
            line2 = " ".join(words[4:8]) if len(words) > 4 else "Generation"
            
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            text_width1 = bbox1[2] - bbox1[0]
            draw.text(((width - text_width1) // 2, height//2 - 30), line1, fill='white', font=font)
            
            bbox2 = draw.textbbox((0, 0), line2, font=font)
            text_width2 = bbox2[2] - bbox2[0]
            draw.text(((width - text_width2) // 2, height//2 + 10), line2, fill='white', font=font)
            
            # Small note
            note = "Hugging Face coming soon..."
            bbox = draw.textbbox((0, 0), note, font=font)
            note_width = bbox[2] - bbox[0]
            draw.text(((width - note_width) // 2, height - 50), note, fill='white', font=font)
            
        except:
            pass
        
        images.append(img)
    
    return images

def create_emergency_placeholder(prompt: str, index: int) -> Image.Image:
    """Last-resort fallback image when all generation attempts fail.
    
    Creates a simple colored image with prompt text. Used after all retries
    and placeholder generation attempts fail. Ensures frontend always gets
    something valid instead of an error, maintaining UX continuity.
    """
    width, height = 512, 512
    
    # Vary colors by index to provide visual diversity across multiple images
    colors = [
        (52, 152, 219),  # Blue
        (155, 89, 182),  # Purple
        (52, 73, 94),    # Dark Blue
        (243, 156, 18),  # Orange
        (231, 76, 60),   # Red
        (46, 204, 113),  # Green
    ]
    
    color = colors[index % len(colors)]
    
    # Create image
    img = Image.new('RGB', (width, height), color=color)
    draw = ImageDraw.Draw(img)
    
    # Add some circles for visual interest
    for i in range(3):
        x = random.randint(100, width-100)
        y = random.randint(100, height-100)
        r = random.randint(30, 60)
        circle_color = tuple(min(c + 30, 255) for c in color)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=circle_color, outline=None)
    
    # Add text
    try:
        font = ImageFont.load_default()
        
        # Format prompt text
        words = prompt.split()
        line1 = " ".join(words[:4]) if words else "Vizzy AI"
        line2 = " ".join(words[4:8]) if len(words) > 4 else "Image Generation"
        
        # Draw lines
        bbox1 = draw.textbbox((0, 0), line1, font=font)
        text_width1 = bbox1[2] - bbox1[0]
        draw.text(((width - text_width1) // 2, height//2 - 30), line1, fill='white', font=font)
        
        bbox2 = draw.textbbox((0, 0), line2, font=font)
        text_width2 = bbox2[2] - bbox2[0]
        draw.text(((width - text_width2) // 2, height//2 + 10), line2, fill='white', font=font)
        
        # Add small logo
        logo = "✨ vizzy.ai"
        bbox_logo = draw.textbbox((0, 0), logo, font=font)
        logo_width = bbox_logo[2] - bbox_logo[0]
        draw.text(((width - logo_width) // 2, height - 40), logo, fill='white', font=font)
        
    except Exception as e:
        logger.error(f"Text drawing failed: {e}")
    
    return img

# ==============================================
# CONVERSATION STATE MANAGEMENT
# ==============================================

# In-memory state to track conversation flow for each user.
# Used to detect if the user is answering a clarifying question or starting fresh.
# In production, this should be moved to a persistent store (Redis, database).
conversation_state = {}

def get_last_interaction(user_id):
    """Retrieve the previous bot message (question or response).
    
    Used to determine if the user's current message is a response to a
    clarifying question versus a new request. If no state exists, returns None.
    """
    if user_id in conversation_state and conversation_state[user_id].get("last_bot_message"):
        return conversation_state[user_id]["last_bot_message"]
    return None

def store_question_asked(user_id, original_query):
    """Record that we asked the user a clarifying question.
    
    Stores the original imprecise query so we can combine it with the user's
    clarification later. Critical for understanding vague requests like "my day."
    """
    if user_id not in conversation_state:
        conversation_state[user_id] = {}
    conversation_state[user_id]["last_bot_message"] = {
        "type": "question",
        "original_query": original_query,
        "asked_at": time.time()
    }

def store_generated_response(user_id, response):
    """Save the response we generated.
    
    Overwrites previous state so we don't re-ask questions for queries
    we've already generated images for.
    """
    if user_id not in conversation_state:
        conversation_state[user_id] = {}
    conversation_state[user_id]["last_bot_message"] = response

def update_context_with_mood(user_id, mood):
    """Store detected mood to influence image generation style.
    
    Mood is extracted from clarifying questions and applied across all
    subsequent generations until the user updates it explicitly.
    """
    if user_id not in pending_context:
        pending_context[user_id] = {}
    pending_context[user_id]["mood"] = mood
    logger.info(f"Updated mood for {user_id}: {mood}")

def generate_conversational_suggestions(mood):
    """Provide quick-response options based on detected mood.
    
    These are fallback suggestions when mood detection succeeds but we don't
    have more specific context. Helps users move toward generation quickly.
    """
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
    """Extract slogan text from user message using multiple strategies.
    
    Tries quoted text first, then checks for explicit "slogan should be" patterns.
    Returns None if no slogan detected. Used in poster mode to overlay text.
    """
    # Try double quotes first (most common for intentional text)
    quoted = re.findall(r'"([^"]*)"', message)
    if quoted:
        return quoted[0]
    
    # Fall back to single quotes
    quoted = re.findall(r"'([^']*)'", message)
    if quoted:
        return quoted[0]
    
    # Check for explicit intent pattern
    if "slogan should be" in message.lower():
        parts = message.lower().split("slogan should be")
        if len(parts) > 1:
            slogan = parts[1].strip()
            # Clean up trailing punctuation
            slogan = re.sub(r'[.!?]$', '', slogan)
            return slogan
    
    return None

def encode_images(images):
    """Convert PIL images to base64 strings for JSON transmission.
    
    Applies size optimization (max 1024px) to reduce bandwidth before
    base64 encoding for frontend display. Silently appends None on encode errors
    rather than breaking the response.
    """
    encoded = []
    for img in images:
        try:
            # Resize if needed to keep payload small for network transmission
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # PNG with optimization for web delivery
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True)
            encoded.append(base64.b64encode(buf.getvalue()).decode())
        except Exception as e:
            logger.error(f"Image encoding failed: {e}")
            # Append None so frontend can handle missing images gracefully
            encoded.append(None)
    return encoded

# ==============================================
# DYNAMIC SUGGESTION GENERATOR
# ==============================================

def generate_dynamic_suggestions(user_message):
    """Create personalized suggestions based on mood keywords in the user's message.
    
    Scans for mood-related words and returns 3-4 relevant style suggestions.
    If no mood keywords detected, falls back to random style/color suggestions.
    """
    message_lower = user_message.lower()
    suggestions = []
    
    # Map mood keywords to specific visual suggestions
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
    """Generate contextual clarifying question to get mood/tone details.
    
    When users say vague things like "visualize my day," we need mood context
    (was it stressful? calm? exciting?) to generate appropriate images.
    This function picks question templates based on detected keywords
    in the user's original message for better conversion rates.
    """
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
    """Craft explanatory text about why we generated specific images.
    
    Uses mode-specific templates to explain the artistic direction and mood,
    tailored to the specific user request. Makes responses feel more personalized.
    """
    message_preview = message[:30] + "..." if len(message) > 30 else message
    
    # Different explanations based on generation mode (art, poster, story, etc)
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
    """Enhance vague original request with user's clarification and regenerate.
    
    When a user answers "tell me about your day," we combine:
    1. The original generic request
    2. The user's mood/tone from their clarification
    
Then generate images with both pieces of context for better results.
    """
    original_query = last_question.get("original_query", req.message)
    clarification = req.message
    
    logger.info(f"Processing clarification - Original: '{original_query}', Clarification: '{clarification}'")
    
    message_lower = clarification.lower()
    
    # Extract mood from common descriptors in the clarification
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
    
    # Reconstruct request with mood context added
    enhanced_message = f"{original_query}. The mood is {detected_mood_desc}."
    
    # Create new request with enhanced context for generation
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
    """Generate content (images/stories) based on user request and selected mode.
    
    Five distinct modes handle different use cases:
    - art: Creative freeform generation
    - poster: Background + overlay-ready
    - story: Sequential multi-scene narratives
    - transform: Style transfer approach
    - business: Professional/corporate visuals
    - personal: Default mode with user context
    """
    start_time = time.time()
    
    # Retrieve user's previous mood context if available
    user_ctx = pending_context.get(req.user_id, {})
    mood = user_ctx.get("mood", "vibrant")
    context_prompt = get_context_prompt(req.user_id)
    
    mode = req.mode if hasattr(req, 'mode') else "personal"
    logger.info(f"Mode: {mode}, Message: {req.message}")
    
    preferences = get_user_preferences(req.user_id)
    
    # Core style directives applied to most generation modes
    base_style = "artistic, creative, atmospheric, emotional"
    negative_prompt = "blurry, low quality, distorted, ugly, text, watermark"
    
    # Incorporate user's learned style preferences if they exist
    if preferences.get('favorite_style'):
        base_style += f", {preferences['favorite_style']}"
    
    # ==============================================
    # MODE 1: ART MODE
    # ==============================================
    if mode == "art":
        # Detect special case: user describing their day
        message_lower = req.message.lower()
        is_about_day = "my day" in message_lower or "today" in message_lower
        
        # Randomize artistic movement for variety across requests
        art_styles = ["expressionist", "impressionist", "abstract", "surreal"]
        selected_style = random.choice(art_styles)
        
        # Generic day requests get mood added; specific requests use exact input
        if is_about_day:
            enhanced_prompt = f"Artistic interpretation of a day, {mood} mood, {selected_style} style"
        else:
            enhanced_prompt = f"{req.message}, {selected_style} style, {base_style}"
        
        # Generate using primary HF endpoint with fallback built-in
        images = await generate_images_hf(enhanced_prompt, 2)
        encoded_images = encode_images(images)
        
        # Create narrative explanation for the generated images
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
        # Extract explicit slogan text if user provided it (in quotes or after "slogan should be")
        slogan = extract_slogan(req.message)
        
        # Vary poster aesthetics to keep designs fresh
        poster_types = ["minimalist", "bold typography", "elegant", "modern"]
        selected_type = random.choice(poster_types)
        
        # Explicitly exclude text from generation to avoid overlapping with user's slogan
        enhanced_prompt = f"{selected_type} poster background, {req.message}, {mood} atmosphere, no text"
        
        # Generate background images that will accept overlaid text
        images = await generate_images_hf(enhanced_prompt, 2)
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
        # Generate story structure (chapters/scenes) from the user's prompt
        story_data = await asyncio.to_thread(generate_story, req.message, mood)
        
        # Pick a visual style that will tie all story scenes together
        story_styles = ["cinematic", "illustrated", "children's book"]
        selected_style = random.choice(story_styles)
        
        # Extract up to 3 scenes to visualize from the generated story
        scenes = story_data.get('scenes', [req.message, "The adventure continues...", "A memorable conclusion."])[:3]
        scene_images = []
        
        # Generate one image per scene to create a visual narrative sequence
        for i, scene in enumerate(scenes):
            scene_prompt = f"{scene}, {selected_style}, {mood} atmosphere"
            # Generate single image per scene (don't need multiple per scene for story mode)
            img_list = await generate_images_hf(scene_prompt, 1)
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
        # User describes something they want reimagined in a different style
        transform_styles = ["oil painting", "watercolor", "sketch", "cyberpunk"]
        target_style = random.choice(transform_styles)
        
        # Instruct model to transform the user's concept into chosen artistic style
        enhanced_prompt = f"{req.message}, transformed into {target_style} style, {mood} atmosphere"
        
        # Generate transformed versions of the concept
        images = await generate_images_hf(enhanced_prompt, 2)
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
        # Generate professional/corporate-appropriate visuals
        business_styles = ["corporate", "professional", "clean", "modern"]
        selected_style = random.choice(business_styles)
        
        # Emphasize professional aesthetics and cleaned-up visuals
        enhanced_prompt = f"{req.message}, {selected_style} business visual, professional, {mood} atmosphere"
        
        # Generate business-appropriate images
        images = await generate_images_hf(enhanced_prompt, 2)
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
        # Default mode when no specific mode is requested.
        # Combines user input with stored context (history, preferences) for personalized results
        enhanced_prompt = f"{req.message}, {context_prompt}, {base_style}"
        
        # Generate primary plus fallback images
        images = await generate_images_hf(enhanced_prompt, 2)
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
    """Input for image/story generation requests.
    
    Fields:
    - user_id: Unique identifier for conversation continuity and context
    - message: User's prompt or request
    - conversation_id: Optional grouping ID for multi-turn conversations
    - mode: Generation mode (art/poster/story/transform/business/personal)
    """
    user_id: str
    message: str
    conversation_id: Optional[str] = None
    mode: Optional[str] = "personal"

class ResetRequest(BaseModel):
    """Request to clear user's conversation history and stored context."""
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
    """Service info endpoint for health checks and version verification."""
    return {
        "service": "Vizzy Chat API",
        "version": "1.0.0",
        "status": "operational",
        "model": "Stable Diffusion XL via Hugging Face",
        "hf_url": HF_API_URL
    }

@app.get("/health")
async def health_check():
    """Health check endpoint. Returns status and API configuration."""
    return {
        "status": "healthy",
        "hf_configured": HF_API_URL != "https://Dvbydt-vizzy-chat-api.hf.space/generate",
        "timestamp": time.time()
    }

@app.options("/chat")
async def chat_options():
    """CORS preflight handler for OPTIONS requests."""
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
    """Clear all conversation context and state for a user.
    
    Called when user starts a new conversation or wants to clear memory.
    Removes stored mood, context, and conversation history.
    """
    clear_context(req.user_id)
    if req.user_id in conversation_state:
        del conversation_state[req.user_id]
    return {"status": "ok"}

@app.post("/chat")
async def chat(req: ChatRequest):
    """Main chat endpoint. Handles conversation flow and mode routing.
    
    Decision tree:
    1. Check if user is answering a previous clarifying question
    2. Check if request is too vague (e.g., "my day" without mood details)
    3. Route to appropriate generation mode
    """
    logger.info(f"=== CHAT REQUEST ===")
    logger.info(f"User: {req.user_id}")
    logger.info(f"Message: {req.message}")
    logger.info(f"Mode: {req.mode}")
    
    start_time = time.time()
    
    try:
        # Store the exchange for memory/context systems
        update_memory(req.user_id, req.message)
        update_context(req.user_id, req.message)
        
        # Check if this is a response to a previous clarifying question
        last_interaction = get_last_interaction(req.user_id)
        
        if last_interaction and last_interaction.get("type") == "question":
            logger.info("✅ Detected response to previous question")
            return await process_clarified_request(req, last_interaction)
        
        # Analyze current message for vagueness
        message_lower = req.message.lower()
        is_day_query = "my day" in message_lower or "today" in message_lower
        is_mood_query = any(word in message_lower for word in ["feel", "emotion", "mood"])
        
        # Check if user provided mood context
        mood_keywords = ["happy", "sad", "dull", "boring", "energetic", "calm"]
        has_mood_detail = any(word in message_lower for word in mood_keywords)
        is_vague_day_request = is_day_query and not has_mood_detail
        
        # Ask for clarification before generating for open-ended "day" requests
        if is_vague_day_request:
            logger.info("❓ Day query detected - asking clarifying question")
            question_text = generate_clarifying_question(req.message)
            store_question_asked(req.user_id, req.message)
            return {
                "type": "question",
                "content": {"text": question_text}
            }
        
        # User specified a mode explicitly - generate directly
        if req.mode in ["art", "poster", "story", "transform", "business", "personal"]:
            logger.info(f"Mode selected: {req.mode} - generating directly")
            result = await generate_content(req)
            store_generated_response(req.user_id, result)
            return result
        
        # Default to personal mode if no specific mode requested
        else:
            result = await generate_content(req)
            store_generated_response(req.user_id, result)
            return result
            
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        # Return graceful error response instead of crashing
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "content": {"text": f"Generation failed: {str(e)}"}
            }
        )

@app.get("/test-deepai")
async def test_deepai():
    """Debug endpoint to test alternative image generation services.
    
    Useful for checking fallback API availability when primary HF service
    is down or overloaded. Should be removed or restricted in production.
    """
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