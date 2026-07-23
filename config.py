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
SEARCH_KEYWORDS = os.environ.get(
    "SEARCH_KEYWORDS",
    "desenvolvedor fullstack junior",
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

# --- Rede / retries (tratamento de erros de API) ---
HTTP_TIMEOUT = 30          # segundos por requisição
MAX_RETRIES = 3            # tentativas em erros transitórios (429/5xx/timeout)
RETRY_BACKOFF = 2.0        # segundos base; cresce exponencialmente por tentativa

# --- Arquivos ---
OUTPUT_DIR = "applications"
JOBS_CSV = "jobs_found.csv"

# Gerar também um resume.pdf ao lado de cada resume.md (precisa de markdown+xhtml2pdf).
EXPORT_PDF = os.environ.get("EXPORT_PDF", "1") not in ("0", "false", "")
