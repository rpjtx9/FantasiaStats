# Fantasia MapleStory Analytics

A data pipeline for tracking and visualizing player statistics on the [Fantasia](https://fantasia.ms) MapleStory private server.

---

## Setup

1. Install dependencies: `pip install requests matplotlib numpy pillow`
2. Place class icons in `data/icons/` (beginner, warrior, magician, archer, thief, pirate as PNG)
3. Edit `guild.py` to set your guild name and member list
4. Run `python main.py --fetch` to collect your first snapshot

---

## Usage

All commands are run via `main.py`.

```
python main.py [options]
```

### Arguments

| Argument | Description |
|---|---|
| `--fetch` | Fetch current rankings from the Fantasia API and save a JSON snapshot |
| `--analyze` | Process the latest snapshot into the database |
| `--backfill` | Reprocess all saved JSON snapshots into the database from scratch |
| `--visualize` | Generate all charts from the current database |
| `--all` | Run fetch, analyze, and visualize in sequence |
| `--hours N` | When used with `--visualize` or `--all`, compare against the snapshot closest to N hours ago instead of the previous snapshot |

### Examples

```bash
# Collect a new snapshot and generate all charts
python main.py --all

# Generate charts comparing the last 24 hours of activity
python main.py --visualize --hours 24

# Rebuild database from scratch after code changes
python main.py --backfill

# View a specific player's progression scorecard
python query.py --player Lide

# View a player's activity over the last 12 hours
python query.py --player Lide --hours 12

# Print top 10 players by exp gained
python query.py --top 10
```

---

## Charts Generated

All charts are saved under `data/charts/`. Most are saved in a timestamped subfolder matching the latest snapshot, so each run produces its own archive.

### Activity Summary (`activity_card.png`)
A dashboard showing active and new players since the last snapshot (or `--hours` window). Displays class icons, class breakdowns, and top 5 players per job tier (1st/2nd/3rd/4th Job) with exp gained.

### Guild Card (`guild/guild_YYYY-MM-DD.png`)
Top 10 guild members ranked by exp gained, levels gained, quests completed, and cards collected over the comparison window. Guild members are defined in `guild.py`.

### Active Player Distribution (`active_distribution.png`)
Stacked bar chart showing level distribution of active players, color-coded by class (Warrior, Magician, Archer, Thief, Pirate, Beginner).

### Level Distribution (`level_distribution.png`)
Overall level distribution of all ranked players in 10-level buckets.

### Level Distribution by Class (`level_distribution_*.png`)
One chart per class showing advancement progression across branches (e.g. Fighter/Crusader/Hero for Warriors).

### Server Health (`server_health/server_health_YYYY-MM-DD.png`)
Two line charts tracking total player count and active players per snapshot over time. Useful for spotting server growth trends and peak activity times.

### Player Scorecard (`players/player_NAME.png`)
Individual player progression showing level history, exp gained per snapshot, and rank progression over time. Generated via `query.py --player`.

### Retention Heatmap (`retention/retention_YYYY-MM-DD.png`)
Weekly cohort retention analysis. Shows what percentage of players first seen in a given week are still active in subsequent weeks. Requires multiple weeks of data to be meaningful.

---

## Project Structure

```
FantasiaRankingsData/
├── main.py          # Entry point - CLI arguments
├── fetch.py         # API calls, saves JSON snapshots
├── analyze.py       # Job definitions, exp table, exp calculations
├── database.py      # SQLite operations
├── query.py         # Player lookup and CLI queries
├── visualize.py     # All chart generation functions
├── guild.py         # Guild name and member list
└── data/
    ├── snapshots/   # Raw JSON snapshots (rankings_YYYY-MM-DD_HH-MM-SS.json)
    ├── icons/       # Class icons (beginner/warrior/magician/archer/thief/pirate.png)
    ├── charts/      # Generated charts
    │   ├── YYYY-MM-DD_HH-MM-SS/   # Per-snapshot chart archives
    │   ├── players/                # Individual player scorecards
    │   ├── guild/                  # Daily guild cards
    │   ├── server_health/          # Daily server health charts
    │   └── retention/              # Weekly retention heatmaps
    └── fantasia.db  # SQLite database
```

---

## Automation

The project is designed to run automatically via Windows Task Scheduler. Recommended schedule:

- **Midnight UTC** (6 PM local CST): `python main.py --all --hours 24`
- **Noon UTC** (6 AM local CST): `python main.py --all --hours 12`

Working directory should be set to the project root (`F:\Documents\Projects\FantasiaRankingsData`).

---

## Database Schema

**snapshots** — one row per fetch
- `id`, `timestamp`, `total_players`

**players** — all ranked players per snapshot
- `id`, `snapshot_id`, `name`, `job`, `level`, `experience`, `fame`, `quests`, `cards`, `rank`

**player_activity** — exp gained between snapshots
- `id`, `snapshot_id`, `name`, `exp_gained`, `leveled_up`
