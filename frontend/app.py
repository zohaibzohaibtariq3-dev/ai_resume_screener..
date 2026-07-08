# frontend/app.py
# ─────────────────────────────────────────────────────────────
# Streamlit frontend for the AI Resume Screener.
# Run with: streamlit run frontend/app.py
#
# Pages / Sections:
#   1. Upload Resume → Extract text
#   2. Resume Analysis → Parsed data + skills
#   3. Job Match → Similarity score + skill gaps
#   4. Interview Questions → Generated Q&A bank
# ─────────────────────────────────────────────────────────────

import streamlit as st
import requests        # For calling our FastAPI backend
import json
from typing import Optional

# ── Backend URL ───────────────────────────────────────────────
# Change this to your deployed URL when going live
API_BASE = "http://localhost:8000/api/v1"

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🧠",
    layout="wide",       # Use full screen width
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────
# Makes the UI look cleaner than default Streamlit
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* Section card styling */
    .section-card {
        background: #f8f9fa;
        border-left: 4px solid #0f3460;
        padding: 1rem 1.5rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }

    /* Skill badge */
    .skill-expert   { background: #d4edda; color: #155724; padding: 4px 10px; border-radius: 20px; margin: 3px; display: inline-block; font-size: 13px; font-weight: 600; }
    .skill-inter    { background: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 20px; margin: 3px; display: inline-block; font-size: 13px; }
    .skill-beginner { background: #f8d7da; color: #721c24; padding: 4px 10px; border-radius: 20px; margin: 3px; display: inline-block; font-size: 13px; }

    /* Question card */
    .question-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Match score display */
    .score-display {
        text-align: center;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }

    /* Sidebar styling */
    .sidebar-info {
        font-size: 12px;
        color: #666;
        padding: 0.5rem;
        background: #f0f0f0;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# Streamlit re-runs the script on every interaction.
# session_state lets us PERSIST data across re-runs.
# ─────────────────────────────────────────────────────────────
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""        # Extracted PDF text

if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = None      # Parsed resume dict

if "match_result" not in st.session_state:
    st.session_state.match_result = None     # Job match result

if "questions" not in st.session_state:
    st.session_state.questions = None        # Generated questions

if "upload_done" not in st.session_state:
    st.session_state.upload_done = False


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────
def call_api(endpoint: str, method: str = "POST", **kwargs) -> Optional[dict]:
    """
    Generic API caller with error handling.
    Returns parsed JSON on success, None on failure.
    Displays error messages via st.error().
    """
    url = f"{API_BASE}/{endpoint}"
    try:
        if method == "POST":
            response = requests.post(url, timeout=30, **kwargs)
        else:
            response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            # Try to extract the detail message from FastAPI error responses
            try:
                error_detail = response.json().get("detail", response.text)
            except:
                error_detail = response.text
            st.error(f"❌ API Error {response.status_code}: {error_detail}")
            return None

    except requests.exceptions.ConnectionError:
        st.error(
            "🔌 Cannot connect to backend. "
            "Make sure the FastAPI server is running on port 8000.\n\n"
            "Run: `uvicorn main:app --reload` in the `backend/` directory."
        )
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The server took too long to respond.")
        return None


def score_color(score: float) -> str:
    """Returns a color based on the match score."""
    if score >= 75:   return "#28a745"   # Green
    elif score >= 50: return "#ffc107"   # Yellow
    elif score >= 30: return "#fd7e14"   # Orange
    else:             return "#dc3545"   # Red


def render_skill_badge(skill: dict) -> str:
    """Returns HTML for a colored skill badge."""
    level = skill.get("level", "Intermediate")
    name  = skill.get("name", "")
    conf  = skill.get("confidence", 0.0)
    css_class = {
        "Expert": "skill-expert",
        "Intermediate": "skill-inter",
        "Beginner": "skill-beginner"
    }.get(level, "skill-inter")
    return f'<span class="{css_class}">{name} ({level})</span>'


# ─────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧠 AI Resume Screener</h1>
    <p style="font-size: 1.1rem; opacity: 0.9;">
        Upload a resume → Get instant skill analysis, job matching, and interview questions
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SIDEBAR: Navigation + Status
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📋 Navigation")

    # Step indicators
    steps = [
        ("1️⃣ Upload Resume",      st.session_state.upload_done),
        ("2️⃣ View Analysis",      st.session_state.parsed_data is not None),
        ("3️⃣ Match Job",          st.session_state.match_result is not None),
        ("4️⃣ Get Questions",      st.session_state.questions is not None),
    ]

    for step_name, completed in steps:
        icon = "✅" if completed else "⏳"
        st.markdown(f"{icon} {step_name}")

    st.divider()

    # Quick status
    if st.session_state.resume_text:
        word_count = len(st.session_state.resume_text.split())
        st.markdown(f"""
        <div class="sidebar-info">
            📄 Resume loaded<br>
            📝 {word_count} words
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # API Health check
    if st.button("🔍 Check API Status"):
        result = call_api("health", method="GET")
        if result:
            st.success(f"✅ API Online — v{result.get('version', '?')}")

    st.divider()
    st.caption("Built with FastAPI + spaCy + scikit-learn + Streamlit")


# ─────────────────────────────────────────────────────────────
# TAB LAYOUT: 4 main sections
# ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 Upload Resume",
    "🔍 Analysis",
    "🎯 Job Match",
    "💬 Interview Prep"
])


# ═══════════════════════════════════════════════════════════════
# TAB 1: UPLOAD RESUME
# ═══════════════════════════════════════════════════════════════
with tab1:

    st.header("📤 Upload Your Resume")
    st.markdown("Upload a PDF resume to begin. The system will extract and analyze the content.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # File uploader widget
        # type=["pdf"] restricts to PDF files only
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload a resume in PDF format (max 10MB)"
        )

        if uploaded_file is not None:
            # Show file details
            file_size_kb = uploaded_file.size / 1024
            st.info(f"📎 **{uploaded_file.name}** — {file_size_kb:.1f} KB")

            if st.button("🚀 Extract Resume Text", type="primary", use_container_width=True):
                with st.spinner("📖 Extracting text from PDF..."):
                    # Send file to backend using multipart/form-data
                    result = call_api(
                        "upload_resume",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    )

                if result:
                    # Store the extracted text in session state
                    st.session_state.resume_text = result["full_text"]
                    st.session_state.upload_done = True

                    # Show success summary
                    
                    st.success("✅ Text extracted successfully!")

                    # Show metrics
                    m1, m2, m3 = st.columns(3)
                    m1.metric("📄 Pages",      result["page_count"])
                    m2.metric("📝 Words",       result["word_count"])
                    m3.metric("✅ Status",      "Ready")

                    # Preview
                    with st.expander("👁️ Preview extracted text"):
                        st.text(result["text_preview"] + "...")

    with col2:
        st.markdown("""
        ### ℹ️ How it works

        1. **Upload** your PDF resume
        2. **Extract** — text is pulled from all pages
        3. **Analyze** — skills, name, education detected
        4. **Match** — compare with a job description
        5. **Prepare** — get custom interview questions

        ---
        ### 📋 Supported Formats
        - Standard PDF resumes
        - Multi-page resumes
        - Text-based PDFs

        ---
        ### ⚠️ Limitations
        - Scanned/image PDFs won't work
        - Max file size: 10 MB
        """)


# ═══════════════════════════════════════════════════════════════
# TAB 2: RESUME ANALYSIS
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.header("🔍 Resume Analysis")

    if not st.session_state.resume_text:
        st.warning("⚠️ Please upload a resume in the **Upload Resume** tab first.")
    else:
        if st.button("🧠 Analyze Resume", type="primary") or st.session_state.parsed_data:
            if not st.session_state.parsed_data:
                with st.spinner("🔬 Parsing resume with NLP..."):
                    result = call_api(
                        "parse_resume",
                        data={"resume_text": st.session_state.resume_text}
                    )
                if result:
                    st.session_state.parsed_data = result

            data = st.session_state.parsed_data

            if data:
                # ── Personal Information ───────────────────────
                st.subheader("👤 Personal Information")
                pi_col1, pi_col2, pi_col3 = st.columns(3)
                pi_col1.markdown(f"**Name:** {data.get('name') or '—'}")
                pi_col2.markdown(f"**Email:** {data.get('email') or '—'}")
                pi_col3.markdown(f"**Phone:** {data.get('phone') or '—'}")

                st.divider()

                # ── Skills ─────────────────────────────────────
                st.subheader("⚡ Detected Skills")

                skills = data.get("skills", [])
                if skills:
                    # Group skills by level
                    experts       = [s for s in skills if s["level"] == "Expert"]
                    intermediates = [s for s in skills if s["level"] == "Intermediate"]
                    beginners     = [s for s in skills if s["level"] == "Beginner"]

                    sk1, sk2, sk3 = st.columns(3)
                    with sk1:
                        st.markdown(f"### 🏆 Expert ({len(experts)})")
                        for s in experts:
                            st.markdown(f"✅ **{s['name']}** `{s['confidence']*100:.0f}%`")

                    with sk2:
                        st.markdown(f"### 📈 Intermediate ({len(intermediates)})")
                        for s in intermediates:
                            st.markdown(f"🔵 {s['name']} `{s['confidence']*100:.0f}%`")

                    with sk3:
                        st.markdown(f"### 🌱 Beginner ({len(beginners)})")
                        for s in beginners:
                            st.markdown(f"🟡 {s['name']} `{s['confidence']*100:.0f}%`")
                else:
                    st.info("No skills detected. The resume may lack technical keywords.")

                st.divider()

                # ── Education ──────────────────────────────────
                ed_col, ex_col = st.columns(2)

                with ed_col:
                    st.subheader("🎓 Education")
                    education = data.get("education", [])
                    if education:
                        for item in education:
                            st.markdown(f"• {item}")
                    else:
                        st.info("Education section not clearly detected.")

                with ex_col:
                    st.subheader("💼 Experience")
                    experience = data.get("experience", [])
                    if experience:
                        for item in experience[:8]:  # Show max 8 lines
                            st.markdown(f"• {item}")
                    else:
                        st.info("Experience section not clearly detected.")

                # ── Raw text viewer ────────────────────────────
                with st.expander("📄 View Raw Resume Text"):
                    st.text_area(
                        "Extracted Text",
                        value=st.session_state.resume_text,
                        height=300,
                        disabled=True
                    )


# ═══════════════════════════════════════════════════════════════
# TAB 3: JOB MATCHING
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.header("🎯 Job Description Matching")

    if not st.session_state.resume_text:
        st.warning("⚠️ Please upload a resume first.")
    else:
        # Job description input
        job_description = st.text_area(
            "📋 Paste the Job Description here",
            height=250,
            placeholder=(
                "Example:\nWe are looking for a Senior Data Scientist with 5+ years of "
                "experience in Python, machine learning, and SQL. The candidate should "
                "have hands-on experience with TensorFlow or PyTorch, AWS deployment, "
                "and strong communication skills..."
            )
        )

        job_title = st.text_input(
            "💼 Job Title (optional)",
            placeholder="e.g., Senior Data Scientist, Backend Engineer, ML Engineer"
        )

        # Save job info in session for question generation
        if job_description:
            st.session_state["job_description"] = job_description
            st.session_state["job_title"]       = job_title

        if st.button("🎯 Calculate Match Score", type="primary", use_container_width=True):
            if not job_description.strip():
                st.error("Please paste a job description first.")
            else:
                with st.spinner("🔄 Calculating similarity..."):
                    result = call_api(
                        "match_job",
                        json={
                            "resume_text": st.session_state.resume_text,
                            "job_description": job_description
                        }
                    )

                if result:
                    st.session_state.match_result = result

        # Display match results
        if st.session_state.match_result:
            result = st.session_state.match_result
            score  = result["match_score"]
            color  = score_color(score)

            st.divider()

            # ── Big score display ───────────────────────────
            st.markdown(f"""
            <div class="score-display" style="background: linear-gradient(135deg, {color}22, {color}11); border: 2px solid {color};">
                <h1 style="color: {color}; font-size: 4rem; margin: 0;">{score}%</h1>
                <h3 style="color: {color}; margin: 0.5rem 0;">Match Score</h3>
            </div>
            """, unsafe_allow_html=True)

            # ── Recommendation ──────────────────────────────
            st.info(result["recommendation"])

            st.divider()

            # ── Skill Breakdown ─────────────────────────────
            mc1, mc2 = st.columns(2)

            with mc1:
                matched = result.get("matched_skills", [])
                st.subheader(f"✅ Matched Skills ({len(matched)})")
                if matched:
                    for skill in matched:
                        st.markdown(f"✅ **{skill}**")
                else:
                    st.info("No direct skill matches found.")

            with mc2:
                missing = result.get("missing_skills", [])
                st.subheader(f"⚠️ Skill Gaps ({len(missing)})")
                if missing:
                    for skill in missing:
                        st.markdown(f"❌ {skill}")
                    st.caption("These are skills mentioned in the JD but absent from the resume.")
                else:
                    st.success("No major skill gaps! Great match.")


# ═══════════════════════════════════════════════════════════════
# TAB 4: INTERVIEW QUESTIONS
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.header("💬 Interview Question Generator")

    if not st.session_state.resume_text:
        st.warning("⚠️ Please upload a resume first.")
    else:
        # Get job details from session (set in Tab 3) or let user enter here
        jd_for_questions = st.session_state.get("job_description", "")
        jt_for_questions = st.session_state.get("job_title", "")

        if not jd_for_questions:
            st.info("💡 Tip: Fill in the Job Description in the **Job Match** tab first for better questions.")
            jd_for_questions = st.text_area(
                "Job Description (for tailored questions)",
                height=150,
                placeholder="Paste job description for more relevant questions..."
            )
            jt_for_questions = st.text_input("Job Title", placeholder="e.g., Data Scientist")
        else:
            st.success(f"✅ Using job description from Job Match tab | Role: **{jt_for_questions or 'Not specified'}**")

        if st.button("💡 Generate Interview Questions", type="primary", use_container_width=True):
            with st.spinner("🤔 Generating tailored questions..."):
                result = call_api(
                    "generate_questions",
                    json={
                        "resume_text": st.session_state.resume_text,
                        "job_description": jd_for_questions or "Software Engineer role",
                        "job_title": jt_for_questions or "Software Engineer"
                    }
                )

            if result:
                st.session_state.questions = result

        # Display questions
        if st.session_state.questions:
            questions = st.session_state.questions
            total     = questions.get("total_count", 0)

            st.success(f"✅ Generated {total} interview questions across 3 categories")
            st.divider()

            # ── Technical Questions ─────────────────────────
            technical = questions.get("technical", [])
            if technical:
                st.subheader(f"⚙️ Technical Questions ({len(technical)})")
                st.caption("Skill-specific questions based on resume + job description")
                for i, q in enumerate(technical, 1):
                    with st.expander(f"Q{i}: {q['question'][:80]}..."):
                        st.markdown(f"**Question:** {q['question']}")
                        st.caption(f"🔍 Reason: {q['rationale']}")

            st.divider()

            # ── Behavioral Questions ────────────────────────
            behavioral = questions.get("behavioral", [])
            if behavioral:
                st.subheader(f"🧠 Behavioral Questions ({len(behavioral)})")
                st.caption("STAR-method questions to assess soft skills and past behavior")
                for i, q in enumerate(behavioral, 1):
                    with st.expander(f"Q{i}: {q['question'][:80]}..."):
                        st.markdown(f"**Question:** {q['question']}")
                        st.caption(f"🔍 Assesses: {q['rationale']}")

            st.divider()

            # ── Role-Based Questions ────────────────────────
            role_based = questions.get("role_based", [])
            if role_based:
                st.subheader(f"🎭 Role-Based Questions ({len(role_based)})")
                st.caption("Questions tailored to the specific job role")
                for i, q in enumerate(role_based, 1):
                    with st.expander(f"Q{i}: {q['question'][:80]}..."):
                        st.markdown(f"**Question:** {q['question']}")
                        st.caption(f"🔍 Context: {q['rationale']}")

            # ── Export ─────────────────────────────────────
            st.divider()
            if st.button("📥 Export Questions as JSON"):
                questions_json = json.dumps(questions, indent=2)
                st.download_button(
                    label="⬇️ Download questions.json",
                    data=questions_json,
                    file_name="interview_questions.json",
                    mime="application/json"
                )
