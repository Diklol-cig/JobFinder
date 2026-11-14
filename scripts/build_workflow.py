import argparse
import json
import re
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def make_init_js(cfg: dict, master_profile: str) -> str:
    """Build the JavaScript for the Initialize Profile and Settings Code node."""
    cand = cfg.get("candidate", {})
    payload = {
        "candidate_name": cand.get("name", "Alex Morgan"),
        "candidate_file_slug": cand.get("file_slug", "Alex_Morgan"),
        "candidate_headline": cand.get(
            "headline",
            "Enterprise & MES System Integrator | AI & Workflow Automation | Linux & DevOps Tooling",
        ),
        "candidate_location": cand.get("location", "Remote / Hybrid"),
        "candidate_email": cand.get("email", "candidate@example.com"),
        "candidate_linkedin_url": cand.get("linkedin_url", "https://www.linkedin.com/in/example"),
        "candidate_linkedin_display": cand.get("linkedin_display", "linkedin.com/in/example"),
        "secondary_cv_language": cfg.get("secondary_cv_language", "hu"),
        "secondary_cv_language_name": cfg.get("secondary_cv_language_name", "Hungarian"),
        "gemini_scoring_model": cfg.get("gemini_scoring_model", "gemini-3.5-flash-lite"),
        "gemini_cv_model": cfg.get("gemini_cv_model", "gemini-3.5-flash-lite"),
        "gotenberg_url": cfg.get("gotenberg_url", "http://gotenberg:3000"),
        "nas_output_dir": cfg.get("nas_output_dir", "/home/node/.n8n"),
        "score_threshold_apply": int(cfg.get("score_threshold_apply", 70)),
        "score_threshold_maybe": int(cfg.get("score_threshold_maybe", 50)),
        "max_new_jobs_per_run": int(cfg.get("max_new_jobs_per_run", 15)),
        "linkedin_time_filter": cfg.get("linkedin_time_filter", "r604800"),
        "always_generate_cover_letter": bool(cfg.get("always_generate_cover_letter", False)),
        "primary_region_max_office_days": int(cfg.get("primary_region_max_office_days", 2)),
        "secondary_city_max_office_days": int(cfg.get("secondary_city_max_office_days", 1)),
        "search_queries_json": cfg.get("search_queries", {}),
        "candidate_profile": master_profile,
    }
    return f"return [{{\n  json: {json.dumps(payload, ensure_ascii=False, indent=4)}\n}}];"


JS_BUILD_LINKEDIN_QUERIES = r"""
const config = $('Initialize Profile and Settings').first().json;
const seenItems = $('Load Seen Jobs File').all();

// Initialize staticData seenJobIds from disk file if available
const staticData = $getWorkflowStaticData('global');
if (!staticData.seenJobIds || typeof staticData.seenJobIds !== 'object') {
  staticData.seenJobIds = {};
}

for (const item of seenItems) {
  if (item.binary && item.binary.data) {
    try {
      const buf = await this.helpers.getBinaryDataBuffer(0, 'data');
      const parsed = JSON.parse(buf.toString('utf8'));
      if (parsed && typeof parsed === 'object') {
        Object.assign(staticData.seenJobIds, parsed);
      }
    } catch (e) {
      // Ignore missing or empty file on first run
    }
  }
}

let searchCfg = {};
try {
  searchCfg = typeof config.search_queries_json === 'string'
    ? JSON.parse(config.search_queries_json)
    : config.search_queries_json;
} catch (e) {
  searchCfg = { linkedin_keywords: [] };
}

const timeFilter = config.linkedin_time_filter || 'r604800';
const queries = (searchCfg.linkedin_keywords || []).map((entry) => {
  const kw = entry.keyword;
  const loc = entry.location || 'Hungary';
  const url = `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=${encodeURIComponent(kw)}&location=${encodeURIComponent(loc)}&f_TPR=${encodeURIComponent(timeFilter)}&start=0`;
  return {
    json: {
      source: 'linkedin',
      keyword: kw,
      search_location: loc,
      default_track: entry.track || 'General',
      search_url: url
    }
  };
});

return queries;
""".strip()

JS_PARSE_LINKEDIN_CARDS = r"""
const allInputs = $input.all();
const queryItems = $('Build LinkedIn Queries').all();
const out = [];

function cleanHtmlText(str) {
  if (!str) return '';
  return str
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

for (let idx = 0; idx < allInputs.length; idx++) {
  const res = allInputs[idx].json || {};
  const qMeta = (queryItems[idx] && queryItems[idx].json) ? queryItems[idx].json : {};
  const html = typeof res.data === 'string' ? res.data : (typeof res.body === 'string' ? res.body : '');
  if (!html || !html.includes('base-search-card')) continue;

  const parts = html.split('<li');
  for (const part of parts) {
    if (!part.includes('jobPosting:')) continue;

    const urnMatch = part.match(/data-entity-urn="urn:li:jobPosting:(\d+)"/);
    if (!urnMatch) continue;
    const rawId = urnMatch[1];

    const titleMatch = part.match(/class="base-search-card__title"[^>]*>([\s\S]*?)<\/h3>/);
    const subMatch = part.match(/class="base-search-card__subtitle"[^>]*>([\s\S]*?)<\/h4>/);
    const locMatch = part.match(/class="job-search-card__location"[^>]*>([\s\S]*?)<\/span>/);
    const linkMatch = part.match(/class="base-card__full-link[^"]*"[^>]*href="([^"]+)"/);
    const dateMatch = part.match(/<time[^>]*datetime="([^"]+)"/);

    const title = cleanHtmlText(titleMatch ? titleMatch[1] : '');
    const company = cleanHtmlText(subMatch ? subMatch[1] : '');
    const location = cleanHtmlText(locMatch ? locMatch[1] : 'Remote');
    const rawUrl = linkMatch ? linkMatch[1].split('?')[0] : `https://www.linkedin.com/jobs/view/${rawId}`;
    const postedDate = dateMatch ? dateMatch[1] : new Date().toISOString().slice(0, 10);

    if (!title) continue;

    out.push({
      json: {
        job_id: `li_${rawId}`,
        raw_id: rawId,
        source: 'LinkedIn',
        title,
        company: company || 'Unknown Company',
        location,
        url: rawUrl,
        detail_url: `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/${rawId}`,
        posted_date: postedDate,
        matched_keyword: qMeta.keyword || '',
        initial_track: qMeta.default_track || 'General',
        salary_info: 'Not disclosed'
      }
    });
  }
}

return out;
""".strip()

JS_BUILD_NFJ_QUERIES = r"""
const config = $('Initialize Profile and Settings').first().json;
let searchCfg = {};
try {
  searchCfg = typeof config.search_queries_json === 'string'
    ? JSON.parse(config.search_queries_json)
    : config.search_queries_json;
} catch (e) {
  searchCfg = { nofluffjobs_queries: [] };
}

return (searchCfg.nofluffjobs_queries || []).map((q) => ({
  json: {
    source: 'nofluffjobs',
    rawSearch: q.rawSearch,
    default_track: q.track || 'General',
    request_body: JSON.stringify({
      rawSearch: q.rawSearch,
      page: 1
    })
  }
}));
""".strip()

JS_PARSE_NFJ_POSTINGS = r"""
const allInputs = $input.all();
const queryItems = $('Build NoFluffJobs Queries').all();
const out = [];

for (let idx = 0; idx < allInputs.length; idx++) {
  const body = allInputs[idx].json || {};
  const qMeta = (queryItems[idx] && queryItems[idx].json) ? queryItems[idx].json : {};
  const postings = Array.isArray(body.postings) ? body.postings : [];

  for (const p of postings) {
    if (!p || !p.id || !p.title) continue;

    const places = (p.location && Array.isArray(p.location.places)) ? p.location.places : [];
    const cities = places.map((pl) => pl.city).filter(Boolean);
    const countries = places.map((pl) => (pl.country && pl.country.code) ? pl.country.code : '').filter(Boolean);
    const isRemote = Boolean(p.fullyRemote) || cities.some((c) => /remote/i.test(c));
    const isHungary = (Array.isArray(p.regions) && p.regions.includes('hu')) ||
      countries.includes('HUN') ||
      cities.some((c) => /budapest|debrecen|nyíregyháza|nyiregyhaza|tiszaújváros|tiszaujvaros|miskolc|polgár|polgar|hajdúszoboszló|hajduszoboszlo|hajdúböszörmény|hajduboszormeny|balmazújváros|balmazujvaros|berettyóújfalu|berettyoujfalu|nyírbátor|nyirbator|püspökladány|puspokladany|karcag|szeged|győr|pécs|hungary/i.test(c));

    // Must be either in target region (Hungary) or Remote
    if (!isHungary && !isRemote) continue;

    let salaryInfo = 'Not disclosed';
    if (p.salary && p.salary.from) {
      salaryInfo = `${p.salary.from} - ${p.salary.to || p.salary.from} ${p.salary.currency || 'HUF'} / ${p.salary.period || 'Month'} (${p.salary.type || 'gross'})`;
    }

    const locationStr = [
      isRemote ? 'Remote' : '',
      ...cities.filter((c) => !/remote/i.test(c)).slice(0, 3)
    ].filter(Boolean).join(', ') || 'Remote / Europe';

    const slug = p.url || p.id;
    out.push({
      json: {
        job_id: `nfj_${p.id}`,
        raw_id: p.id,
        source: 'NoFluffJobs',
        title: p.title.trim(),
        company: (p.name || 'Unknown Company').trim(),
        location: locationStr,
        url: `https://nofluffjobs.com/hu/job/${slug}`,
        detail_url: `https://nofluffjobs.com/api/posting/${encodeURIComponent(p.id)}`,
        posted_date: p.posted ? new Date(p.posted).toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10),
        matched_keyword: qMeta.rawSearch || '',
        initial_track: qMeta.default_track || 'General',
        salary_info: salaryInfo,
        seniority_list: Array.isArray(p.seniority) ? p.seniority.join(', ') : ''
      }
    });
  }
}

return out;
""".strip()

JS_COMBINE_AND_PREFILTER = r"""
const config = $('Initialize Profile and Settings').first().json;
const staticData = $getWorkflowStaticData('global');
const seenMap = staticData.seenJobIds || {};

const allCandidates = $input.all().map((i) => i.json).filter((j) => j && j.job_id);

// Relevant title keywords across Non-SWE Integration, AI/Workflow Automation & DevOps/Observability tracks
const positiveTitleRegex = /\b(ai|artificial intelligence|agentic|llm|genai|generative|automation|n8n|rpa|workflow|api|integration|integrator|mes|manufacturing execution|devops|sre|site reliability|platform|linux|observability|monitoring|grafana|prometheus|solution engineer|solutions engineer|solution consultant|solutions consultant|solution architect|forward deployed|forward-deployed|internal tools|application engineer|it engineer|systems engineer|system engineer)\b/i;

// Exclude Medior/Senior SWE developer titles, non-building coordinator/process roles, support grinds, junior/intern, heavy unrelated stacks, and Polish-only titles
const negativeTitleRegex = /\b(intern|internship|gyakornok|diákmunka|trainee|junior|pályakezdő|working student|accountant|könyvelő|recruiter|hr|sales representative|értékesítő|ertékesítő|senior software engineer|senior software developer|medior software developer|software developer|senior backend|backend developer|backend engineer|senior python developer|python developer|lead developer|lead software engineer|fullstack|full-stack|full stack|incident manager|major incident|change manager|release manager|problem manager|scrum master|agile coach|project manager|manual tester|manual qa|l1 support|l2 support|helpdesk|service desk|servicedesk|frontend|front-end|react|angular|vue|ios|android|flutter|php developer|java developer|abap|starszy|specjalista|analityk|kierownik|programista|inżynier|młodszy)\b|(?:^|[\s\/(,|])(?:\.net|c#|c\+\+|\(m\/k\)|\(k\/m\))(?=$|[\s\/),|])/i;

// Exclude shady, volatile, or controversial industries (crypto, gambling/iGaming, adult, forex/CFDs, MLM)
const excludedIndustryRegex = /\b(crypto|cryptocurrency|blockchain|web3|nft|defi|tokenomics|binance|coinbase|bybit|kraken|casino|gambling|igaming|i-gaming|sportsbook|betting|bet365|unibet|poker|slots|slot machine|roulette|lottery|adult entertainment|nsfw|onlyfans|forex|binary options|cfd trading|mlm|multi-level marketing|szerencsejáték|kaszinó|sportfogadás|kripto)\b/i;

const uniqueById = new Map();
const uniqueByCompanyTitle = new Set();

for (const job of allCandidates) {
  if (seenMap[job.job_id]) continue;
  if (uniqueById.has(job.job_id)) continue;

  const normKey = `${(job.company || '').toLowerCase().trim()}::${(job.title || '').toLowerCase().trim()}`;
  if (uniqueByCompanyTitle.has(normKey)) continue;

  if (excludedIndustryRegex.test(`${job.title || ''} ${job.company || ''}`)) continue;
  if (negativeTitleRegex.test(job.title)) continue;
  if (!positiveTitleRegex.test(job.title)) continue;

  uniqueById.set(job.job_id, job);
  uniqueByCompanyTitle.add(normKey);
}

const maxJobs = Number(config.max_new_jobs_per_run) || 15;
const filtered = Array.from(uniqueById.values()).slice(0, maxJobs);

if (filtered.length === 0) {
  return [{ json: { job_id: '', no_new_jobs: true } }];
}

return filtered.map((j) => ({ json: j }));
""".strip()

JS_EXTRACT_DETAILS_AND_BUILD_SCORING = r"""
const config = $('Initialize Profile and Settings').first().json;
const job = $('Loop Over Candidate Jobs').first().json;
const detailResp = $input.first().json || {};

const candidateName = config.candidate_name || 'the candidate';
const primaryMaxOffice = Number(config.primary_region_max_office_days ?? 2);
const primaryMinHo = Math.max(0, 5 - primaryMaxOffice);
const secondaryMaxOffice = Number(config.secondary_city_max_office_days ?? 1);
const secondaryMinHo = Math.max(0, 5 - secondaryMaxOffice);

function stripHtml(html) {
  if (!html) return '';
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li[^>]*>/gi, '• ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

let descriptionText = '';
let criteriaText = '';
let mustHaveSkills = '';
let niceToHaveSkills = '';

const rawPayload = typeof detailResp.data === 'string'
  ? detailResp.data
  : (typeof detailResp.body === 'string' ? detailResp.body : JSON.stringify(detailResp));

if (job.source === 'LinkedIn') {
  const descMatch = rawPayload.match(/show-more-less-html__markup[^>]*>([\s\S]*?)<\/div>/i);
  descriptionText = stripHtml(descMatch ? descMatch[1] : rawPayload.slice(0, 12000));

  const critMatches = [...rawPayload.matchAll(/description__job-criteria-subheader[^>]*>([\s\S]*?)<\/h3>[\s\S]*?description__job-criteria-text[^>]*>([\s\S]*?)<\/span>/gi)];
  criteriaText = critMatches.map((m) => `${stripHtml(m[1])}: ${stripHtml(m[2])}`).join(' | ');
} else {
  // NoFluffJobs JSON
  let parsed = detailResp;
  if (typeof rawPayload === 'string' && rawPayload.trim().startsWith('{')) {
    try { parsed = JSON.parse(rawPayload); } catch (e) {}
  }
  const desc = (parsed.details && parsed.details.description) ? stripHtml(parsed.details.description) : '';
  const musts = (parsed.requirements && Array.isArray(parsed.requirements.musts))
    ? parsed.requirements.musts.map((m) => m.value).filter(Boolean).join(', ')
    : '';
  const nices = (parsed.requirements && Array.isArray(parsed.requirements.nices))
    ? parsed.requirements.nices.map((n) => n.value).filter(Boolean).join(', ')
    : '';
  const reqDesc = (parsed.requirements && parsed.requirements.description) ? stripHtml(parsed.requirements.description) : '';
  const dailyTasks = (parsed.specs && Array.isArray(parsed.specs.dailyTasks))
    ? parsed.specs.dailyTasks.map((t) => stripHtml(t)).join('\n• ')
    : '';
  mustHaveSkills = musts;
  niceToHaveSkills = nices;
  descriptionText = [
    desc,
    musts ? `Must-have skills: ${musts}` : '',
    nices ? `Nice-to-have skills: ${nices}` : '',
    reqDesc ? `Requirements details: ${reqDesc}` : '',
    dailyTasks ? `Daily tasks:\n• ${dailyTasks}` : ''
  ].filter(Boolean).join('\n\n');
}

if (!descriptionText || descriptionText.length < 30) {
  descriptionText = `Job Title: ${job.title} at ${job.company} (${job.location}). Track: ${job.initial_track}.`;
}

// Truncate description to keep token usage lean
descriptionText = descriptionText.slice(0, 9000);

const systemPrompt = `You are an expert technical career advisor and strict job-matching evaluator for ${candidateName}.
Evaluate the job posting strictly against ${candidateName}'s Master Profile (System Integration, AI/Workflow Automation, Linux/DevOps Tooling — NOT commercial software application development), AI-proof job security rules, contract/compensation rules, and strict location/Home Office boundaries.

CANDIDATE MASTER PROFILE:
${config.candidate_profile}

4-PART 100-POINT SCORING RUBRIC:
1. role_fit_score (0-35 pts):
   - 30-35 pts (Tier 1 Top Priority):
     * AI & Workflow Automation Engineer / Specialist (n8n, LLM workflows, RAG/agents, API integrations, process automation)
     * Enterprise / MES Systems & API Integration Engineer (System Integrator, Application Engineer, Solution Consultant connecting enterprise/industrial systems via REST APIs, SQL, webhooks, MES/ERP, and Python/Bash scripting)
   - 22-29 pts (Tier 2 Secondary Priority):
     * Observability, Linux & DevOps Automation Engineer (Grafana dashboards, Linux automation, Docker, CI/CD tooling — WITHOUT 24/7 on-call firefighting or day-one K8s/Cloud architect mandates)
     * Technical Solutions / Integration Consultant (prototyping & integrating AI/automation/enterprise workflows with stakeholders)
   - 0-12 pts (Mismatch / Dealbreaker):
     * Commercial Software Development / Application Engineering roles (Medior/Senior Software Developer, Backend Software Engineer requiring 2-3+ years commercial application coding, OOP software architecture, or full-time product coding — even in Python -> set requires_commercial_swe_experience=true)
     * Non-building coordinator/process roles (Incident Manager, Change Manager, Release Manager, Scrum Master, manual UAT/QA tester)
     * 24/7 shift work, heavy on-call firefighting, or L1/L2 helpdesk/ticket grinding

2. tech_stack_score (0-30 pts):
   - 24-30 pts: Strong practical overlap with n8n/workflow orchestration, REST APIs/webhooks, LLM workflows/RAG, SQL, Linux, Docker, Grafana, MES/enterprise integration, and Python/Bash scripting.
   - 14-23 pts: Partial overlap with reasonable ramp-up.
   - 0-12 pts (Dealbreaker):
     * If requiring 2-3+ years of commercial Software Development / Backend Application Engineering / OOP product coding (even in Python): set requires_commercial_swe_experience=true and cap tech_stack_score at 12.
     * If requiring 4+ years of Senior Java, C#/.NET, C++, React/Angular frontend, OR deep Cloud/Kubernetes/AWS/Azure/GCP/Terraform architect specialization from day one: set requires_heavy_unrelated_stack=true.

3. job_security_score (0-20 pts):
   - Evaluate BOTH AI-proof job security (system/integration ownership, cross-system operational context, AI/automation architecture vs. easily automated L1 support/manual testing/boilerplate coding) AND employment stability / company trustworthiness.
   - 16-20 pts: Permanent full-time employment (indefinite contract) at a stable product or enterprise company, high AI resilience & real integration/automation ownership.
   - 9-15 pts: Permanent role with moderate AI resilience, or unclear contract type at a reputable product/enterprise firm.
   - 0-8 pts (Dealbreaker - set is_b2b_or_agency_only=true if B2B/contractor-only/body-leasing agency): Short-term contractor, B2B-only, body-leasing agency, or high-churn shift/ticket role.
   - 0 pts (Hard Exclude - set is_shady_or_excluded_industry=true): Shady, volatile, or controversial industries/companies: crypto/Web3/NFTs/token exchanges, gambling/betting/iGaming/casinos, adult entertainment, high-risk forex/binary options/CFDs, MLM/shady affiliate marketing, or unstable stealth startups.

4. location_and_comp_score (0-15 pts):
   - Location/HO sub-score (0-10 pts):
     * 10 pts: Fully Remote (Hungary / EU / Global allowed without relocation).
     * 8-9 pts: Debrecen + 1-hour driving radius (Debrecen, Nyíregyháza, Tiszaújváros, Miskolc, Polgár, Hajdúszoboszló, Hajdúböszörmény, Balmazújváros, Berettyóújfalu, Nyírbátor, Püspökladány, Karcag) explicitly allowing MAX ${primaryMaxOffice} office days/week (MIN ${primaryMinHo} days Home Office); OR Budapest explicitly allowing MAX ${secondaryMaxOffice} office day(s)/week (MIN ${secondaryMinHo} days Home Office).
     * 5-6 pts (set is_unverified_hybrid=true, location_rule_passed=true): Budapest or Debrecen + 1hr region listing with Hybrid or Unknown work mode that does NOT specify exact office/HO day counts (do NOT set location_rule_passed=false when office/HO days are merely unspecified).
     * 0 pts (set location_rule_passed=false): Set ONLY when explicitly Onsite-only, OR explicitly exceeds max office days (more than ${secondaryMaxOffice} day/wk in Budapest, more than ${primaryMaxOffice} days/wk in Debrecen + 1hr area), OR located outside approved zones (e.g., Győr/Germany/Poland/Remote US-only) without Hungary Remote.
   - Compensation sub-score (0-5 pts):
     * Compare against the Target Compensation range in the Candidate Master Profile.
     * 5 pts: Meets or exceeds target salary range.
     * 3-4 pts: Slightly below midpoint OR not disclosed at an enterprise/product firm matching target seniority.
     * 0-1 pts: Disclosed significantly below minimum acceptable target compensation.

ADDITIONAL RULES:
- IMPORTANT CANDIDATE REALITY CHECK: Respect the Career Identity & Exclusions in ${candidateName}'s Master Profile strictly. Never assume commercial software application development experience if the Master Profile explicitly excludes it: whenever a job expects 2-3+ years of commercial software development / application engineering (even in Python), set requires_commercial_swe_experience=true, role_fit_score at most 12, and tech_stack_score at most 12.
- Reject Intern / Junior / Trainee roles (set role_fit_score at most 10).
- Set is_shady_or_excluded_industry=true (and job_security_score=0) if the employer or role involves crypto/Web3/blockchain/NFTs, gambling/betting/iGaming/casinos, adult content, high-risk forex/CFDs, MLM/shady affiliate marketing, or an unstable/shady business.
- Set is_non_building_or_support_grind=true if it is a pure coordinator/process role (Incident/Change/Release Manager, Scrum Master, manual QA) or 24/7 shift/on-call/L1-L2 ticket support grind.
- Set requires_cover_letter=true ONLY if the posting explicitly requests a cover letter, motivational letter, or "motivációs levél".
- match_score MUST equal role_fit_score + tech_stack_score + job_security_score + location_and_comp_score.`;

const userPrompt = `Evaluate this job listing and return JSON matching the schema:

Source: ${job.source}
Job ID: ${job.job_id}
Title: ${job.title}
Company: ${job.company}
Listed Location: ${job.location}
Salary Info: ${job.salary_info || 'Not disclosed'}
Extra Criteria: ${criteriaText || job.seniority_list || 'N/A'}

Full Job Description:
${descriptionText}`;

const geminiRequestBody = {
  systemInstruction: {
    parts: [{ text: systemPrompt }]
  },
  contents: [
    {
      role: 'user',
      parts: [{ text: userPrompt }]
    }
  ],
  generationConfig: {
    temperature: 0.15,
    responseMimeType: 'application/json',
    responseSchema: {
      type: 'OBJECT',
      required: [
        'role_fit_score',
        'tech_stack_score',
        'job_security_score',
        'location_and_comp_score',
        'match_score',
        'matched_track',
        'location_zone',
        'work_mode',
        'office_days_per_week',
        'home_office_days_per_week',
        'location_rule_passed',
        'is_unverified_hybrid',
        'location_notes',
        'requires_commercial_swe_experience',
        'is_shady_or_excluded_industry',
        'is_non_building_or_support_grind',
        'requires_heavy_unrelated_stack',
        'is_b2b_or_agency_only',
        'contract_type',
        'requires_cover_letter',
        'posting_language',
        'ai_proof_assessment',
        'fit_summary',
        'key_matching_skills',
        'missing_or_stretch_skills'
      ],
      properties: {
        role_fit_score: { type: 'INTEGER', description: '0-35 points for AI/Workflow Automation or System Integration fit' },
        tech_stack_score: { type: 'INTEGER', description: '0-30 points for n8n/APIs/LLM/SQL/Linux/Docker/Grafana/MES/scripting overlap' },
        job_security_score: { type: 'INTEGER', description: '0-20 points for AI resilience, system ownership, and permanent contract stability' },
        location_and_comp_score: { type: 'INTEGER', description: '0-15 points (0-10 location/HO fit + 0-5 compensation fit)' },
        match_score: { type: 'INTEGER', description: 'Sum of the 4 sub-scores from 0 to 100' },
        matched_track: {
          type: 'STRING',
          enum: [
            'Tier 1: AI & Workflow Automation',
            'Tier 1: Enterprise / MES & API Integration',
            'Tier 2: Observability, Linux & DevOps',
            'Tier 2: Technical Solutions / Integration Consultant',
            'Other / Mismatch'
          ]
        },
        location_zone: {
          type: 'STRING',
          enum: ['REMOTE', 'DEBRECEN_1HR_AREA', 'BUDAPEST', 'OUTSIDE_ZONES']
        },
        work_mode: {
          type: 'STRING',
          enum: ['Remote', 'Hybrid', 'Onsite', 'Unknown']
        },
        office_days_per_week: {
          type: 'INTEGER',
          description: 'Required onsite office days per week (0-5), or -1 if unspecified'
        },
        home_office_days_per_week: {
          type: 'INTEGER',
          description: 'Home office days per week (0-5), or -1 if unspecified'
        },
        location_rule_passed: {
          type: 'BOOLEAN',
          description: `False ONLY if outside approved zones without Remote, explicitly Onsite-only, more than ${secondaryMaxOffice} office day/wk in Budapest, or more than ${primaryMaxOffice} office days/wk in Debrecen 1hr region. Keep True when Hybrid/Unknown in Budapest or Debrecen 1hr region omits day counts.`
        },
        is_unverified_hybrid: {
          type: 'BOOLEAN',
          description: 'True if in Budapest or Debrecen 1hr region with Hybrid/Unknown work mode and unspecified office/HO day counts'
        },
        location_notes: {
          type: 'STRING',
          description: 'Short note on location and home office policy'
        },
        requires_commercial_swe_experience: {
          type: 'BOOLEAN',
          description: 'True if the role requires 2-3+ years of commercial software development, backend microservice/application coding, or Medior/Senior SWE skills (even in Python)'
        },
        is_shady_or_excluded_industry: {
          type: 'BOOLEAN',
          description: 'True if crypto/Web3/NFTs, gambling/betting/iGaming/casinos, adult, shady forex/CFDs/MLM, or unstable/shady business'
        },
        is_non_building_or_support_grind: {
          type: 'BOOLEAN',
          description: 'True if pure process/coordinator (Incident/Change/Scrum/Manual QA) or 24/7 on-call/L1-L2 support grind'
        },
        requires_heavy_unrelated_stack: {
          type: 'BOOLEAN',
          description: 'True if requiring 4+ yrs Java/C#/.NET/C++/React/Angular or deep day-one Cloud/K8s/Terraform architect expertise'
        },
        is_b2b_or_agency_only: {
          type: 'BOOLEAN',
          description: 'True if B2B/contractor-only or body-leasing outsourcing agency'
        },
        contract_type: {
          type: 'STRING',
          enum: ['Permanent', 'B2B / Contractor', 'Fixed-Term', 'Unknown']
        },
        requires_cover_letter: {
          type: 'BOOLEAN',
          description: 'True ONLY if the posting explicitly requests a cover letter / motivational letter'
        },
        posting_language: {
          type: 'STRING',
          enum: ['en', 'hu', 'de', 'pl', 'other']
        },
        ai_proof_assessment: {
          type: 'STRING',
          description: '1 concise sentence evaluating AI resilience, system ownership, and job security'
        },
        fit_summary: {
          type: 'STRING',
          description: '2-3 concise sentences explaining why this role matches or does not match the candidate'
        },
        key_matching_skills: {
          type: 'ARRAY',
          items: { type: 'STRING' }
        },
        missing_or_stretch_skills: {
          type: 'ARRAY',
          items: { type: 'STRING' }
        }
      }
    }
  }
};

return [{
  json: {
    ...job,
    clean_description: descriptionText,
    criteria_text: criteriaText,
    must_have_skills: mustHaveSkills,
    nice_to_have_skills: niceToHaveSkills,
    scoring_request_body: JSON.stringify(geminiRequestBody)
  }
}];
""".strip()

JS_PARSE_SCORE_AND_SAVE_SEEN = r"""
const config = $('Initialize Profile and Settings').first().json;
const jobData = $('Extract Clean Job Description and Build Scoring Prompt').first().json;
const geminiResp = $input.first().json || {};

const primaryMaxOffice = Number(config.primary_region_max_office_days ?? 2);
const primaryMinHo = Math.max(0, 5 - primaryMaxOffice);
const secondaryMaxOffice = Number(config.secondary_city_max_office_days ?? 1);
const secondaryMinHo = Math.max(0, 5 - secondaryMaxOffice);

let parsedScore = {
  role_fit_score: 0,
  tech_stack_score: 0,
  job_security_score: 0,
  location_and_comp_score: 0,
  match_score: 0,
  matched_track: jobData.initial_track || 'Other / Mismatch',
  location_zone: 'OUTSIDE_ZONES',
  work_mode: 'Unknown',
  office_days_per_week: -1,
  home_office_days_per_week: -1,
  location_rule_passed: true,
  is_unverified_hybrid: false,
  location_notes: 'Not specified',
  is_shady_or_excluded_industry: false,
  requires_commercial_swe_experience: false,
  is_non_building_or_support_grind: false,
  requires_heavy_unrelated_stack: false,
  is_b2b_or_agency_only: false,
  contract_type: 'Unknown',
  requires_cover_letter: false,
  posting_language: 'en',
  ai_proof_assessment: '',
  fit_summary: 'Could not parse Gemini response.',
  key_matching_skills: [],
  missing_or_stretch_skills: []
};

function parseGeminiJson(text) {
  let cleaned = String(text || '{}')
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
  const firstBrace = cleaned.indexOf('{');
  const lastBrace = cleaned.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    cleaned = cleaned.slice(firstBrace, lastBrace + 1);
  }
  try {
    return JSON.parse(cleaned);
  } catch (_) {
    let repaired = '';
    let inString = false;
    let escaped = false;
    for (let i = 0; i < cleaned.length; i++) {
      const ch = cleaned[i];
      if (inString) {
        if (escaped) {
          repaired += ch;
          escaped = false;
        } else if (ch === '\\') {
          repaired += ch;
          escaped = true;
        } else if (ch === '"') {
          repaired += ch;
          inString = false;
        } else if (ch === '\n') {
          repaired += '\\n';
        } else if (ch === '\r') {
          repaired += '\\r';
        } else if (ch === '\t') {
          repaired += '\\t';
        } else if (ch.charCodeAt(0) < 32) {
          repaired += ' ';
        } else {
          repaired += ch;
        }
      } else {
        if (ch === '"') {
          repaired += ch;
          inString = true;
        } else if (ch === ',') {
          let j = i + 1;
          while (j < cleaned.length && /\s/.test(cleaned[j])) j++;
          if (cleaned[j] === ']' || cleaned[j] === '}') {
            continue;
          }
          repaired += ch;
        } else {
          repaired += ch;
        }
      }
    }
    return JSON.parse(repaired);
  }
}

let parseSucceeded = false;
try {
  const parts = geminiResp?.candidates?.[0]?.content?.parts || [];
  const answerPart = [...parts].reverse().find((p) => !p.thought && typeof p.text === 'string');
  if (answerPart?.text && answerPart.text.trim()) {
    parsedScore = { ...parsedScore, ...parseGeminiJson(answerPart.text) };
    parseSucceeded = true;
  }
} catch (e) {
  parsedScore.fit_summary = `JSON parse fallback: ${e.message}`;
}

const roleFitScore = Math.max(0, Math.min(35, Math.round(Number(parsedScore.role_fit_score) || 0)));
const techStackScore = Math.max(0, Math.min(30, Math.round(Number(parsedScore.tech_stack_score) || 0)));
const jobSecurityScore = Math.max(0, Math.min(20, Math.round(Number(parsedScore.job_security_score) || 0)));
const locationCompScore = Math.max(0, Math.min(15, Math.round(Number(parsedScore.location_and_comp_score) || 0)));

const subSum = roleFitScore + techStackScore + jobSecurityScore + locationCompScore;
const rawScore = subSum > 0 ? subSum : Math.max(0, Math.min(100, Math.round(Number(parsedScore.match_score) || 0)));

const zone = String(parsedScore.location_zone || 'OUTSIDE_ZONES');
const workMode = String(parsedScore.work_mode || 'Unknown');
const rawOffice = parsedScore.office_days_per_week;
const rawHo = parsedScore.home_office_days_per_week;
const officeDays = (rawOffice !== null && rawOffice !== undefined && rawOffice !== '' && Number.isFinite(Number(rawOffice)) && Number(rawOffice) >= 0)
  ? Math.max(0, Math.min(5, Math.round(Number(rawOffice))))
  : -1;
const hoDays = (rawHo !== null && rawHo !== undefined && rawHo !== '' && Number.isFinite(Number(rawHo)) && Number(rawHo) >= 0)
  ? Math.max(0, Math.min(5, Math.round(Number(rawHo))))
  : -1;

const effectiveOfficeDays = officeDays >= 0 ? officeDays : (hoDays >= 0 ? Math.max(0, 5 - hoDays) : -1);
const effectiveHoDays = hoDays >= 0 ? hoDays : (officeDays >= 0 ? Math.max(0, 5 - officeDays) : -1);

let score = rawScore;
let locationRulePassed = parsedScore.location_rule_passed !== false;
let verificationBanner = '';

if (!parseSucceeded) {
  locationRulePassed = false;
  score = 0;
} else if (zone === 'REMOTE') {
  locationRulePassed = parsedScore.location_rule_passed !== false;
} else if (zone === 'DEBRECEN_1HR_AREA') {
  if (workMode === 'Remote') {
    locationRulePassed = true;
  } else if (workMode === 'Onsite') {
    locationRulePassed = false;
  } else if (effectiveOfficeDays >= 0 && effectiveOfficeDays > primaryMaxOffice) {
    locationRulePassed = false;
  } else if (effectiveHoDays >= 0 && effectiveHoDays < primaryMinHo) {
    locationRulePassed = false;
  } else if ((workMode === 'Hybrid' || workMode === 'Unknown') && effectiveOfficeDays === -1 && effectiveHoDays === -1) {
    locationRulePassed = true;
    score -= 5;
    verificationBanner = `⚠️ WARNING: Office/HO days unspecified — verify max ${primaryMaxOffice} office days/wk (min ${primaryMinHo} days HO) in Debrecen region`;
  } else if (parsedScore.is_unverified_hybrid && locationRulePassed) {
    score -= 5;
    verificationBanner = `⚠️ WARNING: Office/HO days unspecified — verify max ${primaryMaxOffice} office days/wk (min ${primaryMinHo} days HO) in Debrecen region`;
  }
} else if (zone === 'BUDAPEST') {
  if (workMode === 'Remote') {
    locationRulePassed = true;
  } else if (workMode === 'Onsite') {
    locationRulePassed = false;
  } else if (effectiveOfficeDays >= 0 && effectiveOfficeDays > secondaryMaxOffice) {
    locationRulePassed = false;
  } else if (effectiveHoDays >= 0 && effectiveHoDays < secondaryMinHo) {
    locationRulePassed = false;
  } else if ((workMode === 'Hybrid' || workMode === 'Unknown') && effectiveOfficeDays === -1 && effectiveHoDays === -1) {
    locationRulePassed = true;
    score -= 5;
    verificationBanner = `⚠️ WARNING: Office/HO days unspecified — verify max ${secondaryMaxOffice} office day/wk (min ${secondaryMinHo} days HO) in Budapest`;
  } else if (parsedScore.is_unverified_hybrid && locationRulePassed) {
    score -= 5;
    verificationBanner = `⚠️ WARNING: Office/HO days unspecified — verify max ${secondaryMaxOffice} office day/wk (min ${secondaryMinHo} days HO) in Budapest`;
  }
} else {
  // OUTSIDE_ZONES
  if (workMode !== 'Remote') {
    locationRulePassed = false;
  }
}

// Enforce deterministic dealbreaker hard caps & penalties
if (parsedScore.is_b2b_or_agency_only) {
  score = Math.min(score - 15, 60);
}
if (parsedScore.requires_heavy_unrelated_stack) {
  score = Math.min(score, 45);
}
if (parsedScore.is_non_building_or_support_grind) {
  score = Math.min(score, 40);
}
// Drop listing completely whenever location/HO criteria are explicitly not met
if (!locationRulePassed) {
  score = Math.min(score, 30);
}
if (parsedScore.is_shady_or_excluded_industry) {
  score = Math.min(score, 20);
}
if (parsedScore.requires_commercial_swe_experience) {
  score = Math.min(score, 45);
}

score = Math.max(0, Math.min(100, Math.round(score)));

const applyThreshold = Number(config.score_threshold_apply) || 70;
const maybeThreshold = Number(config.score_threshold_maybe) || 50;

let matchTier = 'SKIPPED';
if (!locationRulePassed || parsedScore.is_shady_or_excluded_industry || parsedScore.requires_commercial_swe_experience) {
  matchTier = 'SKIPPED';
} else if (score >= applyThreshold) {
  matchTier = 'STRONG_MATCH';
} else if (score >= maybeThreshold) {
  matchTier = 'MAYBE_MATCH';
}

const scoredAt = new Date().toISOString();

// Update seenJobIds in staticData & prepare binary for seen_jobs.json
const staticData = $getWorkflowStaticData('global');
if (!staticData.seenJobIds) staticData.seenJobIds = {};
staticData.seenJobIds[jobData.job_id] = {
  title: jobData.title,
  company: jobData.company,
  source: jobData.source,
  score,
  tier: matchTier,
  url: jobData.url,
  scored_at: scoredAt
};

const seenJsonStr = JSON.stringify(staticData.seenJobIds, null, 2);
const seenBinary = await this.helpers.prepareBinaryData(
  Buffer.from(seenJsonStr, 'utf8'),
  'seen_jobs.json',
  'application/json'
);

return [{
  json: {
    job_id: jobData.job_id,
    raw_id: jobData.raw_id,
    source: jobData.source,
    title: jobData.title,
    company: jobData.company,
    location: jobData.location,
    url: jobData.url,
    posted_date: jobData.posted_date,
    salary_info: jobData.salary_info,
    clean_description: jobData.clean_description,
    role_fit_score: roleFitScore,
    tech_stack_score: techStackScore,
    job_security_score: jobSecurityScore,
    location_and_comp_score: locationCompScore,
    raw_score: rawScore,
    match_score: score,
    matched_track: parsedScore.matched_track,
    location_zone: zone,
    work_mode: workMode,
    office_days_per_week: effectiveOfficeDays,
    home_office_days_per_week: effectiveHoDays,
    location_rule_passed: locationRulePassed,
    is_unverified_hybrid: Boolean(parsedScore.is_unverified_hybrid || verificationBanner),
    verification_banner: verificationBanner,
    location_notes: parsedScore.location_notes,
    is_shady_or_excluded_industry: Boolean(parsedScore.is_shady_or_excluded_industry),
    requires_commercial_swe_experience: Boolean(parsedScore.requires_commercial_swe_experience),
    is_non_building_or_support_grind: Boolean(parsedScore.is_non_building_or_support_grind),
    requires_heavy_unrelated_stack: Boolean(parsedScore.requires_heavy_unrelated_stack),
    is_b2b_or_agency_only: Boolean(parsedScore.is_b2b_or_agency_only),
    contract_type: parsedScore.contract_type || 'Unknown',
    requires_cover_letter: Boolean(parsedScore.requires_cover_letter),
    posting_language: parsedScore.posting_language || 'en',
    ai_proof_assessment: parsedScore.ai_proof_assessment || '',
    fit_summary: parsedScore.fit_summary,
    key_matching_skills: parsedScore.key_matching_skills || [],
    missing_or_stretch_skills: parsedScore.missing_or_stretch_skills || [],
    match_tier: matchTier,
    scored_at: scoredAt
  },
  binary: {
    seen_jobs_bin: seenBinary
  }
}];
""".strip()

JS_BUILD_CV_PROMPT = r"""
const config = $('Initialize Profile and Settings').first().json;
const job = $('Parse Score and Update Seen Jobs').first().json;

const candidateName = config.candidate_name || 'the candidate';
const rawSec = String(config.secondary_cv_language || 'none').trim().toLowerCase();
const hasSecondary = Boolean(rawSec && rawSec !== 'none' && rawSec !== 'en');
const secLangName = config.secondary_cv_language_name || rawSec.toUpperCase();
const generateCoverLetter = Boolean(job.requires_cover_letter) || Boolean(config.always_generate_cover_letter);

const cvIntro = hasSecondary
  ? `Your task is to generate a tailored, ATS-optimized CV in BOTH English (cv_en) and ${secLangName} (cv_secondary) for ${candidateName}, tailored specifically to the target job listing.`
  : `Your task is to generate a tailored, ATS-optimized CV in English (cv_en) for ${candidateName}, tailored specifically to the target job listing.`;

const clIntro = generateCoverLetter
  ? (hasSecondary
      ? `Because this job listing requests a cover letter (or cover letter generation is forced), ALSO generate a tailored cover letter in BOTH English (cover_letter_en) and ${secLangName} (cover_letter_secondary).`
      : 'Because this job listing requests a cover letter (or cover letter generation is forced), ALSO generate a tailored cover letter in English (cover_letter_en) and leave cover_letter_secondary empty "".')
  : 'Do NOT generate a cover letter for this job (return empty strings "" for cover_letter_en and cover_letter_secondary).';

const secondarySchemaNote = hasSecondary
  ? `"cv_secondary": {
    "target_headline": "string (${secLangName})",
    "executive_summary": "string (3-4 sentences in ${secLangName})",
    "skill_groups": [{"category": "string", "skills": ["string"]}],
    "experience": [{"company": "string", "role": "string", "period": "string", "location": "string", "bullets": ["string"]}],
    "education": [{"institution": "string", "degree": "string", "period": "string", "details": "string"}],
    "certifications": ["string"],
    "languages": ["string"]
  },
  "cover_letter_en": "string (empty string if not requested)",
  "cover_letter_secondary": "string (empty string if not requested)",`
  : `"cover_letter_en": "string (empty string if not requested)",`;

const secondaryRuleLine = hasSecondary
  ? `6. In ${secLangName} (cv_secondary), use natural, professional local IT terminology while keeping universal technical terms (Python, Bash, REST API, DevOps, Linux, Grafana, CI/CD, LLM, n8n, Docker, SQL, MES) in their standard industry form.`
  : `6. Keep cv_en terminology crisp, quantified, and ATS-friendly (single-column layout ready).`;

const systemPrompt = `You are an elite executive technical CV & Cover Letter writer in Europe and internationally.
${cvIntro}
${clIntro}

TAILORING & LIGHT INFERENCE RULES:
1. Base all dates, employers, job titles, education, and certifications strictly on ${candidateName}'s Master Profile below. Never invent employers, degrees, or years of experience not present in the Master Profile.
2. POSITIONING FOCUS & HONESTY CONSTRAINT: Frame ${candidateName} accurately based on their Master Profile — emphasizing real-world Enterprise & MES System Integration, AI/Workflow Automation (n8n, REST APIs, webhooks, LLM agents & RAG, SQL, Python/Bash scripting), and Linux/DevOps/Observability engineering rather than commercial software application development if excluded by the Master Profile. Include Change/Release/Incident coordination concisely as supporting enterprise reliability experience where helpful.
3. LIGHT INFERENCE ALLOWED: Within their authentic non-SWE scope from the Master Profile, naturally emphasize and surface realistic tools, practices, and workflows implied by their real employers and roles that align with the target job's keywords for ATS matching.
4. Reorder bullet points and skill groups so the skills most relevant to "${job.title}" at "${job.company}" (Track: ${job.matched_track}) appear first.
5. Keep the content concise enough to fit cleanly on 1 to 2 pages in a single-column ATS layout (4-6 high-impact bullet points per recent primary role, 3-5 bullet points for earlier roles).
${secondaryRuleLine}

OUTPUT FORMAT:
Return ONLY valid JSON matching this exact structure (no markdown code fences, no extra keys):
{
  "cv_en": {
    "target_headline": "string",
    "executive_summary": "string (3-4 sentences)",
    "skill_groups": [{"category": "string", "skills": ["string"]}],
    "experience": [{"company": "string", "role": "string", "period": "string", "location": "string", "bullets": ["string"]}],
    "education": [{"institution": "string", "degree": "string", "period": "string", "details": "string"}],
    "certifications": ["string"],
    "languages": ["string"]
  },
  ${secondarySchemaNote}
  "tailoring_notes": ["short bullet 1", "short bullet 2", "short bullet 3"]
}

CANDIDATE MASTER PROFILE:
${config.candidate_profile}`;

const userPrompt = `Generate the tailored CV JSON${hasSecondary ? ` in English and ${secLangName}` : ' in English'}${generateCoverLetter ? ' plus Cover Letter(s)' : ''} for this job:

Job Title: ${job.title}
Company: ${job.company}
Location / Work Mode: ${job.location} (${job.work_mode})
Matched Track: ${job.matched_track}
Match Score: ${job.match_score}/100
Key Matching Skills to Highlight: ${(job.key_matching_skills || []).join(', ')}
Stretch Areas to Frame Positively: ${(job.missing_or_stretch_skills || []).join(', ')}
Generate Cover Letter: ${generateCoverLetter}

Job Description:
${(job.clean_description || '').slice(0, 4500)}`;

const cvObjectSchema = {
  type: 'OBJECT',
  required: [
    'target_headline',
    'executive_summary',
    'skill_groups',
    'experience',
    'education',
    'certifications',
    'languages'
  ],
  properties: {
    target_headline: { type: 'STRING' },
    executive_summary: { type: 'STRING' },
    skill_groups: {
      type: 'ARRAY',
      items: {
        type: 'OBJECT',
        required: ['category', 'skills'],
        properties: {
          category: { type: 'STRING' },
          skills: { type: 'ARRAY', items: { type: 'STRING' } }
        }
      }
    },
    experience: {
      type: 'ARRAY',
      items: {
        type: 'OBJECT',
        required: ['company', 'role', 'period', 'location', 'bullets'],
        properties: {
          company: { type: 'STRING' },
          role: { type: 'STRING' },
          period: { type: 'STRING' },
          location: { type: 'STRING' },
          bullets: { type: 'ARRAY', items: { type: 'STRING' } }
        }
      }
    },
    education: {
      type: 'ARRAY',
      items: {
        type: 'OBJECT',
        required: ['institution', 'degree', 'period', 'details'],
        properties: {
          institution: { type: 'STRING' },
          degree: { type: 'STRING' },
          period: { type: 'STRING' },
          details: { type: 'STRING' }
        }
      }
    },
    certifications: { type: 'ARRAY', items: { type: 'STRING' } },
    languages: { type: 'ARRAY', items: { type: 'STRING' } }
  }
};

const responseProps = hasSecondary
  ? {
      cv_en: cvObjectSchema,
      cv_secondary: cvObjectSchema,
      cover_letter_en: { type: 'STRING' },
      cover_letter_secondary: { type: 'STRING' },
      tailoring_notes: { type: 'ARRAY', items: { type: 'STRING' } }
    }
  : {
      cv_en: cvObjectSchema,
      cover_letter_en: { type: 'STRING' },
      tailoring_notes: { type: 'ARRAY', items: { type: 'STRING' } }
    };

const requiredFields = hasSecondary
  ? ['cv_en', 'cv_secondary', 'cover_letter_en', 'cover_letter_secondary', 'tailoring_notes']
  : ['cv_en', 'cover_letter_en', 'tailoring_notes'];

const requestBody = {
  systemInstruction: {
    parts: [{ text: systemPrompt }]
  },
  contents: [
    {
      role: 'user',
      parts: [{ text: userPrompt }]
    }
  ],
  generationConfig: {
    temperature: 0.2,
    maxOutputTokens: 8192,
    responseMimeType: 'application/json',
    responseSchema: {
      type: 'OBJECT',
      required: requiredFields,
      properties: responseProps
    }
  }
};

return [{
  json: {
    ...job,
    generate_cover_letter: generateCoverLetter,
    cv_request_body: JSON.stringify(requestBody)
  }
}];
""".strip()

JS_RENDER_ATS_HTML = r"""
const config = $('Initialize Profile and Settings').first().json;
const job = $('Build CV and Cover Letter Prompt').first().json;
const geminiResp = $input.first().json || {};

const candidateName = config.candidate_name || 'Candidate';
const candidateHeadline = config.candidate_headline || 'System Integration & AI Automation Engineer';
const candidateLocation = config.candidate_location || 'Remote / Hybrid';
const candidateEmail = config.candidate_email || 'candidate@example.com';
const candidateLinkedinUrl = config.candidate_linkedin_url || 'https://www.linkedin.com';
const candidateLinkedinDisplay = config.candidate_linkedin_display || candidateLinkedinUrl;
const candidateSlug = config.candidate_file_slug || safeSlug(candidateName, 25) || 'Candidate';

const rawSec = String(config.secondary_cv_language || 'none').trim().toLowerCase();
const hasSecondary = Boolean(rawSec && rawSec !== 'none' && rawSec !== 'en');
const secCode = rawSec.toUpperCase();

const LABELS_BY_LANG = {
  en: {
    summary: 'Executive Summary',
    skills: 'Core Competencies & Technical Skills',
    experience: 'Professional Experience',
    education: 'Education & Academic R&D',
    certs: 'Certifications',
    languages: 'Languages',
    clTitle: 'Cover Letter'
  },
  hu: {
    summary: 'Szakmai Összefoglaló',
    skills: 'Kulcskompetenciák és Technológiák',
    experience: 'Szakmai Tapasztalat',
    education: 'Tanulmányok és Kutatás-Fejlesztés',
    certs: 'Tanúsítványok',
    languages: 'Nyelvtudás',
    clTitle: 'Motivációs Levél'
  },
  de: {
    summary: 'Berufliches Profil',
    skills: 'Kernkompetenzen & Technologien',
    experience: 'Berufserfahrung',
    education: 'Ausbildung & Forschung',
    certs: 'Zertifizierungen',
    languages: 'Sprachen',
    clTitle: 'Anschreiben'
  },
  pl: {
    summary: 'Podsumowanie Zawodowe',
    skills: 'Kluczowe Kompetencje i Technologie',
    experience: 'Doświadczenie Zawodowe',
    education: 'Wykształcenie i Badania',
    certs: 'Certyfikaty',
    languages: 'Języki',
    clTitle: 'List Motywacyjny'
  }
};

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function safeSlug(str, maxLen = 30) {
  return String(str || 'Job')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, maxLen) || 'Job';
}

function parseGeminiJson(text) {
  let cleaned = String(text || '{}')
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
  const firstBrace = cleaned.indexOf('{');
  const lastBrace = cleaned.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    cleaned = cleaned.slice(firstBrace, lastBrace + 1);
  }
  try {
    return JSON.parse(cleaned);
  } catch (_) {
    let repaired = '';
    let inString = false;
    let escaped = false;
    for (let i = 0; i < cleaned.length; i++) {
      const ch = cleaned[i];
      if (inString) {
        if (escaped) {
          repaired += ch;
          escaped = false;
        } else if (ch === '\\') {
          repaired += ch;
          escaped = true;
        } else if (ch === '"') {
          repaired += ch;
          inString = false;
        } else if (ch === '\n') {
          repaired += '\\n';
        } else if (ch === '\r') {
          repaired += '\\r';
        } else if (ch === '\t') {
          repaired += '\\t';
        } else if (ch.charCodeAt(0) < 32) {
          repaired += ' ';
        } else {
          repaired += ch;
        }
      } else {
        if (ch === '"') {
          repaired += ch;
          inString = true;
        } else if (ch === ',') {
          let j = i + 1;
          while (j < cleaned.length && /\s/.test(cleaned[j])) j++;
          if (cleaned[j] === ']' || cleaned[j] === '}') {
            continue;
          }
          repaired += ch;
        } else {
          repaired += ch;
        }
      }
    }
    return JSON.parse(repaired);
  }
}

let generated = {};
try {
  const parts = geminiResp?.candidates?.[0]?.content?.parts || [];
  const answerPart = [...parts].reverse().find((p) => !p.thought && typeof p.text === 'string');
  generated = parseGeminiJson(answerPart?.text || '{}');
} catch (e) {
  throw new Error(`Failed to parse Gemini CV JSON: ${e.message}`);
}

function renderCvHtml(cv, langCode) {
  const labels = LABELS_BY_LANG[langCode] || LABELS_BY_LANG.en;

  const skillRows = (cv.skill_groups || []).map((sg) =>
    `<div class="skill-row"><span class="skill-cat">${esc(sg.category)}:</span> <span class="skill-list">${(sg.skills || []).map(esc).join(' • ')}</span></div>`
  ).join('\n');

  const expBlocks = (cv.experience || []).map((exp) => {
    const bullets = (exp.bullets || []).map((b) => `<li>${esc(b)}</li>`).join('\n');
    return `
      <div class="exp-item">
        <div class="exp-header">
          <div>
            <span class="exp-role">${esc(exp.role)}</span>
            <span class="exp-company"> — ${esc(exp.company)}</span>
          </div>
          <div class="exp-meta">${esc(exp.period)} | ${esc(exp.location)}</div>
        </div>
        <ul class="exp-bullets">${bullets}</ul>
      </div>`;
  }).join('\n');

  const eduBlocks = (cv.education || []).map((ed) => `
    <div class="edu-item">
      <div class="exp-header">
        <div><strong>${esc(ed.degree)}</strong> — ${esc(ed.institution)}</div>
        <div class="exp-meta">${esc(ed.period)}</div>
      </div>
      ${ed.details ? `<div class="edu-details">${esc(ed.details)}</div>` : ''}
    </div>`
  ).join('\n');

  const certList = (cv.certifications || []).map((c) => `<li>${esc(c)}</li>`).join('\n');
  const langList = (cv.languages || []).map((l) => `<span class="lang-item">${esc(l)}</span>`).join(' &nbsp;|&nbsp; ');

  return `<!DOCTYPE html>
<html lang="${esc(langCode)}">
<head>
<meta charset="UTF-8">
<title>${esc(candidateName)} - CV (${esc(langCode.toUpperCase())})</title>
<style>
  @page { size: A4; margin: 12mm 14mm 12mm 14mm; }
  * { box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.42;
    color: #1a202c;
    margin: 0;
    padding: 0;
  }
  .header {
    border-bottom: 2px solid #1e3a8a;
    padding-bottom: 8px;
    margin-bottom: 10px;
  }
  .name {
    font-size: 20pt;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
    letter-spacing: 0.3px;
  }
  .headline {
    font-size: 11pt;
    font-weight: 600;
    color: #1e3a8a;
    margin: 3px 0 5px 0;
  }
  .contact {
    font-size: 9pt;
    color: #475569;
  }
  .contact a {
    color: #1e3a8a;
    text-decoration: none;
  }
  .section {
    margin-top: 10px;
  }
  .section-title {
    font-size: 10.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #1e3a8a;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 2px;
    margin-bottom: 6px;
  }
  .summary {
    text-align: justify;
    margin: 0;
    color: #1e293b;
  }
  .skill-row {
    margin-bottom: 3px;
  }
  .skill-cat {
    font-weight: 700;
    color: #0f172a;
  }
  .exp-item {
    margin-bottom: 8px;
    page-break-inside: avoid;
  }
  .exp-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
  }
  .exp-role {
    font-weight: 700;
    font-size: 10.3pt;
    color: #0f172a;
  }
  .exp-company {
    font-weight: 600;
    color: #1e3a8a;
  }
  .exp-meta {
    font-size: 9pt;
    color: #475569;
    font-style: italic;
  }
  .exp-bullets {
    margin: 3px 0 0 0;
    padding-left: 16px;
  }
  .exp-bullets li {
    margin-bottom: 2.5px;
  }
  .edu-item {
    margin-bottom: 5px;
    page-break-inside: avoid;
  }
  .edu-details {
    font-size: 9.5pt;
    color: #334155;
    margin-top: 2px;
  }
  .cert-list {
    margin: 2px 0 0 0;
    padding-left: 16px;
  }
  .two-col-footer {
    display: flex;
    justify-content: space-between;
    gap: 20px;
  }
  .two-col-footer > div {
    flex: 1;
  }
</style>
</head>
<body>
  <div class="header">
    <h1 class="name">${esc(candidateName)}</h1>
    <div class="headline">${esc(cv.target_headline || candidateHeadline)}</div>
    <div class="contact">
      ${esc(candidateLocation)} &nbsp;|&nbsp;
      <a href="mailto:${esc(candidateEmail)}">${esc(candidateEmail)}</a> &nbsp;|&nbsp;
      <a href="${esc(candidateLinkedinUrl)}">${esc(candidateLinkedinDisplay)}</a>
    </div>
  </div>

  <div class="section">
    <div class="section-title">${labels.summary}</div>
    <p class="summary">${esc(cv.executive_summary)}</p>
  </div>

  <div class="section">
    <div class="section-title">${labels.skills}</div>
    ${skillRows}
  </div>

  <div class="section">
    <div class="section-title">${labels.experience}</div>
    ${expBlocks}
  </div>

  <div class="section">
    <div class="section-title">${labels.education}</div>
    ${eduBlocks}
  </div>

  <div class="section two-col-footer">
    <div>
      <div class="section-title">${labels.certs}</div>
      <ul class="cert-list">${certList}</ul>
    </div>
    <div>
      <div class="section-title">${labels.languages}</div>
      <div>${langList}</div>
    </div>
  </div>
</body>
</html>`;
}

function renderCoverLetterHtml(text, langCode) {
  const labels = LABELS_BY_LANG[langCode] || LABELS_BY_LANG.en;
  const paragraphs = String(text || '')
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`)
    .join('\n');

  const dateStr = new Date().toISOString().slice(0, 10);
  const titleLabel = `${labels.clTitle} — ${job.title} (${job.company})`;

  return `<!DOCTYPE html>
<html lang="${esc(langCode)}">
<head>
<meta charset="UTF-8">
<title>${esc(candidateName)} - ${esc(labels.clTitle)} (${esc(langCode.toUpperCase())})</title>
<style>
  @page { size: A4; margin: 18mm 20mm 18mm 20mm; }
  body {
    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a202c;
  }
  .header {
    border-bottom: 2px solid #1e3a8a;
    padding-bottom: 8px;
    margin-bottom: 18px;
  }
  .name { font-size: 18pt; font-weight: 700; color: #0f172a; margin: 0; }
  .contact { font-size: 9.5pt; color: #475569; margin-top: 4px; }
  .subject { font-weight: 700; color: #1e3a8a; margin: 14px 0; font-size: 11pt; }
  p { margin: 0 0 11px 0; text-align: justify; }
</style>
</head>
<body>
  <div class="header">
    <h1 class="name">${esc(candidateName)}</h1>
    <div class="contact">${esc(candidateLocation)} &nbsp;|&nbsp; ${esc(candidateEmail)} &nbsp;|&nbsp; ${esc(candidateLinkedinDisplay)}</div>
  </div>
  <div>${esc(dateStr)}</div>
  <div class="subject">${esc(titleLabel)}</div>
  ${paragraphs}
</body>
</html>`;
}

const datePrefix = new Date().toISOString().slice(0, 10);
const companySlug = safeSlug(job.company, 25);
const baseDir = (config.nas_output_dir || '/home/node/.n8n').replace(/\/+$/, '');
const folderPath = baseDir;

const docsToRender = [
  {
    doc_type: 'CV',
    lang: 'EN',
    slot: 'en',
    pdf_filename: `${candidateSlug}_CV_EN_${companySlug}.pdf`,
    html: renderCvHtml(generated.cv_en || {}, 'en')
  }
];

const secCv = generated.cv_secondary || generated.cv_hu;
if (hasSecondary && secCv) {
  docsToRender.push({
    doc_type: 'CV',
    lang: secCode,
    slot: 'secondary',
    pdf_filename: `${candidateSlug}_CV_${secCode}_${companySlug}.pdf`,
    html: renderCvHtml(secCv, rawSec)
  });
}

if (job.generate_cover_letter && generated.cover_letter_en) {
  docsToRender.push({
    doc_type: 'CoverLetter',
    lang: 'EN',
    slot: 'en',
    pdf_filename: `${candidateSlug}_CoverLetter_EN_${companySlug}.pdf`,
    html: renderCoverLetterHtml(generated.cover_letter_en, 'en')
  });
  const secCl = generated.cover_letter_secondary || generated.cover_letter_hu;
  if (hasSecondary && secCl) {
    docsToRender.push({
      doc_type: 'CoverLetter',
      lang: secCode,
      slot: 'secondary',
      pdf_filename: `${candidateSlug}_CoverLetter_${secCode}_${companySlug}.pdf`,
      html: renderCoverLetterHtml(secCl, rawSec)
    });
  }
}

const outputItems = [];
for (const doc of docsToRender) {
  const htmlBin = await this.helpers.prepareBinaryData(
    Buffer.from(doc.html, 'utf8'),
    'index.html',
    'text/html'
  );
  outputItems.push({
    json: {
      ...job,
      doc_type: doc.doc_type,
      doc_lang: doc.lang,
      doc_slot: doc.slot,
      pdf_filename: doc.pdf_filename,
      folder_path: folderPath,
      save_path: `${baseDir}/JobFinder_${datePrefix}_${doc.pdf_filename}`,
      tailoring_notes: generated.tailoring_notes || []
    },
    binary: {
      index_html: htmlBin
    }
  });
}

return outputItems;
""".strip()

JS_SET_PDF_FILENAME = r"""
const config = $('Initialize Profile and Settings').first().json;
const items = $input.all();
const out = [];
const fallbackName = `${config.candidate_file_slug || 'Candidate'}_CV.pdf`;

for (let i = 0; i < items.length; i++) {
  const item = items[i];
  const meta = item.json || {};
  const pdfBin = item.binary && item.binary.pdf_data;
  if (!pdfBin) {
    throw new Error(`Gotenberg did not return pdf_data binary for ${meta.pdf_filename}`);
  }
  out.push({
    json: meta,
    binary: {
      pdf_data: {
        ...pdfBin,
        fileName: meta.pdf_filename || fallbackName,
        mimeType: 'application/pdf',
        fileExtension: 'pdf'
      }
    }
  });
}

return out;
""".strip()

JS_BUNDLE_DISCORD_STRONG = r"""
const items = $input.all();
if (!items.length) return [];

const firstMeta = items[0].json || {};
const cvEn = items.find((i) => i.json.doc_type === 'CV' && i.json.doc_slot === 'en');
const cvSecondary = items.find((i) => i.json.doc_type === 'CV' && i.json.doc_slot === 'secondary');
const clEn = items.find((i) => i.json.doc_type === 'CoverLetter' && i.json.doc_slot === 'en');
const clSecondary = items.find((i) => i.json.doc_type === 'CoverLetter' && i.json.doc_slot === 'secondary');

const langLabel = cvSecondary ? `EN + ${cvSecondary.json.doc_lang}` : 'EN';
const hoText = firstMeta.home_office_days_per_week >= 0
  ? `${firstMeta.work_mode} (${firstMeta.home_office_days_per_week}d/wk HO, max ${firstMeta.office_days_per_week}d office)`
  : `${firstMeta.work_mode} (${firstMeta.location_notes || 'check HO details'})`;

const rubricLine = `Role ${firstMeta.role_fit_score || 0}/35 | Tech ${firstMeta.tech_stack_score || 0}/30 | Security ${firstMeta.job_security_score || 0}/20 | Loc/Comp ${firstMeta.location_and_comp_score || 0}/15`;
const matchingSkills = (firstMeta.key_matching_skills || []).slice(0, 8).join(', ') || 'See description';
const tailoringBullets = (firstMeta.tailoring_notes || []).slice(0, 3).map((n) => `- ${n}`).join('\n') || `- Tailored to job requirements (${langLabel})`;

const lines = [
  `@everyone 🎯 **Strong Job Match (${firstMeta.match_score}/100) — CV Generated!** — **${firstMeta.title}** at **${firstMeta.company}**`,
  `📂 **Category:** **${firstMeta.matched_track}** | **Source:** ${firstMeta.source} | **Contract:** ${firstMeta.contract_type || 'Unknown'}`,
  firstMeta.verification_banner ? `**${firstMeta.verification_banner}**` : '',
  `**Rubric:** ${rubricLine}`,
  `**Location / Mode:** ${firstMeta.location} — ${hoText}`,
  `**Salary:** ${firstMeta.salary_info || 'Not disclosed'}`,
  firstMeta.ai_proof_assessment ? `**AI-Proof & Security:** ${String(firstMeta.ai_proof_assessment).slice(0, 180)}` : '',
  ``,
  `**Why It Fits You:**`,
  (firstMeta.fit_summary || 'Strong match').slice(0, 300),
  `**Key Matching Skills:** ${matchingSkills.slice(0, 180)}`,
  `**CV Tailoring Highlights (${langLabel} attached):**`,
  tailoringBullets.slice(0, 240),
  `**Saved Output Folder:** \`${firstMeta.folder_path}\``,
  `**Direct Apply Link:** ${firstMeta.url}`
].filter((l) => l !== '');

const discordContent = lines.join('\n').slice(0, 1900);

const out = [];

if (cvEn && cvEn.binary?.pdf_data) {
  const binary = { doc_en: cvEn.binary.pdf_data };
  if (cvSecondary && cvSecondary.binary?.pdf_data) {
    binary.doc_secondary = cvSecondary.binary.pdf_data;
  }
  out.push({
    json: {
      job_id: firstMeta.job_id,
      discord_content: discordContent
    },
    binary
  });
}

if (clEn && clEn.binary?.pdf_data) {
  const clLabel = clSecondary ? `EN + ${clSecondary.json.doc_lang}` : 'EN';
  const clContent = `✉️ **Tailored Cover Letters (${clLabel})** for **${firstMeta.title}** at **${firstMeta.company}** *(posting requested a cover letter)*\n${firstMeta.url}`.slice(0, 1900);
  const clBinary = { doc_en: clEn.binary.pdf_data };
  if (clSecondary && clSecondary.binary?.pdf_data) {
    clBinary.doc_secondary = clSecondary.binary.pdf_data;
  }
  out.push({
    json: {
      job_id: firstMeta.job_id,
      discord_content: clContent
    },
    binary: clBinary
  });
}

return out;
""".strip()

JS_RETURN_ONE_ITEM_TO_LOOP = r"""
const first = $input.first();
return [{
  json: {
    completed_job_id: first?.json?.job_id || 'done'
  }
}];
""".strip()

JS_BUILD_DISCORD_MAYBE = r"""
const job = $input.first().json || {};
const hoText = job.home_office_days_per_week >= 0
  ? `${job.work_mode} (${job.home_office_days_per_week}d/wk HO, max ${job.office_days_per_week}d office)`
  : `${job.work_mode} (${job.location_notes || 'unspecified'})`;

const rubricLine = `Role ${job.role_fit_score || 0}/35 | Tech ${job.tech_stack_score || 0}/30 | Security ${job.job_security_score || 0}/20 | Loc/Comp ${job.location_and_comp_score || 0}/15`;
const statusBanner = job.verification_banner
  ? `**${job.verification_banner}**`
  : '';

const lines = [
  `🤔 **Maybe Match (${job.match_score}/100)** — **${job.title}** at **${job.company}** *(No CV generated)*`,
  `📂 **Category:** **${job.matched_track}** | **Source:** ${job.source} | **Contract:** ${job.contract_type || 'Unknown'}`,
  statusBanner,
  `**Rubric:** ${rubricLine}`,
  `**Location / Mode:** ${job.location} — ${hoText}`,
  `**Salary:** ${job.salary_info || 'Not disclosed'}`,
  job.ai_proof_assessment ? `**AI-Proof & Security:** ${String(job.ai_proof_assessment).slice(0, 180)}` : '',
  `**Assessment:** ${(job.fit_summary || 'Partial match').slice(0, 350)}`,
  `**Link:** ${job.url}`
].filter((l) => l !== '');

return [{
  json: {
    job_id: job.job_id,
    discord_maybe_content: lines.join('\n').slice(0, 1900)
  }
}];
""".strip()


def make_node(name, node_type, type_version, position, parameters, **kwargs):
    node = {
        "parameters": parameters,
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"jobfinder.workflow.{name}")),
        "name": name,
        "type": node_type,
        "typeVersion": type_version,
        "position": position,
    }
    node.update(kwargs)
    return node


def build_from_config(config_path: Path, is_local: bool = False) -> Path:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    raw_profile_path = Path(cfg.get("profile_path", "examples/master_profile.example.md"))
    profile_path = raw_profile_path if raw_profile_path.is_absolute() else (REPO_ROOT / raw_profile_path)
    master_profile = profile_path.read_text(encoding="utf-8")

    raw_out_path = Path(cfg.get("output_path", "jobfinder_n8n_workflow.json"))
    out_path = raw_out_path if raw_out_path.is_absolute() else (REPO_ROOT / raw_out_path)

    init_js = make_init_js(cfg, master_profile)
    sec_lang = str(cfg.get("secondary_cv_language", "hu")).strip().lower()
    has_secondary = bool(sec_lang and sec_lang not in {"none", "en"})
    gotenberg_display = cfg.get("gotenberg_url", "http://gotenberg:3000")
    nas_dir_display = cfg.get("nas_output_dir", "/home/node/.n8n")
    lang_note = (
        f"**EN + {cfg.get('secondary_cv_language_name', sec_lang.upper())} ATS PDF CVs**"
        if has_secondary
        else "**EN ATS PDF CV**"
    )
    sticky_lang_list = (
        f"English + {cfg.get('secondary_cv_language_name', sec_lang.upper())}"
        if has_secondary
        else "English (configurable HU/DE/PL/None)"
    )

    discord_files = [{"inputFieldName": "doc_en"}]
    if has_secondary:
        discord_files.append({"inputFieldName": "doc_secondary"})

    nodes = [
        # Sticky Notes
        make_node(
            "Sticky Note - Setup and Config",
            "n8n-nodes-base.stickyNote",
            1,
            [-640, -260],
            {
                "content": (
                    "## 🚀 JobFinder AI — Self-Hosted n8n Job Hunter (100% Free Stack)\n"
                    "### Quick Setup via n8n Credentials Tab:\n"
                    "1. Open n8n **Credentials** (left sidebar) and create 2 free credentials:\n"
                    "   - **Google Gemini(PaLM) Api**: Paste your free Google AI Studio key (`https://aistudio.google.com/apikey`), keep default host `https://generativelanguage.googleapis.com`\n"
                    "   - **Discord Webhook**: Paste your Discord channel Webhook URL\n"
                    "2. Select those credentials in the **Gemini** and **Discord** nodes (marked in orange until linked).\n"
                    f"3. Check candidate info, languages, and `gotenberg_url` (`{gotenberg_display}`) in **`Initialize Profile and Settings`**, then click **Test workflow**.\n"
                    "4. **Job Categories**: Tier 1 AI & n8n Automation, Enterprise/MES & API Integration; Tier 2 Observability/Linux/DevOps & Technical Solutions.\n"
                    f"5. **Scoring & Pings**: `70+` with valid/unspecified location generates {lang_note}, saves to `{nas_dir_display}`, and pings `@everyone` in Discord. `50-69` sends a quiet 'Maybe' alert (no `@everyone`). Explicit office violations are dropped (`SKIPPED`)."
                ),
                "height": 300,
                "width": 680,
                "color": 4,
            },
        ),
        make_node(
            "Sticky Note - Scraping and Dedup",
            "n8n-nodes-base.stickyNote",
            1,
            [80, -260],
            {
                "content": (
                    "## 🔎 Stage 1: Multi-Source Scraping & Pre-Filter\n"
                    "- **LinkedIn Guest API**: Searches configured target locations and regional radius queries across non-SWE integration/automation/DevOps tracks.\n"
                    "- **NoFluffJobs JSON API**: Pulls configured city and English Remote roles.\n"
                    f"- **Zero-Cost Deduplication**: Checks `{nas_dir_display}/seen_jobs.json` + workflow static data and filters out excluded industries, SWE developer titles, junior, and unrelated stack titles before calling Gemini."
                ),
                "height": 210,
                "width": 760,
                "color": 5,
            },
        ),
        make_node(
            "Sticky Note - Scoring and Routing",
            "n8n-nodes-base.stickyNote",
            1,
            [920, -260],
            {
                "content": (
                    "## 🧠 Stage 2: 4-Part Rubric & Strict Location Gate\n"
                    "- Processes 1 new job at a time with a **4s Wait** node to stay under free-tier 15 RPM limits.\n"
                    "- Uses `gemini-3.5-flash-lite` + deterministic JS enforcement: **Role 35 + Tech 30 + AI-Proof Security 20 + Location/Comp 15**.\n"
                    "- Drops explicit office/location failures (`SKIPPED`), warns when office/HO days are unspecified (`-5` pts), and pings `@everyone` only when CVs are generated."
                ),
                "height": 210,
                "width": 860,
                "color": 6,
            },
        ),
        make_node(
            "Sticky Note - PDF Generation",
            "n8n-nodes-base.stickyNote",
            1,
            [1860, -260],
            {
                "content": (
                    "## 📄 Stage 3: Configurable ATS CV & Cover Letter PDF Pipeline\n"
                    f"- Uses `gemini-3.5-flash-lite` (free tier) to write tailored **{sticky_lang_list}** CVs (and Cover Letters when requested).\n"
                    f"- Renders clean single-column ATS HTML to convert to PDF via **Gotenberg** (`{gotenberg_display}`) to save to `{nas_dir_display}/JobFinder_[Date]_[Filename]` and upload PDFs to **Discord**."
                ),
                "height": 210,
                "width": 980,
                "color": 4,
            },
        ),
        # Triggers
        make_node(
            "Daily 0730 Trigger",
            "n8n-nodes-base.scheduleTrigger",
            1.2,
            [-580, 120],
            {
                "rule": {
                    "interval": [
                        {
                            "field": "cronExpression",
                            "expression": "30 7 * * *",
                        }
                    ]
                }
            },
        ),
        make_node(
            "Manual Test Trigger",
            "n8n-nodes-base.manualTrigger",
            1,
            [-580, 300],
            {},
        ),
        # Initialize Profile and Settings Node
        make_node(
            "Initialize Profile and Settings",
            "n8n-nodes-base.code",
            2,
            [-340, 210],
            {
                "mode": "runOnceForAllItems",
                "jsCode": init_js,
            },
        ),
        # Load Seen Jobs File
        make_node(
            "Load Seen Jobs File",
            "n8n-nodes-base.readWriteFile",
            1,
            [-120, 210],
            {
                "operation": "read",
                "fileSelector": "={{ $json.nas_output_dir }}/seen_jobs.json",
                "dataPropertyName": "data",
                "options": {},
            },
            continueOnFail=True,
            alwaysOutputData=True,
        ),
        # LinkedIn Branch
        make_node(
            "Build LinkedIn Queries",
            "n8n-nodes-base.code",
            2,
            [120, 80],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_BUILD_LINKEDIN_QUERIES,
            },
        ),
        make_node(
            "Fetch LinkedIn Search Cards",
            "n8n-nodes-base.httpRequest",
            4.2,
            [340, 80],
            {
                "method": "GET",
                "url": "={{ $json.search_url }}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "User-Agent",
                            "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        },
                        {
                            "name": "Accept-Language",
                            "value": "en-US,en;q=0.9,hu;q=0.8",
                        },
                    ]
                },
                "options": {
                    "batching": {
                        "batch": {
                            "batchSize": 1,
                            "batchInterval": 1200,
                        }
                    },
                    "response": {
                        "response": {
                            "responseFormat": "text",
                            "outputPropertyName": "data",
                        }
                    },
                    "timeout": 15000,
                },
            },
            continueOnFail=True,
        ),
        make_node(
            "Parse LinkedIn Cards",
            "n8n-nodes-base.code",
            2,
            [560, 80],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_PARSE_LINKEDIN_CARDS,
            },
            alwaysOutputData=True,
        ),
        # NoFluffJobs Branch
        make_node(
            "Build NoFluffJobs Queries",
            "n8n-nodes-base.code",
            2,
            [120, 320],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_BUILD_NFJ_QUERIES,
            },
        ),
        make_node(
            "Fetch NoFluffJobs Search API",
            "n8n-nodes-base.httpRequest",
            4.2,
            [340, 320],
            {
                "method": "POST",
                "url": "https://nofluffjobs.com/api/search/posting?pageTo=1&pageSize=20&salaryCurrency=HUF&salaryPeriod=month&region=hu&language=en-GB",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "User-Agent",
                            "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        },
                        {
                            "name": "Content-Type",
                            "value": "application/json",
                        },
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.request_body }}",
                "options": {
                    "batching": {
                        "batch": {
                            "batchSize": 1,
                            "batchInterval": 800,
                        }
                    },
                    "timeout": 15000,
                },
            },
            continueOnFail=True,
        ),
        make_node(
            "Parse NoFluffJobs Postings",
            "n8n-nodes-base.code",
            2,
            [560, 320],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_PARSE_NFJ_POSTINGS,
            },
            alwaysOutputData=True,
        ),
        # Merge Both Sources
        make_node(
            "Merge Job Sources",
            "n8n-nodes-base.merge",
            3,
            [760, 200],
            {
                "mode": "append",
            },
        ),
        make_node(
            "Combine and Deduplicate Candidates",
            "n8n-nodes-base.code",
            2,
            [960, 200],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_COMBINE_AND_PREFILTER,
            },
        ),
        make_node(
            "Any New Jobs",
            "n8n-nodes-base.if",
            2,
            [1160, 200],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                    },
                    "conditions": [
                        {
                            "id": "cond-has-job-id",
                            "leftValue": "={{ $json.job_id }}",
                            "rightValue": "",
                            "operator": {
                                "type": "string",
                                "operation": "notEmpty",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        # Loop Over Candidate Jobs
        make_node(
            "Loop Over Candidate Jobs",
            "n8n-nodes-base.splitInBatches",
            3,
            [1380, 200],
            {
                "batchSize": 1,
                "options": {},
            },
        ),
        make_node(
            "Fetch Full Job Details",
            "n8n-nodes-base.httpRequest",
            4.2,
            [1600, 200],
            {
                "method": "GET",
                "url": "={{ $json.detail_url }}",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "User-Agent",
                            "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        },
                        {
                            "name": "Accept",
                            "value": "application/json, text/html, */*",
                        },
                    ]
                },
                "options": {
                    "response": {
                        "response": {
                            "responseFormat": "text",
                            "outputPropertyName": "data",
                        }
                    },
                    "timeout": 15000,
                },
            },
            continueOnFail=True,
        ),
        make_node(
            "Extract Clean Job Description and Build Scoring Prompt",
            "n8n-nodes-base.code",
            2,
            [1820, 200],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_EXTRACT_DETAILS_AND_BUILD_SCORING,
            },
        ),
        make_node(
            "Rate Limit Pause Scoring",
            "n8n-nodes-base.wait",
            1.1,
            [2040, 200],
            {
                "resume": "timeInterval",
                "amount": 4,
                "unit": "seconds",
            },
        ),
        make_node(
            "Gemini Score and Filter Job",
            "n8n-nodes-base.httpRequest",
            4.2,
            [2240, 200],
            {
                "method": "POST",
                "url": "=https://generativelanguage.googleapis.com/v1beta/models/{{ $('Initialize Profile and Settings').first().json.gemini_scoring_model }}:generateContent",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googlePalmApi",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Content-Type",
                            "value": "application/json",
                        },
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.scoring_request_body }}",
                "options": {
                    "timeout": 45000,
                },
            },
            credentials={
                "googlePalmApi": {
                    "id": "gemini-api-cred",
                    "name": "Google Gemini(PaLM) Api account",
                }
            },
            retryOnFail=True,
            maxTries=3,
            waitBetweenTries=5000,
        ),
        make_node(
            "Parse Score and Update Seen Jobs",
            "n8n-nodes-base.code",
            2,
            [2460, 200],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_PARSE_SCORE_AND_SAVE_SEEN,
            },
        ),
        make_node(
            "Save Updated Seen Jobs to Disk",
            "n8n-nodes-base.readWriteFile",
            1,
            [2680, 400],
            {
                "operation": "write",
                "fileName": "={{ $('Initialize Profile and Settings').first().json.nas_output_dir }}/seen_jobs.json",
                "dataPropertyName": "seen_jobs_bin",
                "options": {},
            },
            continueOnFail=True,
        ),
        make_node(
            "Log to n8n Data Table Optional",
            "n8n-nodes-base.dataTable",
            1.1,
            [2680, 560],
            {
                "operation": "upsert",
                "dataTableId": {
                    "__rl": True,
                    "value": "",
                    "mode": "list",
                    "cachedResultName": "job_listings",
                },
                "columns": {
                    "mappingMode": "defineBelow",
                    "value": {
                        "job_id": "={{ $json.job_id }}",
                        "source": "={{ $json.source }}",
                        "title": "={{ $json.title }}",
                        "company": "={{ $json.company }}",
                        "location": "={{ $json.location }}",
                        "work_mode": "={{ $json.work_mode }}",
                        "match_score": "={{ $json.match_score }}",
                        "matched_track": "={{ $json.matched_track }}",
                        "match_tier": "={{ $json.match_tier }}",
                        "url": "={{ $json.url }}",
                        "scored_at": "={{ $json.scored_at }}",
                    },
                },
            },
            disabled=True,
            continueOnFail=True,
        ),
        make_node(
            "Route by Match Tier",
            "n8n-nodes-base.switch",
            3.2,
            [3120, 200],
            {
                "rules": {
                    "values": [
                        {
                            "conditions": {
                                "options": {
                                    "caseSensitive": True,
                                    "leftValue": "",
                                    "typeValidation": "strict",
                                },
                                "conditions": [
                                    {
                                        "id": "rule-strong",
                                        "leftValue": "={{ $json.match_tier }}",
                                        "rightValue": "STRONG_MATCH",
                                        "operator": {
                                            "type": "string",
                                            "operation": "equals",
                                        },
                                    }
                                ],
                                "combinator": "and",
                            },
                            "renameOutput": True,
                            "outputKey": "Strong Match 70 plus",
                        },
                        {
                            "conditions": {
                                "options": {
                                    "caseSensitive": True,
                                    "leftValue": "",
                                    "typeValidation": "strict",
                                },
                                "conditions": [
                                    {
                                        "id": "rule-maybe",
                                        "leftValue": "={{ $json.match_tier }}",
                                        "rightValue": "MAYBE_MATCH",
                                        "operator": {
                                            "type": "string",
                                            "operation": "equals",
                                        },
                                    }
                                ],
                                "combinator": "and",
                            },
                            "renameOutput": True,
                            "outputKey": "Maybe Match 50-69",
                        },
                    ]
                },
                "options": {
                    "fallbackOutput": "extra",
                },
            },
        ),
        # Strong Match Branch (70 plus)
        make_node(
            "Build CV and Cover Letter Prompt",
            "n8n-nodes-base.code",
            2,
            [3380, 40],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_BUILD_CV_PROMPT,
            },
        ),
        make_node(
            "Rate Limit Pause CV Gen",
            "n8n-nodes-base.wait",
            1.1,
            [3600, 40],
            {
                "resume": "timeInterval",
                "amount": 5,
                "unit": "seconds",
            },
        ),
        make_node(
            "Gemini Generate Tailored CV and CL",
            "n8n-nodes-base.httpRequest",
            4.2,
            [3820, 40],
            {
                "method": "POST",
                "url": "=https://generativelanguage.googleapis.com/v1beta/models/{{ $('Initialize Profile and Settings').first().json.gemini_cv_model }}:generateContent",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "googlePalmApi",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Content-Type",
                            "value": "application/json",
                        },
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": "={{ $json.cv_request_body }}",
                "options": {
                    "timeout": 240000,
                },
            },
            credentials={
                "googlePalmApi": {
                    "id": "gemini-api-cred",
                    "name": "Google Gemini(PaLM) Api account",
                }
            },
            retryOnFail=True,
            maxTries=3,
            waitBetweenTries=6000,
        ),
        make_node(
            "Render ATS HTML Documents",
            "n8n-nodes-base.code",
            2,
            [4040, 40],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_RENDER_ATS_HTML,
            },
        ),
        make_node(
            "Convert HTML to PDF Gotenberg",
            "n8n-nodes-base.httpRequest",
            4.2,
            [4260, 40],
            {
                "method": "POST",
                "url": "={{ $('Initialize Profile and Settings').first().json.gotenberg_url }}/forms/chromium/convert/html",
                "sendBody": True,
                "contentType": "multipart-form-data",
                "bodyParameters": {
                    "parameters": [
                        {
                            "parameterType": "formBinaryData",
                            "name": "files",
                            "inputDataFieldName": "index_html",
                        },
                        {
                            "name": "marginTop",
                            "value": "0.4",
                        },
                        {
                            "name": "marginBottom",
                            "value": "0.4",
                        },
                        {
                            "name": "marginLeft",
                            "value": "0.45",
                        },
                        {
                            "name": "marginRight",
                            "value": "0.45",
                        },
                        {
                            "name": "printBackground",
                            "value": "true",
                        },
                    ]
                },
                "options": {
                    "response": {
                        "response": {
                            "responseFormat": "file",
                            "outputPropertyName": "pdf_data",
                        }
                    },
                    "timeout": 30000,
                },
            },
            retryOnFail=True,
            maxTries=2,
            waitBetweenTries=3000,
        ),
        make_node(
            "Set PDF Filename and Metadata",
            "n8n-nodes-base.code",
            2,
            [4480, 40],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_SET_PDF_FILENAME,
            },
        ),
        make_node(
            "Save PDF to NAS Folder",
            "n8n-nodes-base.readWriteFile",
            1,
            [4700, 180],
            {
                "operation": "write",
                "fileName": "={{ $json.save_path }}",
                "dataPropertyName": "pdf_data",
                "options": {},
            },
            continueOnFail=True,
        ),
        make_node(
            "Bundle PDFs and Discord Embed",
            "n8n-nodes-base.code",
            2,
            [4920, 40],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_BUNDLE_DISCORD_STRONG,
            },
        ),
        make_node(
            "Send Strong Match PDFs to Discord",
            "n8n-nodes-base.discord",
            2,
            [5140, 40],
            {
                "authentication": "webhook",
                "operation": "sendLegacy",
                "content": "={{ $json.discord_content }}",
                "options": {},
                "files": {
                    "values": discord_files
                },
            },
            credentials={
                "discordWebhookApi": {
                    "id": "discord-webhook-cred",
                    "name": "Discord Webhook account",
                }
            },
        ),
        make_node(
            "Return 1 Item to Loop",
            "n8n-nodes-base.code",
            2,
            [5360, 40],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_RETURN_ONE_ITEM_TO_LOOP,
            },
        ),
        # Maybe Match Branch (50-69)
        make_node(
            "Build Maybe Discord Payload",
            "n8n-nodes-base.code",
            2,
            [3380, 260],
            {
                "mode": "runOnceForAllItems",
                "jsCode": JS_BUILD_DISCORD_MAYBE,
            },
        ),
        make_node(
            "Send Maybe Discord Alert",
            "n8n-nodes-base.discord",
            2,
            [3600, 260],
            {
                "authentication": "webhook",
                "operation": "sendLegacy",
                "content": "={{ $json.discord_maybe_content }}",
                "options": {},
            },
            credentials={
                "discordWebhookApi": {
                    "id": "discord-webhook-cred",
                    "name": "Discord Webhook account",
                }
            },
        ),
    ]

    connections = {
        "Daily 0730 Trigger": {
            "main": [[{"node": "Initialize Profile and Settings", "type": "main", "index": 0}]]
        },
        "Manual Test Trigger": {
            "main": [[{"node": "Initialize Profile and Settings", "type": "main", "index": 0}]]
        },
        "Initialize Profile and Settings": {
            "main": [[{"node": "Load Seen Jobs File", "type": "main", "index": 0}]]
        },
        "Load Seen Jobs File": {
            "main": [
                [
                    {"node": "Build LinkedIn Queries", "type": "main", "index": 0},
                    {"node": "Build NoFluffJobs Queries", "type": "main", "index": 0},
                ]
            ]
        },
        "Build LinkedIn Queries": {
            "main": [[{"node": "Fetch LinkedIn Search Cards", "type": "main", "index": 0}]]
        },
        "Fetch LinkedIn Search Cards": {
            "main": [[{"node": "Parse LinkedIn Cards", "type": "main", "index": 0}]]
        },
        "Parse LinkedIn Cards": {
            "main": [[{"node": "Merge Job Sources", "type": "main", "index": 0}]]
        },
        "Build NoFluffJobs Queries": {
            "main": [[{"node": "Fetch NoFluffJobs Search API", "type": "main", "index": 0}]]
        },
        "Fetch NoFluffJobs Search API": {
            "main": [[{"node": "Parse NoFluffJobs Postings", "type": "main", "index": 0}]]
        },
        "Parse NoFluffJobs Postings": {
            "main": [[{"node": "Merge Job Sources", "type": "main", "index": 1}]]
        },
        "Merge Job Sources": {
            "main": [[{"node": "Combine and Deduplicate Candidates", "type": "main", "index": 0}]]
        },
        "Combine and Deduplicate Candidates": {
            "main": [[{"node": "Any New Jobs", "type": "main", "index": 0}]]
        },
        "Any New Jobs": {
            "main": [
                [{"node": "Loop Over Candidate Jobs", "type": "main", "index": 0}],
                [],
            ]
        },
        "Loop Over Candidate Jobs": {
            "main": [
                [],
                [{"node": "Fetch Full Job Details", "type": "main", "index": 0}],
            ]
        },
        "Fetch Full Job Details": {
            "main": [
                [
                    {
                        "node": "Extract Clean Job Description and Build Scoring Prompt",
                        "type": "main",
                        "index": 0,
                    }
                ]
            ]
        },
        "Extract Clean Job Description and Build Scoring Prompt": {
            "main": [[{"node": "Rate Limit Pause Scoring", "type": "main", "index": 0}]]
        },
        "Rate Limit Pause Scoring": {
            "main": [[{"node": "Gemini Score and Filter Job", "type": "main", "index": 0}]]
        },
        "Gemini Score and Filter Job": {
            "main": [[{"node": "Parse Score and Update Seen Jobs", "type": "main", "index": 0}]]
        },
        "Parse Score and Update Seen Jobs": {
            "main": [
                [
                    {"node": "Route by Match Tier", "type": "main", "index": 0},
                    {"node": "Save Updated Seen Jobs to Disk", "type": "main", "index": 0},
                    {"node": "Log to n8n Data Table Optional", "type": "main", "index": 0},
                ]
            ]
        },
        "Route by Match Tier": {
            "main": [
                [{"node": "Build CV and Cover Letter Prompt", "type": "main", "index": 0}],
                [{"node": "Build Maybe Discord Payload", "type": "main", "index": 0}],
                [{"node": "Loop Over Candidate Jobs", "type": "main", "index": 0}],
            ]
        },
        "Build CV and Cover Letter Prompt": {
            "main": [[{"node": "Rate Limit Pause CV Gen", "type": "main", "index": 0}]]
        },
        "Rate Limit Pause CV Gen": {
            "main": [[{"node": "Gemini Generate Tailored CV and CL", "type": "main", "index": 0}]]
        },
        "Gemini Generate Tailored CV and CL": {
            "main": [[{"node": "Render ATS HTML Documents", "type": "main", "index": 0}]]
        },
        "Render ATS HTML Documents": {
            "main": [[{"node": "Convert HTML to PDF Gotenberg", "type": "main", "index": 0}]]
        },
        "Convert HTML to PDF Gotenberg": {
            "main": [[{"node": "Set PDF Filename and Metadata", "type": "main", "index": 0}]]
        },
        "Set PDF Filename and Metadata": {
            "main": [
                [
                    {"node": "Bundle PDFs and Discord Embed", "type": "main", "index": 0},
                    {"node": "Save PDF to NAS Folder", "type": "main", "index": 0},
                ]
            ]
        },
        "Bundle PDFs and Discord Embed": {
            "main": [[{"node": "Send Strong Match PDFs to Discord", "type": "main", "index": 0}]]
        },
        "Send Strong Match PDFs to Discord": {
            "main": [[{"node": "Return 1 Item to Loop", "type": "main", "index": 0}]]
        },
        "Return 1 Item to Loop": {
            "main": [[{"node": "Loop Over Candidate Jobs", "type": "main", "index": 0}]]
        },
        "Build Maybe Discord Payload": {
            "main": [[{"node": "Send Maybe Discord Alert", "type": "main", "index": 0}]]
        },
        "Send Maybe Discord Alert": {
            "main": [[{"node": "Loop Over Candidate Jobs", "type": "main", "index": 0}]]
        },
    }

    workflow = {
        "name": cfg.get("workflow_name", "JobFinder AI - Automated Job Search and ATS CV Generator"),
        "nodes": nodes,
        "pinData": {},
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "timezone": cfg.get("timezone", "Europe/Budapest"),
            "saveManualExecutions": True,
        },
        "versionId": str(uuid.uuid4()),
        "meta": {
            "templateCredsSetupCompleted": True,
        },
        "id": cfg.get("workflow_id", "jobfinder-ai-workflow"),
        "tags": [],
    }

    # Validate node references and n8n string safety
    node_names = {n["name"] for n in nodes}
    for src, targets in connections.items():
        assert src in node_names, f"Missing source node: {src}"
        for branch in targets.get("main", []):
            for edge in branch:
                assert edge["node"] in node_names, f"Missing target node: {edge['node']} from {src}"
    for n in nodes:
        blob = json.dumps(n["parameters"], ensure_ascii=False)
        for ref in re.findall(r"\$\('([^']+)'\)", blob):
            assert ref in node_names, f"Missing referenced node in {n['name']}: {ref}"
        assert "<" not in n["name"] and ">" not in n["name"], f"Angle bracket in node name: {n['name']}"
        if n["type"] == "n8n-nodes-base.stickyNote":
            c = n["parameters"]["content"]
            assert "<" not in c and ">" not in c, f"Angle bracket in sticky note {n['name']}"
        if n["type"] == "n8n-nodes-base.switch":
            for rule in n["parameters"]["rules"]["values"]:
                ok = rule.get("outputKey", "")
                assert "<" not in ok and ">" not in ok, f"Angle bracket in outputKey: {ok}"

    serialized = json.dumps(workflow, ensure_ascii=False, indent=2)
    if not is_local:
        assert not re.search(r"\b(?:192\.168|10\.\d+|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b", serialized), (
            "Public workflow unexpectedly contains a private LAN IP"
        )
        local_cfg_path = REPO_ROOT / "config.local.json"
        if local_cfg_path.exists():
            local_cfg = json.loads(local_cfg_path.read_text(encoding="utf-8"))
            local_email = local_cfg.get("candidate", {}).get("email", "")
            local_li = local_cfg.get("candidate", {}).get("linkedin_url", "")
            if local_email:
                assert local_email not in serialized, "Public workflow contains local candidate email"
            if local_li:
                assert local_li not in serialized, "Public workflow contains local candidate LinkedIn URL"

    out_path.write_text(serialized, encoding="utf-8")
    print(f"Successfully generated {out_path} ({out_path.stat().st_size} bytes) with {len(nodes)} nodes.")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Build n8n JobFinder workflow JSON from config + Markdown profile.")
    parser.add_argument("--config", type=Path, help="Path to a specific JSON config file.")
    parser.add_argument("--local", action="store_true", help="Build local personal workflow from config.local.json.")
    parser.add_argument("--all", action="store_true", help="Build both public example workflow and local workflow (if present).")
    args = parser.parse_args()

    if args.config:
        cfg_path = args.config if args.config.is_absolute() else (REPO_ROOT / args.config)
        build_from_config(cfg_path, is_local=("local" in cfg_path.name.lower()))
        return

    if args.local:
        local_cfg = REPO_ROOT / "config.local.json"
        if not local_cfg.exists():
            raise FileNotFoundError(f"Local config not found: {local_cfg}")
        build_from_config(local_cfg, is_local=True)
        return

    example_cfg = REPO_ROOT / "examples" / "config.example.json"
    build_from_config(example_cfg, is_local=False)

    if args.all:
        local_cfg = REPO_ROOT / "config.local.json"
        if local_cfg.exists():
            build_from_config(local_cfg, is_local=True)
        else:
            print(f"Skipped local build ({local_cfg} not found).")


if __name__ == "__main__":
    main()
