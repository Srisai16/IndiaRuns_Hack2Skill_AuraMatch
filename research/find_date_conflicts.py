import json
import os
from datetime import datetime

def inspect_conflicts():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    print("Scanning for logical and date conflicts in candidates...")
    count = 0
    duration_mismatch = []
    chronology_errors = []
    zero_duration_skills = []
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            count += 1
            cand_id = cand["candidate_id"]
            
            # 1. Check skill duration vs proficiency
            zero_dur_expert = 0
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    zero_dur_expert += 1
            if zero_dur_expert >= 3:
                zero_duration_skills.append((cand_id, zero_dur_expert))
            
            # 2. Check career history dates vs duration_months
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
                            # Assume current date is around June 2026 for active jobs
                            end_date = datetime(2026, 6, 26)
                        
                        # Calculate expected duration in months
                        expected_dur = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                        # Allow some small buffer (e.g., 2 months)
                        if abs(expected_dur - dur) > 3:
                            duration_mismatch.append({
                                "id": cand_id,
                                "company": job.get("company"),
                                "start": start_str,
                                "end": end_str,
                                "listed_dur": dur,
                                "calculated_dur": expected_dur
                            })
                    except Exception as e:
                        pass
            
            # 3. Check chronology (e.g. starting a job years before university start)
            edu_starts = [e.get("start_year") for e in cand.get("education", []) if e.get("start_year")]
            if edu_starts:
                earliest_edu_year = min(edu_starts)
                for job in cand.get("career_history", []):
                    start_str = job.get("start_date")
                    if start_str:
                        start_year = int(start_str.split("-")[0])
                        # If a candidate started a job more than 5 years before starting university
                        if earliest_edu_year - start_year > 5:
                            chronology_errors.append({
                                "id": cand_id,
                                "earliest_edu": earliest_edu_year,
                                "job_start": start_year,
                                "company": job.get("company")
                            })
                            
            if count >= 20000: # Scan first 20K candidates for samples
                break
                
    print(f"Scanned {count} candidates.")
    print(f"Found {len(zero_duration_skills)} candidates with >=3 zero-duration expert/advanced skills.")
    print(f"Found {len(duration_mismatch)} job duration mismatches.")
    print(f"Found {len(chronology_errors)} chronology errors.")
    
    print("\n--- Example Job Duration Mismatches ---")
    for m in duration_mismatch[:5]:
        print(f"ID: {m['id']}, Company: {m['company']}, Listed Dur: {m['listed_dur']}, Calculated Dur: {m['calculated_dur']} (Dates: {m['start']} to {m['end']})")
        
    print("\n--- Example Chronology Errors ---")
    for ce in chronology_errors[:5]:
        print(f"ID: {ce['id']}, Earliest Edu Year: {ce['earliest_edu']}, Job Start Year: {ce['job_start']}, Company: {ce['company']}")

if __name__ == "__main__":
    inspect_conflicts()
