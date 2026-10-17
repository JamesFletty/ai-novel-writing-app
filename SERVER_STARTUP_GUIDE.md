# Server Startup Guide

Run these commands from a checked-out copy of the repository. There are no machine-specific absolute paths.

## Backend

```bash
cd backend
source venv/bin/activate          # Windows: venv\Scripts\activate
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Expected URLs:

- API: http://localhost:8000
- Health: http://localhost:8000/health
- Swagger: http://localhost:8000/docs

The default provider is GitHub Copilot SDK with `COPILOT_MODEL=auto`. Generation requires GitHub authentication on this host; basic API/database operations do not.

## Frontend

In another terminal:

```bash
cd frontend
npm start
```

The Vite development server defaults to http://localhost:3000 and calls the backend at http://localhost:8000. If you intentionally choose different ports, set `VITE_API_URL` for the frontend and include the frontend origin in backend `CORS_ORIGINS`.

## Verification

Before starting a writing session, the full local checks are:

```bash
cd backend
venv/bin/python -m pytest -q

cd ../frontend
npm test
npm run build
```

If the Copilot runtime is missing, activate the backend virtual environment and run:

```bash
python -m copilot download-runtime
```

See [README.md](README.md) for authentication, provider configuration, and security notes.
