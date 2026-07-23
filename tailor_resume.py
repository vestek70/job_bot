"""
Gera uma versão do currículo (base_resume.md) adaptada para cada vaga em jobs_found.csv.

Usa a API da DeepSeek (modelo deepseek-v4-pro, via endpoint compatível com a API da
Anthropic) para reescrever ênfase/palavras-chave — SEM inventar experiência, empresas
ou tecnologias que não estão no currículo base.

Requer variável de ambiente DEEPSEEK_API_KEY (chave: https://platform.deepseek.com/api_keys).

Cada resultado é salvo em applications/<empresa>_<vaga>/resume.md para VOCÊ revisar
antes de enviar. Nada é enviado automaticamente por este script.
"""
import csv
import os
import re
import sys
import time

import anthropic

import config

TAILOR_PROMPT = """You are a career assistant. Below is a candidate's BASE resume \
(a complete, detailed fact base — longer than a normal resume) and a job posting.

Your task: produce a SHORT, ready-to-send resume by selecting and prioritizing ONLY \
the REAL parts of the base resume that are relevant to this specific job.

IMPORTANT RULES:
- Target length: about ONE printed page (roughly 400-550 words total, not counting \
header/contact info). Cut aggressively anything not relevant to this specific job —
you do NOT have to use all the content from the base resume.
- From the projects, pick only the bullet points (architecture, payments, security, \
AI, testing, etc.) most relevant to this job — usually 4 to 7 bullets total across \
projects, not the full list.
- Do NOT invent professional experience, companies, job titles, years of experience, \
technologies, or certifications that are not in the base resume.
- NEVER name a specific technology, framework, runtime, or tool unless it appears \
VERBATIM in the base resume. This includes "reframing" — e.g. if the base resume \
says "Deno/TypeScript Edge Functions", do NOT rewrite that as "Node.js" or "Express" \
or any other technology just because it's conceptually similar or the job posting \
asks for it. Rephrasing wording is fine; substituting or adding technology NAMES is \
fabrication, full stop — even if hedged as "applied concepts" or "similar to X".
- If the base resume contains a literal "[PLACEHOLDER...]" marker or is otherwise \
unresolved/unclear for some fact, DO NOT invent or pick a value for it (even if the \
placeholder text itself lists example options) — omit that line/bullet entirely from \
the output instead of guessing.
- You may rephrase sentences, reorder sections, and emphasize existing skills that \
match the job.
- You may add a short summary (2-3 lines) connecting the candidate's profile to the \
job, but using only facts from the base resume.
- Keep the same field of work (fullstack development) — do not adapt it into a \
different profession.
- If the job asks for a specific technology that is not in the base resume, do NOT \
claim the candidate knows it — at most mention willingness to learn, if it makes sense.
- Write the output in Brazilian Portuguese, in Markdown, using the same section \
structure as the base resume, but condensed per the rules above.

ATS-FRIENDLY FORMATTING (so parsers like Workday, Taleo, Greenhouse read it correctly):
- Plain Markdown only: no tables, no icons/emoji, no text boxes. Standard section \
headings (e.g. "Resumo", "Experiência", "Formação", not creative alternatives).
- Bullet character: "-" only.
- Spell out acronyms on first use, e.g. "Row Level Security (RLS)".

BANNED PHRASES — do not use any of these (rewrite with concrete evidence instead):
results-driven, dynamic individual, highly motivated, team player, proven track \
record, passionate about, detail-oriented, self-starter, hard worker, strong \
communication skills, synergy, thought leader, go-getter, outside the box, \
people person, visionary, change agent — and their direct Portuguese equivalents \
(ex.: "apaixonado por", "dinâmico", "proativo" usado como enchimento vazio).

FINAL CHECK before output (do not output until every item passes):
- No fabricated title, company, technology, metric, or certification.
- Every technology NAME in the output appears verbatim somewhere in the base resume —
  go back and check each one individually; delete/replace any that don't.
- No placeholder value was invented or guessed.
- No banned phrase from the list above.
- Length is within the ~400-550 word target.
- Tense is consistent (past for finished work, present for anything ongoing).

BASE RESUME (complete fact source — do not copy everything, select from it):
---
{resume}
---

JOB POSTING ({title} — {company}):
---
{description}
---

Output only the tailored resume in Markdown, no extra commentary."""


def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60] or "vaga"


def load_jobs(path: str = None) -> list:
    path = path or config.JOBS_CSV
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_base_resume(path: str = "base_resume.md") -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _maybe_export_pdf(resume_path: str):
    """Gera resume.pdf ao lado do .md, se EXPORT_PDF e as libs estiverem disponíveis.
    Nunca derruba o pipeline: em falha, só avisa e segue (o .md continua válido)."""
    if not config.EXPORT_PDF:
        return
    try:
        import export_pdf
        export_pdf.convert_file(resume_path)
    except ImportError:
        print("  (PDF pulado: instale 'markdown' e 'xhtml2pdf' — pip install -r "
              "requirements.txt)", file=sys.stderr)
    except Exception as e:
        print(f"  (PDF pulado: {e})", file=sys.stderr)


def _extract_text(message) -> str:
    """Pega o primeiro bloco de texto na resposta.

    O endpoint da DeepSeek (deepseek-v4-pro) pode retornar um ThinkingBlock antes
    do TextBlock quando o modo "thinking" está ativo — não dá para assumir que
    content[0] já é o texto final.
    """
    for block in message.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise RuntimeError(
        "Resposta da API não contém bloco de texto (só thinking/outros tipos)."
    )


def tailor_one(client, base_resume: str, job: dict) -> str:
    prompt = TAILOR_PROMPT.format(
        resume=base_resume,
        title=job["title"],
        company=job["company"],
        description=(job["description"] or "")[:4000],
    )
    last_exc = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model=config.TAILOR_MODEL,
                max_tokens=2000,
                thinking={"type": "disabled"},
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_text(message)
        except anthropic.AuthenticationError:
            # Chave inválida: não adianta repetir, é erro fatal para todo o lote.
            raise
        except (anthropic.RateLimitError, anthropic.APIStatusError,
                anthropic.APIConnectionError) as e:
            last_exc = e
            wait = config.RETRY_BACKOFF * attempt
            print(f"  API instável ({type(e).__name__}), repetindo em {wait:.0f}s "
                  f"(tentativa {attempt}/{config.MAX_RETRIES})...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(
        f"Falha ao gerar currículo após {config.MAX_RETRIES} tentativas: {last_exc}"
    )


def main():
    if not config.DEEPSEEK_API_KEY:
        print(
            "ERRO: defina DEEPSEEK_API_KEY para gerar currículos adaptados "
            "(chave: https://platform.deepseek.com/api_keys).",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(
        api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL
    )
    base_resume = load_base_resume()
    jobs = load_jobs()

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    index_rows = []
    for job in jobs:
        folder_name = f"{slugify(job['company'])}_{slugify(job['title'])}_{job['id']}"
        folder_path = os.path.join(config.OUTPUT_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        resume_path = os.path.join(folder_path, "resume.md")
        if os.path.exists(resume_path):
            print(f"Já existe, pulando: {resume_path}")
        else:
            print(f"Adaptando currículo para: {job['title']} @ {job['company']}...")
            try:
                tailored = tailor_one(client, base_resume, job)
            except anthropic.AuthenticationError:
                print(
                    "ERRO: DEEPSEEK_API_KEY inválida. Confira a chave no .env "
                    "(https://platform.deepseek.com/api_keys).",
                    file=sys.stderr,
                )
                sys.exit(1)
            except RuntimeError as e:
                # Falha só nesta vaga: registra e segue para a próxima.
                print(f"  PULANDO esta vaga — {e}", file=sys.stderr)
                continue
            with open(resume_path, "w", encoding="utf-8") as f:
                f.write(tailored)
            _maybe_export_pdf(resume_path)

        with open(os.path.join(folder_path, "job_info.txt"), "w", encoding="utf-8") as f:
            f.write(f"Título: {job['title']}\n")
            f.write(f"Empresa: {job['company']}\n")
            f.write(f"Local: {job['location']}\n")
            f.write(f"Link para candidatura: {job['redirect_url']}\n")

        index_rows.append(
            {
                "empresa": job["company"],
                "vaga": job["title"],
                "pasta": folder_path,
                "link_candidatura": job["redirect_url"],
                "status": "aguardando revisão",
            }
        )

    index_path = os.path.join(config.OUTPUT_DIR, "index.csv")
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["empresa", "vaga", "pasta", "link_candidatura", "status"]
        )
        writer.writeheader()
        writer.writerows(index_rows)

    print(
        f"\nPronto. Revise os currículos em '{config.OUTPUT_DIR}/' e o resumo em "
        f"'{index_path}' ANTES de se candidatar ou enviar qualquer coisa."
    )


if __name__ == "__main__":
    main()
