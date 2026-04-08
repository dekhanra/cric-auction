# 🏏 Cricket Auction App

A simple, real-time IPL-style cricket player auction system for university tournaments. Run it on your laptop and let 4 teams bid live from their phones/laptops!

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Real-time bidding** via WebSockets — all teams see bids instantly
- **4 team logins** with password protection
- **Admin/Auctioneer controls** — next player, sold, unsold
- **Player pools** — Marquee, Batsman, Bowler, All-Rounder
- **Budget tracking** — auto-deducted when player is sold
- **Squad management** — see each team's purchased players
- **SQLite database** — no server setup needed
- **Public URL** — share via Cloudflare Tunnel (free, secure HTTPS)
- **Single file deployment** — one Python file, one HTML file

## 🚀 Quick Start

### One-Command Setup

```bash
git clone https://github.com/yourusername/cricket-auction.git
cd cricket-auction
chmod +x install_and_run.sh
./install_and_run.sh
```

That's it! The script will:
1. Create a Python virtual environment
2. Install dependencies
3. Download Cloudflare Tunnel (for public URL)
4. Start the server
5. Display the public URL to share with teams

### Manual Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/cricket-auction.git
cd cricket-auction

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

## 🔐 Login Credentials

| Role | Username | Password |
|------|----------|----------|
| 🔴 Royal Strikers | `team1` | `strike1` |
| 🔵 Thunder Kings | `team2` | `thunder2` |
| 🟢 Super Chargers | `team3` | `charge3` |
| 🟡 Fire Eagles | `team4` | `eagle4` |
| 👑 Admin (Auctioneer) | `admin` | `admin123` |

> ⚠️ **Change these passwords** in `main.py` before your actual auction!

## 📦 Player Pools

Players are organized into 4 pools for structured bidding:

| Pool | Icon | Description |
|------|------|-------------|
| Marquee | ⭐ | Top premium players (highest base prices) |
| Batsman | 🏏 | Specialist batsmen |
| Bowler | 🎯 | Specialist bowlers |
| All-Rounder | 💪 | All-rounders and Wicket-keepers |

Admin can switch between pools during the auction.

## 🎮 How to Use

### For the Auctioneer (Admin):
1. Open the app and login as `admin`
2. Select a **pool** (start with Marquee)
3. Click **"Next Player"** to put a player on the block
4. Wait for teams to bid
5. Click **"SOLD"** when bidding stops, or **"Unsold"** if no bids
6. Repeat until all players are auctioned

### For Teams:
1. Open the shared URL on your phone/laptop
2. Login with your team credentials
3. When a player is on the block, click **"BID +50"** to place a bid
4. Watch your budget and squad in real-time

## 🌐 Network Options

### Option 1: Mobile Hotspot (Recommended for universities)
If your university network blocks tunnels:
1. Turn on your phone's mobile hotspot
2. Connect your laptop + all team devices to the hotspot
3. Run the server and share your local IP: `http://192.168.x.x:8000`

### Option 2: Cloudflare Tunnel (Public Internet)
The install script automatically sets up a secure HTTPS tunnel:
```
https://random-words.trycloudflare.com
```

### Option 3: Local Network (Same WiFi)
If everyone is on the same network:
```bash
hostname -I  # Get your IP
# Share: http://YOUR_IP:8000
```

## 📁 Project Structure

```
cricket-auction/
├── install_and_run.sh   # One-click setup script
├── main.py              # FastAPI backend (single file)
├── players.csv          # Player data (60 players)
├── requirements.txt     # Python dependencies
├── README.md            # This file
├── LICENSE              # MIT License
├── .gitignore           # Git ignore rules
└── static/
    └── index.html       # Frontend (single file)
```

## ⚙️ Configuration

Edit `main.py` to customize:

```python
# Team settings
TEAMS = {
    "team1": {"name": "Royal Strikers", "password": "strike1", "color": "#e63946"},
    "team2": {"name": "Thunder Kings", "password": "thunder2", "color": "#457b9d"},
    # ... add more teams
}

# Budget and bidding
TOTAL_BUDGET = 5000      # Each team's starting budget
BID_INCREMENT = 50       # Minimum bid increment

# Admin password
ADMIN_PASSWORD = "admin123"
```

## 📋 Customizing Players

Edit `players.csv` to add your own players:

```csv
name,role,base_price,pool
John Doe,Batsman,200,Marquee
Jane Smith,Bowler,150,Bowler
```

**Pools:** `Marquee`, `Batsman`, `Bowler`, `All-Rounder`
**Roles:** `Batsman`, `Bowler`, `All-Rounder`, `Wicket-Keeper`

## 🔧 Troubleshooting

### "Address already in use" error
```bash
pkill -f "python3 main.py"
```

### Database reset
```bash
rm auction.db*
python main.py  # Will recreate from players.csv
```

### Tunnel not working
- Try mobile hotspot instead
- Check if your network blocks outbound connections

## 🛠️ Tech Stack

- **Backend:** Python 3.8+ with FastAPI
- **Frontend:** Vanilla HTML/CSS/JavaScript
- **Database:** SQLite (file-based, no setup)
- **Real-time:** WebSockets
- **Tunnel:** Cloudflare Tunnel (cloudflared)

## 📄 License

MIT License - feel free to use for your university tournaments!

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- Built for university cricket tournaments
- Inspired by IPL auction format
- Thanks to FastAPI and Cloudflare for awesome free tools

---

Made with ❤️ for cricket lovers
