# AuraMatch — Intelligent Sourcing & Talent Matching Engine

AuraMatch is a modern, state-managed, multi-page recruitment and talent sourcing application designed to move from keyword-based candidate filtering to deep semantic human intelligence. 

Developed by **SRISAI SHIVAKOTI**, this platform solves the limitations of traditional recruitment by treating sourcing as a multi-dimensional graph and alignment problem. It evaluates candidates by career trajectory, behavioral signals, deep competency graphs, and profile integrity.

---

## 🌟 Core Features

### 1. Interactive Landing Page
* **Recruiter-Friendly Value Propositions**: Explains how AuraMatch performs deep career velocity analysis, smart fit calculation, and resume honesty checks in clear, simple language.
* **Live Tech Skill Simulator**: An interactive playground where recruiters can map equivalent tech skills (e.g. mapping Django/Flask to FastAPI, or traditional search to modern vector search) and see compatibility scores and verdicts dynamically.

### 2. Recruiter Portal Login & SSO
* **Secure Portal Simulator**: Recruiters can log in with demo credentials (`recruiter@auramatch.ai` / `auramatch2026`).
* **Functional SSO buttons**: Supports single-click authentication via simulated Google and Microsoft OAuth buttons.

### 3. Dynamic Job Description (JD) Calibration
* **Dynamic Sourcing Calibrator**: Pasting any Job Description automatically scans it using a comprehensive professional keyword dictionary (`ALL_PROFESSIONAL_KEYWORDS`).
* **Extracted Experience Band**: Dynamically extracts the target experience range (e.g., `5 to 8 years`).
* **Calibrated Tech Stacks**: Identifies target technology requirements and updates candidate fit scores instantly.
* **AI Calibration Expander**: Displays a clear summary of the AI's understanding of the role at the top of the dashboard.

### 4. Interactive ATS Resume Analyzer & Live Coach
* **Universal Candidate Matching**: Paste any JD and any candidate resume (such as the included Business Manager sample) to calculate match percentages.
* **Dynamic Verdicts**: Generates structured fit verdicts based on the candidate's matched capabilities.
* **Live Interview Coach**: Dynamically generates tailored, context-specific interview questions focused on the candidate's exact competency gaps.

### 5. Talent Analytics & Comparison Matrix
* **Dashboard Analytics**: Visualizes candidate seniority spreads, notice periods, expected salaries, and skill matching distributions using clean charts.
* **Side-by-Side Comparison**: Select any two candidates from your shortlist to perform a complete parameter comparison.

---

## 🛠️ Project Structure
```
├── app.py                     # Main multi-page Streamlit application code
├── rank.py                    # Production ranking execution script for all 100,000 profiles
├── precomputed_scores.json    # Precomputed top 100 lookup scores and reasoning database
├── profile.png                # Developer profile image
├── VectorVanguard.csv         # Final ranked output submission file (Top 100)
├── requirements.txt           # Python application dependencies
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

## ☁️ Deployment Guide (Streamlit Community Cloud)

You can host AuraMatch online for free in under 5 minutes:
1. Fork or push this repository to your GitHub account (e.g. `https://github.com/Srisai16/IndiaRuns_Hack2Skill_AuraMatch.git`).
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. Click **"New app"** in the dashboard.
4. Select your repository, branch (`main`), and set the main file path to `app.py`.
5. Click **"Deploy!"**. Once built, Streamlit will provide a public URL (e.g., `https://auramatch.streamlit.app`) to share.

*Note: After deployment, you can capture screenshots of the live app running online and update this section to showcase your portal.*
