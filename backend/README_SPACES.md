---
title: Vizzy Chat API
emoji: 🎨
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Vizzy Chat API

AI-powered creative image generation API with mood detection and multi-modal outputs.

## Features

- 🎨 Art Mode - Creative artistic interpretations
- 📰 Poster Mode - Typography and marketing materials
- 📖 Story Mode - 3-scene narratives with illustrations
- 🔄 Transform Mode - Style transfer
- 💼 Business Mode - Professional visuals

## API Endpoints

- `POST /chat` - Main chat endpoint
- `POST /reset` - Reset conversation context
- `GET /health` - Health check

## Usage

```python
import requests

response = requests.post(
    "YOUR_SPACE_URL/chat",
    json={
        "user_id": "demo-user",
        "message": "Create a peaceful landscape",
        "mode": "art"
    }
)
```
