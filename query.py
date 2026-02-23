import argparse
import json
from database import get_connection
from analyze import JOB_NAMES
from visualize import plot_player_scorecard
from datetime import datetime, timedelta
from analyze import calculate_exp_gained

def get_player_progression(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.timestamp, p.level, p.experience, p.rank, p.fame, p.quests, p.cards, p.job
        FROM players p
        JOIN snapshots s ON p.snapshot_id = s.id
        WHERE p.name = ?
        ORDER BY s.timestamp
    """, (name,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def print_player_progression(name, hours=None):
    rows = get_player_progression(name)
    
    if hours:
        cutoff = datetime.now() - timedelta(hours=hours)
        rows = [r for r in rows if datetime.strptime(r["timestamp"], "%Y-%m-%d_%H-%M-%S") >= cutoff]
    if not rows:
        print(f"No data found for player '{name}'.")
        return
    
    print(f"\n=== Progression for {name} ===")
    print(f"First seen: {rows[0]['timestamp']}")
    print(f"Latest: {rows[-1]['timestamp']}")
    print(f"Snapshots: {len(rows)}")
    print()
    
    prev = None
    for row in rows:
        exp_gained = calculate_exp_gained(row, prev) if prev else 0
        leveled_up = row["level"] > prev["level"] if prev else False
        job_name = JOB_NAMES.get(row.get("job"), "Unknown") if "job" in row.keys() else ""
        
        level_flag = " *** LEVEL UP ***" if leveled_up else ""
        exp_str = f"+{exp_gained:,}" if exp_gained > 0 else str(exp_gained)
        
        print(f"  {row['timestamp']}  |  Level {row['level']}{level_flag}")
        print(f"    Exp: {row['experience']:,} ({exp_str})  |  Rank: {row['rank']}  |  Fame: {row['fame']}")
        print()
        prev = row

def get_top_players(n):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pa.name, pa.exp_gained, p.level, p.job
        FROM player_activity pa
        JOIN snapshots s ON pa.snapshot_id = s.id
        JOIN players p ON p.snapshot_id = s.id AND p.name = pa.name
        WHERE s.id = (SELECT MAX(id) FROM snapshots)
        ORDER BY pa.exp_gained DESC
        LIMIT ?
    """, (n,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def print_top_players(n):
    rows = get_top_players(n)
    
    if not rows:
        print("No activity data found. Make sure you have at least two snapshots ingested.")
        return
    
    print(f"\n=== Top {n} Players by Exp Gained (Latest Snapshot) ===")
    for i, row in enumerate(rows, 1):
        job_name = JOB_NAMES.get(row["job"], f"Unknown ({row['job']})")
        print(f"  {i}. {row['name']} ({job_name}) - Level {row['level']} - {row['exp_gained']:,} exp gained")

def main():
    parser = argparse.ArgumentParser(description="Fantasia Rankings Query Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--player", type=str, help="Show progression for a specific player")
    group.add_argument("--top", type=int, help="Show top X players by exp gained in latest snapshot")
    parser.add_argument("--hours", type=int, default=None, help="Limit progression to last X hours")
    args = parser.parse_args()

    if args.player:
        print_player_progression(args.player, hours=args.hours)
        plot_player_scorecard(args.player, hours=args.hours)
    elif args.top:
        print_top_players(args.top, hours=args.hours)

if __name__ == "__main__":
    main()
