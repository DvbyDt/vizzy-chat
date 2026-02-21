# 🎨 Vizzy Chat - AI Creative Studio

An intelligent, context-aware AI assistant that generates images, stories, and posters through natural language conversations. Features mood detection, intelligent clarifying questions, and multiple creative modes powered by Hugging Face Stable Diffusion XL.

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Stable Diffusion XL](https://img.shields.io/badge/Stable%20Diffusion%20XL-768x768-FF6B35?logo=huggingface&logoColor=white)](https://huggingface.co)
[![Deploy](https://img.shields.io/badge/Deploy-Vercel%20%26%20Render-000?logo=vercel&logoColor=white)](https://vercel.com)

## ✨ Features

### 🎨 **Art Mode**
Generate expressive artistic interpretations with intelligent mood detection
- Randomized art styles (impressionist, expressionist, abstract, surreal)
- Emotion-aware color palettes
- 768×768 high-quality output
- Fallback placeholders for reliability

### 📰 **Poster Mode**
Create professional poster backgrounds with optional text overlays
- Extract slogans from user input (quoted text or explicit patterns)
- Multiple poster aesthetics (minimalist, bold, elegant, modern)
- Web-ready image optimization
- Perfect for marketing materials

### 📖 **Story Mode**
Generate 3-scene visual narratives with auto-generated story structures
- Cinematic, illustrated, and children's book styles
- Sequential scene-by-scene image generation
- Contextual mood preservation across scenes
- Story title generation included

### 🔄 **Transform Mode**
Reimagine content in different artistic styles
- Oil painting, watercolor, sketch, cyberpunk styles
- Style-aware prompt engineering
- Maintains original intent while transforming aesthetic

### 💼 **Business Mode**
Generate professional commercial visuals
- Clean, modern aesthetic optimized for corporate use
- Professional color palettes
- Premium quality settings
- Perfect for presentations and marketing

### 🧠 **Intelligent Conversation Flow**
- Automatic detection of vague queries ("tell me about your day")
- Context-aware clarifying questions with mood detection
- Persistent user mood tracking across generation attempts
- Smart conversation state management

## 🚀 Quick Start

### Prerequisites
- **Python** 3.10+
- **Node.js** 18+
- **RAM** 4GB minimum (8GB+ recommended)
- **Internet connection** (for HuggingFace API)

### Local Development

#### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with HuggingFace token
echo "HF_API_TOKEN=your_hf_token_here" > .env

# Start backend server
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000`

#### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs at `http://localhost:5173`

#### 3. Test the Application

```bash
# In your browser
open http://localhost:5173

# Or manually test the API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "message": "Create a peaceful landscape",
    "mode": "art"
  }'
```

## 🌐 Deployment

### Frontend Deployment (Vercel)

```bash
# Link to Vercel
vercel link

# Deploy
vercel --prod
```

Environment variables needed:
- `VITE_API_URL`: Backend API endpoint

### Backend Deployment (Render or HuggingFace Spaces)

#### Option 1: HuggingFace Spaces (Recommended)
1. Create new Space on [HuggingFace](https://huggingface.co/spaces)
2. Connect your GitHub repository
3. Add `HF_API_TOKEN` as a secret
4. Deploy automatically on push

#### Option 2: Render
1. Create new Web Service on [Render](https://render.com)
2. Connect GitHub repo
3. Configure environment variables
4. Deploy

Required environment variables:
```env
HF_API_TOKEN=your_token_here
```

## 📚 API Documentation

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-backend-url.com`

### Endpoints

#### `POST /chat` - Generate Content
Main endpoint for all generation modes.

**Request:**
```json
{
  "user_id": "unique-user-id",
  "message": "Create a peaceful landscape with mountains",
  "mode": "art",
  "conversation_id": "optional-conversation-id"
}
```

**Response (Success):**
```json
{
  "type": "image",
  "content": {
    "images": ["base64_encoded_image_1", "base64_encoded_image_2"],
    "reasoning": "I interpreted 'peaceful landscape' through an impressionist lens...",
    "prompt_used": "peaceful landscape with mountains, impressionist style, artistic...",
    "mode": "art",
    "style": "impressionist",
    "metadata": {
      "generation_time": 18.5,
      "mood": "vibrant"
    }
  }
}
```

**Response (Clarifying Question):**
```json
{
  "type": "question",
  "content": {
    "text": "Could you tell me more about how your day was?"
  }
}
```

**Mode Values:**
- `art` - Creative artistic generation
- `poster` - Poster background with optional text
- `story` - 3-scene narrative with images
- `transform` - Style transformation
- `business` - Professional commercial visuals
- `personal` - Default mode with user context (default)

#### `POST /reset` - Clear User Context
Reset conversation history and mood for a user.

**Request:**
```json
{
  "user_id": "unique-user-id"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

#### `GET /health` - Health Check
Check if backend is operational.

**Response:**
```json
{
  "status": "healthy",
  "hf_configured": true,
  "timestamp": 1708536000.123
}
```

#### `GET /` - Service Info
Get API version and model information.

**Response:**
```json
{
  "service": "Vizzy Chat API",
  "version": "1.0.0",
  "status": "operational",
  "model": "Stable Diffusion XL via Hugging Face",
  "hf_url": "https://model-url"
}
```

## 🎯 Usage Examples

### Example 1: Vague to Detailed Conversation
```
User: "Draw my day"
↓
Vizzy: "Could you tell me more about how your day was?"
↓
User: "It was dull and I needed motivation"
↓
Vizzy: [Generates energetic abstract art with vibrant colors]
```

### Example 2: Direct Art Request
```
User (Art Mode): "A cyberpunk cityscape with neon lights at dusk"
↓
Vizzy: [Generates 2 impressionist/surreal interpretations]
```

### Example 3: Story Generation
```
User (Story Mode): "An adventure in an enchanted forest"
↓
Vizzy: 
  Scene 1: Opening image + description
  Scene 2: Middle image + description
  Scene 3: Conclusion image + description
```

### Example 4: Business Content
```
User (Business Mode): "Professional office with modern furniture"
↓
Vizzy: [Generates corporate-ready product photography style images]
```

## 🛠️ Technology Stack

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 19.2.0 | UI framework |
| Vite | 7.3.1 | Build tool & dev server |
| JavaScript | ES6+ | Application logic |
| CSS3 | Custom | Design system & styling |

### Backend
| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.104.1 | REST API framework |
| Python | 3.10+ | Backend runtime |
| Pydantic | 2.4.2 | Data validation |
| Pillow | 10.1.0 | Image processing |
| Requests | 2.31.0 | HTTP client |
| python-dotenv | 1.0.0 | Environment management |

### AI Models
| Model | Provider | Purpose |
|---|---|---|
| Stable Diffusion XL | Hugging Face | Text-to-image generation (768×768) |
| HF Inference API | Hugging Face | Model serving infrastructure |

### Infrastructure
| Service | Purpose |
|---|---|
| Vercel | Frontend hosting & CDN |
| Hugging Face Spaces / Render | Backend hosting with GPU access |
| GitHub | Version control & CI/CD |

## 📊 Performance

| Metric | Value |
|---|---|
| **Image Generation Time** | 15-30 seconds (varies by model availability) |
| **Image Resolution** | 768×768 pixels |
| **Inference Steps** | 30 (quality vs speed tradeoff) |
| **Guidance Scale** | 7.5 (creativity control) |
| **Concurrent Requests** | Limited by backend resource availability |
| **Fallback Placeholder Time** | <100ms |

## 🔐 Security & Privacy

- **No Persistent User Data**: Conversation state is in-memory only
- **CORS Protection**: Configured for frontend URLs only
- **Input Validation**: All requests validated with Pydantic models
- **Environment Secrets**: API tokens stored securely in `.env`
- **API Authentication**: HuggingFace token required for model access
- **No Tracking**: No user analytics or telemetry

## 🐛 Troubleshooting

### Backend Issues

**Error: `HF_API_TOKEN not configured`**
```bash
# Solution: Create .env file in backend directory
cd backend
echo "HF_API_TOKEN=your_token_here" > .env
```

**Error: `Connection refused`**
- Ensure backend is running: `uvicorn main:app --reload`
- Check port 8000 is available
- Verify CORS is configured correctly

**Error: Generation timeouts**
- HuggingFace API may be slow or overloaded
- Check HuggingFace status page
- Fallback placeholders will be generated after 3 retries

### Frontend Issues

**Error: `Failed to fetch from backend`**
- Ensure backend is running and accessible
- Check `VITE_API_URL` environment variable is set
- Verify CORS headers in backend response

**Error: Images not displaying**
- Clear browser cache
- Check base64 image encoding in response
- Verify image MIME types are correct

## 📁 Project Structure

```
vizzy-chat/
├── backend/
│   ├── main.py              # FastAPI application with all endpoints
│   ├── memory.py            # User memory & preference management
│   ├── context.py           # Context tracking & mood detection
│   ├── story.py             # Story generation module
│   ├── intent.py            # Intent classification
│   ├── requirements.txt      # Python dependencies
│   └── .env                 # Environment variables (not in repo)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── Chat.js          # Chat UI component
│   │   ├── App.css          # Styling
│   │   └── main.jsx         # Entry point
│   ├── package.json         # Node dependencies
│   ├── vite.config.js       # Vite configuration
│   └── index.html           # HTML template
│
├── README.md                # This file
├── ARCHITECTURE.md          # Detailed system architecture
└── LICENSE                  # MIT License
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. **Make** your changes with clear, focused commits
4. **Test** thoroughly
5. **Push** to your branch
   ```bash
   git push origin feature/AmazingFeature
   ```
6. **Open** a Pull Request with a descriptive title

### Development Guidelines

- Follow existing code style and conventions
- Add docstrings to functions explaining their purpose
- Test new features locally before submitting
- Keep commits atomic and well-documented
- Update README if adding new features

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

### Third-Party Licenses

- **Stable Diffusion XL** - Model by Stability AI, licensed under OpenRAIL
- **FastAPI** - MIT License
- **React** - MIT License
- **Vite** - MIT License

## 🙏 Acknowledgments

- **Stability AI** for Stable Diffusion XL
- **Hugging Face** for model hosting and inference API
- **FastAPI** community for the amazing framework
- **React** & **Vite** communities for excellent tooling

## 📞 Support & Discussion

- 📝 **Issues**: Report bugs and request features via [GitHub Issues](../../issues)
- 💬 **Discussions**: Join conversations in [GitHub Discussions](../../discussions)
- 🐛 **Bug Reports**: Use the bug report template when creating issues
- ✨ **Feature Requests**: Describe the use case and expected behavior

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [React Documentation](https://react.dev)
- [Stable Diffusion Guide](https://huggingface.co/docs/diffusers)
- [Hugging Face API Docs](https://huggingface.co/docs/api-inference)

## 🚀 Roadmap

Future features under consideration:

- [ ] Image upscaling (4x resolution)
- [ ] Video generation support
- [ ] Fine-tuned model variants
- [ ] Persistent user preferences database
- [ ] Rate limiting and usage quotas
- [ ] Batch processing API
- [ ] WebSocket for real-time streaming
- [ ] User authentication system

---

**Built with ❤️ by [Dhruv Vashist](https://github.com/DvbyDt)**

If you find this project useful, please consider giving it a ⭐ [**Star**](../../)!

*Last Updated: February 2026*
