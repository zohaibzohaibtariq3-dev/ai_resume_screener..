# main.py
# ─────────────────────────────────────────────────────────────
# Entry point for the FastAPI application.
# This is the file you run to start the server:
#   uvicorn main:app --reload
#
# Responsibilities:
#   1. Create the FastAPI app instance
#   2. Configure CORS (Cross-Origin Resource Sharing)
#   3. Register all routers
#   4. Add a root endpoint for quick testing
# ─────────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Allows frontend to call our API
from routes.resume_routes import router             # Our route handlers


# ── Create the FastAPI application ───────────────────────────
# title/description/version appear in the auto-generated docs at /docs
app = FastAPI(
    title="AI Resume Screener & Interview Intelligence",
    description=(
        "Upload a resume PDF → get parsed data, skill analysis, "
        "job match scores, and interview questions. Built with FastAPI + spaCy + scikit-learn."
    ),
    version="1.0.0",
    docs_url="/docs",    # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",  # ReDoc UI at http://localhost:8000/redoc
)


# ── CORS Middleware ───────────────────────────────────────────
# CORS = browser security feature that blocks requests from different origins.
# We need to allow our Streamlit frontend (running on a different port) to talk to this API.
# In production, replace "*" with your actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (use specific URLs in prod)
    allow_credentials=True,       # Allow cookies/auth headers
    allow_methods=["*"],          # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],          # Allow any header
)


# ── Include our routes ────────────────────────────────────────
# This "attaches" all routes from resume_routes.py to our app.
# All routes will have the /api/v1 prefix we set in resume_routes.py
app.include_router(router)


# ── Root endpoint ─────────────────────────────────────────────
# Simple welcome message — useful to confirm the server is running.
@app.get("/")
async def root():
    return {
        "message": "🚀 AI Resume Screener API is running!",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": [
            "POST /api/v1/upload_resume",
            "POST /api/v1/parse_resume",
            "POST /api/v1/match_job",
            "POST /api/v1/generate_questions",
            "POST /api/v1/analyze_skills",
        ]
    }


# ── Run directly ──────────────────────────────────────────────
# This block runs only when you execute: python main.py
# In production, use: uvicorn main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",   # Listen on all network interfaces
        port=8000,
        reload=True        # Auto-reload on file changes (dev only)
    )
