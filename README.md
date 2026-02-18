# 🎨 Vizzy Chat - AI Creative Studio

An intelligent AI-powered creative assistant that generates images, posters, and stories based on natural language descriptions with mood detection and contextual understanding.

![Vizzy Chat](https://img.shields.io/badge/AI-Creative%20Studio-purple?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-blue?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?style=for-the-badge&logo=fastapi)
![Stable Diffusion](https://img.shields.io/badge/Stable%20Diffusion-v1.5-orange?style=for-the-badge)

## ✨ Features

### 🎨 **Art Mode**
Creative artistic interpretations with expressive styles
- Abstract art
- Impressionist renderings
- Surreal compositions
- Emotional color palettes

### 📰 **Poster Mode**
Professional typography and marketing materials
- Text overlay support
- Minimalist designs
- Brand-ready templates

### 📖 **Story Mode**
3-scene narratives with cinematic illustrations
- Automatic scene generation
- Consistent visual storytelling
- Multiple art styles

### 🔄 **Transform Mode**
Style transfer and reimagining
- Oil painting
- Watercolor
- Sketch styles
- Digital art conversion

### 💼 **Business Mode**
Professional commercial visuals
- Product photography
- Corporate aesthetics
- Premium quality

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- 8GB+ RAM (16GB recommended for GPU)

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` 🎉

## 🌐 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

**Quick Deploy:**
- Frontend: [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
- Backend: [![Deploy on HF](https://huggingface.co/datasets/huggingface/badges/resolve/main/deploy-on-spaces-md.svg)](https://huggingface.co/spaces)

## 🏗️ Architecture

```
┌─────────────────┐
│  React + Vite   │
│   (Frontend)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   FastAPI       │─────▶│ Stable Diffusion │
│   (Backend)     │      │   (AI Model)     │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Memory Store   │
│  (JSON/DB)      │
└─────────────────┘
```

## 📖 API Documentation

### Endpoints

#### `POST /chat`
Main chat endpoint for all modes

**Request:**
```json
{
  "user_id": "demo-user",
  "message": "Create a peaceful landscape",
  "mode": "art"
}
```

**Response:**
```json
{
  "type": "image",
  "content": {
    "images": ["base64_encoded_image1", "..."],
    "reasoning": "AI's creative reasoning...",
    "mode": "art",
    "style": "impressionist"
  }
}
```

#### `POST /reset`
Clear user conversation context

#### `GET /health`
Health check endpoint

## 🎯 Usage Examples

### Vague to Detailed Prompts
```
User: "Draw my day"
Vizzy: "Could you tell me more about how your day was?"
User: "It was dull and I needed motivation"
Vizzy: [Generates moody abstract art with subdued colors]
```

### Direct Creative Requests
```
User (Art Mode): "A cyberpunk cityscape at sunset"
Vizzy: [Generates 4 artistic variations]
```

### Business Use Case
```
User (Business Mode): "Product shot of wireless headphones"
Vizzy: [Generates professional product photography]
```

## 🛠️ Technology Stack

**Frontend:**
- React 19
- Vite
- CSS3 (Custom design system)

**Backend:**
- FastAPI
- PyTorch
- Hugging Face Diffusers
- Stable Diffusion v1.5
- Transformers (GPT-2 for stories)

**Infrastructure:**
- Docker
- Vercel (Frontend)
- Hugging Face Spaces (Backend)

## 📊 Performance

- **Generation Time**: 15-25s per image (CPU), 3-5s (GPU)
- **Concurrent Requests**: Up to 5 (configurable)
- **Image Resolution**: 512x512 (configurable)
- **Quality**: 25 inference steps

## 🔐 Security

- CORS protection
- Rate limiting ready
- Input validation
- Environment-based secrets
- No user data storage (memory only)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Stable Diffusion by Stability AI
- Hugging Face for model hosting
- FastAPI framework
- React & Vite communities

## 📞 Support

- Open an issue for bugs
- Discussions for feature requests
- Twitter: [@yourusername](https://twitter.com)

---

**Built with ❤️ by Dhruv Vashist**

⭐ Star this repo if you find it useful!
