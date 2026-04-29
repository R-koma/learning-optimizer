# Repository Guidelines

## Project Structure & Module Organization

This full-stack app is split into `client/` and `server/`. `client/` is a Next.js 16 App Router frontend: routes live in `client/app/`, UI in `client/components/`, hooks in `client/hooks/`, helpers in `client/lib/`, assets in `client/public/`, and Vitest tests in `client/__tests__/`. `server/` is FastAPI: routes are in `server/api/routes/`, WebSockets in `server/api/websocket/`, config/auth in `server/core/`, LangGraph flow logic in `server/graph/`, SQL repositories in `server/repositories/`, schemas in `server/schemas/`, migrations in `server/migrations/`, and tests in `server/tests/`. Docs and ADRs are in `docs/`.

## Build, Test, and Development Commands

- `make setup`: install dependencies, start the dev DB, apply migrations, and install hooks.
- `make dev-db`: start the PostgreSQL development database with Docker Compose.
- `make dev-server`: run FastAPI from `server/` via `uv run fastapi dev main.py`.
- `make dev-client`: run the Next.js dev server from `client/`.
- `cd client && npm run build`: build the frontend.
- `cd client && npm run lint`: run ESLint.
- `cd client && npm test`: run Vitest once.
- `cd server && uv run pytest`: run backend tests.
- `cd server && uv run ruff check . && uv run mypy .`: lint and type-check Python.

## Coding Style & Naming Conventions

Frontend code uses TypeScript, React function components, the `@/` import alias, shadcn/ui, and Prettier. Use established kebab-case filenames, for example `google-login-button.tsx`. Backend code targets Python 3.13 with Ruff formatting, double quotes, 119-character lines, and strict mypy. Keep route handlers, repositories, schemas, and services in their layers; avoid database access in API handlers.

## Testing Guidelines

Client tests use Vitest with jsdom and are named `*.test.ts` or `*.test.tsx` under `client/__tests__/`. Server tests use Pytest; place fast isolated tests in `server/tests/unit/` and database-backed tests in `server/tests/integration/`. Start `make test-db` before PostgreSQL integration tests. Add focused tests for new routes, repositories, graph nodes, and client API helpers.

## Commit & Pull Request Guidelines

Recent history follows Conventional Commits, such as `feat(evals): ...`, `fix: ...`, `refactor: ...`, and `chore: ...`. Keep commits scoped and imperative. PRs should include a summary, tests run, linked issue or context, screenshots for UI changes, and notes for migrations, environment variables, or API changes.

## Security & Configuration Tips

Do not commit secrets. Use `.env.example`, `server/.env.example`, and `client/.env.example` as templates. Pre-commit runs Gitleaks, Ruff, mypy, and Prettier; keep hooks passing before pushing.
