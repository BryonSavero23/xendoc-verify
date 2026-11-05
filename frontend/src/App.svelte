<script lang="ts">
  import {
    ApiError,
    verifyImage,
    verifyPdf,
    verifyText,
    type ImageForensicsResponse,
    type VerificationResponse
  } from './lib/api';

  type Tab = 'text' | 'pdf' | 'image';

  const navigation: { id: Tab; title: string; subtitle: string; icon: string }[] = [
    { id: 'text', title: 'Text verification', subtitle: 'Paste document text', icon: 'T' },
    { id: 'pdf', title: 'PDF verification', subtitle: 'Payslips & statements', icon: 'P' },
    { id: 'image', title: 'Image forensics', subtitle: 'MyKad & passport', icon: 'I' }
  ];

  const sampleText = `SAMPLE FINANCIAL DOCUMENT
Applicant Name: [REDACTED]
NRIC: [SYNTHETIC ID REDACTED]
Monthly Gross Income: RM 0.00
Total Monthly Commitments: RM 0.00
Net Disposable Income: RM 0.00
Employer: [REDACTED]
Account Status: SAMPLE`;

  const imageExtensions = /\.(png|jpe?g|webp|bmp|tiff?)$/i;

  let activeTab: Tab = 'text';
  let rawText = '';
  let selectedFile: File | null = null;
  let fileInput: HTMLInputElement;
  let fileError = '';
  let requestError = '';
  let isLoading = false;
  let verificationResult: VerificationResponse | null = null;
  let verificationSource: 'text' | 'pdf' | null = null;
  let imageResult: ImageForensicsResponse | null = null;

  $: activeItem = navigation.find((item) => item.id === activeTab) ?? navigation[0];
  $: showVerificationResult =
    verificationResult !== null && verificationSource === activeTab;

  function chooseTab(tab: Tab) {
    activeTab = tab;
    selectedFile = null;
    fileError = '';
    requestError = '';
  }

  function handleFileChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    selectFile(input.files?.[0] ?? null, input);
  }

  function handleFileDrop(event: DragEvent) {
    event.preventDefault();
    if (isLoading) return;
    fileInput.value = '';
    selectFile(event.dataTransfer?.files[0] ?? null, fileInput);
  }

  function selectFile(file: File | null, input: HTMLInputElement) {
    selectedFile = null;
    fileError = '';
    requestError = '';

    if (!file) return;

    if (activeTab === 'pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      fileError = 'Choose a PDF file to continue.';
      input.value = '';
      return;
    }

    if (
      activeTab === 'image' &&
      (!imageExtensions.test(file.name) ||
        (file.type !== '' && !file.type.startsWith('image/')))
    ) {
      fileError = 'Choose a PNG, JPEG, WebP, BMP, or TIFF image.';
      input.value = '';
      return;
    }

    selectedFile = file;
  }

  async function submitText(event: SubmitEvent) {
    event.preventDefault();
    if (isLoading) return;
    requestError = '';
    verificationResult = null;
    verificationSource = null;
    imageResult = null;

    if (!rawText.trim()) {
      requestError = 'Enter document text before submitting.';
      return;
    }

    isLoading = true;
    try {
      verificationResult = await verifyText(rawText);
      verificationSource = 'text';
    } catch (error) {
      requestError = getErrorMessage(error);
    } finally {
      isLoading = false;
    }
  }

  async function submitFile(event: SubmitEvent) {
    event.preventDefault();
    if (isLoading) return;
    requestError = '';
    verificationResult = null;
    verificationSource = null;
    imageResult = null;
    const submittedTab = activeTab;

    if (!selectedFile) {
      fileError = activeTab === 'pdf' ? 'Choose a PDF file first.' : 'Choose an image first.';
      return;
    }

    isLoading = true;
    try {
      if (submittedTab === 'pdf') {
        verificationResult = await verifyPdf(selectedFile);
        verificationSource = 'pdf';
      } else {
        imageResult = await verifyImage(selectedFile);
      }
    } catch (error) {
      requestError = getErrorMessage(error);
    } finally {
      isLoading = false;
    }
  }

  function getErrorMessage(error: unknown): string {
    return error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'An unexpected error occurred while contacting the API.';
  }

  function readableLabel(value: string): string {
    return value.replaceAll('_', ' ').toLowerCase();
  }

  function displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    return String(value);
  }

  function statusTone(value: string): string {
    if (value === 'SUCCESS' || value === 'PASS_GENUINE_CAPTURE') return 'positive';
    if (value === 'AUTO_APPROVE_ELIGIBLE') return 'positive';
    if (value === 'REJECT_OR_MANUAL_FRAUD_REVIEW') return 'negative';
    return 'caution';
  }
</script>

<svelte:head>
  <title>{activeItem.title} | XenDoc-Verify</title>
</svelte:head>

<div class="app-shell">
  <aside class="sidebar" aria-label="Main navigation">
    <a class="brand" href="#main" aria-label="XenDoc-Verify home">
      <span class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none">
          <path d="M7 16.5 13 22l12-13" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M16 3.5 27 8v7.5c0 6.2-4.2 10.8-11 13-6.8-2.2-11-6.8-11-13V8l11-4.5Z" stroke="currentColor" stroke-width="1.8" />
        </svg>
      </span>
      <span class="brand-copy">
        <strong>XenDoc</strong>
        <span>VERIFY</span>
      </span>
    </a>

    <div class="sidebar-section-label">WORKSPACE</div>
    <nav class="nav-list" aria-label="Verification tools">
      {#each navigation as item}
        <button
          class:active={activeTab === item.id}
          class="nav-item"
          type="button"
            disabled={isLoading}
            aria-current={activeTab === item.id ? 'page' : undefined}
            onclick={() => chooseTab(item.id)}
        >
          <span class="nav-icon" aria-hidden="true">{item.icon}</span>
          <span class="nav-copy">
            <strong>{item.title}</strong>
            <small>{item.subtitle}</small>
          </span>
          {#if activeTab === item.id}
            <span class="nav-indicator" aria-hidden="true"></span>
          {/if}
        </button>
      {/each}
    </nav>

    <div class="sidebar-footer">
      <div class="secure-mark" aria-hidden="true">
        <svg viewBox="0 0 20 20" fill="none">
          <rect x="4" y="8.5" width="12" height="9" rx="2" stroke="currentColor" stroke-width="1.5" />
          <path d="M6.5 8.5V6a3.5 3.5 0 0 1 7 0v2.5" stroke="currentColor" stroke-width="1.5" />
        </svg>
      </div>
      <div>
        <strong>Private by design</strong>
        <p>Documents are sent directly to your configured API.</p>
      </div>
    </div>
  </aside>

  <main id="main" class="main-content">
    <header class="topbar">
      <div class="breadcrumbs"><span>Workspace</span><span class="crumb-divider">/</span><strong>{activeItem.title}</strong></div>
      <div class="api-indicator">
        <span class="api-dot" aria-hidden="true"></span>
        <span>API configured</span>
      </div>
    </header>

    <div class="page-content">
      <section class="page-heading">
        <div>
          <p class="eyebrow">DOCUMENT INTELLIGENCE</p>
          <h1>{activeItem.title}</h1>
          <p class="page-description">
            {#if activeTab === 'text'}
              Extract applicant details and review deterministic lending checks.
            {:else if activeTab === 'pdf'}
              Upload a financial document to extract and review its contents.
            {:else}
              Review image quality signals returned by the forensic checks.
            {/if}
          </p>
        </div>
        <div class="secure-pill">
          <svg viewBox="0 0 18 18" fill="none" aria-hidden="true">
            <path d="M9 2 15 4.5v4.1c0 3.4-2.3 5.9-6 7.1-3.7-1.2-6-3.7-6-7.1V4.5L9 2Z" stroke="currentColor" stroke-width="1.4" />
            <path d="m6.3 8.7 1.8 1.8 3.7-3.8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          Secure review
        </div>
      </section>

      <section class="content-grid" aria-label="Verification">
        <div class="input-panel panel">
          <div class="panel-heading">
            <div class="step-number">01</div>
            <div>
              <h2>{activeTab === 'text' ? 'Document text' : activeTab === 'pdf' ? 'Upload a PDF' : 'Upload an image'}</h2>
              <p>{activeTab === 'text' ? 'Paste the text you want to verify.' : activeTab === 'pdf' ? 'Choose a searchable PDF document.' : 'Choose a clear photo of an identity document.'}</p>
            </div>
          </div>

          {#if activeTab === 'text'}
            <form onsubmit={submitText}>
              <label class="field-label" for="document-text">Document contents</label>
              <textarea
                id="document-text"
                bind:value={rawText}
                placeholder="Paste payslip, bank statement, or other document text here…"
                rows="12"
                disabled={isLoading}
              ></textarea>
              <div class="input-meta">
                <span>Text is sent securely to the configured API.</span>
                <span>{rawText.length.toLocaleString()} characters</span>
              </div>
              <div class="form-actions">
                <button class="button button-quiet" type="button" onclick={() => (rawText = sampleText)} disabled={isLoading}>
                  <span class="sparkle" aria-hidden="true">✦</span>
                  Use example
                </button>
                <button class="button button-primary" type="submit" disabled={isLoading || !rawText.trim()}>
                  {#if isLoading}<span class="spinner" aria-hidden="true"></span>{/if}
                  {isLoading ? 'Verifying…' : 'Verify document'}
                  {#if !isLoading}<span aria-hidden="true">→</span>{/if}
                </button>
              </div>
            </form>
          {:else}
            <form onsubmit={submitFile}>
              <label class="field-label" for="document-file">
                {activeTab === 'pdf' ? 'PDF document' : 'Identity image'}
              </label>
              <div
                class:has-file={selectedFile !== null}
                class="upload-zone"
                role="group"
                aria-label="Choose a file or drop it here"
                ondragover={(event) => event.preventDefault()}
                ondrop={handleFileDrop}
              >
                <input
                  id="document-file"
                  class="file-input"
                  type="file"
                  accept={activeTab === 'pdf' ? '.pdf,application/pdf' : '.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,image/*'}
                  onchange={handleFileChange}
                  bind:this={fileInput}
                  disabled={isLoading}
                  aria-describedby="upload-help"
                />
                <div class="upload-icon" aria-hidden="true">
                  {#if activeTab === 'pdf'}
                    <svg viewBox="0 0 28 28" fill="none">
                      <path d="M8 3.5h8l6 6V23a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 6 23V5a1.5 1.5 0 0 1 1.5-1.5Z" stroke="currentColor" stroke-width="1.6" />
                      <path d="M16 3.5V10h6M9 15h10m-10 3.5h10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
                    </svg>
                  {:else}
                    <svg viewBox="0 0 28 28" fill="none">
                      <rect x="3.5" y="5" width="21" height="18" rx="2.5" stroke="currentColor" stroke-width="1.6" />
                      <circle cx="10" cy="11" r="2" stroke="currentColor" stroke-width="1.6" />
                      <path d="m5 20 5.5-5 3.5 3 3.5-4 5.5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  {/if}
                </div>
                {#if selectedFile}
                  <strong class="selected-file">{selectedFile.name}</strong>
                  <span class="upload-caption">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB · Ready to upload</span>
                {:else}
                  <strong>Choose a file or drop it here</strong>
                  <span id="upload-help" class="upload-caption">
                    {activeTab === 'pdf' ? 'PDF files only' : 'PNG, JPEG, WebP, BMP, or TIFF'}
                  </span>
                {/if}
                <span class="browse-button" aria-hidden="true">Browse files</span>
              </div>
              {#if fileError}
                <p class="inline-error" role="alert">{fileError}</p>
              {/if}
              <p class="upload-note">
                {activeTab === 'pdf' ? 'Scanned PDFs may need OCR preprocessing before verification.' : 'Image checks are heuristic review signals, not proof of authenticity.'}
              </p>
              <div class="form-actions upload-actions">
                <span class="input-hint">{activeTab === 'pdf' ? 'Maximum file type: PDF' : 'Use a well-lit, in-focus image'}</span>
                <button class="button button-primary" type="submit" disabled={isLoading}>
                  {#if isLoading}<span class="spinner" aria-hidden="true"></span>{/if}
                  {isLoading ? 'Analyzing…' : activeTab === 'pdf' ? 'Verify PDF' : 'Analyze image'}
                  {#if !isLoading}<span aria-hidden="true">→</span>{/if}
                </button>
              </div>
            </form>
          {/if}
        </div>

        <aside class="guidance-panel">
          <div class="guidance-illustration" aria-hidden="true">
            <div class="illustration-sheet">
              <span class="illustration-line wide"></span>
              <span class="illustration-line"></span>
              <span class="illustration-line short"></span>
              <span class="illustration-stamp">✓</span>
            </div>
          </div>
          <p class="eyebrow">HOW IT WORKS</p>
          <h2>Review, then decide.</h2>
          <p class="guidance-copy">
            XenDoc-Verify returns extracted data and checks from your API. Review the findings in context before making a decision.
          </p>
          <div class="guidance-divider"></div>
          <div class="guidance-point">
            <span class="point-icon">1</span>
            <p><strong>Submit a document</strong><span>Text, PDF, or identity image</span></p>
          </div>
          <div class="guidance-point">
            <span class="point-icon">2</span>
            <p><strong>Review returned signals</strong><span>Results come from the API only</span></p>
          </div>
          <div class="guidance-point">
            <span class="point-icon">3</span>
            <p><strong>Use human judgment</strong><span>Checks are not definitive proof</span></p>
          </div>
        </aside>
      </section>

      {#if requestError}
        <div class="error-banner" role="alert">
          <span class="alert-icon" aria-hidden="true">!</span>
          <div><strong>Request failed</strong><p>{requestError}</p></div>
        </div>
      {/if}

      {#if isLoading}
        <section class="loading-panel panel" aria-live="polite">
          <span class="large-spinner" aria-hidden="true"></span>
          <div><strong>Working on your request</strong><p>Waiting for the verification API to return results…</p></div>
        </section>
      {:else if showVerificationResult && verificationResult}
        <section class="results-section" aria-live="polite" aria-label="Verification results">
          <div class="results-title">
            <div>
              <p class="eyebrow">API RESPONSE</p>
              <h2>Verification results</h2>
            </div>
            <span class="response-chip"><span class="response-dot"></span> Results received</span>
          </div>

          <div class="recommendation-card">
            <div class="recommendation-icon" aria-hidden="true">
              {#if verificationResult.lending_recommendation === 'AUTO_APPROVE_ELIGIBLE'}
                ✓
              {:else}
                !
              {/if}
            </div>
            <div class="recommendation-copy">
              <span class="result-label">LENDING RECOMMENDATION</span>
              <h3>{readableLabel(verificationResult.lending_recommendation)}</h3>
              <p>Review information only. This recommendation should not be treated as definitive proof of fraud or eligibility.</p>
            </div>
            <span class:positive={statusTone(verificationResult.lending_recommendation) === 'positive'} class:negative={statusTone(verificationResult.lending_recommendation) === 'negative'} class:caution={statusTone(verificationResult.lending_recommendation) === 'caution'} class="status-badge">
              {readableLabel(verificationResult.status)}
            </span>
          </div>

          <div class="result-summary-grid">
            <div class="result-card panel">
              <div class="result-card-heading">
                <div><span class="card-icon user-icon" aria-hidden="true">A</span><h3>Extracted data</h3></div>
                <span class="section-tag">APPLICANT</span>
              </div>
              <dl class="data-list">
                {#each Object.entries(verificationResult.extracted_data) as [key, value]}
                  <div class="data-row"><dt>{readableLabel(key)}</dt><dd>{displayValue(value)}</dd></div>
                {/each}
              </dl>
            </div>

            <div class="result-card panel">
              <div class="result-card-heading">
                <div><span class="card-icon time-icon" aria-hidden="true">◷</span><h3>Processing</h3></div>
                <span class="section-tag">TIMING</span>
              </div>
              <div class="processing-number">{displayValue(verificationResult.processing_time_ms)}<span>ms</span></div>
              <p class="small-muted">Reported by the verification API</p>
              <div class="api-status-row">
                <span>API status</span>
                <span class:positive={statusTone(verificationResult.status) === 'positive'} class:negative={statusTone(verificationResult.status) === 'negative'} class:caution={statusTone(verificationResult.status) === 'caution'} class="status-badge compact">{displayValue(verificationResult.status)}</span>
              </div>
            </div>
          </div>

          <div class="result-card panel details-card">
            <div class="result-card-heading">
              <div><span class="card-icon check-icon" aria-hidden="true">✓</span><h3>Deterministic checks</h3></div>
              <span class="section-tag">{Object.keys(verificationResult.deterministic_checks).length} CHECKS</span>
            </div>
            {#if Object.keys(verificationResult.deterministic_checks).length}
              <dl class="checks-grid">
                {#each Object.entries(verificationResult.deterministic_checks) as [key, value]}
                  <div class="check-item">
                    <span class:check-positive={value === true} class:check-negative={value === false} class="check-mark" aria-hidden="true">{value === true ? '✓' : value === false ? '!' : '·'}</span>
                    <div><dt>{readableLabel(key)}</dt><dd>{displayValue(value)}</dd></div>
                  </div>
                {/each}
              </dl>
            {:else}
              <p class="empty-message">No deterministic checks returned.</p>
            {/if}
          </div>

          <div class="result-card panel details-card">
            <div class="result-card-heading">
              <div><span class="card-icon flag-icon" aria-hidden="true">!</span><h3>Risk flags</h3></div>
              <span class="section-tag">{verificationResult.risk_flags.length} FLAGS</span>
            </div>
            {#if verificationResult.risk_flags.length}
              <ul class="flag-list">
                {#each verificationResult.risk_flags as flag}
                  <li><span class="flag-marker" aria-hidden="true">!</span>{flag}</li>
                {/each}
              </ul>
            {:else}
              <p class="empty-message no-flags"><span aria-hidden="true">✓</span> No flags returned</p>
            {/if}
          </div>
          <p class="disclaimer">
            Verification results are decision-support information. Risk flags and recommendations are not definitive proof of fraud, identity, or lending eligibility.
          </p>
        </section>
      {:else if activeTab === 'image' && imageResult}
        <section class="results-section" aria-live="polite" aria-label="Image forensics results">
          <div class="results-title">
            <div><p class="eyebrow">API RESPONSE</p><h2>Image forensics results</h2></div>
            <span class="response-chip"><span class="response-dot"></span> Results received</span>
          </div>

          <div class="forensics-verdict panel">
            <div class:positive={statusTone(imageResult.authenticity_verdict) === 'positive'} class:negative={statusTone(imageResult.authenticity_verdict) === 'negative'} class:caution={statusTone(imageResult.authenticity_verdict) === 'caution'} class="verdict-icon" aria-hidden="true">
              {imageResult.authenticity_verdict === 'PASS_GENUINE_CAPTURE' ? '✓' : '!'}
            </div>
            <div class="verdict-copy">
              <span class="result-label">AUTHENTICITY VERDICT</span>
              <h3>{readableLabel(imageResult.authenticity_verdict)}</h3>
              <p>Heuristic image checks are not a guarantee of authenticity. Review the image and signals in context.</p>
            </div>
            <div class="resolution-block"><span>IMAGE RESOLUTION</span><strong>{imageResult.resolution}</strong></div>
          </div>

          <div class="result-card panel details-card">
            <div class="result-card-heading">
              <div><span class="card-icon metric-icon" aria-hidden="true">⌁</span><h3>Forensic metrics</h3></div>
              <span class="section-tag">{Object.keys(imageResult.metrics).length} METRICS</span>
            </div>
            {#if Object.keys(imageResult.metrics).length}
              <dl class="checks-grid metric-grid">
                {#each Object.entries(imageResult.metrics) as [key, value]}
                  <div class="check-item">
                    <span class="metric-symbol" aria-hidden="true">↗</span>
                    <div><dt>{readableLabel(key)}</dt><dd>{displayValue(value)}</dd></div>
                  </div>
                {/each}
              </dl>
            {:else}
              <p class="empty-message">No forensic metrics returned.</p>
            {/if}
          </div>

          <div class="result-card panel details-card">
            <div class="result-card-heading">
              <div><span class="card-icon flag-icon" aria-hidden="true">!</span><h3>Forensic flags</h3></div>
              <span class="section-tag">{imageResult.forensic_flags.length} FLAGS</span>
            </div>
            {#if imageResult.forensic_flags.length}
              <ul class="flag-list">
                {#each imageResult.forensic_flags as flag}
                  <li><span class="flag-marker" aria-hidden="true">!</span>{flag}</li>
                {/each}
              </ul>
            {:else}
              <p class="empty-message no-flags"><span aria-hidden="true">✓</span> No flags returned</p>
            {/if}
          </div>
          <p class="disclaimer">
            Forensic flags are heuristic review signals and cannot guarantee that an image is genuine or fraudulent.
          </p>
        </section>
      {:else if !requestError}
        <div class="empty-state" aria-live="polite">
          <span class="empty-state-mark" aria-hidden="true">✦</span>
          <div><strong>Your results will appear here</strong><p>Submit a document to see the response from your verification API.</p></div>
        </div>
      {/if}

      <footer class="page-footer">
        <span>XenDoc-Verify</span>
        <span>Document intelligence for human review</span>
      </footer>
    </div>
  </main>
</div>
