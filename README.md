# agentic-devkit

**Templates and CLI for the agentic documentation OS** — one `AGENTS.md` router, layered docs, spec-driven work. Cursor, Claude, Copilot share one source of truth.

[![PyPI](https://img.shields.io/pypi/v/agentic-devkit.svg)](https://pypi.org/project/agentic-devkit/)  
[**PyPI**](https://pypi.org/project/agentic-devkit/) · [**GitHub**](https://github.com/pylit-ai/agentic-devkit)

<p align="center">
  <img src="https://raw.githubusercontent.com/pylit-ai/agentic-devkit/main/assets/Pyramid.png" alt="Doc hierarchy pyramid" width="560">
</p>

*The doc hierarchy: **NORTHSTAR.md** (the why — vision and long-term goals) → **CONSTITUTION.md** (rules of engagement — ethical and technical boundaries) → **PRD.md** (the what — features and requirements) → **docs/governance/DOCS_SYSTEM.md** (the format — documentation structure) → **context-registry.yaml** (ground truth — RAG mapping to prevent information overload).*

---

## Quick start

```bash
# New repo
uvx agentic-devkit init my-new-repo

# From example-app-private: prepare sibling public repo, put agentic OS in private
uvx agentic-devkit init example-app --private-overlay

# Existing repo
cd my-existing-repo && uvx agentic-devkit overlay .

# From example-app-private: keep public repo product-only, put overlay docs in private
uvx agentic-devkit overlay ../example-app --private-overlay --private-repo .

# Existing repo + prefill CURRENT_STATE from repo structure
uvx agentic-devkit overlay . --intake
```

Requires [uv](https://docs.astral.sh/uv/) (or `pip install agentic-devkit`).

The **init** and **overlay** commands use bundled templates by default, so no GitHub repo or extra config is required. To use your own template source instead, set `AGENTIC_DEV_GREENFIELD_SOURCE` or `AGENTIC_DEV_BROWNFIELD_SOURCE` to a `gh:org/repo` URL or a local path.

---

## What you get

| Template | Use case |
|----------|----------|
| **Greenfield** | New repo: NORTHSTAR, CONSTITUTION, AGENTS.md, PRD, governance, specs, adapters, bootstrap skill. |
| **Brownfield** | Existing repo: CURRENT_STATE, MIGRATION_GUARDRAILS, brownfield AGENTS.md, governance, intake skill. |
| **Private overlay** | Optional companion workspace: agentic docs/adapters stay private; the public sibling is only prepared or referenced. |

Then **point your agent at AGENTS.md** in the new repo. For greenfield, give a one-sentence product brief in the same chat (e.g. *“CLI for dev teams so they can run templates with less setup”*); the agent fills placeholders or asks if it needs more. For brownfield, ask explicitly for “brownfield intake” when you want CURRENT_STATE and the first spec.

For public/private repo pairs, run `--private-overlay` from the private companion directory when it already exists. If the current directory ends in `-private`, `init example-app --private-overlay` prepares sibling `../example-app` but writes the agentic template and private overlay files into the current private directory. The public repo should stay product-only: no root `AGENTS.md`, generated adapters, private overlay docs, or agentic spec/governance trees. Use `--public-repo` or `--private-repo` when the sibling names differ.

<p align="center">
  <img src="https://raw.githubusercontent.com/pylit-ai/agentic-devkit/main/assets/Artifact_generation.png" alt="Artifact generation cycle" width="640">
</p>

*Cycle: **(1) Template initialization** — Copier populates the directory and AGENTS.md. **(2) Skill execution** — invoke a skill from `.agents/skills/`. **(3) Governance verification** — check scripts (e.g. ci.yml) verify output against CONSTITUTION.md.*

<details>
<summary><strong>Greenfield — objectives, prompt, what gets filled</strong></summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/pylit-ai/agentic-devkit/main/assets/Greenfield.png" alt="Greenfield path" width="640">
</p>

***Path A: Greenfield** — Bootstrap → Scaffolding (Makefile, pyproject.toml, .copier-answers) → Baseline context (docs/architecture, docs/mcp) → ready for agent execution.*

**Objectives:** The agent only has the project name from `init` (or “my-product”). You define the rest by saying it in the same message as the bootstrap prompt, or the skill tells the agent to ask for product name, primary user, and core outcome.

**Copy-paste prompt** (add your one-sentence brief first):

```
Run the repo-os-greenfield-bootstrap skill: read AGENTS.md and .agents/skills/repo-os-greenfield-bootstrap/SKILL.md, then fill NORTHSTAR.md, NORTHSTAR_METRICS.md, PRD.md, docs/architecture/overview.md, and specs/001-bootstrap using .agents/skills/repo-os-greenfield-bootstrap/references/rubric.md. Align AGENTS.md with our real commands. Run scripts/check-governance if present.
```

**What gets filled:** NORTHSTAR (mission, personas, thesis, non-goals, kill criteria) · NORTHSTAR_METRICS (gates, headline northstar, diagnostics, stopping rules) · PRD (product, users, scope, stories, requirements) · docs/architecture/overview · specs/001-bootstrap (in-scope, acceptance criteria, verifiers). Cursor: `.agents/skills/repo-os-greenfield-bootstrap/`. Claude: `.claude/commands/bootstrap-repo.md` or repo-bootstrapper subagent.

</details>

<details>
<summary><strong>Brownfield — intake prompt</strong></summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/pylit-ai/agentic-devkit/main/assets/Brownfield.png" alt="Brownfield intake" width="640">
</p>

***Path B: Brownfield intake** — Legacy repo → `repo_census.py` (intake engine) → Machine-readable map (e.g. opencode.json) + Context API (context-registry.yaml).*

Run only when you explicitly ask (e.g. “run brownfield intake” or “draft CURRENT_STATE”).

```
Run the repo-os-brownfield-intake skill: read AGENTS.md and .agents/skills/repo-os-brownfield-intake/SKILL.md. Run the repo census script, draft CURRENT_STATE.md using the brownfield rubric, propose (don’t overwrite) NORTHSTAR/PRD deltas, create the first spec bundle in specs/ and register it. Run scripts/check-governance if present. Give me a short handoff summary.
```

Cursor: `.agents/skills/repo-os-brownfield-intake/`. Claude: `.claude/commands/intake-brownfield.md`.

</details>

<details>
<summary><strong>Key artifacts (NORTHSTAR, AGENTS, PRD, …)</strong></summary>

<p align="center">
  <img src="https://raw.githubusercontent.com/pylit-ai/agentic-devkit/main/assets/Context_Governance_Execution.png" alt="Context, governance, execution" width="640">
</p>

***Strategic context** (why & what): PRD.md, NORTHSTAR.md → **Governance engine** (boundaries): CONSTITUTION.md, verify_governance.sh → **Execution engine** (action state): context-registry.yaml, specs/plan.md, specs/tasks.md.*

| Artifact | Purpose |
|----------|---------|
| **AGENTS.md** | Entrypoint for agents: read order, commands, boundaries. |
| **NORTHSTAR.md** | Vision: goals, non-goals, success criteria. |
| **NORTHSTAR_METRICS.md** | Verifier-aware agent/eval metrics: gates, headline northstar, stopping rules. |
| **CONSTITUTION.md** | Principles, doc hierarchy. |
| **PRD.md** | Product scope, users, tradeoffs. |
| **specs/** | Spec-driven work; each change has a spec + registry entry. |
| **CURRENT_STATE.md** | (Brownfield) As-is: architecture, debt, fragile areas. |
| **MIGRATION_GUARDRAILS.md** | (Brownfield) Rules for safe change. |

Adapters (CLAUDE.md, Copilot, .cursor/rules) are thin; they point at these and `.agents/skills/`.

</details>

<details>
<summary><strong>Other ways to run (Copier, pipx, local)</strong></summary>

```bash
# Remote Copier
uvx copier copy gh:your-org/agentic-dev-greenfield my-new-repo
cd my-existing-repo && uvx copier copy gh:your-org/agentic-dev-brownfield-overlay .

# Updates (after applying once)
copier update --answers-file .copier-answers.agentic-greenfield.yml   # greenfield
copier update --answers-file .copier-answers.agentic-brownfield.yml   # brownfield

# Local clone
git clone https://github.com/pylit-ai/agentic-devkit.git && cd agentic-devkit && uv sync
uv run agentic-dev init my-new-repo
```

</details>

<details>
<summary><strong>Greenfield repo layout</strong></summary>

```
repo/
├── NORTHSTAR.md
├── NORTHSTAR_METRICS.md
├── CONSTITUTION.md
├── AGENTS.md
├── PRD.md
├── CLAUDE.md
├── opencode.json
├── docs/
│   ├── governance/
│   │   ├── DOCS_SYSTEM.md
│   │   └── context-registry.yaml
│   ├── architecture/
│   │   └── overview.md
│   ├── adr/
│   │   └── ADR-000-template.md
│   └── mcp/
│       └── servers.md
├── specs/
│   ├── registry.yaml
│   ├── 001-bootstrap/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   └── archive/
├── .github/
│   ├── copilot-instructions.md
│   └── instructions/
├── .cursor/
│   └── rules/
│       └── 00-router.mdc
├── .agents/
│   └── skills/
│       └── repo-os-greenfield-bootstrap/
├── .claude/
│   ├── agents/
│   │   └── repo-bootstrapper.md
│   └── commands/
│       └── bootstrap-repo.md
└── skills/
    └── README.md   # → .agents/skills
```

</details>

<details>
<summary><strong>Requirements & maintainers</strong></summary>

[uv](https://docs.astral.sh/uv/) + `uvx`, or `pip install agentic-devkit`. Publishing: sync templates to distribution repos, tag releases. [docs/maintainers/publish-workflow.md](docs/maintainers/publish-workflow.md).

</details>
