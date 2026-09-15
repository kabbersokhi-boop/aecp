"""Publication candidates must fail closed on secrets and disclose report-only redaction."""

import importlib.util
import sys
import unittest
from pathlib import Path

scripts = str(Path(__file__).parents[1] / "scripts")
sys.path.insert(0, scripts)
try:
    specification = importlib.util.spec_from_file_location("public_snapshot", Path(scripts) / "public_snapshot.py")
    snapshot = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(snapshot)
finally:
    sys.path.remove(scripts)


class PublicationTests(unittest.TestCase):
    def test_report_redaction_is_disclosed_and_source_unchanged(self):
        original = b"trace: /" + b"home/" + b"example-person/project/source.py"
        updated, notice = snapshot.sanitize("docs/reports/trace.txt", original)
        self.assertEqual(updated, b"trace: /workspace/project/source.py")
        self.assertEqual(notice["count"], 1)
        self.assertNotEqual(notice["original_sha256"], notice["publication_sha256"])

    def test_secret_database_and_unreviewed_email_fail_closed(self):
        for payload in (b"nvapi-" + b"Z" * 30, b"SQLite format 3\x00", b"real-person" + b"@mail.invalid"):
            with self.subTest(payload_type=payload[:5]):
                with self.assertRaises(ValueError):
                    snapshot.sanitize("data.txt", payload)

    def test_source_paths_require_correction_not_automatic_rewriting(self):
        with self.assertRaises(ValueError):
            snapshot.sanitize("src/module.py", b"/" + b"home/" + b"private-person/project")
