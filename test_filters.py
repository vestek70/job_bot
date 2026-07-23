"""
Testes das heurísticas puras. Rodar: python -m pytest test_filters.py
(ou simplesmente: python test_filters.py — tem um runner mínimo embutido).
"""
from filters import (
    filter_out_irrelevant,
    filter_out_non_local,
    filter_out_senior,
    is_dev_relevant,
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


def test_is_dev_relevant_keeps_real_dev_jobs():
    for t in ["Desenvolvedor Fullstack", "Backend Developer Python",
              "Desenvolvedor(a) Java/React Remoto", "Software Engineer",
              "Engenheiro de Software", "Analista de Sistemas",
              "Programadora PHP", ".NET Developer", "Desenvolvedor Android",
              "Ruby on Rails Pleno"]:
        assert is_dev_relevant(t), t


def test_is_dev_relevant_keeps_adjacent_roles():
    # roles adjacentes habilitadas ao afrouxar filtros (QA, dados)
    for t in ["QA Analyst", "Quality Assurance Engineer", "Analista de Dados",
              "Data Engineer", "Cientista de Dados", "Tester Pleno"]:
        assert is_dev_relevant(t), t


def test_is_dev_relevant_drops_non_dev():
    # inclui a regressão do bug ".net" que casava "internet"
    for t in ["Técnico em Telecomunicações Internet", "Estágio em Nutrição 30h",
              "Técnico de Campo Chapecó", "Recepcionista", "Marketing Associate",
              "Analista de Comércio Exterior", "Mortgage Loan Processor",
              "Human Resources Generalist", "Office Admin",
              "Analista de Suporte em Infraestrutura de TI"]:
        assert not is_dev_relevant(t), t


def test_filter_out_irrelevant_splits():
    jobs = [
        {"title": "Desenvolvedor Fullstack"},
        {"title": "Estágio em Nutrição"},
        {"title": "Backend Developer"},
        {"title": "Técnico de Telecomunicações Internet"},
    ]
    kept, dropped = filter_out_irrelevant(jobs)
    assert {j["title"] for j in kept} == {"Desenvolvedor Fullstack", "Backend Developer"}
    assert len(dropped) == 2


def test_hybrid_other_city_is_dropped():
    # híbrido em SP/RJ = precisa ir ao escritório em outra cidade -> descarta
    j1 = {"id": "1", "title": "Fullstack", "location": "São Paulo, SP",
          "description": "atuacao hibrida, 2 dias remotos e 3 presenciais"}
    j2 = {"id": "2", "title": "Python Full Stack",
          "location": "Rio de Janeiro", "description": "hibrido (3x presencial / 2x remoto)"}
    assert not is_local_or_remote(j1)
    assert not is_local_or_remote(j2)


def test_hybrid_in_home_city_is_kept():
    # híbrido EM Florianópolis é ok (o candidato mora lá)
    j = {"id": "3", "title": "Dev", "location": "Florianópolis, SC",
         "description": "modelo hibrido, 3x presencial"}
    assert is_local_or_remote(j)


def test_pure_remote_brazil_is_kept():
    j = {"id": "4", "title": "Dev", "location": "Brasil",
         "description": "100% remoto, clt"}
    assert is_local_or_remote(j)


def test_intl_remote_foreign_country_is_dropped():
    # fontes internacionais presas a outro país -> descartadas
    for loc in ["Remoto (Berlin)", "Remoto (Markt Indersdorf)",
                "Remoto (Ciudad de México, México)",
                "Bangalore, India, Flexible / Remote"]:
        job = {"id": "arbeitnow-x", "title": "Developer", "location": loc,
               "description": ""}
        assert not is_local_or_remote(job), loc


def test_intl_remote_global_is_kept():
    for loc in ["Flexible / Remote", "Remoto (Worldwide)", "Remoto (Anywhere)",
                "Remoto (Brazil)", "Remoto (Latin America)"]:
        job = {"id": "themuse-1", "title": "Developer", "location": loc,
               "description": ""}
        assert is_local_or_remote(job), loc


def test_adzuna_brazilian_remote_is_kept_even_without_brasil_literal():
    # Adzuna (id numérico) é BR por construção — SP remoto deve ficar
    job = {"id": "5730218698", "title": "Dev Remoto",
           "location": "São Paulo, Estado de São Paulo", "description": ""}
    assert is_local_or_remote(job)


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
