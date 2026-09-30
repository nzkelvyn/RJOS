"""Main Update Manager."""
from .source import UpdateSource
from .github_pages import GitHubPagesSource
from .cache import UpdateCache
from .version import RJOS_VERSION, compare_versions
from .preflight import PreflightChecks
from .verifier import SignatureVerifier
from .ab_partition import ABPartitionManager

class UpdateManager:
    def __init__(self, source: UpdateSource = None):
        self.source = source or GitHubPagesSource()
        self.cache = UpdateCache()
        self.ab_manager = ABPartitionManager()
        self.verifier = SignatureVerifier()

    def run_preflight(self):
        """Executa verificações pré-instalação (espaço, bateria)."""
        return PreflightChecks.run_all()

    def check_for_updates(self, channel="stable"):
        latest = self.source.get_latest(channel)
        if latest:
            # TODO: Obter assinatura remota e chamar self.verifier.verify_metadata(latest, sig)
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
        release = self.source.get_release(channel, version)
        if release:
             # Em ambiente seguro, verificação GPG ocorreria aqui também
             pass
        return release
