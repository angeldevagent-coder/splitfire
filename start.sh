#!/bin/bash
# SplitFire Startup Script
# Usage: ./start.sh

set -e

echo "🔥 Starting SplitFire..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in .env"
fi

# Start Streamlit in background
echo "📦 Starting Streamlit app..."
cd "$(dirname "$0")"
streamlit run app.py --server.port 8501 --server.address 127.0.0.1 &
STREAMLIT_PID=$!

# Wait a moment for Streamlit to start
sleep 3

# Start Cloudflare Tunnel
if command -v cloudflared &> /dev/null; then
    echo "🌐 Starting Cloudflare Tunnel..."
    cloudflared tunnel --url http://localhost:8501 --no-autoupdate 2>&1 &
    TUNNEL_PID=$!
    
    # Wait for tunnel to establish
    sleep 5
    
    # Get the tunnel URL
    TUNNEL_URL=$(curl -s localhost:35457/health 2>/dev/null || echo "")
    echo ""
    echo "✅ SplitFire is running!"
    echo ""
    echo "📍 Local:    http://localhost:8501"
    echo "🌍 Public:   $TUNNEL_URL"
    echo ""
    echo "Press Ctrl+C to stop"
    
    # Wait for tunnel process
    wait $TUNNEL_PID
else
    echo ""
    echo "✅ SplitFire is running locally!"
    echo "📍 Local: http://localhost:8501"
    echo ""
    echo "⚠️  cloudflared not found. Install it to get a public URL:"
    echo "   brew install cloudflare/cloudflare/cloudflared"
    echo ""
    echo "Press Ctrl+C to stop"
    
    # Wait for Streamlit
    wait $STREAMLIT_PID
fi
