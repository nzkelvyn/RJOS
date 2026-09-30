"""Cache for update metadata."""
import os
import json
import yaml
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "rjos-update"

class UpdateCache:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.latest_file = CACHE_DIR / "latest.json"

    def save_latest(self, data):
        with open(self.latest_file, "w") as f:
            json.dump(data, f)

    def get_latest(self):
        if self.latest_file.exists():
            with open(self.latest_file, "r") as f:
                return json.load(f)
        return None
