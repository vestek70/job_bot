"""
Testes de favorites_store.py (applications/favorites.csv — вакансии ★).
Rodar: python test_favorites_store.py
"""
import tempfile

import config
import favorites_store


def _with_tmp_output_dir(fn):
    old = config.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        try:
            fn()
        finally:
            config.OUTPUT_DIR = old


def test_set_and_check():
    def run():
        assert favorites_store.is_favorite("j1") is False
        favorites_store.set_favorite("j1", True, titulo="Dev", empresa="Acme")
        assert favorites_store.is_favorite("j1") is True
        row = favorites_store.load_all()["j1"]
        assert row["titulo"] == "Dev" and row["empresa"] == "Acme"
    _with_tmp_output_dir(run)


def test_unfavorite_removes():
    def run():
        favorites_store.set_favorite("j1", True)
        assert favorites_store.is_favorite("j1") is True
        favorites_store.set_favorite("j1", False)
        assert favorites_store.is_favorite("j1") is False
    _with_tmp_output_dir(run)


def test_multiple_persist():
    def run():
        favorites_store.set_favorite("j1", True)
        favorites_store.set_favorite("j2", True)
        assert set(favorites_store.load_all().keys()) == {"j1", "j2"}
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
