from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import requests

app = FastAPI()

class ReviewRequest(BaseModel):
    review_text: str

class ReviewReply(BaseModel):
    reply_text: str

@app.get("/")
def serve_site():
    return FileResponse("index.html")

@app.post("/generate-reply", response_model=ReviewReply)
def generate_reply(req: ReviewRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
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
                    "content": req.review_text
                }
            ]
        },
        timeout=20
    )

    reply = response.json()["choices"][0]["message"]["content"]
    return ReviewReply(reply_text=reply.strip())



