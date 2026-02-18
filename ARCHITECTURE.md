# 🏗️ Vizzy Chat Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                     (React SPA Interface)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      VERCEL CDN EDGE                             │
│                   (Frontend Deployment)                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │           Static Assets (HTML/CSS/JS)              │         │
│  │  • App.jsx (Main React Component)                 │         │
│  │  • App.css (Design System)                        │         │
│  │  • Mode Selection UI                              │         │
│  │  • Image Display Grid                             │         │
│  └────────────────────────────────────────────────────┘         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ REST API
                            │ POST /chat
                            │ POST /reset
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                  HUGGING FACE SPACES                             │
│                  (Backend GPU Server)                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │              FastAPI Application                   │         │
│  │  ┌──────────────────────────────────────────────┐ │         │
│  │  │  Endpoint: /chat                             │ │         │
│  │  │    • Intent Classification                   │ │         │
│  │  │    • Mode Detection (art/poster/story/etc)   │ │         │
│  │  │    • Vague Query Detection                   │ │         │
│  │  │    • Clarifying Question Generation          │ │         │
│  │  │    • Context Management                      │ │         │
│  │  └──────────────────────────────────────────────┘ │         │
│  │                                                    │         │
│  │  ┌──────────────────────────────────────────────┐ │         │
│  │  │  Endpoint: /reset                            │ │         │
│  │  │    • Clear User Context                      │ │         │
│  │  │    • Reset Conversation State                │ │         │
│  │  └──────────────────────────────────────────────┘ │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │           AI Models (GPU Accelerated)              │         │
│  │                                                    │         │
│  │  ┌──────────────────────────────────────────────┐ │         │
│  │  │ Stable Diffusion v1.5                        │ │         │
│  │  │  • Text-to-Image Generation                  │ │         │
│  │  │  • Style Transfer                            │ │         │
│  │  │  • 4 variations per request                  │ │         │
│  │  │  • Resolution: 512×512                       │ │         │
│  │  │  • Steps: 25 (configurable)                  │ │         │
│  │  └──────────────────────────────────────────────┘ │         │
│  │                                                    │         │
│  │  ┌──────────────────────────────────────────────┐ │         │
│  │  │ GPT-2 Medium                                 │ │         │
│  │  │  • Story Generation                          │ │         │
│  │  │  • 3-scene narratives                        │ │         │
│  │  │  • Scene descriptions for SD                 │ │         │
│  │  └──────────────────────────────────────────────┘ │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │           Custom Logic Modules                     │         │
│  │                                                    │         │
│  │  • intent.py - Intent classification              │         │
│  │  • context.py - User context & mood tracking      │         │
│  │  • memory.py - Conversation memory                │         │
│  │  • story.py - Story generation pipeline           │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │          In-Memory Storage                         │         │
│  │  • conversation_state (dict)                       │         │
│  │  • pending_context (dict)                          │         │
│  │  • user_preferences (JSON file)                    │         │
│  └────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Image Generation Request
```
User Input → Frontend → Backend API → Intent Classification
    ↓
Mode Selection → Prompt Engineering → Stable Diffusion
    ↓
Image Generation (4 variations) → Base64 Encoding → JSON Response
    ↓
Frontend Display → User Selection → Refinement Options
```

### 2. Vague Query Handling
```
User: "Draw my day" → Backend detects vague query
    ↓
Generate clarifying question → Store in pending_context
    ↓
User answers → Retrieve context → Combine with original query
    ↓
Generate final output (image/story/etc.)
```

### 3. Story Mode Flow
```
User request → Story mode detected → GPT-2 generates 3 scenes
    ↓
Each scene → Stable Diffusion → Scene image
    ↓
Combine narrative + images → Return structured response
    ↓
Frontend displays story with images in sequence
```

## Technology Stack Details

### Frontend Technologies
- **React 19.2.0**: UI framework
- **Vite 7.3.1**: Build tool & dev server
- **CSS3 Custom Properties**: Design system
  - Warm color palette (--paper, --accent)
  - Gradient orbs background
  - Responsive grid layout

### Backend Technologies
- **FastAPI 0.104.1**: REST API framework
- **PyTorch 2.x**: Deep learning framework
- **Diffusers**: Stable Diffusion pipeline
- **Transformers**: GPT-2 for text generation
- **Pillow**: Image processing
- **Uvicorn**: ASGI server

### Infrastructure
- **Vercel**: Frontend hosting & CDN
  - Auto-deploy from GitHub
  - Edge network distribution
  - Environment variable management
  
- **Hugging Face Spaces**: Backend hosting
  - Free T4 GPU access
  - Docker container deployment
  - Model caching
  - Auto-rebuild on push

## API Endpoints

### POST /chat
**Purpose**: Main conversation endpoint

**Request**:
```json
{
  "user_id": "string",
  "message": "string",
  "mode": "art|poster|story|transform|business|personal",
  "conversation_id": "string (optional)"
}
```

**Response Types**:

**1. Image Response**:
```json
{
  "type": "image",
  "content": {
    "images": ["base64_image1", "base64_image2", ...],
    "reasoning": "AI's creative reasoning",
    "mode": "art",
    "style": "impressionist"
  }
}
```

**2. Story Response**:
```json
{
  "type": "story_with_images",
  "content": {
    "story": {
      "title": "Story Title",
      "scenes": [
        {
          "scene_number": 1,
          "description": "Scene text",
          "image": "base64_image"
        }
      ]
    },
    "reasoning": "Story generation reasoning"
  }
}
```

**3. Clarifying Question**:
```json
{
  "type": "clarifying_question",
  "content": {
    "question": "Could you describe your day in more detail?",
    "suggestions": ["It was peaceful", "It was hectic", "It was creative"]
  }
}
```

### POST /reset
**Purpose**: Clear user conversation state

**Request**:
```json
{
  "user_id": "string"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Context cleared"
}
```

### GET /health
**Purpose**: Health check

**Response**:
```json
{
  "status": "healthy"
}
```

## State Management

### Frontend State
```javascript
{
  messages: [],              // Chat history
  input: "",                 // Current input
  loading: false,            // Loading state
  loadingStage: "",          // Progress message
  selectedImages: [],        // User selections
  userMode: "personal",      // Current mode
  conversationId: null,      // Conversation ID
  expandedReasoning: {},     // Reasoning visibility
  editableSlogans: {}        // Poster text editing
}
```

### Backend State
```python
conversation_state = {
  "user_id": {
    "last_bot_message": {...},
    "mode": "art",
    "timestamp": 1234567890
  }
}

pending_context = {
  "user_id": {
    "original_query": "...",
    "mode": "...",
    "question_asked": "..."
  }
}
```

## Deployment Pipeline

```
Developer Push to GitHub
    ↓
GitHub Actions (Optional)
    ↓
├─→ Vercel Build
│   ├─ Install dependencies
│   ├─ Build React app
│   ├─ Deploy to Edge
│   └─ Invalidate cache
│
└─→ HF Spaces Build
    ├─ Pull Docker image
    ├─ Install Python deps
    ├─ Download AI models
    ├─ Start FastAPI server
    └─ Expose endpoint
```

## Security Features

### CORS Protection
```python
allow_origins = [
  "http://localhost:5173",      # Local dev
  "https://*.vercel.app",       # Vercel previews
  "https://your-domain.com"     # Production
]
```

### Input Validation
- Pydantic models for request validation
- Max message length limits
- User ID sanitization

### Rate Limiting (Recommended)
```python
# Add to backend
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: ChatRequest):
    ...
```

## Performance Optimization

### Frontend
- Code splitting (Vite automatic)
- Asset caching (31536000s for assets)
- Lazy image loading
- Debounced inputs

### Backend
- Model caching (loaded once)
- Attention slicing (memory optimization)
- Async request handling
- ThreadPoolExecutor for CPU tasks

### Infrastructure
- CDN edge caching (Vercel)
- GPU acceleration (HF Spaces T4)
- Image compression (Base64)

## Monitoring & Logging

### Frontend Monitoring
- Vercel Analytics (page views, performance)
- Browser console errors
- Network request monitoring

### Backend Monitoring
- HF Spaces logs (stdout/stderr)
- FastAPI logging
- GPU usage metrics
- Request timing

## Error Handling

### Frontend Errors
```javascript
try {
  const response = await fetch(...);
  if (!response.ok) throw new Error(...);
  const data = await response.json();
} catch (err) {
  console.error(err);
  // Show user-friendly error
}
```

### Backend Errors
```python
try:
    result = generate_image(...)
except Exception as e:
    logger.error(f"Generation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

## Scaling Strategy

### Horizontal Scaling
- Multiple HF Spaces instances
- Load balancer (Cloudflare/nginx)
- Distributed queue (Redis)

### Vertical Scaling
- Upgrade to larger GPU (A10G, A100)
- Increase memory allocation
- Optimize model precision (FP16)

### Caching Layer
- Redis for conversation state
- CDN for generated images
- Model weight caching

---

**Last Updated**: 2025
**Architecture Version**: 1.0
