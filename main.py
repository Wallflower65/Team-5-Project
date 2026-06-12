import uuid
import asyncio
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from copyleaks.copyleaks import Copyleaks
from copyleaks.models.submit.ai_detection_document import NaturalLanguageDocument

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_ADDRESS = "mutonkoleerico@gmail.com"
API_KEY = "c1f28242-3bc6-4880-8a7c-20d1113ccb54"


def get_auth_token():
    try:
        return Copyleaks.login(EMAIL_ADDRESS, API_KEY)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


def run_detection(text: str, scan_id: str):
    token = get_auth_token()
    document = NaturalLanguageDocument(text)
    document.set_sandbox(True)
    return Copyleaks.AiDetectionClient.submit_natural_language(token, scan_id, document)


@app.post("/scan")
async def scan_assignment(text: str = Form(...)):
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text workspace is empty")

    scan_id = str(uuid.uuid4())

    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, run_detection, text, scan_id)

        ai_raw = res.get("summary", {}).get("ai", 0.0)
        ai_score = int(ai_raw * 100)
        
        sentences = []
        results_list = res.get("results", [])
        
        if not results_list:
            sentences.append({
                "text": text,
                "ai_prob": ai_raw
            })
        else:
            for item in results_list:
                sentences.append({
                    "text": text,
                    "ai_prob": item.get("probability", 0.0) if item.get("classification") == 1 else 0.0
                })

        return {
            "percentage": ai_score,
            "sentences": sentences
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))