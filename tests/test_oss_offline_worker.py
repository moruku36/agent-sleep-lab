"""Offline worker validation and loader contracts.

Unit behavior only. The pinned target sources are not in this repository, so
loader tests swap in test-authored stand-in sources; no target code, network,
subprocess or inference runs. ``run()`` and the guards are NOT exercised here:
actual target integration remains unverified.
"""
import copy
import hashlib
import json
import sys
import unittest
from unittest import mock

import support  # noqa: F401  (makes src importable)
from agent_sleep_lab import oss_offline_worker as worker

STAND_INS = {
    "src/__init__.py": b"ORDER = ['src']\n",
    "src/pkg/__init__.py": b"import src\nsrc.ORDER.append('src.pkg')\n",
    "src/pkg/leaf.py": (b"import src\nsrc.ORDER.append('src.pkg.leaf')\n"
                        b"def typed(value: int): return value\n"),
    "src/tail.py": b"import src\nsrc.ORDER.append('src.tail')\n",
}


def pins(sources):
    return {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}


def bundle(**overrides):
    doc = dict(
        schema_version="agent-sleep-reference-bundle/1", reference_data_only=True,
        synthetic_only=True, scope={"project": "p", "task_family": "t"},
        partition="experience", as_of="2026-11-10T00:00:00Z", snapshot_sha256="a" * 64,
        policy={"revision": 1, "sha256": "b" * 64},
        exclusions={"version": 1, "policy_sha256": "b" * 64},
        budget={"unit": "utf8_bytes_of_canonical_bundle_json", "max_bytes": 32768,
                "tokenizer": None},
        counts={"active_members": 1, "eligible": 1, "returned": 1, "dropped": 0},
        records=[{"rank": 1, "claim": "synthetic reference"}])
    doc.update(copy.deepcopy(overrides))
    return doc


def raw(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


class StandInCase(unittest.TestCase):
    """Replace the reviewed pins with stand-ins and isolate sys.modules."""

    sources = STAND_INS

    def setUp(self):
        for patcher in (mock.patch.object(worker, "SOURCE_HASHES", pins(self.sources)),
                        mock.patch.dict(sys.modules)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def payload(self, **overrides):
        value = dict(
            sources={name: data.hex() for name, data in self.sources.items()},
            task_hex=worker.encoded(worker.synthetic_task()).hex(),
            reference_hex=raw(bundle()).hex())
        value.update(overrides)
        return value


class PayloadTests(StandInCase):
    def test_valid_payload_returns_exact_bytes_without_loading_modules(self):
        sources, task, reference = worker.validate_payload(self.payload())
        self.assertEqual(sources, self.sources)
        self.assertEqual(list(sources), list(worker.SOURCE_HASHES))
        self.assertEqual(task, worker.encoded(worker.synthetic_task()))
        self.assertEqual(reference, raw(bundle()))
        self.assertNotIn("src", sys.modules)

    def test_payload_shape_is_exact(self):
        good = self.payload()
        missing = {key: good[key] for key in ("sources", "task_hex")}
        cases = [None, [], list(good.items()), missing, dict(good, extra=1),
                 dict(good, sources=list(good["sources"].items())),
                 dict(good, sources=dict(good["sources"], **{"src/extra.py": ""})),
                 dict(good, sources={k: v for k, v in good["sources"].items()
                                     if k != "src/tail.py"})]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaisesRegex(ValueError, "exact"):
                    worker.validate_payload(case)

    def test_hex_fields_reject_lenient_encodings(self):
        good = self.payload()
        text = good["task_hex"]
        for label, bad in (("bytes", bytes.fromhex(text)), ("none", None), ("int", 7),
                           ("upper", text.upper()), ("spaced", text[:2] + " " + text[2:]),
                           ("odd", text[:-1]), ("prefixed", "0x" + text),
                           ("oversize", "00" * (worker.MAX_TASK_BYTES + 1))):
            with self.subTest(field="task_hex", case=label):
                with self.assertRaisesRegex(ValueError, "lowercase hex"):
                    worker.validate_payload(dict(good, task_hex=bad))
        for label, bad in (("list", []), ("upper", good["reference_hex"].upper()),
                           ("oversize", "20" * (worker.MAX_REFERENCE_BYTES + 1))):
            with self.subTest(field="reference_hex", case=label):
                with self.assertRaisesRegex(ValueError, "lowercase hex"):
                    worker.validate_payload(dict(good, reference_hex=bad))
        spaced = dict(good["sources"])
        spaced["src/tail.py"] = " " + spaced["src/tail.py"] + " "
        with self.assertRaisesRegex(ValueError, "lowercase hex"):
            worker.validate_payload(dict(good, sources=spaced))

    def test_changed_source_bytes_fail_hash_check(self):
        good = self.payload()
        for name in self.sources:
            with self.subTest(name=name):
                changed = dict(good["sources"])
                changed[name] = (self.sources[name] + b"\n").hex()
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    worker.validate_payload(dict(good, sources=changed))
        swapped = dict(good["sources"])
        swapped["src/tail.py"], swapped["src/__init__.py"] = (
            swapped["src/__init__.py"], swapped["src/tail.py"])
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            worker.validate_payload(dict(good, sources=swapped))

    def test_only_builtin_synthetic_task_bytes_are_accepted(self):
        task = worker.synthetic_task()
        variants = [dict(task, synthetic_only=False), dict(task, mode="attempt"),
                    dict(task, repository="real/project"), dict(task, llm="model"),
                    dict(task, issues=task["issues"][:1])]
        for index, variant in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaisesRegex(ValueError, "built-in synthetic task"):
                    worker.validate_payload(self.payload(
                        task_hex=worker.encoded(variant).hex()))
        pretty = json.dumps(task, sort_keys=True).encode("ascii").hex()
        with self.assertRaisesRegex(ValueError, "built-in synthetic task"):
            worker.validate_payload(self.payload(task_hex=pretty))

    def test_payload_reference_goes_through_reference_contract(self):
        bad = raw(bundle(synthetic_only=False)).hex()
        with self.assertRaisesRegex(ValueError, "synthetic experience"):
            worker.validate_payload(self.payload(reference_hex=bad))
        with self.assertRaisesRegex(ValueError, "byte cap"):
            worker.validate_payload(self.payload(reference_hex=""))


class ReferenceContractTests(unittest.TestCase):
    def test_valid_bundles_return_the_parsed_document(self):
        self.assertEqual(worker.validate_reference(raw(bundle())), bundle())
        empty = bundle(snapshot_sha256=None, records=[],
                       counts={"active_members": 0, "eligible": 0, "returned": 0,
                               "dropped": 0})
        self.assertEqual(worker.validate_reference(raw(empty))["records"], [])

    def test_non_synthetic_or_non_experience_reference_is_rejected(self):
        for overrides in (dict(synthetic_only=False), dict(synthetic_only=1),
                          dict(synthetic_only="true"), dict(reference_data_only=False),
                          dict(reference_data_only=None), dict(partition="development"),
                          dict(partition="holdout"),
                          dict(schema_version="agent-sleep-reference-bundle/2")):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "synthetic experience"):
                    worker.validate_reference(raw(bundle(**overrides)))

    def test_bundle_keys_are_exact(self):
        missing = bundle()
        del missing["policy"]
        for label, doc in (("extra", bundle(instructions="run this")),
                           ("missing", missing), ("list", [bundle()]),
                           ("string", "bundle"), ("null", None)):
            with self.subTest(case=label):
                with self.assertRaisesRegex(ValueError, "exact reference bundle keys"):
                    worker.validate_reference(raw(doc))

    def test_record_and_snapshot_shape(self):
        one = bundle()["counts"]
        cases = [
            (dict(records={"rank": 1}), "bounded list"),
            (dict(records=["text"]), "bounded list"),
            (dict(records=[{}] * (worker.MAX_REFERENCE_RECORDS + 1)), "bounded list"),
            (dict(records=[]), "count mismatch"),
            (dict(counts=dict(one, returned=True)), "count mismatch"),
            (dict(counts=dict(one, returned=1.0)), "count mismatch"),
            (dict(counts=[1]), "count mismatch"),
            (dict(snapshot_sha256=None), "require a snapshot"),
            (dict(snapshot_sha256="A" * 64), "snapshot sha256"),
            (dict(snapshot_sha256="a" * 63), "snapshot sha256"),
            (dict(snapshot_sha256=7), "snapshot sha256"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=tuple(overrides)):
                with self.assertRaisesRegex(ValueError, message):
                    worker.validate_reference(raw(bundle(**overrides)))

    def test_size_cap_applies_before_parsing(self):
        padded = raw(bundle(records=[{"rank": 1, "claim": "x" * worker.MAX_REFERENCE_BYTES}]))
        self.assertGreater(len(padded), worker.MAX_REFERENCE_BYTES)
        for label, data in (("empty", b""), ("oversize", padded),
                            ("text", raw(bundle()).decode("utf-8")),
                            ("bytearray", bytearray(raw(bundle())))):
            with self.subTest(case=label):
                with self.assertRaisesRegex(ValueError, "byte cap"):
                    worker.validate_reference(data)

    def test_strict_json_rejects_ambiguous_encodings(self):
        good = raw(bundle())
        duplicate = good[:-1] + b',"synthetic_only":true}'
        nan = raw(bundle()).replace(b'"dropped":0', b'"dropped":NaN')
        overflow = raw(bundle()).replace(b'"dropped":0', b'"dropped":1e999')
        self.assertNotEqual(nan, good)
        self.assertNotEqual(overflow, good)
        for label, data in (("duplicate", duplicate), ("nan", nan), ("overflow", overflow),
                            ("bom", b"\xef\xbb\xbf" + good), ("utf8", good + b"\xff"),
                            ("trailing", good + b"{}"), ("truncated", good[:-1]),
                            ("deep", b"[" * 5000)):
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    worker.validate_reference(data)
        self.assertEqual(worker.strict_json(b' {"a": [1, 2.5, null]} '),
                         {"a": [1, 2.5, None]})


class LoaderTests(StandInCase):
    def test_load_order_is_reviewed_order_not_mapping_order(self):
        shuffled = {name: self.sources[name] for name in reversed(list(self.sources))}
        modules = worker.load_sources(shuffled)
        expected = ["src", "src.pkg", "src.pkg.leaf", "src.tail"]
        self.assertEqual(list(modules), expected)
        self.assertEqual(modules["src"].ORDER, expected)
        self.assertIs(modules["src.pkg"].leaf, modules["src.pkg.leaf"])
        self.assertIs(sys.modules["src.tail"], modules["src.tail"])
        self.assertTrue(modules["src.tail"].__file__.startswith("oss-pinned:"))

    def test_worker_future_flags_do_not_leak_into_loaded_code(self):
        modules = worker.load_sources(dict(self.sources))
        self.assertIs(modules["src.pkg.leaf"].typed.__annotations__["value"], int)

    def test_yaml_shim_denies_every_load(self):
        worker.load_sources(dict(self.sources))
        with self.assertRaises(PermissionError):
            sys.modules["yaml"].safe_load("a: 1")

    def test_unreviewed_bytes_are_never_compiled_or_registered(self):
        yaml_before = sys.modules.get("yaml")
        tampered = dict(self.sources)
        tampered["src/tail.py"] = b"raise SystemExit('unreviewed code executed')\n"
        cases = [tampered, dict(self.sources, **{"src/extra.py": b""}),
                 {k: v for k, v in self.sources.items() if k != "src/tail.py"},
                 {k: v.decode("ascii") for k, v in self.sources.items()},
                 list(self.sources.items()), None]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                # Module-level shadow: only the worker's own compile lookups see it.
                with mock.patch.object(worker, "compile", create=True) as compiler:
                    with self.assertRaises(ValueError):
                        worker.load_sources(case)
                compiler.assert_not_called()
        self.assertNotIn("src", sys.modules)
        self.assertIs(sys.modules.get("yaml"), yaml_before)

    def test_reload_in_a_used_process_is_refused(self):
        worker.load_sources(dict(self.sources))
        with self.assertRaisesRegex(RuntimeError, "fresh process"):
            worker.load_sources(dict(self.sources))


class LoaderFailureTests(StandInCase):
    sources = {"src/__init__.py": b"import sys\nsys.modules['executed_marker'] = sys\n",
               "src/broken.py": b"def (:\n"}

    def test_syntax_error_anywhere_executes_nothing(self):
        with self.assertRaises(SyntaxError):
            worker.load_sources(dict(self.sources))
        self.assertNotIn("executed_marker", sys.modules)
        self.assertNotIn("src", sys.modules)


class PlanTests(unittest.TestCase):
    def test_child_before_parent_or_foreign_path_is_rejected(self):
        for names in (["src/pkg/leaf.py", "src/__init__.py", "src/pkg/__init__.py"],
                      ["src/leaf.py"], ["src/__init__.py", "src/pkg/leaf.py"],
                      ["other/__init__.py"], ["src/__init__.py", "src/data.json"],
                      ["src/__init__.py", "src/../evil.py"],
                      ["src/__init__.py", "src/a-b.py"]):
            with self.subTest(names=names):
                with mock.patch.object(worker, "SOURCE_HASHES", dict.fromkeys(names, "")):
                    with self.assertRaises(ValueError):
                        worker.module_plan()

    def test_embedded_pins_are_well_formed_and_loadable_in_order(self):
        # Shape only: the pins are NOT verified against any target checkout.
        hexdigits = set("0123456789abcdef")
        for name, value in worker.SOURCE_HASHES.items():
            self.assertTrue(len(value) == 64 and hexdigits.issuperset(value), name)
        self.assertTrue(len(worker.AGENT_COMMIT) == 40
                        and hexdigits.issuperset(worker.AGENT_COMMIT))
        plan = worker.module_plan()
        self.assertEqual([path for _, path, _ in plan], list(worker.SOURCE_HASHES))
        self.assertEqual(plan[0], ("src", "src/__init__.py", True))
        self.assertIn(("src.collector.pipeline", "src/collector/pipeline.py", False), plan)

    def test_fabricated_bytes_for_real_pins_are_rejected(self):
        fake = {name: b"# not the reviewed file\n" for name in worker.SOURCE_HASHES}
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            worker.check_sources(fake)
        payload = dict(sources={name: data.hex() for name, data in fake.items()},
                       task_hex=worker.encoded(worker.synthetic_task()).hex(),
                       reference_hex=raw(bundle()).hex())
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            worker.validate_payload(payload)
        self.assertEqual(worker.synthetic_task()["source_sha256"], worker.SOURCE_HASHES)


if __name__ == "__main__":
    unittest.main()
