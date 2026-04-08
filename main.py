"""
IPL-Style Cricket Auction App
Single-file FastAPI backend with SQLite + WebSockets
"""

import csv
import json
import os
import sqlite3
import asyncio
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ──────────────────── CONFIG ────────────────────
DB_FILE = "auction.db"
CSV_FILE = "players.csv"
TOTAL_BUDGET = 5000  # Each team gets 5000 points

TEAMS = {
    "team1": {"name": "Royal Strikers", "password": "strike1", "color": "#e63946"},
    "team2": {"name": "Thunder Kings", "password": "thunder2", "color": "#457b9d"},
    "team3": {"name": "Super Chargers", "password": "charge3", "color": "#2a9d8f"},
    "team4": {"name": "Fire Eagles", "password": "eagle4", "color": "#e9c46a"},
}

ADMIN_PASSWORD = "admin123"
BID_INCREMENT = 50  # Minimum bid increment

# ──────────────────── DATABASE ────────────────────


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables and load players from CSV."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                base_price INTEGER NOT NULL,
                pool TEXT NOT NULL DEFAULT 'Marquee',
                sold_to TEXT DEFAULT NULL,
                sold_price INTEGER DEFAULT 0,
                status TEXT DEFAULT 'upcoming'
            );
            CREATE TABLE IF NOT EXISTS teams (
                team_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                budget INTEGER NOT NULL,
                color TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auction_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        # Check if already loaded
        count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        if count == 0:
            csv_path = Path(CSV_FILE)
            if csv_path.exists():
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pool = row.get("pool", "Marquee")
                        conn.execute(
                            "INSERT INTO players (name, role, base_price, pool) VALUES (?, ?, ?, ?)",
                            (row["name"], row["role"], int(
                                row["base_price"]), pool),
                        )
                print(f"✅ Loaded {CSV_FILE} into database")
            else:
                print(
                    f"⚠️  {CSV_FILE} not found — add players via admin or re-create it")

        # Init teams
        for tid, info in TEAMS.items():
            conn.execute(
                "INSERT OR IGNORE INTO teams (team_id, name, budget, color) VALUES (?, ?, ?, ?)",
                (tid, info["name"], TOTAL_BUDGET, info["color"]),
            )

        # Init auction state
        conn.execute(
            "INSERT OR IGNORE INTO auction_state (key, value) VALUES ('current_player_id', '')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO auction_state (key, value) VALUES ('current_bid', '0')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO auction_state (key, value) VALUES ('current_bidder', '')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO auction_state (key, value) VALUES ('auction_status', 'waiting')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO auction_state (key, value) VALUES ('current_pool', 'Marquee')"
        )
    print("✅ Database ready")


def get_state(key):
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM auction_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def set_state(key, value):
    with get_db() as conn:
        conn.execute(
            "UPDATE auction_state SET value=? WHERE key=?", (str(value), key))


# ──────────────────── FASTAPI APP ────────────────────

app = FastAPI(title="Cricket Auction")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ──────────── WebSocket Manager ────────────

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)


manager = ConnectionManager()


# ──────────── Helper: Build full state snapshot ────────────

def build_snapshot() -> dict:
    with get_db() as conn:
        current_id = get_state("current_player_id")
        current_player = None
        if current_id:
            row = conn.execute(
                "SELECT * FROM players WHERE id=?", (current_id,)).fetchone()
            if row:
                current_player = dict(row)

        teams = []
        for tid, info in TEAMS.items():
            t = conn.execute(
                "SELECT * FROM teams WHERE team_id=?", (tid,)).fetchone()
            squad = conn.execute(
                "SELECT id, name, role, sold_price FROM players WHERE sold_to=?", (
                    tid,)
            ).fetchall()
            teams.append({
                "team_id": tid,
                "name": t["name"],
                "budget": t["budget"],
                "color": t["color"],
                "squad": [dict(p) for p in squad],
                "squad_count": len(squad),
            })

        upcoming = conn.execute(
            "SELECT COUNT(*) FROM players WHERE status='upcoming'"
        ).fetchone()[0]
        sold = conn.execute(
            "SELECT COUNT(*) FROM players WHERE status='sold'"
        ).fetchone()[0]
        unsold = conn.execute(
            "SELECT COUNT(*) FROM players WHERE status='unsold'"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]

        # Pool stats
        current_pool = get_state("current_pool") or "Marquee"
        pools = ["Marquee", "Batsman", "Bowler", "All-Rounder"]
        pool_stats = {}
        for pool in pools:
            pool_upcoming = conn.execute(
                "SELECT COUNT(*) FROM players WHERE status='upcoming' AND pool=?", (pool,)
            ).fetchone()[0]
            pool_sold = conn.execute(
                "SELECT COUNT(*) FROM players WHERE status='sold' AND pool=?", (pool,)
            ).fetchone()[0]
            pool_total = conn.execute(
                "SELECT COUNT(*) FROM players WHERE pool=?", (pool,)
            ).fetchone()[0]
            pool_stats[pool] = {"upcoming": pool_upcoming,
                                "sold": pool_sold, "total": pool_total}

    return {
        "type": "state",
        "current_player": current_player,
        "current_bid": int(get_state("current_bid") or 0),
        "current_bidder": get_state("current_bidder") or "",
        "auction_status": get_state("auction_status"),
        "current_pool": current_pool,
        "pools": pools,
        "pool_stats": pool_stats,
        "teams": teams,
        "stats": {
            "total": total,
            "upcoming": upcoming,
            "sold": sold,
            "unsold": unsold,
        },
    }


# ──────────── REST Endpoints ────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    role = data.get("role")
    password = data.get("password")

    if role == "admin":
        if password == ADMIN_PASSWORD:
            return {"ok": True, "role": "admin", "name": "Auctioneer"}
        raise HTTPException(401, "Wrong admin password")

    team = TEAMS.get(role)
    if team and team["password"] == password:
        return {"ok": True, "role": role, "name": team["name"]}
    raise HTTPException(401, "Wrong team password")


@app.get("/api/state")
async def api_state():
    return build_snapshot()


@app.get("/api/players")
async def api_players():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM players ORDER BY pool, id").fetchall()
        return [dict(r) for r in rows]


# ──────────── Admin Actions ────────────

@app.post("/api/admin/set_pool")
async def admin_set_pool(request: Request):
    """Switch to a different player pool."""
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(401, "Unauthorized")

    pool = data.get("pool")
    valid_pools = ["Marquee", "Batsman", "Bowler", "All-Rounder"]
    if pool not in valid_pools:
        return {"ok": False, "msg": f"Invalid pool. Choose from: {valid_pools}"}

    set_state("current_pool", pool)
    await manager.broadcast(build_snapshot())
    return {"ok": True, "pool": pool}


@app.post("/api/admin/next")
async def admin_next(request: Request):
    """Put the next upcoming player on the block."""
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(401, "Unauthorized")

    current_pool = get_state("current_pool") or "Marquee"

    with get_db() as conn:
        player = conn.execute(
            "SELECT * FROM players WHERE status='upcoming' AND pool=? ORDER BY id LIMIT 1",
            (current_pool,)
        ).fetchone()
        if not player:
            return {"ok": False, "msg": f"No more players in {current_pool} pool"}

        set_state("current_player_id", player["id"])
        set_state("current_bid", player["base_price"])
        set_state("current_bidder", "")
        set_state("auction_status", "bidding")

        conn.execute(
            "UPDATE players SET status='bidding' WHERE id=?", (player["id"],))

    await manager.broadcast(build_snapshot())
    return {"ok": True, "player": player["name"]}


@app.post("/api/admin/sold")
async def admin_sold(request: Request):
    """Mark current player as SOLD to highest bidder."""
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(401, "Unauthorized")

    pid = get_state("current_player_id")
    bidder = get_state("current_bidder")
    bid = int(get_state("current_bid") or 0)

    if not pid or not bidder:
        return {"ok": False, "msg": "No active bid to confirm"}

    with get_db() as conn:
        conn.execute(
            "UPDATE players SET status='sold', sold_to=?, sold_price=? WHERE id=?",
            (bidder, bid, pid),
        )
        conn.execute(
            "UPDATE teams SET budget = budget - ? WHERE team_id=?", (bid,
                                                                     bidder)
        )

    set_state("auction_status", "sold")
    set_state("current_player_id", "")
    set_state("current_bidder", "")
    set_state("current_bid", "0")

    await manager.broadcast(build_snapshot())
    return {"ok": True}


@app.post("/api/admin/unsold")
async def admin_unsold(request: Request):
    """Mark current player as UNSOLD."""
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(401, "Unauthorized")

    pid = get_state("current_player_id")
    if not pid:
        return {"ok": False, "msg": "No player on block"}

    with get_db() as conn:
        conn.execute("UPDATE players SET status='unsold' WHERE id=?", (pid,))

    set_state("auction_status", "unsold")
    set_state("current_player_id", "")
    set_state("current_bidder", "")
    set_state("current_bid", "0")

    await manager.broadcast(build_snapshot())
    return {"ok": True}


@app.post("/api/admin/reset")
async def admin_reset(request: Request):
    """Full reset — re-load players, reset budgets."""
    data = await request.json()
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(401, "Unauthorized")

    with get_db() as conn:
        conn.execute("DELETE FROM players")
        conn.execute("DELETE FROM teams")
        conn.execute("DELETE FROM auction_state")

    init_db()
    set_state("auction_status", "waiting")

    await manager.broadcast(build_snapshot())
    return {"ok": True, "msg": "Auction reset!"}


# ──────────── Team Bidding ────────────

@app.post("/api/bid")
async def place_bid(request: Request):
    data = await request.json()
    team_id = data.get("team_id")
    password = data.get("password")

    # Auth
    team_cfg = TEAMS.get(team_id)
    if not team_cfg or team_cfg["password"] != password:
        raise HTTPException(401, "Unauthorized")

    # Check auction is live
    if get_state("auction_status") != "bidding":
        return {"ok": False, "msg": "No active auction right now"}

    current_bid = int(get_state("current_bid") or 0)
    current_bidder = get_state("current_bidder")
    new_bid = current_bid + BID_INCREMENT

    # Can't bid against yourself
    if current_bidder == team_id:
        return {"ok": False, "msg": "You are already the highest bidder!"}

    # Budget check
    with get_db() as conn:
        team_row = conn.execute(
            "SELECT budget FROM teams WHERE team_id=?", (team_id,)
        ).fetchone()
        if team_row["budget"] < new_bid:
            return {"ok": False, "msg": "Not enough budget!"}

    set_state("current_bid", new_bid)
    set_state("current_bidder", team_id)

    await manager.broadcast(build_snapshot())
    return {"ok": True, "bid": new_bid}


# ──────────── WebSocket for live updates ────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send current state immediately on connect
        await ws.send_json(build_snapshot())
        while True:
            # Keep connection alive; ignore incoming data (bids go via REST)
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ──────────────────── STARTUP ────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    print()
    print("=" * 55)
    print("  🏏  CRICKET AUCTION SERVER RUNNING")
    print("=" * 55)
    print(f"  Local:  http://localhost:8000")
    print()
    print("  Team Logins:")
    for tid, info in TEAMS.items():
        print(
            f"    {info['name']:20s}  →  role: {tid}, pass: {info['password']}")
    print(f"    {'Admin':20s}  →  role: admin, pass: {ADMIN_PASSWORD}")
    print()
    print("  Waiting for ngrok tunnel... check your other terminal")
    print("=" * 55)
    print()


# ──────────────────── MAIN ────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
