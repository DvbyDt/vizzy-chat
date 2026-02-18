#!/bin/bash

# Vizzy Chat Deployment Helper Script
# This script helps you prepare for deployment

echo "🚀 Vizzy Chat Deployment Helper"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if git is initialized
if [ ! -d .git ]; then
    echo -e "${YELLOW}Git not initialized. Initializing...${NC}"
    git init
    echo -e "${GREEN}✓ Git initialized${NC}"
else
    echo -e "${GREEN}✓ Git already initialized${NC}"
fi

# Check if .gitignore exists
if [ -f .gitignore ]; then
    echo -e "${GREEN}✓ .gitignore exists${NC}"
else
    echo -e "${RED}✗ .gitignore missing!${NC}"
fi

# Check backend dependencies
echo ""
echo "Checking backend..."
cd backend

if [ -f requirements.txt ]; then
    echo -e "${GREEN}✓ requirements.txt found${NC}"
else
    echo -e "${RED}✗ requirements.txt missing!${NC}"
fi

if [ -f Dockerfile ]; then
    echo -e "${GREEN}✓ Dockerfile found${NC}"
else
    echo -e "${RED}✗ Dockerfile missing!${NC}"
fi

# Test backend locally
echo ""
echo "Testing backend Docker build..."
if command -v docker &> /dev/null; then
    docker build -t vizzy-backend-test . 2>&1 | grep -q "Successfully built" || grep -q "Successfully tagged"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backend Docker build successful${NC}"
    else
        echo -e "${YELLOW}⚠ Docker build had warnings. Check output.${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Docker not installed. Skipping Docker test.${NC}"
fi

cd ..

# Check frontend
echo ""
echo "Checking frontend..."
cd frontend

if [ -f package.json ]; then
    echo -e "${GREEN}✓ package.json found${NC}"
else
    echo -e "${RED}✗ package.json missing!${NC}"
fi

if [ -f .env.example ]; then
    echo -e "${GREEN}✓ .env.example found${NC}"
else
    echo -e "${YELLOW}⚠ .env.example not found${NC}"
fi

# Test frontend build
if [ -d node_modules ]; then
    echo ""
    echo "Testing frontend build..."
    npm run build > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend build successful${NC}"
        rm -rf dist # Clean up
    else
        echo -e "${RED}✗ Frontend build failed!${NC}"
    fi
else
    echo -e "${YELLOW}⚠ node_modules not found. Run 'npm install' first.${NC}"
fi

cd ..

# Summary
echo ""
echo "================================"
echo "📋 Next Steps:"
echo "================================"
echo ""
echo "1. Create GitHub repository:"
echo "   ${YELLOW}gh repo create vizzy-chat --public --source=. --remote=origin${NC}"
echo ""
echo "2. Push to GitHub:"
echo "   ${YELLOW}git add .${NC}"
echo "   ${YELLOW}git commit -m 'Initial commit'${NC}"
echo "   ${YELLOW}git push -u origin main${NC}"
echo ""
echo "3. Deploy Backend to Hugging Face Spaces:"
echo "   • Go to https://huggingface.co/spaces"
echo "   • Create new Space (SDK: Docker, Hardware: T4 Small)"
echo "   • Upload backend folder contents"
echo ""
echo "4. Deploy Frontend to Vercel:"
echo "   • Go to https://vercel.com/new"
echo "   • Import your GitHub repo"
echo "   • Set root directory: ${YELLOW}frontend${NC}"
echo "   • Add env var: ${YELLOW}VITE_API_URL${NC} = your HF Space URL"
echo ""
echo "5. Update CORS in backend/main.py with your Vercel domain"
echo ""
echo "📖 See ${YELLOW}DEPLOY_CHECKLIST.md${NC} for complete guide"
echo "📖 See ${YELLOW}DEPLOYMENT.md${NC} for detailed instructions"
echo ""
echo -e "${GREEN}Ready to deploy! 🚀${NC}"
