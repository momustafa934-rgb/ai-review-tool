from fastapi import FastAPI
import os, requests, email, smtplib
from imapclient import IMAPClient
from email.message import EmailMessage

app = FastAPI()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def generate_reply(text):
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "Write a short professional reply to a customer review."},
                {"role": "user", "content": text}
            ]
        },
        timeout=20
    )
    return r.json()["choices"][0]["message"]["content"]

def send_email(to_email, reply):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = "Your review reply"
    msg.set_content(reply)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.send_message(msg)

@app.post("/process-emails")
def process_emails():
    with IMAPClient(IMAP_HOST) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.select_folder("INBOX")
        messages = server.search(["UNSEEN"])

        for uid in messages:
            raw = server.fetch(uid, ["RFC822"])[uid][b"RFC822"]
            msg = email.message_from_bytes(raw)
            from_email = email.utils.parseaddr(msg["From"])[1]

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            reply = generate_reply(body)
            send_email(from_email, reply)
            server.add_flags(uid, ["\\Seen"])

    return {"status": "processed"}


