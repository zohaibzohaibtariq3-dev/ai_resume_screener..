# utils/skill_analyzer.py
# ─────────────────────────────────────────────────────────────
# Detects technical skills in resume text.
# Estimates skill level using frequency + context signals.
# ─────────────────────────────────────────────────────────────

import re
from typing import List, Dict
from models.schemas import SkillEntry

# ── Master skill taxonomy ─────────────────────────────────────
# Each entry: "canonical_name": [list of aliases/variations]
# We match ANY alias, but always return the canonical name.
# Organized by domain for readability.

SKILL_TAXONOMY: Dict[str, List[str]] = {

    # ── Programming Languages ──────────────────────────────────
    "Python":       ["python", "python3", "py"],
    "JavaScript":   ["javascript", "js", "es6", "es2015", "ecmascript"],
    "TypeScript":   ["typescript", "ts"],
    "Java":         ["java", "java8", "java11", "java17"],
    "C++":          ["c\\+\\+", "cpp", "c plus plus"],
    "C#":           ["c#", "csharp", "c sharp", "\\.net"],
    "Go":           ["golang", "\\bgo\\b"],
    "Rust":         ["rust", "rustlang"],
    "PHP":          ["php", "php7", "php8"],
    "Swift":        ["swift", "swiftui"],
    "Kotlin":       ["kotlin"],
    "R":            ["\\br\\b", "r language", "rstudio"],
    "Ruby":         ["ruby", "ruby on rails"],
    "Scala":        ["scala"],

    # ── Web Frameworks ─────────────────────────────────────────
    "React":        ["react", "reactjs", "react.js", "react native"],
    "Vue.js":       ["vue", "vuejs", "vue.js"],
    "Angular":      ["angular", "angularjs"],
    "Django":       ["django"],
    "FastAPI":      ["fastapi"],
    "Flask":        ["flask"],
    "Node.js":      ["node", "nodejs", "node.js", "express", "expressjs"],
    "Spring":       ["spring", "spring boot", "springboot"],
    "Laravel":      ["laravel"],
    "Next.js":      ["next.js", "nextjs"],

    # ── Machine Learning / AI ──────────────────────────────────
    "TensorFlow":   ["tensorflow", "tf"],
    "PyTorch":      ["pytorch", "torch"],
    "scikit-learn": ["scikit.learn", "sklearn", "scikit learn"],
    "Keras":        ["keras"],
    "NLP":          ["nlp", "natural language processing", "spacy", "nltk", "transformers"],
    "Computer Vision": ["computer vision", "cv", "opencv", "image processing"],
    "Deep Learning": ["deep learning", "neural network", "cnn", "rnn", "lstm", "transformer"],
    "LLMs":         ["llm", "large language model", "gpt", "bert", "llama", "fine.tuning"],
    "MLOps":        ["mlops", "ml pipeline", "model deployment", "kubeflow", "mlflow"],

    # ── Data & Analytics ──────────────────────────────────────
    "SQL":          ["sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql", "pl/sql"],
    "NoSQL":        ["nosql", "mongodb", "cassandra", "dynamodb", "redis", "firebase"],
    "Pandas":       ["pandas"],
    "NumPy":        ["numpy"],
    "Spark":        ["apache spark", "pyspark", "spark"],
    "Tableau":      ["tableau"],
    "Power BI":     ["power bi", "powerbi"],
    "Data Science": ["data science", "data analysis", "data analytics", "eda"],

    # ── Cloud & DevOps ────────────────────────────────────────
    "AWS":          ["aws", "amazon web services", "ec2", "s3", "lambda", "sagemaker"],
    "GCP":          ["gcp", "google cloud", "bigquery", "vertex ai"],
    "Azure":        ["azure", "microsoft azure"],
    "Docker":       ["docker", "dockerfile", "containerization"],
    "Kubernetes":   ["kubernetes", "k8s", "kubectl", "helm"],
    "CI/CD":        ["ci/cd", "jenkins", "github actions", "gitlab ci", "travis"],
    "Terraform":    ["terraform", "infrastructure as code", "iac"],
    "Linux":        ["linux", "ubuntu", "bash", "shell scripting", "unix"],

    # ── Databases ────────────────────────────────────────────
    "PostgreSQL":   ["postgresql", "postgres"],
    "MongoDB":      ["mongodb", "mongo"],
    "Redis":        ["redis"],
    "Elasticsearch":["elasticsearch", "elastic search"],

    # ── Tools & Methodologies ─────────────────────────────────
    "Git":          ["git", "github", "gitlab", "bitbucket", "version control"],
    "Agile":        ["agile", "scrum", "kanban", "sprint"],
    "REST API":     ["rest api", "restful", "api design", "openapi", "swagger"],
    "GraphQL":      ["graphql"],
    "Microservices":["microservices", "micro-services", "service mesh"],
}

# ── Level signals: words near a skill that hint at expertise ──
# We look at the CONTEXT around a skill mention.
EXPERT_SIGNALS = [
    "expert", "advanced", "senior", "lead", "architect",
    "years of experience", "yr exp", "proficient", "deep expertise",
    "specialized", "5+", "6+", "7+", "8+", "10+"
]

BEGINNER_SIGNALS = [
    "beginner", "learning", "basic", "familiar", "exposure",
    "coursework", "studying", "introductory", "some knowledge",
    "1 year", "6 months", "recently"
]


def _get_context(text: str, match_start: int, window: int = 120) -> str:
    """
    Grab the text AROUND a skill match (±120 chars).
    This is the "context window" used to determine skill level.
    """
    start = max(0, match_start - window)
    end   = min(len(text), match_start + window)
    return text[start:end].lower()


def estimate_level(skill_name: str, text: str, occurrences: int) -> tuple:
    """
    Returns (level_str, confidence_float) based on:
      1. How many times the skill appears (more = more experienced)
      2. Context signals around the skill mentions
    """
    text_lower = text.lower()

    # Find all positions where this skill appears
    positions = [m.start() for m in re.finditer(
        re.escape(skill_name.lower()), text_lower
    )]

    expert_score   = 0
    beginner_score = 0

    for pos in positions:
        ctx = _get_context(text, pos)
        expert_score   += sum(1 for sig in EXPERT_SIGNALS   if sig in ctx)
        beginner_score += sum(1 for sig in BEGINNER_SIGNALS if sig in ctx)

    # Frequency heuristic
    if occurrences >= 5:
        expert_score += 2
    elif occurrences >= 3:
        expert_score += 1
    elif occurrences == 1:
        beginner_score += 1

    # Decision logic
    if expert_score > beginner_score and expert_score >= 1:
        level      = "Expert"
        confidence = min(0.95, 0.6 + expert_score * 0.1)
    elif beginner_score > expert_score:
        level      = "Beginner"
        confidence = min(0.90, 0.5 + beginner_score * 0.1)
    else:
        level      = "Intermediate"
        confidence = 0.65

    return level, round(confidence, 2)


def detect_skills(text: str) -> List[SkillEntry]:
    """
    Main function: scans the full resume text against SKILL_TAXONOMY.
    Returns a list of SkillEntry objects, sorted by confidence (highest first).
    """
    text_lower = text.lower()
    found_skills: List[SkillEntry] = []
    seen_canonical = set()   # Avoid duplicate entries

    for canonical_name, aliases in SKILL_TAXONOMY.items():
        if canonical_name in seen_canonical:
            continue

        total_occurrences = 0

        # Check each alias for this skill
        for alias in aliases:
            try:
                # re.findall counts ALL occurrences of this alias
                matches = re.findall(alias, text_lower)
                total_occurrences += len(matches)
            except re.error:
                # Some aliases have special regex chars — skip if broken
                pass

        # If we found the skill at least once, analyze it
        if total_occurrences > 0:
            level, confidence = estimate_level(canonical_name, text, total_occurrences)
            found_skills.append(SkillEntry(
                name=canonical_name,
                level=level,
                confidence=confidence
            ))
            seen_canonical.add(canonical_name)

    # Sort by confidence descending — most confident detections first
    return sorted(found_skills, key=lambda s: s.confidence, reverse=True)
