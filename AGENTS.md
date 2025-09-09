# Repository Guidelines

## Project Structure & Module Organization
- `api/`: FastAPI backend (Python). Code in `api/src/` with submodules `routers/`, `workers/`, `utils/`; tests in `api/tests/`; config in `api/pytest.ini`, deps in `api/requirements.txt`.
- `frontend/`: Next.js (App Router, TypeScript, Tailwind). Pages in `frontend/src/app/`, components in `frontend/src/components/`, shared utils in `frontend/src/lib/`.
- Root: `package.json` (pnpm workspaces), `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `README.md`. Temp output (e.g., converted audio) is written to the system temp dir.

## Build, Test, and Development Commands
- Install: `pnpm install` (root) + `pip install -r api/requirements.txt`.
- Dev (both): `pnpm run dev:all` (FE on `:8002`, API on `:8010`).
- Dev (single): `pnpm run dev:fe` or `pnpm run dev:api`.
- Build: `pnpm run build:all` (or `build:fe`, `build:api`).
- Start: `pnpm run start:all` (includes background `cleanup:audio`).
- API tests: `cd api && pytest` or `python run_tests.py` (e.g., `python run_tests.py --unit`).

## Coding Style & Naming Conventions
- Python: 4‑space indent, type hints where practical, `snake_case` for modules/functions, `PascalCase` for classes. Keep FastAPI routes in `api/src/routers/` and pure logic in `workers/`/`utils/`.
- TypeScript/React: `PascalCase` components (`*.tsx`), `camelCase` functions/variables, co-locate UI primitives under `frontend/src/components/ui/`. Run `pnpm --filter frontend run lint` before PRs.

## Testing Guidelines
- Backend: Pytest with markers (`unit`, `integration`, `api`, `utils`) configured in `api/pytest.ini`. File pattern: `api/tests/test_*.py`.
- Run subsets: `cd api && pytest -m unit`, `pytest tests/test_api_endpoints.py`, or `python run_tests.py api`.
- Frontend: No formal tests yet; at minimum, run `pnpm --filter frontend run lint` and verify pages under `/` and `/video-converter`.

## Commit & Pull Request Guidelines
- Commits: Imperative mood, small and scoped. Prefer a prefix like `[api]` or `[frontend]` (e.g., `[api] fix queue deadlock in monitor thread`).
- PRs must include: concise summary, linked issue, testing steps/commands, screenshots for UI changes, and note any env vars or migrations.
- CI hygiene: ensure `pnpm run build:all`, API tests, and frontend lint pass locally.

## Security & Configuration Tips
- Env vars: `MAX_CONCURRENT_TASKS`, `MAX_CONCURRENT_CONVERT_TASKS`. Default ports: FE `8002`, API `8010`.
- Dependencies: Python requires `ffmpeg` available on PATH; Torch/Whisper are heavy—avoid loading in tests unless needed.
- Do not commit secrets; `.env` is git‑ignored. Temporary files are auto‑cleaned by `cleanup:audio`.
