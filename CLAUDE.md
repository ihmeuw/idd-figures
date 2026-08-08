# idd-figures — repo rules

## Environment scheme: venv-only (declared 2026-08-08)

This repo runs the **pure-uv scheme**: a project `.venv` at the repo root,
uv-managed interpreter, uv-managed dependencies. One scheme per repo, never
mixed.

- **Expected:** `./.venv` exists and is the only environment for this repo.
  Its interpreter is a uv-managed standalone CPython (`uv python install`),
  never a conda python. All code runs via `.venv/bin/python` — by absolute
  path in Slurm jobs, no activation required.
- **Forbidden:** conda hosting of any kind for this repo — no conda env named
  after the repo, no `environment.yml`, no `UV_PROJECT_ENVIRONMENT=$CONDA_PREFIX`
  idiom. Those belong to the retired conda+uv scheme (see
  `.claude/UV_PILOT_RECORD.md` for its history and `.claude/VENV_PILOT_RECORD.md`
  for the migration).
- **Session start:** do NOT activate a conda env (this overrides the global
  "activate the matching conda environment" rule — there is no matching env).
  Use `.venv/bin/python` directly.
- **Sync idiom:** `uv sync --inexact` day-to-day; plain `uv sync` (exact) for
  clean rebuilds, vetted first with `uv sync --dry-run`. `--all-extras` to get
  the full dev surface.
- Interpreter downloads are deliberate only: the user-level uv policy is
  `python-downloads = "manual"` — a plain `uv venv`/`uv sync` must never
  trigger a CPython download.
