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
├── tailor_resume.py       # Resume tailoring per job via Anthropic API
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
  uses the Claude API to generate a CONDENSED version (~400-550 words, 4-7 most
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
- All keys (Adzuna, Anthropic, Gmail) go through `.env` / environment variables via
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
   `ANTHROPIC_API_KEY`. `config.py` already loads `.env` via `python-dotenv`.
3. Run `python search_jobs.py "desenvolvedor fullstack junior"` with real keys,
   confirm `jobs_found.csv` actually contains real Brazilian job postings.
4. Run `python tailor_resume.py`, manually review 2-3 generated resumes in
   `applications/` — check they're condensed (~1 page) and relevant.
5. Move on to the backlog (section 5), by priority.

## 5. Backlog (by priority)

### P0 — needed for a working MVP
- [x] `.env` support via `python-dotenv` (done — verify it still works after any
      refactor).
- [ ] Filter jobs by seniority level: Adzuna doesn't always return a structured
      seniority field — need a heuristic (filter out "senior", "sênior",
      "especialista", etc. from title/description when searching junior/pleno).
- [ ] Export `resume.md` to PDF (most application forms require PDF/DOCX, not
      Markdown). Options: `pandoc`, or `markdown2`/`weasyprint` + `wkhtmltopdf`.
- [ ] Robust error handling for API calls (rate limits, timeouts, invalid keys)
      with clear messages instead of raw tracebacks.

### P1 — usability and quality
- [ ] Track "already processed" jobs across runs (currently `tailor_resume.py`
      skips based on existing folder — fine, but `search_jobs.py` overwrites
      `jobs_found.csv` fully each run — should accumulate/dedupe across runs).
- [ ] Simple CLI review step: before spending Anthropic API calls on every job
      found, let the user look at `jobs_found.csv` and pick which ones to tailor
      (`--only-ids 1,2,3` or an interactive picker).
- [ ] More search sources beyond Adzuna — evaluate which Brazilian job boards
      (Gupy, Vagas.com, InfoJobs, Catho) expose a public RSS/JSON feed without login.
- [ ] Unit tests (`pytest`) for pure functions: `slugify`, CSV parsing, prompt
      building.

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
