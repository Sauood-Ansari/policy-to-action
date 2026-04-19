import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = "gemini-2.0-flash"   # free-tier friendly, fast

# Confidence thresholds
CONFIDENCE_THRESHOLD_FOR_AI = 0.55       # below this → trigger AI
DEADLINE_CONFIDENCE_MIN     = 0.60       # below this → trigger AI even if overall is OK
MAX_FILTERED_LINES          = 60         # lines sent to AI (cost guard)

# Deadline risk windows (days)
CRITICAL_DAYS = 3
WARNING_DAYS  = 7

# CORS origins (allow frontend dev server)
ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000",
                   "http://localhost:5500", "http://127.0.0.1:5500",
                   "null"]               # file:// opened directly in browser
