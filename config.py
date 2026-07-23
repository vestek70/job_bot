import os

try:
    from dotenv import load_dotenv

    load_dotenv()  # carrega .env se existir (não sobrescreve variáveis já setadas)
except ImportError:
    pass  # python-dotenv não instalado — segue usando só variáveis de ambiente reais

# --- Adzuna (busca de vagas) ---
# Cadastro gratuito: https://developer.adzuna.com/signup
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")

# --- Anthropic (adaptação do currículo) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

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

# --- Arquivos ---
OUTPUT_DIR = "applications"
JOBS_CSV = "jobs_found.csv"
