# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a subtitle transcription tool monorepo with a FastAPI backend and Next.js frontend:

- **Backend (`api/`)**: FastAPI server using Faster Whisper for audio transcription
  - Main entry point: `api/src/whisper_api.py`
  - Routers: transcription (`api/src/routers/transcribe.py`) and video conversion (`api/src/routers/convert.py`)
  - Workers: Background processing for transcription and conversion tasks
  - Utils: FFmpeg utilities and shared helper functions
  - Test suite: Comprehensive pytest-based testing in `api/tests/`

- **Frontend (`frontend/`)**: Next.js 15 React application with Tailwind CSS
  - Uses React 19 and TypeScript
  - UI components built with Radix UI primitives
  - API routes act as proxy to backend services
  - Pages: Main transcription interface and video converter

## Development Commands

### Package Management
This project uses **pnpm** with workspaces, not npm. Always use pnpm commands:

```bash
# Install all dependencies
pnpm install

# Install frontend dependencies only
pnpm --filter frontend install
```

### Development Servers
```bash
# Start both frontend and backend in development mode
pnpm run dev:all

# Start only frontend (on port 8002)
pnpm run dev:fe

# Start only backend API (on port 8010)
pnpm run dev:api
```

### Build Commands
```bash
# Build everything
pnpm run build:all

# Build only frontend
pnpm run build:fe

# Install API Python dependencies
pnpm run build:api
```

### Production Deployment
```bash
# Start both services in production mode
pnpm run start:all

# This also includes audio cleanup service
```

### Testing

#### Frontend Testing
```bash
# Lint frontend code
pnpm --filter frontend run lint
```

#### Backend Testing
```bash
# Run all Python tests
cd api && python run_tests.py

# Run specific test categories
cd api && python run_tests.py api        # API endpoint tests
cd api && python run_tests.py utils      # Utility function tests  
cd api && python run_tests.py models     # Model class tests

# Using pytest directly
cd api && pytest                         # All tests
cd api && pytest tests/test_utils.py -v  # Specific test file
cd api && pytest -m "unit" -v            # Unit tests only
cd api && pytest -m "api" -v             # API tests only
```

## Key Technical Details

### Backend Configuration
- Uses multiprocessing with "spawn" method for worker processes
- Automatic CUDA detection with fallback to CPU
- Background task management for transcription and conversion
- Audio cleanup service runs alongside production deployment
- Comprehensive error handling and task status management

### Frontend Architecture
- Next.js App Router with API routes as backend proxy
- Component structure follows shadcn/ui patterns
- Audio processing includes chunked upload for large files
- Real-time task monitoring with status polling
- Theme support via next-themes

### API Endpoints
Backend runs on port 8010, frontend proxy routes available at:
- `/api/transcribe/` - Audio transcription endpoints
- `/api/convert-video/` - Video to audio conversion endpoints  
- `/api/health/` - Health check

### Testing Strategy
- **Backend**: pytest with comprehensive fixtures and mocking
- **Test categories**: unit, api, integration, slow
- **Coverage**: utils, models, API endpoints, and error handling
- **Best practices**: parametrized tests, proper mocking, isolated tests

## File Structure Conventions
- Backend follows standard FastAPI project structure with routers/workers/utils separation
- Frontend uses Next.js 15 app directory structure
- UI components in `frontend/src/components/ui/` follow shadcn/ui conventions
- API proxy routes mirror backend endpoint structure

## Development Notes
- Always run tests before committing, especially for the backend
- The project includes Chinese language support and terminology
- Audio files are processed with chunked uploads for better performance
- Background workers handle heavy processing to avoid blocking the API
- Cleanup service manages temporary audio files in production