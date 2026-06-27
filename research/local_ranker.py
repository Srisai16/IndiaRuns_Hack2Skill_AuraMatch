import json
import os
import re
from datetime import datetime

# Core technical keywords from JD
CORE_AI_ML = {
    "embeddings": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
    "vector_db": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
    "retrieval_search": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir"],
    "ranking": ["ranking", "re-ranking", "re-rank", "learning-to-rank", "ltr", "xgboost", "lightgbm", "cross-encoder"],
    "llm_genai": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
    "evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"]
}

# Software/Python keywords
CORE_SWE = ["python", "software engineering", "system design", "backend", "api", "apis", "git", "ci/cd", "docker", "kubernetes"]

# Services / consulting firms list (lowercase)
SERVICES_COMPANIES = {
    "tcs", "tata consultancy services", "wipro", "infosys", "cognizant", "accenture", "capgemini",
    "hcl", "hcltech", "tech mahindra", "mindtree", "genpact", "l&t", "ltts", "mphasis", "persistent",
    "coforge", "ust global", "virtusa", "syntel", "hexaware", "tata consultancy"
}

# Disallowed current roles / non-tech roles (lowercase)
DISALLOWED_ROLES = {
    "marketing", "accountant", "hr", "human resources", "operations manager", "customer support",
    "sales", "finance", "admin", "designer", "writer", "recruiter", "content creator", "editor",
    "mechanical", "chemical", "civil", "hardware", "office assistant", "receptionist", "auditor"
}

# Ideal location matches (lowercase)
PREFERRED_LOCATIONS = {"noida", "pune", "delhi ncr", "delhi", "gurgaon", "hyderabad", "mumbai", "chennai", "bangalore", "bengaluru"}

def is_clean_profile(cand):
    """
    Apply strict checks to filter out honeypots/trap candidates.
    Returns (True, []) if clean, or (False, list_of_reasons) if honeypot.
    """
    reasons = []
    
    # 1. Salary flip check: expected min must be <= max
    sal = cand.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
    sal_min = sal.get("min")
    sal_max = sal.get("max")
    if sal_min is not None and sal_max is not None:
        if sal_min > sal_max:
            reasons.append(f"Salary min ({sal_min}) > max ({sal_max})")

    # 2. Skill duration vs proficiency: expert/advanced cannot have 0 duration
    # We found that honeypots have multiple expert/advanced skills with 0 duration
    bad_skills_count = 0
    for skill in cand.get("skills", []):
        dur = skill.get("duration_months", 0)
        prof = skill.get("proficiency", "")
        if prof in ["expert", "advanced"] and dur == 0:
            bad_skills_count += 1
    if bad_skills_count >= 3:
        reasons.append(f"Expert/Advanced skills with 0 duration ({bad_skills_count} skills)")

    # 3. Job duration vs actual dates range
    for job in cand.get("career_history", []):
        start_str = job.get("start_date")
        end_str = job.get("end_date")
        dur = job.get("duration_months", 0)
        company = job.get("company", "")
        
        if start_str:
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                if end_str:
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
                else:
                    end_date = datetime(2026, 6, 26)  # Reference date for active jobs
                
                max_possible_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                # If job duration is impossible (greater than date range + 3 months buffer)
                if dur > max_possible_months + 3:
                    reasons.append(f"Worked {dur} months at {company} but date range allows max {max_possible_months}")
            except Exception as e:
                pass

    # 4. Job duration vs profile total experience
    years_exp = cand.get("profile", {}).get("years_of_experience", 0)
    for job in cand.get("career_history", []):
        dur_years = job.get("duration_months", 0) / 12.0
        # A single job duration cannot exceed total profile experience
        if dur_years > years_exp + 1.0:
            reasons.append(f"Job duration at {job.get('company')} ({dur_years:.1f} years) exceeds profile experience ({years_exp:.1f} years)")

    # 5. Experience mismatch: sum of durations vs years_of_experience
    sum_dur_years = sum(job.get("duration_months", 0) for job in cand.get("career_history", [])) / 12.0
    if sum_dur_years > years_exp + 5.0:
        reasons.append(f"Sum of job durations ({sum_dur_years:.1f} years) exceeds profile experience ({years_exp:.1f} years) by 5+ years")
    elif years_exp > sum_dur_years + 5.0:
        reasons.append(f"Profile experience ({years_exp:.1f} years) exceeds sum of job durations ({sum_dur_years:.1f} years) by 5+ years")

    # 6. Signup date > active date
    signup_str = cand.get("redrob_signals", {}).get("signup_date")
    active_str = cand.get("redrob_signals", {}).get("last_active_date")
    if signup_str and active_str:
        try:
            signup_dt = datetime.strptime(signup_str, "%Y-%m-%d")
            active_dt = datetime.strptime(active_str, "%Y-%m-%d")
            if signup_dt > active_dt:
                reasons.append(f"Signup date ({signup_str}) is after last active date ({active_str})")
        except:
            pass

    return len(reasons) == 0, reasons

def calculate_skills_score(cand):
    """
    Score the candidate's skills based on core JD requirements.
    This checks both direct skill names and text mentions in summary/career descriptions.
    """
    skill_score = 0.0
    matched_categories = set()
    
    # Text corpus for description search
    headline = cand.get("profile", {}).get("headline", "").lower()
    summary = cand.get("profile", {}).get("summary", "").lower()
    history_desc = " ".join([job.get("description", "").lower() for job in cand.get("career_history", [])])
    history_titles = " ".join([job.get("title", "").lower() for job in cand.get("career_history", [])])
    all_text = f"{headline} {summary} {history_desc} {history_titles}"
    
    # 1. Direct skills check
    cand_skills = cand.get("skills", [])
    for skill in cand_skills:
        skill_name = skill.get("name", "").lower()
        proficiency = skill.get("proficiency", "intermediate")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)
        
        # Determine proficiency weight
        prof_weight = {"expert": 1.5, "advanced": 1.2, "intermediate": 1.0, "beginner": 0.5}.get(proficiency, 1.0)
        dur_weight = min(duration, 60.0) / 12.0  # Cap at 5 years
        endorse_weight = 1.0 + min(endorsements, 50) / 50.0  # Max 2x multiplier
        
        # Match against CORE_AI_ML categories
        for cat_name, synonyms in CORE_AI_ML.items():
            if any(syn in skill_name for syn in synonyms):
                # Calculate category score for this skill
                matched_categories.add(cat_name)
                skill_score += 10.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
                
        # Match against Python / SWE
        if any(swe in skill_name for swe in CORE_SWE):
            skill_score += 5.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
            
    # 2. Text descriptions check (for semantic experience without direct skills listing)
    # This helps find the "Tier 5 candidate who didn't list RAG but built recommendation systems"
    for cat_name, synonyms in CORE_AI_ML.items():
        # If not matched directly in skills list, check in description texts
        if cat_name not in matched_categories:
            count = sum(1 for syn in synonyms if syn in all_text)
            if count > 0:
                matched_categories.add(cat_name)
                # Smaller score for text mentions, but still significant
                skill_score += 4.0 * min(count, 3)

    # Check for Python in text
    if "python" in all_text and not any("python" in s.get("name", "").lower() for s in cand_skills):
        skill_score += 3.0
        
    # Check for evaluation terms
    if any(term in all_text for term in ["ndcg", "mrr", "map", "evaluation framework", "ab test", "a/b test"]):
        if "evaluation" not in matched_categories:
            matched_categories.add("evaluation")
            skill_score += 4.0
            
    # Category breadth multiplier
    # Having skills across multiple core categories (e.g. embeddings, vector db, ranking, evaluation) is excellent
    breadth_multiplier = 1.0 + (len(matched_categories) * 0.15)
    
    return skill_score * breadth_multiplier

def calculate_experience_score(cand):
    """
    Score based on years of experience, current title fit, and services company exclusions.
    """
    # 1. Total Years of Experience
    years_exp = cand.get("profile", {}).get("years_of_experience", 0)
    exp_score = 0.0
    
    if 6.0 <= years_exp <= 8.0:
        exp_score = 10.0  # Perfect fit (6-8 years)
    elif 5.0 <= years_exp <= 9.0:
        exp_score = 8.5   # In sweet spot (5-9 years)
    elif 4.0 <= years_exp <= 10.0:
        exp_score = 6.0   # Tolerable
    elif 3.0 <= years_exp <= 12.0:
        exp_score = 3.0   # Out of sweet spot but allowed
    else:
        exp_score = 0.5   # Very low score for others

    # 2. Current Title Fit
    current_title = cand.get("profile", {}).get("current_title", "").lower()
    
    # Check disqualified titles first
    if any(role in current_title for role in DISALLOWED_ROLES):
        return 0.0  # Reject immediately by setting score to 0
        
    title_score = 1.0
    # Tier 1 titles (AI/ML Specific)
    if any(term in current_title for term in ["ai engineer", "ml engineer", "machine learning", "nlp", "search engineer", "retrieval engineer", "ranking engineer", "applied ml"]):
        title_score = 3.0
    # Tier 2 titles (Backend/Data/Tech Lead)
    elif any(term in current_title for term in ["data engineer", "software engineer", "backend", "full stack", "tech lead", "engineering manager", "developer"]):
        title_score = 2.0
    # Tier 3 (Others)
    else:
        title_score = 1.0
        
    # 3. Services vs Product Company Filter
    # Check if the candidate has ONLY worked at services companies
    companies = []
    curr_company = cand.get("profile", {}).get("current_company", "").lower()
    if curr_company:
        companies.append(curr_company)
    for job in cand.get("career_history", []):
        comp = job.get("company", "").lower()
        if comp:
            companies.append(comp)
            
    is_pure_services = False
    if companies:
        is_pure_services = all(
            any(srv in comp for srv in SERVICES_COMPANIES) for comp in companies
        )
        
    services_multiplier = 0.15 if is_pure_services else 1.0
    
    # Check if they have ever worked at a known product company / startup
    # (e.g. Wayne, Stark, Initech, Swiggy, Swiggy, Zomato, CRED, Razorpay, etc.)
    has_product_exp = any(
        not any(srv in comp for srv in SERVICES_COMPANIES) for comp in companies
    )
    product_multiplier = 1.2 if has_product_exp else 1.0
    
    final_exp_score = exp_score * title_score * services_multiplier * product_multiplier
    return final_exp_score

def calculate_behavioral_multiplier(cand):
    """
    Score candidate availability, response rate, location, notice period, and active github.
    Returns a multiplier (e.g. 0.5 to 1.5).
    """
    signals = cand.get("redrob_signals", {})
    multiplier = 1.0
    
    # 1. Open to work flag
    open_to_work = signals.get("open_to_work_flag", False)
    multiplier *= 1.1 if open_to_work else 1.0
    
    # 2. Last active date recency
    # Current date is June 26, 2026
    last_active_str = signals.get("last_active_date")
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d")
            delta_days = (datetime(2026, 6, 26) - last_active).days
            if delta_days <= 30:
                multiplier *= 1.1
            elif delta_days <= 90:
                multiplier *= 1.0
            elif delta_days <= 180:
                multiplier *= 0.8
            else:
                multiplier *= 0.4  # Stale profile down-weight
        except:
            multiplier *= 0.8
            
    # 3. Recruiter response rate & interview attendance
    response_rate = signals.get("recruiter_response_rate", 0.0)
    interview_rate = signals.get("interview_completion_rate", 0.0)
    
    # Penalize extremely low response rates (<15% response rate)
    if response_rate < 0.15:
        multiplier *= 0.3
    else:
        multiplier *= (0.5 + 0.5 * response_rate)
        
    multiplier *= (0.6 + 0.4 * interview_rate)
    
    # 4. Notice Period
    notice_days = signals.get("notice_period_days", 60)
    if notice_days <= 30:
        multiplier *= 1.15  # Preferred sub-30
    elif notice_days <= 60:
        multiplier *= 1.0
    elif notice_days <= 90:
        multiplier *= 0.8
    else:
        multiplier *= 0.4  # Stiff penalty for 90+ days (e.g., 120, 150, 180)

    # 5. GitHub Activity
    github_score = signals.get("github_activity_score", -1)
    if github_score > 0:
        multiplier *= (1.0 + (github_score / 300.0))  # Max ~1.33x

    # 6. Location & Relocation Fit
    loc = cand.get("profile", {}).get("location", "").lower()
    country = cand.get("profile", {}).get("country", "").lower()
    relocate = signals.get("willing_to_relocate", False)
    
    # Check if location matches preferred Noida/Pune/NCR
    is_preferred_loc = any(p_loc in loc for p_loc in PREFERRED_LOCATIONS)
    is_india = "india" in country or "in" == country or any(p_loc in loc for p_loc in PREFERRED_LOCATIONS)
    
    if is_preferred_loc:
        multiplier *= 1.2
    elif is_india:
        multiplier *= 1.0 if relocate else 0.8
    else:
        # Outside India
        multiplier *= 0.4 if relocate else 0.1  # Heavy penalty - case-by-case, no visa sponsorship
        
    return multiplier

def process_and_rank_all():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    print("Ranking candidates...")
    ranked_pool = []
    honeypot_count = 0
    scanned = 0
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            scanned += 1
            
            # Filter out honeypots
            is_clean, reasons = is_clean_profile(cand)
            if not is_clean:
                honeypot_count += 1
                continue
                
            # Calculate components
            skills_score = calculate_skills_score(cand)
            exp_score = calculate_experience_score(cand)
            behavioral_mult = calculate_behavioral_multiplier(cand)
            
            # Combine components (60% Dense Semantic + 20% Title/Experience + 20% Behavioral)
            # We scale the components so they fit roughly equal ranges
            # Local score = (Skills_Score * 0.6 + Experience_Score * 2.0 * 0.2) * Behavioral_Multiplier
            # Experience_Score has max ~10, skills_score has max ~100
            final_score = (skills_score * 0.65 + exp_score * 3.5 * 0.15) * behavioral_mult
            
            # Exclude zero-scored (disqualified current titles, etc.)
            if final_score <= 0.0:
                continue
                
            ranked_pool.append({
                "candidate_id": cand["candidate_id"],
                "name": cand["profile"]["anonymized_name"],
                "title": cand["profile"]["current_title"],
                "company": cand["profile"]["current_company"],
                "years_exp": cand["profile"]["years_of_experience"],
                "score": final_score,
                "skills_score": skills_score,
                "exp_score": exp_score,
                "behavioral_mult": behavioral_mult,
                "profile": cand["profile"],
                "career_history": cand["career_history"],
                "education": cand["education"],
                "skills": cand["skills"],
                "redrob_signals": cand["redrob_signals"]
            })

    # Sort candidates by final score descending, and break ties by candidate_id ascending
    ranked_pool.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    print(f"Scanned: {scanned}")
    print(f"Filtered Honeypots: {honeypot_count}")
    print(f"Clean Candidates Available: {len(ranked_pool)}")
    
    # Save top 300 candidates to a JSON file for detailed review / LLM re-ranking
    top_300 = ranked_pool[:300]
    with open("top_candidates_to_review.json", "w", encoding="utf-8") as f:
        json.dump(top_300, f, indent=2)
    print("Saved top 300 candidates to top_candidates_to_review.json")
    
    # Print top 15 candidates
    print("\n--- TOP 15 CANDIDATES ---")
    for i, c in enumerate(ranked_pool[:15]):
        print(f"{i+1}. ID: {c['candidate_id']}, Name: {c['name']}, Score: {c['score']:.3f} (S: {c['skills_score']:.1f}, E: {c['exp_score']:.1f}, M: {c['behavioral_mult']:.2f})")
        print(f"   Title: {c['title']} at {c['company']} ({c['years_exp']} yrs exp)")
        print(f"   Location: {c['profile']['location']}, {c['profile']['country']} | Notice: {c['redrob_signals']['notice_period_days']} days | Respond: {c['redrob_signals']['recruiter_response_rate']:.2f}")

if __name__ == "__main__":
    process_and_rank_all()
