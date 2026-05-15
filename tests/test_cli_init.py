from pathlib import Path

from agentic_devkit import cli
from agentic_devkit.planning_harness import apply_planning_harness


def test_cmd_init_uses_bundled_source_when_available(monkeypatch):
    monkeypatch.delenv("AGENTIC_DEV_GREENFIELD_SOURCE", raising=False)
    monkeypatch.setattr(cli, "_bundled_greenfield_path", lambda: Path("/tmp/bundled-greenfield"))

    seen = {}

    def _fake_run_copier(source: str, dest: Path) -> int:
        seen["source"] = source
        seen["dest"] = dest
        return 0

    monkeypatch.setattr(cli.Path, "is_dir", lambda _: True)
    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_init("demo-app")

    assert rc == 0
    assert seen["source"] == "/tmp/bundled-greenfield"
    assert seen["dest"] == Path("demo-app").resolve()


def test_cmd_init_rejects_placeholder_source(monkeypatch, capsys):
    monkeypatch.delenv("AGENTIC_DEV_GREENFIELD_SOURCE", raising=False)
    monkeypatch.setattr(cli, "_bundled_greenfield_path", lambda: Path("/tmp/missing-greenfield"))
    monkeypatch.setattr(cli.Path, "is_dir", lambda _: False)

    called = {"ran": False}

    def _fake_run_copier(source: str, dest: Path) -> int:
        called["ran"] = True
        return 0

    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_init("demo-app")
    out = capsys.readouterr()

    assert rc == 2
    assert called["ran"] is False
    assert "no usable greenfield template source found" in out.err.lower()
    assert "AGENTIC_DEV_GREENFIELD_SOURCE" in out.err


def test_cmd_init_uses_configured_source(monkeypatch):
    source = "gh:acme/agentic-dev-greenfield"
    monkeypatch.setenv("AGENTIC_DEV_GREENFIELD_SOURCE", source)

    seen = {}

    def _fake_run_copier(run_source: str, run_dest: Path) -> int:
        seen["source"] = run_source
        seen["dest"] = run_dest
        return 0

    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_init("demo-app")

    assert rc == 0
    assert seen["source"] == source
    assert seen["dest"] == Path("demo-app").resolve()


def test_cmd_init_private_overlay_defaults_to_public_sibling_from_private_repo(tmp_path, monkeypatch):
    public = tmp_path / "example-app"
    private = tmp_path / "example-app-private"
    private.mkdir()
    monkeypatch.chdir(private)
    monkeypatch.setattr(cli, "_greenfield_source", lambda: "/tmp/template")

    seen = {}

    def _fake_run_copier(source: str, dest: Path) -> int:
        seen["source"] = source
        seen["dest"] = dest
        (dest / "AGENTS.md").write_text("template agent instructions", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_init("example-app", private_overlay=True)

    assert rc == 0
    assert seen == {"source": "/tmp/template", "dest": private.resolve()}
    assert public.is_dir()
    assert not (public / "AGENTS.md").exists()
    assert (private / "AGENTS.md").read_text(encoding="utf-8").startswith("# AGENTS.md - Private Overlay")
    assert "Public sibling: `../example-app`" in (private / "AGENTS.md").read_text(encoding="utf-8")
    assert (private / ".agentic-private-overlay.yml").read_text(encoding="utf-8") == (
        "version: 1\n"
        "repo_slug: example-app\n"
        "mode: greenfield\n"
        "public_repo: ../example-app\n"
        "private_repo: .\n"
    )
    assert (private / "overlays" / "public-patches" / ".gitkeep").exists()
    assert (private / "scripts" / "apply_public_overlay.sh").exists()
    assert (private / "scripts" / "leak_check.sh").exists()


def test_cmd_overlay_private_overlay_uses_explicit_private_repo(tmp_path, monkeypatch):
    public = tmp_path / "legacy"
    private = tmp_path / "legacy-private"
    public.mkdir()
    monkeypatch.setattr(cli, "_brownfield_source", lambda: "/tmp/brownfield-template")

    seen = {}

    def _fake_run_copier(source: str, dest: Path) -> int:
        seen["source"] = source
        seen["dest"] = dest
        (dest / "AGENTS.md").write_text("template agent instructions", encoding="utf-8")
        return 0

    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_overlay(str(public), intake=False, private_overlay=True, private_repo=str(private))

    assert rc == 0
    assert seen == {"source": "/tmp/brownfield-template", "dest": private.resolve()}
    assert not (public / "AGENTS.md").exists()
    assert (private / "AGENTS.md").read_text(encoding="utf-8").startswith("# AGENTS.md - Private Overlay")
    config = (private / ".agentic-private-overlay.yml").read_text(encoding="utf-8")
    assert "repo_slug: legacy\n" in config
    assert "mode: brownfield\n" in config
    assert "public_repo: ../legacy\n" in config


def test_cmd_overlay_private_overlay_writes_intake_to_private_repo(tmp_path, monkeypatch):
    public = tmp_path / "legacy"
    private = tmp_path / "legacy-private"
    public.mkdir()
    monkeypatch.setattr(cli, "_brownfield_source", lambda: "/tmp/brownfield-template")

    seen = {}

    def _fake_write_census(path: Path, out_file: str = ".agentic-bootstrap.yml") -> Path:
        seen["census_path"] = path
        seen["out_file"] = Path(out_file)
        return Path(out_file)

    def _fake_run_copier(source: str, dest: Path) -> int:
        seen["source"] = source
        seen["dest"] = dest
        return 0

    monkeypatch.setattr(cli, "write_census_yaml", _fake_write_census)
    monkeypatch.setattr(cli, "_run_copier", _fake_run_copier)

    rc = cli.cmd_overlay(str(public), intake=True, private_overlay=True, private_repo=str(private))

    assert rc == 0
    assert seen["census_path"] == public.resolve()
    assert seen["out_file"] == private.resolve() / ".agentic-bootstrap.yml"
    assert seen["dest"] == private.resolve()


def test_private_overlay_path_options_require_private_overlay(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_run_copier", lambda _source, _dest: 0)

    init_rc = cli.cmd_init("demo-app", public_repo="../demo-app")
    overlay_rc = cli.cmd_overlay(".", intake=False, private_repo="../demo-app-private")
    out = capsys.readouterr()

    assert init_rc == 2
    assert overlay_rc == 2
    assert "--public-repo and --private-repo require --private-overlay" in out.err
    assert "--private-repo requires --private-overlay" in out.err


def test_cmd_overlay_planning_harness_creates_required_layout(tmp_path, monkeypatch):
    repo = tmp_path / "legacy"
    repo.mkdir()

    def _unexpected_copier(_source: str, _dest: Path) -> int:
        raise AssertionError("planning harness adoption should not run Copier")

    monkeypatch.setattr(cli, "_run_copier", _unexpected_copier)

    rc = cli.cmd_overlay(str(repo), intake=False, planning_harness=True)

    assert rc == 0
    assert (repo / "AGENTS.md").is_file()
    assert (repo / "docs/strategy-briefs/active").is_dir()
    assert (repo / "docs/exec-plans/active").is_dir()
    assert (repo / "status/CURRENT.md").is_file()
    assert (repo / ".codex/config.toml").is_file()
    assert (repo / ".codex/agents/planner.toml").is_file()
    assert (repo / "tools/policy/check_planning_harness.py").is_file()


def test_cmd_overlay_planning_harness_writes_merge_candidates(tmp_path):
    repo = tmp_path / "legacy"
    repo.mkdir()
    existing_agents = repo / "AGENTS.md"
    existing_agents.write_text("# Existing agent rules\n", encoding="utf-8")

    rc = cli.cmd_overlay(str(repo), intake=False, planning_harness=True)

    assert rc == 0
    assert existing_agents.read_text(encoding="utf-8") == "# Existing agent rules\n"
    assert (repo / "AGENTS.md.new").is_file()


def test_cmd_overlay_dry_run_requires_planning_harness(tmp_path, capsys):
    repo = tmp_path / "legacy"
    repo.mkdir()

    rc = cli.cmd_overlay(str(repo), intake=False, dry_run=True)
    out = capsys.readouterr()

    assert rc == 2
    assert "--dry-run, --replace, and --planning-harness-pack require --planning-harness" in out.err


def test_planning_harness_reads_metactl_pack_snippet_interface(tmp_path):
    repo = tmp_path / "legacy"
    repo.mkdir()
    pack = tmp_path / "pack"
    snippet = pack / "codex-planning-harness/snippets/AGENTS.md.addition.md"
    snippet.parent.mkdir(parents=True)
    snippet.write_text("## Canonical Planning Harness\n", encoding="utf-8")

    apply_planning_harness(repo, pack_root=pack)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "## Canonical Planning Harness\n"


def test_planning_harness_projects_pack_template_tree(tmp_path):
    repo = tmp_path / "legacy"
    repo.mkdir()
    pack = tmp_path / "pack"
    template = pack / "codex-planning-harness/templates/repo"
    marker = template / "docs/generated/from-pack.md"
    verifier = template / "tools/verify/run_targeted.sh"
    marker.parent.mkdir(parents=True)
    verifier.parent.mkdir(parents=True)
    marker.write_text("# From Pack\n", encoding="utf-8")
    verifier.write_text("#!/bin/sh\necho targeted\n", encoding="utf-8")
    verifier.chmod(0o755)

    apply_planning_harness(repo, pack_root=pack)

    assert (repo / "docs/generated/from-pack.md").read_text(encoding="utf-8") == "# From Pack\n"
    assert (repo / "tools/verify/run_targeted.sh").read_text(encoding="utf-8").startswith(
        "#!/bin/sh"
    )
    assert (repo / "tools/verify/run_targeted.sh").stat().st_mode & 0o111


def test_cmd_overlay_planning_harness_pack_option_projects_templates(tmp_path):
    repo = tmp_path / "legacy"
    repo.mkdir()
    pack = tmp_path / "pack"
    template = pack / "codex-planning-harness/templates/repo"
    strategy = template / "docs/strategy-briefs/active/StrategyBrief.template.md"
    strategy.parent.mkdir(parents=True)
    strategy.write_text("# StrategyBrief: from pack\n", encoding="utf-8")

    rc = cli.cmd_overlay(
        str(repo),
        intake=False,
        planning_harness=True,
        planning_harness_pack=str(pack),
    )

    assert rc == 0
    assert (repo / "docs/strategy-briefs/active/StrategyBrief.template.md").read_text(
        encoding="utf-8"
    ) == "# StrategyBrief: from pack\n"
