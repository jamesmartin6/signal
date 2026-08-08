# Signal frontend

React + TypeScript + Vite. See the [repo root README](../README.md) for the full picture (architecture, backend setup, eval results).

```bash
npm install
npm run dev      # http://localhost:5173, expects the backend on :8000
npm run build    # type-checks (tsc -b) then builds to dist/
npm run lint
```

Set `VITE_API_BASE_URL` (see `.env.example`) if the backend isn't on `http://localhost:8000`.
