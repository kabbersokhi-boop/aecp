"""A frozen study cannot silently change its code, provider or execution identity."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

specification = importlib.util.spec_from_file_location(
    "semantic_protocol", Path(__file__).parents[1] / "scripts/semantic_protocol.py")
protocol = importlib.util.module_from_spec(specification)
specification.loader.exec_module(protocol)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "src/aecp/worker.py"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("version = 1\n")
        self.git("init", "-q")
        self.commit()
        self.path = self.root / "protocol.json"

    def git(self, *arguments):
        return subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Test",
                               "-c", "user.email=test", *arguments], check=True, capture_output=True)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "test checkpoint")

    def frozen(self):
        protocol.freeze(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)
        self.commit()

    def test_freeze_requires_clean_source_and_committed_protocol(self):
        self.source.write_text("version = 2\n")
        with self.assertRaises(ValueError):
            protocol.freeze(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)
        self.commit()
        protocol.freeze(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)
        with self.assertRaises(subprocess.CalledProcessError):
            protocol.validate(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)
        self.commit()
        self.assertEqual(protocol.validate(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)["split"],
                         "heldout")

    def test_source_and_provider_mutations_fail(self):
        self.frozen()
        for model, endpoint in [("changed", protocol.DEFAULT_BASE), ("fixture-model", "https://other.example/v1")]:
            with self.assertRaises(ValueError):
                protocol.validate(self.root, self.path, model, endpoint)
        self.source.write_text("version = 3\n")
        with self.assertRaises(ValueError):
            protocol.validate(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)

    def test_single_claim_survives_output_name_change(self):
        self.frozen()
        record = protocol.validate(self.root, self.path, "fixture-model", protocol.DEFAULT_BASE)
        protocol.claim(self.path, record, self.root / "first.json")
        with self.assertRaises(FileExistsError):
            protocol.claim(self.path, record, self.root / "second.json")
