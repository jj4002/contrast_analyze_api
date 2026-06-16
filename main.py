import os
import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

from database import init_db
from config import logger
from models import UploadResponse, AnalyzeResponse, ChatResponse
from services import upload_contract, analyze_contract, chat_with_contract

app = FastAPI(title="ContractLens", description="Hệ thống AI rà soát hợp đồng tiếng Việt", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    logger.info("Initializing ContractLens...")
    init_db()
    logger.info("ContractLens ready")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ContractLens", "version": "2.0.0"}


class AnalyzeRequest(BaseModel):
    contract_id: str


class ChatRequest(BaseModel):
    contract_id: str
    question: str
    history: List[Dict[str, Any]] = []


@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    try:
        return await upload_contract(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    try:
        return await analyze_contract(req.contract_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        return await chat_with_contract(req.contract_id, req.question, req.history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_path}")
else:
    logger.warning(f"Frontend not found at {frontend_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
