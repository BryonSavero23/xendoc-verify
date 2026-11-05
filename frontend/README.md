# XenDoc-Verify dashboard

## Run locally

From this directory, install dependencies and start the Vite development server:

```sh
npm install
npm run dev
```

In development, Vite proxies `/api` requests to `http://localhost:8000` by default, so the browser uses the same origin and does not require backend CORS middleware. To use another API base URL, create a `.env.local` file in `frontend/`:

```env
VITE_API_URL=http://localhost:8000
```

Set `VITE_DEMO_MODE=true` to skip API calls and use visibly labeled synthetic results. With demo mode off, a failed network connection also produces synthetic results; API error responses remain visible.

Run `npm run build` to type-check the Svelte app and create a production build in `dist/`. In production, `VITE_API_URL` is used directly by the browser; configure CORS on the API if the frontend and API are on different origins. `VITE_API_BASE_URL` is supported as a backwards-compatible alias.

The Vite development proxy forwards requests without changing the Python backend.

Verification and image-forensics results are review information only. Synthetic demo results do not analyze the submitted document or image; real API heuristics and recommendations are not definitive proof of fraud, authenticity, or lending eligibility.
