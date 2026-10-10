"""FastAPI wrapper.   uvicorn app:app --reload   ->  http://127.0.0.1:8000/docs"""
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from attacks import ATTACKS
from classifier import classify
from pipeline import chat

app = FastAPI(title="AcmeBot - prompt-injection lab")


class ChatRequest(BaseModel):
    message: str
    context_chunks: Optional[List[str]] = None
    protected: bool = True


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    return chat(req.message, req.context_chunks,
                sanitize=req.protected, moderate=req.protected, validate=req.protected)


@app.post("/attacks/run")
def run_attacks(protected: bool = True):
    out = []
    for a in ATTACKS:
        r = chat(a["user_query"], a.get("context_chunks"),
                 sanitize=protected, moderate=protected, validate=protected)
        out.append({"id": a["id"], "name": a["name"], "verdict": classify(a, r), "status": r["status"], "response": r["response"]})
    return {"protected": protected, "results": out}
