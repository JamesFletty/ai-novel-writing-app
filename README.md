# AI Novel Writer

AI Novel Writer is a FastAPI + React application for taking a story from premise to outline, characters, world building, generated chapters, revision, and export. The default generation backend is the GitHub Copilot SDK, so a local user can use an existing GitHub Copilot subscription instead of maintaining a separate model API key.

GitHub Models is not used by this project. GitHub retired that product on July 30, 2026; the supported GitHub path here is the Copilot SDK.

## What works

- Story creation and progress tracking
- Structured outline generation with safe parsing
- Character and world-element generation
- Standard and enhanced chapter generation
- True streaming generation for standard chapters
- Previous-chapter prose continuity in generation prompts
- Multi-pass generation and chapter quality analysis
- Revision-preserving chapter expansion
- Full-draft background generation
- Markdown and plain-text export
- Adjustable prompt complexity (`simple`, `standard`, `complex`, `literary`)
- GitHub Copilot SDK by default, with optional direct OpenAI API and local Ollama providers

The Copilot provider runs in SDK `empty` mode with no tools, skills, MCP servers, configuration discovery, or filesystem/shell capabilities. The model is only being used as a text-generation engine for the novel prompts.

## Requirements

- Python 3.11 or newer (required by the current GitHub Copilot Python SDK)
- Node.js 18 or newer and npm
- A GitHub Copilot plan for the default provider

Copilot Student users should keep `COPILOT_MODEL=auto`. GitHub's SDK supports `model="auto"`, and Student model access is through automatic model selection.

## Quick start

```bash
git clone https://github.com/JamesFletty/ai-novel-writing-app.git
cd ai-novel-writing-app
python3 setup.py
```

The setup script creates `backend/venv`, installs dependencies, downloads the Python Copilot runtime, copies `backend/.env.example` to `backend/.env` if needed, installs the frontend, and runs the backend tests, frontend test, and production build.

### Authenticate Copilot

The app does not need a model-provider API key when using your Copilot subscription. GitHub's SDK can use a locally signed-in Copilot user, supported GitHub token environment variables, or GitHub CLI credentials. For a personal local install, sign in on the machine with the GitHub account that owns your Copilot plan before generating prose.

- [GitHub Copilot SDK authentication](https://docs.github.com/en/copilot/how-tos/copilot-sdk/auth/authenticate)
- [Python SDK bundled-runtime setup](https://docs.github.com/en/copilot/how-tos/copilot-sdk/setup/bundled-cli)

Do not paste or commit GitHub tokens into this repository.

### Start the application

Terminal 1:

```bash
cd backend
source venv/bin/activate          # Windows: venv\Scripts\activate
uvicorn app:app --reload
```

Terminal 2:

```bash
cd frontend
npm start
```

Open:

- Web app: http://localhost:3000
- API: http://localhost:8000
- Swagger API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Manual setup

Backend:

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m copilot download-runtime
cp .env.example .env
python -c "from db.database import init_db; init_db()"
python -m pytest -q
uvicorn app:app --reload
```

Frontend, in another terminal:

```bash
cd frontend
npm ci
npm test
npm run build
npm start
```

## Configuration

`backend/.env.example` contains the development defaults:

```env
AI_PROVIDER=copilot
COPILOT_MODEL=auto
DATABASE_URL=sqlite:///./ai_novel_app.db
CORS_ORIGINS=["http://localhost:3000"]
NOVEL_COMPLEXITY=standard
```

Provider choices:

| Provider | Required configuration | Notes |
| --- | --- | --- |
| `copilot` | Copilot authentication on the host | Default. `COPILOT_MODEL=auto` works with automatic model selection. |
| `openai` | `OPENAI_API_KEY` and `OPENAI_MODEL` | Optional direct API fallback; the model is intentionally explicit rather than hard-coded. |
| `ollama` | `OLLAMA_BASE_URL` and `OLLAMA_MODEL` | Optional local provider. |

`COPILOT_GITHUB_TOKEN` is supported for deliberate OAuth/deployment integrations, but it should be supplied by a secret manager or process environment, not committed to `.env`. For a multi-user deployment, follow GitHub's per-user OAuth guidance instead of sharing one personal credential.

## Generation pipeline

The application entry point is `app:app`. Enhanced chapter generation, multi-pass generation, regeneration, and quality analysis stay on `/api/v1/generate-enhanced`. Provider status and complexity settings are implemented once and mounted on both `/api/v1/generate` and `/api/v1/generate-enhanced`.

The normal workflow is:

1. Create a story.
2. Generate an outline.
3. Generate or edit characters and world elements.
4. Generate chapters in standard, enhanced, or multi-pass mode.
5. Analyze, edit, or expand chapters; prior prose is carried forward as continuity context.
6. Export the current manuscript as Markdown or text.

Important safety behavior: once a story contains chapter prose, regenerating its outline is rejected before an LLM call. This prevents an outline replacement from cascading into deletion of written chapters and avoids wasting AI credits.

Key API groups are available under `/api/v1/stories`, `/api/v1/generate`, `/api/v1/generate-enhanced`, `/api/v1/characters`, `/api/v1/world`, and `/api/v1/export`.

## Tests

Backend:

```bash
cd backend
venv/bin/python -m pytest -q
```

The API pipeline tests use a deterministic injected provider, so they validate the complete application workflow without consuming Copilot credits. A live Copilot call still requires valid GitHub authentication on the machine.

Frontend:

```bash
cd frontend
npm test
npm run build
```

## Security

- `backend/.env` is local-only and must remain ignored by Git.
- Never commit GitHub, OpenAI, or other provider tokens.
- `backend/ai_novel_app.db` is local runtime state and is gitignored. An earlier revision committed a development database. That copy had no accounts, emails, password hashes, phone numbers, or API keys. It did contain unpublished fiction drafts (premises, character notes, and chapter prose). Untracking the file leaves those blobs in history. Rewrite history only if those drafts should not stay recoverable.
- If a secret was ever committed in an earlier revision, removing the file from the current branch does not invalidate that secret. Rotate the credential and, if necessary, separately clean repository history.
- The embedded Copilot session exposes no tools to the model and rejects permission requests.

## Stack

- FastAPI, SQLAlchemy, SQLite, Pydantic
- GitHub Copilot SDK for Python
- React 19, TypeScript, Material UI, Vite
- React Router 6

The project is licensed under the terms in [LICENSE](LICENSE).
