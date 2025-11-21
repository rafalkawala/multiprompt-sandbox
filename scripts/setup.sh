#!/bin/bash

# Local development setup script

set -e

echo "Setting up MultiPrompt Sandbox for local development..."

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }

# Setup Frontend
echo "Setting up Frontend..."
cd frontend
npm install
cd ..

# Setup Backend
echo "Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment files
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created backend/.env - Please update with your API keys"
fi

cd ..

# Copy root environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env - Please update with your API keys"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env and backend/.env with your API keys"
echo "2. Start services with: docker-compose up"
echo "   OR"
echo "   - Frontend: cd frontend && npm start"
echo "   - Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
