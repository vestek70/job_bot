"""
Guarda o status de candidatura por vaga (id) em applications/status.csv, para
o painel mostrar "já respondi a essa" e você não perder o controle de onde já
se candidatou. Independente do jobs_found.csv (que pode ser mesclado/podado)
e independente da pasta de currículo (id, não pasta, é a chave — assim o
status sobrevive mesmo se o currículo for regenerado).

Colunas: id, titulo, empresa, status, canal, contato, data
  status: "enviado" | "candidatei manualmente" | "" (vazio = nada registrado)
  canal:  "email" | "manual"
"""
import csv
import datetime
import os

import config

_FIELDNAMES = ["id", "titulo", "empresa", "status", "canal", "contato", "data"]


def _path() -> str:
    return os.path.join(config.OUTPUT_DIR, "status.csv")


def load_all() -> dict:
    """Retorna {job_id: row_dict} com tudo que já foi registrado."""
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


def get(job_id: str) -> dict:
    return load_all().get(job_id, {})


def set_status(job_id: str, titulo: str = "", empresa: str = "",
               status: str = "", canal: str = "", contato: str = "") -> None:
    """Grava/atualiza o status de uma vaga. status="" remove o registro
    (usado para "desmarcar" uma candidatura marcada manualmente por engano)."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    data = load_all()
    if not status:
        data.pop(job_id, None)
    else:
        data[job_id] = {
            "id": job_id,
            "titulo": titulo,
            "empresa": empresa,
            "status": status,
            "canal": canal,
            "contato": contato,
            "data": datetime.date.today().isoformat(),
        }
    with open(_path(), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for row in data.values():
            writer.writerow(row)
