#!/usr/bin/env bash
# Global Commodity Traffic - Start both backend and frontend servers
# Backend: http://localhost:16667
# Frontend: http://localhost:16668

# ===== UN Comtrade API Key (free tier) =====
# Get yours at https://comtradedeveloper.un.org/
export COMTRADE_API_KEY="YOUR_KEY_HERE"

set -e

echo "============================================"
echo " Global Commodity Traffic - Server Launcher"
echo "============================================"
echo ""
echo "Backend API:  http://localhost:16667"
echo "Frontend UI:  http://localhost:16668"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Setup Python venv if needed
if [ ! -d "backend/.venv" ]; then
    echo "[Setup] Creating Python virtual environment..."
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Setup frontend if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "[Setup] Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Initialize DB if needed
if [ ! -f "backend/data/trade.db" ]; then
    echo "[Setup] Initializing database..."
    cd backend
    source .venv/bin/activate
    python -c "from app.db.seed import init_db; init_db()"
    python -m app.db.seed_demo_trades
    cd ..
fi

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo "[Starting] Backend server on port 16667..."
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 16667 &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 2

# Start frontend
echo "[Starting] Frontend dev server on port 16668..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo " Servers started! Open http://localhost:16668"
echo " Press Ctrl+C to stop both servers..."
echo "============================================"

wait
