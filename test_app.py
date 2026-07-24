"""
Testes do fluxo do painel: extração de e-mail, helpers de envio e as rotas
Flask (via test_client, sem subir servidor nem chamar rede/DeepSeek).
Rodar: python test_app.py
"""
import os
import tempfile

import config
import status_store
import tailor_resume
import send_application


def test_extract_email():
    assert tailor_resume.extract_email(
        "candidate-se pelo email vaga-364733@vagas.abler.in agora"
    ) == "vaga-364733@vagas.abler.in"
    assert tailor_resume.extract_email("sem email aqui") == ""
    assert tailor_resume.extract_email("", "rh@empresa.com.br") == "rh@empresa.com.br"
    # não confunde texto tipo "3x2" com email
    assert tailor_resume.extract_email("2 dias remotos e 3 presenciais") == ""


def test_folder_for_deterministico():
    job = {"company": "Acme X Ltda.", "title": "Dev Fullstack (Remoto)", "id": "999"}
    p1 = tailor_resume.folder_for(job)
    p2 = tailor_resume.folder_for(job)
    assert p1 == p2
    assert p1.endswith("acme-x-ltda_dev-fullstack-remoto_999")


def test_resume_attachment_prefers_pdf():
    with tempfile.TemporaryDirectory() as d:
        # só .md existe
        open(os.path.join(d, "resume.md"), "w").close()
        assert send_application.resume_attachment(d).endswith("resume.md")
        # com .pdf, prefere pdf
        open(os.path.join(d, "resume.pdf"), "w").close()
        assert send_application.resume_attachment(d).endswith("resume.pdf")


def test_subject_and_body_tem_nome_completo():
    subject, body = send_application.subject_and_body("Desenvolvedor Backend")
    assert "Desenvolvedor Backend" in subject
    assert "Konstantin Borisov" in body


def test_send_email_sem_credenciais_levanta():
    import config
    ga, gp = config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD
    config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD = "", ""
    try:
        raised = False
        try:
            send_application.send_email("x@y.com", "s", "b", "/tmp/none.pdf")
        except send_application.SendError:
            raised = True
        assert raised, "deveria levantar SendError sem credenciais"
    finally:
        config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD = ga, gp


def test_build_search_links():
    import app as flask_app
    links = flask_app.build_search_links("desenvolvedor fullstack", "Florianópolis")
    names = [l["name"] for l in links]
    assert any("Vagas.com" in n for n in names)
    assert any("Gupy" == n for n in names)
    assert any("Catho" == n for n in names)
    assert any("InfoJobs" == n for n in names)
    by = {l["name"]: l["url"] for l in links}
    # slug sem acento e com hífen
    assert "vagas-de-desenvolvedor-fullstack" in by["Vagas.com"]
    # acento de Florianópolis normalizado no slug do link local
    floripa = next(u for n, u in by.items() if "Vagas.com (" in n)
    assert "florianopolis" in floripa and "ó" not in floripa
    # LinkedIn com keyword url-encoded
    assert "keywords=desenvolvedor%20fullstack" in by["LinkedIn"]


def test_flask_routes():
    import app as flask_app
    c = flask_app.app.test_client()
    # home renderiza
    r = c.get("/")
    assert r.status_code == 200 and b"Job Bot" in r.data
    # send vazio devolve lista vazia
    r = c.post("/send", json={"ids": []})
    assert r.status_code == 200 and r.get_json() == {"results": []}
    # send de vaga com id inexistente -> erro tratado, não 500
    r = c.post("/send", json={"ids": ["id-que-nao-existe"]})
    data = r.get_json()
    assert data["results"][0]["ok"] is False
    # tailor de id inexistente -> 404 tratado
    r = c.post("/tailor", json={"id": "id-que-nao-existe"})
    assert r.status_code == 404


def test_manual_routes_validation():
    import app as flask_app
    c = flask_app.app.test_client()
    # tailor_manual sem título/texto -> 400 tratado
    r = c.post("/tailor_manual", json={"title": "", "description": ""})
    assert r.status_code == 400 and r.get_json()["ok"] is False
    # send_manual sem dados -> 400
    r = c.post("/send_manual", json={})
    assert r.status_code == 400 and r.get_json()["ok"] is False
    # send_manual com pasta sem currículo -> 400 (gere antes)
    r = c.post("/send_manual",
               json={"folder": "pasta-inexistente", "email": "x@y.com", "title": "t"})
    assert r.status_code == 400
    # o formulário manual aparece na home (rótulo agora em russo)
    assert "Вставить вакансию вручную".encode("utf-8") in c.get("/").data


def test_mark_applied_route():
    import app as flask_app
    old_dir = config.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        try:
            c = flask_app.app.test_client()
            # marcar
            r = c.post("/mark_applied",
                       json={"id": "vaga-x", "title": "Dev", "company": "Acme", "applied": True})
            assert r.status_code == 200 and r.get_json()["ok"] is True
            assert status_store.get("vaga-x")["status"] == "candidatei manualmente"
            # desmarcar
            r = c.post("/mark_applied", json={"id": "vaga-x", "applied": False})
            assert r.status_code == 200 and r.get_json()["ok"] is True
            assert status_store.get("vaga-x") == {}
            # sem id -> 400
            r = c.post("/mark_applied", json={})
            assert r.status_code == 400
        finally:
            config.OUTPUT_DIR = old_dir


def test_job_view_reflete_status_de_candidatura():
    import app as flask_app
    old_dir = config.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        try:
            status_store.set_status("vaga-y", titulo="Dev", empresa="Acme",
                                     status="enviado", canal="email", contato="a@b.com")
            job = {"id": "vaga-y", "title": "Dev", "company": "Acme",
                   "location": "Remoto", "description": "", "redirect_url": ""}
            view = flask_app.job_view(job)
            assert view["applied_status"] == "enviado"
            assert view["applied_canal"] == "email"
        finally:
            config.OUTPUT_DIR = old_dir


def test_search_route_usa_busca_mockada():
    import app as flask_app
    # substitui a busca real (rede) por um mock, para testar só a rota
    orig_search = flask_app.search_jobs_mod.search_jobs
    orig_save = flask_app.search_jobs_mod.save_jobs_csv
    calls = {}

    def fake_search(keywords, filter_seniority=None, filter_location=None):
        calls["keywords"] = keywords
        calls["filter_seniority"] = filter_seniority
        calls["filter_location"] = filter_location
        return [{"id": "1"}, {"id": "2"}]

    def fake_save(jobs, path=None):
        return jobs  # já "mesclado"

    flask_app.search_jobs_mod.search_jobs = fake_search
    flask_app.search_jobs_mod.save_jobs_csv = fake_save
    try:
        c = flask_app.app.test_client()
        r = c.post("/search", json={"keywords": "python dev",
                                    "include_senior": True, "any_location": False})
        d = r.get_json()
        assert r.status_code == 200 and d["ok"] is True
        assert d["found"] == 2 and d["total"] == 2
        assert calls["keywords"] == "python dev"
        # include_senior=True -> filter_seniority=False
        assert calls["filter_seniority"] is False
        # any_location=False -> filter_location=None (usa padrão)
        assert calls["filter_location"] is None
    finally:
        flask_app.search_jobs_mod.search_jobs = orig_search
        flask_app.search_jobs_mod.save_jobs_csv = orig_save


def test_home_tem_controles_de_busca():
    import app as flask_app
    data = flask_app.app.test_client().get("/").data
    assert "Запустить поиск".encode("utf-8") in data
    assert "Обновить".encode("utf-8") in data


def test_delete_route_esconde_vaga():
    import app as flask_app
    old_dir = config.OUTPUT_DIR
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        try:
            c = flask_app.app.test_client()
            r = c.post("/delete", json={"id": "vaga-del", "title": "Dev", "company": "Acme"})
            assert r.status_code == 200 and r.get_json()["ok"] is True
            assert status_store.get("vaga-del")["status"] == "removido"
            # sem id -> 400
            r = c.post("/delete", json={})
            assert r.status_code == 400
        finally:
            config.OUTPUT_DIR = old_dir


def test_index_separa_ativas_arquivadas_e_esconde_removidas():
    import csv as _csv
    import app as flask_app
    old_dir, old_csv = config.OUTPUT_DIR, config.JOBS_CSV
    with tempfile.TemporaryDirectory() as d:
        config.OUTPUT_DIR = d
        jobs_csv = os.path.join(d, "jobs.csv")
        config.JOBS_CSV = jobs_csv
        try:
            # 3 vagas no CSV
            with open(jobs_csv, "w", newline="", encoding="utf-8") as f:
                w = _csv.DictWriter(f, fieldnames=["id", "title", "company", "location",
                                                   "salary_min", "salary_max", "description",
                                                   "redirect_url", "created", "first_seen", "last_seen"])
                w.writeheader()
                for i in ("ativa", "arquiv", "removi"):
                    w.writerow({"id": i, "title": "Dev " + i, "company": "Acme",
                                "location": "Remoto", "description": "", "redirect_url": "",
                                "first_seen": "2026-07-20", "last_seen": "2026-07-20"})
            status_store.set_status("arquiv", status="candidatei manualmente", canal="manual")
            status_store.set_status("removi", status="removido", canal="deleted")

            html = flask_app.app.test_client().get("/").data.decode("utf-8")
            # ativa aparece no corpo; removida não aparece de jeito nenhum
            assert "Dev ativa" in html
            assert "Dev removi" not in html
            # arquivada aparece (dentro do bloco Архив)
            assert "Dev arquiv" in html
            assert "Архив".encode("utf-8").decode("utf-8") in html
        finally:
            config.OUTPUT_DIR, config.JOBS_CSV = old_dir, old_csv


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
