/* ── Config ──────────────────────────────────────────────────────────── */
const API_BASE     = "http://localhost:8000/api";
const POLL_MS      = 2000;   // poll every 2 seconds

/* ── State ───────────────────────────────────────────────────────────── */
let currentJobId   = null;
let pollTimer      = null;
let uploadedFile   = null;

/* ── DOM refs ────────────────────────────────────────────────────────── */
const fileInput      = document.getElementById("file-input");
const uploadZone     = document.getElementById("upload-zone");
const fileInfo       = document.getElementById("file-info");
const fileName       = document.getElementById("file-name");
const clearFileBtn   = document.getElementById("clear-file");
const analyseBtn     = document.getElementById("analyse-btn");
const btnText        = analyseBtn.querySelector(".btn-text");
const btnSpinner     = analyseBtn.querySelector(".btn-spinner");

const resultsEmpty   = document.getElementById("results-empty");
const statusBar      = document.getElementById("status-bar");
const statusDot      = document.getElementById("status-dot");
const statusText     = document.getElementById("status-text");
const confidenceBadge= document.getElementById("confidence-badge");
const aiBadge        = document.getElementById("ai-badge");

const alertsSection  = document.getElementById("alerts-section");
const alertsList     = document.getElementById("alerts-list");
const timelineSection= document.getElementById("timeline-section");
const timelineList   = document.getElementById("timeline-list");
const checklistSection=document.getElementById("checklist-section");
const checklistList  = document.getElementById("checklist-list");
const extractedSection=document.getElementById("extracted-section");
const extractedBody  = document.getElementById("extracted-body");
const extractedToggle= document.getElementById("extracted-toggle");

/* ── File upload ────────────────────────────────────────────────────── */
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", e => setFile(e.target.files[0]));

uploadZone.addEventListener("dragover", e => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", e => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});

clearFileBtn.addEventListener("click", clearFile);

function setFile(f) {
  uploadedFile = f;
  fileName.textContent = f.name;
  fileInfo.classList.remove("hidden");
  uploadZone.classList.add("hidden");
  checkEnableAnalyse();
}

function clearFile() {
  uploadedFile  = null;
  fileInput.value = "";
  fileInfo.classList.add("hidden");
  uploadZone.classList.remove("hidden");
  checkEnableAnalyse();
}

/* ── Form inputs ─────────────────────────────────────────────────────── */
document.querySelectorAll(".form-input").forEach(el =>
  el.addEventListener("input", checkEnableAnalyse)
);

function checkEnableAnalyse() {
  analyseBtn.disabled = !uploadedFile;
}

/* ── Profile builder ─────────────────────────────────────────────────── */
function buildProfile() {
  const docsRaw = document.getElementById("p-docs").value;
  const docs = docsRaw.split(",").map(d => d.trim().toLowerCase()).filter(Boolean);
  return {
    name:          document.getElementById("p-name").value.trim(),
    cgpa:          parseFloat(document.getElementById("p-cgpa").value) || 0,
    percentage:    parseFloat(document.getElementById("p-pct").value)  || 0,
    branch:        document.getElementById("p-branch").value.trim(),
    year_of_study: parseInt(document.getElementById("p-year").value)   || 1,
    semester:      parseInt(document.getElementById("p-sem").value)    || 1,
    nationality:   "Indian",
    available_docs: docs,
  };
}

/* ── Main flow ───────────────────────────────────────────────────────── */
analyseBtn.addEventListener("click", async () => {
  if (!uploadedFile) return;
  await runPipeline();
});

async function runPipeline() {
  setLoading(true);
  clearResults();
  stopPoll();

  try {
    // Step 1: Upload file
    setStatus("Extracting text…", "processing");
    const jobId = await uploadFile(uploadedFile);
    currentJobId = jobId;

    // Step 2: Process
    setStatus("Running analysis…", "processing");
    const initialResult = await processJob(jobId, buildProfile());

    // Step 3: Render fast result immediately
    renderResult(initialResult);
    setLoading(false);

    // Step 4: Poll if AI is pending
    if (initialResult.status === "ai_pending") {
      setStatus("Refining with AI in background…", "processing");
      startPoll(jobId);
    } else {
      setStatus("Analysis complete", "done");
    }

  } catch (err) {
    setLoading(false);
    setStatus(`Error: ${err.message}`, "error");
    console.error(err);
  }
}

/* ── API calls ───────────────────────────────────────────────────────── */
async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body:   formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  const data = await res.json();
  return data.job_id;
}

async function processJob(jobId, profile) {
  const res = await fetch(`${API_BASE}/process`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ job_id: jobId, profile }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Processing failed");
  }
  return res.json();
}

async function fetchResult(jobId) {
  const res = await fetch(`${API_BASE}/result/${jobId}`);
  if (!res.ok) return null;
  return res.json();
}

async function fetchStatus(jobId) {
  const res = await fetch(`${API_BASE}/status/${jobId}`);
  if (!res.ok) return null;
  return res.json();
}

/* ── Polling ─────────────────────────────────────────────────────────── */
function startPoll(jobId) {
  pollTimer = setInterval(async () => {
    const status = await fetchStatus(jobId);
    if (!status) return;

    if (status.ai_complete) {
      stopPoll();
      const result = await fetchResult(jobId);
      if (result) {
        renderResult(result);
        setStatus("Analysis complete — AI refined", "done");
      }
    }
  }, POLL_MS);
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

/* ── Rendering ───────────────────────────────────────────────────────── */
function renderResult(result) {
  resultsEmpty.classList.add("hidden");
  statusBar.classList.remove("hidden");

  // Confidence badge
  if (result.confidence) {
    const pct = Math.round(result.confidence.overall * 100);
    confidenceBadge.textContent = `confidence ${pct}%`;
  }

  // AI badge
  if (result.ai_was_used) {
    aiBadge.classList.remove("hidden");
  }

  renderAlerts(result.alerts     || []);
  renderTimeline(result.timeline || []);
  renderChecklist(result.checklist || []);
  renderExtracted(result.extracted);
}

/* Alerts */
function renderAlerts(alerts) {
  if (!alerts.length) { alertsSection.classList.add("hidden"); return; }
  alertsSection.classList.remove("hidden");
  alertsSection.classList.add("fade-in");
  alertsList.innerHTML = alerts.map(a => `
    <div class="alert-item ${a.severity}">
      <span class="alert-dot"></span>
      <span>${escHtml(a.message)}</span>
    </div>
  `).join("");
}

/* Timeline */
function renderTimeline(entries) {
  if (!entries.length) { timelineSection.classList.add("hidden"); return; }
  timelineSection.classList.remove("hidden");
  timelineSection.classList.add("fade-in");
  timelineList.innerHTML = entries.map(e => `
    <div class="timeline-entry">
      <span class="timeline-date">${escHtml(e.date_str)}</span>
      <span class="timeline-task">${escHtml(e.task)}</span>
      <span class="timeline-badge ${e.risk}">${
        e.days_remaining !== null && e.days_remaining !== undefined
          ? (e.days_remaining < 0 ? "overdue" : `${e.days_remaining}d`)
          : "?"
      }</span>
    </div>
  `).join("");
}

/* Checklist */
let allChecklistItems = [];

function renderChecklist(items) {
  if (!items.length) { checklistSection.classList.add("hidden"); return; }
  checklistSection.classList.remove("hidden");
  checklistSection.classList.add("fade-in");
  allChecklistItems = items;
  renderChecklistFiltered("all");

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", function() {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      this.classList.add("active");
      renderChecklistFiltered(this.dataset.cat);
    });
  });
}

function renderChecklistFiltered(cat) {
  const filtered = cat === "all"
    ? allChecklistItems
    : allChecklistItems.filter(i => i.category === cat);

  const iconMap = { done: "✓", missing: "✕", pending: "⋯", unknown: "?" };

  checklistList.innerHTML = filtered.map(item => `
    <div class="checklist-item">
      <span class="check-icon ${item.status}">${iconMap[item.status] || "?"}</span>
      <span class="check-label">${escHtml(item.task)}</span>
      <span class="check-cat">${escHtml(item.category)}</span>
    </div>
  `).join("") || `<p style="font-size:13px;color:var(--text3);padding:10px 0">No items in this category.</p>`;
}

/* Extracted data (collapsible) */
function renderExtracted(extracted) {
  if (!extracted) { extractedSection.classList.add("hidden"); return; }
  extractedSection.classList.remove("hidden");

  const groups = [
    {
      label: "Deadlines",
      items: (extracted.deadlines || []).map(d =>
        d.date_str ? `${d.label}: ${d.date_str}` : d.raw_text
      ),
    },
    { label: "Required documents", items: extracted.required_docs || [] },
    { label: "Eligibility",        items: extracted.eligibility   || [] },
    { label: "Instructions",       items: (extracted.instructions || []).slice(0, 5) },
    { label: "Stipend",            items: extracted.stipend ? [extracted.stipend] : [] },
  ];

  extractedBody.innerHTML = groups
    .filter(g => g.items.length)
    .map(g => `
      <div class="extracted-group">
        <div class="extracted-label">${escHtml(g.label)}</div>
        <div class="extracted-chips">
          ${g.items.map(i => `<span class="chip">${escHtml(i)}</span>`).join("")}
        </div>
      </div>
    `).join("");

  // Collapse/expand
  let open = false;
  extractedBody.classList.add("hidden");
  extractedToggle.addEventListener("click", () => {
    open = !open;
    extractedBody.classList.toggle("hidden", !open);
    extractedToggle.querySelector(".toggle-arrow").classList.toggle("open", open);
  });
}

/* ── UI helpers ──────────────────────────────────────────────────────── */
function setLoading(loading) {
  analyseBtn.disabled = loading;
  btnText.textContent  = loading ? "Analysing…" : "Analyse Document";
  btnSpinner.classList.toggle("hidden", !loading);
}

function setStatus(msg, state) {
  statusBar.classList.remove("hidden");
  statusText.textContent = msg;
  statusDot.className    = "status-dot";
  if (state === "done")  statusDot.classList.add("done");
  if (state === "error") statusDot.classList.add("error");
}

function clearResults() {
  [alertsSection, timelineSection, checklistSection, extractedSection].forEach(el => {
    el.classList.add("hidden");
  });
  alertsList.innerHTML = timelineList.innerHTML = checklistList.innerHTML = extractedBody.innerHTML = "";
  aiBadge.classList.add("hidden");
  confidenceBadge.textContent = "";
  resultsEmpty.classList.remove("hidden");
}

function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
