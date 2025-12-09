#!/bin/bash

echo "========================================"
echo "Starting Fintech Risk Agent Platform"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run: python -m venv .venv"
    echo "Then run: .venv/Scripts/activate (Windows) or source .venv/bin/activate (Unix)"
    echo "Then run: pip install -r backend/requirements.txt"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "Error: Node modules not found!"
    echo "Please run: cd frontend && npm install"
    exit 1
fi

echo "[1/2] Starting Backend Server (Port 8000)..."
source .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate 2>/dev/null
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 3

echo ""
echo "[2/2] Starting Frontend Dev Server (Port 3000)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Application Started Successfully!"
echo "========================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/api-docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
