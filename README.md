# Policy-to-Action

## Problem Statement
Real-world official notices—such as government scholarships, college internships, and policy documents—are inherently messy, unstructured, and dense. 
Applicants frequently miss critical deadlines, misinterpret complex eligibility criteria, or fail to submit mandatory documents because extracting actionable
requirements from these PDFs manually is error-prone and time-consuming. 

## Approach
The system utilizes a hybrid local-first pipeline that prioritizes speed and efficiency, falling back on AI only when strictly necessary. 

1. **Text Extraction:** Raw text is pulled from documents using `pdfplumber` while preserving line structure.
2. **Line Filtering:** Every line is scored against keyword banks. Irrelevant lines (blank space, decorative elements, location data) are dropped, reducing an 80-line document to roughly 20 highly relevant lines.
3. **Regex Extraction:** Five parallel extractors run across the filtered lines to pull out deadlines, document requirements, eligibility thresholds (CGPA, percentage, year of study), instructions, and stipends.
4. **Confidence Scoring:** Extracted fields are weighted and scored. For example, finding multiple valid dates or mandatory documents yields a high confidence score.
5. **Decision Engine:** If the overall extraction confidence is above a set threshold (0.55) and all dates are parseable, the AI call is bypassed entirely.
6. **Rule Engine:** The system evaluates the extracted data against the user's personal profile to determine document availability, eligibility pass/fail status, and deadline risk factors.

## Tech Stack
* **Core Backend:** Python
* **Document Parsing:** `pdfplumber`
* **Text Processing:** Regular Expressions (Regex)
* **AI Integration:** Google Gemini 2.0 Flash
* **Frontend:** Vanilla HTML/CSS/JS

## AI Implementation
Google's Gemini 2.0 Flash is utilized as a targeted fallback mechanism rather than the primary parser. The Decision Engine triggers the AI exclusively under the following conditions:
* Overall regex extraction confidence falls below 0.55 (e.g., unusual formatting or heavily scanned documents).
* Any deadline lacks parseable dates (e.g., phrases like "TBA" or "contact office").
* Zero required documents are detected.
* Vague language is identified.

When triggered, the system does not send the entire raw PDF to the AI. It only sends the pre-filtered, relevant text lines. This reduces the AI workload to roughly 500 tokens per call, minimizing costs and latency.

## 5-Second Constraints
The architecture is designed to guarantee a sub-5-second response time from upload to UI render. 
* The pure library text extraction is completed in under 1 second.
* The line filtering, parallel regex extraction, and confidence scoring execute in under 100 milliseconds.
* By skipping the AI network call entirely for well-structured documents, the fast path generates the complete JSON payload instantly.
* If Gemini is triggered, the minimal token payload ensures a rapid response, and the system can process AI refinement in the background while the user begins reading the initial rule-based checklist.

## Beginner-Friendly UI and UX
The frontend transforms bureaucratic jargon into an intuitive, visually digestible format for end-users. Instead of asking users to read the document, the interface immediately serves three clear components:
* **Checklists:** A numbered, unified list combining document requirements and eligibility status, visually tagged as "Done," "Missing," or "Pending" based on the user's stored profile.
* **Alerts:** Immediate, color-coded warnings for critical issues (e.g., missing mandatory documents or failing an eligibility requirement).
* **Timelines:** All extracted dates are sorted by urgency, featuring automated buffer reminders (e.g., "Start preparing 7 days before") to help users manage their schedules proactively.
