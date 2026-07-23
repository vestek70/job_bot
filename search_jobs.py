"""
Busca vagas de emprego na Adzuna API (Brasil) e salva em CSV para revisão.

Requer variáveis de ambiente:
  ADZUNA_APP_ID
  ADZUNA_APP_KEY

Cadastro gratuito: https://developer.adzuna.com/signup
"""
import csv
import sys
import time

import requests

import config


def fetch_page(page: int, keywords: str) -> dict:
    url = f"https://api.adzuna.com/v1/api/jobs/{config.COUNTRY}/search/{page}"
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "results_per_page": config.RESULTS_PER_PAGE,
        "what": keywords,
        "category": config.CATEGORY,
        "content-type": "application/json",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def search_jobs(keywords: str = None, max_pages: int = None) -> list:
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        print(
            "ERRO: defina ADZUNA_APP_ID e ADZUNA_APP_KEY (cadastro gratuito em "
            "https://developer.adzuna.com/signup)",
            file=sys.stderr,
        )
        sys.exit(1)

    keywords = keywords or config.SEARCH_KEYWORDS
    max_pages = max_pages or config.MAX_PAGES

    all_jobs = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        data = fetch_page(page, keywords)
        results = data.get("results", [])
        if not results:
            break
        for job in results:
            job_id = job.get("id")
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            all_jobs.append(
                {
                    "id": job_id,
                    "title": (job.get("title") or "").strip(),
                    "company": (job.get("company") or {}).get("display_name", ""),
                    "location": (job.get("location") or {}).get("display_name", ""),
                    "salary_min": job.get("salary_min", ""),
                    "salary_max": job.get("salary_max", ""),
                    "description": (job.get("description") or "").strip(),
                    "redirect_url": job.get("redirect_url", ""),
                    "created": job.get("created", ""),
                }
            )
        time.sleep(1)  # não sobrecarregar a API

    return all_jobs


def save_jobs_csv(jobs: list, path: str = None):
    path = path or config.JOBS_CSV
    fieldnames = [
        "id", "title", "company", "location", "salary_min",
        "salary_max", "description", "redirect_url", "created",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            writer.writerow(job)
    print(f"{len(jobs)} vagas salvas em {path}")


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else None
    found = search_jobs(kw)
    save_jobs_csv(found)
