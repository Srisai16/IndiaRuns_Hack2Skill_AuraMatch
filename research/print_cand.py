import json
import os

def print_cand():
    candidates_file = r"S:\IndiaRuns_Hack2Skill\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
    if not os.path.exists(candidates_file):
        print("Candidates file not found.")
        return

    with open(candidates_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            cand = json.loads(line)
            if cand["candidate_id"] == "CAND_0007353":
                print(json.dumps(cand, indent=2))
                break

if __name__ == "__main__":
    print_cand()
