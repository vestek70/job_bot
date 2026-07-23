"""
Gera applications/dashboard.html: uma página local (abra no navegador) para
revisar cada vaga e currículo lado a lado antes de se candidatar.

Este script NÃO envia nada e NÃO abre navegador nem links sozinho — só gera
um arquivo HTML estático. Candidatar-se continua sendo uma ação manual sua:
o botão "Abrir vaga" apenas leva até a página da vaga para você se candidatar
lá (ou anexar o PDF, se for candidatura por e-mail).

Uso:
  python dashboard.py

Rode depois de tailor_resume.py (main.py já chama isso automaticamente).
"""
import csv
import html
import os
import re
import sys

import config


def _folder_name(pasta: str) -> str:
    """Extrai só o nome da subpasta a partir do valor salvo em index.csv,
    que pode vir com "\\" (Windows) ou "/" — nunca confiar no separador
    literal armazenado, sempre reconstruir o caminho a partir de
    config.OUTPUT_DIR."""
    parts = re.split(r"[\\/]+", (pasta or "").rstrip("/\\"))
    return parts[-1] if parts else pasta

CARD_TEMPLATE = """
    <article class="card">
      <div class="card-head">
        <h2>{vaga}</h2>
        <span class="status">{status}</span>
      </div>
      <p class="empresa">{empresa}{local_suffix}</p>
      <div class="actions">
        <a class="btn btn-primary" href="{link}" target="_blank" rel="noopener">
          Abrir vaga (candidatar-se manualmente)
        </a>
        {resume_link}
      </div>
      <p class="pasta">Pasta: <code>{pasta}</code></p>
    </article>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Job Bot — Painel de candidaturas</title>
<style>
  body {{
    font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    background: #f4f4f2; color: #222; margin: 0; padding: 24px;
  }}
  h1 {{ margin: 0 0 4px; }}
  .subtitle {{ color: #555; margin: 0 0 16px; }}
  .warning {{
    background: #fff4e5; border: 1px solid #f0c36d; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 24px; font-size: 14px;
  }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: #fff; border: 1px solid #ddd; border-radius: 10px;
    padding: 16px 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04);
  }}
  .card-head {{ display: flex; justify-content: space-between; align-items: start; gap: 8px; }}
  .card h2 {{ font-size: 17px; margin: 0 0 4px; }}
  .empresa {{ color: #444; margin: 0 0 12px; font-size: 14px; }}
  .status {{
    font-size: 11px; text-transform: uppercase; letter-spacing: .03em;
    background: #eee; color: #555; border-radius: 999px; padding: 3px 9px;
    white-space: nowrap;
  }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
  .btn {{
    display: inline-block; text-decoration: none; font-size: 13px;
    padding: 8px 12px; border-radius: 6px; border: 1px solid transparent;
  }}
  .btn-primary {{ background: #2f6f4f; color: #fff; }}
  .btn-secondary {{ background: #fff; color: #2f6f4f; border-color: #2f6f4f; }}
  .pasta {{ font-size: 11px; color: #999; margin: 0; }}
  .pasta code {{ font-size: 11px; }}
  .empty {{ color: #666; }}
  footer {{ margin-top: 28px; font-size: 12px; color: #888; }}
</style>
</head>
<body>
  <h1>Job Bot — Painel de candidaturas</h1>
  <p class="subtitle">Gerado a partir de applications/index.csv — {count} vaga(s)</p>
  <div class="warning">
    Revise cada currículo (PDF) antes de se candidatar. Nada aqui é enviado
    automaticamente — os botões só abrem links para você agir manualmente.
    Para marcar uma vaga como "candidatura enviada" ou "rejeitada", edite a
    coluna <code>status</code> em <code>applications/index.csv</code> (Excel
    ou bloco de notas) e rode <code>python dashboard.py</code> de novo.
  </div>
  <div class="grid">
    {cards}
  </div>
  <footer>job_bot — painel gerado localmente, sem envio automático.</footer>
</body>
</html>
"""


def _resume_link(pasta: str) -> str:
    """Link relativo (a partir de applications/dashboard.html) para o currículo
    da vaga: prefere o PDF, cai para o .md se o PDF não existir."""
    folder_name = _folder_name(pasta)
    base_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    pdf_path = os.path.join(base_dir, "resume.pdf")
    md_path = os.path.join(base_dir, "resume.md")
    if os.path.exists(pdf_path):
        return (
            f'<a class="btn btn-secondary" href="{folder_name}/resume.pdf" '
            f'target="_blank" rel="noopener">Ver currículo (PDF)</a>'
        )
    if os.path.exists(md_path):
        return (
            f'<a class="btn btn-secondary" href="{folder_name}/resume.md" '
            f'target="_blank" rel="noopener">Ver currículo (Markdown)</a>'
        )
    return '<span class="empty">Currículo não encontrado</span>'


def _read_local(pasta: str) -> str:
    """Lê o campo 'Local' de job_info.txt, se existir."""
    info_path = os.path.join(config.OUTPUT_DIR, _folder_name(pasta), "job_info.txt")
    if not os.path.exists(info_path):
        return ""
    try:
        with open(info_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("Local:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def load_index(path: str = None) -> list:
    path = path or os.path.join(config.OUTPUT_DIR, "index.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_dashboard(rows: list) -> str:
    cards = []
    for row in rows:
        pasta = row.get("pasta", "")
        local = _read_local(pasta)
        local_suffix = f" — {html.escape(local)}" if local else ""
        cards.append(
            CARD_TEMPLATE.format(
                vaga=html.escape(row.get("vaga", "")),
                status=html.escape(row.get("status", "")),
                empresa=html.escape(row.get("empresa", "")),
                local_suffix=local_suffix,
                link=html.escape(row.get("link_candidatura", "#"), quote=True),
                resume_link=_resume_link(pasta),
                pasta=html.escape(pasta),
            )
        )
    cards_html = "\n".join(cards) if cards else '<p class="empty">Nenhuma vaga em applications/index.csv ainda. Rode main.py primeiro.</p>'
    return PAGE_TEMPLATE.format(count=len(rows), cards=cards_html)


def main():
    rows = load_index()
    out_path = os.path.join(config.OUTPUT_DIR, "dashboard.html")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_dashboard(rows))
    print(f"Painel gerado: {out_path} (abra no navegador)")
    return out_path


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
