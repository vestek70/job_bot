You are continuing development on `job_bot`, a semi-automatic job-search and
resume-tailoring tool for a fullstack developer (junior/pleno) applying to jobs in
Brazil. This is not a greenfield project — read before you write anything.

## Step 1 — Read these files, in this order, before doing anything else

1. `PROGRESS_LOG.md` — read the top 2-3 entries (most recent first) to know what was
   just done and what's still open. Do not skip this.
2. `SPEC.md` — full technical spec: context, current architecture, hard constraints,
   and a prioritized backlog (P0/P1/P2) with a Definition of Done.
3. `README.md` — setup and usage instructions (in Russian, written for the user).
4. `SECURITY_REVIEW.md` — a security review of a batch of third-party "agentic job
   search" tools/skills the user considered. Most were rejected. Do not re-suggest
   them without re-discussing tradeoffs with the user — see SPEC.md section 3 for
   why.

## Step 2 — Non-negotiable constraints (from SPEC.md, repeated here because they matter)

- **Never automate login or apply flows on job platforms** (no Selenium/Playwright
  login on LinkedIn, Gupy, Catho, InfoJobs, etc.). This is a deliberate decision, not
  a missing feature.
- **Never send an application without explicit human confirmation.** No autonomous
  "auto-apply" mode, no unattended scheduled runs that submit anything.
- **Never fabricate experience, companies, titles, technologies, or metrics** in the
  generated resumes. `tailor_resume.py` already enforces this in its prompt — keep
  that rule intact if you touch it.
- Keep all API keys in `.env` (already gitignored) — never hardcode or commit
  secrets.

## Step 3 — Current repo/GitHub state

The project should be connected to `https://github.com/vestek70/job_bot.git`. Check
`git status` and `git remote -v` first — a previous session had a broken `.git` here
(stuck `index.lock` from a network-mount issue) that the user has since cleaned up
manually. Verify the repo is in a sane state (init if needed, first commit, remote
set, pushed) before assuming it's already done. If `.mcp.json` in this folder isn't
picked up automatically, check it — it defines `github-mcp-server` (needs
`GITHUB_PERSONAL_ACCESS_TOKEN` in the environment) and `context7`.

## Step 4 — Get the tool actually working end to end

1. Confirm `.env` has real values for `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (free signup:
   developer.adzuna.com/signup), and `DEEPSEEK_API_KEY` (platform.deepseek.com/api_keys).
   If any are missing, stop
   and ask the user for them — don't guess or proceed with fake keys.
2. Run `python search_jobs.py "desenvolvedor fullstack junior"` and confirm
   `jobs_found.csv` has real Brazilian listings.
3. Run `python tailor_resume.py` and manually read 2-3 generated resumes in
   `applications/` — confirm they're ~1 page, relevant, and contain nothing not in
   `base_resume.md`.
4. Only after that works, move to the backlog in `SPEC.md` section 5, in priority
   order (P0 first: `.env`/dotenv is already done — check off what's already done,
   then filtering out senior-level postings, then PDF export, then error handling).

## Step 5 — Log your work

Before you finish this session, add a new entry at the TOP of `PROGRESS_LOG.md`
following the exact format documented in that file's header (date, what was done,
files changed, how it was verified, what's next). Do not rewrite or delete older
entries.

## What to do if you get stuck or want to change direction

If you think a rejected tool from `SECURITY_REVIEW.md` should be reconsidered, or
you want to relax one of the constraints in Step 2, stop and ask the user directly —
don't decide unilaterally. Otherwise, work through the backlog and keep the resume
generation honest and the applying-to-jobs step manual.
