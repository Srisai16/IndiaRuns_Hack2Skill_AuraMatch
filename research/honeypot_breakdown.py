import json
import os
from datetime import datetime

def breakdown():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    salary_flips = 0
    zero_dur_expert_count = 0
    job_dur_mismatches = 0
    job_longer_than_total_exp = 0
    multi_conflicts = 0
    
    total = 0
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            total += 1
            
            reasons = []
            
            # 1. Salary
            sal = cand.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
            sal_min = sal.get("min")
            sal_max = sal.get("max")
            if sal_min is not None and sal_max is not None and sal_min > sal_max:
                salary_flips += 1
                reasons.append("salary")
                
            # 2. Skill duration
            bad_skills_count = 0
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    bad_skills_count += 1
            if bad_skills_count >= 5:
                zero_dur_expert_count += 1
                reasons.append("zero_dur")
                
            # 3. Job duration vs dates
            job_mismatch = False
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
                            end_date = datetime(2026, 6, 26)
                        max_possible_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                        if dur > max_possible_months + 3:
                            job_mismatch = True
                    except:
                        pass
            if job_mismatch:
                job_dur_mismatches += 1
                reasons.append("job_dur")
                
            # 4. Job longer than total experience
            exp_conflict = False
            years_exp = cand.get("profile", {}).get("years_of_experience", 0)
            for job in cand.get("career_history", []):
                dur_years = job.get("duration_months", 0) / 12.0
                if dur_years > years_exp + 1.0:
                    exp_conflict = True
            if exp_conflict:
                job_longer_than_total_exp += 1
                reasons.append("job_exp")
                
            if len(reasons) > 1:
                multi_conflicts += 1
                
    print(f"Scanned {total} candidates.")
    print(f"Salary flips (min > max): {salary_flips}")
    print(f"Zero duration expert skills (>=5): {zero_dur_expert_count}")
    print(f"Job duration vs dates mismatches: {job_dur_mismatches}")
    print(f"Job duration longer than total experience: {job_longer_than_total_exp}")
    print(f"Candidates with multiple conflicts: {multi_conflicts}")

if __name__ == "__main__":
    breakdown()
