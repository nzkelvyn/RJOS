"""Update sources abstraction."""
from abc import ABC, abstractmethod

class UpdateSource(ABC):
    @abstractmethod
    def get_latest(self, channel="stable"):
        pass

    @abstractmethod
    def get_release(self, channel, version):
        pass
