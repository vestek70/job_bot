"""
Testes das heurísticas puras. Rodar: python -m pytest test_filters.py
(ou simplesmente: python test_filters.py — tem um runner mínimo embutido).
"""
from filters import (
    filter_out_non_local,
    filter_out_senior,
    is_local_or_remote,
    is_too_senior,
)
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


def test_home_city_is_kept_even_if_onsite():
    job = {"title": "Dev Full Stack", "location": "Florianópolis, SC",
           "description": "Presencial, sem home office."}
    assert is_local_or_remote(job)


def test_home_city_alias_floripa_is_kept():
    job = {"title": "Dev Full Stack", "location": "Floripa - SC", "description": ""}
    assert is_local_or_remote(job)


def test_remote_job_elsewhere_is_kept():
    job = {"title": "Dev Full Stack", "location": "São Paulo, SP",
           "description": "Vaga 100% remota, pode morar em qualquer lugar do Brasil."}
    assert is_local_or_remote(job)


def test_remote_in_title_is_kept():
    job = {"title": "Desenvolvedor Full Stack (Remoto)", "location": "São Paulo, SP",
           "description": ""}
    assert is_local_or_remote(job)


def test_onsite_other_city_is_dropped():
    job = {"title": "Dev Full Stack", "location": "São Paulo, SP",
           "description": "Trabalho presencial no escritório."}
    assert not is_local_or_remote(job)


def test_ambiguous_location_without_remote_signal_is_dropped():
    # localização vaga tipo "Brasil", sem menção a remoto -> conservador, descarta
    job = {"title": "Dev Full Stack", "location": "Brasil", "description": ""}
    assert not is_local_or_remote(job)


def test_filter_out_non_local_splits_correctly():
    jobs = [
        {"title": "Dev A", "location": "Florianópolis, SC", "description": ""},
        {"title": "Dev B (Remoto)", "location": "Rio de Janeiro, RJ", "description": ""},
        {"title": "Dev C", "location": "São Paulo, SP", "description": "presencial"},
    ]
    kept, dropped = filter_out_non_local(jobs)
    assert {j["title"] for j in kept} == {"Dev A", "Dev B (Remoto)"}
    assert len(dropped) == 1 and dropped[0]["title"] == "Dev C"


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
