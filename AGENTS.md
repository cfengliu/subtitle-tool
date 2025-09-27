# Agent Handbook

Use this quick reference to keep coding agents aligned with the current repository state.

## Monorepo Overview
- FastAPI backend lives in `api/`; the ASGI entrypoint at `api/src/whisper_api.py` wires routers from `api/src/routers/` and exposes `/health`.
- Background cleanup in `api/src/cleanup_service.py` prunes `${tempdir}/converted_audios` and runs via `pnpm run cleanup:audio` (included in `start:all`).
- Conversion and transcription workers sit in `api/src/workers/` and share helpers from `api/src/utils/`.
- Backend tests reside in `api/tests/` with pytest markers configured in `api/pytest.ini`; `python run_tests.py` wraps common subsets.
- Next.js 15 frontend under `frontend/` uses the App Router (`frontend/src/app`) with shadcn/ui components in `frontend/src/components/ui/`.
- Frontend API routes in `frontend/src/app/api/` proxy requests through `frontend/src/lib/api-client.ts`, which reads `TRANSCRIPTION_API_URL` (defaults to `http://localhost:8010`).

## Backend (FastAPI)
- `uvicorn api.src.whisper_api:app` powers dev (`pnpm run dev:api`) and prod (`pnpm run start:api`); multiprocessing start method is forced to `spawn`.
- `/transcribe` (`api/src/routers/transcribe.py`): accepts audio uploads with optional `language`, caps concurrency via a `MAX_CONCURRENT_TASKS` semaphore (default `3`), tracks in-memory task state, and exposes `/tasks`, `/{task_id}/status`, `/{task_id}/result`, and `/{task_id}/cancel`. `/convert-traditional` converts TXT/SRT payloads to Traditional Chinese.
- `/convert` (`api/src/routers/convert.py`): supports direct uploads and 5 MB chunked uploads (`POST /convert/upload_chunk`), limits concurrency via `MAX_CONCURRENT_CONVERT_TASKS` (default `2`), tracks task metadata, and exposes `/tasks`, `/{task_id}/status`, `/{task_id}/result`, `/{task_id}/cancel`, `/{task_id}/download`, plus `/formats` for supported outputs.
- Chunk uploads assemble into `${tempdir}/chunk_uploads/<task_id>/` before dispatching a worker; completed audio is moved to `${tempdir}/converted_audios/<task_id>.<ext>` for download and later cleanup.
- Workers (`api/src/workers/`):
  - `transcribe_worker.py` boots Faster-Whisper (GPU when available), optionally restores zh punctuation (`zhpr` fallback to rule-based), and emits TXT/SRT with timestamp helpers.
  - `convert_worker.py` validates inputs, calls FFmpeg helpers in `api/src/utils/ffmpeg_utils.py`, reports progress through a shared dict, and writes outputs to temp files.
- Text helpers (`api/src/utils/text_conversion.py`) provide simplified/traditional conversion and punctuation utilities shared by routers and workers.
- External requirements: system `ffmpeg`, Torch/Faster-Whisper, optional `zhpr` weights; heavy deps load lazily inside workers to keep the API responsive.
- Testing: `cd api && python run_tests.py` for the suite, `python run_tests.py --unit` / `--api` / `--utils` for subsets, or invoke `pytest -m unit` etc; markers are defined in `api/pytest.ini`.

## Frontend (Next.js)
- Next.js App Router with React 19 runs on port 8002 via `pnpm run dev:fe`.
- `frontend/src/app/page.tsx` implements the transcription UI: drag-and-drop uploads, language selection, polling `/api/transcribe/{task_id}/status` every second, refreshing `/api/transcribe/tasks` every 5 seconds, and a button that hits `/api/transcribe/convert-traditional` for Traditional Chinese output.
- `frontend/src/components/AudioCutter.tsx` trims audio client-side using the Web Audio API and `@breezystack/lamejs` MP3 encoder before upload.
- `frontend/src/app/video-converter/page.tsx` with `frontend/src/components/VideoToAudio.tsx` enables video-to-audio conversion, 5 MB chunked uploads, format/quality selectors, status polling, and streaming downloads.
- API proxy routes mirror backend endpoints:
  - `/app/api/transcribe` (plus `[taskId]` routes) forward to `/transcribe`.
  - `/app/api/transcribe/convert-traditional` relays JSON payloads for script conversion.
  - `/app/api/convert-video/chunk-upload` forwards multipart chunks to `/convert/upload_chunk`.
  - `/app/api/convert-video/[taskId]/download` streams backend downloads without buffering entire files.
- UI primitives live in `frontend/src/components/ui/`; shared client utilities (e.g., `ApiClient`) live in `frontend/src/lib/`.

## Tooling & Commands
- Install deps with `pnpm install` (root) and `pip install -r api/requirements.txt` for the API.
- Dev workflows: `pnpm run dev:all` runs both servers; `pnpm run dev:api` / `pnpm run dev:fe` start them individually.
- Builds: `pnpm run build:all` (frontend build + `pip install`), or granular `pnpm run build:fe` / `pnpm run build:api`.
- Production: `pnpm run start:all` launches frontend, backend, and the audio cleanup scheduler.
- Frontend linting: `pnpm --filter frontend run lint`.

## Contribution Notes
- Python: 4-space indent, type hints where practical, keep routes thin and move heavy logic into `workers/` or `utils/`.
- TypeScript: PascalCase components (`*.tsx`), camelCase functions, co-locate primitives under `frontend/src/components/ui/`.
- Temporary artifacts land in system temp directories (audio chunks/conversions) and are cleaned automatically—keep them out of git.
- Commit messages stay imperative with scope prefixes like `[api]` / `[frontend]`; before PRs ensure `pnpm run build:all`, backend tests, and frontend lint pass.
