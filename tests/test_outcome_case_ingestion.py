import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

root = Path(__file__).parents[1]
specification = importlib.util.spec_from_file_location(
    "validate_outcome_cases", root / "scripts/validate_outcome_cases.py")
validator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(validator)


class OutcomeCaseIngestionTests(unittest.TestCase):
    def test_fixture_validates_but_cannot_qualify_as_independent(self):
        fixture = root / "examples/outcome_study_cases.fixture.json"
        result = validator.validate(fixture)
        self.assertEqual(result["cases"], 1)
        self.assertFalse(result["eligible_for_final_study"])
        with self.assertRaisesRegex(ValueError, "independently authored"):
            validator.validate(fixture, require_independent=True)

    def test_duplicate_missing_permission_and_unapproved_confidential_data_fail(self):
        fixture = json.loads((root / "examples/outcome_study_cases.fixture.json").read_text())
        mutations = []
        missing_permission = json.loads(json.dumps(fixture))
        missing_permission["contributor"]["permission_to_use"] = False
        mutations.append(missing_permission)
        duplicate = json.loads(json.dumps(fixture))
        duplicate["cases"].append(duplicate["cases"][0])
        mutations.append(duplicate)
        confidential = json.loads(json.dumps(fixture))
        confidential["cases"][0]["confidential_material"] = "customer-data"
        mutations.append(confidential)
        with tempfile.TemporaryDirectory() as directory:
            for index, mutation in enumerate(mutations):
                path = Path(directory) / f"invalid-{index}.json"
                path.write_text(json.dumps(mutation))
                with self.assertRaises(ValueError):
                    validator.validate(path)
