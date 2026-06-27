# AuraMatch — Intelligent Sourcing & Talent Matching Engine

AuraMatch is a modern, state-managed, multi-page recruitment and talent sourcing application designed to move from keyword-based candidate filtering to deep semantic human intelligence. 

Developed by **SRISAI SHIVAKOTI**, this platform solves the limitations of traditional recruitment by treating sourcing as a multi-dimensional graph and alignment problem. It evaluates candidates by career trajectory, behavioral signals, deep competency graphs, and profile integrity.

**Live Application URL**: [https://auramatch.streamlit.app/](https://auramatch.streamlit.app/)

---

## 🌟 Interactive Platform Tour

### 1. Interactive Sourcing Landing Page
![AuraMatch Landing Page](docs/AuraMatch-AI-Recruiter-·-Streamlit-1.png)
*The landing page introduces AuraMatch's semantic approach to talent matching and features an interactive technical skill equivalency simulator for quick validation.*

---

### 2. Secure Login & Enterprise SSO
![AuraMatch Login Screen](docs/AuraMatch-AI-Recruiter-·-Streamlit-2.png)
*Recruiters can log in securely using traditional password authentication or single-click simulated Google and Microsoft Single Sign-On (SSO).*

---

### 3. Recruiter Sourcing Dashboard
![AuraMatch Dashboard](docs/AuraMatch-AI-Recruiter-·-Streamlit-3.png)
*The primary workspace displaying global candidate metrics, verified vs flagged profiles, notice periods, and expected compensation spreads.*

---

### 4. Interactive ATS Resume Analyzer & Live Coach
![AuraMatch ATS Analyzer](docs/AuraMatch-AI-Recruiter-·-Streamlit-4.png)
*Recruiters can paste any custom Job Description and candidate resume to instantly analyze compatibility scores, matched capabilities, and skill gaps.*

---

### 5. AI Sourcing & Custom JD Calibration
![AuraMatch JD Calibration](docs/AuraMatch-AI-Recruiter-·-Streamlit-5.png)
*Displays the AI Sourcing calibration card where the parser dynamically scans and understands pasted JDs, automatically calibrating target experience bands and technology stacks.*

---

### 6. Candidate Side-by-Side Comparison
![AuraMatch Side-by-Side Comparison](docs/AuraMatch-AI-Recruiter-·-Streamlit-6.png)
*Allows recruiters to perform a granular, side-by-side comparison of any two candidates across all tech stacks, notice periods, salaries, and scores.*

---

## 🛠️ Project Structure
```
├── app.py                     # Main multi-page Streamlit application code
├── rank.py                    # Production ranking execution script for all 100,000 profiles
├── precomputed_scores.json    # Precomputed top 100 lookup scores and reasoning database
├── profile.png                # Developer profile image
├── VectorVanguard.csv         # Final ranked output submission file (Top 100)
├── requirements.txt           # Python application dependencies
├── data/                      # Sample datasets
│   └── sample_candidates.json # 50 profiles for cloud demonstration
├── docs/                      # Screenshot documentation
│   ├── AuraMatch-AI-Recruiter-·-Streamlit-1.png
│   ├── AuraMatch-AI-Recruiter-·-Streamlit-2.png
│   ├── AuraMatch-AI-Recruiter-·-Streamlit-3.png
│   ├── AuraMatch-AI-Recruiter-·-Streamlit-4.png
│   ├── AuraMatch-AI-Recruiter-·-Streamlit-5.png
│   └── AuraMatch-AI-Recruiter-·-Streamlit-6.png
├── .gitignore                 # Excludes raw data, system cache, and temp files
└── README.md                  # Project documentation (this file)
```

---

## 🚀 Local Setup & Execution

### 1. Prerequisites
Ensure you have Python 3.8+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Interactive Web Portal
```bash
streamlit run app.py
```
This will open the web interface in your browser at `http://localhost:8501`.

### 4. Run the Production Sourcing Script
To regenerate the final submission CSV from your raw candidate pool:
```bash
python rank.py --candidates ./candidates.jsonl --out ./VectorVanguard.csv
```

---

## 👥 Team: VectorVanguard
* **Primary Contact**: SRISAI SHIVAKOTI
* **Role**: Lead AI Engineer / Developer
