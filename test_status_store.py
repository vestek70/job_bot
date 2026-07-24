"""
Testes de status_store.py (applications/status.csv — "já me candidatei a
essa vaga?"). Rodar: python test_status_store.py
"""
import datetime
import os
import tempfile

import config
import status_store


def _with_tmp_output_dir(fn):
    old = config.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        try:
            fn()
        finally:
            config.OUTPUT_DIR = old


def test_set_and_get():
    def run():
        status_store.set_status("j1", titulo="Dev", empresa="Acme",
                                 status="enviado", canal="email", contato="a@b.com")
        row = status_store.get("j1")
        assert row["status"] == "enviado"
        assert row["canal"] == "email"
        assert row["contato"] == "a@b.com"
        assert row["data"] == datetime.date.today().isoformat()
    _with_tmp_output_dir(run)


def test_get_unknown_returns_empty():
    def run():
        assert status_store.get("nao-existe") == {}
    _with_tmp_output_dir(run)


def test_clear_status_removes_entry():
    def run():
        status_store.set_status("j1", status="candidatei manualmente", canal="manual")
        assert status_store.get("j1")["status"] == "candidatei manualmente"
        status_store.set_status("j1", status="")
        assert status_store.get("j1") == {}
    _with_tmp_output_dir(run)


def test_multiple_entries_persist():
    def run():
        status_store.set_status("j1", status="enviado", canal="email")
        status_store.set_status("j2", status="candidatei manualmente", canal="manual")
        data = status_store.load_all()
        assert set(data.keys()) == {"j1", "j2"}
    _with_tmp_output_dir(run)


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
