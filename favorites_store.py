"""
Guarda as vagas marcadas como favoritas (★) em applications/favorites.csv.
Independente do status de candidatura (status_store) e do jobs_found.csv —
uma vaga pode ser favorita e continuar ativa. Persistente: sobrevive a novas
buscas e reinícios do painel.

Colunas: id, titulo, empresa, data
"""
import csv
import datetime
import os

import config

_FIELDNAMES = ["id", "titulo", "empresa", "data"]


def _path() -> str:
    return os.path.join(config.OUTPUT_DIR, "favorites.csv")


def load_all() -> dict:
    """Retorna {job_id: row_dict} das vagas favoritas."""
    path = _path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("id"):
                        data[row["id"]] = row
        except (OSError, csv.Error):
            pass
    return data


def is_favorite(job_id: str) -> bool:
    return job_id in load_all()


def _save(data: dict) -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(_path(), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for row in data.values():
            writer.writerow(row)


def set_favorite(job_id: str, favorite: bool = True,
                 titulo: str = "", empresa: str = "") -> None:
    """Marca (favorite=True) ou desmarca (favorite=False) a vaga."""
    data = load_all()
    if favorite:
        data[job_id] = {
            "id": job_id,
            "titulo": titulo,
            "empresa": empresa,
            "data": datetime.date.today().isoformat(),
        }
    else:
        data.pop(job_id, None)
    _save(data)
