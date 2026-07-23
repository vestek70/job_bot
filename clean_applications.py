"""
Limpa applications/: remove pastas de currículos antigas (vaga provavelmente
já não está mais ativa). Critério: idade = data de modificação mais recente
dentro da pasta (resume.pdf/resume.md/job_info.txt), não a data de criação —
assim uma pasta que você reabriu/re-gerou recentemente não é apagada.

Por segurança, NUNCA apaga nada sem confirmação:
  - por padrão roda em modo "dry-run" (só mostra o que apagaria)
  - passe --apply para apagar de verdade

Uso:
  python clean_applications.py                  # lista o que seria apagado (30 dias)
  python clean_applications.py --days 45         # outro limite de idade
  python clean_applications.py --apply           # apaga de verdade (pede confirmação)
  python clean_applications.py --days 45 --apply --yes   # apaga sem perguntar (cuidado)
"""
import argparse
import os
import shutil
import sys
import time

import config

DEFAULT_DAYS = 30


def _folder_age_days(folder_path: str) -> float:
    """Idade em dias baseada no arquivo mais recentemente modificado na pasta
    (cobre resume.pdf/resume.md/job_info.txt/index de status)."""
    newest = 0.0
    for name in os.listdir(folder_path):
        fpath = os.path.join(folder_path, name)
        if os.path.isfile(fpath):
            newest = max(newest, os.path.getmtime(fpath))
    if newest == 0.0:
        newest = os.path.getmtime(folder_path)
    return (time.time() - newest) / 86400


def find_stale_folders(output_dir: str, days: int) -> list:
    if not os.path.isdir(output_dir):
        return []
    stale = []
    for name in sorted(os.listdir(output_dir)):
        folder_path = os.path.join(output_dir, name)
        if not os.path.isdir(folder_path):
            continue  # ignora index.csv e afins
        age = _folder_age_days(folder_path)
        if age >= days:
            stale.append((folder_path, age))
    return stale


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--days", type=int, default=DEFAULT_DAYS,
                   help=f"apagar pastas com mais de N dias sem atividade (padrão: {DEFAULT_DAYS})")
    p.add_argument("--apply", action="store_true",
                   help="apaga de verdade (sem isso, só mostra o que seria apagado)")
    p.add_argument("--yes", action="store_true",
                   help="não pedir confirmação antes de apagar (use com --apply)")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    stale = find_stale_folders(config.OUTPUT_DIR, args.days)
    if not stale:
        print(f"Nenhuma pasta em {config.OUTPUT_DIR}/ com mais de {args.days} dia(s) sem atividade.")
        return

    print(f"{len(stale)} pasta(s) em {config.OUTPUT_DIR}/ com mais de {args.days} dia(s) sem atividade:")
    for folder_path, age in stale:
        print(f"  - {os.path.basename(folder_path)}  ({age:.0f} dias)")

    if not args.apply:
        print("\nModo de simulação (nada foi apagado). Rode com --apply para apagar de verdade.")
        return

    if not args.yes:
        resp = input(f"\nApagar essa(s) {len(stale)} pasta(s) de verdade? [s/N] ").strip().lower()
        if resp not in ("s", "sim", "y", "yes"):
            print("Cancelado, nada foi apagado.")
            return

    removed = 0
    for folder_path, _age in stale:
        try:
            shutil.rmtree(folder_path)
            removed += 1
        except OSError as e:
            print(f"  AVISO: não consegui apagar {folder_path}: {e}", file=sys.stderr)
    print(f"Apagadas {removed}/{len(stale)} pasta(s).")


if __name__ == "__main__":
    main()
