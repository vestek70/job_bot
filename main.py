"""
Ponto de entrada: busca vagas e gera currículos adaptados.

Uso:
  python main.py "desenvolvedor fullstack junior"
  python main.py "desenvolvedor fullstack" --include-senior
  python main.py "desenvolvedor fullstack" --any-location
  python main.py "desenvolvedor fullstack" --force   # regera currículos já existentes

Depois, revise manualmente a pasta applications/ antes de se candidatar ou enviar
qualquer e-mail com send_application.py. Nada é enviado sozinho.
"""
import argparse
import sys

import config
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
    parser.add_argument("--any-location", action="store_true",
                        help=f"não descartar vagas presenciais fora de "
                             f"{config.HOME_CITY} (por padrão só ficam vagas em "
                             f"{config.HOME_CITY} ou remotas)")
    parser.add_argument("--force", action="store_true",
                        help="regerar resume.md mesmo para vagas já processadas "
                             "em execuções anteriores (útil depois de editar "
                             "base_resume.md ou o prompt)")
    args = parser.parse_args(sys.argv[1:])

    print("Buscando vagas na Adzuna...")
    jobs = search_jobs(
        args.keywords,
        filter_seniority=False if args.include_senior else None,
        filter_location=False if args.any_location else None,
    )
    save_jobs_csv(jobs)

    if not jobs:
        print("Nenhuma vaga encontrada. Tente outras palavras-chave.")
        return

    print(
        "Gerando currículos adaptados (usa a API da DeepSeek, pode levar "
        "alguns minutos)..."
    )
    tailor_resume.main(force=args.force)
    dashboard.main()


if __name__ == "__main__":
    main()
