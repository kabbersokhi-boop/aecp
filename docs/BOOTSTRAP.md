# Bootstrap the private repository

Target: `kabbersokhi-boop/agent-economic-control-plane`.

The starter can be run locally before publication. A new GitHub repository was **not created by the starter's authoring environment**: its connected GitHub actions allowed repository reads and file writes but did not expose repository creation. The script below performs that step using the owner's authenticated GitHub CLI. No personal access token needs to be shared in chat.

## One-time publication

Extract the ZIP outside any existing Git repository. Use a local terminal with Python 3.11+, Git, and the GitHub CLI installed. Authenticate with `gh auth login` as `kabbersokhi-boop` if not already authenticated. From the extracted project directory, run:

```bash
bash scripts/publish_private_repo.sh
```

The script checks the account and working directory, runs the foundation tests, initializes a main-branch commit if needed, creates the target with `--private` or verifies an existing target is private, and pushes without force. It refuses a public target, an unrelated origin, another logged-in account, an existing non-main branch, and uncommitted changes. It does not overwrite history or change visibility.

If a private target already contains unrelated commits, the normal push should be rejected; do not force it. Integrate the starter intentionally instead. Do not run this bootstrap from another project.

## Start Codex

Select the newly created repository in a Codex environment that can access it. Access granted to one GitHub connection does not prove another connection can see a newly created private repository. Use the normal repository-access settings if it is not listed; do not share tokens in a prompt.

The mission is in `docs/CODEX_FIRST_RUN.md`. Root `AGENTS.md` carries durable engineering constraints; the mission carries the concrete first-build acceptance target. Codex should work on a review branch and should not publish, deploy, change visibility, buy services, or use paid inference during the build.

The foundation needs no runtime dependencies beyond Python's standard library. The first application build may install justified dependencies during setup and must document/lock them. The deterministic application itself must run without external services or API keys.

## CLI reference

GitHub CLI documents private creation and local-source push options at:

`https://cli.github.com/manual/gh_repo_create`

OpenAI documents repository instructions at:

`https://developers.openai.com/codex/guides/agents-md`

These are references, not claims that a remote creation or Codex run has already occurred.
