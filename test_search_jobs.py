"""
Testes do merge de jobs_found.csv entre execuções (search_jobs.save_jobs_csv):
vaga nova entra, vaga já vista tem last_seen atualizado, vaga que sumiu da
busca é mantida por um tempo e só é descartada depois de
config.STALE_JOB_DROP_DAYS dias sem aparecer.
Rodar: python test_search_jobs.py
"""
import csv
import datetime
import os
import tempfile

import config
import search_jobs


def _job(jid, title="Dev", desc="desc"):
    return {"id": jid, "title": title, "company": "Acme", "location": "Remoto",
            "salary_min": "", "salary_max": "", "description": desc,
            "redirect_url": "", "created": ""}


def _write_raw_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=search_jobs.JOBS_FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_new_job_gets_first_and_last_seen_today():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "jobs.csv")
        today = datetime.date.today().isoformat()
        search_jobs.save_jobs_csv([_job("j1")], path=path)
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["first_seen"] == today
        assert rows[0]["last_seen"] == today


def test_returning_job_updates_content_keeps_first_seen():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "jobs.csv")
        search_jobs.save_jobs_csv([_job("j1", desc="v1")], path=path)
        with open(path, encoding="utf-8") as f:
            first_seen_before = list(csv.DictReader(f))[0]["first_seen"]
        search_jobs.save_jobs_csv([_job("j1", desc="v2")], path=path)
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["description"] == "v2"
        assert rows[0]["first_seen"] == first_seen_before


def test_job_missing_from_new_batch_is_kept_if_recent():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "jobs.csv")
        search_jobs.save_jobs_csv([_job("old1"), _job("new1")], path=path)
        # segunda busca só encontra new1 -> old1 não veio, mas é recente, deve ficar
        search_jobs.save_jobs_csv([_job("new1")], path=path)
        with open(path, encoding="utf-8") as f:
            ids = {r["id"] for r in csv.DictReader(f)}
        assert ids == {"old1", "new1"}


def test_job_stale_beyond_threshold_is_dropped():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "jobs.csv")
        old_date = (datetime.date.today() -
                    datetime.timedelta(days=50)).isoformat()
        row = {k: "" for k in search_jobs.JOBS_FIELDNAMES}
        row.update({"id": "veryold", "title": "Old job", "company": "X",
                    "first_seen": old_date, "last_seen": old_date})
        _write_raw_csv(path, [row])

        old_threshold = config.STALE_JOB_DROP_DAYS
        config.STALE_JOB_DROP_DAYS = 45
        try:
            search_jobs.save_jobs_csv([], path=path)
        finally:
            config.STALE_JOB_DROP_DAYS = old_threshold

        with open(path, encoding="utf-8") as f:
            ids = {r["id"] for r in csv.DictReader(f)}
        assert "veryold" not in ids


def test_job_within_threshold_is_not_dropped():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "jobs.csv")
        recent_date = (datetime.date.today() -
                       datetime.timedelta(days=10)).isoformat()
        row = {k: "" for k in search_jobs.JOBS_FIELDNAMES}
        row.update({"id": "recent1", "title": "Recent job", "company": "X",
                    "first_seen": recent_date, "last_seen": recent_date})
        _write_raw_csv(path, [row])

        old_threshold = config.STALE_JOB_DROP_DAYS
        config.STALE_JOB_DROP_DAYS = 45
        try:
            search_jobs.save_jobs_csv([], path=path)
        finally:
            config.STALE_JOB_DROP_DAYS = old_threshold

        with open(path, encoding="utf-8") as f:
            ids = {r["id"] for r in csv.DictReader(f)}
        assert "recent1" in ids


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passaram")
    return failed


if __name__ == "__main__":
    raise SystemExit(1 if _run() else 0)
