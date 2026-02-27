# AGENTS.md

Repo-level working preferences for `/Users/ecohen/Codex`.

## Defaults

- Prefer Python for scripts and automation tasks.
- Prefer `uv` for Python environment/package management.
- Prefer `uv run ...` over invoking Python directly when project dependencies are involved.
- Prefer `uv pip ...` over `pip ...` when managing packages in a `uv` workflow.
- Prefer `rg` / `rg --files` for searching text/files.

## Repo Workflow

- Run commands from repo root: `/Users/ecohen/Codex` unless a project requires otherwise.
- Make small, clear commits; use `WIP:` commits if stopping mid-task.
- Keep `main` pushable; use branches for larger changes (branch prefix: `codex/`).
- After modifying a project, update relevant `README.md` files and other necessary docs/config, then push to GitHub.
- Before pausing, update `/Users/ecohen/Codex/NEXT_STEPS.md` with current status and next command.

## Website Workspace Structure

- Canonical website workspace root: `/Users/ecohen/Codex/web/github.io`
- Olea Media Co project: `/Users/ecohen/Codex/web/github.io/oleamediaco`
- Olea Tax Co project: `/Users/ecohen/Codex/web/github.io/oleataxco`
- GitHub Pages workflow: `/Users/ecohen/Codex/.github/workflows/deploy-oleamediaco-site.yml`

## Project Boundaries (Separate Threads)

- If a thread is for Olea Media Co, only modify files under `web/github.io/oleamediaco` unless explicitly asked otherwise.
- If a thread is for Olea Tax Co, only modify files under `web/github.io/oleataxco` unless explicitly asked otherwise.
- Avoid cross-project refactors or shared style/script changes across both projects unless explicitly requested.
- Keep commit messages project-scoped (for example: `oleamediaco: ...` or `oleataxco: ...`).

## Local Preview Commands

- Olea Media Co: `cd /Users/ecohen/Codex/web/github.io/oleamediaco && python3 -m http.server 8000`
- Olea Tax Co: `cd /Users/ecohen/Codex/web/github.io/oleataxco && python3 -m http.server 8001`

## Python Hygiene

- Do not commit virtual environments (`.venv/`).
- Do not commit Python cache artifacts (`__pycache__/`, `*.pyc`).
- Prefer adding project config (`pyproject.toml`, `uv.lock`) when a Python project grows beyond a single script.

## Safety

- Do not delete or overwrite user files without explicit confirmation.
- Do not rewrite Git history (`push --force`, `reset --hard`) unless explicitly requested.
