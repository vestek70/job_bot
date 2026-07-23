"""
Heurísticas de filtragem de vagas.

Objetivo principal: descartar vagas claramente ACIMA do nível júnior/pleno quando
a busca é por júnior/pleno. A Adzuna não retorna um campo estruturado de senioridade,
então inferimos a partir do título (sinal forte) e, de forma conservadora, da
descrição (só anos de experiência exigidos).

Funções puras, sem I/O — testáveis isoladamente (ver test_filters.py).
"""
import re
import unicodedata

import config


def _normalize(text: str) -> str:
    """minúsculas + remove acentos, para casar 'sênior' == 'senior'."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


# --- Relevância de desenvolvimento --------------------------------------------
# Descarta vagas que NÃO são de dev (nutrição, telecom, recepção, suporte, etc.).
# A busca ampla da Adzuna (what_or) e as fontes remotas trazem muito ruído; este
# é o guarda final aplicado a TODAS as vagas de TODAS as fontes.
_RELEVANCE_RE = re.compile(
    "|".join(config.RELEVANCE_KEYWORDS) if config.RELEVANCE_KEYWORDS else r"$^"
)


def is_dev_relevant(title: str, tags: list = None) -> bool:
    """True se o título (ou alguma tag) casa com algum termo de dev
    (config.RELEVANCE_KEYWORDS, já com escapes/limites de palavra corretos)."""
    if _RELEVANCE_RE.search(_normalize(title)):
        return True
    for tag in (tags or []):
        if _RELEVANCE_RE.search(_normalize(tag)):
            return True
    return False


def filter_out_irrelevant(jobs: list) -> tuple:
    """Separa (dev, não_dev) por relevância no TÍTULO. Guarda final contra vagas
    fora de dev que a busca ampla/fontes remotas deixaram passar."""
    kept, dropped = [], []
    for job in jobs:
        if is_dev_relevant(job.get("title", "")):
            kept.append(job)
        else:
            dropped.append(job)
    return kept, dropped


# Termos que indicam um cargo ACIMA de pleno (casados no TÍTULO da vaga).
_SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsr\b", r"\bespecialista\b", r"\bspecialist\b",
    r"\blead\b", r"\blider\b", r"\bprincipal\b", r"\bstaff\b",
    r"\barquiteto\b", r"\barchiteto\b", r"\barchitect\b",
    r"\bgerente\b", r"\bmanager\b", r"\bcoordenador\b", r"\bcoordinator\b",
    r"\bhead\b", r"\bdiretor\b", r"\bdirector\b",
    r"\btech lead\b", r"\bteam lead\b",
]
# Termos que indicam júnior/pleno (nível-alvo) — se aparecem no título, mantemos
# a vaga mesmo que também haja um termo sênior (ex.: "Dev Pleno/Sênior").
_JUNIOR_PATTERNS = [
    r"\bjunior\b", r"\bjr\b", r"\bpleno\b", r"\bpl\b", r"\btrainee\b",
    r"\bestagi", r"\bintern\b", r"\bentry.level\b", r"\bnivel junior\b",
]

_SENIOR_RE = re.compile("|".join(_SENIOR_PATTERNS))
_JUNIOR_RE = re.compile("|".join(_JUNIOR_PATTERNS))
# "5 anos", "5+ anos", "5 años" — captura o número de anos exigidos.
_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*an[o|õ|ñ]?s?\b")

# A partir de quantos anos de experiência exigidos consideramos "acima de pleno".
_SENIOR_YEARS_THRESHOLD = 5


def is_too_senior(title: str, description: str = "") -> bool:
    """
    True se a vaga parece exigir senioridade acima de júnior/pleno.

    Regras (conservadoras, para não descartar vagas boas por engano):
    1. Se o título tem sinal de júnior/pleno -> NÃO é sênior (mantém).
    2. Se o título tem sinal de sênior/lead/gestão -> é sênior (descarta).
    3. Título neutro: descarta só se a descrição exigir >= 5 anos de experiência.
    """
    t = _normalize(title)
    if _JUNIOR_RE.search(t):
        return False
    if _SENIOR_RE.search(t):
        return True

    d = _normalize(description)
    for m in _YEARS_RE.finditer(d):
        try:
            if int(m.group(1)) >= _SENIOR_YEARS_THRESHOLD:
                return True
        except ValueError:
            continue
    return False


def filter_out_senior(jobs: list) -> tuple:
    """
    Separa as vagas em (mantidas, descartadas_como_senior).
    `jobs` é uma lista de dicts com pelo menos 'title' e 'description'.
    """
    kept, dropped = [], []
    for job in jobs:
        if is_too_senior(job.get("title", ""), job.get("description", "")):
            dropped.append(job)
        else:
            kept.append(job)
    return kept, dropped


# --- Filtro de localização: candidato não quer se mudar de cidade -----------
#
# Regra: só aceitar vaga se ela é NA cidade-base (presencial/híbrido local) OU
# é remota (o candidato pode morar em qualquer lugar). Vaga presencial em
# outra cidade é descartada.

_HOME_CITY_ALIASES = ("florianopolis", "floripa")

_REMOTE_PATTERNS = [
    r"\bremot[ao]s?\b",  # remoto/remota/remotos/remotas (concordância de gênero)
    r"\bremote\b", r"\bhome.?office\b", r"\banywhere\b",
    r"\bwork from home\b", r"\bwfh\b",
]
_REMOTE_RE = re.compile("|".join(_REMOTE_PATTERNS))


def _is_home_city(location: str, home_city: str) -> bool:
    loc = _normalize(location)
    home = _normalize(home_city or "")
    if home and home in loc:
        return True
    return any(alias in loc for alias in _HOME_CITY_ALIASES)


def _is_remote(title: str, location: str, description: str) -> bool:
    combined = _normalize(f"{title} {location} {description}")
    return bool(_REMOTE_RE.search(combined))


# Fontes internacionais (id com esses prefixos) podem trazer vagas remotas
# presas a OUTRO país (ex.: "Remoto (Berlin)", "Remoto (México)"), que não
# servem para quem mora no Brasil (idioma + geo). A Adzuna (ids numéricos) é
# API do Brasil e o Jooble é agregador do Brasil — nesses confiamos que é
# Brasil. Só as internacionais passam pela checagem de região.
_INTL_SOURCE_PREFIXES = (
    "remotive-", "arbeitnow-", "remoteok-", "jobicy-", "themuse-",
)

# Tokens de "remoto global" (aceita Brasil) — removidos ao checar se sobra um
# lugar estrangeiro específico na localização.
_GLOBAL_REMOTE_TOKENS = re.compile(
    r"worldwide|anywhere|global|flexible|remote|remot[ao]s?|home.?office|"
    r"nao especificado|not specified|unspecified|"
    r"latam|latin america|america latina|americas|south america|america do sul"
)
_BRAZIL_TOKENS = ("brasil", "brazil", "florianopolis", "floripa", "santa catarina")


def _remote_region_ok(location: str) -> bool:
    """Para vagas remotas de fontes internacionais: True se a região aceita
    quem está no Brasil — ou seja, menciona Brasil, OU é remoto genuinamente
    global (worldwide/anywhere/flexible/LatAm) SEM um lugar estrangeiro
    específico. 'Remoto (Berlin)' -> False; 'Flexible / Remote' -> True."""
    loc = _normalize(location)
    if any(tok in loc for tok in _BRAZIL_TOKENS):
        return True
    # Remove tokens de remoto-global e pontuação; se sobrar algum nome de lugar,
    # é uma vaga presa a um local estrangeiro específico -> descarta.
    residue = _GLOBAL_REMOTE_TOKENS.sub(" ", loc)
    residue = re.sub(r"[()/,\-.]", " ", residue)
    residue = re.sub(r"\s+", " ", residue).strip()
    return residue == ""


def is_local_or_remote(job: dict, home_city: str = "Florianópolis") -> bool:
    """
    True se a vaga é aceitável para quem não quer se mudar de cidade:
    - a vaga é na cidade-base (`home_city`, ex.: Florianópolis/Floripa), OU
    - a vaga é remota E acessível do Brasil (ver _remote_region_ok para as
      fontes internacionais).

    Conservador: se não há nenhum sinal de remoto e a localização não é a
    cidade-base, a vaga é descartada.
    """
    location = job.get("location", "")
    title = job.get("title", "")
    description = job.get("description", "")
    if _is_home_city(location, home_city):
        return True
    if not _is_remote(title, location, description):
        return False
    # Vaga remota. Se veio de fonte internacional, exige região que aceite o
    # Brasil (descarta 'Remoto (Berlin)', 'Remoto (México)', India-only, etc.).
    job_id = str(job.get("id", ""))
    if job_id.startswith(_INTL_SOURCE_PREFIXES):
        return _remote_region_ok(location)
    return True


def filter_out_non_local(jobs: list, home_city: str = "Florianópolis") -> tuple:
    """
    Separa as vagas em (mantidas, descartadas_por_localizacao).
    Mantém só vagas na `home_city` ou remotas — descarta presencial em
    outra cidade (candidato não quer se mudar).
    """
    kept, dropped = [], []
    for job in jobs:
        if is_local_or_remote(job, home_city):
            kept.append(job)
        else:
            dropped.append(job)
    return kept, dropped
