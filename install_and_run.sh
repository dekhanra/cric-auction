#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  🏏 CRICKET AUCTION - One-Click Setup & Run
# ═══════════════════════════════════════════════════════════════════

set -e

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🏏  CRICKET AUCTION INSTALLER"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ───────────────────────────────────────────────────────────────────
# 1. Check Python
# ───────────────────────────────────────────────────────────────────
echo "📦 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+ first."
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   Found Python $PYTHON_VERSION"

# ───────────────────────────────────────────────────────────────────
# 2. Create virtual environment if needed
# ───────────────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# ───────────────────────────────────────────────────────────────────
# 3. Install dependencies
# ───────────────────────────────────────────────────────────────────
echo "📦 Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet fastapi uvicorn[standard]
echo "   ✅ FastAPI & Uvicorn installed"

# ───────────────────────────────────────────────────────────────────
# 4. Download Cloudflare Tunnel (cloudflared) if not present
# ───────────────────────────────────────────────────────────────────
CLOUDFLARED="$SCRIPT_DIR/cloudflared"
if [ ! -f "$CLOUDFLARED" ]; then
    echo "📦 Downloading Cloudflare Tunnel (for secure public URL)..."
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$CLOUDFLARED"
    chmod +x "$CLOUDFLARED"
    echo "   ✅ Cloudflare Tunnel ready"
else
    echo "   ✅ Cloudflare Tunnel already downloaded"
fi

# ───────────────────────────────────────────────────────────────────
# 5. Clean old database (optional)
# ───────────────────────────────────────────────────────────────────
if [ -f "auction.db" ]; then
    echo ""
    read -p "🗑️  Found existing database. Reset it? (y/N): " RESET_DB
    if [[ "$RESET_DB" =~ ^[Yy]$ ]]; then
        rm -f auction.db auction.db-wal auction.db-shm
        echo "   ✅ Database reset"
    fi
fi

# ───────────────────────────────────────────────────────────────────
# 6. Show credentials
# ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  🔐 LOGIN CREDENTIALS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  TEAM LOGINS:"
echo "  ───────────────────────────────────────────────"
echo "  🔴 Royal Strikers    →  role: team1   pass: strike1"
echo "  🔵 Thunder Kings     →  role: team2   pass: thunder2"
echo "  🟢 Super Chargers    →  role: team3   pass: charge3"
echo "  🟡 Fire Eagles       →  role: team4   pass: eagle4"
echo ""
echo "  👑 ADMIN (Auctioneer) → role: admin   pass: admin123"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ───────────────────────────────────────────────────────────────────
# 7. Start Cloudflare Tunnel in background
# ───────────────────────────────────────────────────────────────────
echo "🌐 Starting secure tunnel (Cloudflare)..."
# Kill any existing cloudflared
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

# Start cloudflared in background, capture output to get URL
"$CLOUDFLARED" tunnel --url http://localhost:8000 > /tmp/cloudflared.log 2>&1 &
TUNNEL_PID=$!

# Wait for tunnel to establish and extract URL
echo "   Waiting for tunnel to connect..."
sleep 5

# Try to get the public URL from logs
TUNNEL_URL=""
for i in {1..10}; do
    TUNNEL_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log 2>/dev/null | head -1)
    if [ -n "$TUNNEL_URL" ]; then
        break
    fi
    sleep 1
done

if [ -n "$TUNNEL_URL" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🌍 PUBLIC URL (share with teams):"
    echo ""
    echo "     🔒 $TUNNEL_URL"
    echo ""
    echo "  This is a secure HTTPS link. Share it with all 4 teams!"
    echo "═══════════════════════════════════════════════════════════════"
else
    echo "   ⚠️  Could not get tunnel URL automatically."
    echo "   Check /tmp/cloudflared.log for the URL"
    echo "   Or run in another terminal: cat /tmp/cloudflared.log | grep trycloudflare"
fi

# ───────────────────────────────────────────────────────────────────
# 8. Start the server
# ───────────────────────────────────────────────────────────────────
echo ""
echo "🚀 Starting Cricket Auction Server..."
echo "   Local:  http://localhost:8000"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $TUNNEL_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Run the FastAPI server
python3 main.py

# Cleanup on normal exit
kill $TUNNEL_PID 2>/dev/null || true
