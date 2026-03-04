import matplotlib.pyplot as plt
from pathlib import Path
from database import get_connection
from analyze import JOB_NAMES
import numpy as np
from analyze import JOB_LEVEL_FLOORS
from datetime import datetime, timedelta
from analyze import calculate_exp_gained
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from analyze import exp_to_level_percent

ICON_DIR = Path("data/icons")

def get_class_icon(class_name, zoom=0.3):
    path = ICON_DIR / f"{class_name.lower()}.png"
    if not path.exists():
        return None
    img = mpimg.imread(str(path))
    return OffsetImage(img, zoom=zoom)

CLASS_GROUPS = {
    "Beginner": [0],
    "Warrior": [100, 110, 111, 112, 120, 121, 122, 130, 131, 132],
    "Magician": [200, 210, 211, 212, 220, 221, 222, 230, 231, 232],
    "Archer": [300, 310, 311, 312, 320, 321, 322],
    "Thief": [400, 410, 411, 412, 420, 421, 422],
    "Pirate": [500, 510, 511, 512, 520, 521, 522],
}
CLASS_BRANCHES = {
    "Beginner": [[0]],
    "Warrior": [
        [100],
        [110, 111, 112],
        [120, 121, 122],
        [130, 131, 132],
    ],
    "Magician": [
        [200],
        [210, 211, 212],
        [220, 221, 222],
        [230, 231, 232],
    ],
    "Archer": [
        [300],
        [310, 311, 312],
        [320, 321, 322],
    ],
    "Thief": [
        [400],
        [410, 411, 412],
        [420, 421, 422],
    ],
    "Pirate": [
        [500],
        [510, 511, 512],
        [520, 521, 522],
    ],
}

# Class accent colors - themed per class
CLASS_COLORS = {
    "Beginner": ["#607375"],
    "Warrior": [
        "#aa1111",                        # Warrior base - dark red
        "#ff4444", "#ff8800", "#ffcc00",  # Fighter branch - red to yellow
        "#cc44ff", "#8800ff", "#4400cc",  # Page branch - purples
        "#ff44aa", "#cc0055", "#880033",  # Spearman branch - pinks
    ],
    "Magician": [
        "#7722bb",                        # Magician base - dark purple
        "#ff6600", "#ff0000", "#880000",  # Fire/Poison branch - oranges/reds
        "#44aaff", "#0066ff", "#0033cc",  # Ice/Lightning branch - blues
        "#ffffff", "#cccccc", "#999999",  # Cleric branch - whites/greys
    ],
    "Archer": [
        "#00aa44",                        # Archer base - dark green
        "#33ff77", "#00cc44", "#008833",  # Hunter branch - bright greens
        "#ffff44", "#cccc00", "#888800",  # Crossbow branch - yellows
    ],
    "Thief": [
        "#1144aa",                        # Thief base - dark blue
        "#4488ff", "#0044cc", "#002288",  # Assassin branch - blues
        "#ff8844", "#cc4400", "#882200",  # Bandit branch - oranges
    ],
    "Pirate": [
        "#cc7700",                        # Pirate base - dark gold
        "#ffdd00", "#ff4400", "#880000",   # Brawler branch - gold, pink, purple
        "#00ffee", "#0088ff", "#cc00ff",  # Gunslinger branch - teal, blue, purple
    ],
}

SUBPLOT_BACKGROUNDS = ["#16213e", "#0d1b2a", "#1a1a2e", "#0f2537"]

DARK_STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#0f3460",
    "axes.labelcolor": "#e0e0e0",
    "axes.titlecolor": "#ffffff",
    "axes.grid": False,
    "grid.color": "#0f3460",
    "grid.linewidth": 0.5,
    "xtick.color": "#e0e0e0",
    "ytick.color": "#e0e0e0",
    "text.color": "#e0e0e0",
    "axes.spines.top": False,
    "axes.spines.right": False,
}

FS = {
    "title": 22,
    "subtitle": 13,
    "axis_label": 11,
    "tick": 9,
    "bar_label": 9,
    "legend": 9,
    "stats": 13,
    "subtitle" : 10
}

BASE_OUTPUT_DIR = Path("data/charts")

def get_output_dir(snapshot_id=None):
    if snapshot_id is None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        timestamp = row["timestamp"]
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM snapshots WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()
        conn.close()
        timestamp = row["timestamp"]
    
    path = BASE_OUTPUT_DIR / timestamp
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_latest_snapshot_id():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM snapshots")
    snapshot_id = cursor.fetchone()[0]
    conn.close()
    return snapshot_id

def add_stats_box(ax, buckets):
    total = sum(buckets.values())
    weighted_sum = 0
    for label, count in buckets.items():
        parts = label.split("-")
        midpoint = int(parts[0]) if len(parts) == 1 else (int(parts[0]) + int(parts[1])) / 2
        weighted_sum += midpoint * count
    avg_level = round(weighted_sum / total, 1) if total > 0 else 0

    text = f"Total: {total}\nAvg Level: {avg_level}"
    ax.text(0.98, 0.98, text,
            transform=ax.transAxes,
            fontsize=7,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f3460",
                      edgecolor="#e0e0e0", alpha=0.9),
            color="#ffffff")

def plot_level_distribution(snapshot_id=None):
    if snapshot_id is None:
        snapshot_id = get_latest_snapshot_id()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM players WHERE snapshot_id = ?", (snapshot_id,))
    levels = [row[0] for row in cursor.fetchall()]
    conn.close()

    buckets = {}
    for level in levels:
        bucket = ((level - 1) // 10) * 10 + 1
        label = f"{bucket}-{bucket + 9}"
        buckets[label] = buckets.get(label, 0) + 1

    sorted_buckets = sorted(buckets.items(), key=lambda x: int(x[0].split("-")[0]))
    labels = [b[0] for b in sorted_buckets]
    counts = [b[1] for b in sorted_buckets]

    with plt.rc_context(DARK_STYLE):
        fig, ax = plt.subplots(figsize=(16, 6))
        fig.suptitle("Player Level Distribution", fontsize=FS["title"],
                     fontweight="bold", color="#ffffff")

        bars = ax.bar(labels, counts, color="#3498db", edgecolor="#1a1a2e", linewidth=0.5)
        ax.grid(False)

        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    str(count), ha="center", va="bottom",
                    fontsize=FS["bar_label"], color="#ffffff")

        ax.set_xlabel("Level Range", fontsize=FS["axis_label"])
        ax.set_ylabel("Number of Players", fontsize=FS["axis_label"])
        ax.tick_params(axis="x", rotation=45, labelsize=FS["tick"])
        ax.tick_params(axis="y", labelsize=FS["tick"])

        plt.tight_layout()
        output_dir = get_output_dir(snapshot_id)
        path = output_dir / "level_distribution.png"
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        plt.close()
        print(f"Saved: {path}")


def plot_level_distribution_by_class(snapshot_id=None):
    if snapshot_id is None:
        snapshot_id = get_latest_snapshot_id()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT job, level FROM players WHERE snapshot_id = ?", (snapshot_id,))
    players = [dict(row) for row in cursor.fetchall()]
    conn.close()

    output_dir = get_output_dir(snapshot_id)

    for class_name, branches in CLASS_BRANCHES.items():
        with plt.rc_context(DARK_STYLE):
            n_subplots = len(branches)
            fig, axes = plt.subplots(1, n_subplots, figsize=(n_subplots * 6, 6))
            axes = np.array(axes).flatten()

            fig.suptitle(f"{class_name} Level Distribution",
                         fontsize=FS["title"], fontweight="bold", color="#ffffff", y=1.02)

            branch_colors = CLASS_COLORS.get(class_name, ["#e0e0e0", "#b0b0b0", "#808080"])

            for subplot_idx, branch_ids in enumerate(branches):
                ax = axes[subplot_idx]
                ax.grid(False)

                if subplot_idx == 0:
                    colors = [branch_colors[0]]
                else:
                    start = 1 + (subplot_idx - 1) * 3
                    colors = branch_colors[start:start + 3]

                subplot_bg = ["#16213e", "#0d1b2a", "#1a1a2e", "#0f2537"]
                ax.set_facecolor(subplot_bg[subplot_idx % len(subplot_bg)])

                all_labels = set()
                branch_data = {}

                for job_id in branch_ids:
                    job_name = JOB_NAMES.get(job_id)
                    floor = JOB_LEVEL_FLOORS.get(job_id, 1)
                    job_players = [p for p in players if p["job"] == job_id]
                    buckets = {}

                    for p in job_players:
                        if p["level"] < floor:
                            continue
                        if p["level"] == floor:
                            label = str(floor)
                        else:
                            bucket = ((p["level"] - floor - 1) // 10) * 10 + floor + 1
                            label = f"{bucket}-{bucket + 9}"
                        buckets[label] = buckets.get(label, 0) + 1

                    branch_data[job_name] = buckets
                    all_labels.update(buckets.keys())

                combined_counts = {}
                for buckets in branch_data.values():
                    for label, count in buckets.items():
                        combined_counts[label] = combined_counts.get(label, 0) + count
                add_stats_box(ax, combined_counts)

                sorted_labels = sorted(all_labels, key=lambda x: int(x.split("-")[0]))
                n_jobs = len(branch_ids)
                x = np.arange(len(sorted_labels))
                width = 0.8 / n_jobs

                for i, (job_name, buckets) in enumerate(branch_data.items()):
                    counts = [buckets.get(label, 0) for label in sorted_labels]
                    offset = (i - n_jobs / 2 + 0.5) * width
                    bar_color = colors[i % len(colors)]
                    bars = ax.bar(x + offset, counts, width=width,
                                  label=job_name, color=bar_color,
                                  edgecolor="#1a1a2e", linewidth=0.5)

                    for bar, count in zip(bars, counts):
                        if count > 0:
                            ax.text(bar.get_x() + bar.get_width() / 2,
                                    bar.get_height() + 0.3,
                                    str(count), ha="center", va="bottom",
                                    fontsize=FS["bar_label"], color="#ffffff")

                branch_title = " / ".join([JOB_NAMES.get(j, "") for j in branch_ids])
                ax.set_title(branch_title, fontsize=FS["subtitle"], fontweight="bold",
             wrap=True, pad=10)
                ax.set_xlabel("Level Range", fontsize=FS["axis_label"])
                ax.set_ylabel("Players", fontsize=FS["axis_label"])
                ax.set_xticks(x)
                ax.set_xticklabels(sorted_labels, rotation=45, ha="right", fontsize=FS["tick"])
                ax.tick_params(axis="y", labelsize=FS["tick"])
                ax.legend(fontsize=FS["legend"], facecolor="#0f3460", edgecolor="#0f3460",
                          labelcolor="#e0e0e0")

            plt.tight_layout()
            path = output_dir / f"level_distribution_{class_name.lower()}.png"
            plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
            plt.close()
            print(f"Saved: {path}")

def plot_activity_card(hours=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
    latest = dict(cursor.fetchone())
    latest_id, latest_ts = latest["id"], latest["timestamp"]

    if hours:
        from database import get_snapshot_closest_to_hours_ago
        prev = get_snapshot_closest_to_hours_ago(hours)
    else:
        cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 2")
        rows = cursor.fetchall()
        if len(rows) < 2:
            print("Need at least two snapshots.")
            conn.close()
            return
        prev = dict(rows[1])

    prev_id, prev_ts = prev["id"], prev["timestamp"]

    fmt = "%Y-%m-%d_%H-%M-%S"
    delta = datetime.strptime(latest_ts, fmt) - datetime.strptime(prev_ts, fmt)
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60

    latest_dt = datetime.strptime(latest_ts, fmt)
    utc_dt = latest_dt + timedelta(hours=6)
    formatted_ts = utc_dt.strftime("%B %d %Y %H:%M UTC")

    cursor.execute("""
        SELECT pa.name, SUM(pa.exp_gained) as exp_gained, p.job, p.level
        FROM player_activity pa
        JOIN players p ON p.snapshot_id = (SELECT MAX(id) FROM snapshots)
            AND p.name = pa.name
        WHERE pa.snapshot_id IN (
            SELECT id FROM snapshots WHERE id > ? AND id <= ?
        )
        GROUP BY pa.name
        ORDER BY exp_gained DESC
    """, (prev_id, latest_id))
    active_players = [dict(row) for row in cursor.fetchall()]

    class_job_ids = {
        "Beginner": [0],
        "Warrior": [100, 110, 111, 112, 120, 121, 122, 130, 131, 132],
        "Magician": [200, 210, 211, 212, 220, 221, 222, 230, 231, 232],
        "Archer": [300, 310, 311, 312, 320, 321, 322],
        "Thief": [400, 410, 411, 412, 420, 421, 422],
        "Pirate": [500, 510, 511, 512, 520, 521, 522],
    }
    active_by_class = {cls: sum(1 for p in active_players if p["job"] in ids)
                       for cls, ids in class_job_ids.items()}

    tier_job_map = {
        "Beginner": [0],
        "1st Job": [100, 200, 300, 400, 500],
        "2nd Job": [110, 120, 130, 210, 220, 230, 310, 320, 410, 420, 510, 520],
        "3rd Job": [111, 121, 131, 211, 221, 231, 311, 321, 411, 421, 511, 521],
        "4th Job": [112, 122, 132, 212, 222, 232, 312, 322, 412, 422, 512, 522],
    }
    active_by_tier = {tier: sum(1 for p in active_players if p["job"] in ids)
                      for tier, ids in tier_job_map.items()}

    cursor.execute("""
        SELECT p.name, p.job, p.level
        FROM players p
        WHERE p.snapshot_id = ?
        AND p.name NOT IN (SELECT name FROM players WHERE snapshot_id = ?)
    """, (latest_id, prev_id))
    new_players = [dict(row) for row in cursor.fetchall()]
    conn.close()

    new_by_class = {cls: sum(1 for p in new_players if p["job"] in ids)
                    for cls, ids in class_job_ids.items()}
    new_by_tier = {tier: sum(1 for p in new_players if p["job"] in ids)
                   for tier, ids in tier_job_map.items()}

    def get_class_for_job(job_id):
        for cls, ids in class_job_ids.items():
            if job_id in ids:
                return cls
        return None

    TIER_JOB_IDS = {
        "1st Job": [100, 200, 300, 400, 500],
        "2nd Job": [110, 120, 130, 210, 220, 230, 310, 320, 410, 420, 510, 520],
        "3rd Job": [111, 121, 131, 211, 221, 231, 311, 321, 411, 421, 511, 521],
        "4th Job": [112, 122, 132, 212, 222, 232, 312, 322, 412, 422, 512, 522],
    }

    TIER_COLORS = {
        "1st Job": "#aaaaaa",
        "2nd Job": "#3498db",
        "3rd Job": "#9b59b6",
        "4th Job": "#f1c40f",
    }

    fig = plt.figure(figsize=(18, 6), facecolor="#1a1a2e")

    fig.text(0.5, 0.97, "Activity Summary",
             ha="center", va="top", fontsize=FS["title"],
             fontweight="bold", color="#ffffff")
    fig.text(0.5, 0.91, f"Last {hours}h {minutes}m  |  {formatted_ts}",
             ha="center", va="top", fontsize=FS["axis_label"], color="#aaaaaa")

    # summary bar
    summary_ax = fig.add_axes([0.02, 0.68, 0.96, 0.18])
    summary_ax.set_facecolor("#16213e")
    summary_ax.set_xticks([])
    summary_ax.set_yticks([])
    summary_ax.set_xlim(0, 1)
    summary_ax.set_ylim(0, 1)
    for spine in summary_ax.spines.values():
        spine.set_edgecolor("#0f3460")

    # row 1 - totals
    summary_ax.text(0.20, 0.82, f"Active Players: {len(active_players)}",
                    transform=summary_ax.transAxes, fontsize=FS["subtitle"],
                    fontweight="bold", color="#2ecc71", va="center", ha="center")
    summary_ax.text(0.75, 0.82, f"New Players: {len(new_players)}",
                    transform=summary_ax.transAxes, fontsize=FS["subtitle"],
                    fontweight="bold", color="#3498db", va="center", ha="center")

    # row 2 - icons + class counts
    active_class_items = [(cls, count) for cls, count in active_by_class.items() if count > 0]
    n_active = len(active_class_items)
    for idx, (cls, count) in enumerate(active_class_items):
        x_pos = 0.05 + idx * (0.35 / max(n_active, 1))
        icon = get_class_icon(cls, zoom=0.22)
        if icon:
            ab = AnnotationBbox(icon, (x_pos, 0.52),
                                xycoords="axes fraction",
                                frameon=False, box_alignment=(0.5, 0.5))
            summary_ax.add_artist(ab)
        summary_ax.text(x_pos, 0.18, f"{cls}: {count}",
                        transform=summary_ax.transAxes, fontsize=FS["tick"],
                        color="#2ecc71", va="center", ha="center", fontweight="bold")

    new_class_items = [(cls, count) for cls, count in new_by_class.items() if count > 0]
    n_new = len(new_class_items)
    for idx, (cls, count) in enumerate(new_class_items):
        x_pos = 0.62 + idx * (0.35 / max(n_new, 1))
        icon = get_class_icon(cls, zoom=0.22)
        if icon:
            ab = AnnotationBbox(icon, (x_pos, 0.52),
                                xycoords="axes fraction",
                                frameon=False, box_alignment=(0.5, 0.5))
            summary_ax.add_artist(ab)
        summary_ax.text(x_pos, 0.18, f"{cls}: {count}",
                        transform=summary_ax.transAxes, fontsize=FS["tick"],
                        color="#3498db", va="center", ha="center", fontweight="bold")

    # four tier panels
    col_width = 0.225
    col_gap = 0.012
    panel_bottom = 0.02
    panel_height = 0.64

    for tier_idx, (tier_label, tier_job_ids) in enumerate(TIER_JOB_IDS.items()):
        left = 0.03 + tier_idx * (col_width + col_gap)
        tier_color = TIER_COLORS[tier_label]

        ax = fig.add_axes([left, panel_bottom, col_width, panel_height])
        ax.set_facecolor("#16213e")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#0f3460")

        ax.text(0.5, 0.97, tier_label,
                transform=ax.transAxes, fontsize=FS["title"],
                fontweight="bold", color=tier_color,
                ha="center", va="top")

        tier_players = [p for p in active_players if p["job"] in tier_job_ids][:5]

        if not tier_players:
            ax.text(0.5, 0.5, "No activity", transform=ax.transAxes,
                    fontsize=FS["tick"], color="#555555", ha="center", va="center")
        else:
            for rank, player in enumerate(tier_players):
                job_name = JOB_NAMES.get(player["job"], "?")
                exp_str = f"{player['exp_gained']:,}"
                y = 0.85 - rank * 0.15
                level_pct = exp_to_level_percent(player["exp_gained"], player.get("level", 1))
                ax.text(0.97, y - 0.035, f"{level_pct}%",
                        transform=ax.transAxes, fontsize=7,
                        color="#27ae60", va="center", ha="right")


                ax.text(0.03, y, f"{rank + 1}. {player['name']}",
                        transform=ax.transAxes, fontsize=FS["subtitle"],
                        color="#ffffff", va="center", fontweight="bold")
                ax.text(0.03, y - 0.035, f"Lv.{player['level']} {job_name}",
                        transform=ax.transAxes, fontsize=FS["tick"],
                        color="#aaaaaa", va="center")

                # icon between name and exp
                cls = get_class_for_job(player["job"])
                icon = get_class_icon(cls, zoom=0.18) if cls else None
                if icon:
                    ab = AnnotationBbox(icon, (0.60, y - 0.01),
                                        xycoords="axes fraction",
                                        frameon=False, box_alignment=(0.5, 0.5))
                    ax.add_artist(ab)

                ax.text(0.97, y, f"+{exp_str}",
                        transform=ax.transAxes, fontsize=FS["subtitle"],
                        color="#2ecc71", va="center", ha="right")


    output_dir = get_output_dir()
    path = output_dir / "activity_card.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    print(f"Saved: {path}")

def plot_player_scorecard(name, hours=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.timestamp, p.level, p.experience, p.rank, p.fame, p.quests, p.cards, p.job
        FROM players p
        JOIN snapshots s ON p.snapshot_id = s.id
        WHERE p.name = ?
        ORDER BY s.timestamp
    """, (name,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    fmt = "%Y-%m-%d_%H-%M-%S"
    if not rows:
        print(f"No data found for player '{name}'.")
        return
    if hours:
        cutoff = datetime.now() - timedelta(hours=hours)
        rows = [r for r in rows if datetime.strptime(r["timestamp"], fmt) >= cutoff]
    
    if not rows:
        print(f"No data found for '{name}' in the last {hours} hours.")
        return


    timestamps = [datetime.strptime(r["timestamp"], fmt) for r in rows]
    levels = [r["level"] for r in rows]
    experiences = [r["experience"] for r in rows]
    ranks = [r["rank"] for r in rows]
    latest = rows[-1]
    first = rows[0]
    job_name = JOB_NAMES.get(latest["job"], "Unknown")

    # exp gained per snapshot
    exp_gains = [0] + [calculate_exp_gained(rows[i], rows[i-1]) for i in range(1, len(rows))]

    fig = plt.figure(figsize=(18, 12), facecolor="#1a1a2e")

    # title
    fig.text(0.5, 0.96, f"{name}",
             ha="center", va="top", fontsize=FS["title"],
             fontweight="bold", color="#ffffff")
    fig.text(0.5, 0.91, f"{job_name}  |  Level {latest['level']}  |  Rank #{latest['rank']}",
             ha="center", va="top", fontsize=FS["axis_label"], color="#aaaaaa")

    # --- stats box ---
    stats_ax = fig.add_axes([0.02, 0.82, 0.96, 0.07])
    stats_ax.set_facecolor("#16213e")
    stats_ax.set_xticks([])
    stats_ax.set_yticks([])
    for spine in stats_ax.spines.values():
        spine.set_edgecolor("#0f3460")

    total_exp_gained = sum(calculate_exp_gained(rows[i], rows[i-1]) for i in range(1, len(rows)))
    total_levels_gained = levels[-1] - levels[0]
    first_seen = timestamps[0].strftime("%B %d %Y")
    days_tracked = (timestamps[-1] - timestamps[0]).days

    prev = rows[-2] if len(rows) >= 2 else None

    def change_indicator(current, previous, key):
        if previous is None:
            return ""
        diff = current[key] - previous[key]
        if diff > 0:
            return f" ▲{diff}"
        return ""

    stats = [
        ("First Seen", first_seen),
        ("Days Tracked", str(days_tracked)),
        ("Levels Gained", str(total_levels_gained)),
        ("Total Exp Gained", f"{total_exp_gained:,}"),
        ("Fame", f"{latest['fame']}{change_indicator(latest, prev, 'fame')}"),
        ("Quests", f"{latest['quests']}{change_indicator(latest, prev, 'quests')}"),
        ("Cards", f"{latest['cards']}{change_indicator(latest, prev, 'cards')}"),
    ]

    for i, (label, value) in enumerate(stats):
        x = 0.02 + i * 0.14
        value_color = "#2ecc71" if "▲" in value else "#ffffff"
        stats_ax.text(x, 0.7, label, transform=stats_ax.transAxes,
                      fontsize=7, color="#aaaaaa", va="center", fontweight="bold")
        stats_ax.text(x, 0.25, value, transform=stats_ax.transAxes,
                    fontsize=FS["tick"], color=value_color, va="center", fontweight="bold")

    # --- level progression chart ---
    with plt.rc_context(DARK_STYLE):
        level_ax = fig.add_axes([0.05, 0.47, 0.55, 0.28])
        level_ax.set_facecolor("#16213e")
        level_ax.grid(False)
        level_ax.plot(timestamps, levels, color="#3498db", linewidth=2, marker="o", markersize=3)
        level_ax.fill_between(timestamps, levels, alpha=0.15, color="#3498db")
        level_ax.set_title("Level Progression", fontsize=FS["subtitle"],
                           fontweight="bold", color="#ffffff")
        level_ax.set_ylabel("Level", fontsize=FS["tick"], color="#aaaaaa")
        # fix level chart y-axis to start near the player's min level
        level_ax.set_ylim(min(levels) - 5, max(levels) + 5)
        level_ax.tick_params(axis="x", rotation=45, labelsize=7, colors="#aaaaaa")
        level_ax.tick_params(axis="y", labelsize=7, colors="#aaaaaa")
        for spine in level_ax.spines.values():
            spine.set_edgecolor("#0f3460")

        # --- exp gained per snapshot chart ---
        exp_ax = fig.add_axes([0.05, 0.08, 0.55, 0.28])
        exp_ax.set_facecolor("#16213e")
        exp_ax.grid(False)
        time_range = timestamps[-1] - timestamps[0]
        bar_width = time_range / (len(timestamps) * 2)
        exp_ax.bar(timestamps, exp_gains, color="#2ecc71", edgecolor="#1a1a2e",
                linewidth=0.5, width=bar_width)
        exp_ax.set_title("Exp Gained Per Snapshot", fontsize=FS["subtitle"],
                         fontweight="bold", color="#ffffff")
        exp_ax.set_ylabel("Exp Gained", fontsize=FS["tick"], color="#aaaaaa")
        exp_ax.tick_params(axis="x", rotation=45, labelsize=7, colors="#aaaaaa")
        exp_ax.tick_params(axis="y", labelsize=7, colors="#aaaaaa")
        for spine in exp_ax.spines.values():
            spine.set_edgecolor("#0f3460")

        # --- rank progression chart ---
        rank_ax = fig.add_axes([0.63, 0.08, 0.35, 0.67])
        rank_ax.set_facecolor("#16213e")
        rank_ax.grid(False)
        rank_ax.plot(timestamps, ranks, color="#f1c40f", linewidth=2, marker="o", markersize=3)
        rank_ax.fill_between(timestamps, ranks, alpha=0.15, color="#f1c40f")
        rank_ax.invert_yaxis()  # lower rank number = better
        rank_ax.set_title("Rank Progression", fontsize=FS["subtitle"],
                          fontweight="bold", color="#ffffff")
        rank_ax.set_ylabel("Rank", fontsize=FS["tick"], color="#aaaaaa")
        rank_ax.tick_params(axis="x", rotation=45, labelsize=7, colors="#aaaaaa")
        rank_ax.tick_params(axis="y", labelsize=7, colors="#aaaaaa")
        for spine in rank_ax.spines.values():
            spine.set_edgecolor("#0f3460")

    output_dir = BASE_OUTPUT_DIR / "players"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"player_{name}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    print(f"Saved: {path}")
def plot_server_health():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.timestamp, s.total_players,
               COUNT(pa.name) as active_count
        FROM snapshots s
        LEFT JOIN player_activity pa ON pa.snapshot_id = s.id
        WHERE s.id > (SELECT MIN(id) FROM snapshots)
        GROUP BY s.id
        ORDER BY s.timestamp
    """)
    rows_active = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT s.timestamp, s.total_players
        FROM snapshots s
        ORDER BY s.timestamp
    """)
    rows_total = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if len(rows_total) < 2:
        print("Need at least two snapshots for server health chart.")
        return

    fmt = "%Y-%m-%d_%H-%M-%S"
    timestamps_total  = [datetime.strptime(r["timestamp"], fmt) for r in rows_total]
    total_players     = [r["total_players"] for r in rows_total]
    timestamps_active = [datetime.strptime(r["timestamp"], fmt) for r in rows_active]
    active_counts     = [r["active_count"] for r in rows_active]

    with plt.rc_context(DARK_STYLE):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8))
        fig.suptitle("Server Health", fontsize=FS["title"],
                     fontweight="bold", color="#ffffff")

        # total players
        ax1.set_facecolor("#16213e")
        ax1.grid(False)
        ax1.plot(timestamps_total, total_players, color="#3498db", linewidth=2,
                 marker="o", markersize=4)
        ax1.fill_between(timestamps_total, total_players, alpha=0.15, color="#3498db")
        ax1.set_title("Total Players", fontsize=FS["subtitle"],
                      fontweight="bold", color="#ffffff")
        ax1.set_ylabel("Players", fontsize=FS["tick"], color="#aaaaaa")
        ax1.tick_params(axis="x", rotation=45, labelsize=FS["tick"], colors="#aaaaaa")
        ax1.tick_params(axis="y", labelsize=FS["tick"], colors="#aaaaaa")
        for spine in ax1.spines.values():
            spine.set_edgecolor("#0f3460")
        ax1.set_ylim(min(total_players) * 0.99, max(total_players) * 1.01)

        # active players per snapshot
        ax2.set_facecolor("#16213e")
        ax2.grid(False)
        ax2.plot(timestamps_active, active_counts, color="#2ecc71", linewidth=2,
                 marker="o", markersize=4)
        ax2.fill_between(timestamps_active, active_counts, alpha=0.15, color="#2ecc71")
        ax2.set_title("Active Players Per Snapshot", fontsize=FS["subtitle"],
                      fontweight="bold", color="#ffffff")
        ax2.set_ylabel("Active Players", fontsize=FS["tick"], color="#aaaaaa")
        ax2.tick_params(axis="x", rotation=45, labelsize=FS["tick"], colors="#aaaaaa")
        ax2.tick_params(axis="y", labelsize=FS["tick"], colors="#aaaaaa")
        for spine in ax2.spines.values():
            spine.set_edgecolor("#0f3460")

        plt.tight_layout()
        output_dir = BASE_OUTPUT_DIR / "server_health"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"server_health_{datetime.now().strftime('%Y-%m-%d')}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        plt.close()
        print(f"Saved: {path}")
def plot_retention():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    snapshots = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if len(snapshots) < 2:
        print("Need at least two snapshots for retention analysis.")
        return

    fmt = "%Y-%m-%d_%H-%M-%S"

    # assign each snapshot to a week number relative to the first snapshot
    first_ts = datetime.strptime(snapshots[0]["timestamp"], fmt)
    for s in snapshots:
        ts = datetime.strptime(s["timestamp"], fmt)
        s["week"] = (ts - first_ts).days // 7

    # get all players per snapshot
    conn = get_connection()
    cursor = conn.cursor()
    snapshot_players = {}
    for s in snapshots:
        cursor.execute("SELECT DISTINCT name FROM players WHERE snapshot_id = ?", (s["id"],))
        snapshot_players[s["id"]] = set(row[0] for row in cursor.fetchall())
    conn.close()

    # build cohorts — players first seen each week
    weeks = sorted(set(s["week"] for s in snapshots))
    cohorts = {}
    seen_players = set()

    for week in weeks:
        week_snapshots = [s for s in snapshots if s["week"] == week]
        week_players = set()
        for s in week_snapshots:
            week_players.update(snapshot_players[s["id"]])
        new_players = week_players - seen_players
        cohorts[week] = new_players
        seen_players.update(new_players)

    # calculate retention per cohort per subsequent week
    retention_data = {}
    for cohort_week, cohort_players in cohorts.items():
        if not cohort_players:
            continue
        retention_data[cohort_week] = {}
        for week in weeks:
            if week < cohort_week:
                continue
            week_snapshots = [s for s in snapshots if s["week"] == week]
            week_players = set()
            for s in week_snapshots:
                week_players.update(snapshot_players[s["id"]])
            pct = round(len(cohort_players & week_players) / len(cohort_players) * 100, 1)
            retention_data[cohort_week][week - cohort_week] = pct

    if not retention_data:
        print("Not enough data for retention analysis.")
        return

    # build matrix for heatmap
    max_weeks = max(max(v.keys()) for v in retention_data.values()) + 1
    cohort_weeks = sorted(retention_data.keys())
    matrix = np.full((len(cohort_weeks), max_weeks), np.nan)

    for i, cohort_week in enumerate(cohort_weeks):
        for week_offset, pct in retention_data[cohort_week].items():
            matrix[i, week_offset] = pct

    with plt.rc_context(DARK_STYLE):
        fig, ax = plt.subplots(figsize=(max(10, max_weeks * 1.5), max(6, len(cohort_weeks) * 1.2)))
        fig.suptitle("Player Retention by Cohort", fontsize=FS["title"],
                     fontweight="bold", color="#ffffff")

        masked = np.ma.masked_invalid(matrix)
        cmap = plt.cm.RdYlGn
        cmap.set_bad(color="#16213e")
        im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=0, vmax=100)

        # cell labels
        for i in range(len(cohort_weeks)):
            for j in range(max_weeks):
                if not np.isnan(matrix[i, j]):
                    ax.text(j, i, f"{matrix[i, j]:.0f}%",
                            ha="center", va="center",
                            fontsize=FS["tick"], fontweight="bold",
                            color="black" if matrix[i, j] > 50 else "white")

        ax.set_xticks(range(max_weeks))
        ax.set_xticklabels([f"Wk {i}" for i in range(max_weeks)],
                           fontsize=FS["tick"], color="#aaaaaa")
        ax.set_yticks(range(len(cohort_weeks)))
        ax.set_yticklabels([f"Week {w+1} Cohort" for w in cohort_weeks],
                           fontsize=FS["tick"], color="#aaaaaa")

        plt.colorbar(im, ax=ax, label="Retention %")
        ax.set_facecolor("#16213e")
        for spine in ax.spines.values():
            spine.set_edgecolor("#0f3460")

        plt.tight_layout()

        output_dir = BASE_OUTPUT_DIR / "retention"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"retention_{datetime.now().strftime('%Y-%m-%d')}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        plt.close()
        print(f"Saved: {path}")
    
def plot_guild_card(hours=None):
    GUILD_NAME = "Classic"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM guilds WHERE name = ?", (GUILD_NAME,))
    guild_row = cursor.fetchone()
    if not guild_row:
        print(f"Guild '{GUILD_NAME}' not found in database.")
        conn.close()
        return
    guild_id = guild_row[0]
    cursor.execute("SELECT player_name FROM guild_members WHERE guild_id = ?", (guild_id,))
    MEMBERS = [r[0] for r in cursor.fetchall()]
    if not MEMBERS:
        print(f"Guild '{GUILD_NAME}' has no members.")
        conn.close()
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
    latest = dict(cursor.fetchone())
    latest_id, latest_ts = latest["id"], latest["timestamp"]

    if hours:
        from database import get_snapshot_closest_to_hours_ago
        prev = get_snapshot_closest_to_hours_ago(hours)
    else:
        cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 2")
        rows = cursor.fetchall()
        if len(rows) < 2:
            print("Need at least two snapshots.")
            conn.close()
            return
        prev = dict(rows[1])

    prev_id, prev_ts = prev["id"], prev["timestamp"]

    fmt = "%Y-%m-%d_%H-%M-%S"
    delta = datetime.strptime(latest_ts, fmt) - datetime.strptime(prev_ts, fmt)
    total_hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    utc_dt = datetime.strptime(latest_ts, fmt) + timedelta(hours=6)
    formatted_ts = utc_dt.strftime("%B %d %Y %H:%M UTC")

    placeholders = ",".join("?" * len(MEMBERS))

    # exp gained - sum across all snapshots in window
    cursor.execute(f"""
        SELECT pa.name, SUM(pa.exp_gained) as exp_gained
        FROM player_activity pa
        WHERE pa.name IN ({placeholders})
        AND pa.snapshot_id IN (
            SELECT id FROM snapshots WHERE id > ? AND id <= ?
        )
        GROUP BY pa.name
        ORDER BY exp_gained DESC
        LIMIT 10
    """, (*MEMBERS, prev_id, latest_id))
    top_exp = [dict(row) for row in cursor.fetchall()]

    # quests, cards, level delta between latest and prev snapshots
    cursor.execute(f"""
        SELECT p_new.name,
               p_new.quests - p_old.quests as quest_delta,
               p_new.cards  - p_old.cards  as card_delta,
               p_new.level  - p_old.level  as level_delta,
               p_new.level, p_new.job
        FROM players p_new
        JOIN players p_old ON p_old.name = p_new.name AND p_old.snapshot_id = ?
        WHERE p_new.snapshot_id = ?
        AND p_new.name IN ({placeholders})
    """, (prev_id, latest_id, *MEMBERS))
    member_rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    member_lookup = {r["name"]: r for r in member_rows}

    top_quests = sorted([r for r in member_rows if r["quest_delta"] > 0],
                        key=lambda x: x["quest_delta"], reverse=True)[:10]
    top_cards  = sorted([r for r in member_rows if r["card_delta"] > 0],
                        key=lambda x: x["card_delta"], reverse=True)[:10]
    top_levels = sorted([r for r in member_rows if r["level_delta"] > 0],
                        key=lambda x: x["level_delta"], reverse=True)[:10]

    # attach job/level/level_delta to exp rows
    for row in top_exp:
        info = member_lookup.get(row["name"], {})
        row["level"]       = info.get("level", "?")
        row["job"]         = info.get("job", 0)
        row["level_delta"] = info.get("level_delta", 0)

    CLASS_JOB_IDS = {
        "Beginner": [0],
        "Warrior":  [100,110,111,112,120,121,122,130,131,132],
        "Magician": [200,210,211,212,220,221,222,230,231,232],
        "Archer":   [300,310,311,312,320,321,322],
        "Thief":    [400,410,411,412,420,421,422],
        "Pirate":   [500,510,511,512,520,521,522],
    }

    def get_class_for_job(job_id):
        for cls, ids in CLASS_JOB_IDS.items():
            if job_id in ids:
                return cls
        return None

    fig = plt.figure(figsize=(24, 8), facecolor="#1a1a2e")

    fig.text(0.5, 0.97, f"Guild: {GUILD_NAME}",
             ha="center", va="top", fontsize=FS["title"],
             fontweight="bold", color="#ffffff")
    fig.text(0.5, 0.91, f"Last {total_hours}h {minutes}m  |  {formatted_ts}",
             ha="center", va="top", fontsize=FS["axis_label"], color="#aaaaaa")

    col_configs = [
        ("Exp Gained", top_exp,    "exp_gained",  "#2ecc71", lambda v: f"+{v:,}"),
        ("Levels",     top_levels, "level_delta", "#e74c3c", lambda v: f"+{v}"),
        ("Quests",     top_quests, "quest_delta", "#3498db", lambda v: f"+{v}"),
        ("Cards",      top_cards,  "card_delta",  "#f1c40f", lambda v: f"+{v}"),
    ]

    col_width = 0.21
    col_gap   = 0.02
    panel_h   = 0.82

    for col_idx, (title, players, key, color, fmt_val) in enumerate(col_configs):
        left = 0.03 + col_idx * (col_width + col_gap)
        ax = fig.add_axes([left, 0.04, col_width, panel_h])
        ax.set_facecolor("#16213e")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#0f3460")

        ax.text(0.5, 0.97, title, transform=ax.transAxes,
                fontsize=FS["title"], fontweight="bold",
                color=color, ha="center", va="top")

        if not players:
            ax.text(0.5, 0.5, "No activity", transform=ax.transAxes,
                    fontsize=FS["tick"], color="#555555", ha="center", va="center")
            continue

        for rank, player in enumerate(players):
            job_name = JOB_NAMES.get(player.get("job", 0), "?")
            y = 0.88 - rank * 0.082

            cls = get_class_for_job(player.get("job", 0))
            icon = get_class_icon(cls, zoom=0.18) if cls else None
            if icon:
                ab = AnnotationBbox(icon, (0.08, y),
                                    xycoords="axes fraction",
                                    frameon=False, box_alignment=(0.5, 0.5))
                ax.add_artist(ab)

            ax.text(0.18, y + 0.015, f"{rank+1}. {player['name']}",
                    transform=ax.transAxes, fontsize=FS["subtitle"],
                    color="#ffffff", va="center", fontweight="bold")
            ax.text(0.18, y - 0.022, f"Lv.{player.get('level','?')} {job_name}",
                    transform=ax.transAxes, fontsize=FS["tick"],
                    color="#aaaaaa", va="center")
            ax.text(0.97, y, fmt_val(player[key]),
                    transform=ax.transAxes, fontsize=FS["subtitle"],
                    color=color, va="center", ha="right")

            if key == "exp_gained":
                level_pct = exp_to_level_percent(player["exp_gained"], player.get("level", 1))
                ax.text(0.97, y - 0.028, f"{level_pct}%",
                        transform=ax.transAxes, fontsize=7,
                        color="#27ae60", va="center", ha="right")

    output_dir = BASE_OUTPUT_DIR / "guild"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"guild_{datetime.now().strftime('%Y-%m-%d')}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    print(f"Saved: {path}")

def plot_active_player_distribution(hours=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
    latest = dict(cursor.fetchone())
    latest_id, latest_ts = latest["id"], latest["timestamp"]

    if hours:
        from database import get_snapshot_closest_to_hours_ago
        prev = get_snapshot_closest_to_hours_ago(hours)
    else:
        cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 2")
        rows = cursor.fetchall()
        if len(rows) < 2:
            print("Need at least two snapshots.")
            conn.close()
            return
        prev = dict(rows[1])

    prev_id = prev["id"]

    # get active players with their level and job from latest snapshot
    cursor.execute("""
        SELECT p.level, p.job
        FROM players p
        JOIN player_activity pa ON pa.name = p.name
        WHERE p.snapshot_id = ?
        AND pa.snapshot_id IN (
            SELECT id FROM snapshots WHERE id > ? AND id <= ?
        )
        GROUP BY p.name
    """, (latest_id, prev_id, latest_id))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not rows:
        print("No active player data found.")
        return

    CLASS_JOB_IDS = {
        "Beginner": [0],
        "Warrior":  [100,110,111,112,120,121,122,130,131,132],
        "Magician": [200,210,211,212,220,221,222,230,231,232],
        "Archer":   [300,310,311,312,320,321,322],
        "Thief":    [400,410,411,412,420,421,422],
        "Pirate":   [500,510,511,512,520,521,522],
    }
    CLASS_COLOR_MAP = {
        "Beginner": "#95a5a6",
        "Warrior":  "#ff4444",
        "Magician": "#bb44ff",
        "Archer":   "#33ff77",
        "Thief":    "#2913ee",
        "Pirate":   "#ffaa00",
    }

    def get_class(job_id):
        for cls, ids in CLASS_JOB_IDS.items():
            if job_id in ids:
                return cls
        return "Beginner"

    # bucket into 10-level ranges
    bucket_data = {}
    for r in rows:
        level = r["level"]
        cls = get_class(r["job"])
        bucket = ((level - 1) // 10) * 10 + 1
        label = f"{bucket}-{bucket+9}"
        if label not in bucket_data:
            bucket_data[label] = {c: 0 for c in CLASS_JOB_IDS}
        bucket_data[label][cls] += 1

    sorted_labels = sorted(bucket_data.keys(), key=lambda x: int(x.split("-")[0]))

    with plt.rc_context(DARK_STYLE):
        fig, ax = plt.subplots(figsize=(16, 6))
        fig.suptitle("Active Player Level Distribution", fontsize=FS["title"],
                     fontweight="bold", color="#ffffff")

        bottoms = [0] * len(sorted_labels)
        for cls, color in CLASS_COLOR_MAP.items():
            counts = [bucket_data[label][cls] for label in sorted_labels]
            bars = ax.bar(sorted_labels, counts, bottom=bottoms,
                          color=color, edgecolor="#1a1a2e", linewidth=0.5,
                          label=cls)
            bottoms = [b + c for b, c in zip(bottoms, counts)]

        # total labels on top of each bar
        for i, total in enumerate(bottoms):
            if total > 0:
                ax.text(i, total + 0.3, str(total),
                        ha="center", va="bottom",
                        fontsize=FS["bar_label"], color="#ffffff")

        ax.set_xlabel("Level Range", fontsize=FS["axis_label"])
        ax.set_ylabel("Active Players", fontsize=FS["axis_label"])
        ax.tick_params(axis="x", rotation=45, labelsize=FS["tick"])
        ax.tick_params(axis="y", labelsize=FS["tick"])
        ax.legend(fontsize=FS["legend"], labelcolor="#ffffff",
                  facecolor="#0f3460", edgecolor="#0f3460")
        ax.grid(False)

        plt.tight_layout()
        output_dir = get_output_dir()
        path = output_dir / "active_distribution.png"
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
        plt.close()
        print(f"Saved: {path}")