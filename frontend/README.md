# Frontend

Vite + React + TypeScript client for AI Novel Writer.

```bash
npm ci
npm start
```

The dev server runs at http://localhost:3000. API requests use `VITE_API_URL` when set, otherwise `http://localhost:8000`.

```bash
npm test
npm run build
```

`npm run build` typechecks with `tsc` and writes the production bundle to `dist/`.
