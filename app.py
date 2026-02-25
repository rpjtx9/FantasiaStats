"""
Fantasia Rankings Dashboard - Flask web server
Drop this file into your FantasiaRankingsData/ folder alongside database.py and analyze.py
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import os


app = Flask(__name__)
DB_PATH = Path(os.environ.get("DATA_DIR", "data")) / "fantasia.db"

JOB_NAMES = {
    0: "Beginner",
    100: "Warrior", 110: "Fighter", 111: "Crusader", 112: "Hero",
    120: "Page", 121: "White Knight", 122: "Paladin",
    130: "Spearman", 131: "Dragon Knight", 132: "Dark Knight",
    200: "Magician",
    210: "Wizard (F/P)", 211: "Mage (F/P)", 212: "Archmage (F/P)",
    220: "Wizard (I/L)", 221: "Mage (I/L)", 222: "Archmage (I/L)",
    230: "Cleric", 231: "Priest", 232: "Bishop",
    300: "Archer",
    310: "Hunter", 311: "Ranger", 312: "Bowmaster",
    320: "Crossbowman", 321: "Sniper", 322: "Marksman",
    400: "Thief",
    410: "Assassin", 411: "Hermit", 412: "Night Lord",
    420: "Bandit", 421: "Chief Bandit", 422: "Shadower",
    500: "Pirate",
    510: "Brawler", 511: "Marauder", 512: "Buccaneer",
    520: "Gunslinger", 521: "Outlaw", 522: "Corsair",
}

CLASS_JOB_IDS = {
    "Beginner": [0],
    "Warrior":  [100,110,111,112,120,121,122,130,131,132],
    "Magician": [200,210,211,212,220,221,222,230,231,232],
    "Archer":   [300,310,311,312,320,321,322],
    "Thief":    [400,410,411,412,420,421,422],
    "Pirate":   [500,510,511,512,520,521,522],
}

TIER_JOB_IDS = {
    "Beginner": [0],
    "1st Job": [100,200,300,400,500],
    "2nd Job": [110,120,130,210,220,230,310,320,410,420,510,520],
    "3rd Job": [111,121,131,211,221,231,311,321,411,421,511,521],
    "4th Job": [112,122,132,212,222,232,312,322,412,422,512,522],
}

FANTASIA_EXP_TABLE = {
    1:15,2:34,3:57,4:92,5:135,6:372,7:560,8:840,9:1242,10:1716,
    11:2302,12:3063,13:3907,14:4964,15:6267,16:7687,17:9396,18:11430,
    19:13616,20:16173,21:19139,22:22292,23:25902,24:30009,25:34339,
    26:39214,27:44678,28:50400,29:56759,30:63800,31:71134,32:79200,
    33:88042,34:97213,35:107210,36:118080,37:129313,38:141471,39:154598,
    40:168123,41:182670,42:198287,43:214334,44:231503,45:249840,46:268642,
    47:288665,48:309957,49:331747,50:354858,51:374304,52:394816,53:416451,
    54:439273,55:463345,56:488736,57:515518,58:543768,59:573566,60:604997,
    61:638151,62:673121,63:710008,64:748916,65:789957,66:833246,67:878908,
    68:927072,69:977875,70:1031463,71:1084597,72:1140480,73:1199253,
    74:1261068,75:1326081,76:1394460,77:1466378,78:1542020,79:1621578,
    80:1705257,81:1793271,82:1885844,83:1983215,84:2085632,85:2193357,
    86:2306667,87:2425853,88:2551218,89:2683087,90:2821796,91:2967702,
    92:3121178,93:3282621,94:3452443,95:3631081,96:3818994,97:4016666,
    98:4224604,99:4443344,100:4673448,101:4915509,102:5170149,103:5438024,
    104:5719824,105:6016275,106:6328141,107:6656225,108:7001375,109:7364479,
    110:7746474,111:8148346,112:8571132,113:9015924,114:9483870,115:9976179,
    116:10494123,117:11039039,118:11612337,119:12215498,120:12850083,
    121:13517733,122:14220175,123:14959228,124:15736803,125:16554915,
    126:17415683,127:18321335,128:19274218,129:20276803,130:21331688,
    131:22441607,132:23609440,133:24838216,134:26131123,135:27491515,
    136:28922926,137:30429070,138:32013860,139:33681411,140:35436057,
    141:37282357,142:39225110,143:41269367,144:43420443,145:45683934,
    146:48065728,147:50572023,148:53209341,149:55984548,150:58904870,
    151:61823738,152:64888849,153:68107591,154:71487731,155:75037428,
    156:78765257,157:82680233,158:86791825,159:91109989,160:95645183,
    161:100408404,162:105411205,163:110665731,164:116184744,165:121981660,
    166:128070578,167:134466316,168:141184451,169:148241352,170:155654228,
    171:163441166,172:171621175,173:180214239,174:189241364,175:198724626,
    176:208687237,177:219153592,178:230149334,179:241701424,180:253838198,
    181:266589447,182:279986486,183:294062235,184:308851304,185:324390073,
    186:340716789,187:357871664,188:375896968,189:394837142,190:414738908,
    191:437466600,192:461439770,193:486726669,194:513399290,195:541533571,
    196:571209611,197:602511898,198:635529549,199:670356568,200:0,
}

TS_FMT = "%Y-%m-%d_%H-%M-%S"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_class_for_job(job_id):
    for cls, ids in CLASS_JOB_IDS.items():
        if job_id in ids:
            return cls
    return "Beginner"

def calculate_exp_gained(current, previous):
    exp_diff = current["experience"] - previous["experience"]
    if current["level"] > previous["level"]:
        levels_gained = current["level"] - previous["level"]
        true_gain = 0
        for lvl_offset in range(levels_gained):
            lvl = previous["level"] + lvl_offset
            if lvl_offset == 0:
                true_gain += FANTASIA_EXP_TABLE.get(lvl, 0) - previous["experience"]
            else:
                true_gain += FANTASIA_EXP_TABLE.get(lvl, 0)
        true_gain += current["experience"]
        return true_gain
    return exp_diff

def exp_to_level_percent(exp_gained, current_level):
    if current_level < 1 or current_level > 200:
        return 0.0
    level_exp = FANTASIA_EXP_TABLE.get(current_level, 1)
    return round((exp_gained / level_exp) * 100, 1)

def snapshot_closest_to(cursor, target_ts):
    """Return the snapshot row closest to target_ts (a datetime object)."""
    cursor.execute("SELECT id, timestamp FROM snapshots ORDER BY timestamp")
    rows = [dict(row) for row in cursor.fetchall()]
    return min(rows, key=lambda r: abs(
        (datetime.strptime(r["timestamp"], TS_FMT) - target_ts).total_seconds()
    ))

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
    return render_template("guild.html")

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

@app.route("/api/snapshots")
def api_snapshots():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, total_players FROM snapshots ORDER BY id DESC LIMIT 50")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

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

@app.route("/api/server_health")
def api_server_health():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp, total_players FROM snapshots ORDER BY timestamp")
    total_rows = [dict(row) for row in cursor.fetchall()]

    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT substr(s.timestamp, 1, 10) as day,
               COUNT(DISTINCT pa.name) as active_count
        FROM snapshots s
        JOIN player_activity pa ON pa.snapshot_id = s.id
        WHERE substr(s.timestamp, 1, 10) < ?
        GROUP BY day
        ORDER BY day
    """, (today,))
    active_rows = [dict(row) for row in cursor.fetchall()]
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

    snapshot_players = {}
    for s in snapshots:
        cursor.execute("SELECT DISTINCT name FROM players WHERE snapshot_id = ?", (s["id"],))
        snapshot_players[s["id"]] = set(row[0] for row in cursor.fetchall())
    conn.close()

    if len(snapshots) < 2:
        return jsonify({"error": "Not enough data"}), 400

    first_ts = datetime.strptime(snapshots[0]["timestamp"], TS_FMT)
    for s in snapshots:
        ts = datetime.strptime(s["timestamp"], TS_FMT)
        s["week"] = (ts - first_ts).days // 7

    weeks = sorted(set(s["week"] for s in snapshots))
    cohorts, seen = {}, set()
    for week in weeks:
        week_snaps = [s for s in snapshots if s["week"] == week]
        week_players = set()
        for s in week_snaps:
            week_players.update(snapshot_players[s["id"]])
        new = week_players - seen
        cohorts[week] = new
        seen.update(new)

    retention_data = {}
    for cw, cp in cohorts.items():
        if not cp:
            continue
        retention_data[cw] = {}
        for week in weeks:
            if week < cw:
                continue
            week_snaps = [s for s in snapshots if s["week"] == week]
            wp = set()
            for s in week_snaps:
                wp.update(snapshot_players[s["id"]])
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
    })

@app.route("/api/player/<name>")
def api_player(name):
    start = request.args.get("start")
    end   = request.args.get("end")
    hours = request.args.get("hours", type=int)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.timestamp, p.level, p.experience, p.rank, p.fame, p.quests, p.cards, p.job
        FROM players p JOIN snapshots s ON p.snapshot_id = s.id
        WHERE p.name = ? ORDER BY s.timestamp
    """, (name,))
    rows = [dict(row) for row in cursor.fetchall()]
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
        "days_tracked": (datetime.strptime(latest["timestamp"], TS_FMT) - datetime.strptime(rows[0]["timestamp"], TS_FMT)).days,
        "data_points": data_points,
    })

@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")

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
        AND p.name LIKE ? LIMIT 10
    """, (f"%{q}%",))
    rows = [{"name": r["name"], "level": r["level"], "job_name": JOB_NAMES.get(r["job"], "?")} for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/api/jobs/level_distribution")
def api_jobs_level_distribution():
    filter_class = request.args.get("class")

    JOB_LEVEL_FLOORS = {
        100: 10, 300: 10, 400: 10, 500: 10, 200: 8,
        110: 30, 120: 30, 130: 30, 210: 30, 220: 30, 230: 30,
        310: 30, 320: 30, 410: 30, 420: 30, 510: 30, 520: 30,
        111: 70, 121: 70, 131: 70, 211: 70, 221: 70, 231: 70,
        311: 70, 321: 70, 411: 70, 421: 70, 511: 70, 521: 70,
        112: 120, 122: 120, 132: 120, 212: 120, 222: 120, 232: 120,
        312: 120, 322: 120, 412: 120, 422: 120, 512: 120, 522: 120,
    }

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

@app.route("/api/guilds")
def api_guilds():
    try:
        from guilds import GUILDS
        return jsonify(list(GUILDS.keys()))
    except ImportError:
        return jsonify([])

@app.route("/api/guild")
def api_guild():
    hours      = request.args.get("hours", type=int)
    start      = request.args.get("start")
    end        = request.args.get("end")
    guild_name = request.args.get("guild", "")

    try:
        from guilds import GUILDS
    except ImportError:
        return jsonify({"error": "guilds.py not found"}), 404

    if not guild_name or guild_name not in GUILDS:
        guild_name = next(iter(GUILDS))

    MEMBERS = GUILDS[guild_name]

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

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)