# SPEC: Job Bot — job search and resume tailoring (Brazil, IT/fullstack)

This document is the technical spec for an AI coding agent (Claude Code / any
VS Code agent) continuing development on this project. Below: context, current
state, hard constraints, and a prioritized backlog. Start with section 4.

## 1. Context and goal

The user (Konstantin) is a fullstack developer, junior/pleno level, looking for IT
jobs in Brazil (Florianópolis / remote). He has no recruiter or HR team — he needs
a tool that:
1. Automatically finds relevant job postings (fullstack/junior/pleno) in Brazil.
2. Prepares a resume tailored to each specific job, based on a full fact base
   (`base_resume.md`), without fabricating experience.
3. Does NOT auto-send applications without human confirmation — it only prepares
   materials and the link; the final action is always the user's.

## 2. Current state (already implemented)

```
job_bot/
├── base_resume.md       # Full fact base about the candidate (NOT the final resume!)
├── config.py             # All settings/keys, loaded from .env / env vars
├── search_jobs.py         # Job search via Adzuna API (Brazil, it-jobs category)
├── tailor_resume.py       # Resume tailoring per job via DeepSeek API
├── send_application.py    # Sends email with resume, ONLY with manual confirmation
├── main.py                 # Runs search_jobs + tailor_resume in one command
├── requirements.txt
├── .env / .env (gitignored) # Real keys go here, never committed
├── .gitignore
└── README.md               # Setup and usage instructions (in Russian, for the user)
```

How it works today:
- `search_jobs.py` queries Adzuna (`https://api.adzuna.com/v1/api/jobs/br/search/{page}`)
  by keywords, saves deduplicated results to `jobs_found.csv`.
- `tailor_resume.py` takes `base_resume.md` (the full fact base, ~1000+ words) and
  uses the DeepSeek API (`deepseek-v4-pro`, via its Anthropic-SDK-compatible
  endpoint) to generate a CONDENSED version (~400-550 words, 4-7 most
  relevant bullets) per job, saved to `applications/<company>_<title>_<id>/resume.md`
  + `job_info.txt` with the job link + a combined `applications/index.csv`.
- `send_application.py` — optional email sending with confirmation (`input()`),
  only works when a job posting has a direct contact email (rare on aggregators).
- No script logs into any platform (LinkedIn, Gupy, Catho, InfoJobs) — that would
  violate their ToS and risk an account ban. Applying on those platforms is manual,
  using the generated resume file.

Scripts are syntax-checked and dry-run tested with fake data. NOT yet tested with
real API keys (not set up yet).

## 3. Hard constraints (do not violate)

- **No automation of login/apply flows on job platforms** (Selenium/Playwright login
  on LinkedIn, Gupy, Catho, InfoJobs, etc.) — this is a deliberate architectural
  decision, not a gap to fill. Do not propose this as an "improvement".
- **No fully-autonomous scheduled runs that apply without human review.** A batch of
  third-party "agentic" skills (browser-login automation, auto-apply platforms,
  self-scheduling agents) was evaluated and deliberately rejected for this project —
  see `SECURITY_REVIEW.md` in this folder. Only a read-only job-search MCP
  (`ai-dev-jobs-mcp`, optional, AI/ML roles) was approved. Do not re-propose the
  rejected tools without discussing the tradeoffs with the user again.
- **The resume must never contain fabricated experience.** `tailor_resume.py`
  already has an explicit anti-fabrication rule in its prompt — preserve this rule
  in any prompt changes.
- **Sending anything (email or otherwise) only happens after explicit user
  confirmation.** No "fully autonomous" mode without a confirm step.
- All keys (Adzuna, DeepSeek, Gmail) go through `.env` / environment variables via
  `config.py` — never hardcode or commit real secrets. `.env` is gitignored.

## 3.1. Progress log (PROGRESS_LOG.md)

The project has a `PROGRESS_LOG.md` — update it after EVERY work session: add a
new entry at the TOP (most recent first), never rewrite or delete old entries.
Entry format and rules are documented at the top of that file itself. Read the
last 1-2 entries before starting work, to know what's already done.

## 4. First steps (where to start in VS Code)

1. Read `README.md`, `config.py`, `search_jobs.py`, `tailor_resume.py` to
   understand the current architecture before changing anything.
2. Help the user get and fill in the API keys in `.env`:
   `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free signup at developer.adzuna.com/signup),
   `DEEPSEEK_API_KEY` (platform.deepseek.com/api_keys). `config.py` already loads
   `.env` via `python-dotenv`.
3. Run `python search_jobs.py "desenvolvedor fullstack junior"` with real keys,
   confirm `jobs_found.csv` actually contains real Brazilian job postings.
4. Run `python tailor_resume.py`, manually review 2-3 generated resumes in
   `applications/` — check they're condensed (~1 page) and relevant.
5. Move on to the backlog (section 5), by priority.

## 5. Backlog (by priority)

### P0 — needed for a working MVP
- [x] `.env` support via `python-dotenv` (done — verify it still works after any
      refactor).
- [x] Filter jobs by seniority level: heuristic in `filters.py` (`is_too_senior`)
      drops titles with senior/lead/gestão terms and, for neutral titles, jobs whose
      description requires ≥5 years. Keeps júnior/pleno (and pleno/sênior hybrids).
      Toggle off with `--include-senior`. Covered by `test_filters.py`.
- [x] Export `resume.md` to PDF via `export_pdf.py` (markdown + xhtml2pdf, pure
      Python, selectable text for ATS). Runs automatically after each resume when
      `EXPORT_PDF` is on; also usable standalone (`python export_pdf.py`).
- [x] Robust error handling for API calls: Adzuna (`search_jobs._get_with_retries`)
      and the resume-tailoring call (`tailor_resume.tailor_one`) now retry transient
      errors (429/5xx/timeouts) with backoff, give clear messages on invalid keys, and
      isolate per-job failures instead of crashing the batch. Also fixed a
      UnicodeEncodeError crash on non-UTF-8 Windows consoles (config.py reconfigures
      stdout/stderr to UTF-8).
- [x] Switched the tailoring model from Anthropic (Claude Sonnet 4.5) to DeepSeek
      (`deepseek-v4-pro`), using DeepSeek's Anthropic-SDK-compatible endpoint
      (`https://api.deepseek.com/anthropic`) — same `anthropic` Python package, just
      different `api_key`/`base_url`/`model`. Reason: ~7x cheaper per resume, and the
      user already uses DeepSeek elsewhere. `ANTHROPIC_API_KEY` was replaced by
      `DEEPSEEK_API_KEY` everywhere (`.env`, `config.py`, error messages).
- [x] Local review/apply dashboard: `dashboard.py` generates
      `applications/dashboard.html` (cards per job: company/location/status, link
      to the job posting, link to the resume PDF). Regenerated automatically by
      `main.py` after tailoring. Nothing is sent or opened automatically.
- [x] Location filter: candidate isn't willing to relocate. `filters.py`
      (`is_local_or_remote`/`filter_out_non_local`) keeps only jobs in
      `config.HOME_CITY` (Florianópolis, default) or remote-and-reachable-from-
      Brazil. Drops on-site jobs elsewhere. For INTERNATIONAL sources
      (remotive-/arbeitnow-/remoteok-/jobicy-/themuse- id prefixes) a remote
      job must be Brazil or genuinely global (worldwide/anywhere/flexible/
      LatAm) — `_remote_region_ok` drops jobs geo-locked to another country
      (e.g. "Remoto (Berlin)", "Remoto (México)", India-only), which the
      German/Mexico/India leaks on the first big run exposed. Adzuna (numeric
      ids) and Jooble are BR APIs, trusted as Brazil (no region check). Toggle
      off with `--any-location`. Covered by `test_filters.py`.
- [x] Hybrid jobs treated as on-site: a hybrid role ("híbrido: 3x presencial
      / 2x remoto") requires physical presence, so `filters._is_hybrid`
      flags it and `is_local_or_remote` keeps it only if it's in HOME_CITY —
      hybrid SP/RJ jobs were leaking through because "remoto" appears in the
      description. On-site = Florianópolis only; remote = anywhere reachable
      from Brazil. Covered by `test_filters.py`.

### P1 — usability and quality
- [ ] Track "already processed" jobs across runs (currently `tailor_resume.py`
      skips based on existing folder — fine, but `search_jobs.py` overwrites
      `jobs_found.csv` fully each run — should accumulate/dedupe across runs).
- [ ] Simple CLI review step: before spending DeepSeek API calls on every job
      found, let the user look at `jobs_found.csv` and pick which ones to tailor
      (`--only-ids 1,2,3` or an interactive picker).
- [x] More search sources: added Remotive, Arbeitnow, RemoteOK, Jobicy, and
      The Muse (`extra_sources.py`) — all public JSON APIs, no login, no API
      key. Most are remote-only by nature (The Muse also returns Brazil
      on-site, filtered down by the location filter), pairing with the
      location filter. No reliable Portuguese keyword search on any of them,
      so all are filtered by a broad dev-relevance regex on title/tags
      (`config.RELEVANCE_KEYWORDS` — fullstack/backend/frontend/react/node/
      python/php/etc., broadened from the original fullstack-only). Toggle
      individually via `ENABLE_REMOTIVE`/`ENABLE_ARBEITNOW`/`ENABLE_REMOTEOK`/
      `ENABLE_JOBICY`/`ENABLE_THEMUSE` in `.env`. Parsing logic verified
      offline against fixtures matching each API's documented schema (sandbox
      network egress blocks these domains directly, same as Adzuna/DeepSeek —
      live verification is on the user, locally; Remotive/Arbeitnow/RemoteOK
      have been confirmed live by the user, Jobicy/The Muse not yet).
      Gupy/Vagas.com/InfoJobs/Catho were explicitly evaluated with the user
      on 2026-07-22 and declined for now (no public no-login API; scraping
      public pages carries ToS risk) — see PROGRESS_LOG.md. LinkedIn/login
      automation remains out of scope per the project's own hard constraint.
- [x] Broadened Adzuna coverage: `search_jobs.py` now runs three Adzuna
      passes (dedup by id) — the user keyword (`what`), a broad `what_or`
      pass OR-ing many dev terms (`config.ADZUNA_BROAD_OR`), and the local
      `where=HOME_CITY` pass — via a reusable `_collect_adzuna_pass` helper.
      The broad `what_or` pass is the biggest volume lever within Brazil.
- [x] Broadened remote-source relevance from fullstack-only to a
      config-driven dev keyword set (`config.RELEVANCE_KEYWORDS`), then made
      it a FINAL GUARD applied to ALL sources (`filters.is_dev_relevant` /
      `filters.filter_out_irrelevant`, called in `search_jobs.py` before the
      seniority/location filters). Reason: after broadening, the wide Adzuna
      `what_or` pass and the English remote boards leaked lots of non-dev
      jobs (nutrition, telecom, reception, support, HR) — on one live run 52
      found → 35 non-dev dropped → 17 clean dev jobs. Also fixed a regex bug:
      the keyword ".net" was unescaped, so its "." matched any char and
      caught "internet" (telecom jobs); now escaped/word-bounded
      (`\.net\b`, `\breact\b`, etc.). `RELEVANCE_KEYWORDS` is env-tunable.
      `_is_dev_relevant`/`_normalize` moved from `extra_sources.py` to
      `filters.py` (single source of truth; extra_sources imports it).
- [x] Added Jooble (`extra_sources.fetch_jooble`) — a legitimate job
      aggregator with a public POST API (free key `JOOBLE_API_KEY`), NOT
      scraping. Best Brazil/Florianópolis coverage of all sources; has real
      Portuguese keyword search so it bypasses the relevance regex. Two
      queries per run (local HOME_CITY + remote Brasil), deduped. Inactive
      without a key. Schema from documented API, not live-verified in sandbox.
      Decided WITH the user (2026-07-22) as the legal alternative to Apify/
      RapidAPI LinkedIn scrapers, which the user considered but declined —
      those still violate LinkedIn's ToS even though they don't touch the
      user's personal account. LinkedIn scraping (direct or via third-party
      actors) stays out of scope.
- [x] Adzuna location-scoped reinforcement pass: `search_jobs.py` now also
      queries Adzuna with `where=HOME_CITY` (2 pages) in addition to the
      broad keyword search, to surface local Florianópolis listings that the
      relevance-ranked broad search might not show within `max_pages`.
- [x] Broadened default `SEARCH_KEYWORDS` from "desenvolvedor fullstack
      junior" to "desenvolvedor fullstack" — the literal word "junior" in
      Adzuna's free-text search was excluding postings titled just "Pleno"
      that `filters.is_too_senior` would have kept anyway. Level filtering is
      now entirely the filter's job, not the search string's.
- [~] Unit tests (`pytest`) for pure functions: `test_filters.py`
      (`slugify`, `is_too_senior`, `filter_out_senior`, `is_local_or_remote`,
      `filter_out_non_local`) and `test_extra_sources.py` (fixture-based
      tests for Remotive/Arbeitnow/RemoteOK/Jobicy/The Muse parsing +
      broadened `_is_dev_relevant`). Still missing: CSV
      parsing, prompt building, Adzuna `_adzuna_job_to_dict`/reinforcement
      pass (needs a live-network-shaped mock, not done yet).

### P2 — nice to have
- [ ] Lightweight status tracker on top of `applications/index.csv` (statuses:
      found → resume ready → applied → response received), updated manually or
      via a small CLI command.
- [ ] Self-notification email (to vestek70@gmail.com) about new jobs after each
      run, instead of checking files by hand.

## 6. Definition of Done for MVP

- `python main.py "desenvolvedor fullstack junior"` with real keys finds Brazilian
  job postings and generates tailored resumes with no fabricated experience.
- Each generated resume is roughly one page and relevant to its job.
- The user can look at `applications/index.csv`, open the job link, and manually
  apply with the ready-made file — the script never performs an action on the
  user's behalf on a third-party platform.
