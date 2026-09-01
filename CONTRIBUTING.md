# Contributing

Thanks for contributing to CleanSport Intelligence. This is a prototype anti-doping
intelligence decision-support system. Please keep the following in mind.

## Ground rules

- **Investigative product boundary (non-negotiable).** Outputs are signals and leads
  for human review. Never add "guilt probability", "doping score", or automatic
  "violation confirmed" constructs — in code, UI, prompts, reports or docs.
- **Synthetic data only.** No real personal, medical, financial or confidential
  source data. Never commit real credentials or secrets.
- **Documentation stays synchronized.** If you change architecture, schema, APIs,
  algorithms or setup, update the corresponding docs in the same change.

## Development setup

1. Clone the repository.
2. Copy `.env.example` to `.env` and adjust.
3. Backend: create a virtualenv from `backend/`, install from `backend/requirements.txt`.
4. Apply migrations: `alembic upgrade head`.
5. Run the API: `uvicorn app.main:app --reload`.
6. Docker path: `docker compose up --build postgres backend`.

## Branch naming

- `feature/<feature-name>` — new functionality
- `fix/<bug-name>` — bug fixes
- `refactor/<area>` — refactoring
- `docs/<topic>` — documentation

`main` is the stable branch. Work in short-lived branches and open a pull request.

## Commit conventions

- Meaningful, focused commits. One logical change per commit.
- Conventional prefixes: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Examples:
  - `feat: add intelligence ingestion endpoint`
  - `fix: correct alert priority calculation`
  - `test: add anomaly scoring tests`
  - `docs: update system architecture`
- Avoid commits like `update`, `changes`, `final`, `stuff`.

## Testing expectations

- Backend: `pytest` from `backend/`. New backend code should include tests.
- Keep the intelligence engine deterministically testable (fixed seeds).
- Frontend/CI checks will be added when the frontend is scaffolded.

## Pull request expectations

- Describe what changed and why; reference the requirement or decision (e.g. §N,
  D-00N) where relevant.
- Update affected documentation in the same PR.
- Ensure tests pass and no secrets are introduced.
- Do not include generated output (`__pycache__`, `.venv`, `node_modules`, `dist`,
  coverage) or `.env` files.

## Code quality

- Python: type hints, clean docstrings, format consistent with existing code.
- Follow the existing architecture (modules under `backend/app/{api,core,db,models,security,services}`);
  do not introduce a second pattern without a documented reason.
- Run the linters/type checks in CI where configured.