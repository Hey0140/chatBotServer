from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from typing import Dict, Any
from openai import OpenAI
import httpx
import os
import asyncio

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL")
MM_INCOMING_WEBHOOK_URL = os.getenv("MM_INCOMING_WEBHOOK_URL")
MATTERMOST_TOKEN = os.getenv("MATTERMOST_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()


# 🔹 OpenAI 답변 함수
async def ask_openai(prompt: str) -> str:
    msgs = [
        {"role": "system", "content": "너는 SSAFY 학사도우미이다."},
        {"role": "user", "content": prompt.strip()},
    ]
    resp = client.chat.completions.create(
        model=FINE_TUNED_MODEL,
        messages=msgs,
        temperature=0.3,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()


# 🔹 Mattermost로 메시지 전송 함수 (Incoming Webhook용)
async def post_to_mattermost(text: str, props: Dict[str, Any] | None = None):
    if not MM_INCOMING_WEBHOOK_URL:
        print("⚠️ MM_INCOMING_WEBHOOK_URL이 설정되지 않았습니다.")
        return
    payload = {"text": text}
    if props:
        payload["props"] = props
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(MM_INCOMING_WEBHOOK_URL, json=payload)
        r.raise_for_status()


# 🔹 Mattermost Outgoing Webhook 수신 엔드포인트
@app.post("/")
async def mm_outgoing(
    token: str = Form(...),
    text: str = Form(""),
    trigger_word: str = Form(""),
    channel_name: str = Form(""),
    user_name: str = Form(""),
    post_id: str = Form(""),
):

    if not token or token != MATTERMOST_TOKEN:
        return JSONResponse({"text": "forbidden"}, status_code=403)


    answer = await ask_openai(text) 

    msg = f"**@{user_name}**\n{answer}"
    await post_to_mattermost(msg)

    return JSONResponse({"text": "✅ 답변 생성 중..."}, status_code=200)


@app.get("/end")
def health():
    return {"ok": True}
