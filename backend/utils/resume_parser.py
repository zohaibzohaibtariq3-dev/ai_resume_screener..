# utils/resume_parser.py
# ─────────────────────────────────────────────────────────────
# Takes clean resume text → extracts structured fields:
#   Name, Email, Phone, Education, Experience
# Uses regex + spaCy NER (Named Entity Recognition).
# ─────────────────────────────────────────────────────────────

import re                        # Regex for pattern matching
import spacy                     # NLP library for entity detection
from typing import List, Optional

# ── Load spaCy's small English model ─────────────────────────
# "en_core_web_sm" is a lightweight model (~12MB) that can detect
# PERSON names, ORG names, DATE entities, etc.
# We load it once at module level (not inside a function) so we
# don't reload it on every API call — that would be very slow.
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # If the model isn't downloaded yet, tell the user how to fix it
    raise RuntimeError(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )


# ── Section keywords: used to find resume sections ───────────
# When parsing a resume, we look for lines that act as headings.
EDUCATION_KEYWORDS = [
    "education", "academic", "qualification", "degree",
    "university", "college", "school", "b.s.", "m.s.", "b.e.", "b.tech", "m.tech"
]

EXPERIENCE_KEYWORDS = [
    "experience", "work history", "employment", "career",
    "professional background", "internship", "projects", "positions held"
]


def extract_name(text: str) -> Optional[str]:
    """
    Strategy: Run spaCy NER on the FIRST 500 characters.
    Resumes almost always put the name at the very top.
    We look for the first PERSON entity spaCy finds.
    """
    # Only process the beginning — avoids false positives in body text
    snippet = text[:500]
    doc = nlp(snippet)

    for ent in doc.ents:
        # ent.label_ == "PERSON" means spaCy thinks this is a person's name
        if ent.label_ == "PERSON":
            name = ent.text.strip()
            # Basic sanity check: names are usually 2–4 words, not too long
            if 2 <= len(name.split()) <= 4:
                return name

    # Fallback: take the very first non-empty line (often the name)
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) < 50:   # Names are short
            # Make sure it's not an email or phone line
            if not re.search(r'[@\d]', line):
                return line

    return None   # Couldn't find a name


def extract_email(text: str) -> Optional[str]:
    """
    Regex to find email addresses anywhere in the text.
    Pattern breakdown:
      [a-zA-Z0-9._%+\-]+ → local part (before @)
      @                   → the @ symbol
      [a-zA-Z0-9.\-]+    → domain name
      \.[a-zA-Z]{2,}     → TLD like .com, .io, .co.uk
    """
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """
    Catches common phone formats:
      +92-300-1234567  |  (042) 1234567  |  03001234567
    The pattern is deliberately loose to handle international numbers.
    """
    pattern = r'(\+?\d[\d\s\-().]{7,}\d)'
    match = re.search(pattern, text)
    if match:
        phone = match.group(0).strip()
        # Only return if it looks like a real phone (7–15 digits)
        digits_only = re.sub(r'\D', '', phone)
        if 7 <= len(digits_only) <= 15:
            return phone
    return None


def extract_section(text: str, section_keywords: List[str]) -> List[str]:
    """
    Generic section extractor.
    How it works:
      1. Split resume into lines
      2. When we hit a line that matches a section keyword → start collecting
      3. Stop when we hit another known section heading
      4. Return collected lines (filtered to non-empty)

    This works for both Education and Experience sections.
    """
    lines = text.splitlines()
    collecting = False          # Are we currently inside the target section?
    section_lines = []

    # All known section headings (so we know when to STOP collecting)
    all_headings = EDUCATION_KEYWORDS + EXPERIENCE_KEYWORDS + [
        "skills", "certifications", "awards", "languages",
        "summary", "objective", "publications", "references"
    ]

    for line in lines:
        lower_line = line.lower().strip()

        # Check if this line IS the section we want
        if any(kw in lower_line for kw in section_keywords):
            collecting = True
            continue   # Skip the heading line itself

        # Check if this is a DIFFERENT section heading → stop collecting
        if collecting and any(kw in lower_line for kw in all_headings):
            # But only stop if it's actually a short heading-like line
            if len(lower_line) < 40:
                break

        # Collect the line if we're inside the target section
        if collecting and line.strip():
            section_lines.append(line.strip())

    # Return up to 10 entries (avoids overflow in response)
    return section_lines[:10]


def parse_resume(text: str) -> dict:
    """
    Master function: calls all the extractors above
    and bundles results into a dictionary that maps to ParsedResume schema.
    """
    return {
        "name":       extract_name(text),
        "email":      extract_email(text),
        "phone":      extract_phone(text),
        "education":  extract_section(text, EDUCATION_KEYWORDS),
        "experience": extract_section(text, EXPERIENCE_KEYWORDS),
        "raw_text":   text,
        "word_count": len(text.split()),
    }
