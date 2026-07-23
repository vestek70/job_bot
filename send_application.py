"""
Envia (por e-mail) uma candidatura para UMA vaga específica, após sua confirmação manual.

Uso:
  python send_application.py applications/empresa_vaga_123 destinatario@empresa.com

Só funciona quando a vaga tem um e-mail de contato direto. A maioria dos agregadores
(como Adzuna) redireciona para o site da empresa, onde a candidatura deve ser feita
manualmente — este script NÃO contorna isso, nem faz login automático em nenhuma
plataforma (LinkedIn, Gupy, Catho, InfoJobs etc.), pois isso violaria os termos de
uso dessas plataformas e pode levar ao bloqueio da conta.

Requer variáveis de ambiente:
  GMAIL_ADDRESS
  GMAIL_APP_PASSWORD  (senha de app do Gmail, não a senha normal da conta —
                        crie em https://myaccount.google.com/apppasswords)
"""
import os
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(to_email: str, subject: str, body: str, attachment_path: str):
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        print(
            "ERRO: defina GMAIL_ADDRESS e GMAIL_APP_PASSWORD (crie uma 'senha de "
            "app' em https://myaccount.google.com/apppasswords).",
            file=sys.stderr,
        )
        sys.exit(1)

    msg = MIMEMultipart()
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
    part["Content-Disposition"] = (
        f'attachment; filename="{os.path.basename(attachment_path)}"'
    )
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print(f"Enviado para {to_email}.")


def main():
    if len(sys.argv) < 3:
        print(
            "Uso: python send_application.py <pasta_da_vaga> <email_destino> "
            "[caminho_do_curriculo]"
        )
        sys.exit(1)

    folder = sys.argv[1]
    to_email = sys.argv[2]
    attachment = sys.argv[3] if len(sys.argv) > 3 else os.path.join(folder, "resume.md")

    job_info_path = os.path.join(folder, "job_info.txt")
    title = "vaga"
    if os.path.exists(job_info_path):
        with open(job_info_path, encoding="utf-8") as f:
            content = f.read()
        for line in content.splitlines():
            if line.startswith("Título:"):
                title = line.split(":", 1)[1].strip()

    subject = f"Candidatura — {title}"
    body = (
        "Olá,\n\n"
        f"Meu nome é Konstantin e tenho interesse na vaga de {title}. "
        "Segue meu currículo em anexo.\n\n"
        "Fico à disposição para conversar.\n\n"
        "Atenciosamente,\nKonstantin"
    )

    print(f"Assunto: {subject}")
    print(f"Anexo: {attachment}")
    confirm = input(f"Confirma o envio para {to_email}? (s/N): ")
    if confirm.strip().lower() != "s":
        print("Cancelado.")
        return

    send_email(to_email, subject, body, attachment)


if __name__ == "__main__":
    main()
