from fastapi import FastAPI
import os
import requests
import email
import smtplib
from imapclient import IMAPClient
from email.message import EmailMessage

app = FastAPI()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# prevents re-processing the same emails (works while server stays up)
PROCESSED_MESSAGE_IDS = set()


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
    return r.json()["choices"][0]["message"]["content"].strip()


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


def extract_text(msg_obj) -> str:
    body = ""
    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg_obj.get_payload(decode=True).decode(errors="ignore")
    return body.strip()


@app.get("/process-emails")
def process_emails():
    processed = 0
    checked = 0

    with IMAPClient(IMAP_HOST) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # Check INBOX first
        for folder in ["INBOX", "[Gmail]/All Mail"]:
            try:
                server.select_folder(folder)
            except Exception:
                continue

            uids = server.search(["ALL"])
            if not uids:
                continue

            # only look at the most recent 10 emails
            recent = uids[-10:]

            for uid in recent:
                checked += 1
                raw = server.fetch(uid, ["RFC822"])[uid][b"RFC822"]
                msg = email.message_from_bytes(raw)

                msg_id = msg.get("Message-ID", str(uid))
                if msg_id in PROCESSED_MESSAGE_IDS:
                    continue

                from_email = email.utils.parseaddr(msg.get("From"))[1]
                text = extract_text(msg)

                if not from_email or not text:
                    PROCESSED_MESSAGE_IDS.add(msg_id)
                    continue

                reply = generate_reply(text)
                send_email(from_email, reply)

                PROCESSED_MESSAGE_IDS.add(msg_id)
                processed += 1

            # if we processed something, stop (don’t double-run on All Mail)
            if processed > 0:
                break

    return {"status": "processed", "count": processed, "checked_last_10_each_folder": checked}


@app.get("/")
def health():
    return {"status": "Email review bot running"}


