"""
Policy-to-Action Assistant — FastAPI Backend
Entry point: registers all routers, configures CORS, starts server.
"""
import sys
import os

# Make sure backend/ is on the path when running from project root
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.upload  import router as upload_router
from api.routes.process import router as process_router
from api.routes.status  import router as status_router
from api.routes.result  import router as result_router
from config import ALLOWED_ORIGINS

app = FastAPI(
    title       = "Policy-to-Action Assistant",
    description = "Hybrid AI system for extracting actionable info from college/scholarship notices.",
    version     = "1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(upload_router,  prefix="/api", tags=["upload"])
app.include_router(process_router, prefix="/api", tags=["process"])
app.include_router(status_router,  prefix="/api", tags=["status"])
app.include_router(result_router,  prefix="/api", tags=["result"])


@app.get("/")
async def root():
    return {
        "name":    "Policy-to-Action Assistant",
        "status":  "running",
        "docs":    "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Run ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = "0.0.0.0",
        port    = 8000,
        reload  = True,
        workers = 1,
    )
