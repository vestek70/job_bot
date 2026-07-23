"""
Ponto de entrada: busca vagas e gera currículos adaptados.

Uso:
  python main.py "desenvolvedor fullstack junior"
  python main.py "desenvolvedor fullstack" --include-senior

Depois, revise manualmente a pasta applications/ antes de se candidatar ou enviar
qualquer e-mail com send_application.py. Nada é enviado sozinho.
"""
import argparse
import sys

import dashboard
import tailor_resume
from search_jobs import save_jobs_csv, search_jobs


def main():
    parser = argparse.ArgumentParser(
        description="Busca vagas (Adzuna) e gera currículos adaptados (DeepSeek)."
    )
    parser.add_argument("keywords", nargs="?", default=None,
                        help="palavras-chave da busca")
    parser.add_argument("--include-senior", action="store_true",
                        help="não descartar vagas de nível sênior/lead/gestão")
    args = parser.parse_args(sys.argv[1:])

    print("Buscando vagas na Adzuna...")
    jobs = search_jobs(
        args.keywords,
        filter_seniority=False if args.include_senior else None,
    )
    save_jobs_csv(jobs)

    if not jobs:
        print("Nenhuma vaga encontrada. Tente outras palavras-chave.")
        return

    print(
        "Gerando currículos adaptados (usa a API da DeepSeek, pode levar "
        "alguns minutos)..."
    )
    tailor_resume.main()
    dashboard.main()


if __name__ == "__main__":
    main()
