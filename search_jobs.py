"""
Busca vagas de emprego na Adzuna API (Brasil) e salva em CSV para revisão.

Requer variáveis de ambiente:
  ADZUNA_APP_ID
  ADZUNA_APP_KEY

Cadastro gratuito: https://developer.adzuna.com/signup

Além da busca ampla por palavra-chave, faz uma segunda passada reforçada com
`where=HOME_CITY` (config.py) para não perder vagas locais que a busca ampla
ordenaria mais abaixo.

Uso:
  python search_jobs.py "desenvolvedor fullstack"
  python search_jobs.py "desenvolvedor fullstack" --include-senior
"""
import argparse
import csv
import sys
import time

import requests

import config
from extra_sources import fetch_all_extra_sources
from filters import (
    filter_out_irrelevant,
    filter_out_non_local,
    filter_out_senior,
)


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


def fetch_page(page: int, keywords: str = None, where: str = None,
               what_or: str = None) -> dict:
    url = f"https://api.adzuna.com/v1/api/jobs/{config.COUNTRY}/search/{page}"
    params = {
        "app_id": config.ADZUNA_APP_ID,
        "app_key": config.ADZUNA_APP_KEY,
        "results_per_page": config.RESULTS_PER_PAGE,
        "category": config.CATEGORY,
        "content-type": "application/json",
    }
    if keywords:
        params["what"] = keywords
    if what_or:
        # OR lógico entre os termos — pega muito mais que uma única palavra.
        params["what_or"] = what_or
    if where:
        params["where"] = where
    return _get_with_retries(url, params)


def _collect_adzuna_pass(all_jobs: list, seen_ids: set, max_pages: int,
                         label: str, *, keywords: str = None,
                         where: str = None, what_or: str = None) -> int:
    """Roda uma passada paginada na Adzuna, acrescenta vagas novas (dedup por
    id) a `all_jobs` e retorna quantas foram adicionadas. Best-effort: erros
    da Adzuna nesta passada não são fatais se já houver algo — só avisa.
    A primeira passada (label='busca principal') é a única que pode encerrar
    o programa se falhar sem nada coletado."""
    added = 0
    try:
        for page in range(1, max_pages + 1):
            data = fetch_page(page, keywords=keywords, where=where, what_or=what_or)
            results = data.get("results", [])
            if not results:
                break
            for job in results:
                job_id = job.get("id")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                all_jobs.append(_adzuna_job_to_dict(job))
                added += 1
            time.sleep(1)  # não sobrecarregar a API
    except AdzunaError as e:
        if all_jobs:
            print(f"AVISO: passada '{label}' falhou ({e}). Continuando com "
                  f"{len(all_jobs)} vaga(s) já obtida(s).", file=sys.stderr)
        else:
            print(f"ERRO: {e}", file=sys.stderr)
            sys.exit(1)
    return added


def _adzuna_job_to_dict(job: dict) -> dict:
    return {
        "id": job.get("id"),
        "title": (job.get("title") or "").strip(),
        "company": (job.get("company") or {}).get("display_name", ""),
        "location": (job.get("location") or {}).get("display_name", ""),
        "salary_min": job.get("salary_min", ""),
        "salary_max": job.get("salary_max", ""),
        "description": (job.get("description") or "").strip(),
        "redirect_url": job.get("redirect_url", ""),
        "created": job.get("created", ""),
    }


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

    # Passada 1 — busca principal pela palavra-chave do usuário (pode encerrar
    # o programa se falhar sem nada coletado).
    _collect_adzuna_pass(all_jobs, seen_ids, max_pages, "busca principal",
                         keywords=keywords)

    # Passada 2 — busca ampla "what_or" (OR de muitos termos de dev): pega
    # vagas de backend/frontend/react/python/etc. que a palavra-chave única
    # não pegaria. É o que mais aumenta o volume dentro do Brasil.
    if config.ADZUNA_BROAD_OR:
        broad = _collect_adzuna_pass(all_jobs, seen_ids, max_pages, "busca ampla",
                                     what_or=config.ADZUNA_BROAD_OR)
        if broad:
            print(f"+ {broad} vaga(s) via busca ampla (backend/frontend/react/etc.).")

    # Passada 3 — reforço local em HOME_CITY (a busca ampla ordena por
    # relevância de texto; uma vaga real na cidade pode não aparecer nas
    # primeiras páginas mesmo existindo).
    local = _collect_adzuna_pass(all_jobs, seen_ids, min(max_pages, 2),
                                 f"busca local {config.HOME_CITY}",
                                 what_or=config.ADZUNA_BROAD_OR,
                                 where=config.HOME_CITY)
    if local:
        print(f"+ {local} vaga(s) via busca local reforçada em {config.HOME_CITY}.")

    extra_jobs = fetch_all_extra_sources()
    if extra_jobs:
        print(f"+ {len(extra_jobs)} vaga(s) de fontes extras (Remotive/Arbeitnow/"
              f"RemoteOK/Jobicy/The Muse/Jooble).")
    for job in extra_jobs:
        if job.get("id") in seen_ids:
            continue
        seen_ids.add(job.get("id"))
        all_jobs.append(job)

    # Guarda de relevância (aplicado a TODAS as fontes): descarta vagas fora de
    # dev que a busca ampla da Adzuna / fontes remotas deixaram passar
    # (nutrição, telecom, recepção, suporte, etc.).
    kept, dropped = filter_out_irrelevant(all_jobs)
    if dropped:
        print(f"Filtradas {len(dropped)} vaga(s) fora de desenvolvimento "
              f"(ajuste RELEVANCE_KEYWORDS no .env se cortar demais/de menos).")
    all_jobs = kept

    if filter_seniority:
        kept, dropped = filter_out_senior(all_jobs)
        if dropped:
            print(f"Filtradas {len(dropped)} vaga(s) acima de júnior/pleno "
                  f"(use --include-senior para incluí-las).")
        all_jobs = kept

    if filter_location:
        kept, dropped = filter_out_non_local(all_jobs, home_city=config.HOME_CITY)
        if dropped:
            print(f"Filtradas {len(dropped)} vaga(s) fora de {config.HOME_CITY}: "
                  f"presenciais em outra cidade OU remotas presas a outro país "
                  f"(ex.: Alemanha) (use --any-location para incluí-las).")
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
