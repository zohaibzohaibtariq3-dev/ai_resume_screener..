# utils/question_generator.py
# ─────────────────────────────────────────────────────────────
# Generates interview questions based on:
#   - Skills detected in the resume
#   - Skills mentioned in the job description
#   - Job title context
#
# We use a rich template bank + intelligent selection.
# Each question comes with a rationale explaining WHY it was generated.
# ─────────────────────────────────────────────────────────────

import re
import random
from typing import List, Dict
from models.schemas import InterviewQuestion, QuestionBank
from utils.skill_analyzer import detect_skills, SKILL_TAXONOMY


# ── Technical question templates per skill ────────────────────
# {skill} is replaced with the actual skill name at runtime.
# These are thoughtfully written to be useful in real interviews.

TECHNICAL_TEMPLATES: Dict[str, List[str]] = {
    "Python": [
        "Explain the difference between a list and a tuple in Python, and when would you use each?",
        "What are Python decorators and how have you used them in production code?",
        "How does Python's GIL affect multi-threaded applications, and how do you work around it?",
        "Explain list comprehensions vs generator expressions — when do you prefer one over the other?",
        "How would you profile and optimize a slow Python script?",
    ],
    "Machine Learning": [
        "Walk me through how you would approach a new classification problem from raw data to deployment.",
        "Explain the bias-variance tradeoff and how it influences your model selection.",
        "How do you handle class imbalance in a binary classification dataset?",
        "What cross-validation strategy do you use and why?",
        "Describe a time you debugged an underperforming ML model — what was your process?",
    ],
    "Deep Learning": [
        "Explain vanishing gradients — how does it occur and what techniques address it?",
        "When would you use a CNN vs an RNN vs a Transformer for a sequence problem?",
        "How do you decide the number of layers and neurons in a neural network?",
        "What is batch normalization and why does it help training?",
        "Explain dropout regularization and when you'd apply it.",
    ],
    "SQL": [
        "Write a query to find the second highest salary from an employees table.",
        "Explain the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN.",
        "What is a window function? Give an example use case.",
        "How would you optimize a slow SQL query? Walk me through your process.",
        "Explain the difference between WHERE and HAVING clauses.",
    ],
    "React": [
        "Explain the Virtual DOM — how does React's reconciliation algorithm work?",
        "What are React hooks? Explain useState and useEffect with examples.",
        "How do you manage global state in a large React application?",
        "Explain the difference between controlled and uncontrolled components.",
        "How do you optimize performance in a React app with large lists?",
    ],
    "AWS": [
        "Explain the difference between EC2, Lambda, and ECS — when would you use each?",
        "How would you design a highly available, fault-tolerant application on AWS?",
        "What is IAM and how do you follow least-privilege principles?",
        "How does S3 handle storage classes and lifecycle policies?",
        "Explain how you would set up a CI/CD pipeline on AWS.",
    ],
    "Docker": [
        "Explain the difference between a Docker image and a container.",
        "What is a multi-stage Docker build and why is it useful?",
        "How do you handle secrets and environment variables in Docker containers?",
        "Explain Docker networking — bridge, host, and overlay networks.",
        "How would you debug a Docker container that fails to start?",
    ],
    "NLP": [
        "Explain the difference between stemming and lemmatization with examples.",
        "How does TF-IDF work and when would you prefer it over word embeddings?",
        "What is attention mechanism in transformers — explain it intuitively.",
        "How would you approach a named entity recognition task from scratch?",
        "Explain fine-tuning a pre-trained language model for a specific domain.",
    ],
    "Git": [
        "Explain git rebase vs git merge — when would you choose rebase?",
        "How do you handle a merge conflict? Walk me through the process.",
        "What branching strategy does your team use and why?",
        "How would you recover commits from an accidental git reset --hard?",
        "Explain the difference between git fetch and git pull.",
    ],
    "default": [
        "Describe your most technically challenging project — what was your role?",
        "How do you stay updated with the latest developments in {skill}?",
        "Explain a complex concept in {skill} to someone with no technical background.",
        "What tools or practices do you use to write maintainable {skill} code?",
        "Describe a bug you found and fixed in a {skill} codebase — how did you debug it?",
    ]
}

# ── Behavioral questions (universal) ─────────────────────────
BEHAVIORAL_QUESTIONS = [
    {
        "q": "Tell me about a time you had to meet a tight deadline. How did you prioritize?",
        "r": "Tests time management and pressure handling"
    },
    {
        "q": "Describe a situation where you disagreed with your team's technical decision. What did you do?",
        "r": "Tests conflict resolution and professional communication"
    },
    {
        "q": "Give me an example of a project that failed. What did you learn from it?",
        "r": "Tests self-awareness and growth mindset"
    },
    {
        "q": "Tell me about a time you had to learn a new technology quickly. How did you approach it?",
        "r": "Tests adaptability and learning ability"
    },
    {
        "q": "Describe a time you mentored or helped a junior team member. What was the outcome?",
        "r": "Tests leadership and communication skills"
    },
    {
        "q": "Tell me about the most complex system you've designed or contributed to.",
        "r": "Tests system design thinking and experience depth"
    },
    {
        "q": "How do you handle feedback on your code during a code review?",
        "r": "Tests professionalism and collaborative development habits"
    },
    {
        "q": "Describe a time you proactively identified and fixed a problem before it became critical.",
        "r": "Tests initiative and ownership mindset"
    },
]

# ── Role-based question templates ────────────────────────────
ROLE_BASED_TEMPLATES: Dict[str, List[str]] = {
    "data scientist": [
        "How do you communicate model results to non-technical stakeholders?",
        "Walk me through your end-to-end ML project workflow.",
        "How do you validate that a deployed model is still performing well over time?",
        "Describe your approach to feature engineering for a tabular dataset.",
    ],
    "software engineer": [
        "How do you approach designing a new feature from scratch?",
        "What's your code review process and what do you look for?",
        "How do you ensure your code is testable and maintainable?",
        "Describe your approach to debugging a production issue.",
    ],
    "backend engineer": [
        "How would you design a REST API for a high-traffic e-commerce platform?",
        "Explain your approach to database schema design and migrations.",
        "How do you handle authentication and authorization in your APIs?",
        "What strategies do you use for horizontal scaling of backend services?",
    ],
    "frontend engineer": [
        "How do you approach performance optimization for a slow web page?",
        "Explain your strategy for making a UI accessible (WCAG compliance).",
        "How do you handle responsive design across different screen sizes?",
        "What's your testing strategy for frontend components?",
    ],
    "devops engineer": [
        "How would you design a zero-downtime deployment pipeline?",
        "Describe your approach to infrastructure monitoring and alerting.",
        "How do you handle secrets management across multiple environments?",
        "Explain your disaster recovery strategy for a critical service.",
    ],
    "ml engineer": [
        "How do you version control ML models and datasets?",
        "Describe your approach to serving a model in production at scale.",
        "How do you monitor model drift and trigger retraining?",
        "Explain the differences between batch inference and real-time inference — when do you use each?",
    ],
    "default": [
        "What does a typical workday look like in your current/previous role?",
        "How do you prioritize when you have multiple competing deadlines?",
        "Where do you see yourself professionally in 3 years?",
        "What are you looking for in your next role that your current role doesn't offer?",
    ]
}


def _detect_role(job_description: str, job_title: str) -> str:
    """Match the job title/description to one of our role templates."""
    combined = (job_title + " " + job_description).lower()
    for role_key in ROLE_BASED_TEMPLATES:
        if role_key in combined:
            return role_key
    return "default"


def generate_questions(
    resume_text: str,
    job_description: str,
    job_title: str = "Software Engineer"
) -> QuestionBank:
    """
    Main question generation pipeline.
    Steps:
      1. Detect skills in the resume
      2. Detect skills in the JD (to find skill gaps)
      3. Generate technical questions for TOP skills
      4. Pick behavioral questions randomly
      5. Generate role-based questions
    """

    # Step 1: Detect resume skills
    detected_skills = detect_skills(resume_text)
    top_skill_names = [s.name for s in detected_skills[:6]]  # Top 6 by confidence

    # Step 2: Detect JD skills (for gap-based questions)
    jd_skills = []
    jd_lower = job_description.lower()
    for canonical, aliases in SKILL_TAXONOMY.items():
        for alias in aliases:
            try:
                if re.search(alias, jd_lower):
                    jd_skills.append(canonical)
                    break
            except re.error:
                pass

    # Combine: resume skills + JD skills (deduplicated)
    all_relevant_skills = list(dict.fromkeys(top_skill_names + jd_skills))[:8]

    # Step 3: Generate TECHNICAL questions
    technical_questions: List[InterviewQuestion] = []
    for skill in all_relevant_skills:
        templates = TECHNICAL_TEMPLATES.get(skill, TECHNICAL_TEMPLATES["default"])
        # Pick 1 random question per skill to keep the bank diverse
        chosen = random.choice(templates)
        # Replace {skill} placeholder in default templates
        chosen = chosen.replace("{skill}", skill)
        technical_questions.append(InterviewQuestion(
            category="Technical",
            question=chosen,
            rationale=f"'{skill}' was detected in the resume/JD"
        ))

    # Step 4: Pick BEHAVIORAL questions (pick 4 random ones)
    selected_behavioral = random.sample(BEHAVIORAL_QUESTIONS, min(4, len(BEHAVIORAL_QUESTIONS)))
    behavioral_questions = [
        InterviewQuestion(
            category="Behavioral",
            question=item["q"],
            rationale=item["r"]
        )
        for item in selected_behavioral
    ]

    # Step 5: Role-based questions
    role = _detect_role(job_description, job_title)
    role_templates = ROLE_BASED_TEMPLATES.get(role, ROLE_BASED_TEMPLATES["default"])
    role_questions = [
        InterviewQuestion(
            category="Role-Based",
            question=q,
            rationale=f"Tailored for {job_title} role"
        )
        for q in role_templates[:3]   # Pick up to 3 role questions
    ]

    total = len(technical_questions) + len(behavioral_questions) + len(role_questions)

    return QuestionBank(
        technical=technical_questions,
        behavioral=behavioral_questions,
        role_based=role_questions,
        total_count=total
    )
