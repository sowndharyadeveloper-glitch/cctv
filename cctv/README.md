# PRESENT SIR frontend

The Vite frontend is deployed independently from the Python attendance backend.
Set `VITE_API_URL` to the backend's HTTPS origin in Vercel. Do not set it to
localhost or commit `.env.local`. The backend must be deployed as a persistent
Flask service with the dependencies in `AI_CCTV_Attendance/requirements.txt`.

Required backend environment variables:

```text
SECRET_KEY=<long-random-value>
DATABASE_PATH=<persistent database path>
CORS_ORIGINS=https://<your-vercel-domain>
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=None
```

Local production-like check:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r AI_CCTV_Attendance\requirements.txt
$env:CORS_ORIGINS='http://localhost:5173'
$env:SESSION_COOKIE_SECURE='false'
Push-Location AI_CCTV_Attendance
..\.venv\Scripts\python.exe app.py
Pop-Location
Push-Location cctv
$env:VITE_API_URL=''
npm install
npm run build
npm run lint
Pop-Location
```

The Vercel project root is `cctv`. Configure `VITE_API_URL` in Vercel for
Preview and Production separately, then redeploy. Vercel hosts the SPA only;
OpenCV camera access, SQLite persistence, face recognition, and SSE remain on
the Flask service.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
