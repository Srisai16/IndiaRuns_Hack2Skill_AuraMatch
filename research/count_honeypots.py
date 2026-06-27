import json
import os
from datetime import datetime

def count_honeypots():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    print("Scanning all 100,000 candidates for honeypots...")
    total = 0
    honeypots = []
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            total += 1
            cand_id = cand["candidate_id"]
            
            is_honeypot = False
            reasons = []
            
            # 1. Salary conflict
            sal = cand.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
            sal_min = sal.get("min")
            sal_max = sal.get("max")
            if sal_min is not None and sal_max is not None:
                if sal_min > sal_max:
                    is_honeypot = True
                    reasons.append(f"Salary min ({sal_min}) > max ({sal_max})")
            
            # 2. Skill duration vs proficiency conflict
            bad_skills_count = 0
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    bad_skills_count += 1
            if bad_skills_count >= 5: # Let's see if 5 is the threshold
                is_honeypot = True
                reasons.append(f"Expert/Advanced skills with 0 duration ({bad_skills_count} skills)")
                
            # 3. Job duration vs actual dates conflict
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
                            end_date = datetime(2026, 6, 26) # Reference date for active jobs
                            
                        max_possible_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                        if dur > max_possible_months + 3:
                            is_honeypot = True
                            reasons.append(f"Worked {dur} months at {company} but the date range only allows {max_possible_months} months")
                    except Exception as e:
                        pass
                        
            # 4. Experience vs Job History duration conflict
            # Let's check if the candidate has years_of_experience in profile which matches
            # but has a single job that is much longer than total years_of_experience
            years_exp = cand.get("profile", {}).get("years_of_experience", 0)
            for job in cand.get("career_history", []):
                dur_years = job.get("duration_months", 0) / 12.0
                # If a single job duration is longer than the total years of experience by more than 1 year
                if dur_years > years_exp + 1.0:
                    is_honeypot = True
                    reasons.append(f"Single job duration ({dur_years:.1f} years) exceeds profile total experience ({years_exp:.1f} years)")

            if is_honeypot:
                honeypots.append({
                    "id": cand_id,
                    "name": cand["profile"]["anonymized_name"],
                    "reasons": reasons
                })

    print(f"Total candidates scanned: {total}")
    print(f"Total honeypots detected: {len(honeypots)}")
    
    print("\nFirst 10 honeypots detected:")
    for hp in honeypots[:10]:
        print(f"ID: {hp['id']}, Name: {hp['name']}, Reasons: {hp['reasons']}")
        
    # Save the honeypot IDs to a file so we can exclude them easily
    with open("honeypot_ids.json", "w") as f:
        json.dump([hp["id"] for hp in honeypots], f, indent=2)
    print("Saved honeypot IDs to honeypot_ids.json")

if __name__ == "__main__":
    count_honeypots()
