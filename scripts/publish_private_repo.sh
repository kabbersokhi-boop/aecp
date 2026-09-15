#!/usr/bin/env bash
# Create/verify one private target; never change visibility or force-push.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
OWNER="kabbersokhi-boop"
NAME="agent-economic-control-plane"
REPO="$OWNER/$NAME"
REMOTE="https://github.com/$REPO.git"

for executable in gh git python3; do
    if ! command -v "$executable" >/dev/null 2>&1; then
        printf 'Required command not found: %s\n' "$executable" >&2
        printf 'Install it locally; do not paste credentials into chat.\n' >&2
        exit 1
    fi
done

gh auth status >/dev/null 2>&1 || {
    printf 'Authenticate locally with gh auth login, then rerun this script.\n' >&2
    exit 1
}
LOGIN="$(gh api user --jq .login)"
if [ "$LOGIN" != "$OWNER" ]; then
    printf 'Refusing account mismatch: authenticated as %s; expected %s.\n' "$LOGIN" "$OWNER" >&2
    exit 1
fi

cd "$ROOT"
if TOP="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    if [ "$(cd "$TOP" && pwd -P)" != "$ROOT" ]; then
        printf 'Extract the starter outside another Git repository before running this script.\n' >&2
        exit 1
    fi
else
    git init -b main
fi

BRANCH="$(git symbolic-ref --short HEAD)"
if [ "$BRANCH" != "main" ]; then
    printf 'Refusing to rename or push branch %s; this bootstrap expects main.\n' "$BRANCH" >&2
    exit 1
fi
if ORIGIN="$(git remote get-url origin 2>/dev/null)"; then
    case "$ORIGIN" in
        "$REMOTE"|"https://github.com/$REPO"|"git@github.com:$REPO.git") ;;
        *) printf 'Refusing unrelated origin: %s\n' "$ORIGIN" >&2; exit 1 ;;
    esac
fi

PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m aecp demo-ledger >/dev/null

# Only initialize an uncommitted starter. Never sweep later user changes into a commit.
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    git add --all
    git -c user.name="$LOGIN" \
        -c user.email="$LOGIN@users.noreply.github.com" \
        commit -m "Initialize economic control plane foundation"
fi
if [ -n "$(git status --porcelain)" ]; then
    printf 'Working tree is not clean. Review and commit your changes before publishing.\n' >&2
    exit 1
fi

if ! gh repo view "$REPO" --json isPrivate --jq .isPrivate >/dev/null 2>&1; then
    gh repo create "$REPO" --private \
        --description "Funded agent execution, scarce-resource markets, and reproducible failure experiments."
fi
PRIVATE="$(gh repo view "$REPO" --json isPrivate --jq .isPrivate)"
if [ "$PRIVATE" != "true" ]; then
    printf 'Refusing to push: %s is not verified private. Visibility was not changed.\n' "$REPO" >&2
    exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$REMOTE"
fi
# Uses existing GitHub authentication; never prints or embeds a token.
gh auth setup-git
# An unrelated existing history will be rejected by this non-force push.
git push -u origin main
printf '\nPublished and verified private: %s\n' "$REPO"
printf 'Select this repository in Codex and use docs/CODEX_FIRST_RUN.md.\n'
