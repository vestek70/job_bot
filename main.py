"""
Ponto de entrada: busca vagas e gera currículos adaptados.

Uso:
  python main.py "desenvolvedor fullstack junior"

Depois, revise manualmente a pasta applications/ antes de se candidatar ou enviar
qualquer e-mail com send_application.py. Nada é enviado sozinho.
"""
import sys

import tailor_resume
from search_jobs import save_jobs_csv, search_jobs


def main():
    keywords = sys.argv[1] if len(sys.argv) > 1 else None
    print("Buscando vagas na Adzuna...")
    jobs = search_jobs(keywords)
    save_jobs_csv(jobs)

    if not jobs:
        print("Nenhuma vaga encontrada. Tente outras palavras-chave.")
        return

    print(
        "Gerando currículos adaptados (usa a API da Anthropic, pode levar "
        "alguns minutos)..."
    )
    tailor_resume.main()


if __name__ == "__main__":
    main()
