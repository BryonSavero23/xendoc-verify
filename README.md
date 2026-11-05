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

Open the local URL printed by Vite (by default, `http://localhost:5173`). The frontend `.env.example` sets `VITE_API_BASE_URL=http://localhost:8000`; the Vite development proxy uses this value for `/api` requests.

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
- Replace or remove the identity/financial demo text in the source before publishing; scan the complete Git staging area, not only the paths covered by `.gitignore`.

## License

No license is currently included. Add a license before publishing if you want to grant others permission to use, modify, or distribute the project.
