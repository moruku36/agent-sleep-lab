"""Run all unique regression cases by default, or explicit affected names.

Owner authorized full regression on 2026-11-10. Imported fixture TestCase
aliases are deduplicated by unittest ID; no test body is silently filtered.
"""
import argparse
from pathlib import Path
import sys
import unittest


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    directory = str(Path(__file__).resolve().parent)
    sys.path.insert(0, directory)
    loader = unittest.TestLoader()
    suite = (loader.loadTestsFromNames(args.tests) if args.tests else
             loader.discover(directory, pattern="test_*.py"))
    if loader.errors:
        parser.error("\n".join(loader.errors))
    cases = {case.id(): case for case in flatten(suite)}
    if not cases:
        parser.error("no tests selected")
    print(f"Selected {len(cases)} unique cases; executions {0 if args.list else 1} invocation", flush=True)
    if args.list:
        for name in sorted(cases):
            print(name)
        return 0
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(cases.values()))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
