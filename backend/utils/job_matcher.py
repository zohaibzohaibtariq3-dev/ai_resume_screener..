# utils/job_matcher.py
# ─────────────────────────────────────────────────────────────
# Compares a resume against a job description.
# Uses TF-IDF vectorization + cosine similarity from scikit-learn.
#
# TF-IDF = Term Frequency × Inverse Document Frequency
#   - High score for words that appear often in THIS doc but rarely elsewhere
#   - Basically: "what words make this doc unique?"
#
# Cosine Similarity = how "similar" two vectors are (0 = opposite, 1 = identical)
# ─────────────────────────────────────────────────────────────

import re
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer  # The magic
from sklearn.metrics.pairwise import cosine_similarity        # Distance calc
from utils.skill_analyzer import SKILL_TAXONOMY               # Reuse skill list
from models.schemas import JobMatchResult


# ── Stop words: common words to ignore (they add no signal) ───
# We add tech-specific ones ON TOP of sklearn's built-in stop list.
EXTRA_STOP_WORDS = [
    "required", "preferred", "experience", "strong", "good",
    "knowledge", "ability", "work", "team", "using", "including",
    "etc", "must", "well", "like", "ensure", "opportunity"
]


def _preprocess(text: str) -> str:
    """
    Normalize text before vectorizing:
      1. Lowercase everything
      2. Keep only letters, numbers, and spaces
      3. Collapse multiple spaces
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()   # Collapse whitespace
    return text


def compute_tfidf_similarity(resume_text: str, job_text: str) -> float:
    """
    Core matching function.
    Steps:
      1. Preprocess both texts
      2. Build a TF-IDF matrix (2 documents → 2 rows of numbers)
      3. Compute cosine similarity between the two rows
      4. Return as 0–100 float
    """
    clean_resume = _preprocess(resume_text)
    clean_job    = _preprocess(job_text)

    # TfidfVectorizer converts text → numeric vectors
    # stop_words removes common English words + our custom ones
    # ngram_range=(1,2) considers single words AND 2-word phrases (e.g. "machine learning")
    # max_features caps vocabulary size to avoid memory issues
    vectorizer = TfidfVectorizer(
        stop_words="english",           # Built-in English stop words
        ngram_range=(1, 2),             # Unigrams + bigrams
        max_features=5000,              # Limit vocabulary
        sublinear_tf=True               # Log-scale TF to reduce impact of very common words
    )

    # fit_transform builds the vocabulary from BOTH docs and converts them
    # tfidf_matrix has shape (2, vocab_size)
    try:
        tfidf_matrix = vectorizer.fit_transform([clean_resume, clean_job])
    except ValueError:
        # Edge case: empty text after preprocessing
        return 0.0

    # cosine_similarity returns a 2×2 matrix:
    #   [[resume vs resume, resume vs job],
    #    [job vs resume,    job vs job   ]]
    # We want [0][1] — resume vs job
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    # Convert to percentage and round to 1 decimal
    return round(float(similarity) * 100, 1)


def extract_jd_keywords(job_description: str) -> List[str]:
    """
    Pulls all skill keywords mentioned in the job description.
    We reuse SKILL_TAXONOMY so we only look for real tech skills.
    """
    jd_lower = job_description.lower()
    found = []

    for canonical_name, aliases in SKILL_TAXONOMY.items():
        for alias in aliases:
            try:
                if re.search(alias, jd_lower):
                    found.append(canonical_name)
                    break  # Found this skill — no need to check other aliases
            except re.error:
                pass

    return list(set(found))  # deduplicate


def match_job(resume_text: str, job_description: str) -> JobMatchResult:
    """
    Full matching pipeline:
      1. TF-IDF similarity score
      2. Extract skills from JD
      3. Check which JD skills are in resume (matched) vs missing
      4. Generate a recommendation string
    """
    # Step 1: Compute similarity score
    score = compute_tfidf_similarity(resume_text, job_description)

    # Step 2: What skills does the JD require?
    jd_skills = extract_jd_keywords(job_description)

    # Step 3: What skills does the resume have?
    resume_lower = resume_text.lower()
    resume_skills_present = set()

    for canonical_name, aliases in SKILL_TAXONOMY.items():
        for alias in aliases:
            try:
                if re.search(alias, resume_lower):
                    resume_skills_present.add(canonical_name)
                    break
            except re.error:
                pass

    # Skills the JD wants AND the resume has
    matched_skills = [s for s in jd_skills if s in resume_skills_present]

    # Skills the JD wants but the resume LACKS (= skill gaps)
    missing_skills = [s for s in jd_skills if s not in resume_skills_present]

    # Step 4: Human-readable recommendation
    recommendation = _generate_recommendation(score, len(matched_skills), len(missing_skills))

    return JobMatchResult(
        match_score=score,
        matched_skills=sorted(matched_skills),
        missing_skills=sorted(missing_skills),
        recommendation=recommendation
    )


def _generate_recommendation(score: float, matched: int, missing: int) -> str:
    """Simple rule-based verdict based on the match score."""
    if score >= 75:
        return (
            f"🟢 Strong Match! Resume aligns well with the job description "
            f"({matched} skills matched). Recommended for interview."
        )
    elif score >= 50:
        return (
            f"🟡 Moderate Match. Candidate has {matched} relevant skills but "
            f"is missing {missing} skills from the JD. Consider for screening."
        )
    elif score >= 30:
        return (
            f"🟠 Weak Match. Only {matched} skills align. "
            f"Candidate would need upskilling in: {missing} areas."
        )
    else:
        return (
            f"🔴 Poor Match. The resume does not align well with this role. "
            f"Major skill gaps detected ({missing} missing skills)."
        )
