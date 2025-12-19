from fastapi import FastAPI
import os
import requests
import email
import smtplib
from imapclient import IMAPClient
from email.message import EmailMessage

app = FastAPI()

# ENV VARS (set in Render)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def generate_reply(review_text: str) -> str:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "Write a short, professional, polite reply to a customer review."},
                {"role": "user", "content": review_text},
            ],
        },
        timeout=20,
    )
    data = r.json()
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


@app.get("/process-emails")
def process_emails():
    processed = 0

    with IMAPClient(IMAP_HOST) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.select_folder("INBOX")
        messages = server.search(["UNSEEN"])

        for uid in messages:
            raw = server.fetch(uid, ["RFC822"])[uid][b"RFC822"]
            msg = email.message_from_bytes(raw)

            from_email = email.utils.parseaddr(msg.get("From"))[1]

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            if body.strip():
                reply = generate_reply(body)
                send_email(from_email, reply)
                processed += 1

            server.add_flags(uid, ["\\Seen"])

    return {"status": "processed", "count": processed}


@app.get("/")
def health():
    return {"status": "Email review bot running"}

