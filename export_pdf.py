"""
Exporta currículos Markdown (applications/<pasta>/resume.md) para PDF.

A maioria dos formulários de candidatura exige PDF (não Markdown). O PDF gerado tem
TEXTO REAL selecionável (não imagem), então parsers de ATS conseguem lê-lo.

Uso:
  python export_pdf.py                     # converte TODOS os applications/*/resume.md
  python export_pdf.py caminho/resume.md   # converte um arquivo específico
  python export_pdf.py applications/pasta   # converte o resume.md dentro da pasta

Dependências (já em requirements.txt): markdown, xhtml2pdf.
"""
import glob
import os
import sys

import config

# CSS simples e ATS-friendly: fonte serifada legível, A4, margens de 2cm, sem cores
# chamativas, títulos padrão. Nada de tabelas/ícones (o próprio prompt já evita isso).
_CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: "Helvetica", "Arial", sans-serif; font-size: 10.5pt;
       line-height: 1.35; color: #111; }
h1 { font-size: 18pt; margin: 0 0 2px 0; }
h2 { font-size: 12.5pt; margin: 14px 0 4px 0; border-bottom: 1px solid #999;
     padding-bottom: 2px; }
h3 { font-size: 11pt; margin: 10px 0 2px 0; }
p  { margin: 3px 0; }
ul { margin: 3px 0 6px 0; padding-left: 18px; }
li { margin: 1px 0; }
a  { color: #111; text-decoration: none; }
"""


def _require_libs():
    try:
        import markdown  # noqa: F401
        from xhtml2pdf import pisa  # noqa: F401
    except ImportError:
        print(
            "ERRO: faltam bibliotecas para gerar PDF. Instale com:\n"
            "  pip install markdown xhtml2pdf\n"
            "(já estão no requirements.txt: pip install -r requirements.txt)",
            file=sys.stderr,
        )
        raise


def md_to_pdf(md_text: str, out_path: str) -> str:
    """Converte texto Markdown em PDF salvo em out_path. Retorna out_path."""
    _require_libs()
    import markdown
    from xhtml2pdf import pisa

    body = markdown.markdown(md_text, extensions=["extra", "sane_lists"])
    html = f"<html><head><meta charset='utf-8'><style>{_CSS}</style></head>" \
           f"<body>{body}</body></html>"
    with open(out_path, "wb") as f:
        result = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"Falha ao gerar PDF: {out_path}")
    return out_path


def convert_file(md_path: str) -> str:
    """Converte um resume.md em resume.pdf na mesma pasta."""
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()
    out_path = os.path.splitext(md_path)[0] + ".pdf"
    md_to_pdf(md_text, out_path)
    print(f"PDF gerado: {out_path}")
    return out_path


def convert_all(base_dir: str = None) -> int:
    """Converte todos os applications/*/resume.md. Retorna quantos foram gerados."""
    base_dir = base_dir or config.OUTPUT_DIR
    md_files = sorted(glob.glob(os.path.join(base_dir, "*", "resume.md")))
    if not md_files:
        print(f"Nenhum resume.md encontrado em '{base_dir}/'.")
        return 0
    count = 0
    for md_path in md_files:
        try:
            convert_file(md_path)
            count += 1
        except Exception as e:  # não abortar o lote por causa de um arquivo
            print(f"AVISO: não consegui converter {md_path}: {e}", file=sys.stderr)
    print(f"\n{count} PDF(s) gerado(s).")
    return count


def _resolve_arg(arg: str) -> str:
    """Aceita tanto o .md quanto a pasta que o contém."""
    if os.path.isdir(arg):
        return os.path.join(arg, "resume.md")
    return arg


if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_file(_resolve_arg(sys.argv[1]))
    else:
        convert_all()
