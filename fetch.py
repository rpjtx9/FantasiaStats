import requests
import json
import time
from datetime import datetime
from pathlib import Path

URL = "https://fantasia.ms/rankings"
HEADERS = {
    "Accept": "text/x-component",
    "Content-Type": "text/plain;charset=UTF-8",
    "next-action": "406c342766703ed52506458681f002cc544df0e354",
    "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22rankings%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
    "Origin": "https://fantasia.ms",
    "Referer": "https://fantasia.ms/rankings",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
}

def fetch_page(page, limit=100):
    payload = json.dumps([{"job": "all", "limit": limit, "page": page, "search": "", "sortBy": "level"}])
    response = requests.post(URL, data=payload, headers=HEADERS)
    lines = response.text.strip().split("\n")
    return json.loads(lines[1][2:])

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
    data_dir = Path("data/snapshots")
    data_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = data_dir / f"rankings_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(players, f, indent=2)
    
    print(f"Saved {len(players)} players to {filename}")
    return filename

def load_snapshot(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def get_latest_snapshots(n=2):
    data_dir = Path("data/snapshots")
    snapshots = sorted(data_dir.glob("rankings_*.json"), reverse=True)
    return snapshots[:n]

if __name__ == "__main__":
    players = fetch_all_players()
    save_snapshot(players)