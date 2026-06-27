import json
import os
from datetime import datetime

def find_logical_mismatches():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    start_after_end = []
    exp_sum_mismatch_high = []
    exp_sum_mismatch_low = []
    
    total = 0
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            total += 1
            cand_id = cand["candidate_id"]
            
            # 1. Job start > end date
            for job in cand.get("career_history", []):
                s_str = job.get("start_date")
                e_str = job.get("end_date")
                if s_str and e_str:
                    try:
                        s_dt = datetime.strptime(s_str, "%Y-%m-%d")
                        e_dt = datetime.strptime(e_str, "%Y-%m-%d")
                        if s_dt > e_dt:
                            start_after_end.append((cand_id, f"Job start {s_str} > end {e_str}"))
                    except:
                        pass
            
            # 2. Sum of job durations vs years_of_experience
            years_exp = cand.get("profile", {}).get("years_of_experience", 0)
            sum_dur_months = sum(job.get("duration_months", 0) for job in cand.get("career_history", []))
            sum_dur_years = sum_dur_months / 12.0
            
            # Allow some discrepancy, but if it is extreme:
            # If sum of durations is much larger than profile years_of_experience (e.g. 5+ years larger)
            if sum_dur_years > years_exp + 5.0:
                exp_sum_mismatch_high.append((cand_id, f"Sum of job durations ({sum_dur_years:.1f} years) exceeds profile experience ({years_exp:.1f} years)"))
            # If profile experience is much larger than sum of durations (e.g. 5+ years larger)
            elif years_exp > sum_dur_years + 5.0:
                exp_sum_mismatch_low.append((cand_id, f"Profile experience ({years_exp:.1f} years) exceeds sum of job durations ({sum_dur_years:.1f} years)"))
                
    print(f"Total candidates scanned: {total}")
    print(f"Job start date > end date: {len(start_after_end)}")
    print(f"Sum of durations > Profile exp + 5 years: {len(exp_sum_mismatch_high)}")
    print(f"Profile exp > Sum of durations + 5 years: {len(exp_sum_mismatch_low)}")
    
    print("\nJob start > end examples:")
    for x in start_after_end[:5]:
        print(f"  {x[0]}: {x[1]}")
        
    print("\nSum of durations high mismatch examples:")
    for x in exp_sum_mismatch_high[:5]:
        print(f"  {x[0]}: {x[1]}")

if __name__ == "__main__":
    find_logical_mismatches()
