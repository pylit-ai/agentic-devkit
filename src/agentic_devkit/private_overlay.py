"""Private companion overlay scaffolding for public/private repo pairs."""

import os
from pathlib import Path

PRIVATE_OVERLAY_DIRS = (
    "overlays/public-patches",
    "overlays/public-files",
    "overlays/retired-public-patches",
    "overlays/retired-public-files",
    "imported-public-agent-artifacts",
    "planning",
    "scripts",
)


def is_simple_path_name(value: str) -> bool:
    path = Path(value)
    return value not in {"", ".", ".."} and not path.is_absolute() and len(path.parts) == 1


def default_public_repo_for_init(dest: str, public_repo: str | None) -> Path:
    if public_repo:
        return Path(public_repo).resolve()
    cwd = Path.cwd().resolve()
    if cwd.name.endswith("-private") and is_simple_path_name(dest):
        return (cwd.parent / dest).resolve()
    return Path(dest).resolve()


def default_private_repo(public_repo: Path, private_repo: str | None) -> Path:
    if private_repo:
        return Path(private_repo).resolve()
    cwd = Path.cwd().resolve()
    if cwd.name.endswith("-private") and cwd != public_repo:
        return cwd
    return (public_repo.parent / f"{public_repo.name}-private").resolve()


def _relpath(from_dir: Path, target: Path) -> str:
    return os.path.relpath(target, from_dir)


def _write_if_missing(path: Path, content: str, executable: bool = False, replace: bool = False) -> bool:
    if path.exists() and not replace:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return True


def _private_overlay_agents(repo_slug: str, public_rel: str, private_rel: str, mode: str) -> str:
    return f"""# AGENTS.md - Private Overlay

## Purpose
This private repository is the active agentic workspace for `{repo_slug}`.

- Public sibling: `{public_rel}`
- Private workspace: `{private_rel}`
- Bootstrap mode: `{mode}`

## Operating Model
- Treat this private `AGENTS.md` as canonical for agent behavior in the repo pair.
- Touch the public sibling only for deliberate public code, public docs, public tests, releases, or overlay application.
- Keep publishable code, public docs, public tests, and public release automation in the public repo.
- Keep private specs, agent protocols, customer or provider details, local automation, generated adapters, private tests, and release guardrails here.
- Ambiguous material stays private until explicit promotion review.

## Read Order
- Start here for repo-pair boundaries and commands.
- Product direction: `NORTHSTAR.md`, `NORTHSTAR_METRICS.md`, `PRD.md`.
- Project rules: `CONSTITUTION.md`, `docs/governance/DOCS_SYSTEM.md`.
- Brownfield state, when present: `CURRENT_STATE.md`, `MIGRATION_GUARDRAILS.md`.
- Active work: `specs/registry.yaml` and `specs/<id>/{{spec.md,plan.md,tasks.md}}`.

## Overlay Layout
- `overlays/public-patches/`: active patches to apply to the public checkout.
- `overlays/public-files/`: active files to copy into the public checkout for local/private testing.
- `overlays/retired-public-patches/`: inactive patches kept only as source material.
- `overlays/retired-public-files/`: inactive files kept only as source material.
- `imported-public-agent-artifacts/`: prior public agent instructions or generated adapters imported for comparison.
- `planning/`: private plans, evidence, reviews, and release notes.
- `scripts/`: private helper scripts, leak checks, and release guards.

## Commands
- Apply active overlays: `scripts/apply_public_overlay.sh {public_rel}`
- Check public sibling for private markers: `scripts/leak_check.sh {public_rel}`

## Boundary Rules
- Do not publish private overlay paths, private repo names, customer names, account identifiers, secret-adjacent config, local model routing, or internal workflow details.
- Do not use `overlays/` for replacement private instructions or local agent config.
- If public docs need a reusable rule, promote only product-generic wording after review.
"""


def _private_overlay_readme(repo_slug: str, public_rel: str) -> str:
    return f"""# {repo_slug} Private Overlay

Private companion workspace for `{repo_slug}`.

- Public repo: `{public_rel}`
- Canonical private instructions: `AGENTS.md`
- Active public changes: `overlays/public-patches/` and `overlays/public-files/`
- Private evidence and plans: `planning/`

Run `scripts/leak_check.sh {public_rel}` before promoting files or patches to the public repo.
"""


def _private_overlay_config(repo_slug: str, public_rel: str, private_rel: str, mode: str) -> str:
    return f"""version: 1
repo_slug: {repo_slug}
mode: {mode}
public_repo: {public_rel}
private_repo: {private_rel}
"""


def _private_overlay_gitignore() -> str:
    return """.DS_Store
.env
.env.*
!.env.example
.codex-goal/
__pycache__/
.pytest_cache/
.mypy_cache/
"""


def _overlay_readme() -> str:
    return """# Public Overlays

Active overlay paths are release-affecting.

- `public-patches/`: patch files applied with `scripts/apply_public_overlay.sh`.
- `public-files/`: files copied into the public checkout for local/private testing.
- `retired-public-patches/` and `retired-public-files/`: source material only.

Move stale active overlays to the retired directories instead of leaving them in the active release path.
"""


def _apply_overlay_script(public_rel: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"
PUBLIC_REPO="${{1:-{public_rel}}}"

if [ ! -d "$PUBLIC_REPO" ]; then
  echo "Public repo not found: $PUBLIC_REPO" >&2
  exit 1
fi

applied=0
while IFS= read -r -d '' patch; do
  git -C "$PUBLIC_REPO" apply --check "$patch"
  git -C "$PUBLIC_REPO" apply "$patch"
  echo "Applied patch: $patch"
  applied=1
done < <(find "$ROOT/overlays/public-patches" -type f -name '*.patch' -print0)

while IFS= read -r -d '' file; do
  rel="${{file#"$ROOT/overlays/public-files/"}}"
  mkdir -p "$PUBLIC_REPO/$(dirname "$rel")"
  cp "$file" "$PUBLIC_REPO/$rel"
  echo "Copied file: $rel"
  applied=1
done < <(find "$ROOT/overlays/public-files" -type f ! -name '.gitkeep' -print0)

if [ "$applied" -eq 0 ]; then
  echo "No active public overlays found."
fi
"""


def _leak_check_script(repo_slug: str, public_rel: str) -> str:
    private_name = f"{repo_slug}-private"
    return f"""#!/usr/bin/env bash
set -euo pipefail

PUBLIC_REPO="${{1:-{public_rel}}}"
PRIVATE_MARKERS='{private_name}|private-overlay|private_overlay|imported-public-agent-artifacts|bootstrap-agent-artifacts|\\.env\\.symphony|LINEAR_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY'

if [ ! -d "$PUBLIC_REPO" ]; then
  echo "Public repo not found: $PUBLIC_REPO" >&2
  exit 1
fi

found=0
if git -C "$PUBLIC_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git -C "$PUBLIC_REPO" grep -n -E "$PRIVATE_MARKERS"; then
    found=1
  fi
else
  while IFS= read -r -d '' file; do
    if grep -n -E "$PRIVATE_MARKERS" "$file"; then
      echo "  in $file"
      found=1
    fi
  done < <(find "$PUBLIC_REPO" -type f -not -path '*/.git/*' -print0)
fi

if [ "$found" -ne 0 ]; then
  echo "Potential private markers found in public repo." >&2
  exit 1
fi

echo "No private markers found in public repo."
"""


def scaffold_private_overlay(
    public_repo: Path,
    private_repo: Path,
    repo_slug: str,
    mode: str,
    replace_agents: bool = False,
) -> list[Path]:
    if public_repo == private_repo:
        raise ValueError("public and private repositories must be different paths")

    private_repo.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    public_rel = _relpath(private_repo, public_repo)
    private_rel = "."

    for rel_dir in PRIVATE_OVERLAY_DIRS:
        directory = private_repo / rel_dir
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if _write_if_missing(gitkeep, ""):
            created.append(gitkeep)

    files = (
        ("AGENTS.md", _private_overlay_agents(repo_slug, public_rel, private_rel, mode), False, replace_agents),
        ("README.md", _private_overlay_readme(repo_slug, public_rel), False),
        (".agentic-private-overlay.yml", _private_overlay_config(repo_slug, public_rel, private_rel, mode), False),
        (".gitignore", _private_overlay_gitignore(), False),
        ("overlays/README.md", _overlay_readme(), False),
        ("scripts/apply_public_overlay.sh", _apply_overlay_script(public_rel), True),
        ("scripts/leak_check.sh", _leak_check_script(repo_slug, public_rel), True),
    )
    for item in files:
        rel_path, content, executable = item[:3]
        replace = item[3] if len(item) > 3 else False
        path = private_repo / rel_path
        if _write_if_missing(path, content, executable=executable, replace=replace):
            created.append(path)
    return created
