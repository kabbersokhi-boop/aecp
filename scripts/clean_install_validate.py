"""Install a wheel outside the source tree and exercise a separately copied scoped consumer."""

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def validate(wheel: Path, output: Path) -> dict:
    wheel = wheel.resolve(strict=True)
    if output.exists():
        raise ValueError("refusing existing evidence")
    repository = Path(__file__).resolve().parents[1]
    installer = shutil.which("uv")
    if not installer:
        raise ValueError("uv is required only for this installation verification harness")
    started = time.perf_counter()
    environment = {"PATH": os.defpath}
    with tempfile.TemporaryDirectory(prefix="aecp-clean-install-") as directory:
        root = Path(directory)
        consumer = root / "independent-consumer"
        consumer.mkdir()
        for path in (repository / "examples/semantic_consumer").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                           else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                if any(module == "aecp" or module.startswith("aecp.") for module in modules):
                    raise ValueError("consumer must not import AECP internals")
            shutil.copy2(path, consumer / path.name)
        shutil.copy2(repository / "scripts/isolation_validate.py", root / "operator_harness.py")
        local_wheel = root / wheel.name
        shutil.copy2(wheel, local_wheel)
        subprocess.run([installer, "venv", "--offline", "--python", sys.executable, str(root / "venv")],
                       cwd=root, env=environment, check=True, capture_output=True, timeout=60)
        python = root / "venv/bin/python"
        subprocess.run([installer, "pip", "install", "--offline", "--python", str(python), str(local_wheel)],
                       cwd=root, env=environment, check=True, capture_output=True, timeout=60)
        installed = time.perf_counter()
        origin = subprocess.check_output([str(python), "-c", "import aecp; print(aecp.__file__)"],
                                         cwd=root, env=environment, text=True).strip()
        if not Path(origin).resolve().is_relative_to(root / "venv"):
            raise ValueError("installed package resolved outside clean environment")
        evidence_path = root / "isolation.json"
        subprocess.run([str(python), "operator_harness.py", "--consumer-dir", str(consumer),
                        "--output", str(evidence_path)], cwd=root, env=environment,
                       check=True, capture_output=True, timeout=180)
        evidence = json.loads(evidence_path.read_text())
        if not all(evidence["isolation_checks"].values()) or not evidence["audit"]["consistent"]:
            raise ValueError("isolated public interface checks failed")
        cases = evidence["operator_evaluation"]["cases"]
        result = {"version": "clean-wheel-consumer.v3", "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                  "installed_from_wheel": True, "source_tree_on_pythonpath": False,
                  "consumer_internal_imports": False, "provider_environment_inherited": False,
                  "package_origin": "fresh virtual environment site-packages",
                  "install_seconds": round(installed - started, 3),
                  "total_validation_seconds": round(time.perf_counter() - started, 3),
                  "cases": len(cases), "verified": sum(case["outcome"]["verified"] for case in cases),
                  "checks": evidence["isolation_checks"], "audit": evidence["audit"],
                  "provider_calls": 0, "outside_human_validation": False,
                  "scope": "separate clean consumer project, installed wheel server, native HTTP; "
                           "development tasks and fake-provider ambiguity, not fresh live model evidence"}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("var/evidence-v3/clean-install.json"))
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.wheel, arguments.output)))
