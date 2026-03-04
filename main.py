import argparse
import json
from datetime import datetime
from pathlib import Path
from fetch import fetch_all_players, save_snapshot, load_snapshot, get_latest_snapshots
from analyze import level_distribution, level_distribution_by_class_grouped, job_popularity, active_players, summary
from database import initialize_db, ingest_snapshot


def run_fetch():
    print("=== Fetching Rankings ===")
    players = fetch_all_players()
    filepath = save_snapshot(players)

    # extract timestamp from filename and ingest into db
    timestamp = filepath.stem.replace("rankings_", "")

    snapshots = get_latest_snapshots(2)
    activity = None
    if len(snapshots) == 2:
        today = load_snapshot(snapshots[0])
        yesterday = load_snapshot(snapshots[1])
        activity = active_players(today, yesterday)

    ingest_snapshot(timestamp, players, activity)

def run_analyze():
    print("=== Running Analysis ===")
    snapshots = get_latest_snapshots(2)

    if not snapshots:
        print("No snapshots found. Run with --fetch first.")
        return

    today = load_snapshot(snapshots[0])
    print(f"Snapshot: {snapshots[0].name}")

    print("\n--- Summary ---")
    print(json.dumps(summary(today), indent=2))

    print("\n--- Level Distribution ---")
    print(json.dumps(level_distribution(today), indent=2))

    print("\n--- Level Distribution by Class ---")
    print(json.dumps(level_distribution_by_class_grouped(today), indent=2))

    print("\n--- Job Popularity ---")
    print(json.dumps(job_popularity(today), indent=2))

    if len(snapshots) == 2:
        yesterday = load_snapshot(snapshots[1])
        print(f"Comparing against: {snapshots[1].name}")

        fmt = "%Y-%m-%d_%H-%M-%S"
        time_today = datetime.strptime(snapshots[0].stem.replace("rankings_", ""), fmt)
        time_yesterday = datetime.strptime(snapshots[1].stem.replace("rankings_", ""), fmt)
        delta = time_today - time_yesterday
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60

        print(f"\n--- Active Players (last {hours}h {minutes}m) ---")
        activity = active_players(today, yesterday)
        print(f"Active: {activity['active_count']}")
        print(f"New players: {activity['new_players_count']}")
        print(f"Top 10 by exp gained:")
        for p in activity["active_players"][:10]:
            print(f"  {p['name']} - {p['exp_gained']:,} exp gained")
    else:
        print("\nOnly one snapshot found, skipping activity comparison.")

def run_backfill():
    print("=== Backfilling Database from JSON Snapshots ===")
    snapshots = sorted(Path("data/snapshots").glob("rankings_*.json"))

    if not snapshots:
        print("No snapshots found.")
        return

    print(f"Found {len(snapshots)} snapshots.")

    for i, filepath in enumerate(snapshots):
        timestamp = filepath.stem.replace("rankings_", "")
        players = load_snapshot(filepath)

        # calculate activity by comparing to previous snapshot if available
        activity = None
        if i > 0:
            yesterday = load_snapshot(snapshots[i - 1])
            activity = active_players(players, yesterday)

        ingest_snapshot(timestamp, players, activity)

    print("Backfill complete.")

def main():
    initialize_db()

    parser = argparse.ArgumentParser(description="Fantasia Rankings Tool")
    parser.add_argument("--fetch", action="store_true", help="Fetch latest rankings and save snapshot")
    parser.add_argument("--analyze", action="store_true", help="Run analysis on latest snapshots")
    parser.add_argument("--all", action="store_true", help="Fetch and then analyze")
    parser.add_argument("--backfill", action="store_true", help="Ingest all existing JSON snapshots into the database")
    parser.add_argument("--hours", type=int, default=None, help="Compare against snapshot closest to X hours ago")
    args = parser.parse_args()

    if args.all:
        run_fetch()
        run_analyze()
    elif args.fetch:
        run_fetch()
    elif args.analyze:
        run_analyze()
    elif args.backfill:
        run_backfill()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()