from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# (CORS is fine to keep; not required once we use same domain, but okay)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReviewRequest(BaseModel):
    review_text: str
    business_name: str = "Your Business"
    tone: str = "professional and friendly"

class ReviewReply(BaseModel):
    reply_text: str

@app.get("/")
def home():
    # serves your website
    return FileResponse("index.html")

def generate_reply(review_text: str, business_name: str, tone: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "API key missing."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": "Write short, polite replies to customer reviews. Keep it under 80 words."},
            {"role": "user", "content": f"Business name: {business_name}\nTone: {tone}\n\nCustomer review:\n\"{review_text}\"\n\nWrite a reply as the business owner."}
        ],
    }

    try:
        r = requests.post(url, headers=headers, json=data, timeout=20)
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"]
        return reply.strip().strip('"')
    except Exception:
        return "Thank you for your feedback. We appreciate you taking the time to leave a review."

@app.post("/generate-reply", response_model=ReviewReply)
def api_generate(req: ReviewRequest):
    reply = generate_reply(req.review_text, req.business_name, req.tone)
    return {"reply_text": reply}
