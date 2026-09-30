"""Main Update Manager."""
from .source import UpdateSource
from .github_pages import GitHubPagesSource
from .cache import UpdateCache
from .version import RJOS_VERSION, compare_versions

class UpdateManager:
    def __init__(self, source: UpdateSource = None):
        self.source = source or GitHubPagesSource()
        self.cache = UpdateCache()

    def check_for_updates(self, channel="stable"):
        latest = self.source.get_latest(channel)
        if latest:
            self.cache.save_latest(latest)
            avail_version = latest.get("version")
            if compare_versions(RJOS_VERSION, avail_version) < 0:
                return latest
        return None
    
    def get_release_info(self, channel="stable", version=None):
        if not version:
            latest = self.cache.get_latest()
            if not latest: return None
            version = latest["version"]
        return self.source.get_release(channel, version)
