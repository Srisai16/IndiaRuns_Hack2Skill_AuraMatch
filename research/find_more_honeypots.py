import json
import os
from datetime import datetime

def find_anomalies():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    edu_date_flips = []
    signup_active_flips = []
    exp_history_mismatch = []
    zero_dur_any = []
    zero_dur_3plus = []
    
    total = 0
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            total += 1
            cand_id = cand["candidate_id"]
            
            # 1. Edu dates flip
            for edu in cand.get("education", []):
                s = edu.get("start_year")
                e = edu.get("end_year")
                if s and e and s > e:
                    edu_date_flips.append((cand_id, f"Edu start {s} > end {e}"))
            
            # 2. Signup vs active date
            signup_str = cand.get("redrob_signals", {}).get("signup_date")
            active_str = cand.get("redrob_signals", {}).get("last_active_date")
            if signup_str and active_str:
                try:
                    signup_dt = datetime.strptime(signup_str, "%Y-%m-%d")
                    active_dt = datetime.strptime(active_str, "%Y-%m-%d")
                    if signup_dt > active_dt:
                        signup_active_flips.append((cand_id, f"Signup {signup_str} > Active {active_str}"))
                except:
                    pass
            
            # 3. Exp vs history mismatch
            years_exp = cand.get("profile", {}).get("years_of_experience", 0)
            history = cand.get("career_history", [])
            if years_exp > 0 and len(history) == 0:
                exp_history_mismatch.append((cand_id, f"Has {years_exp} years exp but 0 history items"))
            elif years_exp == 0 and len(history) > 0:
                # check if any history item has duration > 0
                has_dur = any(job.get("duration_months", 0) > 0 for job in history)
                if has_dur:
                    exp_history_mismatch.append((cand_id, "Has 0 years exp but has jobs with duration > 0"))
                    
            # 4. Zero duration skills
            zero_dur_count = 0
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    zero_dur_count += 1
            if zero_dur_count >= 1:
                zero_dur_any.append((cand_id, zero_dur_count))
            if zero_dur_count >= 3:
                zero_dur_3plus.append((cand_id, zero_dur_count))

    print(f"Total candidates: {total}")
    print(f"Education date flips (start > end): {len(edu_date_flips)}")
    print(f"Signup vs active date flips (signup > active): {len(signup_active_flips)}")
    print(f"Exp vs history mismatches: {len(exp_history_mismatch)}")
    print(f"Candidates with any zero-duration expert/adv skill: {len(zero_dur_any)}")
    print(f"Candidates with >=3 zero-duration expert/adv skills: {len(zero_dur_3plus)}")
    
    print("\nEducation flips examples:")
    for x in edu_date_flips[:5]:
        print(f"  {x[0]}: {x[1]}")
        
    print("\nSignup flips examples:")
    for x in signup_active_flips[:5]:
        print(f"  {x[0]}: {x[1]}")

if __name__ == "__main__":
    find_anomalies()
