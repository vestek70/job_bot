import os
import sys

# Consoles Windows em locale não-UTF-8 (ex.: cp1251/cp866) quebram com
# UnicodeEncodeError ao imprimir acentos do português. Reconfigura stdout/stderr
# para UTF-8 (com errors='replace') logo no import — todos os entry points
# importam config, então isso vale para todo o projeto.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # stream já ok, ou não suporta reconfigure (ex.: redirecionado)

try:
    from dotenv import load_dotenv

    load_dotenv()  # carrega .env se existir (não sobrescreve variáveis já setadas)
except ImportError:
    pass  # python-dotenv não instalado — segue usando só variáveis de ambiente reais

# --- Adzuna (busca de vagas) ---
# Cadastro gratuito: https://developer.adzuna.com/signup
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")

# --- DeepSeek (adaptação do currículo) ---
# Usa o endpoint compatível com a API da Anthropic (mesmo SDK 'anthropic', só troca
# base_url/api_key/model) — https://api-docs.deepseek.com/guides/anthropic_api
# Chave: https://platform.deepseek.com/api_keys
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"
TAILOR_MODEL = "deepseek-v4-pro"

# --- Gmail (envio opcional, só quando há e-mail direto de contato) ---
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "vestek70@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

# --- Busca ---
COUNTRY = "br"
# "junior" foi removido da palavra-chave padrão: a busca de texto livre da
# Adzuna ("what") tratava "junior" como termo obrigatório, excluindo vagas
# tituladas só "Pleno" que o filtro de senioridade (filters.py) aceitaria de
# qualquer forma. A palavra-chave só precisa achar candidatas relevantes; o
# nível é responsabilidade do filtro, não do texto de busca.
SEARCH_KEYWORDS = os.environ.get(
    "SEARCH_KEYWORDS",
    "desenvolvedor fullstack",
)
CATEGORY = "it-jobs"
RESULTS_PER_PAGE = 20
MAX_PAGES = 3

# Descartar vagas claramente acima de júnior/pleno (ver filters.py).
# Pode desligar por vaga com a flag --include-senior na linha de comando.
FILTER_SENIORITY = os.environ.get("FILTER_SENIORITY", "1") not in ("0", "false", "")

# Cidade onde o candidato mora e não pretende se mudar. Vagas presenciais em
# outra cidade são descartadas por padrão — só ficam vagas na HOME_CITY ou
# remotas (ver filters.is_local_or_remote). Desligar com --any-location.
HOME_CITY = os.environ.get("HOME_CITY", "Florianópolis")
FILTER_LOCATION = os.environ.get("FILTER_LOCATION", "1") not in ("0", "false", "")

# --- Fontes extras de vagas (além da Adzuna) — ver extra_sources.py ---
# Todas são APIs públicas, sem login, sem chave necessária. Desligáveis
# individualmente se ficarem instáveis ou indesejadas.
ENABLE_REMOTIVE = os.environ.get("ENABLE_REMOTIVE", "1") not in ("0", "false", "")
ENABLE_ARBEITNOW = os.environ.get("ENABLE_ARBEITNOW", "1") not in ("0", "false", "")
ENABLE_REMOTEOK = os.environ.get("ENABLE_REMOTEOK", "1") not in ("0", "false", "")
ENABLE_JOBICY = os.environ.get("ENABLE_JOBICY", "1") not in ("0", "false", "")
ENABLE_THEMUSE = os.environ.get("ENABLE_THEMUSE", "1") not in ("0", "false", "")

# Jooble — agregador legítimo com API pública (não é scraping): agrega vagas de
# vários sites do Brasil, incluindo postagens que se originam em plataformas.
# Precisa de chave gratuita: https://jooble.org/api/about . Sem chave, a fonte
# fica inativa silenciosamente. Diferente das fontes remotas em inglês, o Jooble
# tem busca por palavra-chave em português de verdade — então não passa pelo
# filtro de relevância, a própria query já mira dev.
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY")
ENABLE_JOOBLE = os.environ.get("ENABLE_JOOBLE", "1") not in ("0", "false", "")
# NOTA (confirmado via debug_jooble.py, 2026-07-23): nesta conta free-tier o
# Jooble responde a "Brazil" (inglês, não "Brasil") e a termos em inglês
# ("developer" traz ~47 vagas; "desenvolvedor" traz 0). Por isso consultamos em
# inglês + location "Brazil"; o filtro de localização/relevância refina depois.
JOOBLE_LOCATION = os.environ.get("JOOBLE_LOCATION", "Brazil")
JOOBLE_QUERIES = [
    kw.strip() for kw in os.environ.get(
        "JOOBLE_QUERIES",
        "developer,fullstack developer,software engineer,"
        "react developer,python developer,desenvolvedor",
    ).split(",") if kw.strip()
]

# Relevância: usada para descartar vagas que NÃO são de desenvolvimento (a
# busca ampla da Adzuna e as fontes remotas trazem muita coisa fora de dev —
# nutrição, telecom, recepção, etc.). Cada item é um regex (minúsculo, sem
# acento — o texto é normalizado antes de casar).
#
# IMPORTANTE sobre a sintaxe:
# - Pontos são literais SÓ se escapados: "\.net" casa ".net" mas NÃO "internet"
#   (o bug anterior era ".net" sem escape, que casava "inter[net]").
# - "\b" = limite de palavra, para "react" não casar "reaction", etc.
# Sobrescrever via env RELEVANCE_KEYWORDS="a,b,c" para afinar ao seu stack.
_DEFAULT_RELEVANCE = (
    r"full[\s-]?stack,back[\s-]?end,front[\s-]?end,"
    r"\bdeveloper\b,\bdesenvolvedor,\bprogramador,"
    r"\breact\b,\bnode\b,\bvue\b,\bangular\b,\btypescript\b,\bjavascript\b,"
    r"\bpython\b,\bdjango\b,\bflask\b,\bphp\b,\blaravel\b,\bruby\b,\brails\b,"
    r"\bjava\b,\bgolang\b,\bkotlin\b,\bflutter\b,\.net\b,dotnet,c#,"
    r"software engineer,software developer,web developer,"
    r"engenheiro de software,engenharia de software,software,"
    r"analista de sistemas,analista de desenvolvimento,analista de ti,"
    r"\bdevops\b,\bsre\b"
)
RELEVANCE_KEYWORDS = [
    kw.strip() for kw in
    os.environ.get("RELEVANCE_KEYWORDS", _DEFAULT_RELEVANCE).split(",")
    if kw.strip()
]

# Termos amplos para a busca "what_or" da Adzuna (OR lógico) — pega muito mais
# que a palavra-chave única, dentro da categoria it-jobs no Brasil.
ADZUNA_BROAD_OR = os.environ.get(
    "ADZUNA_BROAD_OR",
    "desenvolvedor programador fullstack backend frontend react node python "
    "php javascript typescript",
)

# --- Rede / retries (tratamento de erros de API) ---
HTTP_TIMEOUT = 30          # segundos por requisição
MAX_RETRIES = 3            # tentativas em erros transitórios (429/5xx/timeout)
RETRY_BACKOFF = 2.0        # segundos base; cresce exponencialmente por tentativa

# --- Arquivos ---
OUTPUT_DIR = "applications"
JOBS_CSV = "jobs_found.csv"

# Gerar também um resume.pdf ao lado de cada resume.md (precisa de markdown+xhtml2pdf).
EXPORT_PDF = os.environ.get("EXPORT_PDF", "1") not in ("0", "false", "")
