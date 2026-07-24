"""
Painel local (Flask) para o fluxo semi-automático:
  1. você RODA a busca antes:  python main.py "desenvolvedor fullstack"
     (isso só salva jobs_found.csv — NÃO gera currículos)
  2. rode este painel:         python app.py
  3. abra http://127.0.0.1:5000 no navegador
  4. escolha as vagas, clique "Gerar currículo" nas que interessam
  5. marque as vagas com e-mail de contato e clique "Enviar selecionados"
     (confirma antes de enviar — nada sai sem seu OK)

Só envia por e-mail as vagas que trazem um e-mail de contato na descrição.
Vagas de plataforma (Adzuna/LinkedIn/Gupy/…) continuam manuais: botão "Abrir
vaga" leva ao site para você se candidatar lá. Nada de login/automação de
plataforma (ver SECURITY_REVIEW.md).

Roda só localmente (127.0.0.1) — nada é exposto para a internet.
"""
import csv
import html
import os
import re
import unicodedata
import urllib.parse

from flask import Flask, jsonify, request, send_from_directory

import config
import search_jobs as search_jobs_mod
import send_application
import status_store
import tailor_resume

app = Flask(__name__)


@app.after_request
def _no_cache(resp):
    # painel local — nunca cachear o HTML/JS, senão o navegador mostra versão
    # antiga depois de a gente atualizar o app.py
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

_client = None          # cliente da API (lazy)
_base_resume_cache = None


def _get_client():
    global _client
    if _client is None:
        _client = tailor_resume.make_client()  # RuntimeError se sem chave
    return _client


def _base_resume():
    global _base_resume_cache
    if _base_resume_cache is None:
        _base_resume_cache = tailor_resume.load_base_resume()
    return _base_resume_cache


def load_jobs():
    """Lê jobs_found.csv (fonte da verdade). Retorna lista de dicts."""
    path = config.JOBS_CSV
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def job_view(job: dict) -> dict:
    """Enriquece a vaga com status para a UI."""
    folder = tailor_resume.folder_for(job)
    pdf_path = os.path.join(folder, "resume.pdf")
    md_path = os.path.join(folder, "resume.md")
    has_resume = os.path.exists(pdf_path) or os.path.exists(md_path)
    email = tailor_resume.extract_email(
        job.get("description", ""), job.get("redirect_url", "")
    )
    applied = status_store.get(job.get("id", ""))
    return {
        "id": job.get("id", ""),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "link": job.get("redirect_url", ""),
        "email": email,
        "has_resume": has_resume,
        "folder": os.path.basename(folder.rstrip("/\\")),
        "last_seen": job.get("last_seen", ""),
        "applied_status": applied.get("status", ""),
        "applied_date": applied.get("data", ""),
        "applied_canal": applied.get("canal", ""),
    }


def _find_job(job_id: str):
    for job in load_jobs():
        if job.get("id") == job_id:
            return job
    return None


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def build_search_links(keyword: str = None, location: str = None) -> list:
    """Links de BUSCA (não scraping) para plataformas que não têm API pública:
    abrem a página de busca já com seus critérios, para você revisar e se
    candidatar manualmente no site. Legal e sem risco de bloqueio."""
    kw = keyword or config.SEARCH_KEYWORDS
    loc = location or config.HOME_CITY
    kw_enc = urllib.parse.quote(kw)
    loc_enc = urllib.parse.quote(loc)
    kw_slug = _slug(kw)
    loc_slug = _slug(loc)
    return [
        {"name": "Vagas.com", "url": f"https://www.vagas.com.br/vagas-de-{kw_slug}"},
        {"name": f"Vagas.com ({loc})",
         "url": f"https://www.vagas.com.br/vagas-de-{kw_slug}-em-{loc_slug}-sc"},
        {"name": "Gupy", "url": f"https://portal.gupy.io/job-search/term={kw_enc}"},
        {"name": "Catho", "url": f"https://www.catho.com.br/vagas/{kw_slug}/"},
        {"name": "InfoJobs",
         "url": f"https://www.infojobs.com.br/vagas-de-emprego-{kw_slug}.aspx"},
        {"name": "LinkedIn",
         "url": f"https://www.linkedin.com/jobs/search/?keywords={kw_enc}"
                f"&location={loc_enc}"},
    ]


# ---------------------------------------------------------------- rotas -------

_ARCHIVED_STATUSES = ("enviado", "candidatei manualmente")


@app.route("/")
def index():
    kw = request.args.get("q") or config.SEARCH_KEYWORDS
    jobs = [job_view(j) for j in load_jobs()]
    # "última busca" = data mais recente vista entre as vagas atuais; quem
    # não tem essa data não voltou a aparecer na busca mais recente
    latest = max((j["last_seen"] for j in jobs if j["last_seen"]), default="")
    active, archived = [], []
    for j in jobs:
        j["is_stale"] = bool(latest) and j["last_seen"] and j["last_seen"] != latest
        st = j["applied_status"]
        if st == "removido":
            continue  # vagas excluídas: não aparecem em lugar nenhum
        if st in _ARCHIVED_STATUSES:
            archived.append(j)  # já me candidatei -> arquivo
        else:
            active.append(j)
    return render_page(active, build_search_links(kw), archived=archived)


@app.route("/tailor", methods=["POST"])
def tailor():
    job_id = (request.json or {}).get("id", "")
    job = _find_job(job_id)
    if not job:
        return jsonify(ok=False, error="Vaga não encontrada."), 404
    try:
        client = _get_client()
        tailor_resume.tailor_and_save(client, _base_resume(), job)
    except Exception as e:  # noqa: BLE001 — devolve erro amigável para a UI
        return jsonify(ok=False, error=str(e)), 500
    view = job_view(job)
    return jsonify(ok=True, has_resume=view["has_resume"], folder=view["folder"])


@app.route("/tailor_manual", methods=["POST"])
def tailor_manual():
    """Gera currículo para uma vaga que VOCÊ colou (achou manualmente numa
    plataforma). Legal: você navega e copia o texto; o bot só adapta o
    currículo. Não faz fetch/scraping de link."""
    import hashlib
    data = request.json or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    company = (data.get("company") or "").strip() or "vaga-manual"
    link = (data.get("link") or "").strip()
    if not title or not description:
        return jsonify(ok=False,
                       error="Preencha o título e cole o texto da vaga."), 400
    jid = "manual-" + hashlib.sha1(
        (title + "|" + description).encode("utf-8")).hexdigest()[:10]
    job = {
        "id": jid, "title": title, "company": company,
        "location": (data.get("location") or "").strip() or "informado manualmente",
        "description": description, "redirect_url": link,
    }
    try:
        client = _get_client()
        folder = tailor_resume.tailor_and_save(client, _base_resume(), job)
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(
        ok=True,
        id=jid,
        folder=os.path.basename(folder.rstrip("/\\")),
        title=title,
        company=company,
        email=tailor_resume.extract_email(description, link),
    )


@app.route("/send_manual", methods=["POST"])
def send_manual():
    """Envia por e-mail o currículo de uma vaga colada manualmente."""
    data = request.json or {}
    folder_name = os.path.basename((data.get("folder") or "").rstrip("/\\"))
    email = (data.get("email") or "").strip()
    title = (data.get("title") or "vaga").strip()
    jid = (data.get("id") or "").strip()
    company = (data.get("company") or "").strip()
    if not folder_name or not email:
        return jsonify(ok=False, error="Faltam pasta ou e-mail."), 400
    target_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    attachment = send_application.resume_attachment(target_dir)
    if not os.path.exists(attachment):
        return jsonify(ok=False, error="Gere o currículo antes de enviar."), 400
    subject, body = send_application.subject_and_body(title)
    try:
        send_application.send_email(email, subject, body, attachment)
    except send_application.SendError as e:
        return jsonify(ok=False, error=str(e)), 500
    if jid:
        status_store.set_status(jid, titulo=title, empresa=company,
                                 status="enviado", canal="email", contato=email)
    return jsonify(ok=True, msg=f"enviado p/ {email}")


@app.route("/send", methods=["POST"])
def send():
    ids = (request.json or {}).get("ids", [])
    results = []
    for job_id in ids:
        job = _find_job(job_id)
        if not job:
            results.append({"id": job_id, "ok": False, "msg": "vaga não encontrada"})
            continue
        view = job_view(job)
        if not view["email"]:
            results.append({"id": job_id, "ok": False,
                            "msg": "sem e-mail de contato (candidate-se pelo link)"})
            continue
        folder = tailor_resume.folder_for(job)
        attachment = send_application.resume_attachment(folder)
        if not os.path.exists(attachment):
            results.append({"id": job_id, "ok": False,
                            "msg": "gere o currículo antes de enviar"})
            continue
        subject, body = send_application.subject_and_body(view["title"])
        try:
            send_application.send_email(view["email"], subject, body, attachment)
            status_store.set_status(job_id, titulo=view["title"], empresa=view["company"],
                                     status="enviado", canal="email", contato=view["email"])
            results.append({"id": job_id, "ok": True, "msg": f"enviado p/ {view['email']}"})
        except send_application.SendError as e:
            results.append({"id": job_id, "ok": False, "msg": str(e)})
    return jsonify(results=results)


@app.route("/mark_applied", methods=["POST"])
def mark_applied():
    """Marca/desmarca manualmente uma vaga como 'já me candidatei' — para as
    vagas de plataforma (Vagas.com/Gupy/LinkedIn/…) onde você aplica direto
    no site e o bot não tem como saber sozinho."""
    data = request.json or {}
    jid = (data.get("id") or "").strip()
    if not jid:
        return jsonify(ok=False, error="Falta o id da vaga."), 400
    applied = bool(data.get("applied", True))
    if applied:
        status_store.set_status(
            jid, titulo=(data.get("title") or "").strip(),
            empresa=(data.get("company") or "").strip(),
            status="candidatei manualmente", canal="manual",
        )
    else:
        status_store.set_status(jid, status="")
    return jsonify(ok=True, applied=applied)


@app.route("/delete", methods=["POST"])
def delete():
    """Exclui uma vaga do painel (não serve, não interessa). Fica marcada como
    'removido' no status.csv, então NÃO reaparece nem depois de uma nova busca
    (o merge do jobs_found.csv pode trazer a vaga de volta ao CSV, mas o painel
    a esconde). Para desfazer, apague a linha dela em applications/status.csv."""
    data = request.json or {}
    jid = (data.get("id") or "").strip()
    if not jid:
        return jsonify(ok=False, error="Falta o id da vaga."), 400
    status_store.set_status(
        jid, titulo=(data.get("title") or "").strip(),
        empresa=(data.get("company") or "").strip(),
        status="removido", canal="deleted",
    )
    return jsonify(ok=True)


@app.route("/search", methods=["POST"])
def search():
    """Roda a busca de vagas (Adzuna + fontes extras) e mescla no
    jobs_found.csv — o mesmo que 'python main.py', mas pelo painel, para
    você não precisar do terminal. Faz chamadas de rede: pode levar alguns
    segundos. Só busca; NÃO gera currículos."""
    data = request.json or {}
    keywords = (data.get("keywords") or "").strip() or None
    include_senior = bool(data.get("include_senior"))
    any_location = bool(data.get("any_location"))
    try:
        jobs = search_jobs_mod.search_jobs(
            keywords,
            filter_seniority=False if include_senior else None,
            filter_location=False if any_location else None,
        )
        final = search_jobs_mod.save_jobs_csv(jobs)
    except SystemExit as e:
        # search_jobs faz sys.exit se faltar chave da Adzuna — trata sem
        # derrubar o servidor
        return jsonify(ok=False, error="Busca falhou: verifique ADZUNA_APP_ID/"
                       "ADZUNA_APP_KEY no .env."), 500
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, error=str(e)), 500
    return jsonify(ok=True, total=len(final), found=len(jobs))


@app.route("/pdf/<folder>")
def pdf(folder):
    # serve o currículo daquela vaga (PDF; cai para .md)
    base = os.path.abspath(config.OUTPUT_DIR)
    target_dir = os.path.join(base, folder)
    fname = "resume.pdf" if os.path.exists(os.path.join(target_dir, "resume.pdf")) \
        else "resume.md"
    return send_from_directory(target_dir, fname)


# ---------------------------------------------------------------- html --------

def _row_html(j: dict, archived: bool = False) -> str:
    tid = html.escape(j["id"], quote=True)
    title_esc = html.escape(j["title"])
    company_esc = html.escape(j["company"])
    title_attr = html.escape(j["title"], quote=True)
    company_attr = html.escape(j["company"], quote=True)
    email_badge = (f'<span class="badge email">✉ {html.escape(j["email"])}</span>'
                   if j["email"] else '<span class="badge link">только ссылка</span>')
    stale_badge = (' <span class="badge stale">⚠ не в последнем поиске'
                   f'{" (" + html.escape(j["last_seen"]) + ")" if j.get("last_seen") else ""}'
                   '</span>') if j.get("is_stale") else ""
    # ссылку "Открыть PDF" рендерим ВСЕГДА, но прячем, если резюме ещё нет —
    # так JS после генерации просто показывает готовый элемент и не создаёт дубль
    pdf_style = "" if j["has_resume"] else ' style="display:none"'
    resume_cell = (
        f'<a class="btn small pdf-link" href="/pdf/{html.escape(j["folder"], quote=True)}" '
        f'target="_blank"{pdf_style}>Открыть PDF</a>')
    checkbox = (f'<input type="checkbox" class="sel" value="{tid}">'
                if j["email"] and not archived else '')
    if j["applied_status"] == "enviado":
        applied_cell = (f'<span class="badge applied">✅ отправлено {html.escape(j["applied_date"])}'
                        f' (email)</span> '
                        f'<button class="btn small ghost" onclick="unmark(this,\'{tid}\')">вернуть</button>')
    elif j["applied_status"]:
        applied_cell = (
            f'<span class="badge applied">✅ откликался {html.escape(j["applied_date"])}</span> '
            f'<button class="btn small ghost" onclick="unmark(this,\'{tid}\')">вернуть</button>')
    else:
        applied_cell = (f'<button class="btn small ghost mark-btn" '
                        f'onclick="mark(this,\'{tid}\',\'{title_attr}\',\'{company_attr}\')">'
                        f'Отметить как отправлено</button>')
    del_btn = (f'<button class="btn small del" title="Удалить вакансию из списка" '
               f'onclick="excluir(this,\'{tid}\',\'{title_attr}\',\'{company_attr}\')">✕ Удалить</button>')
    return f"""
        <tr data-id="{tid}" data-email="{'1' if j['email'] else '0'}">
          <td>{checkbox}</td>
          <td><div class="title">{title_esc}</div>
              <div class="muted">{company_esc} · {html.escape(j["location"])}</div>
              {email_badge}{stale_badge}</td>
          <td class="status">{'✅ готово' if j['has_resume'] else '<span class="muted">не создано</span>'}</td>
          <td class="applied-cell">{applied_cell}</td>
          <td>
            <button class="btn gen" onclick="gerar(this, '{tid}')">Создать резюме</button>
            <a class="btn ghost" href="{html.escape(j["link"], quote=True)}" target="_blank">Открыть вакансию</a>
            {resume_cell}
            {del_btn}
          </td>
        </tr>"""


def render_page(jobs: list, search_links: list = None, archived: list = None) -> str:
    archived = archived or []
    links_html = ""
    if search_links:
        btns = " ".join(
            f'<a class="btn ghost small" href="{html.escape(l["url"], quote=True)}" '
            f'target="_blank" rel="noopener">{html.escape(l["name"])}</a>'
            for l in search_links
        )
        links_html = (
            '<div class="links"><b>Искать вручную</b> (открывает поиск на сайте — '
            'откликаться там; без скрапинга): ' + btns + '</div>'
        )
    rows_html = "\n".join(_row_html(j) for j in jobs) if jobs else (
        '<tr><td colspan="5" class="muted">Нет активных вакансий. '
        'Нажми «🔍 Запустить поиск» вверху или запусти '
        '<code>python main.py "desenvolvedor fullstack"</code>.</td></tr>')

    archive_html = ""
    if archived:
        arows = "\n".join(_row_html(j, archived=True) for j in archived)
        archive_html = (
            f'<details class="archive"><summary>📁 Архив — вакансии, на которые '
            f'откликался ({len(archived)})</summary>'
            f'<table><thead><tr><th></th><th>Вакансия</th><th>Резюме</th>'
            f'<th>Отклик</th><th>Действия</th></tr></thead><tbody>{arows}</tbody></table>'
            f'</details>')

    return (PAGE.replace("{{ROWS}}", rows_html)
                .replace("{{COUNT}}", str(len(jobs)))
                .replace("{{ARCHIVE}}", archive_html)
                .replace("{{LINKS}}", links_html))


PAGE = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<title>Job Bot — панель</title>
<style>
  body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#f4f4f2;color:#222;margin:0;padding:24px}
  h1{margin:0 0 4px} .sub{color:#555;margin:0 0 16px}
  .bar{position:sticky;top:0;background:#f4f4f2;padding:12px 0;display:flex;gap:12px;align-items:center;border-bottom:1px solid #ddd;margin-bottom:8px}
  table{width:100%;border-collapse:collapse;background:#fff}
  th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #eee;vertical-align:top}
  th{font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#666}
  .title{font-weight:600}
  .muted{color:#999;font-size:13px}
  .badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;margin-top:4px}
  .badge.email{background:#e3f0e3;color:#2f6f4f} .badge.link{background:#eee;color:#777}
  .badge.stale{background:#fdecec;color:#a33} .badge.applied{background:#e3ecf7;color:#2f5f9f}
  .btn{display:inline-block;font-size:13px;padding:7px 11px;border-radius:6px;border:1px solid #2f6f4f;background:#2f6f4f;color:#fff;cursor:pointer;text-decoration:none;margin:2px}
  .btn.ghost{background:#fff;color:#2f6f4f}
  .btn.small{background:#fff;color:#555;border-color:#ccc;padding:5px 9px}
  .btn:disabled{opacity:.5;cursor:default}
  .btn.primary{background:#b4622b;border-color:#b4622b}
  .btn.del{border-color:#d9a3a3;color:#a33}
  .archive{margin-top:18px;background:#fff;border:1px solid #ddd;border-radius:8px;padding:8px 14px}
  .archive summary{cursor:pointer;font-weight:600;color:#555}
  .archive table{margin-top:10px}
  .warn{background:#fff4e5;border:1px solid #f0c36d;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px}
  .links{background:#eef2f4;border:1px solid #d5dde0;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px}
  .manual{background:#fff;border:1px solid #d5dde0;border-radius:8px;padding:8px 14px;font-size:13px;margin-bottom:12px}
  .manual summary{cursor:pointer;font-weight:600}
  .mform{display:flex;flex-direction:column;gap:8px;margin-top:10px;max-width:720px}
  .mform input,.mform textarea{font:inherit;padding:8px;border:1px solid #ccc;border-radius:6px}
  .bar input[type=text],.bar #s_kw{font:inherit;padding:7px 9px;border:1px solid #ccc;border-radius:6px}
  .chk{font-size:13px;color:#555;display:flex;align-items:center;gap:4px}
  #log{font-size:13px;margin-left:auto;color:#444}
</style></head><body>
  <h1>Job Bot — панель</h1>
  <p class="sub">{{COUNT}} вакансий в jobs_found.csv. Создавай резюме только под интересные; отправляй по e-mail отмеченные.</p>
  <div class="warn">Автоматически отправить можно только вакансии с <b>контактным e-mail</b> (у них доступен чекбокс). Вакансии с площадок: жми <b>Открыть вакансию</b> и откликайся на сайте. Ничего не отправляется без твоего подтверждения.</div>
  {{LINKS}}
  <details class="manual"><summary>➕ Вставить вакансию вручную (нашёл на Vagas.com / Gupy / LinkedIn?)</summary>
    <div class="mform">
      <div class="muted">Скопируй ТЕКСТ вакансии с сайта и вставь ниже. Бот создаст резюме под неё (ничего не качается с сайта — ты копируешь, бот только адаптирует).</div>
      <input id="m_title" placeholder="Название вакансии * (напр.: Desenvolvedor Backend Python)">
      <input id="m_company" placeholder="Компания (необязательно)">
      <input id="m_link" placeholder="Ссылка на вакансию (необязательно, чтобы открыть потом)">
      <textarea id="m_desc" rows="7" placeholder="Вставь сюда описание/требования вакансии *"></textarea>
      <div><button class="btn" onclick="gerarManual()">Создать резюме под эту вакансию</button>
           <span id="mresult"></span></div>
    </div>
  </details>
  <div class="bar">
    <input id="s_kw" placeholder="ключевые слова (напр.: desenvolvedor python)" style="min-width:260px">
    <button class="btn" onclick="buscar(this)">🔍 Запустить поиск</button>
    <label class="chk"><input type="checkbox" id="s_senior"> с senior</label>
    <label class="chk"><input type="checkbox" id="s_anyloc"> любая локация</label>
    <button class="btn ghost" onclick="location.reload()">↻ Обновить</button>
    <button class="btn primary" onclick="enviar()">Отправить выбранные (e-mail)</button>
    <span class="muted" id="selinfo">0 выбрано</span>
    <span id="log"></span>
  </div>
  <table>
    <thead><tr><th></th><th>Вакансия</th><th>Резюме</th><th>Отклик</th><th>Действия</th></tr></thead>
    <tbody>{{ROWS}}</tbody>
  </table>
  {{ARCHIVE}}
<script>
function setLog(t){document.getElementById('log').textContent=t;}
function updSel(){
  const n=document.querySelectorAll('.sel:checked').length;
  document.getElementById('selinfo').textContent=n+' выбрано';
}
document.addEventListener('change',e=>{if(e.target.classList.contains('sel'))updSel();});

async function buscar(btn){
  const keywords=document.getElementById('s_kw').value.trim();
  const include_senior=document.getElementById('s_senior').checked;
  const any_location=document.getElementById('s_anyloc').checked;
  btn.disabled=true;const old=btn.textContent;btn.textContent='Ищу…';
  setLog('Ищу вакансии (Adzuna + 6 источников)… это займёт несколько секунд.');
  try{
    const r=await fetch('/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keywords,include_senior,any_location})});
    const d=await r.json();
    if(d.ok){setLog('Найдено в этом поиске: '+d.found+'. Всего в списке: '+d.total+'. Обновляю…');
      setTimeout(()=>location.reload(),800);}
    else{btn.disabled=false;btn.textContent=old;setLog('Ошибка: '+d.error);}
  }catch(e){btn.disabled=false;btn.textContent=old;setLog('Ошибка сети: '+e);}
}

async function gerar(btn,id){
  btn.disabled=true;const old=btn.textContent;btn.textContent='Создаю…';setLog('Создаю резюме…');
  try{
    const r=await fetch('/tailor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    const d=await r.json();
    if(d.ok){btn.disabled=false;btn.textContent=old;
      const cell=btn.closest('tr').querySelector('.status');cell.innerHTML='✅ готово';
      // используем уже существующую ссылку в строке — не создаём вторую
      let a=btn.parentNode.querySelector('.pdf-link');
      if(!a){a=document.createElement('a');a.className='btn small pdf-link';a.target='_blank';a.textContent='Открыть PDF';btn.parentNode.appendChild(a);}
      a.href='/pdf/'+d.folder;a.style.display='';
      setLog('Резюме создано.');}
    else{btn.disabled=false;btn.textContent=old;setLog('Ошибка: '+d.error);}
  }catch(e){btn.disabled=false;btn.textContent=old;setLog('Ошибка сети: '+e);}
}

async function gerarManual(){
  const title=document.getElementById('m_title').value.trim();
  const description=document.getElementById('m_desc').value.trim();
  const company=document.getElementById('m_company').value.trim();
  const link=document.getElementById('m_link').value.trim();
  const out=document.getElementById('mresult');
  if(!title||!description){alert('Заполни название и вставь текст вакансии.');return;}
  out.textContent=' Создаю…';
  try{
    const r=await fetch('/tailor_manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,description,company,link})});
    const d=await r.json();
    if(!d.ok){out.textContent=' Ошибка: '+d.error;return;}
    out.innerHTML=' ✅ Готово — <a class="btn small" target="_blank" href="/pdf/'+d.folder+'">Открыть PDF</a>';
    if(d.email){
      const b=document.createElement('button');b.className='btn small';b.textContent='Отправить на '+d.email;
      b.onclick=async()=>{
        if(!confirm('Отправить твоё резюме на '+d.email+'?'))return;
        b.disabled=true;b.textContent='Отправляю…';
        const rr=await fetch('/send_manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:d.id,folder:d.folder,email:d.email,title:d.title,company:d.company})});
        const dd=await rr.json();b.textContent=dd.ok?('✓ '+dd.msg):('Ошибка: '+dd.error);
      };
      out.appendChild(document.createTextNode(' '));out.appendChild(b);
    }
  }catch(e){out.textContent=' Ошибка сети: '+e;}
}

function removeRow(id){
  const row=document.querySelector('tr[data-id="'+id+'"]');
  if(row){row.style.transition='opacity .3s';row.style.opacity='0';setTimeout(()=>row.remove(),300);}
}

async function enviar(){
  const ids=[...document.querySelectorAll('.sel:checked')].map(c=>c.value);
  if(!ids.length){alert('Отметь хотя бы одну вакансию с контактным e-mail.');return;}
  if(!confirm('Отправить твоё резюме по e-mail в '+ids.length+' вакансий? Отправка настоящая.'))return;
  setLog('Отправляю…');
  try{
    const r=await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
    const d=await r.json();
    const ok=d.results.filter(x=>x.ok).length;
    setLog('Отправлено: '+ok+'/'+d.results.length+' (отправленные ушли в архив). '+d.results.map(x=>x.msg).join(' | '));
    // успешно отправленные -> в архив (убираем из активного списка)
    d.results.forEach(res=>{if(res.ok)removeRow(res.id);});
  }catch(e){setLog('Ошибка сети: '+e);}
}

async function mark(btn,id,title,company){
  btn.disabled=true;btn.textContent='...';
  try{
    const r=await fetch('/mark_applied',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,title,company,applied:true})});
    const d=await r.json();
    if(d.ok){removeRow(id);setLog('Помечено как отклик — ушло в архив (открой «📁 Архив» внизу).');}
    else{btn.disabled=false;btn.textContent='Отметить как отправлено';setLog('Ошибка: '+d.error);}
  }catch(e){btn.disabled=false;btn.textContent='Отметить как отправлено';setLog('Ошибка сети: '+e);}
}

async function unmark(btn,id){
  // "вернуть" из архива в активные: снимаем статус отклика и убираем строку из
  // архива (появится в активных после «↻ Обновить»)
  btn.disabled=true;
  try{
    const r=await fetch('/mark_applied',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,applied:false})});
    const d=await r.json();
    if(d.ok){removeRow(id);setLog('Возвращено в активные — нажми «↻ Обновить», чтобы увидеть.');}
    else{btn.disabled=false;setLog('Ошибка: '+d.error);}
  }catch(e){btn.disabled=false;setLog('Ошибка сети: '+e);}
}

async function excluir(btn,id,title,company){
  if(!confirm('Удалить вакансию «'+title+'» из списка? Она не будет появляться снова, даже после нового поиска.'))return;
  btn.disabled=true;btn.textContent='...';
  try{
    const r=await fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,title,company})});
    const d=await r.json();
    if(d.ok){removeRow(id);setLog('Вакансия удалена.');}
    else{btn.disabled=false;btn.textContent='✕ Удалить';setLog('Ошибка: '+d.error);}
  }catch(e){btn.disabled=false;btn.textContent='✕ Удалить';setLog('Ошибка сети: '+e);}
}
</script>
</body></html>"""


if __name__ == "__main__":
    # porta configurável: defina a env var PORT (ex.: set PORT=5001) para rodar
    # em outra porta se a 5000 estiver presa por um processo antigo do painel
    port = int(os.environ.get("PORT", "5000"))
    print(f"Painel em http://127.0.0.1:{port}  (Ctrl+C para parar)")
    print("*** VERSAO NOVA: busca no painel + coluna Otklik + no-cache ***")
    app.run(host="127.0.0.1", port=port, debug=False)
