"""Thin adapter for adopting the Codex Planning Harness."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACK_ROOT = Path("/Users/reynard/src/wx-b/metactl-library/packs/wxb-pack-codex-planning-harness")

_PACK_SOURCE_ROOTS = (
    Path("codex-planning-harness/templates/repo"),
    Path("templates/repo"),
    Path("agentic-devkit"),
    Path("template"),
    Path("templates/default"),
    Path("files"),
    Path("codex-planning-harness"),
    Path("."),
)

_PACK_SPECIAL_FILES = {
    "AGENTS.md": (
        Path("codex-planning-harness/snippets/AGENTS.md.addition.md"),
        Path("snippets/AGENTS.md.addition.md"),
    ),
}

_REQUIRED_DIRS = (
    "docs/architecture/domain-maps",
    "docs/strategy-briefs/active",
    "docs/strategy-briefs/completed",
    "docs/exec-plans/active",
    "docs/exec-plans/completed",
    "docs/runbooks",
    "docs/references",
    "docs/generated",
    "status",
    "evals/historical_tasks",
    "evals/graders",
    "evals/traces",
    "tools/harness",
    "tools/verify",
    "tools/policy",
    ".codex/agents",
    ".github/workflows",
)

_FALLBACK_FILES = {
    "AGENTS.md": """# AGENTS.md

## Mission
Preserve correctness, reduce long-term complexity, and keep diffs reviewable.

## Default Workflow
For non-trivial tasks:
1. Explore read-only.
2. Produce `docs/strategy-briefs/active/<task>.md`.
3. Run a skeptic pass.
4. Produce `docs/exec-plans/active/<task>.md`.
5. Execute only from the accepted ExecPlan.
6. Verify before claiming completion.

## Planning Requirements
A StrategyBrief must include the problem statement, relevant files/symbols/tests/runtime paths,
unknowns and assumptions, at least three strategies, scoring, recommendation, verification plan,
and stop conditions.

## Execution Requirements
Stay inside the ExecPlan file ownership boundary. Update `status/CURRENT.md` after each milestone.
If verification fails, repair before expanding scope.

## Verification
Run the narrowest relevant checks first, then broader checks when interfaces or runtime behavior changed.

## Escalation
Ask for human review when product behavior is ambiguous, migration/data-loss risk appears, a new
production dependency is needed, verification is impossible, or the chosen strategy changes materially.
""",
    "docs/strategy-briefs/active/README.md": """# Active Strategy Briefs

Place in-progress StrategyBrief files here. Canonical harness content lives in
`/Users/reynard/src/wx-b/metactl-library/packs/wxb-pack-codex-planning-harness/`.
""",
    "docs/exec-plans/active/README.md": """# Active ExecPlans

Place accepted execution plans here before implementation starts.
""",
    "status/CURRENT.md": """# Current Status

## Active Work
- No active Codex Planning Harness work recorded yet.

## Last Verified
- Not verified yet.

## Notes
- Update after each milestone and before completion claims.
""",
    ".codex/config.toml": """# Project-scoped Codex Planning Harness config.
# Canonical role content is maintained by the metactl-library planning harness pack.

approval_policy = "on-request"
sandbox_mode = "workspace-write"
""",
    ".codex/agents/planner.toml": """name = "planner"
description = "Drafts StrategyBriefs and compares implementation strategies before execution."
""",
    ".codex/agents/cartographer.toml": """name = "cartographer"
description = "Maps repository structure, dependencies, ownership, tests, and runtime paths."
""",
    ".codex/agents/skeptic.toml": """name = "skeptic"
description = "Challenges assumptions, migration risk, verifier gaps, and scope expansion."
""",
    ".codex/agents/executor.toml": """name = "executor"
description = "Implements only the accepted ExecPlan within its ownership boundary."
""",
    ".codex/agents/reviewer.toml": """name = "reviewer"
description = "Reviews diffs against the StrategyBrief, ExecPlan, and verifier evidence."
""",
    "tools/policy/check_planning_harness.py": """#!/usr/bin/env python3
from pathlib import Path

REQUIRED = [
    "AGENTS.md",
    "docs/strategy-briefs/active",
    "docs/exec-plans/active",
    "status/CURRENT.md",
    ".codex/agents",
    ".codex/config.toml",
    "tools/policy",
]

missing = [path for path in REQUIRED if not Path(path).exists()]
if missing:
    for path in missing:
        print(f"missing: {path}")
    raise SystemExit(1)
print("planning harness layout ok")
""",
}


@dataclass(frozen=True)
class HarnessWrite:
    """One filesystem action from planning harness adoption."""

    path: Path
    action: str
    reason: str


def apply_planning_harness(
    target: str | Path,
    *,
    pack_root: str | Path | None = None,
    dry_run: bool = False,
    replace: bool = False,
) -> list[HarnessWrite]:
    """Project planning harness files into an existing repo.

    The adapter prefers canonical files from the metactl-library pack when present.
    Missing canonical files fall back to small deterministic shims so adoption can
    proceed while the pack is implemented in parallel.
    """

    target_path = Path(target).resolve()
    if not target_path.is_dir():
        raise ValueError(f"not a directory: {target_path}")

    source_root = Path(pack_root).resolve() if pack_root else DEFAULT_PACK_ROOT
    files = _load_pack_files(source_root)
    actions: list[HarnessWrite] = []

    for rel_dir in _REQUIRED_DIRS:
        dest_dir = target_path / rel_dir
        if dest_dir.is_dir():
            actions.append(HarnessWrite(dest_dir, "exists", "directory already present"))
            continue
        actions.append(HarnessWrite(dest_dir, "create", "required harness directory"))
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        dest = target_path / rel_path
        actions.append(_write_file(dest, content, dry_run=dry_run, replace=replace))

    return actions


def _load_pack_files(pack_root: Path) -> dict[str, str]:
    files = dict(_FALLBACK_FILES)
    if not pack_root.is_dir():
        return files

    for rel_path in _FALLBACK_FILES:
        source = _find_pack_file(pack_root, rel_path)
        if source is not None:
            files[rel_path] = source.read_text(encoding="utf-8")
    return files


def _find_pack_file(pack_root: Path, rel_path: str) -> Path | None:
    for candidate_path in _PACK_SPECIAL_FILES.get(rel_path, ()):
        candidate = pack_root / candidate_path
        if candidate.is_file():
            return candidate
    for root in _PACK_SOURCE_ROOTS:
        candidate = pack_root / root / rel_path
        if candidate.is_file():
            return candidate
    return None


def _write_file(dest: Path, content: str, *, dry_run: bool, replace: bool) -> HarnessWrite:
    dest.parent.mkdir(parents=True, exist_ok=True) if not dry_run else None
    if not dest.exists():
        if not dry_run:
            dest.write_text(content, encoding="utf-8")
        return HarnessWrite(dest, "create", "required harness file")

    current = dest.read_text(encoding="utf-8")
    if current == content:
        return HarnessWrite(dest, "exists", "file already matches")

    if replace:
        if not dry_run:
            dest.write_text(content, encoding="utf-8")
        return HarnessWrite(dest, "replace", "explicit replace requested")

    merge_dest = _merge_candidate_path(dest, content)
    if not dry_run and not merge_dest.exists():
        merge_dest.write_text(content, encoding="utf-8")
    return HarnessWrite(merge_dest, "merge-candidate", f"{dest.name} already exists")


def _merge_candidate_path(dest: Path, content: str) -> Path:
    candidate = dest.with_name(f"{dest.name}.new")
    if not candidate.exists() or candidate.read_text(encoding="utf-8") == content:
        return candidate
    index = 2
    while True:
        numbered = dest.with_name(f"{dest.name}.new.{index}")
        if not numbered.exists() or numbered.read_text(encoding="utf-8") == content:
            return numbered
        index += 1
