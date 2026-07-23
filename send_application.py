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


class SendError(Exception):
    """Erro tratável de envio (mensagem amigável já embutida)."""


def send_email(to_email: str, subject: str, body: str, attachment_path: str):
    """Envia o e-mail com o currículo anexado. Levanta SendError em caso de
    problema (credenciais faltando, anexo inexistente, falha SMTP) — para o
    app tratar sem derrubar o processo."""
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD:
        raise SendError(
            "GMAIL_ADDRESS/GMAIL_APP_PASSWORD não definidos no .env. Crie uma "
            "'senha de app' em https://myaccount.google.com/apppasswords."
        )
    if not os.path.exists(attachment_path):
        raise SendError(f"Anexo não encontrado: {attachment_path}")

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

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        raise SendError(
            "Falha de autenticação no Gmail. Confira GMAIL_ADDRESS e use uma "
            "'senha de app' (não a senha normal)."
        ) from e
    except (smtplib.SMTPException, OSError) as e:
        raise SendError(f"Falha ao enviar e-mail: {e}") from e

    print(f"Enviado para {to_email}.")


def resume_attachment(folder: str) -> str:
    """Prefere resume.pdf; cai para resume.md se o PDF não existir."""
    pdf = os.path.join(folder, "resume.pdf")
    return pdf if os.path.exists(pdf) else os.path.join(folder, "resume.md")


def subject_and_body(title: str) -> tuple:
    """Assunto + corpo padrão da candidatura (nome completo do candidato)."""
    subject = f"Candidatura — {title}"
    body = (
        "Olá,\n\n"
        f"Meu nome é Konstantin Borisov e tenho interesse na vaga de {title}. "
        "Segue meu currículo em anexo.\n\n"
        "Fico à disposição para conversar.\n\n"
        "Atenciosamente,\nKonstantin Borisov"
    )
    return subject, body


def read_title(folder: str) -> str:
    job_info_path = os.path.join(folder, "job_info.txt")
    if os.path.exists(job_info_path):
        with open(job_info_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("Título:"):
                    return line.split(":", 1)[1].strip()
    return "vaga"


def main():
    if len(sys.argv) < 3:
        print(
            "Uso: python send_application.py <pasta_da_vaga> <email_destino> "
            "[caminho_do_curriculo]"
        )
        sys.exit(1)

    folder = sys.argv[1]
    to_email = sys.argv[2]
    attachment = sys.argv[3] if len(sys.argv) > 3 else resume_attachment(folder)

    title = read_title(folder)
    subject, body = subject_and_body(title)

    print(f"Assunto: {subject}")
    print(f"Anexo: {attachment}")
    confirm = input(f"Confirma o envio para {to_email}? (s/N): ")
    if confirm.strip().lower() != "s":
        print("Cancelado.")
        return

    try:
        send_email(to_email, subject, body, attachment)
    except SendError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
