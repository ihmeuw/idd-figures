# Poetry → uv migration — handoff

**Purpose.** Execute the migration of this repo's packaging from Poetry (`[tool.poetry]`
dialect) to **uv + PEP-621 `[project]`**, with optional-dependency **extras** so consumers
install only what they use. Read this file **plus `pyproject.toml`** and you have the full
picture; no prior session context is needed.

**Repo.** `idd-figures` — a shared, cross-repo figure library (painters + GridSpec layout
engine + primitives + maps). Env: conda env `idd-figures`, Python 3.12. Tests: `tests/lib/**`
(~105 passing / 2 skipped; run `PYTHONPATH=src python -m pytest`). Why migrate: today `shiny`
is a mandatory dependency and the heavy geo stack is conda-only / undeclared for pip, so a pip
consumer can't cleanly install "just the core."

---

## 1. Decisions already settled (one-line rationale each)

- **uv replaces Poetry** as resolver/installer/lock — faster, PEP-621-native, single lockfile.
- **PEP-621 `[project]` metadata + PEP-508 version ranges** (`>=x,<y`), dropping all
  `[tool.poetry]` tables and caret/tilde pins — standardize on the interoperable standard.
- **Extras layout** (`[project.optional-dependencies]`), derived from the grep usage map (heavy
  deps are confined to specific modules, so let consumers opt in):
  - core `dependencies = numpy, matplotlib, pandas`
  - `maps = cartopy, geopandas, shapely` · `ternary = mpltern` · `thumbnails = pillow`
  - `config = pyyaml` · `app = shiny (+ cartopy, geopandas)` · `all = maps+ternary+thumbnails+config`
  - **`rasterio` is NOT declared** — it has zero real imports in the codebase (planning artifact only).
- **`[dependency-groups]` (PEP-735) for dev deps** (pytest, pytest-cov, ruff, mypy, pre-commit)
  instead of `[tool.poetry.group.dev.dependencies]` — uv-native dev group, never shipped to consumers.
- **`[[tool.uv.index]]` for the IHME artifactory source** (replaces `[[tool.poetry.source]]`) — uv's
  index mechanism. NOTE: idd-figures itself has **no** internal-only deps (no jobmon), so it does
  **not** need this block; it is the pattern to carry into the scaffold/global standards (Phase 2).
- **Conda stays interpreter-only** — conda provides the Python interpreter + env namespace; **uv
  manages every Python dependency inside it**. The geo stack moves from conda-forge to PyPI wheels
  via the `maps` extra. Single dependency source of truth = uv. (This hinges on the open question below.)
- **Build alongside, then switch; committed `poetry.lock` is the rollback** — author the uv
  `pyproject` + `uv.lock` beside the existing Poetry setup, verify green, and only THEN remove the
  Poetry tables / `poetry.lock` / conda-geo reliance. Reversible until verified.

---

## 2. Open questions (NOT resolved — decide/verify during execution)

- **[BIGGEST RISK] Does the geo stack install as PyPI wheels under uv on the IHME cluster?
  — UNTESTED.** `cartopy`/`geopandas`/`shapely` (and the underlying GDAL/GEOS/PROJ / pyproj) come
  today from **conda-forge** (`environment.yml`), not pip. `uv sync --extra maps` requires working
  binary wheels for that stack on the cluster platform, **plus** cartopy's Natural Earth data
  download/cache. This was **not** tested this session. **Verify before committing to
  conda-interpreter-only.** If wheels fail on-cluster: fall back to keeping geo on conda for now, or
  pin known-good wheel versions. This gates the "conda interpreter-only" decision.
- **Build backend under uv** — keep `poetry-core` (works with any PEP-517 frontend) vs switch to
  `hatchling` / `uv_build`. Not decided.
- **`pandas` placement** — core (used by `example_data` + `idd_beeswarm`; consumers pass DataFrames)
  vs an `examples` extra. Currently listed core; confirm.
- **`shiny_app.py` fate** — keep behind the `app` extra, or quarantine to `attic/` like `plot_map.py`
  (it's a legacy demo that alone pulls shiny + the geo stack).
- **`requires-python`** — confirm canonical range (repo has `^3.12`; scaffold stub has `>=3.12,<4`).
- **Prune candidates** — `xarray` (`pyproject` line 15) and `jupyter` (line 16) are declared but no
  `import xarray`/jupyter appears in the package import scan; verify and drop from the migrated deps
  (jupyter, if wanted, belongs in the dev group).

---

## 3. Current repo state (established this session)

- **`__init__.py` behavior — clean seams, no lazy magic needed.** The top-level
  `src/idd_figures/__init__.py` and every subpackage `__init__.py` (`lib/`, `lib/painters/`,
  `lib/layouts/`) are comments/docstrings **only — zero imports**; `import idd_figures` triggers no
  third-party deps. No core module top-imports a heavy dep. The **only** top-level heavy imports are
  `lib/painters/maps.py` + `lib/layouts/maps.py` (cartopy, shapely) and `shiny_app.py` (shiny,
  geopandas, cartopy). `composition.py` imports `mpltern` and `io.py` imports `PIL` **lazily** inside
  functions. → extras isolate by submodule automatically; **no `__getattr__` required**.
- **Import patterns — submodule only.** All tests/vignettes use `from idd_figures.lib.<sub> import
  <x>`; there are **zero** `from idd_figures import X` top-level imports. → the split can require
  submodule imports; nothing needs top-level re-export.
- **Caret pins live in `pyproject.toml` lines 10–16:** `python="^3.12"`, `numpy="^1.26.0"`,
  `pandas="^2.1.0"`, `matplotlib="^3.8.0"`, `shiny="^0.6.0"`, `xarray="^2023.10.0"`,
  `jupyter="^1.0.0"`. These are the only caret pins in the whole rule/repo surface (the global
  standards + scaffold stub already use PEP-508 `>=,<`). → convert to PEP-508; prune unused.
- **Geo declaration lives in `environment.yml`** (conda: `geopandas`, `cartopy`, … + `- poetry` via
  pip), **not** in `pyproject.toml`. `shiny` is in `[tool.poetry.dependencies]` (mandatory core today)
  → move to the `app` extra.
- **`poetry.lock`** — committed at repo root (~341 KB) = the rollback anchor. **build-system** =
  `poetry-core` (`pyproject.toml` lines 31–33).
- **Tests** — `tests/lib/**`, ~105 pass / 2 skip (the 2 skips are `mpltern`-gated). Geo stack is
  present in the conda env, so the map tests actually RUN. CI (`.github/workflows/tests.yml`) uses
  `pip install poetry && poetry install` + `poetry run pytest` (a migration touch-point).
- **Legacy modules** — `idd_beeswarm.py` (standalone, queued for a framework rewrite) and
  `attic/plot_map.py` (quarantined prototype, not installed).

---

## 4. Plan shape — one session, three approval gates

- **Phase 1 — migrate THIS repo.** Author the PEP-621 `[project]` `pyproject.toml` (core deps +
  `[project.optional-dependencies]` extras + `[dependency-groups]` dev + `[[tool.uv.index]]` only if
  needed) **alongside** the existing Poetry file. `uv lock` → `uv.lock`; `uv sync --extra maps
  --extra ternary …`; run the full suite; **verify the geo stack installs/works under uv on-cluster**
  (§2 open risk). Only after green + geo verified: remove `[tool.poetry.*]`, delete `poetry.lock`,
  and drop the conda-geo reliance from `environment.yml`.
  → **Gate A** — approve migrated `pyproject.toml` + `uv.lock` + green tests + geo-wheel result
  **before** destroying the Poetry rollback.
- **Phase 2 — update the global standards from the proven Phase-1 patterns** (see §5 pointers).
  → **Gate B** — approve the global-standards / scaffold edits **before** touching `~/.claude`.
- **Close — write a `/move-to-uv` skill** that codifies the migration for the other idd-* repos.
  → **Gate C** — approve the skill.

---

## 5. Pointers — the rule sources Phase 2 must edit (from this session's audit)

Convert dialect (the `[tool.poetry.*]` tables, `[[tool.poetry.source]]`, group syntax, `poetry-core`
backend) — the version-range *syntax* in these sources is already PEP-508 (no caret to fix in the
global docs; caret only lives in this repo's `pyproject.toml`).

- **`~/.claude/commands/scaffold-repo.md`** (highest priority — it emits the pyproject):
  stub at lines **133–167** (`[tool.poetry]`, `[tool.poetry.dependencies]` `python=">=3.12,<4"`,
  `[tool.poetry.group.dev.dependencies]`, `[[tool.poetry.source]]` artifactory, `[build-system]`
  poetry-core); env steps **57–59** (`pip install poetry` / `poetry install` / `poetry run
  pre-commit install`); conda-activate helper reads `[tool.poetry] name` (~**319**).
- **`~/.claude/STANDARDS.md`**: §Environment **372–464** (conda+poetry pairing; `python -m poetry
  install`); §Required deps **402–426** *already* uses `[project]` but with Poetry's `(>=…)` paren
  notation — reconcile to clean PEP-508; §Pre-commit **492**; §CI/CD tests.yml **809–810**; §Git
  **910** (`poetry.lock` committed).
- **`~/.claude/CLAUDE.md`**: §Environment **382–384** (reads the project name from `pyproject.toml`
  to pick the conda env — name-read is dialect-sensitive).
- **`~/.claude/commands/migrate-jobmon.md:55`** references `[tool.poetry.scripts]` → `[project.scripts]`.
- **No standard currently teaches extras** — add `[project.optional-dependencies]` guidance in Phase 2.
- **This repo's incidental cleanup:** README Poetry badge (line 4); `environment.yml` `- poetry`
  (line 24); `.github/workflows/tests.yml` (`poetry install` / `poetry run pytest`, lines 10–11).
