import unittest
import sys
from pathlib import Path

# Add system dir to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from update.version import compare_versions

class TestUpdateSystem(unittest.TestCase):
    def test_version_comparison_same(self):
        self.assertEqual(compare_versions("0.1.2", "0.1.2"), 0)

    def test_version_comparison_newer(self):
        self.assertEqual(compare_versions("0.1.1", "0.1.2"), -1)
        self.assertEqual(compare_versions("0.1.2", "0.1.10"), -1)
        self.assertEqual(compare_versions("0.1.2", "0.2.0"), -1)

    def test_version_comparison_older(self):
        self.assertEqual(compare_versions("0.1.2", "0.1.1"), 1)
        self.assertEqual(compare_versions("0.1.10", "0.1.2"), 1)
        self.assertEqual(compare_versions("0.2.0", "0.1.2"), 1)

if __name__ == '__main__':
    unittest.main()
