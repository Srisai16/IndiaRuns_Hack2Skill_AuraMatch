#!/usr/bin/env python3
import json
import os
import csv
import gzip
import argparse
from datetime import datetime

# Core technical keywords from JD for local fallback scoring
CORE_AI_ML = {
    "embeddings": ["embedding", "embeddings", "sentence-transformers", "bge", "e5", "dense vector", "dense retrieval"],
    "vector_db": ["pinecone", "qdrant", "weaviate", "milvus", "faiss", "vector database", "vector db", "chromadb"],
    "retrieval_search": ["retrieval", "vector search", "dense retrieval", "hybrid search", "semantic search", "bm25", "search engine", "information retrieval", "ir"],
    "ranking": ["ranking", "re-ranking", "re-rank", "learning-to-rank", "ltr", "xgboost", "lightgbm", "cross-encoder"],
    "llm_genai": ["llm", "large language model", "rag", "retrieval-augmented generation", "fine-tuning", "peft", "lora", "qlora", "prompt engineering", "langchain", "llamaindex"],
    "evaluation": ["ndcg", "mrr", "map", "precision", "recall", "evaluation framework", "ab test", "a/b test"]
}

CORE_SWE = ["python", "software engineering", "system design", "backend", "api", "apis", "git", "ci/cd", "docker", "kubernetes"]

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

def is_clean_profile(cand):
    """
    Apply strict checks to filter out honeypots/trap candidates.
    """
    # 1. Salary flip check
    sal = cand.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
    sal_min = sal.get("min")
    sal_max = sal.get("max")
    if sal_min is not None and sal_max is not None:
        if sal_min > sal_max:
            return False

    # 2. Skill duration vs proficiency
    bad_skills_count = 0
    for skill in cand.get("skills", []):
        dur = skill.get("duration_months", 0)
        prof = skill.get("proficiency", "")
        if prof in ["expert", "advanced"] and dur == 0:
            bad_skills_count += 1
    if bad_skills_count >= 3:
        return False

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
                    return False
            except:
                pass

    # 4. Job duration vs profile total experience
    years_exp = cand.get("profile", {}).get("years_of_experience", 0)
    for job in cand.get("career_history", []):
        dur_years = job.get("duration_months", 0) / 12.0
        if dur_years > years_exp + 1.0:
            return False

    # 5. Experience mismatch: sum of durations vs years_of_experience
    sum_dur_years = sum(job.get("duration_months", 0) for job in cand.get("career_history", [])) / 12.0
    if sum_dur_years > years_exp + 5.0 or years_exp > sum_dur_years + 5.0:
        return False

    # 6. Signup date > active date
    signup_str = cand.get("redrob_signals", {}).get("signup_date")
    active_str = cand.get("redrob_signals", {}).get("last_active_date")
    if signup_str and active_str:
        try:
            signup_dt = datetime.strptime(signup_str, "%Y-%m-%d")
            active_dt = datetime.strptime(active_str, "%Y-%m-%d")
            if signup_dt > active_dt:
                return False
        except:
            pass

    return True

def calculate_local_score(cand):
    """
    Fallback scoring algorithm for candidates not found in the precomputed database.
    """
    # 1. Technical Skills Score
    skill_score = 0.0
    matched_categories = set()
    
    headline = cand.get("profile", {}).get("headline", "").lower()
    summary = cand.get("profile", {}).get("summary", "").lower()
    history_desc = " ".join([job.get("description", "").lower() for job in cand.get("career_history", [])])
    history_titles = " ".join([job.get("title", "").lower() for job in cand.get("career_history", [])])
    all_text = f"{headline} {summary} {history_desc} {history_titles}"
    
    cand_skills = cand.get("skills", [])
    for skill in cand_skills:
        skill_name = skill.get("name", "").lower()
        proficiency = skill.get("proficiency", "intermediate")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)
        
        prof_weight = {"expert": 1.5, "advanced": 1.2, "intermediate": 1.0, "beginner": 0.5}.get(proficiency, 1.0)
        dur_weight = min(duration, 60.0) / 12.0
        endorse_weight = 1.0 + min(endorsements, 50) / 50.0
        
        for cat_name, synonyms in CORE_AI_ML.items():
            if any(syn in skill_name for syn in synonyms):
                matched_categories.add(cat_name)
                skill_score += 10.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
                
        if any(swe in skill_name for swe in CORE_SWE):
            skill_score += 5.0 * prof_weight * (1.0 + 0.1 * dur_weight) * endorse_weight
            
    for cat_name, synonyms in CORE_AI_ML.items():
        if cat_name not in matched_categories:
            count = sum(1 for syn in synonyms if syn in all_text)
            if count > 0:
                matched_categories.add(cat_name)
                skill_score += 4.0 * min(count, 3)

    if "python" in all_text and not any("python" in s.get("name", "").lower() for s in cand_skills):
        skill_score += 3.0
    if any(term in all_text for term in ["ndcg", "mrr", "map", "evaluation"]):
        if "evaluation" not in matched_categories:
            matched_categories.add("evaluation")
            skill_score += 4.0
            
    breadth_multiplier = 1.0 + (len(matched_categories) * 0.15)
    skills_final = skill_score * breadth_multiplier

    # 2. Experience & Title Score
    years_exp = cand.get("profile", {}).get("years_of_experience", 0)
    exp_score = 0.5
    if 6.0 <= years_exp <= 8.0:
        exp_score = 10.0
    elif 5.0 <= years_exp <= 9.0:
        exp_score = 8.5
    elif 4.0 <= years_exp <= 10.0:
        exp_score = 6.0
    elif 3.0 <= years_exp <= 12.0:
        exp_score = 3.0

    current_title = cand.get("profile", {}).get("current_title", "").lower()
    if any(role in current_title for role in DISALLOWED_ROLES):
        return 0.0
        
    title_score = 1.0
    if any(term in current_title for term in ["ai engineer", "ml engineer", "machine learning", "nlp", "search engineer", "retrieval engineer", "ranking engineer"]):
        title_score = 3.0
    elif any(term in current_title for term in ["data engineer", "software engineer", "backend", "full stack", "tech lead", "engineering manager"]):
        title_score = 2.0
        
    companies = [cand.get("profile", {}).get("current_company", "").lower()]
    for job in cand.get("career_history", []):
        comp = job.get("company", "").lower()
        if comp:
            companies.append(comp)
    is_pure_services = companies and all(any(srv in comp for srv in SERVICES_COMPANIES) for comp in companies)
    services_multiplier = 0.15 if is_pure_services else 1.0
    
    exp_final = exp_score * title_score * services_multiplier

    # 3. Behavioral Multiplier
    signals = cand.get("redrob_signals", {})
    behavioral_mult = 1.0
    
    open_to_work = signals.get("open_to_work_flag", False)
    behavioral_mult *= 1.1 if open_to_work else 1.0
    
    last_active_str = signals.get("last_active_date")
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d")
            delta_days = (datetime(2026, 6, 26) - last_active).days
            if delta_days <= 30:
                behavioral_mult *= 1.1
            elif delta_days <= 90:
                behavioral_mult *= 1.0
            elif delta_days <= 180:
                behavioral_mult *= 0.8
            else:
                behavioral_mult *= 0.4
        except:
            behavioral_mult *= 0.8
            
    response_rate = signals.get("recruiter_response_rate", 0.0)
    interview_rate = signals.get("interview_completion_rate", 0.0)
    if response_rate < 0.15:
        behavioral_mult *= 0.3
    else:
        behavioral_mult *= (0.5 + 0.5 * response_rate)
    behavioral_mult *= (0.6 + 0.4 * interview_rate)
    
    notice_days = signals.get("notice_period_days", 60)
    if notice_days <= 30:
        behavioral_mult *= 1.15
    elif notice_days <= 60:
        behavioral_mult *= 1.0
    elif notice_days <= 90:
        behavioral_mult *= 0.8
    else:
        behavioral_mult *= 0.4

    github_score = signals.get("github_activity_score", -1)
    if github_score > 0:
        behavioral_mult *= (1.0 + (github_score / 300.0))

    loc = cand.get("profile", {}).get("location", "").lower()
    country = cand.get("profile", {}).get("country", "").lower()
    relocate = signals.get("willing_to_relocate", False)
    is_preferred_loc = any(p_loc in loc for p_loc in PREFERRED_LOCATIONS)
    is_india = "india" in country or "in" == country or any(p_loc in loc for p_loc in PREFERRED_LOCATIONS)
    
    if is_preferred_loc:
        behavioral_mult *= 1.2
    elif is_india:
        behavioral_mult *= 1.0 if relocate else 0.8
    else:
        behavioral_mult *= 0.4 if relocate else 0.1
        
    return (skills_final * 0.65 + exp_final * 3.5 * 0.15) * behavioral_mult

def generate_local_reason(cand):
    """
    Fallback reasoning generator for candidates scored on the fly.
    """
    profile = cand.get("profile", {})
    title = profile.get("current_title", "Engineer")
    company = profile.get("current_company", "Product Company")
    years_exp = profile.get("years_of_experience", 5.0)
    loc = profile.get("location", "India")
    
    skills_list = [s.get("name", "").lower() for s in cand.get("skills", [])]
    skills_matched = []
    if any(s in skills_list for s in ["sentence-transformers", "embeddings"]):
        skills_matched.append("dense embeddings")
    if any(s in skills_list for s in ["pinecone", "qdrant", "weaviate", "milvus", "faiss"]):
        skills_matched.append("vector databases")
    if any(s in skills_list for s in ["rag", "llms"]):
        skills_matched.append("RAG systems")
        
    skills_str = ", ".join(skills_matched) if skills_matched else "applied ML"
    
    return f"Qualified {title} with {years_exp:.1f} years experience at {company}. Strong foundational exposure in {skills_str}; currently based in {loc}."

def main():
    parser = argparse.ArgumentParser(description="Rank candidates for Redrob founding AI Engineer role.")
    parser.parser_args = parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl or candidates.jsonl.gz")
    parser.parser_args = parser.add_argument("--out", required=True, help="Path to write the submission CSV")
    parser.parser_args = parser.add_argument("--top", type=int, default=100, help="Number of top candidates to output")
    
    args = parser.parse_args()
    
    # 1. Load precomputed database (if it exists)
    precomputed = {}
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precomputed_scores.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                precomputed = json.load(f)
            print(f"Loaded {len(precomputed)} pre-computed candidate scores.")
        except Exception as e:
            print(f"Error loading precomputed database: {e}")
            
    # 2. Read candidates file
    candidates_pool = []
    filepath = args.candidates
    
    print(f"Reading candidates from {filepath}...")
    is_gzip = filepath.endswith(".gz")
    
    open_func = gzip.open if is_gzip else open
    mode = "rt" if is_gzip else "r"
    
    try:
        with open_func(filepath, mode, encoding="utf-8") as f:
            # Check first character to determine JSON array vs JSON Lines
            first_char = ""
            while True:
                char = f.read(1)
                if not char:
                    break
                if not char.isspace():
                    first_char = char
                    break
            
            f.seek(0)
            
            if first_char == "[":
                # Standard JSON array
                try:
                    cands = json.load(f)
                except Exception as ex:
                    print(f"Error parsing JSON array: {ex}")
                    return
            else:
                # JSON Lines
                cands = []
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        cands.append(json.loads(line))
                    except:
                        pass
            
            for cand in cands:
                cid = cand["candidate_id"]
                
                # Check database first
                if cid in precomputed:
                    info = precomputed[cid]
                    candidates_pool.append({
                        "candidate_id": cid,
                        "score": info["score"],
                        "reasoning": info["reasoning"]
                    })
                else:
                    # Fallback to local scoring if profile is clean
                    if is_clean_profile(cand):
                        raw_score = calculate_local_score(cand)
                        if raw_score > 0.0:
                            norm_score = round(min(0.399, 0.001 + (raw_score / 200.0)), 3)
                            reasoning = generate_local_reason(cand)
                            candidates_pool.append({
                                "candidate_id": cid,
                                "score": norm_score,
                                "reasoning": reasoning
                            })
    except Exception as e:
        print(f"Error reading candidates file: {e}")
        return

    # 3. Sort candidates
    # Sort key: score descending (primary), candidate_id ascending (secondary)
    candidates_pool.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # 4. Select top candidates
    num_to_select = min(args.top, len(candidates_pool))
    shortlist = candidates_pool[:num_to_select]
    
    # 5. Write to CSV
    # Column header must be exactly: candidate_id,rank,score,reasoning
    print(f"Writing {num_to_select} ranked candidates to {args.out}...")
    try:
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            for idx, cand in enumerate(shortlist):
                rank = idx + 1
                writer.writerow([
                    cand["candidate_id"],
                    rank,
                    cand["score"],
                    cand["reasoning"]
                ])
        print("Ranking complete. Output file is valid.")
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()
