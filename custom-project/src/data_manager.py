import json
from pathlib import Path

DATA_DIR = Path("data")

def load_tickets(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tickets(filename, data):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
