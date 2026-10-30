# S&P 500 Quantitative Valuation & Forensic Terminal — Free Web App Package

This directory contains the self-contained package required to deploy and host your terminal online as a **100% free web app** accessible from your phone, laptop, or any web browser.

---

## 1. What You Need to Use

To host this for free, you only need:
1. **A Free GitHub Account** (to store the code).
2. **A Free Cloud Host Account** (choose one of the options below — all offer free tiers with zero credit card required):
   - **Render.com** (Recommended: 1-click Python web service, free SSL domain).
   - **Hugging Face Spaces** (Alternative: unlimited free CPU Docker container).
   - **Railway / Koyeb** (Alternative free container hosting).

---

## 2. Files in This Folder & Their Purpose

| File | Purpose |
| :--- | :--- |
| **`app.py`** | Web server using Python's standard library `http.server` (zero heavy web framework overhead). Automatically detects cloud ports (`$PORT`), serves the dashboard at `/`, and provides live REST API endpoints (`/api/scan/audit`, `/api/watchlists`, `/api/payload`). |
| **`sp500_tierlist_dashboard.html`** | The pre-compiled terminal frontend. Bundles the complete audited database of 481 S&P 500 companies so the cloud app boots in **under 1 second** without crashing free-tier memory limits. |
| **`dashboard_builder.py`** | Generates the HTML workstation, UI themes, 4-year financial tables, Peter Lynch PEG/PEGY ratios, and watchlists. |
| **`sp500_peg_screener.py`** | Forensic screening engine; powers the on-demand single-ticker live audit (`audit_single_ticker_live`). |
| **`fundamentals.py`** | Reverse DCF engine, Piotroski F-Score, Beneish M-Score, Altman Z-Score, and Owner Free Cash Flow calculations. |
| **`research_agent.py`** | Pulls SEC EDGAR 10-K/10-Q filings, Google News RSS, and qualitative moats. |
| **`openinsider.py`** | Scrapes and scores 12-month OpenInsider open-market insider transaction ledgers. |
| **`requirements.txt`** | Python dependencies (`yfinance`, `pandas`, `requests`, `beautifulsoup4`, `lxml`). |
| **`render.yaml`** | 1-click blueprint configuration file for Render.com. |
| **`Procfile`** | Deployment command (`web: python app.py`) recognized by Render, Railway, and Heroku-compatible buildpacks. |
| **`runtime.txt`** | Specifies Python 3.11.9 runtime for cloud build environments. |
| **`Dockerfile`** | Container specification for Hugging Face Spaces or container cloud providers. |

---

## 3. How to Deploy (Step-by-Step)

### Option A: Render.com (Recommended — Fastest Setup)

Render provides a 100% free web service tier with an automatic `https://your-name.onrender.com` domain and free SSL.

1. **Push this folder to GitHub:**
   - Go to [github.com/new](https://github.com/new) and create a repository (e.g. `sp500-investment-terminal`).
   - Open a terminal in this `free_web_app` folder and run:
     ```bash
     git init
     git add .
     git commit -m "Deploy S&P 500 terminal"
     git branch -M main
     git remote add origin https://github.com/YOUR_USERNAME/sp500-investment-terminal.git
     git push -u origin main
     ```

2. **Connect to Render:**
   - Go to [dashboard.render.com](https://dashboard.render.com) and log in with your GitHub account.
   - Click **New +** $\rightarrow$ **Web Service**.
   - Select your `sp500-investment-terminal` repository.

3. **Configure Settings:**
   - **Name:** `sp500-terminal` (or your choice).
   - **Region:** Ohio or Oregon (US).
   - **Branch:** `main`.
   - **Runtime:** `Python 3`.
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Instance Type:** `Free`.

4. **Click "Deploy Web Service":**
   - Render will install dependencies and start the app.
   - Within 2 minutes, your terminal is live at:
     `https://sp500-terminal.onrender.com`

---

### Option B: Hugging Face Spaces (Always-On Free Docker Hosting)

If you prefer an environment that never spins down after inactivity:

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. **Space Name:** `sp500-terminal`.
3. **Space SDK:** Select **Docker** $\rightarrow$ **Blank**.
4. **Visibility:** Public or Private (your choice; Private is free too).
5. Clone the space or push the files from this `free_web_app` folder directly into the Space.
6. The included `Dockerfile` will automatically build and expose port `7860`.
7. Your terminal will be live at `https://huggingface.co/spaces/YOUR_USERNAME/sp500-terminal`.

---

### Option C: Static Hosting via GitHub Pages (Read-Only)

If you just want to view the full interactive dashboard on your phone/browser without running a live Python server:
1. Rename `sp500_tierlist_dashboard.html` to `index.html`.
2. Push `index.html` to a GitHub repository.
3. In GitHub Settings $\rightarrow$ **Pages**, set Source to `main` branch $\rightarrow$ `/ (root)`.
4. Your dashboard will be instantly accessible at `https://YOUR_USERNAME.github.io/REPOSITORY_NAME`.

---

## 4. How the Cloud Terminal Functions

- **Instant Load:** Boots in under 1 second using the pre-cached 481 audited companies.
- **Interactive Dossiers:** Click any ticker to open the 4-year audited statements, 3Y Peter Lynch PEG, reverse DCF expectation gap, and 12-month OpenInsider ledger.
- **On-Demand Single-Stock Audits:** Type any ticker in the search bar and press **[Enter]** (or click **Run Live Audit**) to fetch real-time 10-K data from Yahoo Finance and OpenInsider directly inside the cloud app.
- **Watchlists:** Create and manage custom watchlists with data saved dynamically.
