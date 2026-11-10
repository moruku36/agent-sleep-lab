"""Bounded personal-development test entry: <=10 cases, concise output.

Default: review-fix acceptance, 5 new + 5 existing regression cases. UNEXECUTED;
requires an explicit +10 extension to the exhausted Gate 3 budget BEFORE PR creation.
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
    "test_review_fixes.ReviewFixTests.test_bilingual_ranking_normalizes_punctuation_and_keeps_no_query_order",
    "test_review_fixes.ReviewFixTests.test_policy_chain_is_once_per_retrieval_and_revocation_is_not_cached",
    "test_review_fixes.ReviewFixTests.test_metadata_reads_do_not_reserve_writer_and_cleanup_on_failure",
    "test_review_fixes.ReviewFixTests.test_directory_is_classified_before_open_and_regular_permission_is_preserved",
    "test_review_fixes.ReviewFixTests.test_rollback_ignores_unrelated_broken_journal_but_checks_target_proof",
    "test_adoption_store.AdoptionTests.test_carried_member_is_rechecked_under_current_policy",
    "test_runtime_store.PolicyTests.test_exclusions_only_grow_and_bad_input_is_rejected",
    "test_rollback.RollbackTests.test_current_revocation_refuses_whole_rollback_and_leaves_history",
    "test_forgetting.ForgettingTests.test_same_scope_impact_preserves_unrelated_and_commit_is_atomic",
    "test_cli.CliTests.test_unreadable_input_exits_two_on_stderr",
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
