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


def _normalize(text: str) -> str:
    """minúsculas + remove acentos, para casar 'sênior' == 'senior'."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


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
