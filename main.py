from fastapi import FastAPI
import os, time, threading, requests
from imapclient import IMAPClient
import email
import smtplib
from email.message import EmailMessage

app = FastAPI()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def generate_reply(review_text: str) -> str:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "Write a short, professional reply to a customer review."},
                {"role": "user", "content": review_text}
            ]
        },
        timeout=20
    )
    return r.json()["choices"][0]["message"]["content"]

def send_email(to_email: str, reply_text: str):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = "Your review reply is ready"
    msg.set_content(reply_text)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.send_message(msg)

def check_emails_loop():
    while True:
        try:
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
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    reply = generate_reply(body)
                    send_email(from_email, reply)

                    server.add_flags(uid, ["\\Seen"])

        except Exception as e:
            print("Email loop error:", e)

        time.sleep(60)  # check every minute

@app.on_event("startup")
def start_email_bot():
    threading.Thread(target=check_emails_loop, daemon=True).start()

@app.get("/")
def health():
    return {"status": "Email review bot running"}

