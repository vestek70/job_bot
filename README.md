**🇧🇷 Português** · [🇷🇺 Русский](README.ru.md)

# Job Bot — busca de vagas e currículo sob medida (Brasil, TI/dev)

Ferramenta **semiautomática** de busca de emprego: encontra vagas em 7 fontes,
gera um currículo adaptado a cada vaga com IA e — só depois da sua confirmação —
envia por e-mail. Painel local no navegador, em português ou russo.

> **Nada é enviado sem você clicar e confirmar.** Sem login automático em
> plataformas, sem scraping, sem invenção de experiência no currículo.
> Veja [Princípios de segurança](#princípios-de-segurança).

---

## O que ele faz

1. **Busca vagas** em 7 fontes públicas (Adzuna, Remotive, Arbeitnow, RemoteOK,
   Jobicy, The Muse, Jooble) — sem login, só APIs públicas.
2. **Filtra** o que não serve: fora de desenvolvimento, acima do seu nível,
   presencial em outra cidade, ou "remoto" preso a outro país.
3. **Gera um currículo sob medida** para a vaga que VOCÊ escolher, usando IA
   (DeepSeek) — em PDF e Markdown, formatado para ATS.
4. **Acompanha suas candidaturas**: favoritas (★), arquivo de vagas em que já
   se candidatou, e exclusão das que não interessam.
5. **Envia por e-mail** (opcional) as vagas que trazem e-mail de contato —
   sempre com confirmação explícita.

## O currículo é adaptado, não inventado

Esta é a parte central. O bot lê `base_resume.md` (seus fatos reais) e a
descrição da vaga, e reescreve o currículo para aquela vaga específica:

- **Espelha o vocabulário da vaga** para passar em triagem por ATS/IA: se a vaga
  diz "Postgres" e você escreveu "PostgreSQL", ele alinha a escrita; se pede
  "REST APIs", usa esse termo — mas **só para o que você realmente tem**.
- **Adapta o ângulo**: vaga de back-end → destaca banco/APIs/segurança; de
  front-end → React/JavaScript/PWA.
- **Coloca as palavras-chave relevantes no topo** (resumo + habilidades), onde
  o ATS dá mais peso.
- **Nunca inventa** tecnologia, empresa, cargo ou certificação que não esteja no
  seu `base_resume.md`. Se a vaga pede algo que você não tem, ele não afirma que
  você tem.

## Instalação

Requisitos: Python 3.10+.

```bash
git clone https://github.com/vestek70/job_bot.git
cd job_bot
pip install -r requirements.txt
```

### 1. Crie o seu currículo base

```bash
cp base_resume.example.md base_resume.md   # Windows: copy base_resume.example.md base_resume.md
```

Abra `base_resume.md` e preencha com os **seus** dados reais. Este arquivo é a
única fonte de fatos do bot — quanto mais concreto (números, resultados,
tecnologias), melhor o resultado. Ele está no `.gitignore`: seus dados pessoais
não vão para o repositório.

### 2. Configure as chaves

Crie um arquivo `.env` na raiz do projeto:

```ini
# Busca de vagas (obrigatório) — cadastro gratuito
ADZUNA_APP_ID=seu_app_id
ADZUNA_APP_KEY=sua_app_key

# Geração de currículo com IA (obrigatório para gerar currículos)
DEEPSEEK_API_KEY=sua_chave

# Fonte extra de vagas (opcional, gratuito)
JOOBLE_API_KEY=sua_chave

# Envio por e-mail (opcional)
GMAIL_ADDRESS=seu-email@gmail.com
GMAIL_APP_PASSWORD=sua_senha_de_app

# Preferências (opcional)
HOME_CITY=Florianópolis
SEARCH_KEYWORDS=desenvolvedor fullstack
UI_LANG=pt          # idioma do painel: pt ou ru
```

Onde conseguir cada chave (todas têm plano gratuito):

| Chave | Onde | Obrigatória? |
|---|---|---|
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | https://developer.adzuna.com/signup | Sim (busca) |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/api_keys | Sim (currículo) |
| `JOOBLE_API_KEY` | https://jooble.org/api/about | Não |
| `GMAIL_APP_PASSWORD` | https://myaccount.google.com/apppasswords | Não (só p/ envio) |

> **Senha de app do Gmail**: é uma senha específica para aplicativos, não a sua
> senha normal. Exige verificação em duas etapas ativada. O `.env` está no
> `.gitignore` — nunca comite suas chaves.

## Uso

```bash
python app.py
```

Abra `http://127.0.0.1:5000` no navegador. Tudo é feito por ali:

- **🔍 Buscar vagas** — roda a busca nas 7 fontes (pode digitar palavras-chave e
  marcar "incluir sênior" / "qualquer localização").
- **Gerar currículo** — cria o currículo sob medida para aquela vaga (~30s).
- **Abrir PDF** — vê o resultado.
- **★** — favorita a vaga (sobe para o topo; filtro "Só favoritas" no topo).
- **Marcar como enviada** — a vaga vai para o **📁 Arquivo** (para vagas em que
  você se candidatou pelo site).
- **✕ Excluir** — some da lista e não volta nem em buscas futuras.
- **Enviar selecionadas (e-mail)** — só para vagas com e-mail de contato; pede
  confirmação antes de enviar de verdade.
- **PT / RU** (canto superior direito) — troca o idioma do painel.

### Colar uma vaga manualmente

Achou uma vaga no Vagas.com, Gupy, Catho ou LinkedIn? Essas plataformas não têm
API pública, e fazer scraping violaria os termos de uso delas. Então:

1. Abra a vaga no site (há botões de busca prontos no painel).
2. Copie o texto da vaga.
3. Cole no bloco **"➕ Colar vaga manualmente"** e clique em gerar.

O bot cria o currículo sob medida sem tocar no site — você navega e copia, ele
só adapta.

### Pela linha de comando (opcional)

```bash
python main.py "desenvolvedor fullstack"        # só busca, salva em jobs_found.csv
python main.py "python" --include-senior        # inclui vagas sênior
python main.py "dev" --any-location             # sem filtro de localização
python clean_applications.py --days 45 --apply  # limpa currículos antigos
```

## Fontes de vagas

| Fonte | Cobertura | Chave |
|---|---|---|
| **Adzuna** | Brasil (3 passadas: sua palavra-chave, busca ampla, reforço local) | Sim |
| **Jooble** | Agregador, Brasil | Sim (grátis) |
| **Remotive** | Remoto internacional | Não |
| **Arbeitnow** | Remoto internacional | Não |
| **RemoteOK** | Remoto internacional | Não |
| **Jobicy** | Remoto internacional | Não |
| **The Muse** | Brasil + remoto | Não |

Vagas duplicadas entre fontes são unificadas. O `jobs_found.csv` **acumula**
entre buscas: vagas já vistas mantêm histórico e currículo; as que somem da
busca ficam marcadas como "fora da última busca" e só são descartadas após
`STALE_JOB_DROP_DAYS` dias (padrão: 45).

## Filtros

Três filtros rodam em sequência (todos ajustáveis pelo `.env`):

1. **Relevância** — mantém só vagas de desenvolvimento (`RELEVANCE_KEYWORDS`).
2. **Senioridade** — descarta sênior/lead/gestão (desligue com `--include-senior`).
3. **Localização** — mantém vagas na sua cidade (`HOME_CITY`) **ou** remotas de
   verdade. Vagas híbridas em outra cidade contam como presenciais e são
   descartadas; vagas "remotas" presas a outro país (ex.: "Remote (Berlin)")
   também. Desligue com `--any-location`.

## Princípios de segurança

Decisões deliberadas do projeto — veja `SECURITY_REVIEW.md`:

- **Sem login ou automação em plataformas de emprego.** Nada de Selenium
  logando no LinkedIn/Gupy/Catho. Isso viola os termos de uso delas.
- **Sem scraping.** Só APIs públicas e oficiais. Para plataformas sem API, o
  bot abre a busca no site para você navegar, ou você cola o texto da vaga.
- **Nenhum envio sem confirmação.** Não existe modo "candidatar-se
  automaticamente a tudo".
- **Sem invenção no currículo.** O prompt proíbe explicitamente adicionar
  tecnologias, empresas ou experiências que não estejam no seu currículo base.
- **Roda só localmente** (`127.0.0.1`) — nada é exposto para a internet.
- **Seus dados ficam com você**: `.env`, `base_resume.md`, `jobs_found.csv` e
  `applications/` estão todos no `.gitignore`.

## Estrutura

```
app.py                  painel web local (Flask, bilíngue PT/RU)
main.py                 busca pela linha de comando
search_jobs.py          Adzuna + merge do jobs_found.csv
extra_sources.py        as 6 fontes extras
filters.py              relevância, senioridade, localização
tailor_resume.py        geração do currículo com IA (prompt anti-invenção + ATS)
send_application.py     envio por e-mail (SMTP)
status_store.py         status de candidatura (arquivo/excluídas)
favorites_store.py      vagas favoritas (★)
clean_applications.py   limpeza de currículos antigos
export_pdf.py           Markdown → PDF
config.py               configuração via .env
test_*.py               testes (rodam offline, sem rede)
base_resume.example.md  modelo do currículo base
```

Testes:

```bash
python test_filters.py && python test_app.py && python test_search_jobs.py
```

## Limitações conhecidas

- O volume de vagas depende do seu nicho. Filtros rigorosos (júnior/pleno +
  cidade específica) podem render poucas vagas novas por dia — isso é o mercado,
  não um bug.
- Plataformas brasileiras (Vagas.com, Gupy, Catho, InfoJobs) não têm API pública
  e não são raspadas por decisão de projeto; use o fluxo de colar manualmente.
- A qualidade do currículo depende da qualidade do seu `base_resume.md`.
  **Sempre revise o PDF antes de enviar.**

## Licença

[MIT](LICENSE) — use, modifique e adapte à sua busca de emprego.
