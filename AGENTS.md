# AGENTS.md

Repo-level working preferences for `~/Codex`.

## Response Protocol

- If a request may take more than ~5 seconds, send a quick acknowledgment first (e.g., "got it"), then follow with results.
- If results are immediate, respond directly with results.
- When working anywhere under `~/Codex`, read and follow the nearest applicable `AGENTS.md` at the start of the task unless the user explicitly says otherwise.
- For website changes meant to be viewed externally, always push to GitHub immediately after each change.

## Defaults

- Prefer Python for scripts and automation tasks.
- Prefer `uv` for Python environment/package management.
- Prefer `uv run ...` over invoking Python directly when project dependencies are involved.
- Prefer `uv pip ...` over `pip ...` when managing packages in a `uv` workflow.
- Prefer `rg` / `rg --files` for searching text/files.

## Repo Workflow

- Run commands from repo root: `~/Codex` unless a project requires otherwise.
- Make small, clear commits; use `WIP:` commits if stopping mid-task.
- Default to committing each completed change and pushing it to GitHub unless the user asks not to.
- Keep `main` pushable; use branches for larger changes (branch prefix: `codex/`).
- After modifying a project, update relevant `README.md` files and other necessary docs/config, then push to GitHub.
- For each modification cycle in Codex, increment the version number, push updates, and report: local URL, GitHub Pages URL, and the new version to expect on refresh.
- By Elie (and Codex projects) versioning scheme: use `vX.Y` where `X` is the number of days since `2026-02-28` and `Y` increments for each new iteration that day-index (example: `2026-03-10` => `X=10` => `v10.0`, `v10.1`, `v10.2`).
- Before pausing, update `~/Codex/NEXT_STEPS.md` with current status and next command.

## Skills

- `frontend-design` skill: `skills/frontend-design/SKILL.md`
  - Use for premium front-end refinement (hierarchy, spacing, typography, non-breaking visual iterations).
- `video-to-website` skill: `skills/video-to-website/SKILL.md`
  - Use to turn a video into a premium scroll-driven website with GSAP/Lenis/canvas choreography.
- `video-to-webpage` skill: `skills/video-to-webpage/SKILL.md`
  - Use to turn a video into a premium scroll-driven single web page experience.

## Website Workspace Structure

- Canonical website workspace root: `~/Codex/web/github.io`
- Olea Media Co project: `~/Codex/web/github.io/oleamediaco`
- Olea Tax Co project: `~/Codex/web/github.io/oleataxco`
- GitHub Pages workflow: `~/Codex/.github/workflows/deploy-oleamediaco-site.yml`

## Project Boundaries (Separate Threads)

- If a thread is for Olea Media Co, only modify files under `web/github.io/oleamediaco` unless explicitly asked otherwise.
- If a thread is for Olea Tax Co, only modify files under `web/github.io/oleataxco` unless explicitly asked otherwise.
- Avoid cross-project refactors or shared style/script changes across both projects unless explicitly requested.
- Keep commit messages project-scoped (for example: `oleamediaco: ...` or `oleataxco: ...`).

## Local Preview Commands

- Top-level site index: `cd ~/Codex/web/github.io && python3 -m http.server 8000`
- Olea Media Co: `http://localhost:8000/oleamediaco/`
- Olea Tax Co: `http://localhost:8000/oleataxco/`

## Execution Discipline

- Prefer deterministic tooling over manual repetition. Before creating new scripts, check whether an existing script or workflow already covers the task.
- If a project includes `workflows/` and `tools/`, follow that flow: read the workflow first, then execute with the corresponding tool scripts.
- Treat failures as a fix loop: read the full error, patch the tool/process, retest, and record the constraint in project docs so the issue does not repeat.
- Keep secrets out of source files. Use `.env` and credential files (gitignored), and never commit API keys or tokens.
- Use `.tmp/` for regenerable intermediates whenever practical; keep final deliverables in their project-owned locations.
## Python Hygiene

- Do not commit virtual environments (`.venv/`).
- Do not commit Python cache artifacts (`__pycache__/`, `*.pyc`).
- Prefer adding project config (`pyproject.toml`, `uv.lock`) when a Python project grows beyond a single script.

## Safety

- Do not delete or overwrite user files without explicit confirmation.
- Do not rewrite Git history (`push --force`, `reset --hard`) unless explicitly requested.
