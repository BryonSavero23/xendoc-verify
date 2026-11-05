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
}

export interface ImageForensicsResponse {
  filename: string;
  resolution: string;
  metrics: Record<string, boolean | number | string | null>;
  forensic_flags: string[];
  authenticity_verdict: string;
}

const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
  .trim()
  .replace(/\/+$/, '');
const apiRequestBaseUrl = import.meta.env.DEV ? '' : configuredApiBaseUrl;

function networkError(): ApiError {
  if (import.meta.env.DEV) {
    return new ApiError(
      `Could not reach the API at ${configuredApiBaseUrl} through the Vite development proxy. Check that the backend is running and that VITE_API_BASE_URL is correct.`
    );
  }

  return new ApiError(
    `Could not reach the API at ${configuredApiBaseUrl}. Check that the backend is running. If the browser reports a CORS error, configure CORS middleware or a reverse proxy for the frontend origin.`
  );
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiRequestBaseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw networkError();
    }
    throw error;
  }

  return readResponse<T>(response);
}

async function postFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(`${apiRequestBaseUrl}${path}`, {
      method: 'POST',
      body: formData
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw networkError();
    }
    throw error;
  }

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
  return postJson<VerificationResponse>('/api/v1/verify-text', {
    raw_text: rawText
  });
}

export function verifyPdf(file: File): Promise<VerificationResponse> {
  return postFile<VerificationResponse>('/api/v1/verify-pdf', file);
}

export function verifyImage(file: File): Promise<ImageForensicsResponse> {
  return postFile<ImageForensicsResponse>('/api/v1/verify-mykad-forensics', file);
}
