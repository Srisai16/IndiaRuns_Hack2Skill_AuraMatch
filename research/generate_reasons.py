import json
import os
import random

def generate_reason(cand, rank):
    # Extract details
    profile = cand["profile"]
    title = cand["title"]
    company = cand["company"]
    years_exp = profile["years_of_experience"]
    loc = profile["location"]
    
    signals = cand["redrob_signals"]
    notice = signals["notice_period_days"]
    github = signals["github_activity_score"]
    
    # Identify matched technical categories
    skills_list = [s["name"].lower() for s in cand["skills"]]
    skills_matched = []
    
    # Look for specific skills
    if any(s in skills_list for s in ["sentence-transformers", "embeddings", "bge", "e5"]):
        skills_matched.append("dense embeddings")
    if any(s in skills_list for s in ["pinecone", "qdrant", "weaviate", "milvus", "faiss"]):
        skills_matched.append("vector databases")
    if any(s in skills_list for s in ["rag", "llms", "fine-tuning", "lora", "qlora"]):
        skills_matched.append("RAG & LLM fine-tuning")
    if any(s in skills_list for s in ["search", "retrieval", "bm25", "hybrid search"]):
        skills_matched.append("hybrid retrieval systems")
    if any(s in skills_list for s in ["ndcg", "mrr", "map", "evaluation"]):
        skills_matched.append("ranking evaluation frameworks")
    if any(s in skills_list for s in ["python"]):
        skills_matched.append("strong Python development")
        
    skills_str = ", ".join(skills_matched[:3])
    if not skills_str:
        skills_str = "applied ML engineering"
        
    # Notice period description
    if notice <= 15:
        notice_str = "available on a very short 15-day notice"
    elif notice <= 30:
        notice_str = "available on a 30-day notice"
    elif notice <= 60:
        notice_str = "on a standard 60-day notice"
    else:
        notice_str = "on a 90-day notice period"
        
    # Location description
    pune_noida = any(p in loc.lower() for p in ["pune", "noida"])
    if pune_noida:
        loc_str = f"based locally in {loc} (ideal for hybrid setup)"
    else:
        if signals.get("willing_to_relocate"):
            loc_str = f"based in {loc} (willing to relocate)"
        else:
            loc_str = f"located in {loc}"
        
    # GitHub signal
    git_str = ""
    if github > 50:
        git_str = f", highly active on GitHub (score {github:.0f})"
    elif github > 20:
        git_str = ", with solid GitHub activity"
        
    # Combine details based on rank
    if rank <= 10:
        templates = [
            f"Exceptional {title} with {years_exp:.1f} years experience at {company}; has hands-on production experience in {skills_str}{git_str}. Currently {loc_str} and {notice_str}.",
            f"Top founding-team fit: {years_exp:.1f} years of experience as {title} at {company}. Strong depth in {skills_str}{git_str}; {loc_str} and {notice_str}.",
            f"Outstanding {title} with {years_exp:.1f} years at {company} shipping applied ML systems. Skilled in {skills_str}; {loc_str} and is {notice_str}."
        ]
        reason = random.choice(templates)
        
    elif rank <= 30:
        templates = [
            f"Strong candidate working as {title} at {company} with {years_exp:.1f} years of experience. Experienced in {skills_str}{git_str}; {loc_str}. Notice period is {notice} days.",
            f"Solid product-company track record ({years_exp:.1f} years exp as {title} at {company}). Demonstrates proficiency in {skills_str}; {loc_str} and is {notice_str}.",
            f"High-quality candidate with {years_exp:.1f} years exp at {company}. Built systems using {skills_str}{git_str}; {loc_str} and is {notice_str}."
        ]
        reason = random.choice(templates)
        
    elif rank <= 70:
        templates = [
            f"{years_exp:.1f} years exp as {title} at {company}; has good foundational experience in {skills_str}. Notice period is {notice} days and candidate is {loc_str}.",
            f"Applied ML professional from {company} with {years_exp:.1f} years of experience. Strong in {skills_str}, notice period is {notice} days, currently {loc_str}.",
            f"Decent profile with {years_exp:.1f} years exp at {company}. Experience covers {skills_str}. Notice is {notice} days, located in {loc}."
        ]
        reason = random.choice(templates)
        
    else:
        templates = [
            f"Adjacent fit: {years_exp:.1f} years exp as {title} at {company}. Covers {skills_str} but notice period is {notice} days; candidate is {loc_str}.",
            f"Candidate with adjacent skills in {skills_str} and {years_exp:.1f} years experience. Notice period is {notice} days, currently {loc_str}.",
            f"Final shortlist candidate: {title} with {years_exp:.1f} years experience at {company}. Experience includes {skills_str}. Notice is {notice} days."
        ]
        reason = random.choice(templates)
        
    # Ensure there's a minor concern acknowledged if notice is long or experience is on the low end
    if notice >= 90 and "notice" not in reason.lower() and "notice_str" not in reason.lower():
        reason += f" Note: notice period of {notice} days is a potential concern."
    elif years_exp < 5.0 and "experience" not in reason.lower() and "yrs" not in reason.lower():
        reason += f" Note: experience ({years_exp:.1f} years) is slightly below our preferred 5-9 years band."
        
    return reason

def generate_reasons_and_save():
    with open("top_candidates_to_review.json", "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    # We will process the top 100 candidates
    top_100 = candidates[:100]
    precomputed = {}
    
    print("Generating reasonings for Top 100 candidates...")
    for i, cand in enumerate(top_100):
        rank = i + 1
        cid = cand["candidate_id"]
        score = cand["score"]
        
        # We normalize score to be between 0.4 and 0.99 for display
        # The highest score gets 0.99, lowest gets 0.4
        max_score = top_100[0]["score"]
        min_score = top_100[-1]["score"]
        norm_score = 0.4 + 0.59 * ((score - min_score) / (max_score - min_score + 1e-6))
        # Ensure it is rounded to 3 decimal places
        norm_score = round(norm_score, 3)
        
        reason = generate_reason(cand, rank)
        precomputed[cid] = {
            "rank": rank,
            "score": norm_score,
            "reasoning": reason
        }
        
    # Check score monotonicity
    scores = [item["score"] for item in precomputed.values()]
    for idx in range(len(scores) - 1):
        if scores[idx] < scores[idx+1]:
            print(f"Warning: Monotonicity violation at index {idx}: {scores[idx]} < {scores[idx+1]}")
            
    # Save the database
    with open("precomputed_scores.json", "w", encoding="utf-8") as f:
        json.dump(precomputed, f, indent=2)
    print("Saved 100 candidates to precomputed_scores.json")
    
    # Print the top 5 reasonings as samples
    print("\n--- SAMPLE REASONINGS ---")
    for cid in list(precomputed.keys())[:5]:
        item = precomputed[cid]
        print(f"Rank {item['rank']} [{cid}] Score {item['score']}: {item['reasoning']}")

if __name__ == "__main__":
    generate_reasons_and_save()
