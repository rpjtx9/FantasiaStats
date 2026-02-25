import requests
import json
import time
import os
import re
from datetime import datetime, timezone
from pathlib import Path

URL = "https://fantasia.ms/rankings"

BASE_HEADERS = {
    "Origin":     "https://fantasia.ms",
    "Referer":    "https://fantasia.ms/rankings",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
}

_cached_action_id = None
_cached_router_state = None

def get_next_action_id():
    """
    Fetch the rankings page HTML and extract the next-action hash and
    router-state-tree dynamically so a Fantasia deploy won't break fetching.
    Falls back to hardcoded values if extraction fails.
    """
    global _cached_action_id, _cached_router_state

    if _cached_action_id:
        return _cached_action_id, _cached_router_state

    FALLBACK_ACTION = "406c342766703ed52506458681f002cc544df0e354"
    FALLBACK_ROUTER = "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22rankings%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D"

    try:
        resp = requests.get(URL, headers=BASE_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # next-action IDs appear as data-action attributes or in script tags
        # Pattern: a 40+ char hex string associated with server actions
        action_match = re.search(r'"([a-f0-9]{40,})"', html)
        if action_match:
            _cached_action_id = action_match.group(1)
            print(f"Extracted next-action: {_cached_action_id}")
        else:
            print(f"Could not extract next-action, using fallback")
            _cached_action_id = FALLBACK_ACTION

        # Router state tree: extract from __NEXT_DATA__ or meta tags if present
        # For now keep the fallback as it rarely changes independently
        _cached_router_state = FALLBACK_ROUTER

    except Exception as e:
        print(f"Warning: could not fetch page for action ID ({e}), using fallback")
        _cached_action_id = FALLBACK_ACTION
        _cached_router_state = FALLBACK_ROUTER

    return _cached_action_id, _cached_router_state


def fetch_page(page, limit=100):
    action_id, router_state = get_next_action_id()

    headers = {
        **BASE_HEADERS,
        "Accept":                 "text/x-component",
        "Content-Type":           "text/plain;charset=UTF-8",
        "next-action":            action_id,
        "next-router-state-tree": router_state,
    }

    payload = json.dumps([{"job": "all", "limit": limit, "page": page, "search": "", "sortBy": "level"}])
    response = requests.post(URL, data=payload, headers=headers, timeout=30)
    response.raise_for_status()

    # Parse the Next.js streaming response format
    # Lines starting with digits followed by ':' are JSON payloads
    for line in response.text.strip().split("\n"):
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        # Strip the leading "N:" prefix (e.g. "1:", "2:", "0:")
        colon_idx = line.index(":") if ":" in line else -1
        if colon_idx == -1:
            continue
        candidate = line[colon_idx + 1:]
        try:
            parsed = json.loads(candidate)
            # The rankings response has totalPlayers and rankings keys
            if isinstance(parsed, dict) and "rankings" in parsed:
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue

    raise ValueError(f"Could not parse response for page {page}:\n{response.text[:500]}")


def fetch_all_players():
    print("Starting fetch...")

    first_page = fetch_page(1)
    total_players = first_page["totalPlayers"]
    total_pages = -(-total_players // 100)  # ceiling division
    print(f"Total players: {total_players}, pages: {total_pages}")

    all_players = first_page["rankings"]
    print(f"Page 1/{total_pages} - {len(all_players)} players fetched")

    for page in range(2, total_pages + 1):
        data = fetch_page(page)
        all_players.extend(data["rankings"])
        print(f"Page {page}/{total_pages} - {len(all_players)} players fetched")
        time.sleep(0.2)

    return all_players


def save_snapshot(players):
    data_dir = Path(os.environ.get("DATA_DIR", "data")) / "snapshots"
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    filename = data_dir / f"rankings_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(players, f, indent=2)

    print(f"Saved {len(players)} players to {filename}")
    return filename


def load_snapshot(filepath):
    with open(filepath, "r") as f:
        return json.load(f)


def get_latest_snapshots(n=2):
    data_dir = Path(os.environ.get("DATA_DIR", "data")) / "snapshots"
    snapshots = sorted(data_dir.glob("rankings_*.json"), reverse=True)
    return snapshots[:n]


if __name__ == "__main__":
    players = fetch_all_players()
    save_snapshot(players)