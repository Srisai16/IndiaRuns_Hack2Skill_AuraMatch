import json
import os
import re

def search_founded():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    print("Searching for 'founded' or 'established' in career descriptions...")
    matches = []
    pattern = re.compile(r"\b(founded|established)\b", re.IGNORECASE)
    
    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            cand_id = cand["candidate_id"]
            
            for job in cand.get("career_history", []):
                desc = job.get("description", "")
                company = job.get("company", "")
                duration_months = job.get("duration_months", 0)
                
                if pattern.search(desc):
                    sentences = re.split(r'[.!?]', desc)
                    for s in sentences:
                        if pattern.search(s):
                            matches.append({
                                "id": cand_id,
                                "company": company,
                                "duration_months": duration_months,
                                "sentence": s.strip()
                            })
                            
    print(f"Found {len(matches)} occurrences of 'founded' or 'established':")
    for m in matches[:10]:
        print(f"ID: {m['id']}, Company: {m['company']}, Dur: {m['duration_months']} months")
        print(f"  Sentence: {m['sentence']}")

if __name__ == "__main__":
    search_founded()
