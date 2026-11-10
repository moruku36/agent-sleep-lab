"""Bounded personal-development test entry: <=10 cases, concise output.

Default: five new offline Gate 4A cases, one PR-only invocation.
Historical Gate 3 is exhausted and is NOT rerun by this selection.
A per-invocation cap is not a cumulative-budget ledger. No full-suite discovery.
--list validates/selects without executing test bodies. Historical tests remain available, but
this entry never starts a full discovery run. The 10-case cap is unchanged.
"""

import argparse
from pathlib import Path
import sys
import unittest


MAX_CASES = 10
DEFAULT_CASES = (
    "test_sleep_coordinator.SleepTests.test_synthetic_roundtrip_reconciles_lost_adoption_ack",
    "test_sleep_coordinator.SleepTests.test_reopen_resumes_deep_without_repeating_light",
    "test_sleep_coordinator.SleepTests.test_changed_run_binding_rejects_without_mutation",
    "test_sleep_coordinator.SleepTests.test_budget_stops_before_deep_and_retains_consumed_usage",
    "test_sleep_coordinator.SleepTests.test_provider_verification_claim_cannot_promote_memory",
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
