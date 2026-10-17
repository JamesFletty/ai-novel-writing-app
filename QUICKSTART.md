# Quick Start

## 1. Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- GitHub Copilot access for the default LLM provider

## 2. Set up everything

From the repository root:

```bash
python3 setup.py
```

The setup installs both applications, downloads the Python Copilot runtime, creates a local `.env` from `.env.example`, and runs the test/build checks.

For local Copilot use, authenticate the machine with the GitHub account that owns your Copilot plan. The SDK supports stored Copilot CLI credentials and GitHub CLI credentials; see the [GitHub authentication guide](https://docs.github.com/en/copilot/how-tos/copilot-sdk/auth/authenticate). No separate LLM API key is required for this default path.

## 3. Run it

Backend:

```bash
cd backend
source venv/bin/activate          # Windows: venv\Scripts\activate
uvicorn app:app --reload
```

Frontend:

```bash
cd frontend
npm start
```

Then visit http://localhost:3000. API docs are at http://localhost:8000/docs.

## 4. Default configuration

```env
AI_PROVIDER=copilot
COPILOT_MODEL=auto
CORS_ORIGINS=["http://localhost:3000"]
```

Keep `COPILOT_MODEL=auto` for Copilot Student. Optional `openai` and `ollama` fallbacks are documented in [README.md](README.md).

## Troubleshooting

- `No module named ...`: activate `backend/venv` and reinstall `requirements.txt`.
- Copilot runtime missing: run `python -m copilot download-runtime` inside the backend virtual environment.
- Copilot authentication failure: sign in to GitHub/Copilot on the host and confirm that account has Copilot access.
- Port 8000 busy: start Uvicorn with `--port 8001` and set `VITE_API_URL` for the frontend accordingly.
- Port 3000 busy: Vite will try the next port; add that origin to `CORS_ORIGINS` before using it.

Never commit `backend/.env` or credentials.
