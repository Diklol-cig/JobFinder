# JobFinder AI — Self-Hosted Setup Guide (100% Free Stack)

This guide walks you through running the **100% free** JobFinder workflow on self-hosted **Docker Compose** or **CasaOS + n8n (`v2.22+`)**.

---

## 1. Repository Files Overview
- [`jobfinder_n8n_workflow.json`](jobfinder_n8n_workflow.json) — The 38-node n8n workflow built from the sanitized example configuration (`Alex Morgan`).
- [`scripts/build_workflow.py`](scripts/build_workflow.py) — Python builder to generate either the public template workflow or your private local workflow (`--local` / `--all`).
- [`examples/config.example.json`](examples/config.example.json) & [`examples/master_profile.example.md`](examples/master_profile.example.md) — Example settings and Candidate Master Profile templates.
- [`docker-compose.yml`](docker-compose.yml) — Full stack (`n8n` + `gotenberg` on a shared Docker network).
- [`docker/docker-compose.gotenberg.yml`](docker/docker-compose.gotenberg.yml) — Standalone Gotenberg container Compose file for CasaOS or existing n8n servers.

---

## 2. Target Profile, Scoring Rubric & Guardrails

### Search Tracks (Integration, AI/Workflow Automation & DevOps Focus — Non-SWE)
- **Tier 1 (Top Priority — up to 35 Role Fit pts):**
  - AI & Workflow Automation Engineer / Specialist (`n8n`, LLM workflows, API integrations, process automation)
  - Enterprise / MES Systems & API Integration Engineer (System Integrator, Application Engineer, Solution Consultant connecting enterprise/industrial systems via REST APIs, SQL, webhooks, MES/ERP, and Python/Bash scripting)
- **Tier 2 (Secondary Priority — 22–29 Role Fit pts):**
  - Observability, Linux & DevOps Automation Engineer (`Grafana`, `Linux`, `Docker`, `CI/CD` tooling — without 24/7 firefighting or day-one Cloud/K8s architect requirements)
  - Technical Solutions / Integration Consultant (prototyping & integrating AI/automation/enterprise workflows with stakeholders)

### 4-Part 100-Point Scoring Rubric
1. **Role Fit (`0–35` pts):** Evaluates alignment with your Tier 1 / Tier 2 target roles.
2. **Tech Stack (`0–30` pts):** Overlap with `n8n`/workflow orchestration, REST APIs/webhooks, LLM workflows, SQL, Linux, Docker, Grafana, MES integration, and scripting.
3. **AI-Proof Job Security & Stability (`0–20` pts):** System/integration ownership & AI resilience at stable product/enterprise companies with permanent employment.
4. **Location & Compensation (`0–15` pts):** Location/Home Office match (`0–10`) + salary fit (`0–5`).

### Location Gate, Categories & Dealbreaker Hard Caps (Enforced in Code)
- **Category Breakdown (`matched_track`):** Scored jobs are categorized into **`Tier 1: AI & Workflow Automation`**, **`Tier 1: Enterprise / MES & API Integration`**, **`Tier 2: Observability, Linux & DevOps`**, **`Tier 2: Technical Solutions / Integration Consultant`**, or **`Other / Mismatch`**, and displayed prominently under `📂 Category:` in Discord.
- **Approved Locations & Home Office Limits (Configurable):**
  - **Fully Remote:** Pass.
  - **Primary Region (`DEBRECEN_1HR_AREA`):** Default **Max `2` office days/week** (min `3` days Home Office).
  - **Secondary Metro (`BUDAPEST`):** Default **Max `1` office day/week** (min `4` days Home Office).
  - *Unspecified Office/HO Schedule (Keep with Warning):* Hybrid or Unknown work-mode roles in approved zones without explicit office/HO day counts remain eligible with a **-5 pt penalty** and display a **`⚠️ WARNING: Office/HO days unspecified...`** banner.
- **Explicit Office / Location Failure — Auto-Drop (`SKIPPED`):** Any role outside approved zones without Remote, explicitly Onsite-only, or explicitly exceeding your max office days (`>1d` secondary city / `>2d` primary region) is capped at **30** and immediately **dropped (`SKIPPED`)** (no CV, no Discord notification).
- **Excluded Industries (Auto-Skipped):** Any company or role involving **crypto / Web3 / NFTs / token exchanges, gambling / betting / iGaming / casinos, adult entertainment, high-risk forex / binary options / CFDs, MLM / shady affiliate marketing, or unstable stealth startups** is pre-filtered or flagged (`is_shady_or_excluded_industry`), capped at **20**, and forced to **`SKIPPED`**.
- **Commercial SWE Roles (Auto-Skipped):** Medior/Senior Software Developer or Backend Application Engineering roles requiring `2–3+` years of commercial software development (even in Python) are flagged (`requires_commercial_swe_experience`), capped at **45**, and forced to **`SKIPPED`**.
- **Notification Noise Control (`@everyone` Tagging):** **`@everyone` notifications are sent ONLY when a `70+` Strong Match generates ATS PDF CVs.** `50–69` Maybe alerts post quietly without `@everyone`.

---

## 3. Deploy n8n + Gotenberg

### Option A: Full Docker Compose Stack
```bash
docker compose up -d
```
- n8n runs at `http://localhost:5678`.
- Gotenberg runs on the same Docker network at `http://gotenberg:3000` (already set as the default in `examples/config.example.json`).

### Option B: CasaOS / Existing n8n Instance
1. Open your **CasaOS dashboard** -> **`+`** -> **Install a customized app** -> **Import**.
2. Upload [`docker/docker-compose.gotenberg.yml`](docker/docker-compose.gotenberg.yml) and click **Submit** -> **Install**.
3. Verify `http://<YOUR_SERVER_LAN_IP>:3000/health` returns `{"status":"up"}`.

---

## 4. Storage Defaults (`/home/node/.n8n`)
By default, `Initialize Profile and Settings` sets `nas_output_dir` to `/home/node/.n8n`, which is writable inside the standard n8n container so `seen_jobs.json` and generated PDFs save cleanly without extra host volume configuration.

*(Optional)* If you mount a custom share (e.g. `/files` with `N8N_RESTRICT_FILE_ACCESS_TO=/files`), update `nas_output_dir` inside `Initialize Profile and Settings` (or `config.local.json`).

---

## 5. Create Your 2 Free Credentials in n8n
All API secrets stay inside n8n's encrypted **Credentials** store instead of inside workflow JSON files:

### A. Google Gemini(PaLM) Api (Free Google AI Studio Key)
1. Go to **[Google AI Studio API Keys](https://aistudio.google.com/apikey)** and create a free API key.
2. In n8n, open **Credentials** -> **Add credential** -> search for **`Google Gemini(PaLM) Api`**.
3. Keep **Host** as `https://generativelanguage.googleapis.com`, paste your **API Key**, and click **Save**.
   - The workflow uses `gemini-3.5-flash-lite` with built-in **4s–5s rate-limit pauses** and retries to stay comfortably within free-tier RPM limits.

### B. Discord Webhook
1. In Discord, open **Channel Settings** -> **Integrations** -> **Webhooks** -> **New Webhook** -> **Copy Webhook URL**.
2. In n8n, open **Credentials** -> **Add credential** -> search for **`Discord Webhook`**.
3. Paste your **Webhook URL** and click **Save**.

---

## 6. Customize Your Profile & Build Local Workflow (Optional)
For personal deployments without risking committing private details:
1. Copy `examples/config.example.json` -> `config.local.json` (gitignored).
2. Create your personal Markdown profile (e.g., `master_profile.local.md`, gitignored) and point `"profile_path"` in `config.local.json` to it.
3. Update `"output_path"` to `"jobfinder_n8n_workflow.local.json"`, `"gotenberg_url"` to `http://<YOUR_SERVER_LAN_IP>:3000` (or `http://gotenberg:3000`), and your `"candidate"` object + `"secondary_cv_language"` (`"hu"`, `"de"`, `"pl"`, or `"none"`).
4. Generate your private workflow JSON:
   ```bash
   python scripts/build_workflow.py --local
   ```

---

## 7. Import & Link Credentials in n8n
1. Open n8n, create a new workflow, click **`⋯` (top right menu)** -> **Import from File...**, and select `jobfinder_n8n_workflow.local.json` (or `jobfinder_n8n_workflow.json`).
2. Link your 2 credentials in these 4 nodes:
   - **`Gemini Score and Filter Job`** -> select **`Google Gemini(PaLM) Api`**
   - **`Gemini Generate Tailored CV and CL`** -> select **`Google Gemini(PaLM) Api`**
   - **`Send Strong Match PDFs to Discord`** -> click to explicitly bind **`Discord Webhook`**
   - **`Send Maybe Discord Alert`** -> click to explicitly bind **`Discord Webhook`**
3. Click **Test workflow** (via **`Manual Test Trigger`**). Once verified, toggle the workflow **Active** so **`Daily 0730 Trigger`** runs every morning at **07:30**.

---

## 8. Optional: Connect the n8n Data Table UI
The workflow already deduplicates jobs automatically via `/home/node/.n8n/seen_jobs.json`. `Log to n8n Data Table Optional` is deactivated by default so imports never fail if Data Tables are unused. To enable it:
1. In n8n's left sidebar, open **Data Tables** and create a table named **`job_listings`** with columns:
   `job_id` (String), `source` (String), `title` (String), `company` (String), `location` (String), `work_mode` (String), `match_score` (Number), `matched_track` (String), `match_tier` (String), `url` (String), `scored_at` (String).
2. Open **`Log to n8n Data Table Optional`**, select `job_listings`, and activate the node (`D`).
