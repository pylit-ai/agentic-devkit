"""Minimal repo census for brownfield preflight. Stdlib only."""
from pathlib import Path


def census(root: Path) -> dict:
    root = Path(root).resolve()
    out = {
        "manifests": [],
        "ci": [],
        "lockfiles": [],
        "has_makefile": (root / "Makefile").exists(),
        "test_dirs": [],
        "docs_dirs": [],
    }
    for p in root.iterdir():
        if p.is_file():
            if p.name in (
                "package.json",
                "pyproject.toml",
                "Cargo.toml",
                "go.mod",
                "requirements.txt",
            ):
                out["manifests"].append(p.name)
            if p.name in (
                "uv.lock",
                "package-lock.json",
                "yarn.lock",
                "Cargo.lock",
                "poetry.lock",
            ):
                out["lockfiles"].append(p.name)
        elif p.is_dir() and not p.name.startswith("."):
            if p.name in ("tests", "test", "__tests__", "spec"):
                out["test_dirs"].append(p.name)
            if p.name == "docs":
                out["docs_dirs"].append(p.name)
    ci = root / ".github" / "workflows"
    if ci.exists():
        out["ci"].extend(
            f.name for f in ci.iterdir() if f.suffix in (".yml", ".yaml")
        )
    return out


def to_yaml(obj, indent=0):
    """Minimal YAML dump (stdlib only)."""
    spaces = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{spaces}{k}:")
                lines.append(to_yaml(v, indent + 1))
            else:
                if v is True:
                    v = "true"
                elif v is False:
                    v = "false"
                elif isinstance(v, str) and (":" in v or "\n" in v or v == ""):
                    v = repr(v)
                lines.append(f"{spaces}{k}: {v}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return f"{spaces}[]"
        return "\n".join(f"{spaces}- {item}" for item in obj)
    return str(obj)


def write_census_yaml(path: Path, out_file: str = ".agentic-bootstrap.yml") -> Path:
    """Run census on path and write YAML to path/out_file. Returns path to written file."""
    root = Path(path).resolve()
    out_path = Path(out_file)
    dest = out_path if out_path.is_absolute() else root / out_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(to_yaml(census(path)))
    return dest
