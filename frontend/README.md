# XenDoc-Verify dashboard

## Run locally

From this directory, install dependencies and start the Vite development server:

```sh
npm install
npm run dev
```

In development, Vite proxies `/api` requests to `http://localhost:8000` by default, so the browser uses the same origin and does not require backend CORS middleware. To use another API base URL, create a `.env.local` file in `frontend/`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Run `npm run build` to type-check the Svelte app and create a production build in `dist/`. In production, `VITE_API_BASE_URL` is used directly by the browser; configure CORS on the API or provide a same-origin reverse proxy if the frontend and API are on different origins.

The Vite development proxy forwards requests without changing the Python backend.

Verification and image-forensics results are review information from the API. Heuristic checks and recommendations are not definitive proof of fraud, authenticity, or lending eligibility.
