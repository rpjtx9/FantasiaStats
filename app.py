"""
Fantasia Rankings Dashboard - Flask web server
Drop this file into your FantasiaRankingsData/ folder alongside database.py and analyze.py
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pathlib import Path
from datetime import datetime, timedelta
import os
import bcrypt

from analyze import (
    JOB_NAMES, JOB_LEVEL_FLOORS, CLASS_JOB_IDS, TIER_JOB_IDS,
    FANTASIA_EXP_TABLE, calculate_exp_gained, exp_to_level_percent,
    get_class_for_job,
)
from database import get_connection


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

TS_FMT = "%Y-%m-%d_%H-%M-%S"

def snapshot_closest_to(cursor, target_ts):
    """Return the snapshot nearest in time to target_ts (a datetime object)."""
    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return None
    return min(rows, key=lambda r: abs((datetime.strptime(r["timestamp"], TS_FMT) - target_ts).total_seconds()))

def get_snapshot_window(hours=None, start=None, end=None):
    """
    Returns (latest_snap, prev_snap) dicts.
    Priority: date range (start/end) > hours > default (last two snapshots).
    start/end are ISO date strings: "YYYY-MM-DD"
    """
    conn = get_connection()
    cursor = conn.cursor()

    if start and end:
        # end date: use end of that day (23:59:59)
        end_dt = datetime.strptime(end, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        latest = snapshot_closest_to(cursor, end_dt)
        prev = snapshot_closest_to(cursor, start_dt)
        conn.close()
        # ensure latest is actually after prev
        if latest["id"] <= prev["id"]:
            return prev, None
        return latest, prev
    elif hours:
        cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
        latest = dict(cursor.fetchone())
        latest_ts = datetime.strptime(latest["timestamp"], TS_FMT)
        target_ts = latest_ts - timedelta(hours=hours)
        prev = snapshot_closest_to(cursor, target_ts)
        conn.close()
        return latest, prev
    else:
        cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY id DESC LIMIT 2")
        rows = cursor.fetchall()
        conn.close()
        if len(rows) < 2:
            latest = dict(rows[0]) if rows else None
            return latest, None
        return dict(rows[0]), dict(rows[1])

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/icons/<filename>")
def serve_icon(filename):
    from flask import send_from_directory
    return send_from_directory(Path(os.environ.get("DATA_DIR", "data")) / "icons", filename)

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/guild")
def guild_page():
    return render_template("guild.html",
        session_guild_id=session.get("guild_id"),
        session_guild_name=session.get("guild_name"),
    )

@app.route("/player")
@app.route("/player/<n>")
def player_page(n=""):
    return render_template("player.html")

@app.route("/api/snapshot_range")
def api_snapshot_range():
    """Returns the earliest and latest snapshot dates for date picker bounds."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM snapshots")
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return jsonify({"error": "No snapshots"}), 400
    fmt_out = "%Y-%m-%d"
    return jsonify({
        "min": datetime.strptime(row[0], TS_FMT).strftime(fmt_out),
        "max": datetime.strptime(row[1], TS_FMT).strftime(fmt_out),
    })

@app.route("/api/level_distribution")
def api_level_distribution():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM snapshots")
    snapshot_id = cursor.fetchone()[0]
    cursor.execute("SELECT level FROM players WHERE snapshot_id = ?", (snapshot_id,))
    levels = [row[0] for row in cursor.fetchall()]
    conn.close()

    buckets = {}
    for level in levels:
        bucket = ((level - 1) // 10) * 10 + 1
        label = f"{bucket}–{bucket + 9}"
        buckets[label] = buckets.get(label, 0) + 1

    sorted_items = sorted(buckets.items(), key=lambda x: int(x[0].split("–")[0]))
    return jsonify({"labels": [x[0] for x in sorted_items], "counts": [x[1] for x in sorted_items]})

@app.route("/api/class_distribution")
def api_class_distribution():
    CLASS_BRANCHES_DIST = {
        "Warrior":  {"1st Job": [100], "Fighter": [110,111,112], "Page": [120,121,122], "Spearman": [130,131,132]},
        "Magician": {"1st Job": [200], "Fire/Poison": [210,211,212], "Ice/Lightning": [220,221,222], "Cleric": [230,231,232]},
        "Archer":   {"1st Job": [300], "Hunter": [310,311,312], "Crossbow": [320,321,322]},
        "Thief":    {"1st Job": [400], "Assassin": [410,411,412], "Bandit": [420,421,422]},
        "Pirate":   {"1st Job": [500], "Brawler": [510,511,512], "Gunslinger": [520,521,522]},
        "Beginner": {"Beginner": [0]},
    }

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM snapshots")
    snapshot_id = cursor.fetchone()[0]
    cursor.execute("""
        SELECT job, COUNT(*) as cnt FROM players
        WHERE snapshot_id = ?
        AND (job != 0 OR level >= 11)
        GROUP BY job
    """, (snapshot_id,))
    job_counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    result = {}
    for cls, branches in CLASS_BRANCHES_DIST.items():
        result[cls] = {}
        for branch_name, job_ids in branches.items():
            result[cls][branch_name] = sum(job_counts.get(j, 0) for j in job_ids)

    return jsonify(result)

@app.route("/api/activity")
def api_activity():
    hours = request.args.get("hours", type=int)
    start = request.args.get("start")
    end   = request.args.get("end")
    latest, prev = get_snapshot_window(hours=hours, start=start, end=end)
    if not prev:
        return jsonify({"error": "Need at least two snapshots"}), 400

    latest_id, latest_ts = latest["id"], latest["timestamp"]
    prev_id, prev_ts = prev["id"], prev["timestamp"]

    delta = datetime.strptime(latest_ts, TS_FMT) - datetime.strptime(prev_ts, TS_FMT)
    total_hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pa.name, SUM(pa.exp_gained) as exp_gained, p.job, p.level
        FROM player_activity pa
        JOIN players p ON p.snapshot_id = ? AND p.name = pa.name
        WHERE pa.snapshot_id IN (SELECT id FROM snapshots WHERE id > ? AND id <= ?)
        GROUP BY pa.name
        ORDER BY exp_gained DESC
    """, (latest_id, prev_id, latest_id))
    active = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT p.name, p.job, p.level
        FROM players p WHERE p.snapshot_id = ?
        AND p.name NOT IN (SELECT name FROM players WHERE snapshot_id = ?)
    """, (latest_id, prev_id))
    new_players = [dict(row) for row in cursor.fetchall()]

    conn.close()

    for p in active:
        p["job_name"] = JOB_NAMES.get(p["job"], "Unknown")
        p["class"] = get_class_for_job(p["job"])
        p["level_pct"] = exp_to_level_percent(p["exp_gained"], p["level"])

    class_counts = {cls: 0 for cls in CLASS_JOB_IDS}
    for p in active:
        class_counts[p["class"]] += 1

    tier_counts = {}
    for tier, ids in TIER_JOB_IDS.items():
        tier_counts[tier] = sum(1 for p in active if p["job"] in ids)

    new_class_counts = {cls: 0 for cls in CLASS_JOB_IDS}
    for p in new_players:
        new_class_counts[get_class_for_job(p["job"])] += 1

    top_by_tier = {}
    for tier, ids in TIER_JOB_IDS.items():
        top_by_tier[tier] = [p for p in active if p["job"] in ids][:5]

    return jsonify({
        "window_label": f"{total_hours}h {minutes}m",
        "snapshot_time": latest_ts,
        "active_count": len(active),
        "new_count": len(new_players),
        "class_counts": class_counts,
        "new_class_counts": new_class_counts,
        "tier_counts": tier_counts,
        "top_by_tier": top_by_tier,
        "new_players": [{"name": p["name"], "job_name": JOB_NAMES.get(p["job"], "?"), "level": p["level"], "class": get_class_for_job(p["job"])} for p in new_players[:10]],
    })

@app.route("/activity/jobs")
def activity_jobs_page():
    return render_template("activity_jobs.html")

@app.route("/api/active_class_distribution")
def api_active_class_distribution():
    """Branch-level breakdown of active players, mirroring /api/class_distribution."""
    hours = request.args.get("hours", type=int)
    start = request.args.get("start")
    end   = request.args.get("end")
    latest, prev = get_snapshot_window(hours=hours, start=start, end=end)
    if not prev:
        return jsonify({"error": "Need at least two snapshots"}), 400

    latest_id = latest["id"]
    prev_id = prev["id"]
    latest_ts = latest["timestamp"]
    prev_ts = prev["timestamp"]

    delta = datetime.strptime(latest_ts, TS_FMT) - datetime.strptime(prev_ts, TS_FMT)
    total_hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pa.name, SUM(pa.exp_gained) as exp_gained, p.job, p.level
        FROM player_activity pa
        JOIN players p ON p.snapshot_id = ? AND p.name = pa.name
        WHERE pa.snapshot_id IN (SELECT id FROM snapshots WHERE id > ? AND id <= ?)
        GROUP BY pa.name
        ORDER BY exp_gained DESC
    """, (latest_id, prev_id, latest_id))
    active = [dict(row) for row in cursor.fetchall()]
    conn.close()

    CLASS_BRANCHES_DIST = {
        "Warrior":  {"1st Job": [100], "Fighter": [110,111,112], "Page": [120,121,122], "Spearman": [130,131,132]},
        "Magician": {"1st Job": [200], "Fire/Poison": [210,211,212], "Ice/Lightning": [220,221,222], "Cleric": [230,231,232]},
        "Archer":   {"1st Job": [300], "Hunter": [310,311,312], "Crossbow": [320,321,322]},
        "Thief":    {"1st Job": [400], "Assassin": [410,411,412], "Bandit": [420,421,422]},
        "Pirate":   {"1st Job": [500], "Brawler": [510,511,512], "Gunslinger": [520,521,522]},
        "Beginner": {"Beginner": [0]},
    }

    # Count active players per job
    job_counts = {}
    for p in active:
        job_counts[p["job"]] = job_counts.get(p["job"], 0) + 1

    # Branch-level counts (same shape as /api/class_distribution)
    branch_counts = {}
    for cls, branches in CLASS_BRANCHES_DIST.items():
        branch_counts[cls] = {}
        for branch_name, job_ids in branches.items():
            branch_counts[cls][branch_name] = sum(job_counts.get(j, 0) for j in job_ids)

    # Per-job counts and top players per job for the drilldown
    job_details = {}
    for p in active:
        jid = p["job"]
        if jid not in job_details:
            job_details[jid] = {"count": 0, "players": []}
        job_details[jid]["count"] += 1
        if len(job_details[jid]["players"]) < 20:
            job_details[jid]["players"].append({
                "name": p["name"],
                "level": p["level"],
                "exp_gained": p["exp_gained"],
                "job_name": JOB_NAMES.get(jid, "Unknown"),
            })

    return jsonify({
        "window_label": f"{total_hours}h {minutes}m",
        "branches": branch_counts,
        "job_details": {str(k): v for k, v in job_details.items()},
        "total_active": len(active),
    })

@app.route("/api/server_health")
def api_server_health():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp, total_players FROM snapshots ORDER BY timestamp")
    total_rows = [dict(row) for row in cursor.fetchall()]

    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    all_snapshots = [dict(row) for row in cursor.fetchall()]

    # Group snapshots by logical day with 10-minute grace on each side of midnight
    days = {}
    for s in all_snapshots:
        ts = datetime.strptime(s["timestamp"], TS_FMT)
        # Shift timestamp forward by 10 minutes — anything within 10min of midnight
        # gets attributed to the following day
        logical_day = (ts + timedelta(minutes=10)).strftime("%Y-%m-%d")
        days.setdefault(logical_day, []).append(s)

    active_rows = []
    for day in sorted(days):
        if day >= today:
            continue
        day_snaps = days[day]
        min_id = day_snaps[0]["id"]
        max_id = day_snaps[-1]["id"]
        # The first snapshot in a day is the *baseline* — its player_activity
        # records belong to the previous period, but all subsequent snapshots
        # within (and up to the next day's baseline) represent this day's gains.
        # lower_id = day's first snap (baseline); upper_id = next day's first snap (next baseline)
        # Query: id > lower_id AND id <= upper_id captures exactly this day's activity.
        prev_snap = next((s for s in reversed(all_snapshots) if s["id"] < min_id), None)
        lower_id = min_id
        next_day = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        next_day_snaps = days.get(next_day, [])
        # Next day's first snap is that day's baseline — use it as our upper bound
        # so its activity isn't double-counted in our day
        upper_id = next_day_snaps[0]["id"] if next_day_snaps else max_id
        cursor.execute("""
            SELECT COUNT(DISTINCT pa.name) as cnt
            FROM player_activity pa
            WHERE pa.snapshot_id IN (
                SELECT id FROM snapshots WHERE id > ? AND id <= ?
            )
        """, (lower_id, upper_id))
        count = cursor.fetchone()["cnt"]
        if prev_snap is None:
            continue
        active_rows.append({"day": day, "active_count": count})
    conn.close()

    return jsonify({
        "total": [{
            "label": datetime.strptime(r["timestamp"], TS_FMT).strftime("%m/%d %H:%M"),
            "total_players": r["total_players"],
        } for r in total_rows],
        "active": [{
            "label": r["day"][5:],
            "active_count": r["active_count"],
        } for r in active_rows],
    })

@app.route("/api/active_distribution")
def api_active_distribution():
    hours = request.args.get("hours", type=int)
    start = request.args.get("start")
    end   = request.args.get("end")
    latest, prev = get_snapshot_window(hours=hours, start=start, end=end)
    if not prev:
        return jsonify({"error": "Need at least two snapshots"}), 400

    latest_id, prev_id = latest["id"], prev["id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.level, p.job
        FROM players p
        JOIN player_activity pa ON pa.name = p.name
        WHERE p.snapshot_id = ?
        AND pa.snapshot_id IN (SELECT id FROM snapshots WHERE id > ? AND id <= ?)
        GROUP BY p.name
    """, (latest_id, prev_id, latest_id))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    CLASS_COLORS = {
        "Beginner": "#95a5a6", "Warrior": "#ff4444", "Magician": "#bb44ff",
        "Archer": "#33ff77", "Thief": "#0044cc", "Pirate": "#ffaa00",
    }

    bucket_data = {}
    for r in rows:
        level, cls = r["level"], get_class_for_job(r["job"])
        bucket = ((level - 1) // 10) * 10 + 1
        label = f"{bucket}–{bucket+9}"
        if label not in bucket_data:
            bucket_data[label] = {c: 0 for c in CLASS_JOB_IDS}
        bucket_data[label][cls] += 1

    sorted_labels = sorted(bucket_data.keys(), key=lambda x: int(x.split("–")[0]))
    series = []
    for cls, color in CLASS_COLORS.items():
        series.append({
            "name": cls,
            "color": color,
            "data": [bucket_data[lbl][cls] for lbl in sorted_labels]
        })

    return jsonify({"labels": sorted_labels, "series": series})

@app.route("/api/retention")
def api_retention():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    snapshots = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if len(snapshots) < 2:
        return jsonify({"error": "Not enough data"}), 400

    first_ts = datetime.strptime(snapshots[0]["timestamp"], TS_FMT)
    now_ts   = datetime.strptime(snapshots[-1]["timestamp"], TS_FMT)
    for s in snapshots:
        ts = datetime.strptime(s["timestamp"], TS_FMT)
        s["week"] = (ts - first_ts).days // 7

    # A week is "complete" if its last snapshot is at least 7 days after its first snapshot,
    # or if it's not the current week (i.e. a newer week exists after it)
    weeks = sorted(set(s["week"] for s in snapshots))
    current_week = max(weeks)

    MIN_ACTIVE_EXP = 1265  # total exp to reach level 8

    def week_active_players(week):
        snap_ids = [s["id"] for s in snapshots if s["week"] == week]
        placeholders = ",".join("?" * len(snap_ids))
        conn2 = get_connection()
        cur2 = conn2.cursor()
        cur2.execute(f"""
            SELECT name, COUNT(*) as instances, SUM(exp_gained) as total_exp
            FROM player_activity
            WHERE snapshot_id IN ({placeholders}) AND exp_gained > 0
            GROUP BY name
            HAVING COUNT(*) >= 2 OR SUM(exp_gained) >= ?
        """, snap_ids + [MIN_ACTIVE_EXP])
        result = set(r[0] for r in cur2.fetchall())
        conn2.close()
        return result

    cohorts = {week: week_active_players(week) for week in weeks}

    # New active players = active this week but never seen active in any prior week
    seen_active = set()
    new_active = {}
    for week in weeks:
        new_active[week] = len(cohorts[week] - seen_active)
        seen_active.update(cohorts[week])

    retention_data = {}
    for cw, cp in cohorts.items():
        if not cp:
            continue
        retention_data[cw] = {}
        for week in weeks:
            if week < cw:
                continue
            # Skip the current (incomplete) week as a retention target,
            # except for offset 0 (the cohort's own week, always shown as 100%)
            if week == current_week and week != cw:
                continue
            wp = week_active_players(week)
            pct = round(len(cp & wp) / len(cp) * 100, 1)
            retention_data[cw][week - cw] = pct

    if not retention_data:
        return jsonify({"error": "Not enough data for retention"}), 400

    max_weeks = max(max(v.keys()) for v in retention_data.values()) + 1
    cohort_weeks = sorted(retention_data.keys())
    matrix = []
    for cw in cohort_weeks:
        row = []
        for wo in range(max_weeks):
            row.append(retention_data[cw].get(wo, None))
        matrix.append(row)

    return jsonify({
        "cohort_labels": [f"Week {w+1}" for w in cohort_weeks],
        "week_labels": [f"Wk {i}" for i in range(max_weeks)],
        "matrix": matrix,
        "cohort_sizes": [len(cohorts[w]) for w in cohort_weeks],
        "new_active_players": [new_active[w] for w in cohort_weeks],
    })

@app.route("/api/player/<name>")
def api_player(name):
    start = request.args.get("start")
    end   = request.args.get("end")
    hours = request.args.get("hours", type=int)

    conn = get_connection()
    cursor = conn.cursor()

    # Resolve canonical name (case-insensitive match)
    cursor.execute("SELECT DISTINCT name FROM players WHERE LOWER(name) = LOWER(?)", (name,))
    canonical = cursor.fetchone()
    if canonical:
        name = canonical[0]

    cursor.execute("""
        SELECT s.timestamp, p.level, p.experience, p.rank, p.fame, p.quests, p.cards, p.job
        FROM players p JOIN snapshots s ON p.snapshot_id = s.id
        WHERE p.name = ? ORDER BY s.timestamp
    """, (name,))
    rows = [dict(row) for row in cursor.fetchall()]

    # Find last snapshot where player had any exp activity (unfiltered)
    cursor.execute("""
        SELECT MAX(s.timestamp) as last_active
        FROM player_activity pa
        JOIN snapshots s ON pa.snapshot_id = s.id
        WHERE pa.name = ? AND pa.exp_gained > 0
    """, (name,))
    last_active_row = cursor.fetchone()
    last_active = last_active_row["last_active"] if last_active_row else None

    # Check if player is absent from the latest snapshot
    cursor.execute("SELECT MAX(id) FROM snapshots")
    latest_snap_id = cursor.fetchone()[0]
    cursor.execute("SELECT 1 FROM players WHERE snapshot_id = ? AND name = ?", (latest_snap_id, name))
    is_deleted = cursor.fetchone() is None

    conn.close()

    if not rows:
        return jsonify({"error": f"Player '{name}' not found"}), 404

    if start and end:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt   = datetime.strptime(end, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
        rows = [r for r in rows if start_dt <= datetime.strptime(r["timestamp"], TS_FMT) <= end_dt]
    elif hours:
        cutoff = datetime.now() - timedelta(hours=hours)
        rows = [r for r in rows if datetime.strptime(r["timestamp"], TS_FMT) >= cutoff]

    if not rows:
        return jsonify({"error": "No data in that time range"}), 404

    exp_gains = [0] + [calculate_exp_gained(rows[i], rows[i-1]) for i in range(1, len(rows))]
    latest = rows[-1]

    data_points = []
    for i, r in enumerate(rows):
        data_points.append({
            "timestamp": r["timestamp"],
            "label": datetime.strptime(r["timestamp"], TS_FMT).strftime("%m/%d %H:%M"),
            "level": r["level"],
            "rank": r["rank"],
            "exp_gained": exp_gains[i],
            "fame": r["fame"],
            "quests": r["quests"],
            "cards": r["cards"],
        })

    total_exp = sum(exp_gains)
    return jsonify({
        "name": name,
        "job_name": JOB_NAMES.get(latest["job"], "Unknown"),
        "class": get_class_for_job(latest["job"]),
        "level": latest["level"],
        "rank": latest["rank"],
        "fame": latest["fame"],
        "quests": latest["quests"],
        "cards": latest["cards"],
        "total_exp_gained": total_exp,
        "levels_gained": latest["level"] - rows[0]["level"],
        "first_seen": rows[0]["timestamp"],
        "last_active": last_active,
        "is_deleted": is_deleted,
        "days_tracked": (datetime.strptime(latest["timestamp"], TS_FMT) - datetime.strptime(rows[0]["timestamp"], TS_FMT)).days,
        "data_points": data_points,
    })

@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")

@app.route("/api/players_by_job/<int:job_id>")
def api_players_by_job(job_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.name, p.level, p.rank
        FROM players p
        WHERE p.snapshot_id = (SELECT MAX(id) FROM snapshots)
        AND p.job = ?
        AND (p.job != 0 OR p.level >= 11)
        ORDER BY p.rank
    """, (job_id,))
    players = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({
        "job_name": JOB_NAMES.get(job_id, "Unknown"),
        "players": players,
    })

@app.route("/api/jobs")
def api_jobs():
    """Current job populations from latest snapshot, grouped by class."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM snapshots")
    snapshot_id = cursor.fetchone()[0]
    cursor.execute("SELECT job, level FROM players WHERE snapshot_id = ? AND (job != 0 OR level >= 11)", (snapshot_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    job_counts = {}
    for r in rows:
        job_counts[r["job"]] = job_counts.get(r["job"], 0) + 1

    # Group by class
    result = {}
    for cls, job_ids in CLASS_JOB_IDS.items():
        result[cls] = []
        for job_id in job_ids:
            count = job_counts.get(job_id, 0)
            result[cls].append({
                "job_id": job_id,
                "job_name": JOB_NAMES.get(job_id, "Unknown"),
                "count": count,
            })

    # Tier counts (excluding base jobs and sub-11 beginners)
    eligible = [r for r in rows if r["job"] != 0 or r["level"] >= 11]
    tier_counts = {}
    for tier, ids in TIER_JOB_IDS.items():
        tier_counts[tier] = sum(1 for r in eligible if r["job"] in ids)
    total = sum(tier_counts.values())

    return jsonify({"classes": result, "tier_counts": tier_counts, "total": total})

@app.route("/api/jobs/trends")
def api_jobs_trends():
    """Job population trends over all snapshots, grouped by class."""
    filter_class = request.args.get("class")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    snapshots = [dict(row) for row in cursor.fetchall()]

    if not snapshots:
        conn.close()
        return jsonify({"error": "No snapshots"}), 400

    # Determine which job_ids to include
    if filter_class and filter_class in CLASS_JOB_IDS:
        job_ids_to_include = CLASS_JOB_IDS[filter_class]
    else:
        job_ids_to_include = [jid for ids in CLASS_JOB_IDS.values() for jid in ids]

    labels = []
    series = {jid: [] for jid in job_ids_to_include}

    for s in snapshots:
        labels.append(datetime.strptime(s["timestamp"], TS_FMT).strftime("%m/%d"))
        cursor.execute(
            "SELECT job, COUNT(*) as cnt FROM players WHERE snapshot_id = ? AND (job != 0 OR level >= 11) GROUP BY job",
            (s["id"],)
        )
        counts = {row[0]: row[1] for row in cursor.fetchall()}
        for jid in job_ids_to_include:
            series[jid].append(counts.get(jid, 0))

    conn.close()

    return jsonify({
        "labels": labels,
        "series": [
            {
                "job_id": jid,
                "job_name": JOB_NAMES.get(jid, "Unknown"),
                "class": get_class_for_job(jid),
                "data": series[jid],
            }
            for jid in job_ids_to_include
        ],
    })


@app.route("/api/players/search")
def api_players_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT p.name, p.level, p.job
        FROM players p
        WHERE p.snapshot_id = (SELECT MAX(id) FROM snapshots)
        AND LOWER(p.name) LIKE LOWER(?) LIMIT 10
    """, (f"%{q}%",))
    rows = [{"name": r["name"], "level": r["level"], "job_name": JOB_NAMES.get(r["job"], "?")} for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/jobs/level_distribution")
def api_jobs_level_distribution():
    filter_class = request.args.get("class")

    CLASS_BRANCHES = {
        "Beginner": [[0]],
        "Warrior":  [[110,111,112],[120,121,122],[130,131,132]],
        "Magician": [[210,211,212],[220,221,222],[230,231,232]],
        "Archer":   [[310,311,312],[320,321,322]],
        "Thief":    [[410,411,412],[420,421,422]],
        "Pirate":   [[510,511,512],[520,521,522]],
    }

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM snapshots")
    snapshot_id = cursor.fetchone()[0]
    cursor.execute("SELECT job, level FROM players WHERE snapshot_id = ? AND (job != 0 OR level >= 11)", (snapshot_id,))
    players = [dict(row) for row in cursor.fetchall()]
    conn.close()

    classes_to_include = [filter_class] if filter_class and filter_class in CLASS_BRANCHES else list(CLASS_BRANCHES.keys())

    result = []
    for cls in classes_to_include:
        if cls == "Beginner":
            # Beginner is a single job with no branches, handle separately
            beg_players = [p for p in players if p["job"] == 0]
            buckets = {}
            for p in beg_players:
                bucket = ((p["level"] - 1) // 10) * 10 + 1
                label = f"{bucket}-{bucket+9}"
                buckets[label] = buckets.get(label, 0) + 1
            sorted_labels = sorted(buckets.keys(), key=lambda x: int(x.split("-")[0]))
            result.append({
                "class": "Beginner",
                "branch_name": "Beginner",
                "jobs": [{"job_id": 0, "job_name": "Beginner", "buckets": buckets}],
                "labels": sorted_labels,
            })
            continue
        for branch_ids in CLASS_BRANCHES[cls]:
            branch_jobs = []
            all_labels = set()
            for job_id in branch_ids:
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
                        label = f"{bucket}-{bucket+9}"
                    buckets[label] = buckets.get(label, 0) + 1
                branch_jobs.append({
                    "job_id": job_id,
                    "job_name": JOB_NAMES.get(job_id, "Unknown"),
                    "buckets": buckets,
                })
                all_labels.update(buckets.keys())

            sorted_labels = sorted(all_labels, key=lambda x: int(x.split("-")[0]))
            result.append({
                "class": cls,
                "branch_name": " / ".join(JOB_NAMES.get(j, "?") for j in branch_ids),
                "jobs": branch_jobs,
                "labels": sorted_labels,
            })

    return jsonify(result)

@app.route("/api/players/deleted")
def api_players_deleted():
    """Players who appeared in at least one snapshot but are absent from the latest."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM snapshots ORDER BY id DESC LIMIT 1")
    latest_id = cursor.fetchone()[0]

    # Names in latest snapshot
    cursor.execute("SELECT DISTINCT name FROM players WHERE snapshot_id = ?", (latest_id,))
    latest_names = set(r[0] for r in cursor.fetchall())

    # Names that ever appeared but aren't in the latest
    cursor.execute("SELECT DISTINCT name FROM players WHERE snapshot_id != ?", (latest_id,))
    gone = [r[0] for r in cursor.fetchall() if r[0] not in latest_names]

    results = []
    for name in gone:
        cursor.execute("""
            SELECT s.timestamp, p.level, p.job, p.rank
            FROM players p JOIN snapshots s ON p.snapshot_id = s.id
            WHERE p.name = ? ORDER BY s.timestamp
        """, (name,))
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            continue
        first, last = rows[0], rows[-1]

        cursor.execute("SELECT SUM(exp_gained) FROM player_activity WHERE name = ?", (name,))
        total_exp = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT MAX(s.timestamp) FROM player_activity pa
            JOIN snapshots s ON pa.snapshot_id = s.id
            WHERE pa.name = ? AND pa.exp_gained > 0
        """, (name,))
        last_active = cursor.fetchone()[0]

        results.append({
            "name": name,
            "level": last["level"],
            "job_name": JOB_NAMES.get(last["job"], "Unknown"),
            "class": get_class_for_job(last["job"]),
            "rank": last["rank"],
            "first_seen": first["timestamp"],
            "last_seen": last["timestamp"],
            "last_active": last_active,
            "snapshots": len(rows),
            "total_exp": total_exp,
        })

    results.sort(key=lambda x: x["level"], reverse=True)
    conn.close()
    return jsonify(results)

@app.route("/api/guilds")
def api_guilds():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT g.name FROM guilds g
            WHERE EXISTS (SELECT 1 FROM guild_members gm WHERE gm.guild_id = g.id)
            ORDER BY g.name
        """)
        names = [r[0] for r in cursor.fetchall()]
    except Exception:
        names = []
    conn.close()
    return jsonify(names)

@app.route("/api/guild")
def api_guild():
    hours      = request.args.get("hours", type=int)
    start      = request.args.get("start")
    end        = request.args.get("end")
    guild_name = request.args.get("guild", "")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name FROM guilds ORDER BY name")
        guilds = {r[1]: r[0] for r in cursor.fetchall()}
        if not guilds:
            conn.close()
            return jsonify({"error": "No guilds configured"}), 404
        if not guild_name or guild_name not in guilds:
            guild_name = next(iter(guilds))
        guild_id = guilds[guild_name]
        cursor.execute("SELECT player_name FROM guild_members WHERE guild_id = ?", (guild_id,))
        MEMBERS = [r[0] for r in cursor.fetchall()]
    except Exception:
        conn.close()
        return jsonify({"error": "No guilds configured"}), 404
    conn.close()

    if not MEMBERS:
        return jsonify({"error": "Guild has no members"}), 404

    latest, prev = get_snapshot_window(hours=hours, start=start, end=end)
    if not prev:
        return jsonify({"error": "Need at least two snapshots"}), 400

    latest_id, latest_ts = latest["id"], latest["timestamp"]
    prev_id, prev_ts = prev["id"], prev["timestamp"]

    delta = datetime.strptime(latest_ts, TS_FMT) - datetime.strptime(prev_ts, TS_FMT)
    total_hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60

    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(MEMBERS))

    cursor.execute(f"""
        SELECT pa.name, SUM(pa.exp_gained) as exp_gained
        FROM player_activity pa
        WHERE pa.name IN ({placeholders})
        AND pa.snapshot_id IN (SELECT id FROM snapshots WHERE id > ? AND id <= ?)
        GROUP BY pa.name ORDER BY exp_gained DESC
    """, (*MEMBERS, prev_id, latest_id))
    exp_rows = {r["name"]: r["exp_gained"] for r in cursor.fetchall()}

    cursor.execute(f"""
        SELECT p_new.name, p_new.quests - p_old.quests as quest_delta,
               p_new.cards - p_old.cards as card_delta,
               p_new.level - p_old.level as level_delta,
               p_new.level, p_new.job
        FROM players p_new
        JOIN players p_old ON p_old.name = p_new.name AND p_old.snapshot_id = ?
        WHERE p_new.snapshot_id = ? AND p_new.name IN ({placeholders})
    """, (prev_id, latest_id, *MEMBERS))
    member_rows = {r["name"]: dict(r) for r in cursor.fetchall()}
    conn.close()

    members = []
    for name in MEMBERS:
        if name in member_rows or name in exp_rows:
            info = member_rows.get(name, {})
            members.append({
                "name": name,
                "exp_gained": exp_rows.get(name, 0),
                "level": info.get("level", "?"),
                "job_name": JOB_NAMES.get(info.get("job", 0), "?"),
                "class": get_class_for_job(info.get("job", 0)),
                "level_delta": info.get("level_delta", 0),
                "quest_delta": info.get("quest_delta", 0),
                "card_delta": info.get("card_delta", 0),
            })

    return jsonify({
        "guild_name": guild_name,
        "window_label": f"{total_hours}h {minutes}m",
        "top_exp":    sorted(members, key=lambda x: x["exp_gained"], reverse=True)[:10],
        "top_levels": sorted([m for m in members if m["level_delta"] > 0], key=lambda x: x["level_delta"], reverse=True)[:10],
        "top_quests": sorted([m for m in members if m["quest_delta"] > 0], key=lambda x: x["quest_delta"], reverse=True)[:10],
        "top_cards":  sorted([m for m in members if m["card_delta"] > 0], key=lambda x: x["card_delta"], reverse=True)[:10],
    })


# ─── Guild Roster Management ──────────────────────────────────────────────────

@app.route("/guild/login", methods=["GET", "POST"])
def guild_login():
    error = None
    if request.method == "POST":
        guild_name = request.form.get("guild", "").strip()
        password   = request.form.get("password", "").encode()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM guilds WHERE name = ?", (guild_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            if row["password"] and bcrypt.checkpw(password, row["password"].encode()):
                session["guild_id"]   = row["id"]
                session["guild_name"] = guild_name
                return redirect(url_for("guild_roster"))
        error = "Incorrect guild name or password."
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM guilds ORDER BY name")
        guilds = [r[0] for r in cursor.fetchall()]
    except Exception:
        guilds = []
    conn.close()
    return render_template("guild_login.html", guilds=guilds, error=error)

@app.route("/guild/logout")
def guild_logout():
    session.clear()
    return redirect(url_for("guild_login"))

@app.route("/guild/roster")
def guild_roster():
    if "guild_id" not in session:
        return redirect(url_for("guild_login"))
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT gm.player_name,
                  (SELECT MAX(s.timestamp)
                   FROM player_activity pa
                   JOIN snapshots s ON pa.snapshot_id = s.id
                   WHERE pa.name = gm.player_name AND pa.exp_gained > 0) AS last_active
           FROM guild_members gm
           WHERE gm.guild_id = ?
           ORDER BY gm.player_name""",
        (session["guild_id"],)
    )
    members = [{"name": r["player_name"], "last_active": r["last_active"]} for r in cursor.fetchall()]
    # All known player names for autocomplete
    cursor.execute("SELECT DISTINCT name FROM players ORDER BY name")
    all_players = [r[0] for r in cursor.fetchall()]
    conn.close()
    return render_template("guild_roster.html",
        guild_name=session["guild_name"],
        members=members,
        all_players=all_players,
    )

@app.route("/guild/roster/add", methods=["POST"])
def guild_roster_add():
    if "guild_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO guild_members (guild_id, player_name) VALUES (?, ?)",
            (session["guild_id"], name)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500
    conn.close()
    return jsonify({"ok": True})

@app.route("/guild/roster/remove", methods=["POST"])
def guild_roster_remove():
    if "guild_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name required"}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM guild_members WHERE guild_id = ? AND player_name = ?",
        (session["guild_id"], name)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/guild/roster/set-password", methods=["POST"])
def guild_roster_set_password():
    if "guild_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.json
    current  = data.get("current", "").encode()
    new_pw   = data.get("new", "").strip()
    if len(new_pw) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM guilds WHERE id = ?", (session["guild_id"],))
    row = cursor.fetchone()
    # Allow setting password if currently blank, otherwise verify current
    if row["password"] and not bcrypt.checkpw(current, row["password"].encode()):
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 403
    hashed = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    cursor.execute("UPDATE guilds SET password = ? WHERE id = ?", (hashed, session["guild_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)