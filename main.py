from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests

app = FastAPI()

class ReviewRequest(BaseModel):
    review_text: str
    business_name: str = "Your Business"
    tone: str = "professional and friendly"

class ReviewReply(BaseModel):
    reply_text: str

def generate_reply(review_text: str, business_name: str, tone: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Missing API key."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {
                "role": "system",
                "content": "Write a short, polite reply to a customer review. Keep it under 80 words."
            },
            {
                "role": "user",
                "content": (
                    f"Business name: {business_name}\n"
                    f"Tone: {tone}\n\n"
                    f"Customer review:\n\"{review_text}\"\n\n"
                    "Write a reply as the business owner."
                )
            }
        ]
    }

    try:
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return "Thank you for your feedback! We appreciate you taking the time to leave a review."

@app.get("/")
def root():
    return {"status": "AI Review Reply API running"}

@app.post("/generate-reply", response_model=ReviewReply)
def generate(req: ReviewRequest):
    reply = generate_reply(req.review_text, req.business_name, req.tone)
    return ReviewReply(reply_text=reply)


