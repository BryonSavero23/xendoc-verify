import json
import os
import re
import time
from typing import List, Optional
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader
import io
import cv2
import numpy as np

app = FastAPI(
    title="XenDoc-Verify: AI KYC & Lending Document Pipeline",
    description="Automated identity & financial document extraction + deterministic fraud/compliance validation for e-KYC and Digital Lending workflows.",
    version="1.0.0"
)

# Browser origins allowed to call this API (comma-separated), e.g. the Vercel site.
frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434/api/generate"

# --- 1. PYDANTIC SCHEMAS (Structured Outputs) ---
class DocumentInput(BaseModel):
    raw_text: str = Field(
        ..., 
        example="SAMPLE FINANCIAL DOCUMENT\nApplicant Name: [REDACTED]\nNRIC: [SYNTHETIC ID REDACTED]\nMonthly Gross Income: RM 0.00\nTotal Monthly Commitments: RM 0.00\nNet Disposable Income: RM 0.00\nEmployer: [REDACTED]\nAccount Status: SAMPLE"
    )

class ExtractedKYCData(BaseModel):
    applicant_name: Optional[str] = None
    id_number: Optional[str] = None
    employer_name: Optional[str] = None
    gross_monthly_income: float = 0.0
    monthly_commitments: float = 0.0
    net_income_stated: float = 0.0
    document_type: str = "Unknown"

    # The LLM returns null for fields missing from the document; treat as 0.
    @field_validator("gross_monthly_income", "monthly_commitments", "net_income_stated", mode="before")
    @classmethod
    def _null_amount_to_zero(cls, value):
        return 0.0 if value is None else value

    @field_validator("document_type", mode="before")
    @classmethod
    def _null_doc_type_to_unknown(cls, value):
        return "Unknown" if value is None else value

class VerificationResponse(BaseModel):
    status: str
    processing_time_ms: float
    extracted_data: ExtractedKYCData
    deterministic_checks: dict
    risk_flags: List[str]
    lending_recommendation: str

class ImageForensicsResponse(BaseModel):
    filename: str
    resolution: str
    metrics: dict
    forensic_flags: List[str]
    authenticity_verdict: str    


# --- 2. DETERMINISTIC VALIDATION LAYER (Zero-Hallucination Math & Regex) ---
def run_deterministic_checks(data: ExtractedKYCData) -> tuple[dict, List[str]]:
    risk_flags = []
    
    # Check 1: Malaysian NRIC format validation (YYMMDD-PB-####)
    nric_pattern = r"^\d{6}-\d{2}-\d{4}$"
    id_clean = (data.id_number or "").strip()
    is_valid_nric = bool(re.match(nric_pattern, id_clean))
    if not is_valid_nric:
        risk_flags.append(f"INVALID_ID_FORMAT: '{id_clean}' does not match standard Malaysian NRIC format.")

    # Check 2: Financial Math Reconciliation (Tamper Detection) (gross - commitments = net)
    calculated_net = round(data.gross_monthly_income - data.monthly_commitments, 2)
    math_discrepancy = abs(calculated_net - data.net_income_stated)
    is_math_consistent = math_discrepancy < 1.0  # Allow RM1 rounding tolerance
    if not is_math_consistent and data.net_income_stated > 0:
        risk_flags.append(
            f"TAMPER_RISK_MATH_MISMATCH: Stated Net (RM {data.net_income_stated}) != Gross - Commitments (RM {calculated_net})."
        )

    # Check 3: Debt Service Ratio (DSR) Calculation for Digital Lending
    dsr_percentage = 0.0
    if data.gross_monthly_income > 0:
        dsr_percentage = round((data.monthly_commitments / data.gross_monthly_income) * 100, 2)
        if dsr_percentage > 60.0:
            risk_flags.append(f"HIGH_DSR_RISK: Debt Service Ratio is {dsr_percentage}% (Exceeds 60% threshold).")
    else:
        risk_flags.append("ZERO_INCOME_DETECTED: Unable to compute Debt Service Ratio.")

    checks = {
        "nric_format_valid": is_valid_nric,
        "income_math_reconciled": is_math_consistent,
        "calculated_net_income_myr": calculated_net,
        "debt_service_ratio_pct": dsr_percentage
    }
    return checks, risk_flags


# --- 3. LOCAL LLM EXTRACTION ENGINE (Ollama) ---
def extract_with_llm(raw_text: str) -> ExtractedKYCData:
    prompt = f"""
    You are an AI Document Extraction Engine for a Malaysian Fintech & e-KYC platform.
    Extract the following fields from the unstructured document text below and return ONLY valid JSON matching this exact structure:
    {{
        "applicant_name": "string or null",
        "id_number": "Malaysian NRIC in YYMMDD-XX-XXXX format or null",
        "employer_name": "string or null",
        "gross_monthly_income": float,
        "monthly_commitments": float,
        "net_income_stated": float,
        "document_type": "Payslip | Bank Statement | Invoice | ID_Card"
    }}

    Document Text:
    \"\"\"{raw_text}\"\"\"
    """
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0}  # Zero temperature for deterministic extraction
            },
            timeout=120
        )
        response.raise_for_status()
        llm_json_str = response.json().get("response", "{}")
        parsed_dict = json.loads(llm_json_str)
        return ExtractedKYCData(**parsed_dict)
    except Exception as e:
        # Fallback regex/heuristic extraction if Ollama isn't running during demo
        raise HTTPException(
            status_code=500, 
            detail=f"LLM Inference Error (Check if Ollama is running with model '{OLLAMA_MODEL}'): {str(e)}"
        )


# --- 4. API ENDPOINTS ---
@app.post("/api/v1/verify-text", response_model=VerificationResponse, tags=["KYC & Lending Verification"])
def verify_document_text(payload: DocumentInput):
    """
    Accepts raw OCR text from a payslip/bank statement, extracts structured entities via local LLM,
    and runs deterministic compliance & fraud checks (NRIC regex, math reconciliation, DSR scoring).
    """
    start_time = time.time()
    
    # Step 1: AI Structured Extraction
    extracted = extract_with_llm(payload.raw_text)
    
    # Step 2: Deterministic Rule & Fraud Validation
    checks, risk_flags = run_deterministic_checks(extracted)
    
    # Step 3: Automated Lending Decision
    if len(risk_flags) == 0:
        recommendation = "AUTO_APPROVE_ELIGIBLE"
    elif any("TAMPER_RISK" in flag or "INVALID_ID" in flag for flag in risk_flags):
        recommendation = "REJECT_OR_MANUAL_FRAUD_REVIEW"
    else:
        recommendation = "MANUAL_CREDIT_UNDERWRITING"

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return VerificationResponse(
        status="SUCCESS",
        processing_time_ms=latency_ms,
        extracted_data=extracted,
        deterministic_checks=checks,
        risk_flags=risk_flags,
        lending_recommendation=recommendation
    )


@app.post("/api/v1/verify-pdf", response_model=VerificationResponse, tags=["KYC & Lending Verification"])
async def verify_pdf_upload(file: UploadFile = File(...)):
    """
    Uploads a PDF financial statement or payslip, extracts text layer, and runs the KYC/Lending verification pipeline.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    pdf_bytes = await file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    
    if not extracted_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from PDF. Document may require OCR preprocessing.")
        
    return verify_document_text(DocumentInput(raw_text=extracted_text))


@app.post("/api/v1/verify-mykad-forensics", response_model=ImageForensicsResponse, tags=["XenKYC Computer Vision Forensics"])
async def analyze_document_image(file: UploadFile = File(...)):
    """
    Training-free classical CV forensics for MyKad/Passport capture:
    1. Laplacian Variance (Blur / Defocus detection)
    2. HSV / LAB Gamut & Specular Glare Analysis (Laminate gloss vs Photocopy detection)
    3. 2D Fast Fourier Transform (FFT) High-Frequency Energy (Screen replay Moiré / Halftone detection)
    """
    img_bytes = await file.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    h, w, _ = img_bgr.shape
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    forensic_flags = []

    # 1. Optical Blur / Defocus Check (Variance of Laplacian)
    laplacian_var = float(round(cv2.Laplacian(gray, cv2.CV_64F).var(), 2))
    if laplacian_var < 80.0:
        forensic_flags.append(f"OPTICAL_BLUR_REJECT: Laplacian variance ({laplacian_var}) is below sharpness threshold (80.0).")

    # 2. Colour Gamut / Saturation Check (Photocopy / B&W Replay Detection)
    mean_saturation = float(round(np.mean(hsv[:, :, 1]), 2))
    if mean_saturation < 25.0:
        forensic_flags.append(f"LOW_GAMUT_PHOTOCOPY_RISK: Mean HSV saturation ({mean_saturation}) indicates desaturated/photocopied document.")

    # 3. Specular Laminate Glare Check (Over-exposed white pixels masking text/photo)
    glare_mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)[1]
    glare_ratio_pct = float(round((np.sum(glare_mask > 0) / (h * w)) * 100, 3))
    if glare_ratio_pct > 5.0:
        forensic_flags.append(f"EXCESSIVE_LAMINATE_GLARE: {glare_ratio_pct}% of image is clipped at max brightness (>250).")

    # 4. Frequency-Domain Analysis (2D FFT for Screen Replay Moiré / Periodic Spikes)
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-8)
    
    # Mask out the DC / low-frequency center to measure high-frequency periodic noise
    crow, ccol = h // 2, w // 2
    magnitude_spectrum[crow-15:crow+15, ccol-15:ccol+15] = 0
    high_freq_energy = float(round(np.percentile(magnitude_spectrum, 99.5), 2))
    if high_freq_energy > 240.0:
        forensic_flags.append(f"FREQUENCY_MOIRE_SPIKE: High 99.5th percentile FFT energy ({high_freq_energy}) suggests screen replay or halftone grid.")

    verdict = "PASS_GENUINE_CAPTURE" if len(forensic_flags) == 0 else "FLAGGED_FOR_SPOOF_OR_RECAPTURE"

    return ImageForensicsResponse(
        filename=file.filename,
        resolution=f"{w}x{h}",
        metrics={
            "laplacian_sharpness_var": laplacian_var,
            "hsv_mean_saturation": mean_saturation,
            "specular_glare_pct": glare_ratio_pct,
            "fft_high_freq_99p5_energy": high_freq_energy
        },
        forensic_flags=forensic_flags,
        authenticity_verdict=verdict
    )