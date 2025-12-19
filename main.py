from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests

app = FastAPI()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# ✅ Demo email you can use anytime for testing
# ✅ Paid emails get added automatically when Stripe redirects back with ?email=
PAID_EMAILS = {"demo@test.com"}

class ReviewRequest(BaseModel):
    review_text: str
    email: str

@app.get("/")
def serve_site(request: Request):
    # If Stripe redirects back with ?email=their@email.com, unlock them
    email_param = request.query_params.get("email")
    if email_param:
        PAID_EMAILS.add(email_param.strip().lower())
    return FileResponse("index.html")

@app.post("/generate-reply")
def generate(req: ReviewRequest):
    user_email = (req.email or "").strip().lower()

    if user_email not in PAID_EMAILS:
        return {"reply_text": "Locked. Please subscribe (£35/month) to use the generator."}

    if not OPENROUTER_KEY:
        return {"reply_text": "Server error: Missing OPENROUTER_API_KEY."}

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "Write a short, professional, polite reply to a customer review."},
                {"role": "user", "content": req.review_text}
            ]
        },
        timeout=20
    )

    reply = r.json()["choices"][0]["message"]["content"].strip()
    return {"reply_text": reply}

