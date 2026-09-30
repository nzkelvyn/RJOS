"""Version definitions for RJOS."""
import re

RJOS_VERSION = "0.1.1"

def compare_versions(v1, v2):
    """Compares semantic versions. Returns -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2."""
    def parse_version(v):
        return tuple(map(int, re.findall(r'\d+', v)))
    
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    if p1 < p2: return -1
    if p1 > p2: return 1
    return 0
