"""Read-only CLI cases using real synthetic adoptions and receipts."""
from datetime import timedelta
import io
import json
from pathlib import Path
from unittest import mock

import evidence_support
from runtime_support import make_control, policy_body
import test_retrieval as fixtures
from agent_sleep_lab import resume_advice_cli as reader
from agent_sleep_lab.cli import main
from agent_sleep_lab.provenance import sha256_hex

ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENT = "lab:local"
CANDIDATE = "resume:1"
TAG = "resume-advice:lab:local/resume:1"


class ResumeAdviceTests(evidence_support.StoreCase):
    open_adoption = fixtures.RetrievalTests.open_adoption
    setup_store = fixtures.RetrievalTests.setup_store
    adopt = fixtures.RetrievalTests.adopt

    def setUp(self):
        super().setUp()
        self.store = self.setup_store()
        config = json.loads((ROOT / "configs/runtime-store.example.json").read_text(encoding="utf-8"))
        config["path"] = str(self.path)
        self.config_path = Path(self.dir) / "config.json"
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        clock = mock.patch("agent_sleep_lab.evidence_store._utc_now", self.clock)
        clock.start()
        self.addCleanup(clock.stop)

    def run_cli(self):
        out, err = io.StringIO(), io.StringIO()
        code = main([
            "resume-advice", "--store-config", str(self.config_path),
            "--project", fixtures.SCOPE["project"], "--task-family", fixtures.SCOPE["task_family"],
            "--environment", ENVIRONMENT, "--candidate", CANDIDATE,
        ], out, err)
        self.assertEqual((code, err.getvalue()), (0, ""))
        self.assertIn("Reference only. This advice never authorizes execution or retry.", out.getvalue())
        return out.getvalue()

    def memory_ids(self, output):
        return [json.loads(line.removeprefix("Memory ID: "))
                for line in output.splitlines() if line.startswith("Memory ID: ")]

    def test_matching_advice_reports_provenance_and_escapes_terminal_text(self):
        snapshot = self.adopt(
            self.store, "m-1", "e-1", tags=(TAG, "unrelated-tag"),
            claim="Review checkpoint\n\x1b[31m\u202e", valid_until="2026-11-12T00:00:00Z",
        )
        source = self.store.get("e-1")
        output = self.run_cli()
        self.assertEqual(self.memory_ids(output), ["m-1"])
        for line in (
            'Scope: project="p" task_family="t"',
            'Match: environment="lab:local" candidate="resume:1"',
            r'Claim: "Review checkpoint\n\u001b[31m\u202e"',
            f'  Verified event: "e-1" (SHA-256 "{source.event_sha256}")',
            f'  Source SHA-256: "{source.source_sha256}"',
            '  Recorded locator (not independently verified): "summary"',
            'Observed at: "2026-11-08T00:03:00+09:00"',
            'Memory valid until: "2026-11-12T00:00:00Z"',
            'As of: "2026-11-10T00:00:00Z"',
            f'Snapshot SHA-256: "{sha256_hex(snapshot)}"',
            'Policy revision: 1',
        ):
            self.assertIn(line, output.splitlines())
        for private in ("\x1b", "\u202e", "fixture://s-1/1", "raw source for e-1", "unrelated-tag", self.dir):
            self.assertNotIn(private, output)

    def test_excludes_other_pairs_scopes_partitions_expired_revoked_and_untagged(self):
        partitions = ("experience", "development")
        self.store.set_policy(make_control(), policy_body(partitions=partitions), expected_revision=1)
        self.put(self.store, evidence_support.make_item("e-revoked"))
        self.put(self.store, evidence_support.make_item("e-development", evaluation="development"))
        split_pair = ("resume-advice:lab:local/resume:10", "resume-advice:remote/resume:1")
        parent = None
        for memory_id, event_id, tags, expiry in (
            ("m-case", "e-1", ("resume-advice:Lab:local/resume:1",), None),
            ("m-candidate", "e-1", split_pair, None),
            ("m-development", "e-development", (TAG,), None),
            ("m-expired", "e-1", (TAG,), "2026-11-11T00:00:00Z"),
            ("m-lexical", "e-1", (), None),
            ("m-revoked", "e-revoked", (TAG,), None),
            ("m-visible", "e-1", (TAG,), None),
        ):
            parent = self.adopt(self.store, memory_id, event_id, parent=parent, tags=tags,
                                claim=f"{memory_id} mentions {TAG}", valid_until=expiry, revision=2)
        for event_id, scope in (("e-project", ("q", "t")), ("e-family", ("p", "u"))):
            self.put(self.store, evidence_support.make_item(event_id, scope=scope))
            self.adopt(self.store, event_id.replace("e-", "m-", 1), event_id, tags=(TAG,), revision=2,
                       scope={"project": scope[0], "task_family": scope[1]})
        self.store.set_policy(make_control(), policy_body(partitions=partitions, event_ids=("e-revoked",)),
                              expected_revision=2)
        self.clock.now += timedelta(days=1)
        self.assertEqual(self.memory_ids(self.run_cli()), ["m-visible"])

    def test_filters_before_three_record_cap_in_deterministic_id_order(self):
        parent = None
        other_tag = "resume-advice:remote/resume:1"
        for suffix, tag in (("03", other_tag), ("14", TAG), ("01", other_tag), ("12", TAG),
                            ("02", other_tag), ("13", TAG), ("11", TAG)):
            parent = self.adopt(self.store, f"m-{suffix}", "e-1", parent=parent, tags=(tag,))
        self.assertEqual(self.memory_ids(self.run_cli()), ["m-11", "m-12", "m-13"])

    def test_empty_match_succeeds_read_only_without_mutation(self):
        self.adopt(self.store, "m-1", "e-1", claim="Unrelated synthetic memory")
        before = tuple(self.store._db().iterdump())
        files = sorted(Path(self.dir).iterdir())
        with mock.patch.object(reader, "AdoptionStore", wraps=reader.AdoptionStore) as opened:
            output = self.run_cli()
        opened.assert_called_once()
        self.assertIs(opened.call_args.kwargs["read_only"], True)
        self.assertIn("No matching advice.", output)
        self.assertEqual(self.memory_ids(output), [])
        self.assertNotIn("Unrelated synthetic memory", output)
        self.assertEqual(tuple(self.store._db().iterdump()), before)
        self.assertEqual(sorted(Path(self.dir).iterdir()), files)
