from fastapi import FastAPI
import os
import time
import threading
import requests
from imapclient import IMAPClient
import email
import smtplib
from email.message import EmailMessage

app = FastAPI()

# ENV VARIABLES (from Render)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def generate_reply(review_text: str) -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "Write a short, professional, polite reply to a customer review."
                },
                {
                    "role": "user",
                    "content": review_text
                }
            ]
        },
        timeout=20
    )

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def send_email(to_email: str, reply_text: str):
    msg = EmailMessage()
    msg["From"] = f"Review Bot <{EMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = "Your review reply is ready"
    msg.set_content(reply_text)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)


def check_emails_loop():
    print("📧 Email bot running...")

    while True:
        try:
            with IMAPClient(IMAP_HOST) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.select_folder("INBOX")

                messages = server.search(["UNSEEN"])

                for uid in messages:
                    raw_message = server.fetch(uid, ["RFC822"])[uid][b"RFC822"]
                    msg = email.message_from_bytes(raw_message)

                    from_email = email.utils.parseaddr(msg["From"])[1]

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    print("📩 New email from:", from_email)

                    reply_text = generate_reply(body)
                    send_email(from_email, reply_text)

                    server.add_flags(uid, ["\\Seen"])

        except Exception as e:
            print("❌ Email loop error:", e)

        time.sleep(60)  # check every minute


@app.on_event("startup")
def start_email_bot():
    threading.Thread(target=check_emails_loop, daemon=True).start()


@app.get("/")
def health():
    return {"status": "Email review bot running"}


