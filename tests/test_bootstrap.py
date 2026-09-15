"""Offline orchestration tests. Fake gh/push never contact or create a remote.

The fake python3 deliberately skips nested checks; the real foundation tests
run separately. These tests validate refusal/creation logic, not GitHub auth.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "requires bash and git")
class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.root = base / "project"
        self.bin = base / "bin"
        self.state = base / "state"
        for directory in (self.root / "scripts", self.bin, self.state):
            directory.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "scripts" / "publish_private_repo.sh"
        self.script = self.root / "scripts" / "publish_private_repo.sh"
        shutil.copy(source, self.script)
        (self.root / "README.md").write_text("Offline bootstrap test fixture.\n")
        self.real_git = shutil.which("git")
        self.env = {
            **os.environ,
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "MOCK_STATE": str(self.state),
            "REAL_GIT": str(self.real_git),
            "MOCK_LOGIN": "kabbersokhi-boop",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.executable("python3", "#!/bin/sh\nexit 0\n")
        self.executable("git", '''#!/bin/sh
printf '%s\n' "$*" >> "$MOCK_STATE/git.log"
if [ "$1" = push ]; then exit 0; fi
exec "$REAL_GIT" "$@"
''')
        self.executable("gh", '''#!/bin/sh
printf '%s\n' "$*" >> "$MOCK_STATE/gh.log"
case "$1 $2" in
  'auth status'|'auth setup-git') exit 0 ;;
  'api user') printf '%s\n' "$MOCK_LOGIN" ;;
  'repo view')
    [ -f "$MOCK_STATE/private" ] || exit 1
    cat "$MOCK_STATE/private"
    ;;
  'repo create')
    case " $* " in *' --private '*) ;; *) exit 90 ;; esac
    printf 'true\n' > "$MOCK_STATE/private"
    ;;
  *) exit 91 ;;
esac
''')

    def executable(self, name: str, content: str) -> None:
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(self.script)], cwd=self.root, env=self.env,
                              text=True, capture_output=True, timeout=20)

    def git(self, *args: str) -> None:
        subprocess.run([self.real_git, *args], cwd=self.root, env=self.env,
                       check=True, capture_output=True, text=True)

    def test_new_target_is_created_private_before_nonforce_push(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.state / "gh.log").read_text()
        self.assertIn("repo create kabbersokhi-boop/agent-economic-control-plane --private", calls)
        pushes = [line for line in (self.state / "git.log").read_text().splitlines()
                  if line.startswith("push ")]
        self.assertEqual(pushes, ["push -u origin main"])

    def test_existing_public_target_is_never_pushed_or_changed(self) -> None:
        (self.state / "private").write_text("false\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not verified private", result.stderr)
        self.assertNotIn("push ", (self.state / "git.log").read_text())
        self.assertNotIn("repo create", (self.state / "gh.log").read_text())

    def test_wrong_authenticated_account_is_refused(self) -> None:
        self.env["MOCK_LOGIN"] = "different-user"
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("account mismatch", result.stderr)
        self.assertFalse((self.root / ".git").exists())

    def test_existing_private_target_is_reused_without_creation(self) -> None:
        (self.state / "private").write_text("true\n")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("repo create", (self.state / "gh.log").read_text())

    def test_unrelated_remote_is_refused(self) -> None:
        self.git("init", "-b", "main")
        self.git("remote", "add", "origin", "https://example.invalid/unrelated.git")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrelated origin", result.stderr)
        self.assertNotIn("repo create", (self.state / "gh.log").read_text())

    def test_nonmain_branch_is_not_renamed(self) -> None:
        self.git("init", "-b", "work")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expects main", result.stderr)

    def test_later_uncommitted_changes_are_not_swept_into_a_commit(self) -> None:
        first = self.run_script()
        self.assertEqual(first.returncode, 0, first.stderr)
        (self.root / "README.md").write_text("Uncommitted user work.\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not clean", result.stderr)


if __name__ == "__main__":
    unittest.main()
