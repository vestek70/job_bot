"""
Testes das heurísticas puras. Rodar: python -m pytest test_filters.py
(ou simplesmente: python test_filters.py — tem um runner mínimo embutido).
"""
from filters import is_too_senior, filter_out_senior
from tailor_resume import slugify


def test_senior_titles_are_dropped():
    assert is_too_senior("Desenvolvedor Full Stack Sênior")
    assert is_too_senior("Senior Software Engineer")
    assert is_too_senior("Tech Lead Full Stack")
    assert is_too_senior("Especialista em Backend")
    assert is_too_senior("Arquiteto de Software")
    assert is_too_senior("Engineering Manager")


def test_junior_pleno_titles_are_kept():
    assert not is_too_senior("Desenvolvedor Full Stack Júnior")
    assert not is_too_senior("Desenvolvedor Pleno")
    assert not is_too_senior("Programador Junior React")
    assert not is_too_senior("Estágio em Desenvolvimento Web")


def test_pleno_senior_hybrid_is_kept():
    # vaga aberta a pleno também -> não descartar
    assert not is_too_senior("Desenvolvedor Pleno/Sênior")


def test_neutral_title_uses_years_in_description():
    assert is_too_senior("Desenvolvedor Full Stack", "Exigimos 7 anos de experiência.")
    assert not is_too_senior("Desenvolvedor Full Stack", "1 a 2 anos de experiência.")
    assert not is_too_senior("Desenvolvedor Full Stack", "Sem descrição relevante.")


def test_filter_out_senior_splits_correctly():
    jobs = [
        {"title": "Dev Júnior", "description": ""},
        {"title": "Dev Sênior", "description": ""},
        {"title": "Dev Full Stack", "description": "8 anos de experiência"},
    ]
    kept, dropped = filter_out_senior(jobs)
    assert len(kept) == 1 and kept[0]["title"] == "Dev Júnior"
    assert len(dropped) == 2


def test_slugify():
    assert slugify("Empresa X Ltda.") == "empresa-x-ltda"
    assert slugify("Dev Full-Stack (Remoto)") == "dev-full-stack-remoto"
    assert slugify("") == "vaga"


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
