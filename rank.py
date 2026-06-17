#!/usr/bin/env python3
import json
import csv
import datetime
import argparse
import sys

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def is_honeypot(c):
    # Check A: zero duration expert/advanced skills
    for s in c.get('skills', []):
        if s.get('proficiency') in ['advanced', 'expert'] and s.get('duration_months', 0) == 0:
            return True
            
    # Check B: job duration mismatch
    career = c.get('career_history', [])
    current_date = datetime.date(2026, 6, 16)
    for job in career:
        start_str = job.get('start_date')
        end_str = job.get('end_date')
        reported_months = job.get('duration_months', 0)
        
        start = parse_date(start_str)
        end = parse_date(end_str) if end_str else None
        if not end and job.get('is_current'):
            end = current_date
            
        if start and end:
            days = (end - start).days
            actual_months = round(days / 30.44)
            if abs(actual_months - reported_months) > 2:
                return True
                
    # Check C: claimed vs actual experience mismatch
    claimed_years = c['profile'].get('years_of_experience', 0)
    total_months = sum(job.get('duration_months', 0) for job in career)
    total_years = total_months / 12.0
    if abs(claimed_years - total_years) > 1.5:
        return True
        
    return False

def compute_scores(c):
    # Stage 3: Strict Honeypot Filtering
    if is_honeypot(c):
        return None
        
    # Anti-gaming: Check keyword stuffing for trend skills
    trend_skills = {"llm", "rag", "gpt", "openai", "langchain", "faiss", "vector database", "vector db", "embeddings", "pinecone", "weaviate", "qdrant", "milvus"}
    skills_list = c.get('skills', [])
    skills_lower = [s['name'].lower() for s in skills_list]
    claimed_trends = [s for s in skills_lower if any(t in s for t in trend_skills)]
    
    profile_text = c['profile'].get('summary', '').lower() + ' ' + c['profile'].get('headline', '').lower()
    for job in c.get('career_history', []):
        profile_text += ' ' + job.get('description', '').lower()
        profile_text += ' ' + job.get('title', '').lower()
        
    trust_score = 1.0
    evidence_ratio = 1.0
    if claimed_trends:
        evidenced_trends = sum(1 for t in claimed_trends if t in profile_text)
        evidence_ratio = evidenced_trends / len(claimed_trends)
        if evidence_ratio < 0.25:
            # Scale down trust score to limit ranking potential of stuffing profiles
            trust_score = max(0.5, evidence_ratio * 4.0)

    # 1. Skill Match (embeddings, vector db, python, evaluation)
    emb_kws = ["embedding", "retrieval", "sentence-transformer", "bge", "e5", "dense retrieval", "hybrid search", "nlp", "information retrieval"]
    vdb_kws = ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "vector database", "vector db"]
    py_kws = ["python", "pyspark"]
    eval_kws = ["ndcg", "mrr", "map", "evaluation", "ab test", "a/b test", "eval framework", "experimentation"]
    
    pref_kws = {
        'fine_tuning': ["fine-tuning", "fine-tune", "lora", "qlora", "peft"],
        'ltr': ["learning-to-rank", "learning to rank", "xgboost", "lightgbm", "neural ranking"],
        'hr_tech': ["hr-tech", "hr tech", "recruiting", "talent intelligence", "marketplace"],
        'distributed': ["distributed systems", "inference optimization", "triton", "onnx", "tensorrt"],
        'open_source': ["open-source", "open source"]
    }
    
    def check_category(keywords):
        max_prof = 0.0
        for s in skills_list:
            s_name = s['name'].lower()
            if any(kw in s_name for kw in keywords):
                prof = s.get('proficiency', 'beginner').lower()
                val = 0.4
                if prof == 'intermediate': val = 0.6
                elif prof == 'advanced': val = 0.8
                elif prof == 'expert': val = 1.0
                max_prof = max(max_prof, val)
        if any(kw in profile_text for kw in keywords):
            max_prof = max(max_prof, 0.5)
        return max_prof
        
    skill_emb = check_category(emb_kws)
    skill_vdb = check_category(vdb_kws)
    skill_py = check_category(py_kws)
    skill_eval = check_category(eval_kws)
    
    core_skill = (skill_emb + skill_vdb + skill_py + skill_eval) / 4.0
    
    pref_bonus = 0.0
    for category, keywords in pref_kws.items():
        if check_category(keywords) > 0.0:
            pref_bonus += 0.05
    pref_bonus = min(0.20, pref_bonus)
    
    skill_score = core_skill + pref_bonus
    if claimed_trends:
        skill_score = skill_score * (0.5 + 0.5 * evidence_ratio)
    skill_score = min(1.0, max(0.0, skill_score))
    
    # 2. Experience Fit (target 5-9 years, ideal 6-8 years)
    years = c['profile'].get('years_of_experience', 0)
    if 6.0 <= years <= 8.0:
        base_exp = 1.0
    elif 5.0 <= years < 6.0:
        base_exp = 0.8 + (years - 5.0) * 0.2
    elif 8.0 < years <= 9.0:
        base_exp = 1.0 - (years - 8.0) * 0.2
    elif years < 5.0:
        base_exp = max(0.0, years / 5.0 * 0.6)
    else:
        base_exp = max(0.0, 1.0 - (years - 8.0) * 0.15)
        
    # Applied ML experience duration estimation
    ml_kws = ["machine learning", "ml", "nlp", "computer vision", "cv", "deep learning", "data scientist", "search", "retrieval", "recommendation"]
    ml_months = 0
    for job in c.get('career_history', []):
        j_title = job.get('title', '').lower()
        j_desc = job.get('description', '').lower()
        if any(kw in j_title or kw in j_desc for kw in ml_kws):
            ml_months += job.get('duration_months', 0)
    ml_years = ml_months / 12.0
    ml_factor = min(1.0, ml_years / 4.0)
    
    exp_score = base_exp * 0.6 + ml_factor * 0.4
    
    # Disqualifier check: large consultancies only
    consultancies = {'tcs', 'infosys', 'wipro', 'accenture', 'cognizant', 'capgemini', 'l&t', 'wipro technologies', 'tata consultancy services', 'cognizant technology solutions'}
    companies = [job.get('company', '').lower() for job in c.get('career_history', [])]
    if companies and all(any(con in comp for con in consultancies) for comp in companies):
        exp_score *= 0.1
        
    # Disqualifier check: academic research only
    titles = [job.get('title', '').lower() for job in c.get('career_history', [])]
    is_pure_research = titles and all('research' in t or 'academic' in t or 'student' in t or 'postdoc' in t for t in titles)
    if is_pure_research:
        exp_score *= 0.3
        
    # Penalty check: title chasers
    num_jobs = len(c.get('career_history', []))
    total_months = sum(job.get('duration_months', 0) for job in c.get('career_history', []))
    avg_tenure = total_months / num_jobs if num_jobs > 0 else 0
    if avg_tenure < 18 and any(any(title in t for title in ['staff', 'principal', 'lead']) for t in titles):
        exp_score *= 0.8
        
    exp_score = min(1.0, max(0.0, exp_score))

    # 3. Behavioral Score
    sig = c.get('redrob_signals', {})
    completeness = sig.get('profile_completeness_score', 0) / 100.0
    open_to_work = 1.0 if sig.get('open_to_work_flag') else 0.6
    resp_rate = sig.get('recruiter_response_rate', 0.0)
    
    resp_time = sig.get('avg_response_time_hours', 0.0)
    resp_time_score = max(0.0, 1.0 - resp_time / 168.0)
    
    github = sig.get('github_activity_score', 0.0)
    github_score = 0.3 if github == -1 else github / 100.0
    
    completion = sig.get('interview_completion_rate', 0.0)
    
    acceptance = sig.get('offer_acceptance_rate', 0.0)
    acceptance_score = 0.7 if acceptance == -1 else acceptance
    
    active_date = parse_date(sig.get('last_active_date'))
    current_date = datetime.date(2026, 6, 16)
    days_inactive = (current_date - active_date).days if active_date else 365
    if days_inactive <= 30:
        activity_factor = 1.0
    else:
        # Penalize if inactive for more than a month (6 months inactivity sets this to 0.0)
        activity_factor = max(0.0, 1.0 - (days_inactive - 30) / 150.0)
        
    verifications = 0.0
    if sig.get('verified_email'): verifications += 0.02
    if sig.get('verified_phone'): verifications += 0.02
    if sig.get('linkedin_connected'): verifications += 0.01
    
    beh_score = (
        resp_rate * 0.25 +
        activity_factor * 0.25 +
        completion * 0.15 +
        open_to_work * 0.10 +
        github_score * 0.10 +
        completeness * 0.05 +
        acceptance_score * 0.05 +
        verifications
    )
    beh_score = min(1.0, max(0.0, beh_score))

    # 4. Startup Fit
    startup_sizes = ["1-10", "11-50", "51-200"]
    max_size_score = 0.3
    for job in c.get('career_history', []):
        size = job.get('company_size', '')
        if size in startup_sizes:
            max_size_score = max(max_size_score, 1.0)
        elif size in ["201-500", "501-1000"]:
            max_size_score = max(max_size_score, 0.7)
            
    has_founding = any(any(kw in t for kw in ['founder', 'co-founder', 'founding', 'chief', 'cto']) for t in titles)
    founding_bonus = 0.2 if has_founding else 0.0
    
    scrappy_text = any(kw in profile_text for kw in ['startup', 'velocity', 'scrappy', 'shipping', 'ownership'])
    scrappy_bonus = 0.1 if scrappy_text else 0.0
    
    startup_score = min(1.0, max_size_score + founding_bonus + scrappy_bonus)

    # 5. Location Fit
    loc = c['profile'].get('location', '').lower()
    country = c['profile'].get('country', '').lower()
    willing = sig.get('willing_to_relocate', False)
    
    foreign_cities = ['toronto', 'austin', 'sydney', 'london', 'seattle', 'sf', 'san francisco', 'vancouver', 'melbourne', 'berlin', 'new york', 'boston', 'chicago']
    if country != 'india' or any(fc in loc for fc in foreign_cities):
        loc_score = 0.1
    else:
        if 'noida' in loc or 'pune' in loc:
            loc_score = 1.0
        elif any(c in loc for c in ['delhi', 'ncr', 'gurgaon', 'gurugram', 'ghaziabad', 'faridabad', 'hyderabad', 'mumbai', 'bangalore', 'bengaluru']):
            loc_score = 0.9 if willing else 0.8
        else:
            loc_score = 0.7 if willing else 0.3
            
    final_score = (
        0.35 * skill_score +
        0.25 * exp_score +
        0.20 * beh_score +
        0.10 * startup_score +
        0.10 * loc_score
    )
    
    adjusted_score = final_score * trust_score
    return {
        'candidate_id': c['candidate_id'],
        'name': c['profile']['anonymized_name'],
        'title': c['profile']['current_title'],
        'company': c['profile']['current_company'],
        'location_raw': c['profile'].get('location', ''),
        'years': years,
        'skill_score': skill_score,
        'exp_score': exp_score,
        'beh_score': beh_score,
        'startup_score': startup_score,
        'loc_score': loc_score,
        'trust_score': trust_score,
        'adjusted_score': adjusted_score,
        'response_rate': resp_rate,
        'skill_emb': skill_emb,
        'skill_vdb': skill_vdb,
        'skill_py': skill_py,
        'skill_eval': skill_eval,
        'notice_period': sig.get('notice_period_days', 0)
    }

def generate_reasoning(sc, rank):
    title = sc['title']
    company = sc['company']
    years = sc['years']
    resp_rate = sc['response_rate']
    loc_score = sc['loc_score']
    loc_raw = sc['location_raw']
    notice = sc['notice_period']
    
    skills_matched = []
    if sc['skill_emb'] > 0: skills_matched.append("retrieval/embeddings")
    if sc['skill_vdb'] > 0: skills_matched.append("vector databases")
    if sc['skill_py'] > 0: skills_matched.append("Python coding")
    if sc['skill_eval'] > 0: skills_matched.append("ranking evaluation")
    
    skills_str = ", ".join(skills_matched[:3])
    
    # Sentence 1: Title, experience, and current company
    s1 = f"{title} with {years:.1f} years of experience, currently at {company}."
    
    # Sentence 2: Skill Fit
    if skills_matched:
        s2 = f"Demonstrates strong technical expertise in {skills_str}, fitting the core systems architecture outlined in the JD."
    else:
        s2 = "Brings solid engineering fundamentals with adjacent AI/ML interest."
        
    # Sentence 3: Availability / Location / Gaps
    if loc_score == 1.0:
        loc_str = f"based in preferred hub {loc_raw}"
    elif loc_score >= 0.8:
        loc_str = f"located in {loc_raw} (Tier-1 hub, relocation willing)"
    else:
        loc_str = f"currently based in {loc_raw}"
        
    s3 = f"Highly active with a {resp_rate*100:.0f}% response rate, is {loc_str}, and has a {notice}-day notice period."
    
    reasoning = f"{s1} {s2} {s3}"
    return reasoning

def main():
    parser = argparse.ArgumentParser(description="AI Candidate Ranking System")
    parser.add_argument("--candidates", default="./candidates.jsonl", help="Path to candidates JSONL dataset")
    parser.add_argument("--out", default="./submission.csv", help="Path to output submission CSV file")
    args = parser.parse_args()
    
    print(f"Reading candidates from {args.candidates}...")
    scored = []
    count = 0
    try:
        with open(args.candidates, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                sc = compute_scores(c)
                if sc:
                    scored.append(sc)
                count += 1
                if count % 25000 == 0:
                    print(f"Processed {count} records...")
    except Exception as e:
        print(f"Error reading candidates file: {e}")
        sys.exit(1)
        
    # Sort candidates:
    # 1. descending by rounded adjusted_score (to match 4 decimal places in CSV)
    # 2. tie-break: ascending by candidate_id (required by validator)
    scored.sort(key=lambda x: (-round(x['adjusted_score'], 4), x['candidate_id']))
    
    # Take Top 100
    top_100 = scored[:100]
    
    print(f"Writing exactly {len(top_100)} top candidates to {args.out}...")
    try:
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            
            for i, sc in enumerate(top_100):
                rank = i + 1
                score_str = f"{sc['adjusted_score']:.4f}"
                reasoning = generate_reasoning(sc, rank)
                writer.writerow([sc['candidate_id'], rank, score_str, reasoning])
                
        print("Done! Submission generated successfully.")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
