"""
Busca vagas de emprego na Adzuna API (Brasil) e salva em CSV para revisão.

Requer variáveis de ambiente:
  ADZUNA_APP_ID
  ADZUNA_APP_KEY

Cadastro gratuito: https://developer.adzuna.com/signup

Uso:
  python search_jobs.py "desenvolvedor fullstack junior"
  python search_jobs.py "desenvolvedor fullstack" --include-senior
"""
import argparse
import csv
import sys
import time

import requests

import config
from extra_sources import fetch_all_extra_sources
from filters import filter_out_non_local, filter_out_senior


class AdzunaError(Exception):
    """Erro tratável de comunicação com a Adzuna (mensagem amigável já embutida)."""


def _get_with_retries(url: str, params: dict) -> dict:
    """GET com timeout + retry exponencial em erros transitórios (429/5xx/timeout)."""
    last_exc = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT)
        except requests.exceptions.Timeout as e:
            last_exc = e
            wait = config.RETRY_BACKOFF * attempt
            print(f"  timeout (tentativa {attempt}/{config.MAX_RETRIES}), "
                  f"repetindo em {wait:.0f}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        except requests.exceptions.ConnectionError as e:
            raise AdzunaError(
                "Sem conexão com a Adzuna. Verifique sua internet e tente de novo."
            ) from e

        if resp.status_code in (401, 403):
            raise AdzunaError(
                "Chaves da Adzuna inválidas ou sem permissão (HTTP "
                f"{resp.status_code}). Confira ADZUNA_APP_ID / ADZUNA_APP_KEY no .env "
                "(cadastro: https://developer.adzuna.com/signup)."
            )
        if resp.status_code == 429:
            wait = config.RETRY_BACKOFF * attempt
            print(f"  limite de taxa (429), aguardando {wait:.0f}s "
                  f"(tentativa {attempt}/{config.MAX_RETRIES})...", file=sys.stderr)
            time.sleep(wait)
            last_exc = AdzunaError("Limite de taxa da Adzuna atingido.")
            continue
        if resp.status_code >= 500:
            wait = config.RETRY_BACKOFF * attempt
            print(f"  erro no servidor Adzuna ({resp.status_code}), repetindo em "
                  f"{wait:.0f}s (tentativa {attempt}/{config.MAX_RETRIES})...",
                  file=sys.stderr)
            time.sleep(wait)
            last_exc = AdzunaError(f"Erro no servidor da Adzuna ({resp.status_code}).")
            continue

        try:
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            raise AdzunaError(f"Erro HTTP da Adzuna: {resp.status_code}.") from e
        except ValueError as e:
            raise AdzunaError("Resposta da Adzuna não é um JSON válido.") from e

    raise AdzunaError(
        f"Falha ao contatar a Adzuna após {config.MAX_RETRIES} tentativas "
        f"({last_exc})."
    )


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
    return _get_with_retries(url, params)


def search_jobs(keywords: str = None, max_pages: int = None,
                filter_seniority: bool = None, filter_location: bool = None) -> list:
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        print(
            "ERRO: defina ADZUNA_APP_ID e ADZUNA_APP_KEY no .env (cadastro gratuito em "
            "https://developer.adzuna.com/signup)",
            file=sys.stderr,
        )
        sys.exit(1)

    keywords = keywords or config.SEARCH_KEYWORDS
    max_pages = max_pages or config.MAX_PAGES
    if filter_seniority is None:
        filter_seniority = config.FILTER_SENIORITY
    if filter_location is None:
        filter_location = config.FILTER_LOCATION

    all_jobs = []
    seen_ids = set()

    try:
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
    except AdzunaError as e:
        # Se já pegamos algo, seguimos com o que temos; senão, encerra com a mensagem.
        if all_jobs:
            print(f"AVISO: {e} Continuando com {len(all_jobs)} vaga(s) já obtida(s).",
                  file=sys.stderr)
        else:
            print(f"ERRO: {e}", file=sys.stderr)
            sys.exit(1)

    extra_jobs = fetch_all_extra_sources()
    if extra_jobs:
        print(f"+ {len(extra_jobs)} vaga(s) de fontes extras (Remotive/Arbeitnow, "
              f"só remotas).")
    for job in extra_jobs:
        if job.get("id") in seen_ids:
            continue
        seen_ids.add(job.get("id"))
        all_jobs.append(job)

    if filter_seniority:
        kept, dropped = filter_out_senior(all_jobs)
        if dropped:
            print(f"Filtradas {len(dropped)} vaga(s) acima de júnior/pleno "
                  f"(use --include-senior para incluí-las).")
        all_jobs = kept

    if filter_location:
        kept, dropped = filter_out_non_local(all_jobs, home_city=config.HOME_CITY)
        if dropped:
            print(f"Filtradas {len(dropped)} vaga(s) presenciais fora de "
                  f"{config.HOME_CITY} e sem sinal de remoto "
                  f"(use --any-location para incluí-las).")
        all_jobs = kept

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


def _parse_args(argv):
    p = argparse.ArgumentParser(description="Busca vagas na Adzuna (Brasil).")
    p.add_argument("keywords", nargs="?", default=None,
                   help="palavras-chave da busca (ex.: 'desenvolvedor fullstack junior')")
    p.add_argument("--include-senior", action="store_true",
                   help="não descartar vagas de nível sênior/lead/gestão")
    p.add_argument("--any-location", action="store_true",
                   help=f"não descartar vagas presenciais fora de "
                        f"{config.HOME_CITY} (por padrão só ficam vagas em "
                        f"{config.HOME_CITY} ou remotas)")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    found = search_jobs(
        args.keywords,
        filter_seniority=False if args.include_senior else None,
        filter_location=False if args.any_location else None,
    )
    save_jobs_csv(found)
