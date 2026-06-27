import json
import os
from datetime import datetime

def find_strict_honeypots():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    honeypots = {}
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            cand_id = cand["candidate_id"]
            
            reasons = []
            
            # 1. Zero duration skills for expert/advanced
            # Let's count how many skills have duration == 0 and proficiency in ['expert', 'advanced']
            zero_dur_expert_skills = []
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    zero_dur_expert_skills.append(skill.get("name"))
            if len(zero_dur_expert_skills) >= 3: # Threshold of 3 or more
                reasons.append(f"Zero duration expert/advanced skills ({len(zero_dur_expert_skills)}): {zero_dur_expert_skills}")
                
            # 2. Job duration vs dates mismatch
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
                            end_date = datetime(2026, 6, 26)
                        max_possible_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                        if dur > max_possible_months + 3:
                            reasons.append(f"Worked {dur} months at {company} but dates allow max {max_possible_months}")
                    except Exception as e:
                        pass
                        
            # 3. Job duration longer than total experience
            years_exp = cand.get("profile", {}).get("years_of_experience", 0)
            for job in cand.get("career_history", []):
                dur_years = job.get("duration_months", 0) / 12.0
                if dur_years > years_exp + 1.0:
                    reasons.append(f"Job at {job.get('company')} is {dur_years:.1f} years, exceeding total exp of {years_exp:.1f} years")
            
            # 4. Mismatch in total experience vs dates
            # If the sum of all non-overlapping job durations is significantly greater than years_of_experience
            # or if years_of_experience is 0 but they have job history
            
            if reasons:
                honeypots[cand_id] = reasons
                
    print(f"Total strict honeypots found: {len(honeypots)}")
    
    # Save the strict honeypot IDs
    with open("strict_honeypots.json", "w") as f:
        json.dump(honeypots, f, indent=2)
    print("Saved to strict_honeypots.json")
    
    # Print the first 20 honeypots
    for i, (cid, rlist) in enumerate(list(honeypots.items())[:20]):
        print(f"{i+1}. {cid}: {rlist}")

if __name__ == "__main__":
    find_strict_honeypots()
