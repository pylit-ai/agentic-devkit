"""agentic-dev CLI: init, overlay, intake."""
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

from .census import write_census_yaml
from .planning_harness import apply_planning_harness
from .private_overlay import (
    default_private_repo,
    default_public_repo_for_init,
    scaffold_private_overlay,
)
from .traceability import compile_traceability, diagnostics, load_requirement

DEFAULT_GREENFIELD = "gh:your-org/agentic-dev-greenfield"
DEFAULT_BROWNFIELD = "gh:your-org/agentic-dev-brownfield-overlay"


def _bundled_greenfield_path() -> Path:
    """Path to the greenfield template bundled with the package."""
    return Path(__file__).resolve().parent / "templates" / "greenfield-dev-os"


def _bundled_brownfield_path() -> Path:
    """Path to the brownfield overlay template bundled with the package."""
    return Path(__file__).resolve().parent / "templates" / "brownfield-dev-overlay"


def _greenfield_source() -> str:
    env_source = os.environ.get("AGENTIC_DEV_GREENFIELD_SOURCE")
    if env_source:
        return env_source
    bundled = _bundled_greenfield_path()
    if bundled.is_dir():
        return str(bundled)
    return DEFAULT_GREENFIELD


def _is_placeholder_source(source: str) -> bool:
    return source.strip().startswith("gh:your-org/")


def _brownfield_source() -> str:
    env_source = os.environ.get("AGENTIC_DEV_BROWNFIELD_SOURCE")
    if env_source:
        return env_source
    bundled = _bundled_brownfield_path()
    if bundled.is_dir():
        return str(bundled)
    return DEFAULT_BROWNFIELD


def _run_copier(source: str, dest: Path) -> int:
    dest_str = str(dest.resolve())
    return subprocess.call([sys.executable, "-m", "copier", "copy", source, dest_str])


def _package_version() -> str:
    try:
        return importlib.metadata.version("agentic-devkit")
    except importlib.metadata.PackageNotFoundError:
        return "0+unknown"


def _print_private_overlay_summary(public_repo: Path, private_repo: Path, created: list[Path]) -> None:
    print(f"Private overlay: public={public_repo} private={private_repo}")
    if created:
        print("Private overlay files created:")
        for path in created:
            print(f"  - {path}")
    else:
        print("Private overlay scaffold already present; no files created.")


def cmd_init(
    dest: str,
    private_overlay: bool = False,
    public_repo: str | None = None,
    private_repo: str | None = None,
) -> int:
    """Create a new greenfield repo from template."""
    if (public_repo or private_repo) and not private_overlay:
        print("Error: --public-repo and --private-repo require --private-overlay.", file=sys.stderr)
        return 2

    source = _greenfield_source()
    if _is_placeholder_source(source):
        print(
            "Error: no usable greenfield template source found.",
            file=sys.stderr,
        )
        print(
            "The packaged greenfield template was not found and the fallback "
            f"default is a placeholder ({DEFAULT_GREENFIELD}).",
            file=sys.stderr,
        )
        print(
            "Set AGENTIC_DEV_GREENFIELD_SOURCE to a real template source, for example:",
            file=sys.stderr,
        )
        print(
            "  AGENTIC_DEV_GREENFIELD_SOURCE=gh:<your-org>/<your-template-repo> uvx agentic-devkit init <dest>",
            file=sys.stderr,
        )
        print(
            "or a local template path:",
            file=sys.stderr,
        )
        print(
            "  AGENTIC_DEV_GREENFIELD_SOURCE=./templates/greenfield-dev-os uvx agentic-devkit init <dest>",
            file=sys.stderr,
        )
        return 2
    if not private_overlay:
        dest_path = Path(dest).resolve()
        print(f"Running: copier copy {source} {dest_path}")
        return _run_copier(source, dest_path)

    dest_path = default_public_repo_for_init(dest, public_repo)
    private_path = default_private_repo(dest_path, private_repo)
    dest_path.mkdir(parents=True, exist_ok=True)
    print(f"Public repo prepared: {dest_path}")
    print(f"Running: copier copy {source} {private_path}")
    rc = _run_copier(source, private_path)
    if rc != 0:
        return rc

    try:
        created = scaffold_private_overlay(dest_path, private_path, dest_path.name, "greenfield", replace_agents=True)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    _print_private_overlay_summary(dest_path, private_path, created)
    return 0


def cmd_overlay(
    path: str,
    intake: bool,
    private_overlay: bool = False,
    private_repo: str | None = None,
    planning_harness: bool = False,
    dry_run: bool = False,
    replace: bool = False,
) -> int:
    """Apply brownfield overlay to an existing repo. With --intake, run census first."""
    if private_repo and not private_overlay:
        print("Error: --private-repo requires --private-overlay.", file=sys.stderr)
        return 2
    if (dry_run or replace) and not planning_harness:
        print("Error: --dry-run and --replace require --planning-harness.", file=sys.stderr)
        return 2

    path = Path(path).resolve()
    if not path.is_dir():
        print(f"Error: not a directory: {path}", file=sys.stderr)
        return 1

    if planning_harness:
        try:
            actions = apply_planning_harness(path, dry_run=dry_run, replace=replace)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        prefix = "Would " if dry_run else ""
        print(f"{prefix}Apply Codex Planning Harness to {path}")
        for action in actions:
            rel = action.path.relative_to(path) if action.path.is_relative_to(path) else action.path
            print(f"  - {action.action}: {rel} ({action.reason})")
        print("Canonical source: /Users/reynard/src/wx-b/metactl-library/packs/wxb-pack-codex-planning-harness/")
        if any(action.action == "merge-candidate" for action in actions):
            print("Existing files were not overwritten; review the .new merge candidates.")
        return 0

    source = _brownfield_source()

    if not private_overlay:
        if intake:
            out_path = write_census_yaml(path)
            print(f"Wrote {out_path}")
        print(f"Running: copier copy {source} {path}")
        return _run_copier(source, path)

    private_path = default_private_repo(path, private_repo)
    private_path.mkdir(parents=True, exist_ok=True)
    if intake:
        out_path = write_census_yaml(path, out_file=str(private_path / ".agentic-bootstrap.yml"))
        print(f"Wrote {out_path}")
    print(f"Public repo left unchanged: {path}")
    print(f"Running: copier copy {source} {private_path}")
    rc = _run_copier(source, private_path)
    if rc != 0:
        return rc

    try:
        created = scaffold_private_overlay(path, private_path, path.name, "brownfield", replace_agents=True)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    _print_private_overlay_summary(path, private_path, created)
    return 0


def cmd_intake(path: str) -> int:
    """Print next-step instructions for brownfield intake (no Copier run)."""
    path = Path(path).resolve()
    if not path.is_dir():
        print(f"Error: not a directory: {path}", file=sys.stderr)
        return 1
    print("Brownfield intake — next steps:")
    print()
    print("1. Run preflight census (writes .agentic-bootstrap.yml):")
    print(f"   uvx agentic-devkit overlay {path} --intake")
    print("   or, after overlay: python .agents/skills/repo-os-brownfield-intake/scripts/repo_census.py . --format yaml -o .agentic-bootstrap.yml")
    print()
    print("2. Apply the overlay if you have not yet:")
    print(f"   uvx agentic-devkit overlay {path}")
    print()
    print("3. Run the repo-os-brownfield-intake skill (explicit only) to draft CURRENT_STATE.md and create the first spec.")
    print("   Use your agent's skill or .claude/commands/intake-brownfield.md.")
    return 0


def cmd_trace_compile(repo: str | Path = ".") -> int:
    result = compile_traceability(repo)
    print(f"Wrote {result.graph_path}")
    print(f"Wrote {result.index_path}")
    return 0


def cmd_trace_report(repo: str | Path = ".") -> int:
    result = compile_traceability(repo)
    print(f"Wrote {result.coverage_path}")
    print(f"Wrote {result.ledger_path}")
    print(f"Wrote {result.drift_report_path}")
    print(f"Wrote {result.forgotten_report_path}")
    return 0


def cmd_trace_inspect(requirement_id: str, repo: str | Path = ".") -> int:
    req = load_requirement(requirement_id, repo)
    if req is None:
        print(
            f"Error: requirement {requirement_id} not found. Run `agentic-devkit trace compile` first.",
            file=sys.stderr,
        )
        return 1
    print(f"{req['id']} — {req['status']}")
    print(req["text"])
    print(f"source: {req['source']}:{req['line']}")
    print("tasks:")
    for task in req["tasks"] or []:
        state = "done" if task["done"] else "open"
        print(f"  - {task['id']} ({state}) {task['source']}")
    print("implementation evidence:")
    for path in req["code_entities"] or []:
        print(f"  - {path}")
    print("verifier evidence:")
    for path in req["verifiers"] or []:
        print(f"  - {path}")
    if req["missing"]:
        print("missing:")
        for item in req["missing"]:
            print(f"  - {item}")
    return 0


def cmd_trace_doctor(repo: str | Path = ".") -> int:
    messages = diagnostics(repo)
    if not messages:
        print("No traceability diagnostics found.")
        return 0
    for message in messages:
        print(f"{message}. Suggested remediation: add the smallest code or verifier link that cites the requirement ID.")
    return 1


def cmd_trace_check(repo: str | Path = ".") -> int:
    messages = diagnostics(repo)
    if not messages:
        print("Traceability checks passed.")
        return 0
    for message in messages:
        print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog="agentic-dev",
        description="Init, overlay, or intake for the agentic documentation OS templates.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    sub = ap.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create a new repo from greenfield template")
    p_init.add_argument("dest", help="Destination path (e.g. my-new-repo)")
    p_init.add_argument(
        "--private-overlay",
        action="store_true",
        help="Scaffold a private companion repo beside the public greenfield repo",
    )
    p_init.add_argument("--public-repo", help="Public repo path to use with --private-overlay")
    p_init.add_argument("--private-repo", help="Private overlay repo path to use with --private-overlay")
    p_init.set_defaults(func=lambda a: cmd_init(a.dest, a.private_overlay, a.public_repo, a.private_repo))

    p_overlay = sub.add_parser("overlay", help="Apply brownfield overlay to an existing repo")
    p_overlay.add_argument("path", nargs="?", default=".", help="Repo path (default: .)")
    p_overlay.add_argument("--intake", action="store_true", help="Run repo census first and write .agentic-bootstrap.yml")
    p_overlay.add_argument(
        "--private-overlay",
        action="store_true",
        help="Scaffold or refresh a private companion repo for this public repo",
    )
    p_overlay.add_argument("--private-repo", help="Private overlay repo path to use with --private-overlay")
    p_overlay.add_argument(
        "--planning-harness",
        action="store_true",
        help="Apply the Codex Planning Harness layout without making this package canonical source",
    )
    p_overlay.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planning harness file actions without writing files",
    )
    p_overlay.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing planning harness files instead of writing .new merge candidates",
    )
    p_overlay.set_defaults(
        func=lambda a: cmd_overlay(
            a.path,
            a.intake,
            a.private_overlay,
            a.private_repo,
            a.planning_harness,
            a.dry_run,
            a.replace,
        )
    )

    p_intake = sub.add_parser("intake", help="Show brownfield intake next-step instructions")
    p_intake.add_argument("path", nargs="?", default=".", help="Repo path (default: .)")
    p_intake.set_defaults(func=lambda a: cmd_intake(a.path))

    p_trace = sub.add_parser("trace", help="Compile and inspect requirement evidence")
    trace_sub = p_trace.add_subparsers(dest="trace_command", required=True)

    p_trace_compile = trace_sub.add_parser("compile", help="Build generated traceability graph and index")
    p_trace_compile.add_argument("--repo", default=".", help="Repo path (default: .)")
    p_trace_compile.set_defaults(func=lambda a: cmd_trace_compile(a.repo))

    p_trace_check = trace_sub.add_parser("check", help="Fail when traceability evidence is missing")
    p_trace_check.add_argument("--repo", default=".", help="Repo path (default: .)")
    p_trace_check.set_defaults(func=lambda a: cmd_trace_check(a.repo))

    p_trace_report = trace_sub.add_parser("report", help="Regenerate human-readable traceability reports")
    p_trace_report.add_argument("--repo", default=".", help="Repo path (default: .)")
    p_trace_report.set_defaults(func=lambda a: cmd_trace_report(a.repo))

    p_trace_inspect = trace_sub.add_parser("inspect", help="Inspect a requirement by ID")
    p_trace_inspect.add_argument("requirement_id", help="Requirement ID, for example REQ-login-001")
    p_trace_inspect.add_argument("--repo", default=".", help="Repo path (default: .)")
    p_trace_inspect.set_defaults(func=lambda a: cmd_trace_inspect(a.requirement_id, a.repo))

    p_trace_doctor = trace_sub.add_parser("doctor", help="Explain missing traceability links")
    p_trace_doctor.add_argument("--repo", default=".", help="Repo path (default: .)")
    p_trace_doctor.set_defaults(func=lambda a: cmd_trace_doctor(a.repo))

    args = ap.parse_args()
    return args.func(args)
