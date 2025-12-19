from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# TEMP storage of paid emails (works fine for now)
PAID_EMAILS = set()

class ReviewRequest(BaseModel):
    review_text: str
    email: str

@app.get("/")
def home(request: Request):
    email = request.query_params.get("email")
    if email:
        PAID_EMAILS.add(email)
    return FileResponse("index.html")

@app.post("/generate-reply")
def generate(req: ReviewRequest):
    if req.email not in PAID_EMAILS:
        return {"reply_text": "Please subscribe (£35/month) before using the generator."}

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": "Write a professional reply to a customer review."},
                {"role": "user", "content": req.review_text}
            ]
        },
        timeout=20
    )

    reply = r.json()["choices"][0]["message"]["content"]
    return {"reply_text": reply}
