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
  público, sem chave.
- Arbeitnow (https://www.arbeitnow.com/api/job-board-api) — vagas
  majoritariamente europeias/remotas, JSON público, sem chave; só remote=true.
- RemoteOK (https://remoteok.com/api) — vagas remotas, JSON público, sem
  chave (precisa de User-Agent explícito).
- Jobicy (https://jobicy.com/api/v2/remote-jobs) — vagas remotas, JSON
  público, sem chave.
- The Muse (https://www.themuse.com/api/public/jobs) — engenharia de software,
  filtrado por Brasil/remoto; único que também traz presenciais no Brasil (o
  filtro de localização decide depois). Rate-limited sem chave.

Quase todas retornam só vagas remotas — o que já combina com o filtro de
localização do projeto (Florianópolis ou remoto, ver filters.py).

Limitação conhecida: essas fontes não têm busca por palavra-chave em português
confiável (conteúdo majoritariamente em inglês). Em vez de traduzir o termo de
busca, filtramos por relevância via regex de termos de dev
(config.RELEVANCE_KEYWORDS — fullstack, backend, frontend, react, node, python,
php, etc.) no título/tags. Assim as fontes trazem vagas de dev em geral,
independentemente da palavra-chave passada em `python main.py "..."`.
"""
import html as html_module
import re
import sys

import requests

import config
from filters import is_dev_relevant as _is_dev_relevant


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
        if not _is_dev_relevant(title, tags):
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
                if not _is_dev_relevant(title, tags):
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


def fetch_remoteok() -> list:
    """Vagas remotas do RemoteOK, filtradas por relevância fullstack. Não
    precisa de chave de API, mas o RemoteOK bloqueia User-Agent genérico de
    biblioteca HTTP (retorna 403) — por isso enviamos um User-Agent explícito.

    Aviso: formato baseado na API pública documentada do RemoteOK, não
    verificado com uma chamada de rede real nesta sessão (rede bloqueada na
    sandbox de desenvolvimento — mesma limitação de Remotive/Arbeitnow). Se
    o parsing não achar nenhuma vaga na primeira execução real e não houver
    AVISO de erro no stderr, o formato pode ter mudado — conferir
    https://remoteok.com/api."""
    if not config.ENABLE_REMOTEOK:
        return []
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={
                "User-Agent": "job-bot/1.0 (uso pessoal, busca de vagas fullstack)"
            },
            timeout=config.HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: RemoteOK indisponível ({e}), pulando esta fonte.",
              file=sys.stderr)
        return []

    jobs = []
    for job in data:
        # O primeiro item do array costuma ser um aviso legal, não uma vaga —
        # pula qualquer item sem os campos mínimos de uma vaga real.
        if not isinstance(job, dict) or not job.get("id") or not job.get("position"):
            continue
        title = (job.get("position") or "").strip()
        tags = job.get("tags") or []
        if not _is_dev_relevant(title, tags):
            continue
        location = job.get("location") or "não especificado"
        jobs.append(
            {
                "id": f"remoteok-{job.get('id')}",
                "title": title,
                "company": job.get("company", ""),
                "location": f"Remoto ({location})",
                "salary_min": job.get("salary_min", ""),
                "salary_max": job.get("salary_max", ""),
                "description": _strip_html(job.get("description", "")),
                "redirect_url": job.get("url") or job.get("apply_url", ""),
                "created": job.get("date", ""),
            }
        )
    return jobs


def fetch_jobicy() -> list:
    """Vagas remotas do Jobicy (API pública v2, sem chave), filtradas por
    relevância de dev. Pedimos a indústria 'dev' e um count alto.

    Aviso: formato baseado na API pública documentada (jobicy.com/jobs-rss-feed,
    endpoint /api/v2/remote-jobs), não verificado ao vivo nesta sessão (rede
    bloqueada na sandbox)."""
    if not config.ENABLE_JOBICY:
        return []
    try:
        resp = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 50, "industry": "dev"},
            headers={"User-Agent": "job-bot/1.0 (uso pessoal, busca de vagas)"},
            timeout=config.HTTP_TIMEOUT,
            allow_redirects=False,  # o endpoint às vezes redireciona p/ blog e dá 403
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: Jobicy indisponível ({e}), pulando esta fonte.",
              file=sys.stderr)
        return []

    jobs = []
    for job in data.get("jobs", []):
        if not isinstance(job, dict):
            continue
        title = (job.get("jobTitle") or "").strip()
        tags = job.get("jobIndustry") or []
        if not title or not _is_dev_relevant(title, tags):
            continue
        location = job.get("jobGeo") or "não especificado"
        jobs.append(
            {
                "id": f"jobicy-{job.get('id')}",
                "title": title,
                "company": job.get("companyName", ""),
                "location": f"Remoto ({location})",
                "salary_min": job.get("annualSalaryMin", ""),
                "salary_max": job.get("annualSalaryMax", ""),
                "description": _strip_html(
                    job.get("jobDescription") or job.get("jobExcerpt", "")
                ),
                "redirect_url": job.get("url", ""),
                "created": job.get("pubDate", ""),
            }
        )
    return jobs


def fetch_themuse(max_pages: int = 2) -> list:
    """Vagas de engenharia de software do The Muse (API pública, sem chave)
    filtradas por localização Brasil ou remoto/flexível. Diferente das outras
    fontes extras, o Muse tem vagas presenciais no Brasil também — o filtro de
    localização do projeto (filters.py) decide o que manter depois.

    Aviso: formato baseado na API pública documentada (themuse.com/developers/
    api/v2), não verificado ao vivo nesta sessão (rede bloqueada na sandbox).
    A API é rate-limited para chamadas sem chave — por isso poucas páginas."""
    if not config.ENABLE_THEMUSE:
        return []
    jobs = []
    url = "https://www.themuse.com/api/public/jobs"
    try:
        for page in range(0, max_pages):
            resp = requests.get(
                url,
                params={
                    "category": "Software Engineering",
                    "location": "Brazil",
                    "page": page,
                },
                headers={"User-Agent": "job-bot/1.0 (uso pessoal, busca de vagas)"},
                timeout=config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            for job in results:
                if not isinstance(job, dict):
                    continue
                title = (job.get("name") or "").strip()
                if not title or not _is_dev_relevant(title):
                    continue
                locs = job.get("locations") or []
                loc_names = ", ".join(
                    (loc.get("name") or "") for loc in locs if isinstance(loc, dict)
                ) or "não especificado"
                company = (job.get("company") or {}).get("name", "")
                landing = (job.get("refs") or {}).get("landing_page", "")
                jobs.append(
                    {
                        "id": f"themuse-{job.get('id')}",
                        "title": title,
                        "company": company,
                        "location": loc_names,
                        "salary_min": "",
                        "salary_max": "",
                        "description": _strip_html(job.get("contents", "")),
                        "redirect_url": landing,
                        "created": job.get("publication_date", ""),
                    }
                )
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: The Muse indisponível ({e}), continuando com "
              f"{len(jobs)} vaga(s) já obtida(s) dessa fonte.", file=sys.stderr)
    return jobs


def fetch_jooble() -> list:
    """Vagas do Jooble — agregador legítimo com API pública (POST, precisa de
    chave gratuita em config.JOOBLE_API_KEY). NÃO é scraping: o Jooble agrega
    vagas de vários sites do Brasil e as expõe via API oficial.

    Faz duas buscas: uma local (HOME_CITY) e uma remota (Brasil + "remoto").
    O filtro de localização do projeto (filters.py) decide o que manter depois.
    Como o Jooble tem busca por palavra-chave em português de verdade, NÃO
    aplicamos o filtro de relevância aqui — a query já mira dev.

    Aviso: formato baseado na API pública documentada do Jooble
    (https://jooble.org/api/about), não verificado ao vivo nesta sessão."""
    if not config.ENABLE_JOOBLE or not config.JOOBLE_API_KEY:
        return []
    url = f"https://jooble.org/api/{config.JOOBLE_API_KEY}"
    queries = [
        {"keywords": config.SEARCH_KEYWORDS, "location": config.HOME_CITY},
        {"keywords": f"{config.SEARCH_KEYWORDS} remoto", "location": "Brasil"},
    ]
    jobs = []
    local_seen = set()
    try:
        for q in queries:
            resp = requests.post(
                url, json=q,
                headers={"Content-Type": "application/json",
                         "User-Agent": "job-bot/1.0 (uso pessoal, busca de vagas)"},
                timeout=config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            for job in data.get("jobs", []):
                if not isinstance(job, dict):
                    continue
                title = (job.get("title") or "").strip()
                jid = f"jooble-{job.get('id')}"
                if not title or jid in local_seen:
                    continue
                local_seen.add(jid)
                jobs.append(
                    {
                        "id": jid,
                        "title": title,
                        "company": job.get("company", ""),
                        "location": job.get("location", ""),
                        "salary_min": "",
                        "salary_max": job.get("salary", ""),
                        "description": _strip_html(job.get("snippet", "")),
                        "redirect_url": job.get("link", ""),
                        "created": job.get("updated", ""),
                    }
                )
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"AVISO: Jooble indisponível ({e}), continuando com "
              f"{len(jobs)} vaga(s) já obtida(s) dessa fonte.", file=sys.stderr)
    return jobs


def fetch_all_extra_sources() -> list:
    """Agrega todas as fontes extras habilitadas (além da Adzuna). Nunca
    lança exceção — cada fonte trata seus próprios erros e retorna []."""
    jobs = []
    jobs.extend(fetch_remotive())
    jobs.extend(fetch_arbeitnow())
    jobs.extend(fetch_remoteok())
    jobs.extend(fetch_jobicy())
    jobs.extend(fetch_themuse())
    jobs.extend(fetch_jooble())
    return jobs
