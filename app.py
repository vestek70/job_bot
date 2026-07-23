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


# ---------------------------------------------------------------- rotas -------

@app.route("/")
def index():
    jobs = [job_view(j) for j in load_jobs()]
    return render_page(jobs)


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

def render_page(jobs: list) -> str:
    rows = []
    for j in jobs:
        tid = html.escape(j["id"], quote=True)
        email_badge = (f'<span class="badge email">✉ {html.escape(j["email"])}</span>'
                       if j["email"] else '<span class="badge link">só link</span>')
        resume_cell = (
            f'<a class="btn small" href="/pdf/{html.escape(j["folder"], quote=True)}" '
            f'target="_blank">Ver PDF</a>' if j["has_resume"]
            else '<span class="muted">—</span>')
        checkbox = (f'<input type="checkbox" class="sel" value="{tid}">'
                    if j["email"] else '')
        rows.append(f"""
        <tr data-id="{tid}" data-email="{'1' if j['email'] else '0'}">
          <td>{checkbox}</td>
          <td><div class="title">{html.escape(j["title"])}</div>
              <div class="muted">{html.escape(j["company"])} · {html.escape(j["location"])}</div>
              {email_badge}</td>
          <td class="status">{'✅ pronto' if j['has_resume'] else '<span class="muted">não gerado</span>'}</td>
          <td>
            <button class="btn gen" onclick="gerar(this, '{tid}')">Gerar currículo</button>
            <a class="btn ghost" href="{html.escape(j["link"], quote=True)}" target="_blank">Abrir vaga</a>
            {resume_cell}
          </td>
        </tr>""")
    rows_html = "\n".join(rows) if rows else (
        '<tr><td colspan="4" class="muted">Nenhuma vaga em jobs_found.csv. '
        'Rode <code>python main.py "desenvolvedor fullstack"</code> primeiro.</td></tr>')

    return PAGE.replace("{{ROWS}}", rows_html).replace("{{COUNT}}", str(len(jobs)))


PAGE = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>Job Bot — painel</title>
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
  #log{font-size:13px;margin-left:auto;color:#444}
</style></head><body>
  <h1>Job Bot — painel</h1>
  <p class="sub">{{COUNT}} vaga(s) em jobs_found.csv. Gere o currículo só nas que interessam; envie por e-mail as marcáveis.</p>
  <div class="warn">Só é possível enviar automaticamente vagas com <b>e-mail de contato</b> (checkbox disponível). Vagas de plataforma: use <b>Abrir vaga</b> e candidate-se no site. Nada é enviado sem sua confirmação.</div>
  <div class="bar">
    <button class="btn primary" onclick="enviar()">Enviar selecionados (e-mail)</button>
    <span class="muted" id="selinfo">0 selecionadas</span>
    <span id="log"></span>
  </div>
  <table>
    <thead><tr><th></th><th>Vaga</th><th>Currículo</th><th>Ações</th></tr></thead>
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
  btn.disabled=true;const old=btn.textContent;btn.textContent='Gerando…';setLog('Gerando currículo…');
  try{
    const r=await fetch('/tailor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    const d=await r.json();
    if(d.ok){btn.textContent='Gerado ✓';const cell=btn.closest('tr').querySelector('.status');cell.innerHTML='✅ pronto';
      const a=document.createElement('a');a.className='btn small';a.target='_blank';a.href='/pdf/'+d.folder;a.textContent='Ver PDF';btn.parentNode.appendChild(a);
      setLog('Currículo gerado.');}
    else{btn.disabled=false;btn.textContent=old;setLog('Erro: '+d.error);}
  }catch(e){btn.disabled=false;btn.textContent=old;setLog('Erro de rede: '+e);}
}

async function enviar(){
  const ids=[...document.querySelectorAll('.sel:checked')].map(c=>c.value);
  if(!ids.length){alert('Marque ao menos uma vaga com e-mail de contato.');return;}
  if(!confirm('Enviar seu currículo por e-mail para '+ids.length+' vaga(s)? Isso envia de verdade.'))return;
  setLog('Enviando…');
  try{
    const r=await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})});
    const d=await r.json();
    const ok=d.results.filter(x=>x.ok).length;
    setLog('Enviadas: '+ok+'/'+d.results.length+'. '+d.results.map(x=>x.msg).join(' | '));
  }catch(e){setLog('Erro de rede: '+e);}
}
</script>
</body></html>"""


if __name__ == "__main__":
    print("Painel em http://127.0.0.1:5000  (Ctrl+C para parar)")
    app.run(host="127.0.0.1", port=5000, debug=False)
