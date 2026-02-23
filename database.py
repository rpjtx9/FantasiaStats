import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/fantasia.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_players INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            job INTEGER NOT NULL,
            level INTEGER NOT NULL,
            experience INTEGER NOT NULL,
            fame INTEGER NOT NULL,
            quests INTEGER NOT NULL,
            cards INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        );

        CREATE TABLE IF NOT EXISTS player_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            exp_gained INTEGER NOT NULL,
            leveled_up INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        );

        CREATE INDEX IF NOT EXISTS idx_players_snapshot ON players(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
        CREATE INDEX IF NOT EXISTS idx_activity_snapshot ON player_activity(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_activity_name ON player_activity(name);
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")

def insert_snapshot(timestamp, total_players):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO snapshots (timestamp, total_players) VALUES (?, ?)",
        (timestamp, total_players)
    )
    snapshot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return snapshot_id

def insert_players(snapshot_id, players):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO players (snapshot_id, name, job, level, experience, fame, quests, cards, rank)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(snapshot_id, p["name"], p["job"], p["level"], p["experience"],
          p["fame"], p["quests"], p["cards"], p["rank"]) for p in players]
    )
    conn.commit()
    conn.close()

def insert_activity(snapshot_id, activity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany(
        """INSERT INTO player_activity (snapshot_id, name, exp_gained, leveled_up)
           VALUES (?, ?, ?, ?)""",
        [(snapshot_id, p["name"], p["exp_gained"], 1 if p["level"] > 0 else 0)
         for p in activity]
    )
    conn.commit()
    conn.close()

def get_snapshot_by_timestamp(timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snapshots WHERE timestamp = ?", (timestamp,))
    row = cursor.fetchone()
    conn.close()
    return row

def snapshot_exists(timestamp):
    return get_snapshot_by_timestamp(timestamp) is not None

def ingest_snapshot(timestamp, players, activity=None):
    if snapshot_exists(timestamp):
        print(f"Snapshot {timestamp} already exists in database, skipping.")
        return

    snapshot_id = insert_snapshot(timestamp, len(players))
    insert_players(snapshot_id, players)

    if activity:
        insert_activity(snapshot_id, activity["active_players"])

    print(f"Ingested snapshot {timestamp} — {len(players)} players.")
    return snapshot_id

def get_snapshot_closest_to_hours_ago(hours):
    from datetime import datetime, timedelta
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    latest_ts = datetime.strptime(latest["timestamp"], "%Y-%m-%d_%H-%M-%S")
    target_ts = latest_ts - timedelta(hours=hours)

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    fmt = "%Y-%m-%d_%H-%M-%S"
    closest = min(rows, key=lambda r: abs(
        (datetime.strptime(r["timestamp"], fmt) - target_ts).total_seconds()
    ))
    return closest