import json
import os
import re

def inspect():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    print("Scanning all 100,000 candidates for honeypot indicators...")
    count = 0
    zero_duration_honeypots = []
    date_conflict_honeypots = []
    
    # We want to search for terms like "founded" in descriptions
    founded_pattern = re.compile(r"founded\s+(\d+)\s+years?\s+ago|founded\s+in\s+(\d{4})", re.IGNORECASE)
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            count += 1
            cand_id = cand["candidate_id"]
            
            # Check 1: "expert" or "advanced" proficiency in skills with 0 duration
            # Let's count how many such skills there are
            bad_skills = []
            for skill in cand.get("skills", []):
                dur = skill.get("duration_months", 0)
                prof = skill.get("proficiency", "")
                if prof in ["expert", "advanced"] and dur == 0:
                    bad_skills.append((skill.get("name"), prof))
                    
            if len(bad_skills) >= 5: # Threshold of 5 or more
                zero_duration_honeypots.append({
                    "id": cand_id,
                    "name": cand["profile"]["anonymized_name"],
                    "bad_skills": bad_skills
                })
                
            # Check 2: Date conflict (worked longer than company existed)
            # Let's check descriptions for "founded X years ago" or "founded in YYYY"
            for job in cand.get("career_history", []):
                desc = job.get("description", "")
                company = job.get("company", "")
                duration_months = job.get("duration_months", 0)
                start_date_str = job.get("start_date", "")
                
                # Check 2.1: founded X years ago
                # e.g., "founded 3 years ago"
                m1 = re.search(r"founded\s+(\d+)\s+years?\s+ago", desc, re.IGNORECASE)
                if m1:
                    years_ago = int(m1.group(1))
                    # If job duration is greater than company age (years_ago * 12)
                    if duration_months > (years_ago * 12):
                        date_conflict_honeypots.append({
                            "id": cand_id,
                            "reason": f"Worked {duration_months} months at {company} which was founded only {years_ago} years ago.",
                            "desc": desc
                        })
                        
                # Check 2.2: founded in YYYY
                m2 = re.search(r"founded\s+in\s+(\d{4})", desc, re.IGNORECASE)
                if m2:
                    year_founded = int(m2.group(1))
                    if start_date_str:
                        start_year = int(start_date_str.split("-")[0])
                        if start_year < year_founded:
                            date_conflict_honeypots.append({
                                "id": cand_id,
                                "reason": f"Started working in {start_year} at {company} which was founded later in {year_founded}.",
                                "desc": desc
                            })
                            
    print(f"Scanned {count} candidates.")
    print(f"Found {len(zero_duration_honeypots)} zero-duration skill honeypots.")
    print(f"Found {len(date_conflict_honeypots)} date conflict honeypots.")
    
    print("\n--- Example Zero Duration Honeypots (Top 5) ---")
    for hp in zero_duration_honeypots[:5]:
        print(f"ID: {hp['id']}, Name: {hp['name']}, Bad Skills count: {len(hp['bad_skills'])}")
        print(f"  Skills: {hp['bad_skills']}")
        
    print("\n--- Example Date Conflict Honeypots (Top 5) ---")
    for hp in date_conflict_honeypots[:5]:
        print(f"ID: {hp['id']}, Reason: {hp['reason']}")
        print(f"  Desc: {hp['desc']}")

if __name__ == "__main__":
    inspect()
