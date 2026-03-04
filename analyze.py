"""
Fantasia game constants, lookup tables, and shared analysis utilities.
This module is the single source of truth — all other modules import from here.
"""

import json
from collections import Counter
from pathlib import Path


# ─── Job Definitions ─────────────────────────────────────────────────────────

JOB_NAMES = {
    0: "Beginner",
    100: "Warrior",
    110: "Fighter", 111: "Crusader", 112: "Hero",
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

JOB_LEVEL_FLOORS = {
    # 1st job (x00)
    100: 10, 300: 10, 400: 10, 500: 10,
    200: 8,
    # 2nd job (x10, x20, x30)
    110: 30, 120: 30, 130: 30,
    210: 30, 220: 30, 230: 30,
    310: 30, 320: 30,
    410: 30, 420: 30,
    510: 30, 520: 30,
    # 3rd job (x11, x21, x31)
    111: 70, 121: 70, 131: 70,
    211: 70, 221: 70, 231: 70,
    311: 70, 321: 70,
    411: 70, 421: 70,
    511: 70, 521: 70,
    # 4th job (x12, x22, x32)
    112: 120, 122: 120, 132: 120,
    212: 120, 222: 120, 232: 120,
    312: 120, 322: 120,
    412: 120, 422: 120,
    512: 120, 522: 120,
}

CLASS_JOB_IDS = {
    "Beginner": [0],
    "Warrior":  [100, 110, 111, 112, 120, 121, 122, 130, 131, 132],
    "Magician": [200, 210, 211, 212, 220, 221, 222, 230, 231, 232],
    "Archer":   [300, 310, 311, 312, 320, 321, 322],
    "Thief":    [400, 410, 411, 412, 420, 421, 422],
    "Pirate":   [500, 510, 511, 512, 520, 521, 522],
}

TIER_JOB_IDS = {
    "Beginner": [0],
    "1st Job": [100, 200, 300, 400, 500],
    "2nd Job": [110, 120, 130, 210, 220, 230, 310, 320, 410, 420, 510, 520],
    "3rd Job": [111, 121, 131, 211, 221, 231, 311, 321, 411, 421, 511, 521],
    "4th Job": [112, 122, 132, 212, 222, 232, 312, 322, 412, 422, 512, 522],
}

# Reverse lookup: job_id -> class name
_JOB_TO_CLASS = {}
for _cls, _ids in CLASS_JOB_IDS.items():
    for _jid in _ids:
        _JOB_TO_CLASS[_jid] = _cls

def get_class_for_job(job_id):
    """Return the class name (Warrior, Magician, etc.) for a given job_id."""
    return _JOB_TO_CLASS.get(job_id, "Beginner")


# ─── Exp Table ───────────────────────────────────────────────────────────────

FANTASIA_EXP_TABLE = {
    1: 15, 2: 34, 3: 57, 4: 92, 5: 135, 6: 372, 7: 560, 8: 840, 9: 1242, 10: 1716,
    11: 2302, 12: 3063, 13: 3907, 14: 4964, 15: 6267, 16: 7687, 17: 9396, 18: 11430,
    19: 13616, 20: 16173, 21: 19139, 22: 22292, 23: 25902, 24: 30009, 25: 34339,
    26: 39214, 27: 44678, 28: 50400, 29: 56759, 30: 63800, 31: 71134, 32: 79200,
    33: 88042, 34: 97213, 35: 107210, 36: 118080, 37: 129313, 38: 141471, 39: 154598,
    40: 168123, 41: 182670, 42: 198287, 43: 214334, 44: 231503, 45: 249840, 46: 268642,
    47: 288665, 48: 309957, 49: 331747, 50: 354858, 51: 374304, 52: 394816, 53: 416451,
    54: 439273, 55: 463345, 56: 488736, 57: 515518, 58: 543768, 59: 573566, 60: 604997,
    61: 638151, 62: 673121, 63: 710008, 64: 748916, 65: 789957, 66: 833246, 67: 878908,
    68: 927072, 69: 977875, 70: 1031463, 71: 1084597, 72: 1140480, 73: 1199253,
    74: 1261068, 75: 1326081, 76: 1394460, 77: 1466378, 78: 1542020, 79: 1621578,
    80: 1705257, 81: 1793271, 82: 1885844, 83: 1983215, 84: 2085632, 85: 2193357,
    86: 2306667, 87: 2425853, 88: 2551218, 89: 2683087, 90: 2821796, 91: 2967702,
    92: 3121178, 93: 3282621, 94: 3452443, 95: 3631081, 96: 3818994, 97: 4016666,
    98: 4224604, 99: 4443344, 100: 4673448, 101: 4915509, 102: 5170149, 103: 5438024,
    104: 5719824, 105: 6016275, 106: 6328141, 107: 6656225, 108: 7001375, 109: 7364479,
    110: 7746474, 111: 8148346, 112: 8571132, 113: 9015924, 114: 9483870, 115: 9976179,
    116: 10494123, 117: 11039039, 118: 11612337, 119: 12215498, 120: 12850083,
    121: 13517733, 122: 14220175, 123: 14959228, 124: 15736803, 125: 16554915,
    126: 17415683, 127: 18321335, 128: 19274218, 129: 20276803, 130: 21331688,
    131: 22441607, 132: 23609440, 133: 24838216, 134: 26131123, 135: 27491515,
    136: 28922926, 137: 30429070, 138: 32013860, 139: 33681411, 140: 35436057,
    141: 37282357, 142: 39225110, 143: 41269367, 144: 43420443, 145: 45683934,
    146: 48065728, 147: 50572023, 148: 53209341, 149: 55984548, 150: 58904870,
    151: 61823738, 152: 64888849, 153: 68107591, 154: 71487731, 155: 75037428,
    156: 78765257, 157: 82680233, 158: 86791825, 159: 91109989, 160: 95645183,
    161: 100408404, 162: 105411205, 163: 110665731, 164: 116184744, 165: 121981660,
    166: 128070578, 167: 134466316, 168: 141184451, 169: 148241352, 170: 155654228,
    171: 163441166, 172: 171621175, 173: 180214239, 174: 189241364, 175: 198724626,
    176: 208687237, 177: 219153592, 178: 230149334, 179: 241701424, 180: 253838198,
    181: 266589447, 182: 279986486, 183: 294062235, 184: 308851304, 185: 324390073,
    186: 340716789, 187: 357871664, 188: 375896968, 189: 394837142, 190: 414738908,
    191: 437466600, 192: 461439770, 193: 486726669, 194: 513399290, 195: 541533571,
    196: 571209611, 197: 602511898, 198: 635529549, 199: 670356568, 200: 0,
}


# ─── Exp Calculation Utilities ───────────────────────────────────────────────

def calculate_exp_gained(current, previous):
    """Calculate true exp gained between two snapshots, accounting for level-ups."""
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
    """Convert raw exp gained to percentage of a level at current_level."""
    if current_level < 1 or current_level > 200:
        return 0.0
    level_exp = FANTASIA_EXP_TABLE.get(current_level, 1)
    return round((exp_gained / level_exp) * 100, 1)


# ─── Snapshot Analysis (used by CLI / main.py) ──────────────────────────────

def level_distribution(players, bucket_size=10):
    buckets = Counter()
    for player in players:
        bucket = ((player["level"] - 1) // bucket_size) * bucket_size + 1
        label = f"{bucket}-{bucket + bucket_size - 1}"
        buckets[label] += 1
    return dict(sorted(buckets.items(), key=lambda x: int(x[0].split("-")[0])))

def job_popularity(players):
    counts = Counter()
    for player in players:
        job_name = JOB_NAMES.get(player["job"], f"Unknown ({player['job']})")
        counts[job_name] += 1
    return dict(counts.most_common())

def active_players(snapshot_today, snapshot_yesterday, exp_threshold=0):
    yesterday_by_name = {p["name"]: p for p in snapshot_yesterday}

    active = []
    new_players = []

    for player in snapshot_today:
        name = player["name"]
        if name in yesterday_by_name:
            exp_gained = calculate_exp_gained(player, yesterday_by_name[name])
            if exp_gained > exp_threshold:
                active.append({
                    **player,
                    "exp_gained": exp_gained
                })
        else:
            new_players.append(player)

    return {
        "active_count": len(active),
        "new_players_count": len(new_players),
        "active_players": sorted(active, key=lambda x: x["exp_gained"], reverse=True),
        "new_players": new_players,
    }

def summary(players):
    levels = [p["level"] for p in players]
    return {
        "total_players": len(players),
        "max_level": max(levels),
        "min_level": min(levels),
        "avg_level": round(sum(levels) / len(levels), 2),
    }

def level_distribution_by_class(players, bucket_size=10):
    class_buckets = {}

    for player in players:
        job_name = JOB_NAMES.get(player["job"], f"Unknown ({player['job']})")

        floor = JOB_LEVEL_FLOORS.get(player["job"], 1)
        if player["level"] < floor:
            continue

        if player["level"] == floor:
            label = str(floor)
        else:
            bucket = ((player["level"] - floor - 1) // bucket_size) * bucket_size + floor + 1
            label = f"{bucket}-{bucket + bucket_size - 1}"

        if job_name not in class_buckets:
            class_buckets[job_name] = {}

        class_buckets[job_name][label] = class_buckets[job_name].get(label, 0) + 1

    for job_name in class_buckets:
        class_buckets[job_name] = dict(sorted(class_buckets[job_name].items(), key=lambda x: int(x[0].split("-")[0])))

    return class_buckets

def level_distribution_by_class_grouped(players, bucket_size=10):
    flat = level_distribution_by_class(players, bucket_size)

    grouped = {}
    current_group = None

    # Add Beginner first
    if "Beginner" in flat:
        grouped["Beginner"] = {"Beginner": flat["Beginner"]}

    for job_id in sorted(JOB_NAMES.keys()):
        job_name = JOB_NAMES[job_id]

        if job_id % 100 == 0 and job_id != 0:
            current_group = job_name
            grouped[current_group] = {}

        if current_group and job_name in flat:
            grouped[current_group][job_name] = flat[job_name]

    return grouped