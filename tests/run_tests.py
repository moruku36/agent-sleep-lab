"""Run the repository unittest suite from an explicit, reviewable entry file."""

from pathlib import Path
import sys
import unittest


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
