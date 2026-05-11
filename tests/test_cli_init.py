from pathlib import Path

from agentic_devkit import cli


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
