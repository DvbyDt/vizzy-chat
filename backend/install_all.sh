#!/bin/bash

echo "🚀 Installing all missing packages..."
echo "==================================="

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install core packages
echo "📦 Installing FastAPI and related packages..."
pip install "fastapi==0.104.1"
pip install "pydantic==2.4.2"
pip install "python-multipart==0.0.6"

# Install uvicorn (with quotes for zsh)
echo "📦 Installing uvicorn..."
pip install "uvicorn[standard]==0.24.0"

# Install ML packages
echo "📦 Installing ML packages..."
pip install "torch==2.1.0" --index-url https://download.pytorch.org/whl/cpu
pip install "numpy==1.24.3"
pip install "huggingface-hub==0.23.0"
pip install "diffusers==0.24.0"
pip install "transformers==4.35.0"
pip install "accelerate==0.24.1"
pip install "sentencepiece==0.1.99"

# Install image processing
echo "📦 Installing Pillow..."
pip install "pillow==10.1.0"

# Install utilities
echo "📦 Installing utilities..."
pip install "python-dotenv==1.0.0"
pip install "requests==2.31.0"

# Verify installation
echo -e "\n🔍 Verifying installations..."
python -c "
import fastapi
import uvicorn
import torch
import diffusers
import transformers
print('✅ fastapi:', fastapi.__version__)
print('✅ uvicorn:', uvicorn.__version__)
print('✅ torch:', torch.__version__)
print('✅ All packages installed successfully!')
"

echo -e "\n✅ Setup complete!"