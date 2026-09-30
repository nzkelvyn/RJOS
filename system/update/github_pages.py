"""GitHub Pages Update Source implementation."""
import urllib.request
import json
import yaml
from .source import UpdateSource

class GitHubPagesSource(UpdateSource):
    def __init__(self, base_url="https://raw.githubusercontent.com/rjos/rjos-updates/main/updates"):
        self.base_url = base_url

    def _fetch_yaml(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'RJOS-Update'})
            with urllib.request.urlopen(req) as response:
                return yaml.safe_load(response.read().decode('utf-8'))
        except Exception as e:
            return None

    def get_latest(self, channel="stable"):
        return self._fetch_yaml(f"{self.base_url}/{channel}/latest.yaml")

    def get_release(self, channel, version):
        return self._fetch_yaml(f"{self.base_url}/{channel}/releases/{version}.yaml")
