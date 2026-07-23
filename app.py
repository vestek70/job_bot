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
import send_application
import tailor_resume

app = Flask(__name__)

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
    return {
        "id": job.get("id", ""),
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "link": job.get("redirect_url", ""),
        "email": email,
        "has_resume": has_resume,
        "folder": os.path.basename(folder.rstrip("/\\")),
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

@app.route("/")
def index():
    kw = request.args.get("q") or config.SEARCH_KEYWORDS
    jobs = [job_view(j) for j in load_jobs()]
    return render_page(jobs, build_search_links(kw))


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
        folder=os.path.basename(folder.rstrip("/\\")),
        title=title,
        email=tailor_resume.extract_email(description, link),
    )


@app.route("/send_manual", methods=["POST"])
def send_manual():
    """Envia por e-mail o currículo de uma vaga colada manualmente."""
    data = request.json or {}
    folder_name = os.path.basename((data.get("folder") or "").rstrip("/\\"))
    email = (data.get("email") or "").strip()
    title = (data.get("title") or "vaga").strip()
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
            results.append({"id": job_id, "ok": True, "msg": f"enviado p/ {view['email']}"})
        except send_application.SendError as e:
            results.append({"id": job_id, "ok": False, "msg": str(e)})
    return jsonify(results=results)


@app.route("/pdf/<folder>")
def pdf(folder):
    # serve o currículo daquela vaga (PDF; cai para .md)
    base = os.path.abspath(config.OUTPUT_DIR)
    target_dir = os.path.join(base, folder)
    fname = "resume.pdf" if os.path.exists(os.path.join(target_dir, "resume.pdf")) \
        else "resume.md"
    return send_from_directory(target_dir, fname)


# ---------------------------------------------------------------- html --------

def render_page(jobs: list, search_links: list = None) -> str:
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
    rows = []
    for j in jobs:
        tid = html.escape(j["id"], quote=True)
        email_badge = (f'<span class="badge email">✉ {html.escape(j["email"])}</span>'
                       if j["email"] else '<span class="badge link">только ссылка</span>')
        # ссылку "Открыть PDF" рендерим ВСЕГДА, но прячем, если резюме ещё нет —
        # так JS после генерации просто показывает готовый элемент и не создаёт дубль
        pdf_style = "" if j["has_resume"] else ' style="display:none"'
        resume_cell = (
            f'<a class="btn small pdf-link" href="/pdf/{html.escape(j["folder"], quote=True)}" '
            f'target="_blank"{pdf_style}>Открыть PDF</a>')
        checkbox = (f'<input type="checkbox" class="sel" value="{tid}">'
                    if j["email"] else '')
        rows.append(f"""
        <tr data-id="{tid}" data-email="{'1' if j['email'] else '0'}">
          <td>{checkbox}</td>
          <td><div class="title">{html.escape(j["title"])}</div>
              <div class="muted">{html.escape(j["company"])} · {html.escape(j["location"])}</div>
              {email_badge}</td>
          <td class="status">{'✅ готово' if j['has_resume'] else '<span class="muted">не создано</span>'}</td>
          <td>
            <button class="btn gen" onclick="gerar(this, '{tid}')">Создать резюме</button>
            <a class="btn ghost" href="{html.escape(j["link"], quote=True)}" target="_blank">Открыть вакансию</a>
            {resume_cell}
          </td>
        </tr>""")
    rows_html = "\n".join(rows) if rows else (
        '<tr><td colspan="4" class="muted">В jobs_found.csv нет вакансий. '
        'Сначала запусти <code>python main.py "desenvolvedor fullstack"</code>.</td></tr>')

    return (PAGE.replace("{{ROWS}}", rows_html)
                .replace("{{COUNT}}", str(len(jobs)))
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
  .btn{display:inline-block;font-size:13px;padding:7px 11px;border-radius:6px;border:1px solid #2f6f4f;background:#2f6f4f;color:#fff;cursor:pointer;text-decoration:none;margin:2px}
  .btn.ghost{background:#fff;color:#2f6f4f}
  .btn.small{background:#fff;color:#555;border-color:#ccc;padding:5px 9px}
  .btn:disabled{opacity:.5;cursor:default}
  .btn.primary{background:#b4622b;border-color:#b4622b}
  .warn{background:#fff4e5;border:1px solid #f0c36d;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px}
  .links{background:#eef2f4;border:1px solid #d5dde0;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px}
  .manual{background:#fff;border:1px solid #d5dde0;border-radius:8px;padding:8px 14px;font-size:13px;margin-bottom:12px}
  .manual summary{cursor:pointer;font-weight:600}
  .mform{display:flex;flex-direction:column;gap:8px;margin-top:10px;max-width:720px}
  .mform input,.mform textarea{font:inherit;padding:8px;border:1px solid #ccc;border-radius:6px}
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
    <button class="btn primary" onclick="enviar()">Отправить выбранные (e-mail)</button>
    <span class="muted" id="selinfo">0 выбрано</span>
    <span id="log"></span>
  </div>
  <table>
    <thead><tr><th></th><th>Вакансия</th><th>Резюме</th><th>Действия</th></tr></thead>
    <tbody>{{ROWS}}</tbody>
  </table>
<script>
function setLog(t){document.getElementById('log').textContent=t;}
function updSel(){
  const n=document.querySelectorAll('.sel:checked').length;
  document.getElementById('selinfo').textContent=n+' selecionadas';
}
document.addEventListener('change',e=>{if(e.target.classList.contains('sel'))updSel();});

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
        const rr=await fetch('/send_manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({folder:d.folder,email:d.email,title:d.title})});
        const dd=await rr.json();b.textContent=dd.ok?('✓ '+dd.msg):('Ошибка: '+dd.error);
      };
      out.appendChild(document.createTextNode(' '));out.appendChild(b);
    }
  }catch(e){out.textContent=' Ошибка сети: '+e;}
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
    setLog('Отправлено: '+ok+'/'+d.results.length+'. '+d.results.map(x=>x.msg).join(' | '));
  }catch(e){setLog('Ошибка сети: '+e);}
}
</script>
</body></html>"""


if __name__ == "__main__":
    print("Painel em http://127.0.0.1:5000  (Ctrl+C para parar)")
    app.run(host="127.0.0.1", port=5000, debug=False)
