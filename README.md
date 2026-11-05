# XenDoc-Verify

**Privacy-first AI e-KYC and document intelligence platform**

XenDoc-Verify is a local-first demonstration of financial-document review that combines a local language model for structured text extraction with deterministic rules and classical computer-vision heuristics. It exposes a FastAPI backend and a TypeScript web dashboard for text, PDF, and identity-image workflows.

> **Important:** This project is a prototype, not a production e-KYC, fraud-detection, or credit-decision system. Its format checks and image metrics are heuristics, not proof of identity, authenticity, or eligibility. Do not use it to make consequential decisions without appropriate validation, human review, security controls, and regulatory assessment. Use synthetic data for demos.

## Core workspaces

### 1. Text verification

- Sends supplied document text to a locally running Ollama model (`llama3.2`) for structured extraction.
- Applies deterministic checks after extraction: a Malaysian NRIC **format** regex (`YYMMDD-PB-####`), gross-income/commitment/net-income reconciliation, and Debt Service Ratio (DSR) calculation.
- Returns extracted fields, check results, risk flags, and a review recommendation.
- The NRIC check verifies the string shape only; it does not establish that an identity number is genuine or belongs to the applicant.

### 2. PDF verification

- Uses PyPDF to extract selectable text from uploaded PDF pages and submits that text to the same verification pipeline.
- Image-only/scanned PDFs are not OCR-processed and are rejected when no text can be extracted.
- **Current limitation:** the endpoint does not inspect PDF metadata for tampering. It also does not verify document signatures or prove that a document is authentic.

### 3. Image forensics (MyKad and passport captures)

- Uses OpenCV and NumPy for training-free image heuristics.
- Reports the following metrics:
  - `laplacian_sharpness_var` — variance of the Laplacian as a blur/sharpness signal.
  - `hsv_mean_saturation` — mean HSV saturation as a color-gamut signal.
  - `specular_glare_pct` — proportion of pixels above the grayscale brightness threshold.
  - `fft_high_freq_99p5_energy` — 99.5th-percentile 2D FFT magnitude after masking the low-frequency center, as a possible screen-replay/moiré signal.
- Threshold-based flags can be affected by capture conditions, device, and document type. They should be treated as triage signals only.

## Architecture and technology

- **Backend:** Python, FastAPI, Pydantic, Requests, PyPDF, OpenCV, and NumPy.
- **Extraction:** Ollama running locally with the `llama3.2` model.
- **Frontend:** Svelte 5, TypeScript, Vite, and custom CSS.
- In development, Vite proxies `/api` requests to `http://localhost:8000`. The backend calls Ollama at `http://localhost:11434/api/generate`.

The current frontend is Svelte with custom CSS; it does not use React or Tailwind CSS.

## Deploy the frontend to Vercel

The root `vercel.json` builds the Vite app in `frontend/` and publishes `frontend/dist`. Keep the Vercel project's Root Directory set to the repository root. The FastAPI backend is not part of this static deployment: it depends on a local Ollama service and Python computer-vision libraries, which are not included in this Vercel configuration.

Add these build-time environment variables in the Vercel project settings:

| Variable | Value | Purpose |
|---|---|---|
| `VITE_DEMO_MODE` | `true` | Run the UI with clearly labeled synthetic sample results without calling an API. Recommended for a portfolio demo. |
| `VITE_API_URL` | Your publicly reachable API origin, e.g. `https://api.example.com` | Optional when using a separately hosted backend. Leave unset for frontend-only demo mode. |

Redeploy after changing environment variables. Vite embeds `VITE_` variables into the browser bundle, so do not put secrets in them. When demo mode is off, the frontend automatically uses synthetic results if the API request cannot connect; HTTP/API errors are still shown normally. A separately hosted API must allow browser requests from the Vercel site's origin (CORS). `VITE_API_BASE_URL` remains supported as an alias for local setups; `VITE_API_URL` takes precedence.

For local development, copy `frontend/.env.example` to `frontend/.env.local`; the Vite development proxy forwards `/api` to the configured API URL.

## Local setup

### Prerequisites

- Python 3.10 or newer
- Node.js and npm
- [Ollama](https://ollama.com/) installed and available on your local machine

### 1. Create a Python environment and install backend dependencies

From the repository root, in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" requests pydantic pypdf opencv-python numpy python-multipart
```

### 2. Start Ollama and pull the model

In a terminal with Ollama installed:

```powershell
ollama pull llama3.2
ollama serve
```

If Ollama is already running as a background service, the `ollama serve` command is not needed. The backend currently uses the model name and Ollama URL defined in `main.py`.

### 3. Start the FastAPI backend

From the repository root, in a separate terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

### 4. Start the frontend

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open the local URL printed by Vite (by default, `http://localhost:5173`). The frontend `.env.example` sets `VITE_API_URL=http://localhost:8000`; the Vite development proxy uses this value for `/api` requests. Set `VITE_DEMO_MODE=true` to exercise the UI with synthetic responses and no API calls.

To check and build the frontend:

```powershell
npm run build
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/verify-text` | Extract and run deterministic checks on supplied document text |
| `POST` | `/api/v1/verify-pdf` | Extract PDF text and run the text-verification pipeline |
| `POST` | `/api/v1/verify-mykad-forensics` | Calculate image-forensics metrics and heuristic flags |

## Privacy and safe demos

- Keep identity documents, financial statements, uploads, environment files, and local development artifacts out of public commits. The root `.gitignore` excludes common local documents and build artifacts; review `git status` before committing.
- Do not paste real personal or financial information into public issues, screenshots, sample data, or prompts to hosted services.
- Ollama is configured for a local endpoint by default, but this prototype has no authentication or production-grade data-handling controls. Do not expose it or the API publicly with real documents.
- The included demo responses use synthetic values only. Keep real identity and financial documents out of the source, public issues, screenshots, and prompts; scan the complete Git staging area before publishing.

## License

No license is currently included. Add a license before publishing if you want to grant others permission to use, modify, or distribute the project.
