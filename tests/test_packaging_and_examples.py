"""Consistency of packaged schemas, pins, entry point, and the repository's synthetic examples."""

import importlib
import importlib.metadata
import tomllib
import unittest

import support

from agent_sleep_lab.validation import CONTRACTS, validate_bytes
from agent_sleep_lab.strictjson import loads_strict_bytes

ROOT = support.ROOT


class SchemaCopyTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "schemas").is_dir(), "repository schemas/ not present")
    def test_packaged_schemas_identical_to_repository_schemas(self):
        for contract in CONTRACTS.values():
            with self.subTest(schema=contract.schema_file):
                repo = (ROOT / "schemas" / contract.schema_file).read_bytes()
                packaged = (support.SRC / "agent_sleep_lab" / "schemas" / contract.schema_file).read_bytes()
                self.assertEqual(repo, packaged)

    def test_packaged_schemas_parse_strictly(self):
        for contract in CONTRACTS.values():
            path = support.SRC / "agent_sleep_lab" / "schemas" / contract.schema_file
            self.assertIsInstance(loads_strict_bytes(path.read_bytes()), dict)


class PinTests(unittest.TestCase):
    def setUp(self):
        with open(ROOT / "pyproject.toml", "rb") as fh:
            self.pyproject = tomllib.load(fh)

    def _requirements(self):
        lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        return sorted(x.strip() for x in lines if x.strip() and not x.lstrip().startswith("#"))

    def test_requirements_match_pyproject_dependencies(self):
        self.assertEqual(self._requirements(), sorted(self.pyproject["project"]["dependencies"]))

    def test_dependencies_are_exactly_pinned(self):
        for dep in self.pyproject["project"]["dependencies"]:
            self.assertRegex(dep, r"^[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*$")

    def test_installed_versions_match_pins(self):
        for dep in self.pyproject["project"]["dependencies"]:
            name, version = dep.split("==")
            self.assertEqual(importlib.metadata.version(name), version, f"{name} differs from pin")

    def test_package_data_and_entry_point(self):
        self.assertIn("schemas/*.json", self.pyproject["tool"]["setuptools"]["package-data"]["agent_sleep_lab"])
        target = self.pyproject["project"]["scripts"]["agent-sleep-lab"]
        module, func = target.split(":")
        self.assertTrue(callable(getattr(importlib.import_module(module), func)))


@unittest.skipUnless((ROOT / "examples").is_dir(), "repository examples/ not present")
class SyntheticExampleTests(unittest.TestCase):
    def check(self, kind, name):
        result = validate_bytes(kind, (ROOT / "examples" / name).read_bytes())
        self.assertTrue(result.valid, [d.render() for d in result.report.diagnostics])
        return result

    def test_events_example(self):
        self.assertEqual(self.check("events", "events.synthetic.jsonl").records, 4)

    def test_memory_example(self):
        self.assertEqual(self.check("memory", "memory.candidates.synthetic.json").records, 1)

    def test_promotion_example(self):
        self.assertEqual(self.check("promotion", "promotion-request.synthetic.json").records, 1)

    def test_synthetic_promotion_stays_a_proposal(self):
        document = loads_strict_bytes((ROOT / "examples" / "promotion-request.synthetic.json").read_bytes())
        self.assertIs(document["proposal_only"], True)


if __name__ == "__main__":
    unittest.main()
