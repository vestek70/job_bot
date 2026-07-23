"""
Testes do fluxo do painel: extração de e-mail, helpers de envio e as rotas
Flask (via test_client, sem subir servidor nem chamar rede/DeepSeek).
Rodar: python test_app.py
"""
import os
import tempfile

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
