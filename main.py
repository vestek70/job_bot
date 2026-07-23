"""
Ponto de entrada: BUSCA vagas e salva em jobs_found.csv.

NÃO gera currículos automaticamente. A geração passou a ser sob demanda, pelo
painel (você escolhe as vagas que interessam):

  1. python main.py "desenvolvedor fullstack"     # busca e salva jobs_found.csv
  2. python app.py                                 # abre o painel local
  3. no navegador (http://127.0.0.1:5000): escolha as vagas, gere o currículo
     só nas que interessam e envie por e-mail as marcáveis.

Flags:
  --include-senior   não descartar vagas de nível sênior/lead/gestão
  --any-location     não descartar vagas fora de Florianópolis
  --tailor-all       (compat.) gerar currículo de TODAS as vagas encontradas,
                     como era antes — evite: gasta a API à toa. Prefira o painel.
  --force            com --tailor-all, regenera currículos já existentes
"""
import argparse
import sys

import config
from search_jobs import save_jobs_csv, search_jobs


def main():
    parser = argparse.ArgumentParser(
        description="Busca vagas (Adzuna + fontes extras) e salva jobs_found.csv. "
                    "Currículos são gerados sob demanda no painel (python app.py)."
    )
    parser.add_argument("keywords", nargs="?", default=None,
                        help="palavras-chave da busca")
    parser.add_argument("--include-senior", action="store_true",
                        help="não descartar vagas de nível sênior/lead/gestão")
    parser.add_argument("--any-location", action="store_true",
                        help=f"não descartar vagas presenciais fora de "
                             f"{config.HOME_CITY} (por padrão só ficam vagas em "
                             f"{config.HOME_CITY} ou remotas)")
    parser.add_argument("--tailor-all", action="store_true",
                        help="gerar currículo de TODAS as vagas (comportamento "
                             "antigo) — prefira o painel (python app.py)")
    parser.add_argument("--force", action="store_true",
                        help="com --tailor-all, regenera currículos já existentes")
    args = parser.parse_args(sys.argv[1:])

    print("Buscando vagas (Adzuna + 6 fontes extras: Remotive, Arbeitnow, "
          "RemoteOK, Jobicy, The Muse, Jooble)...")
    jobs = search_jobs(
        args.keywords,
        filter_seniority=False if args.include_senior else None,
        filter_location=False if args.any_location else None,
    )
    save_jobs_csv(jobs)

    if not jobs:
        print("Nenhuma vaga encontrada. Tente outras palavras-chave.")
        return

    if args.tailor_all:
        # Compatibilidade: gera tudo (gasta a API). Prefira o painel.
        import tailor_resume
        print("Gerando currículos de TODAS as vagas (--tailor-all)...")
        tailor_resume.main(force=args.force)
        return

    print(
        f"\nPronto: {len(jobs)} vaga(s) em jobs_found.csv.\n"
        "Agora rode o painel para escolher e gerar currículos só nas que "
        "interessam:\n"
        "    python app.py\n"
        "e abra http://127.0.0.1:5000 no navegador."
    )


if __name__ == "__main__":
    main()
