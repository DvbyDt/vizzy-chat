# 🏗️ Vizzy Chat - System Architecture

**Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready

## System Overview

Vizzy Chat is a full-stack AI creative generation platform with intelligent conversation flow and multi-mode content generation. The system is designed for reliability, with built-in fallback mechanisms and graceful degradation.

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER BROWSER                               │
│                   (React 19 SPA)                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS REST API
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    VERCEL GLOBAL EDGE                           │
│              (Frontend CDN & Static Assets)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ API Routes
                            │ POST /chat
                            │ POST /reset
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              BACKEND SERVER (Render/HF Spaces)                  │
│                    (FastAPI 0.104.1)                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Request Handler                         │  │
│  │  • Request validation (Pydantic models)                 │  │
│  │  • User session management                              │  │
│  │  • CORS & security middleware                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Conversation State Manager                       │  │
│  │  • In-memory conversation_state dict                    │  │
│  │  • Last interaction tracking                            │  │
│  │  • Clarifying question detection                        │  │
│  │  • User mood context (pending_context)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Request Processing Pipeline                      │  │
│  │                                                          │  │
│  │  1. Vague Query Detection                              │  │
│  │     └─ Detect "my day", "today" queries               │  │
│  │                                                          │  │
│  │  2. Clarifying Question Generation                     │  │
│  │     └─ Ask about mood/emotion if needed               │  │
│  │                                                          │  │
│  │  3. Mode-Specific Processing                           │  │
│  │     ├─ Art: Random style selection                     │  │
│  │     ├─ Poster: Slogan extraction                       │  │
│  │     ├─ Story: Story structure generation              │  │
│  │     ├─ Transform: Style specification                  │  │
│  │     ├─ Business: Professional aesthetic                │  │
│  │     └─ Personal: User context integration              │  │
│  │                                                          │  │
│  │  4. Prompt Engineering                                  │  │
│  │     └─ Combine user input + mood + style               │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Image Generation Engine                         │  │
│  │                                                          │  │
│  │  Primary: Stable Diffusion XL (768x768)               │  │
│  │  ├─ Provider: Hugging Face API endpoint                │  │
│  │  ├─ Inference steps: 30                                │  │
│  │  ├─ Guidance scale: 7.5                                │  │
│  │  ├─ Retry logic: 3 attempts with 5s backoff            │  │
│  │  └─ Timeout: 120 seconds per request                   │  │
│  │                                                          │  │
│  │  Fallback 1: Custom HF Space                           │  │
│  │  └─ URL: https://Dvbydt-VizzyAPICHAT.hf.space         │  │
│  │                                                          │  │
│  │  Fallback 2: High-quality placeholders                 │  │
│  │  └─ Gradient backgrounds with decorative elements      │  │
│  │                                                          │  │
│  │  Fallback 3: Emergency placeholders                    │  │
│  │  └─ Solid color + prompt text (last resort)            │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Image Optimization & Encoding                   │  │
│  │  • Resize if > 1024px (LANCZOS)                        │  │
│  │  • PNG compression optimization                         │  │
│  │  • Base64 encoding for JSON transmission                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
                      JSON Response
                    (base64 images
                 + reasoning + metadata)
```

## Data Flow Diagrams

### Flow 1: Vague Query Resolution

```
User Input: "Draw my day"
    │
    ▼
Vague Query Detector
├─ Detect "my day" / "today" keywords
├─ Check if mood/emotion details provided
└─ If vague → STOP, ask clarifying question
    │
    ▼
Generate Clarifying Question
├─ Template: "Could you tell me more about how your day was?"
├─ Store original query in conversation_state
└─ Return question to frontend
    │
    ▼ [User responds with mood]
    │
User Input: "It was dull and I needed motivation"
    │
    ▼
Extract Mood Keywords
├─ Scan for: "dull", "tired", "happy", "energetic", etc.
├─ Map to mood description: "dull and unmotivated"
└─ Store mood in pending_context
    │
    ▼
Enhance Original Query
├─ Combine: "Draw my day. The mood is dull and unmotivated."
├─ Retrieve mood preference for style
└─ Generate artistic prompt

Result: Context-aware image generation based on clarification
```

### Flow 2: Multi-Scene Story Generation

```
User Input: "Tell a story about an adventure in a magical forest"
    │
    ▼
Story Mode Detected
├─ Message contains keywords suggesting narrative
└─ Route to story generation pipeline
    │
    ▼
Generate Story Structure (via generate_story module)
├─ Use language model to create 3 scenes
├─ Extract: scene descriptions, plot progression
└─ Store scenes as list of descriptions
    │
    ▼
Generate Scene Visuals
├─ For each of 3 scenes:
│  ├─ Create prompt: "scene_text + story_style + mood"
│  ├─ Call generate_images_hf(prompt, 1)
│  ├─ Encode result to base64
│  └─ Add to output array
    │
    ▼
Combine Into Narrative
├─ Title: Auto-generated or from story module
├─ Scenes array: [desc1 + img1, desc2 + img2, desc3 + img3]
├─ Style: Selected from ["cinematic", "illustrated", "children's book"]
└─ Metadata: Generation time, mood, etc.

Result: Sequential visual storytelling with 3 unique images
```

### Flow 3: Poster Mode with Text Overlay

```
User Input: "Create a poster about 'Save the Planet' in green tones"
             (slogan explicitly provided in quotes)
    │
    ▼
Slogan Extraction
├─ Look for: quoted text "...", or "slogan should be"
├─ Example: Extract "Save the Planet"
└─ Store for frontend overlay
    │
    ▼
Generate Poster Background
├─ Prompt: "bold typography poster background,
│           Save the Planet, vibrant atmosphere, NO TEXT"
├─ Style: Selected from ["minimalist", "bold", "elegant", "modern"]
└─ Explicitly exclude text to avoid conflicts
    │
    ▼
Encode Images
├─ Generate 2 poster variations
├─ Optimize for web display
└─ Base64 encode

Result: Background image + slogan text
Frontend: Overlays slogan on top of generated image
```

## Component Architecture

### Backend (FastAPI Application)

```python
main.py                          # FastAPI app initialization
├── generate_images_hf()         # Primary image generation (HF Inference API)
├── generate_with_hf()           # Custom HF Space generation with retries
├── generate_high_quality_placeholders()  # Aesthetic fallback images
├── create_emergency_placeholder()  # Basic fallback (last resort)
│
├── Conversation Management
│   ├── get_last_interaction()   # Retrieve previous message/question
│   ├── store_question_asked()   # Save clarifying question
│   ├── store_generated_response() # Save generation result
│   └── update_context_with_mood()  # Store mood for session
│
├── Query Analysis
│   ├── generate_dynamic_suggestions()  # Mood-based suggestions
│   ├── generate_clarifying_question()  # Smart questions
│   └── extract_slogan()         # Poster text extraction
│
├── Content Generation (async)
│   ├── generate_content()       # Main orchestrator
│   │   ├─ Art Mode
│   │   ├─ Poster Mode
│   │   ├─ Story Mode
│   │   ├─ Transform Mode
│   │   ├─ Business Mode
│   │   └─ Personal Mode
│   │
│   └── process_clarified_request()  # Clarification handler
│
├── Utility Functions
│   ├── encode_images()          # Base64 encoding with optimization
│   ├── generate_dynamic_reasoning()  # Explanation text generation
│   └── extract_slogan()         # Marketing text extraction
│
└── API Endpoints
    ├── GET / (service info)
    ├── GET /health (health check)
    ├── POST /chat (main endpoint)
    ├── POST /reset (clear context)
    └── GET /test-deepai (debug)

Supporting Modules:
├── memory.py           # User memory & preferences
├── context.py          # Context tracking
├── story.py            # Story generation
└── intent.py           # Intent classification (optional)
```

### Frontend (React Application)

```javascript
App.jsx                    # Main component
├── State Management
│   ├── messages           // Chat history
│   ├── input              // Current user input
│   ├── loading            // Generation in progress
│   ├── selectedImages     // User selections
│   ├── userMode           // Current generation mode
│   └── expandedReasoning  // UI state
│
├── Component: Chat.js
│   ├── Message Display
│   │   ├─ User messages
│   │   ├─ Bot text responses
│   │   ├─ Image grid (max 4 per message)
│   │   ├─ Story mode display
│   │   └─ Clarifying questions
│   │
│   ├── Input Handling
│   │   ├─ Text input field
│   │   ├─ Mode selector buttons
│   │   └─ Send button
│   │
│   └── API Communication
│       ├─ POST /chat requests
│       ├─ Response parsing
│       ├─ Error handling
│       └─ Loading states
│
└── Styling (App.css)
    ├─ Color palette (--paper, --accent)
    ├─ Responsive grid layout
    ├─ Animation & transitions
    └─ Design system
```

## State Management Architecture

### Frontend State (React)
```javascript
{
  messages: [
    {
      id: 1,
      sender: 'user',
      text: 'Create a peaceful landscape',
      timestamp: 1708536000,
      mode: 'art'
    },
    {
      id: 2,
      sender: 'bot',
      type: 'image',
      content: {
        images: ['base64_1', 'base64_2'],
        reasoning: 'I interpreted...',
        style: 'impressionist'
      },
      timestamp: 1708536018
    }
  ],
  input: '',
  loading: false,
  loadingStage: 'Generating artwork...',
  userMode: 'personal',
  conversationId: 'conv-12345'
}
```

### Backend State (Python)
```python
# In-memory conversation state
conversation_state = {
  'user-123': {
    'last_bot_message': {
      'type': 'question',
      'original_query': 'Draw my day',
      'asked_at': 1708536000
    },
    'mode': 'art',
    'timestamp': 1708536002
  }
}

# Pending context for mood/preferences
pending_context = {
  'user-123': {
    'mood': 'peaceful',
    'original_query': 'Draw my day',
    'question_asked_at': 1708536000
  }
}
```

## Error Handling & Fallbacks

### Three-Tier Fallback System

```
Attempt 1: Primary Generation
└─ Hugging Face API (router.huggingface.co)
   Timeout: 120s
   Retry: 3 attempts with 5s backoff

Attempt 2: If Primary Fails (After 3 retries)
└─ High-quality placeholders
   └─ Gradient backgrounds + decorative elements
   └─ Generated instantly (< 100ms)

Attempt 3: If All Else Fails
└─ Emergency placeholders
   └─ Solid color + prompt text
   └─ Always succeeds, immediate response
```

### Error Handling Flow

```
Request arrives
    │
    ▼
Try primary generation (3 attempts)
    │
    ├─ Success → Return images
    │
    └─ Failure → Next tier
        │
        ▼
    Try high-quality placeholders
        │
        ├─ Success → Return images
        │
        └─ Failure → Next tier
            │
            ▼
        Create emergency placeholders
            │
            └─ Always succeeds → Return images

Result: User never sees error, always gets visual response
```

## Retry Strategy

```python
for attempt in range(3):  # Attempt 1, 2, 3
    try:
        # Make request to HF API
        response = requests.post(
            HF_API_URL,
            json={...},
            timeout=120  # 2 minute timeout
        )
        
        if response.status_code == 200:
            # Success - parse and return
            return decode_images(response.content)
        else:
            # HTTP error - continue to retry
            log_warning(f"HTTP {response.status_code}")
            
    except Timeout:
        # Timeout - wait before retry
        await asyncio.sleep(5)
        continue
        
    except Exception:
        # Other error - wait before retry
        await asyncio.sleep(5)
        continue

# After 3 attempts fail - use placeholder
return create_placeholder_images()
```

## API Response Structure

### Success Response (Image Generation)
```json
{
  "type": "image",
  "content": {
    "images": ["base64_image_1", "base64_image_2"],
    "reasoning": "I interpreted your request...",
    "prompt_used": "peaceful landscape, impressionist style...",
    "mode": "art",
    "style": "impressionist",
    "metadata": {
      "generation_time": 18.5,
      "mode": "art",
      "mood": "peaceful"
    }
  }
}
```

### Clarifying Question Response
```json
{
  "type": "question",
  "content": {
    "text": "Could you tell me more about how your day was?"
  }
}
```

### Error Response
```json
{
  "type": "error",
  "content": {
    "text": "Generation failed: [detailed error message]"
  }
}
```

## Deployment Architecture

### Development Environment
```
Local Machine
├── Backend: http://localhost:8000
│   └─ uvicorn main:app --reload
├── Frontend: http://localhost:5173
│   └─ vite dev server
└── HF Token: .env file
```

### Production Environment
```
Git Repository (GitHub)
    │
    ├─ Push to main branch
    │
    ├─────────────────────────────┬──────────────────────────┐
    │                             │                          │
    ▼                             ▼                          ▼
Vercel                      HF Spaces              OR    Render
(Frontend Deployment)       (Backend Option 1)    (Backend Option 2)
├─ Auto-deploy on push      ├─ Auto-deploy       ├─ Docker container
├─ Global CDN               ├─ Free T4 GPU       ├─ Custom runtime
├─ Environment vars         ├─ Model caching     ├─ Rolling deploy
└─ 99.99% uptime           └─ Hot reload        └─ Easy scaling
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **API Response Time** | 15-30s | Image generation dominant factor |
| **Generation Time** | 15-30s | Varies with HF load |
| **Placeholder Fallback** | <100ms | Instant visual feedback |
| **Image Resolution** | 768×768 | 589,824 pixels per image |
| **Inference Steps** | 30 | Quality/speed tradeoff |
| **Concurrent Requests** | Limited | By backend resource limits |
| **Memory Per Session** | ~1KB | Conversation state only |
| **Database Size** | N/A | No persistent DB (in-memory only) |

## Security Architecture

### CORS Configuration
```python
allow_origins = [
  "http://localhost:5173",           # Local dev
  "http://localhost:5174",           # Alt dev port
  "http://localhost:3000",           # React dev server
  "https://*.vercel.app",            # Vercel previews
  "https://vizzy-chat.vercel.app"    # Production
]
```

### API Key Management
```
Environment Variable: HF_API_TOKEN
├─ Loaded from .env file (local)
├─ Managed in backend only (never sent to frontend)
├─ Validated at startup (fail fast)
└─ Required for every HF API call
```

### Input Validation
```python
# Pydantic models validate all inputs
class ChatRequest(BaseModel):
    user_id: str           # Required
    message: str           # Required
    mode: Optional[str]    # Validated against enum
    conversation_id: Optional[str]  # Optional

# Automatic validation on request
@app.post("/chat")
async def chat(req: ChatRequest):
    # req is guaranteed valid or 422 returned
```

## Scalability Considerations

### Horizontal Scaling
- Multiple backend instances (HF Spaces or Render)
- Load balancer or reverse proxy (nginx/Cloudflare)
- Session state stored in Redis (instead of in-memory)

### Vertical Scaling
- Upgrade GPU (A10, A100 for 3-10x speedup)
- Increase model precision (FP32 → FP16 for memory)
- Cache model in memory for faster inference

### Caching Strategy
- Frontend: Vercel edge caching
- Images: CDN caching with long TTLs
- Models: HF Spaces automatic caching

## Monitoring & Logging

### Frontend Monitoring
- Vercel Analytics (Web Vitals)
- Error tracking (console errors)
- User interactions (optional)

### Backend Monitoring
- HF Spaces logs (stdout/stderr)
- Generation timing metrics
- Error rates and retry statistics
- API token usage tracking

### Health Checks
```python
GET /health
{
  "status": "healthy",
  "hf_configured": true,
  "timestamp": 1708536000.123
}
```

---

**For questions or updates to this document, please open an issue or PR.**

*Document Version: 1.0 | Updated: February 2026*
