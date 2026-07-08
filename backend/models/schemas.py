# models/schemas.py
# ─────────────────────────────────────────────────────────────
# This file defines the DATA SHAPES used throughout our API.
# Pydantic models validate incoming and outgoing data automatically.
# Think of these as "blueprints" for what data should look like.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel   # BaseModel = base class that gives us auto-validation
from typing import List, Dict, Optional  # Python type hints for lists, dicts, optional fields


# ── Skill entry: one detected skill with its estimated level ──
class SkillEntry(BaseModel):
    name: str               # e.g., "Python"
    level: str              # "Beginner" / "Intermediate" / "Expert"
    confidence: float       # 0.0 – 1.0 how confident we are in the level


# ── Full parsed resume structure ──────────────────────────────
class ParsedResume(BaseModel):
    name: Optional[str] = None           # Candidate's full name
    email: Optional[str] = None          # Contact email
    phone: Optional[str] = None          # Contact phone
    skills: List[SkillEntry] = []        # List of detected skills
    education: List[str] = []            # Education entries as plain strings
    experience: List[str] = []           # Work experience entries
    raw_text: str = ""                   # Full extracted text (used for matching)
    word_count: int = 0                  # Total words (quick quality check)


# ── Job matching request body ──────────────────────────────────
class JobMatchRequest(BaseModel):
    resume_text: str          # Raw text of the resume (from parse step)
    job_description: str      # The JD pasted by the recruiter


# ── Job matching result ────────────────────────────────────────
class JobMatchResult(BaseModel):
    match_score: float                  # 0–100 percentage
    matched_skills: List[str] = []      # Skills present in both resume & JD
    missing_skills: List[str] = []      # Skills in JD but NOT in resume (skill gaps)
    recommendation: str = ""            # Short human-readable verdict


# ── Interview question generator request ──────────────────────
class QuestionRequest(BaseModel):
    resume_text: str
    job_description: str
    job_title: Optional[str] = "Software Engineer"  # defaults to generic title


# ── Single interview question ──────────────────────────────────
class InterviewQuestion(BaseModel):
    category: str    # "Technical" | "Behavioral" | "Role-Based"
    question: str    # The actual question text
    rationale: str   # Why this question was generated (transparency)


# ── Full question bank returned to frontend ───────────────────
class QuestionBank(BaseModel):
    technical: List[InterviewQuestion] = []
    behavioral: List[InterviewQuestion] = []
    role_based: List[InterviewQuestion] = []
    total_count: int = 0
