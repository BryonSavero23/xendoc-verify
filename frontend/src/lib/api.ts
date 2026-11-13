export interface ExtractedKYCData {
  applicant_name: string | null;
  id_number: string | null;
  employer_name: string | null;
  gross_monthly_income: number;
  monthly_commitments: number;
  net_income_stated: number;
  document_type: string;
}

export interface VerificationResponse {
  status: string;
  processing_time_ms: number;
  extracted_data: ExtractedKYCData;
  deterministic_checks: Record<string, boolean | number | string | null>;
  risk_flags: string[];
  lending_recommendation: string;
  demo_mode?: boolean;
}

export interface ImageForensicsResponse {
  filename: string;
  resolution: string;
  metrics: Record<string, boolean | number | string | null>;
  forensic_flags: string[];
  authenticity_verdict: string;
  demo_mode?: boolean;
}

const configuredApiBaseUrl = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : '')
)
  .trim()
  .replace(/\/+$/, '');
const apiRequestBaseUrl = import.meta.env.DEV ? '' : configuredApiBaseUrl;
// A production build with no API URL has no backend to call: same-origin
// requests would hit the static host and fail, so use demo mode instead.
const forceDemoMode =
  import.meta.env.VITE_DEMO_MODE?.trim().toLowerCase() === 'true' ||
  (!import.meta.env.DEV && !configuredApiBaseUrl);

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function createDemoVerificationResponse(): VerificationResponse {
  return {
    status: 'SUCCESS',
    processing_time_ms: 420,
    extracted_data: {
      applicant_name: 'Sample Applicant (Demo)',
      id_number: '900101-14-1234',
      employer_name: 'Contoso Manufacturing (Demo)',
      gross_monthly_income: 8000,
      monthly_commitments: 2500,
      net_income_stated: 5500,
      document_type: 'Payslip'
    },
    deterministic_checks: {
      nric_format_valid: true,
      income_math_reconciled: true,
      calculated_net_income_myr: 5500,
      debt_service_ratio_pct: 31.25
    },
    risk_flags: [],
    lending_recommendation: 'AUTO_APPROVE_ELIGIBLE',
    demo_mode: true
  };
}

function createDemoImageResponse(file: File): ImageForensicsResponse {
  return {
    filename: file.name,
    resolution: '1280x800',
    metrics: {
      laplacian_sharpness_var: 67.4,
      hsv_mean_saturation: 39.2,
      specular_glare_pct: 0.8,
      fft_high_freq_99p5_energy: 214.6
    },
    forensic_flags: ['OPTICAL_BLUR_REJECT: The sample sharpness score is below the illustrative threshold.'],
    authenticity_verdict: 'FLAGGED_FOR_SPOOF_OR_RECAPTURE',
    demo_mode: true
  };
}

async function withDemoFallback<T extends object>(
  request: () => Promise<T>,
  demoResponse: T
): Promise<T> {
  if (forceDemoMode) return demoResponse;

  try {
    return await request();
  } catch (error) {
    if (error instanceof TypeError) return demoResponse;
    throw error;
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiRequestBaseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return readResponse<T>(response);
}

async function postFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${apiRequestBaseUrl}${path}`, {
    method: 'POST',
    body: formData
  });
  return readResponse<T>(response);
}

async function readResponse<T>(response: Response): Promise<T> {
  const responseText = await response.text();
  let payload: unknown;

  try {
    payload = responseText ? JSON.parse(responseText) : null;
  } catch {
    throw new ApiError(
      response.ok
        ? 'The API returned a response that was not valid JSON.'
        : `The API returned HTTP ${response.status} with an unreadable error response.`
    );
  }

  if (!response.ok) {
    const detail =
      typeof payload === 'object' &&
      payload !== null &&
      'detail' in payload &&
      typeof payload.detail === 'string'
        ? payload.detail
        : `The API request failed with HTTP ${response.status}.`;
    throw new ApiError(detail);
  }

  return payload as T;
}

export function verifyText(rawText: string): Promise<VerificationResponse> {
  return withDemoFallback(
    () =>
      postJson<VerificationResponse>('/api/v1/verify-text', {
        raw_text: rawText
      }),
    createDemoVerificationResponse()
  );
}

export function verifyPdf(file: File): Promise<VerificationResponse> {
  return withDemoFallback(
    () => postFile<VerificationResponse>('/api/v1/verify-pdf', file),
    createDemoVerificationResponse()
  );
}

export function verifyImage(file: File): Promise<ImageForensicsResponse> {
  return withDemoFallback(
    () => postFile<ImageForensicsResponse>('/api/v1/verify-mykad-forensics', file),
    createDemoImageResponse(file)
  );
}
