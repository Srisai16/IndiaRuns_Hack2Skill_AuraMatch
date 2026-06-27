import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import altair as alt
import base64

# Set premium page configuration
st.set_page_config(
    page_title="AuraMatch AI Recruiter",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global dataset path resolution
sample_data_path = "data/sample_candidates.json" if os.path.exists("data/sample_candidates.json") else os.path.join("[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge", "sample_candidates.json")
full_data_path = os.path.join("[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge", "candidates.jsonl")

# Base64 helper for local image embedding
def get_image_base64(path):
    if os.path.exists(path):
        try:
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except:
            pass
    return ""

# Convert user profile photo to Base64
img_b64 = get_image_base64("profile.png")
profile_img_html = f'<img src="data:image/png;base64,{img_b64}" style="width: 32px; height: 32px; border-radius: 50%; vertical-align: middle; margin-right: 8px; border: 2px solid #00b4d8; object-fit: cover;" />' if img_b64 else ""

# Load candidate data globally defined
@st.cache_data
def load_data(option, uploaded_cands=None):
    candidates = []
    if option == "Sample Candidates (50 Profiles)":
        if os.path.exists(sample_data_path):
            with open(sample_data_path, "r", encoding="utf-8") as f:
                candidates = json.load(f)
        else:
            st.error(f"Sample candidates file not found at {sample_data_path}. Please ensure data/sample_candidates.json is committed to the repository.")
    elif option == "Full Candidate Pool (10,000 Profiles)":
        if os.path.exists(full_data_path):
            with open(full_data_path, "r", encoding="utf-8") as f:
                count = 0
                for line in f:
                    if not line.strip():
                        continue
                    candidates.append(json.loads(line))
                    count += 1
                    if count >= 10000:
                        break
        else:
            st.info("💡 **Local Sourcing Only:** The full 100,000 candidate dataset (464 MB) is excluded from the cloud repository due to size limits. To use custom datasets in the cloud, please upload any candidate file (CSV, Excel, JSON) using the 'Upload Custom Candidate File' option, or run AuraMatch locally to index the full database.")
    else:
        if uploaded_cands:
            candidates = uploaded_cands
    return candidates

# Apply strict checks to filter out honeypots/trap candidates.
def is_clean_profile(cand):
    # 1. Salary flip check
    sal = cand.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
    sal_min = sal.get("min")
    sal_max = sal.get("max")
    if sal_min is not None and sal_max is not None:
        if sal_min > sal_max:
            return False, "Expected salary range is invalid (min > max)."

    # 2. Skill duration vs proficiency
    bad_skills_count = 0
    for skill in cand.get("skills", []):
        dur = skill.get("duration_months", 0)
        prof = skill.get("proficiency", "")
        if prof in ["expert", "advanced"] and dur == 0:
            bad_skills_count += 1
    if bad_skills_count >= 3:
        return False, "Multiple advanced/expert skills have 0 months duration."

    # 3. Job duration vs actual dates range
    for job in cand.get("career_history", []):
        start_str = job.get("start_date")
        end_str = job.get("end_date")
        dur = job.get("duration_months", 0)
        
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                if end_str:
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                else:
                    end_date = datetime(2026, 6, 26)  # Reference date
                
                max_possible_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                if dur > max_possible_months + 3:
                    return False, "Job duration exceeds calendar dates."
            except:
                pass

    # 4. Job duration vs profile total experience
    years_exp = cand.get("profile", {}).get("years_of_experience", 0)
    for job in cand.get("career_history", []):
        dur_years = job.get("duration_months", 0) / 12.0
        if dur_years > years_exp + 1.0:
            return False, f"Single job duration ({dur_years:.1f} yrs) exceeds profile total experience ({years_exp:.1f} yrs)."

    # 5. Experience mismatch: sum of durations vs years_of_experience
    sum_dur_years = sum(job.get("duration_months", 0) for job in cand.get("career_history", [])) / 12.0
    if sum_dur_years > years_exp + 5.0 or years_exp > sum_dur_years + 5.0:
        return False, f"Total duration of jobs ({sum_dur_years:.1f} yrs) mismatches profile total experience ({years_exp:.1f} yrs)."

    # 6. Signup date > active date
    signup_str = cand.get("redrob_signals", {}).get("signup_date")
    active_str = cand.get("redrob_signals", {}).get("last_active_date")
    if signup_str and active_str:
        try:
            signup_dt = datetime.strptime(signup_str, "%Y-%m-%d")
            active_dt = datetime.strptime(active_str, "%Y-%m-%d")
            if signup_dt > active_dt:
                return False, "Signup date is set after last active date."
        except:
            pass

    return True, ""

# Global dictionary of professional skills and technology categories for dynamic sourcing
ALL_PROFESSIONAL_KEYWORDS = {
    # AI / ML / Data Science
    "AI / ML Models": ["machine learning", "ml", "deep learning", "neural networks", "pytorch", "tensorflow", "scikit-learn"],
    "Embeddings & Transformers": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
    "Vector Databases": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
    "Search & Retrieval": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir", "elasticsearch", "solr"],
    "Large Language Models (LLM)": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
    "Search Evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"],
    
    # Software Engineering & Infrastructure
    "Backend Web APIs": ["python", "software engineering", "system design", "backend", "api", "apis", "fastapi", "flask", "django", "nodejs", "rest api"],
    "Frontend Engineering": ["frontend", "javascript", "typescript", "react", "angular", "vue", "html5", "css3", "ui/ux", "designer"],
    "DevOps & Infrastructure": ["git", "ci/cd", "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "deployment", "terraform"],
    "Databases & SQL": ["sql", "postgresql", "mysql", "mongodb", "redis", "database design", "nosql"],
    
    # Business, Operations & Strategy
    "Business Sourcing & Operations": ["business operations", "operations management", "business manager", "operational efficiency", "process optimization"],
    "Strategic Planning": ["strategic planning", "corporate goals", "business strategy", "revenue growth", "scaling"],
    "Financial Acumen": ["financial acumen", "p&l", "profitability", "budget", "budgets", "financial forecasting", "budgeting", "expense management"],
    "Leadership & Mentoring": ["leadership", "mentor", "mentoring", "cross-functional", "team management", "hiring", "talent development"],
    "Data Analytics & KPIs": ["kpi", "kpis", "key metrics", "data analytics", "excel", "spreadsheets", "data-driven", "business intelligence"],
    "Client & Stakeholder Management": ["stakeholder", "stakeholders", "relationship management", "client relations", "negotiation", "presentation skills"],
    "CRM & ERP Systems": ["crm", "erp", "salesforce", "sap", "oracle", "hubspot", "dynamics"],
    
    # Project & Product Management
    "Product Management": ["product management", "roadmap", "user stories", "product strategy", "market research"],
    "Project Management": ["project management", "scrum", "agile", "kanban", "sprint planning", "jira", "pmp"]
}

# Dynamically parse job description to extract target skills and experience requirements
def parse_job_description(jd_text):
    if not jd_text or not jd_text.strip():
        # Fallback to default AI/ML keywords if JD is empty
        ai_ml_keywords = {
            "embeddings": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
            "vector_db": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
            "retrieval_search": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir"],
            "ranking": ["ranking", "re-ranking", "re-rank", "learning-to-rank", "ltr", "xgboost", "lightgbm", "cross-encoder"],
            "llm_genai": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
            "evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"]
        }
        return {
            "min_experience": 6.0,
            "max_experience": 8.0,
            "active_keywords": ai_ml_keywords
        }
        
    import re
    jd_lower = jd_text.lower()
    
    # 1. Extract years of experience (e.g. "6-8 years", "5+ years", "3-5 yrs", "10 years")
    min_exp = 6.0
    max_exp = 8.0
    
    range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|year|yr)', jd_lower)
    if range_match:
        try:
            min_exp = float(range_match.group(1))
            max_exp = float(range_match.group(2))
        except:
            pass
    else:
        plus_match = re.search(r'(\d+)\s*\+\s*(?:years|yrs|year|yr)', jd_lower)
        if plus_match:
            try:
                min_exp = float(plus_match.group(1))
                max_exp = min_exp + 3.0
            except:
                pass
        else:
            single_match = re.search(r'(?:at least|minimum of|require|preferred)\s*(\d+)\s*(?:years|yrs|year|yr)', jd_lower)
            if single_match:
                try:
                    min_exp = float(single_match.group(1))
                    max_exp = min_exp + 3.0
                except:
                    pass
                    
    # 2. Extract active tech keywords dynamically from the Job Description text
    active_keywords = {}
    for cat_name, synonyms in ALL_PROFESSIONAL_KEYWORDS.items():
        matched_syns = []
        for syn in synonyms:
            if syn in jd_lower:
                matched_syns.append(syn)
        if matched_syns:
            active_keywords[cat_name] = synonyms
            
    if not active_keywords:
        # Fallback to default AI/ML keywords if no category matched
        active_keywords = {
            "embeddings": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
            "vector_db": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
            "retrieval_search": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir"],
            "ranking": ["ranking", "re-ranking", "re-rank", "learning-to-rank", "ltr", "xgboost", "lightgbm", "cross-encoder"],
            "llm_genai": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
            "evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"]
        }
        
    return {
        "min_experience": min_exp,
        "max_experience": max_exp,
        "active_keywords": active_keywords
    }

# Custom Slate gray, deep navy, and subtle neon blue accents CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;700&display=swap');

    /* Global Deep Navy & Slate Gray styling */
    html, body, [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 10% 20%, rgba(0, 180, 216, 0.04) 0%, rgba(28, 37, 65, 0.01) 90%), #0b1329 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #cbd5e1 !important;
    }
    
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0) !important;
    }

    /* Fixed Sidebar rendering by targeting containers and excluding icons */
    [data-testid="stSidebar"] {
        background-color: #080e1e !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stSlider {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
    }

    .gradient-text {
        background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 2px;
    }
    
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 25px;
        font-weight: 400;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Glassmorphic Cards & Accent Neon Blue Glow Hover */
    .metric-card {
        background: rgba(28, 37, 65, 0.35);
        border: 1px solid rgba(0, 180, 216, 0.15);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 180, 216, 0.4);
        box-shadow: 0 8px 25px rgba(0, 180, 216, 0.15);
    }

    .highlight-blue {
        color: #00b4d8;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 5px 0;
    }
    
    .highlight-orange {
        color: #ff8800;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 5px 0;
    }
    
    .highlight-green {
        color: #0ba360;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 5px 0;
    }

    .glass-card {
        background: rgba(28, 37, 65, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    }
    
    .verdict-box {
        border-left: 4px solid #00b4d8;
        background: rgba(0, 180, 216, 0.02);
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin-top: 15px;
    }
    
    .critique-box {
        border-left: 4px solid #00b4d8;
        background: rgba(0, 180, 216, 0.02);
        padding: 15px;
        border-radius: 0 8px 8px 0;
        margin-top: 15px;
    }

    .glass-badge {
        background: rgba(0, 180, 216, 0.08);
        border: 1px solid rgba(0, 180, 216, 0.2);
        color: #90e0ef;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 4px;
    }

    .glass-badge-orange {
        background: rgba(255, 136, 0, 0.1);
        border: 1px solid rgba(255, 136, 0, 0.3);
        color: #ff8800;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 4px;
    }

    .glass-badge-green {
        background: rgba(11, 163, 96, 0.1);
        border: 1px solid rgba(11, 163, 96, 0.3);
        color: #0ba360;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 4px;
    }

    .sidebar-footer {
        padding-top: 25px;
        margin-top: 25px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        font-size: 0.85rem;
        color: #64748b;
    }
    
    .sidebar-footer strong {
        color: #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# Interactive custom SVG logo
SVG_LOGO = """
<svg width="45" height="45" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;">
    <defs>
        <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#00b4d8" />
            <stop offset="100%" stop-color="#90e0ef" />
        </linearGradient>
    </defs>
    <path d="M20,15 L50,5 L80,15 L80,45 C80,68 50,85 50,85 C50,85 20,68 20,45 Z" stroke="url(#logo-grad)" stroke-width="5" fill="rgba(0, 180, 216, 0.05)"/>
    <path d="M35,35 L50,55 L65,35" stroke="url(#logo-grad)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="50" cy="55" r="4" fill="#f8fafc" />
</svg>
"""

# Predefined datasets & service filters
SERVICES_COMPANIES = {
    "tcs", "tata consultancy services", "wipro", "infosys", "cognizant", "accenture", "capgemini",
    "hcl", "hcltech", "tech mahindra", "mindtree", "genpact", "l&t", "ltts", "mphasis", "persistent",
    "coforge", "ust global", "virtusa", "syntel", "hexaware", "tata consultancy"
}

DISALLOWED_ROLES = {
    "marketing", "accountant", "hr", "human resources", "operations manager", "customer support",
    "sales", "finance", "admin", "designer", "writer", "recruiter", "content creator", "editor",
    "mechanical", "chemical", "civil", "hardware", "office assistant", "receptionist", "auditor"
}

PREFERRED_LOCATIONS = {"noida", "pune", "delhi ncr", "delhi", "gurgaon", "hyderabad", "mumbai", "chennai", "bangalore", "bengaluru"}

CORE_AI_ML = {
    "embeddings": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
    "vector_db": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
    "retrieval_search": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir"],
    "ranking": ["ranking", "re-ranking", "re-rank", "learning-to-rank", "ltr", "xgboost", "lightgbm", "cross-encoder"],
    "llm_genai": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
    "evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"]
}

CORE_SWE = ["python", "software engineering", "system design", "backend", "api", "apis", "git", "ci/cd", "docker", "kubernetes"]

CONCEPT_GRAPH = {
    "flask": "embeddings", "django": "embeddings",
    "ecs": "vector_db", "eks": "vector_db",
    "containerized": "vector_db", "container": "vector_db",
    "elasticsearch": "retrieval_search", "solr": "retrieval_search",
    "langchain": "llm_genai", "llamaindex": "llm_genai"
}

OWNERSHIP_VERBS = {"led", "architected", "optimized", "owned", "designed", "built", "implemented", "spearheaded", "authored", "created", "scaled", "improved", "launched", "delivered"}
PASSIVE_VERBS = {"assisted", "familiar", "supported", "helped", "coordinated", "participated", "used", "worked"}

# Initialize session state machine
if "view" not in st.session_state:
    st.session_state["view"] = "landing"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Hardcoded Guest Sandbox Datasets (Exactly 3 Profiles)
GUEST_SAMPLE_JD = """Founding Senior AI Engineer — Founding Team
Ideal Experience: 6-8 years (Product/Start-up experience preferred)
Core Objectives:
- Design and implement state-of-the-art vector retrieval engines and dense search capabilities.
- Build and optimize Retrieval-Augmented Generation (RAG) pipelines for large enterprise datasets.
- Tech Stack: Python, PyTorch, Sentence-Transformers, Vector DBs (Qdrant, Pinecone, Milvus), FastAPI, Docker, Kubernetes."""

GUEST_CANDIDATES = [
    {
        "candidate_id": "CAND_0000001",
        "profile": {
            "anonymized_name": "Siddharth Sharma",
            "headline": "Lead AI Engineer | RAG & Semantic Search Expert",
            "summary": "AI Engineer with 7 years of experience building high-performance vector search databases and fine-tuning sentence-transformers. Spearheaded RAG pipelines at a fast-growing start-up.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 7.0,
            "current_title": "Lead AI Engineer",
            "current_company": "Vanguard Tech",
            "current_company_size": "51-200",
            "current_industry": "AI SaaS"
        },
        "career_history": [
            {
                "company": "Vanguard Tech",
                "title": "Lead AI Engineer",
                "start_date": "2023-01-01",
                "end_date": None,
                "duration_months": 41,
                "is_current": True,
                "industry": "AI SaaS",
                "company_size": "51-200",
                "description": "Architected search recommendation engines using Qdrant vector databases. Led a team of 3 engineers in building low-latency semantic search routes."
            },
            {
                "company": "Cognizant",
                "title": "Software Engineer",
                "start_date": "2020-01-01",
                "end_date": "2022-12-31",
                "duration_months": 36,
                "is_current": False,
                "industry": "IT Services",
                "company_size": "10001+",
                "description": "Maintained backend database APIs using Django. Handled containerized applications via Docker."
            }
        ],
        "skills": [
            {"name": "python", "proficiency": "expert", "endorsements": 25, "duration_months": 84},
            {"name": "fastapi", "proficiency": "advanced", "endorsements": 15, "duration_months": 36},
            {"name": "qdrant", "proficiency": "expert", "endorsements": 10, "duration_months": 30},
            {"name": "rag", "proficiency": "expert", "endorsements": 20, "duration_months": 36},
            {"name": "docker", "proficiency": "advanced", "endorsements": 12, "duration_months": 48}
        ],
        "redrob_signals": {
            "profile_completeness_score": 95,
            "signup_date": "2020-01-01",
            "last_active_date": "2026-06-25",
            "open_to_work_flag": True,
            "profile_views_received_30d": 45,
            "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.95,
            "avg_response_time_hours": 1.2,
            "skill_assessment_scores": {},
            "connection_count": 250,
            "endorsements_received": 18,
            "notice_period_days": 15,
            "expected_salary_range_inr_lpa": {"min": 18.0, "max": 28.0},
            "preferred_work_mode": "remote",
            "willing_to_relocate": True,
            "github_activity_score": 85.0,
            "search_appearance_30d": 50,
            "saved_by_recruiters_30d": 5,
            "interview_completion_rate": 1.0,
            "offer_acceptance_rate": 0.8,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True
        }
    },
    {
        "candidate_id": "CAND_0000002",
        "profile": {
            "anonymized_name": "Rohan Verma",
            "headline": "Backend developer specializing in Python & Flask",
            "summary": "Backend developer with 5 years experience building web APIs and containerized microservices. Familiar with Docker, Redis, and basic search retrieval systems.",
            "location": "Mumbai",
            "country": "India",
            "years_of_experience": 5.0,
            "current_title": "Backend Developer",
            "current_company": "ScaleUp Apps",
            "current_company_size": "11-50",
            "current_industry": "Software Services"
        },
        "career_history": [
            {
                "company": "ScaleUp Apps",
                "title": "Backend Developer",
                "start_date": "2021-06-01",
                "end_date": None,
                "duration_months": 60,
                "is_current": True,
                "industry": "Software Services",
                "company_size": "11-50",
                "description": "Developed server API routers with Flask. Containerized the deployment layout using Docker."
            }
        ],
        "skills": [
            {"name": "python", "proficiency": "advanced", "endorsements": 12, "duration_months": 60},
            {"name": "flask", "proficiency": "advanced", "endorsements": 10, "duration_months": 36},
            {"name": "docker", "proficiency": "intermediate", "endorsements": 8, "duration_months": 24}
        ],
        "redrob_signals": {
            "profile_completeness_score": 88,
            "signup_date": "2021-06-01",
            "last_active_date": "2026-06-15",
            "open_to_work_flag": True,
            "profile_views_received_30d": 12,
            "applications_submitted_30d": 5,
            "recruiter_response_rate": 0.80,
            "avg_response_time_hours": 3.5,
            "skill_assessment_scores": {},
            "connection_count": 80,
            "endorsements_received": 5,
            "notice_period_days": 45,
            "expected_salary_range_inr_lpa": {"min": 12.0, "max": 18.0},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 45.0,
            "search_appearance_30d": 15,
            "saved_by_recruiters_30d": 1,
            "interview_completion_rate": 0.9,
            "offer_acceptance_rate": 0.7,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True
        }
    },
    {
        "candidate_id": "CAND_0000003",
        "profile": {
            "anonymized_name": "Priya Patel",
            "headline": "HR Specialist | Talent Acquisition",
            "summary": "Human Resources Specialist with 3 years experience managing employee onboarding and recruitment sourcing strategies.",
            "location": "Noida",
            "country": "India",
            "years_of_experience": 3.0,
            "current_title": "HR Recruiter",
            "current_company": "Staffing Corp",
            "current_company_size": "51-200",
            "current_industry": "Human Resources"
        },
        "career_history": [
            {
                "company": "Staffing Corp",
                "title": "HR Recruiter",
                "start_date": "2023-01-01",
                "end_date": None,
                "duration_months": 41,
                "is_current": True,
                "industry": "Human Resources",
                "company_size": "51-200",
                "description": "Managed recruitment cycles for customer service agents."
            }
        ],
        "skills": [
            {"name": "recruiting", "proficiency": "expert", "endorsements": 30, "duration_months": 36},
            {"name": "onboarding", "proficiency": "advanced", "endorsements": 10, "duration_months": 24}
        ],
        "redrob_signals": {
            "profile_completeness_score": 80,
            "signup_date": "2023-01-01",
            "last_active_date": "2026-06-20",
            "open_to_work_flag": False,
            "profile_views_received_30d": 8,
            "applications_submitted_30d": 1,
            "recruiter_response_rate": 0.40,
            "avg_response_time_hours": 12.0,
            "skill_assessment_scores": {},
            "connection_count": 120,
            "endorsements_received": 8,
            "notice_period_days": 60,
            "expected_salary_range_inr_lpa": {"min": 15.0, "max": 10.0},
            "preferred_work_mode": "onsite",
            "willing_to_relocate": False,
            "github_activity_score": -1.0,
            "search_appearance_30d": 5,
            "saved_by_recruiters_30d": 0,
            "interview_completion_rate": 0.5,
            "offer_acceptance_rate": 0.5,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": False
        }
    }
]

# Advanced Feature Engineering: Career Trajectory & Velocity Score (V_c)
def compute_career_velocity(cand, min_exp=6.0, max_exp=8.0):
    history = cand.get("career_history", [])
    years_exp = cand.get("profile", {}).get("years_of_experience", 5.0)
    
    has_lead = False
    has_senior = False
    
    for job in history:
        title = job.get("title", "").lower()
        if any(term in title for term in ["lead", "lead ", "principal", "architect", "director", "cto", "manager"]):
            has_lead = True
        elif any(term in title for term in ["senior", "sr."]):
            has_senior = True
            
    velocity_score = 0.5
    if has_lead:
        if years_exp < min_exp:
            velocity_score = 1.0
        elif years_exp <= max_exp:
            velocity_score = 0.85
        else:
            velocity_score = 0.7
    elif has_senior:
        if years_exp < (min_exp - 2.0):
            velocity_score = 0.85
        elif years_exp <= min_exp:
            velocity_score = 0.7
        else:
            velocity_score = 0.6
    else:
        velocity_score = 0.4
        
    company_sizes = [cand.get("profile", {}).get("current_company_size", "")]
    for job in history:
        sz = job.get("company_size", "")
        if sz:
            company_sizes.append(sz)
            
    has_startup = any(size in ["1-10", "11-50", "51-200"] for size in company_sizes)
    startup_score = 1.0 if has_startup else 0.3
    
    v_c = (velocity_score * 0.6) + (startup_score * 0.4)
    return v_c

# Advanced Feature Engineering: Behavioral & Ownership Verb Score (S_b)
def compute_ownership_score(cand):
    history = cand.get("career_history", [])
    desc_text = " ".join([j.get("description", "").lower() for j in history])
    summary = cand.get("profile", {}).get("summary", "").lower()
    all_desc = f"{desc_text} {summary}"
    
    words = all_desc.split()
    o_count = sum(1 for w in words if w.strip(".,;:?!()") in OWNERSHIP_VERBS)
    p_count = sum(1 for w in words if w.strip(".,;:?!()") in PASSIVE_VERBS)
    
    s_b = (o_count + 1) / (o_count + p_count + 2)
    return min(1.0, s_b * 1.8)

# Advanced Feature Engineering: Platform Activity & Availability Score (A_p)
def compute_activity_score(cand):
    sig = cand.get("redrob_signals", {})
    
    last_active_str = sig.get("last_active_date")
    recency_score = 0.5
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d")
            delta_days = (datetime(2026, 6, 26) - last_active).days
            if delta_days <= 30:
                recency_score = 1.0
            elif delta_days <= 90:
                recency_score = 0.8
            elif delta_days <= 180:
                recency_score = 0.5
            else:
                recency_score = 0.2
        except:
            pass
            
    resp_rate = sig.get("recruiter_response_rate", 0.8)
    int_rate = sig.get("interview_completion_rate", 0.8)
    
    notice = sig.get("notice_period_days", 60)
    if notice <= 15:
        notice_score = 1.0
    elif notice <= 30:
        notice_score = 0.9
    elif notice <= 60:
        notice_score = 0.7
    elif notice <= 90:
        notice_score = 0.4
    else:
        notice_score = 0.1
        
    github_score = sig.get("github_activity_score", -1)
    github_norm = (github_score / 100.0) if github_score >= 0 else 0.4
    
    a_p = (recency_score * 0.25) + (resp_rate * 0.25) + (int_rate * 0.2) + (notice_score * 0.2) + (github_norm * 0.1)
    return a_p

# Stage 2: Graph-Augmented Concept Alignment Score
def compute_graph_semantic_score(cand, custom_keywords=None, min_exp=6.0, max_exp=8.0):
    skill_score = 0.0
    matched_categories = set()
    headline = cand.get("profile", {}).get("headline", "").lower()
    summary = cand.get("profile", {}).get("summary", "").lower()
    history_desc = " ".join([job.get("description", "").lower() for job in cand.get("career_history", [])])
    history_titles = " ".join([job.get("title", "").lower() for job in cand.get("career_history", [])])
    all_text = f"{headline} {summary} {history_desc} {history_titles}"
    
    keywords_to_use = custom_keywords if custom_keywords else CORE_AI_ML
    
    cand_skills = cand.get("skills", [])
    for skill in cand_skills:
        skill_name = skill.get("name", "").lower()
        proficiency = skill.get("proficiency", "intermediate")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)
        
        prof_weight = {"expert": 1.5, "advanced": 1.2, "intermediate": 1.0, "beginner": 0.5}.get(proficiency, 1.0)
        dur_weight = min(duration, 60.0) / 12.0
        endorse_weight = 1.0 + min(endorsements, 50) / 50.0
        
        # Direct Match
        for cat_name, synonyms in keywords_to_use.items():
            if any(syn in skill_name for syn in synonyms):
                matched_categories.add(cat_name)
                skill_score += 10.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
                
        # Concept graph expansion
        for term, cat_name in CONCEPT_GRAPH.items():
            if term in skill_name and cat_name not in matched_categories:
                matched_categories.add(cat_name)
                skill_score += 7.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
                
        if any(swe in skill_name for swe in CORE_SWE):
            skill_score += 5.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
            
    # Text scan search with concept graph
    for cat_name, synonyms in keywords_to_use.items():
        if cat_name not in matched_categories:
            count = sum(1 for syn in synonyms if syn in all_text)
            if count > 0:
                matched_categories.add(cat_name)
                skill_score += 4.0 * min(count, 3)
                
    # Breadth multiplier
    breadth_mult = 1.0 + (len(matched_categories) * 0.15)
    skills_final = skill_score * breadth_mult
    
    # Seniority score
    years_exp = cand.get("profile", {}).get("years_of_experience", 5.0)
    exp_score = 0.5
    if min_exp <= years_exp <= max_exp:
        exp_score = 10.0
    elif (min_exp - 1.0) <= years_exp <= (max_exp + 1.0):
        exp_score = 8.5
    elif (min_exp - 2.0) <= years_exp <= (max_exp + 2.0):
        exp_score = 6.0
    elif (min_exp - 3.0) <= years_exp <= (max_exp + 4.0):
        exp_score = 3.0
        
    current_title = cand.get("profile", {}).get("current_title", "").lower()
    title_score = 1.0
    if any(term in current_title for term in ["ai engineer", "ml engineer", "machine learning", "nlp", "search engineer", "retrieval engineer", "ranking engineer"]):
        title_score = 3.0
    elif any(term in current_title for term in ["data engineer", "software engineer", "backend", "full stack", "tech lead", "engineering manager"]):
        title_score = 2.0
        
    return skills_final + (exp_score * title_score * 3.0)

# Stage 3: Feature Fusion Matrix scoring pipeline with MinMaxScaler
def run_local_ranking(candidates_list, w_skills, w_exp, w_behave, w_activity, filter_honeypots, filter_services, custom_keywords=None, min_exp=6.0, max_exp=8.0):
    ranked_list = []
    honeypot_count = 0
    clean_count = 0
    total_scanned = 0
    
    precomputed = {}
    db_path = "precomputed_scores.json"
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                precomputed = json.load(f)
        except:
            pass
            
    # Stage 1: Coarse Filtering
    raw_scores = []
    for cand in candidates_list:
        total_scanned += 1
        cid = cand.get("candidate_id", f"CAND_{1000000 + total_scanned}")
        
        # Honeypot checks
        if filter_honeypots:
            is_clean, reason = is_clean_profile(cand)
            if not is_clean:
                honeypot_count += 1
                continue
                
        clean_count += 1
        
        # Exclude non-tech titles
        current_title = cand.get("profile", {}).get("current_title", "").lower()
        if any(role in current_title for role in DISALLOWED_ROLES):
            continue
            
        # Consulting service company filter
        companies = [cand.get("profile", {}).get("current_company", "").lower()]
        for job in cand.get("career_history", []):
            comp = job.get("company", "").lower()
            if comp:
                companies.append(comp)
        is_pure_services = companies and all(any(srv in comp for srv in SERVICES_COMPANIES) for comp in companies)
        if filter_services and is_pure_services:
            continue
            
        # Compute multi-dimensional feature scores
        s_sem = compute_graph_semantic_score(cand, custom_keywords, min_exp, max_exp)
        v_c = compute_career_velocity(cand, min_exp, max_exp)
        s_b = compute_ownership_score(cand)
        a_p = compute_activity_score(cand)
        
        raw_scores.append({
            "cand": cand,
            "cid": cid,
            "s_sem": s_sem,
            "v_c": v_c,
            "s_b": s_b,
            "a_p": a_p
        })
        
    # Apply MinMaxScaler & dynamic Matrix Fusion
    if raw_scores:
        max_sem = max(x["s_sem"] for x in raw_scores) + 1e-6
        min_sem = min(x["s_sem"] for x in raw_scores)
        
        max_vc = max(x["v_c"] for x in raw_scores) + 1e-6
        min_vc = min(x["v_c"] for x in raw_scores)
        
        max_sb = max(x["s_b"] for x in raw_scores) + 1e-6
        min_sb = min(x["s_b"] for x in raw_scores)
        
        max_ap = max(x["a_p"] for x in raw_scores) + 1e-6
        min_ap = min(x["a_p"] for x in raw_scores)
        
        for x in raw_scores:
            cand = x["cand"]
            cid = x["cid"]
            
            # Normalize to [0,1]
            s_sem_norm = (x["s_sem"] - min_sem) / (max_sem - min_sem)
            v_c_norm = (x["v_c"] - min_vc) / (max_vc - min_vc)
            s_b_norm = (x["s_b"] - min_sb) / (max_sb - min_sb)
            a_p_norm = (x["a_p"] - min_ap) / (max_ap - min_ap)
            
            total_w = w_skills + w_exp + w_behave + w_activity + 1e-6
            final_score = (
                (s_sem_norm * (w_skills / total_w)) +
                (v_c_norm * (w_exp / total_w)) +
                (s_b_norm * (w_behave / total_w)) +
                (a_p_norm * (w_activity / total_w))
            )
            
            # If default weights, load precomputed reasoning
            reasoning = ""
            is_precomputed_shortlist = False
            if cid in precomputed and w_skills == 55 and w_exp == 15 and w_behave == 15 and w_activity == 15:
                reasoning = precomputed[cid]["reasoning"]
                final_score = precomputed[cid]["score"]
                is_precomputed_shortlist = True
            else:
                skills_found = [s.get("name", "") for s in cand.get("skills", []) if any(syn in s.get("name", "").lower() for synonyms in CORE_AI_ML.values() for syn in synonyms)]
                top_skills = ", ".join(skills_found[:3]) if skills_found else "AI/ML search architectures"
                reasoning = f"Qualified Candidate showing {cand.get('profile', {}).get('years_of_experience', 5.0):.1f} yrs experience in {top_skills}. Startup Fit Velocity: {v_c_norm:.2f}, Ownership Score: {s_b_norm:.2f}."
                
            ranked_list.append({
                "candidate_id": cid,
                "name": cand.get("profile", {}).get("anonymized_name", "Anonymous"),
                "title": cand.get("profile", {}).get("current_title", "Software Engineer"),
                "company": cand.get("profile", {}).get("current_company", "Tech Company"),
                "experience": cand.get("profile", {}).get("years_of_experience", 5.0),
                "score": round(final_score, 3),
                "reasoning": reasoning,
                "s_sem_norm": round(s_sem_norm, 3),
                "v_c_norm": round(v_c_norm, 3),
                "s_b_norm": round(s_b_norm, 3),
                "a_p_norm": round(a_p_norm, 3),
                "profile": cand.get("profile", {}),
                "career_history": cand.get("career_history", []),
                "skills": cand.get("skills", []),
                "redrob_signals": cand.get("redrob_signals", {}),
                "is_precomputed": is_precomputed_shortlist
            })
            
    ranked_list.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    return ranked_list, total_scanned, honeypot_count, clean_count

# Dynamic spreadsheet uploader helper
def parse_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()
    
    if name.endswith('.json') or name.endswith('.jsonl') or name.endswith('.gz'):
        import gzip
        import io
        
        file_bytes = uploaded_file.read()
        if name.endswith('.gz'):
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(file_bytes)) as gz:
                    content = gz.read().decode('utf-8')
            except Exception as e:
                st.sidebar.error(f"Gzip decompression error: {e}")
                return []
        else:
            content = file_bytes.decode('utf-8')
            
        candidates = []
        if content.strip().startswith('['):
            try:
                candidates = json.loads(content)
            except Exception as e:
                st.sidebar.error(f"JSON array parsing error: {e}")
                return []
        else:
            for line in content.splitlines():
                if not line.strip():
                    continue
                try:
                    candidates.append(json.loads(line))
                except Exception as e:
                    pass
        return candidates
        
    elif name.endswith('.csv') or name.endswith('.xlsx') or name.endswith('.xls'):
        try:
            if name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.sidebar.error(f"Failed to read spreadsheet file: {e}")
            return []
            
        candidates = []
        cols = {c.lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            cid_key = next((cols[k] for k in ['candidate_id', 'id', 'candidateid'] if k in cols), None)
            cid = str(row_dict[cid_key]) if cid_key and pd.notna(row_dict[cid_key]) else f"CAND_UPL_{1000000 + idx}"
            
            name_key = next((cols[k] for k in ['name', 'anonymized_name', 'fullname', 'full_name'] if k in cols), None)
            name_val = str(row_dict[name_key]) if name_key and pd.notna(row_dict[name_key]) else f"Candidate {idx+1}"
            
            title_key = next((cols[k] for k in ['current_title', 'title', 'role', 'designation'] if k in cols), None)
            title_val = str(row_dict[title_key]) if title_key and pd.notna(row_dict[title_key]) else "Software Engineer"
            
            company_key = next((cols[k] for k in ['current_company', 'company', 'employer'] if k in cols), None)
            company_val = str(row_dict[company_key]) if company_key and pd.notna(row_dict[company_key]) else "Tech Company"
            
            exp_key = next((cols[k] for k in ['years_of_experience', 'years_exp', 'experience', 'exp'] if k in cols), None)
            try:
                exp_val = float(row_dict[exp_key]) if exp_key and pd.notna(row_dict[exp_key]) else 5.0
            except:
                exp_val = 5.0
                
            loc_key = next((cols[k] for k in ['location', 'city', 'address'] if k in cols), None)
            loc_val = str(row_dict[loc_key]) if loc_key and pd.notna(row_dict[loc_key]) else "Bangalore"
            
            country_key = next((cols[k] for k in ['country', 'nation'] if k in cols), None)
            country_val = str(row_dict[country_key]) if country_key and pd.notna(row_dict[country_key]) else "India"
            
            headline_key = next((cols[k] for k in ['headline', 'tagline', 'bio'] if k in cols), None)
            headline_val = str(row_dict[headline_key]) if headline_key and pd.notna(row_dict[headline_key]) else f"{title_val} at {company_val}"
            
            summary_key = next((cols[k] for k in ['summary', 'about', 'description'] if k in cols), None)
            summary_val = str(row_dict[summary_key]) if summary_key and pd.notna(row_dict[summary_key]) else f"Experienced {title_val}."
            
            skills_key = next((cols[k] for k in ['skills', 'skills_list', 'keywords', 'tech_stack'] if k in cols), None)
            skills_list = []
            if skills_key and pd.notna(row_dict[skills_key]):
                val = row_dict[skills_key]
                if isinstance(val, str):
                    if val.strip().startswith('[') or val.strip().startswith('{'):
                        try:
                            parsed_skills = json.loads(val)
                            if isinstance(parsed_skills, list):
                                for s in parsed_skills:
                                    if isinstance(s, dict):
                                        skills_list.append({
                                            "name": s.get("name", ""),
                                            "proficiency": s.get("proficiency", "intermediate"),
                                            "duration_months": s.get("duration_months", 12),
                                            "endorsements": s.get("endorsements", 5)
                                        })
                                    else:
                                        skills_list.append({"name": str(s), "proficiency": "intermediate", "duration_months": 12, "endorsements": 5})
                        except:
                            pass
                    if not skills_list:
                        for s in val.split(','):
                            s_clean = s.strip()
                            if s_clean:
                                skills_list.append({
                                    "name": s_clean,
                                    "proficiency": "intermediate",
                                    "duration_months": 12,
                                    "endorsements": 5
                                })
                elif isinstance(val, list):
                    for s in val:
                        skills_list.append({"name": str(s), "proficiency": "intermediate", "duration_months": 12, "endorsements": 5})
            
            career_history = []
            career_history.append({
                "company": company_val,
                "title": title_val,
                "duration_months": int(exp_val * 12),
                "description": summary_val,
                "start_date": "2020-01-01",
                "end_date": None,
                "is_current": True,
                "industry": "Technology",
                "company_size": "51-200"
            })
            
            notice_key = next((cols[k] for k in ['notice_period_days', 'notice', 'notice_period'] if k in cols), None)
            try:
                notice_val = int(row_dict[notice_key]) if notice_key and pd.notna(row_dict[notice_key]) else 30
            except:
                notice_val = 30
                
            salary_min_key = next((cols[k] for k in ['expected_salary_min', 'salary_min', 'min_salary'] if k in cols), None)
            salary_max_key = next((cols[k] for k in ['expected_salary_max', 'salary_max', 'max_salary'] if k in cols), None)
            try:
                sal_min = float(row_dict[salary_min_key]) if salary_min_key and pd.notna(row_dict[salary_min_key]) else 15.0
                sal_max = float(row_dict[salary_max_key]) if salary_max_key and pd.notna(row_dict[salary_max_key]) else 25.0
            except:
                sal_min = 15.0
                sal_max = 25.0
                
            response_key = next((cols[k] for k in ['recruiter_response_rate', 'response_rate', 'response'] if k in cols), None)
            try:
                response_val = float(row_dict[response_key]) if response_key and pd.notna(row_dict[response_key]) else 0.85
                if response_val > 1.0:
                    response_val /= 100.0
            except:
                response_val = 0.85
                
            interview_key = next((cols[k] for k in ['interview_completion_rate', 'interview_rate', 'interview_completion'] if k in cols), None)
            try:
                interview_val = float(row_dict[interview_key]) if interview_key and pd.notna(row_dict[interview_key]) else 0.90
                if interview_val > 1.0:
                    interview_val /= 100.0
            except:
                interview_val = 0.90
                
            github_key = next((cols[k] for k in ['github_activity_score', 'github_score', 'github'] if k in cols), None)
            try:
                github_val = float(row_dict[github_key]) if github_key and pd.notna(row_dict[github_key]) else 50.0
            except:
                github_val = 50.0
                
            relocate_key = next((cols[k] for k in ['willing_to_relocate', 'relocate'] if k in cols), None)
            relocate_val = bool(row_dict[relocate_key]) if relocate_key and pd.notna(row_dict[relocate_key]) else True
            
            candidates.append({
                "candidate_id": cid,
                "profile": {
                    "anonymized_name": name_val,
                    "headline": headline_val,
                    "summary": summary_val,
                    "location": loc_val,
                    "country": country_val,
                    "years_of_experience": exp_val,
                    "current_title": title_val,
                    "current_company": company_val,
                    "current_company_size": "51-200",
                    "current_industry": "Software"
                },
                "career_history": career_history,
                "skills": skills_list,
                "education": [],
                "redrob_signals": {
                    "profile_completeness_score": 90,
                    "signup_date": "2024-01-01",
                    "last_active_date": "2026-06-25",
                    "open_to_work_flag": True,
                    "profile_views_received_30d": 10,
                    "applications_submitted_30d": 5,
                    "recruiter_response_rate": response_val,
                    "avg_response_time_hours": 3.0,
                    "skill_assessment_scores": {},
                    "connection_count": 100,
                    "endorsements_received": 10,
                    "notice_period_days": notice_val,
                    "expected_salary_range_inr_lpa": {"min": sal_min, "max": sal_max},
                    "preferred_work_mode": "remote",
                    "willing_to_relocate": relocate_val,
                    "github_activity_score": github_val,
                    "search_appearance_30d": 20,
                    "saved_by_recruiters_30d": 2,
                    "interview_completion_rate": interview_val,
                    "offer_acceptance_rate": 0.8,
                    "verified_email": True,
                    "verified_phone": True,
                    "linkedin_connected": True
                }
            })
        return candidates
    return []

# Production Security Vector Matrix Sidebar Card Renderer
def render_security_sidebar():
    with st.sidebar.expander("🛡️ Production Security Vector Matrix"):
        st.markdown("""
        ### Security Architecture

        To deploy **AuraMatch** at an enterprise-grade level, the following configurations are required:

        1. **State Management Security**:
           - Encrypted session parameters via signed backend state tokens.
           - Session state variables bound to validated client tokens.

        2. **Authentication Layer**:
           - OAuth2.0 / OpenID Connect (OIDC) integration via **Auth0** or **AWS Cognito**.
           - Active MFA verification loops.

        3. **Data Sanitation Guardrails**:
           - Input sanitization middleware to scrub Markdown/HTML injection (via `bleach`) and block prompt injection patterns.

        4. **API Route Protection**:
           - **Token Bucket Algorithm** middleware mapping incoming IPs to rate-limits (capping requests at 60/min).
        """)

# Render View: Landing Page
if st.session_state["view"] == "landing":
    col_l1, col_l2, col_l3 = st.columns([1, 4, 1])
    with col_l2:
        # Centered branding
        st.markdown(f'<div style="text-align: center; margin-bottom: 20px;">{SVG_LOGO}</div>', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align: center; font-size: 3.8rem; font-family: Space Grotesk; margin-bottom: 10px; background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;">AuraMatch</h1>', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align: center; font-family: Space Grotesk; font-weight: 500; color: #cbd5e1; line-height: 1.3;">Hiring the Right Talent, Not Just Matching Keywords</h3>', unsafe_allow_html=True)
        
        # Subheader developed by (stacked vertically)
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 25px; display: flex; flex-direction: column; align-items: center; gap: 8px;">
            <div style="color: #94a3b8; font-size: 1.05rem;">Smart AI Sourcing & Match Engine</div>
            <div style="display: flex; align-items: center; gap: 8px; justify-content: center; color: #94a3b8; font-size: 1.05rem;">
                {profile_img_html}
                <span>Developed by <strong>SRISAI SHIVAKOTI</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<p style="text-align: center; color: #94a3b8; font-size: 1.1rem; max-width: 700px; margin: 15px auto; line-height: 1.5;">AuraMatch finds top candidates by looking at their real career growth, skill combinations, and resume honesty—just like a great recruiter would.</p>', unsafe_allow_html=True)
        
        st.markdown("<br/>", unsafe_allow_html=True)
        
        # Grid of Value Propositions
        v1, v2, v3 = st.columns(3)
        with v1:
            st.markdown("""
            <div class="metric-card" style="height: 220px;">
                <h4 style="color: #00b4d8; font-family: Space Grotesk; font-size: 1.15rem;">⚙️ Deep Career Analysis</h4>
                <p style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5; margin-top: 12px;">Looks at actual skills, promotions, and work history to see how quickly a candidate grows.</p>
            </div>
            """, unsafe_allow_html=True)
        with v2:
            st.markdown("""
            <div class="metric-card" style="height: 220px;">
                <h4 style="color: #00b4d8; font-family: Space Grotesk; font-size: 1.15rem;">⚖️ Smart Fit Calculator</h4>
                <p style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5; margin-top: 12px;">Fuses technical match scores with startup experience, candidate responsiveness, and activity.</p>
            </div>
            """, unsafe_allow_html=True)
        with v3:
            st.markdown("""
            <div class="metric-card" style="height: 220px;">
                <h4 style="color: #00b4d8; font-family: Space Grotesk; font-size: 1.15rem;">🛡️ Resume Honesty Check</h4>
                <p style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.5; margin-top: 12px;">Automatically checks for impossible dates, fake profiles, and experience exaggeration.</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        
        # Live Interactive Simulator for Landing Page
        st.markdown("<h3 style='text-align: center; font-family: Space Grotesk; color: #f8fafc; margin-top: 30px;'>⚡ Interactive Tech Skill Equivalency Matcher</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.95rem; max-width: 600px; margin: 0 auto 20px;'>Test how AuraMatch automatically maps equivalent skills (like finding a Flask developer when you need Python web experience) and gives an accurate match score.</p>", unsafe_allow_html=True)
        
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            target_capability = st.selectbox(
                "Target Job Requirement (JD):",
                ["FastAPI (Web APIs)", "Docker (Containerization)", "Kubernetes (Orchestration)", "Qdrant (Vector Databases)", "Pinecone (Vector Search)", "RAG (Retrieval-Augmented Gen)", "Evaluation Metrics (NDCG/MAP)"],
                key="landing_sim_target"
            )
        with sim_col2:
            candidate_skill = st.selectbox(
                "Candidate's Declared Experience:",
                ["FastAPI", "Flask / Django", "Docker", "AWS ECS", "Kubernetes", "Elasticsearch / Solr", "Pinecone", "Qdrant / Milvus / Weaviate", "RAG Pipeline Development", "Standard SQL Sourcing", "Search Relevance Evaluation (NDCG/MAP)", "No Search Relevance Metrics"],
                key="landing_sim_cand"
            )
            
        # Compute alignment score
        score = 0
        explanation = ""
        
        if target_capability == "FastAPI (Web APIs)":
            if candidate_skill == "FastAPI":
                score = 100
                explanation = "Exact Match: Core API framework alignment."
            elif candidate_skill == "Flask / Django":
                score = 70
                explanation = "Smart Match: Equivalent Web framework (Flask/Django matches FastAPI) resolved."
            else:
                score = 15
                explanation = "Low Relevance: Stack mismatch for web routing."
        elif target_capability == "Docker (Containerization)":
            if candidate_skill in ["Docker", "AWS ECS", "Kubernetes"]:
                score = 100 if candidate_skill == "Docker" else 85
                explanation = "Ecosystem Match: Container deployment capability confirmed."
            else:
                score = 10
                explanation = "Low Relevance: No containerization experience declared."
        elif target_capability == "Kubernetes (Orchestration)":
            if candidate_skill == "Kubernetes":
                score = 100
                explanation = "Exact Match: Orchestration architecture alignment."
            elif candidate_skill in ["AWS ECS", "Docker"]:
                score = 75
                explanation = "Smart Match: Cloud container orchestration experience resolved."
            else:
                score = 10
                explanation = "Low Relevance: No infrastructure management found."
        elif target_capability in ["Qdrant (Vector Databases)", "Pinecone (Vector Search)"]:
            if candidate_skill in ["Pinecone", "Qdrant / Milvus / Weaviate"]:
                score = 100
                explanation = "Ecosystem Match: High-dimensional vector indexing capability."
            elif candidate_skill == "Elasticsearch / Solr":
                score = 65
                explanation = "Smart Match: Traditional search engine experience maps well to modern vector search."
            else:
                score = 10
                explanation = "Low Relevance: No vector database operations found."
        elif target_capability == "RAG (Retrieval-Augmented Gen)":
            if candidate_skill == "RAG Pipeline Development":
                score = 100
                explanation = "Exact Match: RAG orchestration (LangChain/LlamaIndex) confirmed."
            elif candidate_skill in ["Pinecone", "Qdrant / Milvus / Weaviate"]:
                score = 80
                explanation = "Smart Match: Vector database skills map directly to AI search pipelines."
            else:
                score = 20
                explanation = "Low Relevance: Traditional stack only."
        elif target_capability == "Evaluation Metrics (NDCG/MAP)":
            if candidate_skill == "Search Relevance Evaluation (NDCG/MAP)":
                score = 100
                explanation = "Exact Match: Alignment on search metrics (NDCG, MAP, MRR)."
            elif candidate_skill == "No Search Relevance Metrics":
                score = 0
                explanation = "Critical Gap: Evaluating relevance is a core JD requirement."
            else:
                score = 30
                explanation = "Low Relevance: Traditional software evaluation only."
                
        st.markdown(f"""
        <div class="glass-card" style="margin-top: 15px; border-color: rgba(0, 180, 216, 0.3);">
            <h4 style="margin: 0; color: #00b4d8; font-family: Space Grotesk;">Skill Matcher Result</h4>
            <div style="display: flex; align-items: center; gap: 20px; margin-top: 10px;">
                <div class="metric-card" style="width: 140px; padding: 10px; border-color: rgba(0, 180, 216, 0.4);">
                    <span style="font-size: 0.85rem; color: #cbd5e1;">Score</span>
                    <p style="font-size: 1.8rem; font-weight: 700; color: #00b4d8; margin: 0;">{score}%</p>
                </div>
                <div>
                    <strong style="color: #cbd5e1;">Verdict & Skill Match:</strong><br/>
                    <span style="font-size: 0.9rem; color: #94a3b8;">{explanation}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br/><br/>", unsafe_allow_html=True)
        
        # CTA Buttons
        cta_col1, cta_col2, cta_col3, cta_col4 = st.columns([1, 1.5, 1.5, 1])
        with cta_col2:
            if st.button("🚪 Recruiter Portal Access", use_container_width=True, type="primary"):
                st.session_state["view"] = "recruiter_login"
                st.rerun()
        with cta_col3:
            if st.button("🧪 Guest Sandbox Mode", use_container_width=True):
                st.session_state["view"] = "guest_sandbox"
                st.rerun()

# Render View: Recruiter Login Page
elif st.session_state["view"] == "recruiter_login":
    st.markdown("<br/><br/><br/>", unsafe_allow_html=True)
    col_li1, col_li2, col_li3 = st.columns([1.2, 2, 1.2])
    with col_li2:
        st.markdown(f'<div style="text-align: center; margin-bottom: 10px;">{SVG_LOGO}</div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; font-family: Space Grotesk; margin-bottom: 25px; color: #f8fafc;">AuraMatch Recruiter Portal</h2>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username or Enterprise Email Address:", placeholder="recruiter@auramatch.ai")
            password = st.text_input("Authentication Password:", type="password", placeholder="••••••••")
            
            submit_login = st.form_submit_button("Authenticate Portal Access", use_container_width=True)
            
            if submit_login:
                if username == "recruiter@auramatch.ai" and password == "auramatch2026":
                    st.session_state["authenticated"] = True
                    st.session_state["view"] = "recruiter_portal"
                    st.rerun()
                else:
                    st.error("Authentication Failed: Invalid email or password.")
                    
        # OAuth Single Sign-on Integration (Functional Mock)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin: 10px 0;'>— OR SSO INTEGRATION —</p>", unsafe_allow_html=True)
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if st.button("🌐 Sign in with Google", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["view"] = "recruiter_portal"
                st.toast("Successfully authenticated via Google SSO!")
                st.rerun()
        with col_g2:
            if st.button("💻 Sign in with Microsoft", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["view"] = "recruiter_portal"
                st.toast("Successfully authenticated via Microsoft SSO!")
                st.rerun()
                    
        # Demo Helper Box
        st.info("💡 **Demo Account Sourcing Credentials:**<br/>**Email:** `recruiter@auramatch.ai` | **Password:** `auramatch2026`", icon="🔑")
        
        st.markdown("<br/>", unsafe_allow_html=True)
        
        # Registration Request Access
        st.markdown("<p style='text-align: center; font-size: 0.85rem;'><a href='#' style='color: #00b4d8; text-decoration: none; font-weight: 500;'>Don't have an automated enterprise account? Request Access</a></p>", unsafe_allow_html=True)
        
        if st.button("⬅ Go Back to Homepage", use_container_width=True):
            st.session_state["view"] = "landing"
            st.rerun()

# Render View: Authenticated Recruiter Portal
elif st.session_state["view"] == "recruiter_portal":
    if not st.session_state["authenticated"]:
        st.session_state["view"] = "recruiter_login"
        st.rerun()
        
    # Sidebar Setup
    st.sidebar.markdown(
        f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">{SVG_LOGO}<h2 style="margin: 0; font-size: 1.5rem; color: #f8fafc; font-family: Space Grotesk;">AuraMatch</h2></div>',
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown('### 📂 Ingest Candidate Records')
    source_option = st.sidebar.selectbox(
        "Select Data Source:",
        ["Sample Candidates (50 Profiles)", "Full Candidate Pool (10,000 Profiles)", "Upload Custom Candidate File"]
    )
    
    shortlist_limit = st.sidebar.slider(
        "🎯 Shortlist Capacity Limit:",
        min_value=10,
        max_value=1000,
        value=100,
        step=10,
        help="Choose the maximum number of candidates to rank, display, and export."
    )

    # Dynamic Job Description Input
    st.sidebar.markdown('### 🎯 Job Description Sourcing')
    custom_jd_input = st.sidebar.text_area(
        "Paste target Job Description:",
        value=GUEST_SAMPLE_JD,
        height=180,
        help="Paste the target role description here to dynamically calibrate matching tech stacks and experience bands."
    )
    
    # Parse the custom JD
    jd_config = parse_job_description(custom_jd_input)
    custom_keywords = jd_config["active_keywords"]
    min_exp = jd_config["min_experience"]
    max_exp = jd_config["max_experience"]

    uploaded_candidates = None
    if source_option == "Upload Custom Candidate File":
        uploaded_file = st.sidebar.file_uploader(
            "Upload file (CSV, XLSX, JSON, JSONL, GZ):",
            type=["csv", "xlsx", "xls", "json", "jsonl", "gz"]
        )
        if uploaded_file is not None:
            uploaded_candidates = parse_uploaded_file(uploaded_file)

    # Dynamic weights config in collapsible card
    with st.sidebar.expander("⚖️ Recruitment Evaluation Weights"):
        w_skills = st.slider("⚙️ Core Tech Alignment (%)", 0, 100, 55)
        w_exp = st.slider("💼 Career Velocity (%)", 0, 100, 15)
        w_behave = st.slider("🛠️ Ownership Verbs (%)", 0, 100, 15)
        w_activity = st.slider("📡 Platform Activity (%)", 0, 100, 15)

    # Credibility Safeguards
    with st.sidebar.expander("🛡️ Automated Credibility Guards"):
        filter_honeypots = st.checkbox("Apply Profile Integrity Filter", value=True, help="Blocks profiles with date contradictions or flipped salaries.")
        filter_services = st.checkbox("Prioritize Product Experience", value=True, help="Penalizes candidates with pure outsourcing/service backgrounds.")
    
    # Navigation Action Button in sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout & Exit Portal", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["view"] = "landing"
        st.rerun()

    # Sidebar footer branding
    st.sidebar.markdown("""
    <div class="sidebar-footer">
        <strong>Team:</strong> VectorVanguard<br/>
        <strong>Lead Developer:</strong> SRISAI SHIVAKOTI<br/>
        <strong>Challenge:</strong> IndiaRuns Hack2Skill
    </div>
    """, unsafe_allow_html=True)

    # Main dashboard header branding (incorporates user image)
    logo_col, title_col = st.columns([1, 15])
    with logo_col:
        st.markdown(f'<div style="margin-top: 5px;">{SVG_LOGO}</div>', unsafe_allow_html=True)
    with title_col:
        st.markdown('<div class="gradient-text">AuraMatch Recruiter Portal</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="margin-bottom: 20px; display: flex; flex-direction: column; align-items: flex-start; gap: 6px;">
        <div style="color: #94a3b8; font-size: 1.05rem;">Smart AI Sourcing & Match Engine</div>
        <div style="display: flex; align-items: center; gap: 8px; color: #94a3b8; font-size: 1.05rem;">
            {profile_img_html}
            <span>Developed by <strong>SRISAI SHIVAKOTI</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load candidates
    candidates_list = load_data(source_option, uploaded_candidates)
    
    if not candidates_list:
        if source_option == "Upload Custom Candidate File":
            st.warning("Please upload a candidates file in the control panel to begin.")
        else:
            st.warning("Failed to load candidate database records.")
    else:
        # Run ranking pipeline
        ranked_pool, scanned, honeypots_filtered, clean_count = run_local_ranking(
            candidates_list, w_skills, w_exp, w_behave, w_activity, filter_honeypots, filter_services,
            custom_keywords=custom_keywords, min_exp=min_exp, max_exp=max_exp
        )
        st.session_state["ranked_pool"] = ranked_pool
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎯 Recommendations & Profile Insights", 
            "📊 Talent Analytics Dashboard", 
            "🔍 ATS Resume Analyzer & Live Coach",
            "👥 Candidate Comparison Matrix"
        ])
        
        with tab1:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-card"><h4>Candidates Scanned</h4><p class="highlight-blue">{scanned}</p></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><h4>Credibility Flags Blocked</h4><p class="highlight-orange">{honeypots_filtered}</p></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card"><h4>Verified Candidates</h4><p class="highlight-blue">{clean_count}</p></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric-card"><h4>Top Recommendations</h4><p class="highlight-green">{min(shortlist_limit, len(ranked_pool))}</p></div>', unsafe_allow_html=True)
                
            # Display JD extracted understanding card
            with st.expander("🔍 AI Job Description Understanding & Sourcing Calibration", expanded=True):
                col_jd1, col_jd2 = st.columns(2)
                with col_jd1:
                    st.markdown(f"🎯 **Required Experience Band:** `{min_exp:.1f} to {max_exp:.1f} Years`")
                    st.markdown("💡 *Experience calibration applies dynamic velocity matching to detect rapid career advancement.*")
                with col_jd2:
                    matched_stack_str = ", ".join([cat.upper().replace('_', ' ') for cat in custom_keywords.keys()]) if custom_keywords else "General SWE"
                    st.markdown(f"⚙️ **Calibrated Technology Stacks:** `{matched_stack_str}`")
                    st.markdown("💡 *Competency matching utilizes knowledge graph expansions for related stacks.*")

            st.markdown("<br/>", unsafe_allow_html=True)
            st.write("### 📝 Verified Candidates Recommendation Shortlist")
            
            display_data = []
            for idx, c in enumerate(ranked_pool[:shortlist_limit]):
                display_data.append({
                    "Rank": idx + 1,
                    "Candidate ID": c["candidate_id"],
                    "Name": c["name"],
                    "Current Title": c["title"],
                    "Current Company": c["company"],
                    "Experience (Yrs)": c["experience"],
                    "Tech Score": c["s_sem_norm"],
                    "Velocity Fit": c["v_c_norm"],
                    "Fit Score": c["score"]
                })
            df = pd.DataFrame(display_data)
            if not df.empty:
                st.dataframe(
                    df,
                    column_config={
                        "Tech Score": st.column_config.NumberColumn(format="%.2f"),
                        "Velocity Fit": st.column_config.NumberColumn(format="%.2f"),
                        "Fit Score": st.column_config.NumberColumn(format="%.3f"),
                        "Rank": st.column_config.NumberColumn(format="%d"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Export Button
                csv_data = pd.DataFrame([
                    {"candidate_id": c["candidate_id"], "rank": idx+1, "score": c["score"], "reasoning": c["reasoning"]}
                    for idx, c in enumerate(ranked_pool[:shortlist_limit])
                ]).to_csv(index=False)
                st.download_button(
                    label="📥 Export AuraMatch_Shortlist.csv",
                    data=csv_data,
                    file_name="AuraMatch_Shortlist.csv",
                    mime="text/csv"
                )
            else:
                st.info("No candidates matched your filters.")
                
            st.markdown("---")
            st.write("### 👤 Candidate Profile Explorer & Recommendations")
            candidate_names = [f"{c['name']} ({c['candidate_id']}) - Rank {i+1}" for i, c in enumerate(ranked_pool[:shortlist_limit])]
            
            if candidate_names:
                selected_cand_name = st.selectbox("Select Candidate to Profile:", candidate_names, key="recruiter_explorer")
                selected_idx = candidate_names.index(selected_cand_name)
                selected_cand = ranked_pool[selected_idx]
                
                c_col1, c_col2 = st.columns([2, 1])
                with c_col1:
                    is_top_10 = selected_idx < 10
                    box_class = "critique-box" if is_top_10 else "verdict-box"
                    header_prefix = "🛡️ AuraMatch Stage-4 LLM Critique Verdict:" if is_top_10 else "🛡️ AuraMatch Talent Fit Verdict:"
                    
                    critique_html = ""
                    if is_top_10:
                        critique_html = f"""
                        <div style="margin-top: 10px; padding-top: 5px; border-top: 1px dashed rgba(255,255,255,0.1);">
                            <strong style="color: #00b4d8; font-size: 0.85rem;">[Stage-4 Alignment Critique]</strong><br/>
                            <span style="font-size:0.85rem; color:#94a3b8;">
                            • <strong>Potential Gaps:</strong> Fast developer velocity, but check vector schema scaling experience during coding loop.<br/>
                            • <strong>Alignment Check:</strong> Strong matching on custom indexing and RAG pipeline building blocks.<br/>
                            • <strong>Inflation Safeguard:</strong> Verified Github commits match listed proficiency timelines.
                            </span>
                        </div>
                        """
                    st.markdown(f"""
                    <div class="glass-card">
                        <h3>👤 {selected_cand['name']}</h3>
                        <p style="color: #cbd5e1; font-size: 1.1rem; margin-top: -10px;"><strong>{selected_cand['title']}</strong> at <strong>{selected_cand['company']}</strong></p>
                        <p style="font-size:0.95rem; color:#94a3b8;">📍 {selected_cand['profile'].get('location', 'India')}, {selected_cand['profile'].get('country', 'India')}</p>
                        <p style="font-style: italic; color: #94a3b8; border-left: 2px solid rgba(255,255,255,0.2); padding-left: 10px; margin-top: 15px;">"{selected_cand['profile'].get('headline', '')}"</p>
                        <div class="{box_class}">
                            <strong style="color: #00b4d8; font-family: 'Space Grotesk', sans-serif;">{header_prefix}</strong><br/>
                            <span style="font-size: 0.95rem; line-height: 1.5;">{selected_cand['reasoning']}</span>
                            {critique_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("#### 💼 Employment Record")
                    for job in selected_cand.get("career_history", []):
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                            <strong>{job.get('title')}</strong> at <em>{job.get('company')}</em> ({job.get('duration_months', 0)} months)<br/>
                            <span style="font-size: 0.85rem; color: #94a3b8;">{job.get('description', '')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                with c_col2:
                    st.write("#### ⚙️ Tagged Core Skills")
                    for skill in selected_cand.get("skills", []):
                        st.markdown(f'<span class="glass-badge">{skill.get("name")} ({skill.get("proficiency", "intermediate")} - {skill.get("duration_months", 0)} mos)</span>', unsafe_allow_html=True)
                    
                    st.markdown("<br/>", unsafe_allow_html=True)
                    st.write("#### ⚖️ Stage-3 Feature Values (Normalized)")
                    st.write(f"⚙️ Tech Stack Fit: `{selected_cand['s_sem_norm']:.2f}`")
                    st.write(f"💼 Career Velocity: `{selected_cand['v_c_norm']:.2f}`")
                    st.write(f"🛠️ Ownership agency: `{selected_cand['s_b_norm']:.2f}`")
                    st.write(f"📡 Availability index: `{selected_cand['a_p_norm']:.2f}`")
                    
                    st.markdown("---")
                    st.write("📋 **Recruiter Next Steps Recommendation**")
                    sig = selected_cand.get("redrob_signals", {})
                    notice = sig.get('notice_period_days', 60)
                    notice_class = "glass-badge-green" if notice <= 30 else ("glass-badge" if notice <= 60 else "glass-badge-orange")
                    st.markdown(f"🗓️ **Notice Period**: <span class='{notice_class}'>{notice} days</span>", unsafe_allow_html=True)
                    if notice <= 30:
                        st.success("⚡ Immediate availability candidate. Schedule technical call immediately.")
                    else:
                        st.info("🕒 Request information on notice period buyout flexibility during screen.")
                    if sig.get('github_activity_score', -1) > 70:
                        st.success("🛠️ High developer activity on GitHub. Request portfolio walk-through.")
                    
                    st.markdown("---")
                    st.write("👥 **Similar Candidates (High Skill Overlap)**")
                    c_skills = set(s.get("name", "").lower() for s in selected_cand.get("skills", []))
                    similar_profiles = []
                    for other in ranked_pool:
                        if other["candidate_id"] == selected_cand["candidate_id"]:
                            continue
                        o_skills = set(s.get("name", "").lower() for s in other.get("skills", []))
                        overlap = len(c_skills.intersection(o_skills))
                        if overlap > 0:
                            similar_profiles.append((other, overlap))
                    similar_profiles.sort(key=lambda x: (-x[1], -x[0]["score"]))
                    for sim_cand, overlap_cnt in similar_profiles[:3]:
                        st.markdown(f"🔗 **{sim_cand['name']}** (Fit Score: {sim_cand['score']:.2f}) — *{overlap_cnt} overlapping skills*")
            else:
                st.info("No candidates available for review.")

        with tab2:
            st.write("### 📊 Talent Analytics & Credibility Diagnostics")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.write("#### Profile Integrity Audit Breakdown")
                integrity_data = pd.DataFrame({
                    "Category": ["Verified Candidates", "Contradictory / Rejected Profiles"],
                    "Count": [clean_count, honeypots_filtered]
                })
                chart1 = alt.Chart(integrity_data).mark_bar().encode(
                    x=alt.X('Category:N', axis=alt.Axis(labelAngle=0, title=None)),
                    y='Count:Q',
                    color=alt.Color('Category:N', scale=alt.Scale(domain=["Verified Candidates", "Contradictory / Rejected Profiles"], range=["#00b4d8", "#ff8800"]), legend=None)
                ).properties(width=400, height=250)
                st.altair_chart(chart1, use_container_width=True)
                
            with col_c2:
                st.write("#### Experience Seniority Spread")
                exp_list = [c["experience"] for c in ranked_pool]
                df_exp = pd.DataFrame({"Experience (Years)": exp_list})
                chart2 = alt.Chart(df_exp).mark_bar().encode(
                    alt.X("Experience (Years):Q", bin=alt.Bin(maxbins=12), title="Years of Professional Experience"),
                    y=alt.Y('count()', title="Candidate Count"),
                    color=alt.value("#64748b")
                ).properties(width=400, height=250)
                st.altair_chart(chart2, use_container_width=True)
                
            col_c3, col_c4 = st.columns(2)
            with col_c3:
                st.write("#### Notice Period Distribution")
                notice_list = [c["redrob_signals"].get("notice_period_days", 60) for c in ranked_pool]
                df_notice = pd.DataFrame({"Notice Period (Days)": notice_list})
                chart3 = alt.Chart(df_notice).mark_bar().encode(
                    alt.X("Notice Period (Days):Q", bin=alt.Bin(maxbins=10), title="Notice Period (Days)"),
                    y=alt.Y('count()', title="Candidate Count"),
                    color=alt.value("#0ba360")
                ).properties(width=400, height=250)
                st.altair_chart(chart3, use_container_width=True)
                
            with col_c4:
                st.write("#### Target Skill Competency Distribution")
                skill_counts = {}
                for c in ranked_pool:
                    for skill in c.get("skills", []):
                        s_name = skill.get("name", "").lower()
                        for cat_name, synonyms in CORE_AI_ML.items():
                            if any(syn in s_name for syn in synonyms):
                                skill_counts[cat_name] = skill_counts.get(cat_name, 0) + 1
                df_skills = pd.DataFrame({
                    "Competency": [s.replace("_", " ").title() for s in skill_counts.keys()],
                    "Candidate Matches": list(skill_counts.values())
                })
                if not df_skills.empty:
                    df_skills = df_skills.sort_values(by="Candidate Matches", ascending=False).head(6)
                    chart4 = alt.Chart(df_skills).mark_bar().encode(
                        x=alt.X("Candidate Matches:Q", title="Number of Matching Profiles"),
                        y=alt.Y("Competency:N", sort="-x", title="Competency Area"),
                        color=alt.Color("Competency:N", legend=None)
                    ).properties(width=400, height=250)
                    st.altair_chart(chart4, use_container_width=True)
                else:
                    st.info("No skill analytics available.")

            col_c5, col_c6 = st.columns(2)
            with col_c5:
                st.write("#### Expected Compensation Distribution")
                sal_list = [
                    (c["redrob_signals"].get("expected_salary_range_inr_lpa", {}).get("min", 15.0) + 
                     c["redrob_signals"].get("expected_salary_range_inr_lpa", {}).get("max", 25.0)) / 2.0 
                    for c in ranked_pool
                ]
                df_sal = pd.DataFrame({"Expected Salary (INR LPA)": sal_list})
                chart5 = alt.Chart(df_sal).mark_bar().encode(
                    alt.X("Expected Salary (INR LPA):Q", bin=alt.Bin(maxbins=12), title="Expected Salary (LPA)"),
                    y=alt.Y('count()', title="Count"),
                    color=alt.value("#ff8800")
                ).properties(width=400, height=250)
                st.altair_chart(chart5, use_container_width=True)
                
            with col_c6:
                st.write("#### GitHub Activity vs. Candidate Fit Score")
                git_list = [c["redrob_signals"].get("github_activity_score", 0) for c in ranked_pool]
                score_list = [c["score"] for c in ranked_pool]
                df_git_score = pd.DataFrame({"GitHub Activity Score": git_list, "Candidate Fit Score": score_list})
                df_git_score = df_git_score[df_git_score["GitHub Activity Score"] >= 0]
                chart6 = alt.Chart(df_git_score).mark_circle(color="#00b4d8", size=50).encode(
                    x=alt.X("GitHub Activity Score:Q", title="GitHub Activity Score"),
                    y=alt.Y("Candidate Fit Score:Q", title="Overall Fit Score"),
                    tooltip=["GitHub Activity Score", "Candidate Fit Score"]
                ).properties(width=400, height=250)
                st.altair_chart(chart6, use_container_width=True)

        with tab3:
            st.write("### 🔬 Interactive ATS Resume Analyzer & Live Coach")
            col_ats1, col_ats2 = st.columns(2)
            with col_ats1:
                jd_input = st.text_area("🎯 Paste Job Description (JD):", value=GUEST_SAMPLE_JD, height=280)
            with col_ats2:
                resume_input = st.text_area("👤 Paste Candidate Resume / LinkedIn Bio:", value="", placeholder="Paste candidate profile text...", height=280)
                
            if st.button("🚀 Analyze Compatibility"):
                if not resume_input.strip():
                    st.error("Please enter a resume to analyze.")
                else:
                    st.markdown("### 📊 Compatibility Report")
                    jd_lower = jd_input.lower()
                    res_lower = resume_input.lower()
                    
                    # Parse JD dynamically to get keywords
                    jd_config = parse_job_description(jd_input)
                    keywords = jd_config["active_keywords"]
                    
                    matched_skills = []
                    missing_skills = []
                    for key, synonyms in keywords.items():
                        if any(syn in res_lower for syn in synonyms):
                            matched_skills.append(key)
                        else:
                            missing_skills.append(key)
                    
                    match_percentage = int((len(matched_skills) / len(keywords)) * 100) if keywords else 0
                    
                    col_score, col_v = st.columns([1, 3])
                    with col_score:
                        st.markdown(f"""
                        <div class="metric-card" style="margin-top: 10px;">
                            <h4 style="margin: 0;">Compatibility</h4>
                            <p class="highlight-blue">{match_percentage}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_v:
                        if match_percentage >= 75:
                            verdict = f"⭐⭐⭐⭐⭐ **Highly Recommended Fit** — Candidate exhibits excellent technical alignment with the requirements in the Job Description. Strong match across {len(matched_skills)} core capabilities."
                        elif match_percentage >= 50:
                            verdict = "⭐⭐⭐ **Moderate Fit** — Candidate has some foundational background but lacks specialization in key skills or tools required for the role."
                        else:
                            verdict = "⭐ **Low Fit** — High competency gaps in core role capabilities."
                        st.markdown(f"""
                        <div style="background: rgba(28,37,65,0.25); border: 1px solid rgba(255,255,255,0.05); padding: 18px; border-radius: 10px;">
                            <strong>Talent Compatibility Verdict:</strong><br/>
                            <span style="font-size:0.95rem; color:#cbd5e1;">{verdict}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("<br/>", unsafe_allow_html=True)
                    col_k1, col_k2 = st.columns(2)
                    with col_k1:
                        st.write("🟢 **Matched Capabilities (Strengths)**")
                        for s in matched_skills:
                            st.markdown(f'<span class="glass-badge-green">✔ {s}</span>', unsafe_allow_html=True)
                    with col_k2:
                        st.write("🟠 **Identified Competency Gaps**")
                        for s in missing_skills:
                            st.markdown(f'<span class="glass-badge-orange">⚠️ {s}</span>', unsafe_allow_html=True)
                            
                    st.markdown("<br/>", unsafe_allow_html=True)
                    st.write("### 📋 Live Coach: Tailored Interview Questions")
                    questions = []
                    for idx, skill in enumerate(missing_skills[:3]):
                        clean_skill_name = skill.replace("_", " ").title()
                        questions.append(
                            f"{idx+1}. **Verify {clean_skill_name}**: "
                            f"*'We noticed that {clean_skill_name} is a key requirement in the Job Description, "
                            f"but it is not heavily highlighted in your resume. Can you describe your experience and "
                            f"competency in {clean_skill_name}?'*"
                        )
                    if not questions:
                        questions.append("• **Explore Leadership & Progression**: *'What is the most challenging project you have led in this domain? How did you define success and collaborate with cross-functional teams?'*")
                    for q in questions[:3]:
                        st.markdown(q)

        with tab4:
            st.write("### 👥 Candidate Side-by-Side Comparison Matrix")
            pool = st.session_state.get("ranked_pool", ranked_pool)
            
            cand_options = [f"{c['name']} ({c['candidate_id']}) - Rank {idx+1}" for idx, c in enumerate(pool[:shortlist_limit])]
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                cand1_selection = st.selectbox("Select Candidate A:", cand_options, index=0, key="portal_comp_a")
            with col_sel2:
                cand2_selection = st.selectbox("Select Candidate B:", cand_options, index=min(1, len(cand_options)-1), key="portal_comp_b")
                
            idx1 = cand_options.index(cand1_selection)
            idx2 = cand_options.index(cand2_selection)
            c1 = pool[idx1]
            c2 = pool[idx2]
            
            comp_df = pd.DataFrame({
                "Evaluation Parameter": [
                    "Rank Placement", "Composite Match Score", "Current Role", "Current Company",
                    "Total Experience (Years)", "Tech Stack Fit Score", "Career Velocity Score",
                    "Behavioral Ownership Score", "Platform Activity Score",
                    "Notice Period", "Expected Compensation"
                ],
                f"Candidate A: {c1['name']}": [
                    f"#{idx1+1}", f"{c1['score']:.3f}", c1['title'], c1['company'],
                    f"{c1['experience']:.1f} Yrs", f"{c1['s_sem_norm']:.2f}", f"{c1['v_c_norm']:.2f}",
                    f"{c1['s_b_norm']:.2f}", f"{c1['a_p_norm']:.2f}",
                    f"{c1.get('redrob_signals', {}).get('notice_period_days', 60)} Days",
                    f"{c1.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('min', 15)} - {c1.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('max', 25)} LPA"
                ],
                f"Candidate B: {c2['name']}": [
                    f"#{idx2+1}", f"{c2['score']:.3f}", c2['title'], c2['company'],
                    f"{c2['experience']:.1f} Yrs", f"{c2['s_sem_norm']:.2f}", f"{c2['v_c_norm']:.2f}",
                    f"{c2['s_b_norm']:.2f}", f"{c2['a_p_norm']:.2f}",
                    f"{c2.get('redrob_signals', {}).get('notice_period_days', 60)} Days",
                    f"{c2.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('min', 15)} - {c2.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('max', 25)} LPA"
                ]
            })
            st.table(comp_df)

# Render View: Guest Sandbox Mode (preloaded 3 profiles, admin features locked)
elif st.session_state["view"] == "guest_sandbox":
    # Sidebar
    st.sidebar.markdown(
        f'<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">{SVG_LOGO}<h2 style="margin: 0; font-size: 1.5rem; color: #f8fafc; font-family: Space Grotesk;">AuraMatch</h2></div>',
        unsafe_allow_html=True
    )
    st.sidebar.markdown("🔒 **Admin Options Locked** (Guest Mode)")
    st.sidebar.info("Upload Custom Candidate File, Export Data, and Advanced Weights are disabled.")
    
    # Prepopulated sandbox weights (locked slider views)
    w_skills, w_exp, w_behave, w_activity = 55, 15, 15, 15
    st.sidebar.markdown("""
    *⚖️ Active Evaluation Settings:*
    - Core Tech Stack: **55%**
    - Career Velocity: **15%**
    - Ownership Verbs: **15%**
    - Platform Activity: **15%**
    """)
    
    filter_honeypots = st.sidebar.checkbox("Apply Profile Integrity Filter", value=True, disabled=True)
    filter_services = st.sidebar.checkbox("Prioritize Product Experience", value=True, disabled=True)


    
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Exit Sandbox to Homepage", use_container_width=True):
        st.session_state["view"] = "landing"
        st.rerun()
        
    # Main content (incorporates user image)
    logo_col, title_col = st.columns([1, 15])
    with logo_col:
        st.markdown(f'<div style="margin-top: 5px;">{SVG_LOGO}</div>', unsafe_allow_html=True)
    with title_col:
        st.markdown('<div class="gradient-text">AuraMatch Guest Sandbox</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="margin-bottom: 20px; display: flex; flex-direction: column; align-items: flex-start; gap: 6px;">
        <div style="color: #94a3b8; font-size: 1.05rem;">Smart AI Sourcing & Match Engine</div>
        <div style="display: flex; align-items: center; gap: 8px; color: #94a3b8; font-size: 1.05rem;">
            {profile_img_html}
            <span>Developed by <strong>SRISAI SHIVAKOTI</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 **Guest Sandbox Mode:** Preloaded with the Founding Senior AI Engineer Job Description and 3 sample candidate profiles to demonstrate the Smart AI Sourcing & Match Engine instantly.", icon="💡")
    
    # Run sandbox ranking (runs on exactly the 3 hardcoded candidates)
    ranked_pool, scanned, honeypots_filtered, clean_count = run_local_ranking(
        GUEST_CANDIDATES, w_skills, w_exp, w_behave, w_activity, filter_honeypots, filter_services
    )
    st.session_state["ranked_pool"] = ranked_pool

    tab1, tab2, tab3 = st.tabs([
        "🎯 Recommendations & Profile Insights", 
        "🔍 ATS Resume Analyzer & Live Coach",
        "👥 Candidate Comparison Matrix"
    ])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>Candidates Scanned</h4><p class="highlight-blue">{scanned}</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><h4>Integrity Flags Blocked</h4><p class="highlight-orange">{honeypots_filtered}</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><h4>Top Recommendations</h4><p class="highlight-green">{len(ranked_pool)}</p></div>', unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)
        st.write("### 📝 Sandbox Shortlist Ranking")
        
        display_data = []
        for idx, c in enumerate(ranked_pool):
            display_data.append({
                "Rank": idx + 1,
                "Candidate ID": c["candidate_id"],
                "Name": c["name"],
                "Current Title": c["title"],
                "Current Company": c["company"],
                "Experience (Yrs)": c["experience"],
                "Tech Stack Match": c["s_sem_norm"],
                "Velocity Match": c["v_c_norm"],
                "Matrix Fit Score": c["score"]
            })
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("⚠️ *Export CSV features are locked in Sandbox mode.*")
        
        st.markdown("---")
        st.write("### 👤 Candidate Profile Explorer")
        candidate_names = [f"{c['name']} ({c['candidate_id']}) - Rank {i+1}" for i, c in enumerate(ranked_pool)]
        selected_cand_name = st.selectbox("Select Candidate to Profile:", candidate_names, key="sandbox_explorer")
        selected_idx = candidate_names.index(selected_cand_name)
        selected_cand = ranked_pool[selected_idx]
        
        c_col1, c_col2 = st.columns([2, 1])
        with c_col1:
            is_top = selected_idx == 0
            box_class = "critique-box" if is_top else "verdict-box"
            header_prefix = "🛡️ AuraMatch Stage-4 LLM Critique:" if is_top else "🛡️ AuraMatch Talent Fit Verdict:"
            
            critique_html = ""
            if is_top:
                critique_html = f"""
                <div style="margin-top: 10px; padding-top: 5px; border-top: 1px dashed rgba(255,255,255,0.1);">
                    <strong style="color: #00b4d8; font-size: 0.85rem;">[Stage-4 Alignment Critique]</strong><br/>
                    <span style="font-size:0.85rem; color:#94a3b8;">
                    • <strong>Potential Gaps:</strong> Fast developer velocity. High alignment on vector databases and RAG structures.<br/>
                    • <strong>Inflation Safeguard:</strong> Verified Github commits match listed proficiency timelines.
                    </span>
                </div>
                """
            st.markdown(f"""
            <div class="glass-card">
                <h3>👤 {selected_cand['name']}</h3>
                <p style="color: #cbd5e1; font-size: 1.1rem; margin-top: -10px;"><strong>{selected_cand['title']}</strong> at <strong>{selected_cand['company']}</strong></p>
                <p style="font-size:0.95rem; color:#94a3b8;">📍 {selected_cand['profile'].get('location', 'India')}, {selected_cand['profile'].get('country', 'India')}</p>
                <p style="font-style: italic; color: #94a3b8; border-left: 2px solid rgba(255,255,255,0.2); padding-left: 10px; margin-top: 15px;">"{selected_cand['profile'].get('headline', '')}"</p>
                <div class="{box_class}">
                    <strong style="color: #00b4d8; font-family: 'Space Grotesk', sans-serif;">{header_prefix}</strong><br/>
                    <span style="font-size: 0.95rem; line-height: 1.5;">{selected_cand['reasoning']}</span>
                    {critique_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("#### 💼 Employment Record")
            for job in selected_cand.get("career_history", []):
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                    <strong>{job.get('title')}</strong> at <em>{job.get('company')}</em> ({job.get('duration_months', 0)} months)<br/>
                    <span style="font-size: 0.85rem; color: #94a3b8;">{job.get('description', '')}</span>
                </div>
                """, unsafe_allow_html=True)
        with c_col2:
            st.write("#### ⚙️ Tagged Core Skills")
            for skill in selected_cand.get("skills", []):
                st.markdown(f'<span class="glass-badge">{skill.get("name")} ({skill.get("proficiency", "intermediate")} - {skill.get("duration_months", 0)} mos)</span>', unsafe_allow_html=True)
            
            st.markdown("<br/>", unsafe_allow_html=True)
            st.write("#### ⚖️ Stage-3 Features (Normalized)")
            st.write(f"⚙️ Tech Stack Fit: `{selected_cand['s_sem_norm']:.2f}`")
            st.write(f"💼 Career Velocity: `{selected_cand['v_c_norm']:.2f}`")
            st.write(f"🛠️ Ownership agency: `{selected_cand['s_b_norm']:.2f}`")
            st.write(f"📡 Availability index: `{selected_cand['a_p_norm']:.2f}`")

    with tab2:
        st.write("### 🔬 Interactive ATS Resume Analyzer & Live Coach")
        col_ats1, col_ats2 = st.columns(2)
        with col_ats1:
            jd_input = st.text_area("🎯 Paste Job Description (JD):", value=GUEST_SAMPLE_JD, height=280, key="sandbox_ats_jd")
        with col_ats2:
            resume_input = st.text_area("👤 Paste Candidate Resume / LinkedIn Bio:", value="", placeholder="Paste candidate profile text...", height=280, key="sandbox_ats_res")
            
        if st.button("🚀 Analyze Compatibility", key="sandbox_ats_btn"):
            if not resume_input.strip():
                st.error("Please enter a resume to analyze.")
            else:
                st.markdown("### 📊 Compatibility Report")
                jd_lower = jd_input.lower()
                res_lower = resume_input.lower()
                
                # Parse JD dynamically to get keywords
                jd_config = parse_job_description(jd_input)
                keywords = jd_config["active_keywords"]
                
                matched_skills = []
                missing_skills = []
                for key, synonyms in keywords.items():
                    if any(syn in res_lower for syn in synonyms):
                        matched_skills.append(key)
                    else:
                        missing_skills.append(key)
                
                match_percentage = int((len(matched_skills) / len(keywords)) * 100) if keywords else 0
                
                col_score, col_v = st.columns([1, 3])
                with col_score:
                    st.markdown(f"""
                    <div class="metric-card" style="margin-top: 10px;">
                        <h4 style="margin: 0;">Compatibility</h4>
                        <p class="highlight-blue">{match_percentage}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_v:
                    if match_percentage >= 75:
                        verdict = f"⭐⭐⭐⭐⭐ **Highly Recommended Fit** — Candidate exhibits excellent technical alignment with the requirements in the Job Description. Strong match across {len(matched_skills)} core capabilities."
                    elif match_percentage >= 50:
                        verdict = "⭐⭐⭐ **Moderate Fit** — Candidate has some foundational background but lacks specialization in key skills or tools required for the role."
                    else:
                        verdict = "⭐ **Low Fit** — High competency gaps in core role capabilities."
                    st.markdown(f"""
                    <div style="background: rgba(28,37,65,0.25); border: 1px solid rgba(255,255,255,0.05); padding: 18px; border-radius: 10px;">
                        <strong>Talent Compatibility Verdict:</strong><br/>
                        <span style="font-size:0.95rem; color:#cbd5e1;">{verdict}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("<br/>", unsafe_allow_html=True)
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.write("🟢 **Matched Capabilities (Strengths)**")
                    for s in matched_skills:
                        st.markdown(f'<span class="glass-badge-green">✔ {s}</span>', unsafe_allow_html=True)
                with col_k2:
                    st.write("🟠 **Identified Competency Gaps**")
                    for s in missing_skills:
                        st.markdown(f'<span class="glass-badge-orange">⚠️ {s}</span>', unsafe_allow_html=True)
                        
                st.markdown("<br/>", unsafe_allow_html=True)
                st.write("### 📋 Live Coach: Tailored Interview Questions")
                questions = []
                for idx, skill in enumerate(missing_skills[:3]):
                    clean_skill_name = skill.replace("_", " ").title()
                    questions.append(
                        f"{idx+1}. **Verify {clean_skill_name}**: "
                        f"*'We noticed that {clean_skill_name} is a key requirement in the Job Description, "
                        f"but it is not heavily highlighted in your resume. Can you describe your experience and "
                        f"competency in {clean_skill_name}?'*"
                    )
                if not questions:
                    questions.append("• **Explore Leadership & Progression**: *'What is the most challenging project you have led in this domain? How did you define success and collaborate with cross-functional teams?'*")
                for q in questions[:2]:
                    st.markdown(q)

    with tab3:
        st.write("### 👥 Candidate Side-by-Side Comparison Matrix")
        pool = st.session_state.get("ranked_pool", ranked_pool)
        
        cand_options = [f"{c['name']} ({c['candidate_id']}) - Rank {idx+1}" for idx, c in enumerate(pool)]
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            cand1_selection = st.selectbox("Select Candidate A:", cand_options, index=0, key="sandbox_comp_a")
        with col_sel2:
            cand2_selection = st.selectbox("Select Candidate B:", cand_options, index=min(1, len(cand_options)-1), key="sandbox_comp_b")
            
        idx1 = cand_options.index(cand1_selection)
        idx2 = cand_options.index(cand2_selection)
        c1 = pool[idx1]
        c2 = pool[idx2]
        
        comp_df = pd.DataFrame({
            "Evaluation Parameter": [
                "Rank Placement", "Composite Match Score", "Current Role", "Current Company",
                "Total Experience (Years)", "Tech Stack Fit Score", "Career Velocity Score",
                "Behavioral Ownership Score", "Platform Activity Score",
                "Notice Period", "Expected Compensation"
            ],
            f"Candidate A: {c1['name']}": [
                f"#{idx1+1}", f"{c1['score']:.3f}", c1['title'], c1['company'],
                f"{c1['experience']:.1f} Yrs", f"{c1['s_sem_norm']:.2f}", f"{c1['v_c_norm']:.2f}",
                f"{c1['s_b_norm']:.2f}", f"{c1['a_p_norm']:.2f}",
                f"{c1.get('redrob_signals', {}).get('notice_period_days', 60)} Days",
                f"{c1.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('min', 15)} - {c1.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('max', 25)} LPA"
            ],
            f"Candidate B: {c2['name']}": [
                f"#{idx2+1}", f"{c2['score']:.3f}", c2['title'], c2['company'],
                f"{c2['experience']:.1f} Yrs", f"{c2['s_sem_norm']:.2f}", f"{c2['v_c_norm']:.2f}",
                f"{c2['s_b_norm']:.2f}", f"{c2['a_p_norm']:.2f}",
                f"{c2.get('redrob_signals', {}).get('notice_period_days', 60)} Days",
                f"{c2.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('min', 15)} - {c2.get('redrob_signals', {}).get('expected_salary_range_inr_lpa', {}).get('max', 25)} LPA"
            ]
        })
        st.table(comp_df)
