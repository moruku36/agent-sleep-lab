"""Bounded personal-development test entry: <=10 cases, concise output.

Default: 3 focused Gate 3 rollback cases (UNEXECUTED until the single PR CI run). The 4 scoped-
retrieval cases remain selectable by explicit name. Pass explicit unittest names to select checks for another change.
--list validates/selects without executing test bodies. Historical tests remain available, but
this entry never starts a full discovery run. The 10-case cap is unchanged.
"""

import argparse
from pathlib import Path
import sys
import unittest


MAX_CASES = 10
DEFAULT_CASES = (
    "test_rollback.RollbackTests.test_scope_bound_rollback_then_normal_adoption",
    "test_rollback.RollbackTests.test_current_revocation_refuses_whole_rollback_and_leaves_history",
    "test_rollback.RollbackTests.test_stale_head_conflict_and_exact_replay_survive_reopen",
)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*", help="explicit unittest module/class/method names")
    parser.add_argument("--limit", type=int, default=MAX_CASES, help="case cap, at most 10")
    parser.add_argument("--list", action="store_true", help="show selection, do not execute test bodies")
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_CASES:
        parser.error("--limit must be between 1 and 10")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    loader = unittest.TestLoader()
    cases = list(flatten(loader.loadTestsFromNames(args.tests or DEFAULT_CASES)))
    if loader.errors:
        parser.error("could not load the requested tests; no test bodies executed")
    if not cases or len(cases) > args.limit:
        parser.error(f"selected {len(cases)} cases; limit {args.limit}; no test bodies executed")
    identifiers = [case.id() for case in cases]
    if len(set(identifiers)) != len(identifiers):
        parser.error("duplicate case selection; no test bodies executed")
    if args.list:
        print(f"Selected {len(cases)} cases; limit {args.limit}; execution count 0")
        for name in identifiers:
            print(name)
        return 0
    print(f"Executing {len(cases)} selected cases in one invocation; limit {args.limit}", flush=True)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(cases))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
