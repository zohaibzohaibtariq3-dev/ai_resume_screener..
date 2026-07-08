# routes/resume_routes.py
# ─────────────────────────────────────────────────────────────
# All API endpoints live here as an APIRouter.
# We keep routes separate from main.py to keep things organized.
# main.py just "includes" this router.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional

# Import our utility functions
from utils.pdf_extractor import extract_text_from_pdf
from utils.resume_parser import parse_resume
from utils.skill_analyzer import detect_skills
from utils.job_matcher import match_job
from utils.question_generator import generate_questions

# Import our data models
from models.schemas import (
    ParsedResume, JobMatchRequest, JobMatchResult,
    QuestionRequest, QuestionBank, SkillEntry
)

# ── Create router ─────────────────────────────────────────────
# APIRouter is like a "mini FastAPI app" — we group related routes here.
# prefix="/api/v1" means all routes start with /api/v1/...
router = APIRouter(prefix="/api/v1", tags=["Resume Intelligence"])


# ─────────────────────────────────────────────────────────────
# ENDPOINT 1: /upload_resume
# Takes a PDF file, extracts text, returns raw text + page count.
# This is the entry point — every other feature depends on this.
# ─────────────────────────────────────────────────────────────
@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...)   # UploadFile = FastAPI's file upload type
):
    """
    POST /api/v1/upload_resume
    Body: multipart/form-data with a PDF file

    Returns:
      - filename: original file name
      - page_count: number of pages in the PDF
      - word_count: approximate word count
      - text_preview: first 300 chars of extracted text
      - full_text: complete extracted text (used in subsequent calls)
    """

    # Validate that the uploaded file is actually a PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file."
        )

    # Read the file bytes into memory
    # await is used because this is an async operation
    file_bytes = await file.read()

    # Safety check: reject empty files
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # File size limit: 10 MB (PDFs should be much smaller)
    MAX_SIZE_MB = 10
    if len(file_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_SIZE_MB}MB."
        )

    # Extract text from the PDF
    try:
        extracted_text, page_count = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )

    # Sanity check: did we actually get any text?
    if not extracted_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. The PDF may be scanned/image-only."
        )

    return {
        "filename":     file.filename,
        "page_count":   page_count,
        "word_count":   len(extracted_text.split()),
        "text_preview": extracted_text[:300],   # Just for UI display
        "full_text":    extracted_text           # Full text for next API calls
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 2: /parse_resume
# Takes resume text → returns structured data + detected skills
# ─────────────────────────────────────────────────────────────
@router.post("/parse_resume", response_model=ParsedResume)
async def parse_resume_endpoint(
    resume_text: str = Form(...)   # Form field (sent as form data, not JSON)
):
    """
    POST /api/v1/parse_resume
    Body: form field `resume_text`

    Returns a ParsedResume object with name, email, phone, skills, etc.
    """

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text cannot be empty.")

    # Parse structured fields from text
    parsed_data = parse_resume(resume_text)

    # Detect skills separately (returns List[SkillEntry])
    skills = detect_skills(resume_text)

    # Build and return the full ParsedResume model
    return ParsedResume(
        name=parsed_data["name"],
        email=parsed_data["email"],
        phone=parsed_data["phone"],
        skills=skills,
        education=parsed_data["education"],
        experience=parsed_data["experience"],
        raw_text=resume_text,
        word_count=parsed_data["word_count"]
    )


# ─────────────────────────────────────────────────────────────
# ENDPOINT 3: /match_job
# Takes resume text + job description → returns similarity score
# ─────────────────────────────────────────────────────────────
@router.post("/match_job", response_model=JobMatchResult)
async def match_job_endpoint(request: JobMatchRequest):
    """
    POST /api/v1/match_job
    Body: JSON with resume_text and job_description

    Returns match score, matched skills, missing skills, recommendation.
    """

    if not request.resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text is required.")
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required.")

    # Minimum length sanity check
    if len(request.job_description.split()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short. Please provide a detailed JD."
        )

    result = match_job(request.resume_text, request.job_description)
    return result


# ─────────────────────────────────────────────────────────────
# ENDPOINT 4: /generate_questions
# Takes resume + JD + job title → returns interview question bank
# ─────────────────────────────────────────────────────────────
@router.post("/generate_questions", response_model=QuestionBank)
async def generate_questions_endpoint(request: QuestionRequest):
    """
    POST /api/v1/generate_questions
    Body: JSON with resume_text, job_description, and optional job_title

    Returns categorized interview questions:
      - technical: skill-specific questions
      - behavioral: situational/STAR questions
      - role_based: role-specific questions
    """

    if not request.resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text is required.")
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required.")

    questions = generate_questions(
        resume_text=request.resume_text,
        job_description=request.job_description,
        job_title=request.job_title or "Software Engineer"
    )
    return questions


# ─────────────────────────────────────────────────────────────
# ENDPOINT 5: /analyze_skills (bonus — skill-only endpoint)
# ─────────────────────────────────────────────────────────────
@router.post("/analyze_skills")
async def analyze_skills_endpoint(
    resume_text: str = Form(...)
):
    """
    POST /api/v1/analyze_skills
    Lightweight endpoint: just returns skill analysis, nothing else.
    Useful for quick skill checks without full parsing.
    """
    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="resume_text cannot be empty.")

    skills = detect_skills(resume_text)

    # Group by level for a cleaner response
    grouped = {"Expert": [], "Intermediate": [], "Beginner": []}
    for skill in skills:
        grouped[skill.level].append(skill.name)

    return {
        "total_skills_detected": len(skills),
        "skills_by_level": grouped,
        "all_skills": [s.dict() for s in skills]
    }


# ─────────────────────────────────────────────────────────────
# ENDPOINT 6: /health (simple ping — used by deployment platforms)
# ─────────────────────────────────────────────────────────────
@router.get("/health")
async def health_check():
    """GET /api/v1/health — Returns API status. Used by Render/Railway health checks."""
    return {"status": "healthy", "version": "1.0.0", "service": "AI Resume Screener"}
