"""Update History."""
import json
import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".config" / "rjos" / "update_history.json"

class UpdateHistory:
    def __init__(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not HISTORY_FILE.exists():
            with open(HISTORY_FILE, "w") as f:
                json.dump([], f)

    def add_entry(self, version, status, packages=None, error=None):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        entry = {
            "version": version,
            "date": datetime.datetime.now().isoformat(),
            "status": status,
            "packages": packages or [],
            "error": error
        }
        history.append(entry)
        
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
