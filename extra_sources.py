"""
Fontes adicionais de vagas, além da Adzuna — só APIs públicas que não exigem
login nem automação de plataforma. Mesmo princípio de segurança do projeto:
nada de login/scraping autenticado em LinkedIn/Gupy/Catho/InfoJobs (ver
SECURITY_REVIEW.md e a decisão em PROGRESS_LOG.md de 2026-07-22).

Cada fonte é opcional e best-effort: se a API estiver fora do ar ou mudar de
formato, avisa no stderr e segue com zero vagas dessa fonte — nunca derruba
o pipeline inteiro (mesmo princípio do tratamento de erro da Adzuna em
search_jobs.py).

Fontes:
- Remotive (https://remotive.com/api/remote-jobs) — vagas remotas, JSON
  público, sem necessidade de chave.
- Arbeitnow (https://www.arbeitnow.com/api/job-board-api) — vagas
  majoritariamente europeias/remotas, JSON público, sem necessidade de chave;
  filtramos só as marcadas remote=true.

Ambas retornam essencialmente só vagas remotas — o que já combina com o
filtro de localização do projeto (Florianópolis ou remoto, ver filters.py).

Limitação conhecida: nenhuma das duas tem busca por palavra-chave em
português que funcione bem (conteúdo é majoritariamente em inglês). Em vez de
tentar traduzir o termo de busca, filtramos por relevância "fullstack" via
regex no título/tags — mais robusto do que confiar em tradução automática.
Isso significa que estas fontes sempre trazem vagas fullstack, independente
da palavra-chave passada em `python main.py "..."`.
"""
import html as html_module
import re
import sys

import requests

import config

_FULLSTACK_RE = re.compile(r"full[\s-]?stack", re.IGNORECASE)


def _is_fullstack_relevant(title: str, tags: list = None) -> bool:
    if _FULLSTACK_RE.search(title or ""):
        return True
    for tag in (tags or []):
        if _FULLSTACK_RE.search(tag or ""):
            return True
    return False


def _strip_html(text: str) -> str:
    """Remove tags HTML e decodifica entidades — Remotive retorna a descrição
    como HTML; o resto do pipeline (filtros por regex, prompt do DeepSeek)
    espera texto simples."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_remotive() -> list:
    """Vagas remotas da Remotive, categoria software-dev, filtradas por
    relevância fullstack. Não precisa de chave de API."""
    if not config.ENABLE_REMOTIVE:
        return []
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"category": "software-dev"},
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: Remotive indisponível ({e}), pulando esta fonte.",
              file=sys.stderr)
        return []

    jobs = []
    for job in data.get("jobs", []):
        title = (job.get("title") or "").strip()
        tags = job.get("tags") or []
        if not _is_fullstack_relevant(title, tags):
            continue
        location = job.get("candidate_required_location") or "não especificado"
        jobs.append(
            {
                "id": f"remotive-{job.get('id')}",
                "title": title,
                "company": job.get("company_name", ""),
                "location": f"Remoto ({location})",
                "salary_min": "",
                "salary_max": job.get("salary", ""),
                "description": _strip_html(job.get("description", "")),
                "redirect_url": job.get("url", ""),
                "created": job.get("publication_date", ""),
            }
        )
    return jobs


def fetch_arbeitnow(max_pages: int = None) -> list:
    """Vagas remotas do Arbeitnow (só remote=true), filtradas por relevância
    fullstack. Não precisa de chave de API. A API não tem busca por palavra-
    chave — filtramos no cliente, por isso limitamos a `max_pages` para não
    varrer o board inteiro a cada execução."""
    if not config.ENABLE_ARBEITNOW:
        return []
    max_pages = max_pages or config.MAX_PAGES
    jobs = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        for page in range(1, max_pages + 1):
            resp = requests.get(url, params={"page": page}, timeout=config.HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            page_jobs = data.get("data", [])
            if not page_jobs:
                break
            for job in page_jobs:
                if not job.get("remote"):
                    continue
                title = (job.get("title") or "").strip()
                tags = job.get("tags") or []
                if not _is_fullstack_relevant(title, tags):
                    continue
                slug = job.get("slug") or re.sub(r"\W+", "-", title.lower()).strip("-")
                jobs.append(
                    {
                        "id": f"arbeitnow-{slug}",
                        "title": title,
                        "company": job.get("company_name", ""),
                        "location": f"Remoto ({job.get('location') or 'não especificado'})",
                        "salary_min": "",
                        "salary_max": "",
                        "description": _strip_html(job.get("description", "")),
                        "redirect_url": job.get("url", ""),
                        "created": job.get("created_at", ""),
                    }
                )
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: Arbeitnow indisponível ({e}), continuando com "
              f"{len(jobs)} vaga(s) já obtida(s) dessa fonte.", file=sys.stderr)
    return jobs


def fetch_all_extra_sources() -> list:
    """Agrega todas as fontes extras habilitadas (além da Adzuna). Nunca
    lança exceção — cada fonte trata seus próprios erros e retorna []."""
    jobs = []
    jobs.extend(fetch_remotive())
    jobs.extend(fetch_arbeitnow())
    return jobs
