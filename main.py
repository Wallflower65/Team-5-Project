import os
import asyncio
import io
import json
import uuid
from typing import Optional

from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from copyleaks.copyleaks import Copyleaks
from copyleaks.models.submit.ai_detection_document import NaturalLanguageDocument

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html at the root path
@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to Team-5 API"}

# Allow the frontend (served from a different origin/port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your actual frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_ADDRESS = "mutonkoleerico@gmail.com"
API_KEY = "c1f28242-3bc6-4880-8a7c-20d1113ccb54"


def get_auth_token():
    """Authenticate with Copyleaks and return token."""
    try:
        return Copyleaks.login(EMAIL_ADDRESS, API_KEY)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Copyleaks authentication failed: {str(e)}")


def run_detection(text: str, scan_id: str):
    """Run AI detection using Copyleaks SDK. Synchronous - call via run_in_executor."""
    auth_token = get_auth_token()
    document = NaturalLanguageDocument(text)
    document.set_sandbox(False)
    try:
        return Copyleaks.AiDetectionClient.submit_natural_language(
            auth_token, scan_id, document
        )
    except Exception as e:
        import traceback
        
        print("=" * 60)
        print("FULL EXCEPTION DEBUG:")
        print(f"Exception Type: {type(e)}")
        print(f"Exception Args: {e.args}")
        print(f"All attributes: {dir(e)}")
        
        # Try to find the actual response anywhere
        if hasattr(e, 'response'):
            print(f"Response status: {getattr(e.response, 'status_code', 'N/A')}")
            try:
                print(f"Response body: {e.response.text}")
            except:
                print("Could not read response.text")
        
        # Sometimes the SDK stores it in the first argument
        if e.args and isinstance(e.args[0], str):
            print(f"First arg (string): {e.args[0]}")
        
        # Check for wrapped exceptions
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"Cause: {e.__cause__}")
        if hasattr(e, '__context__') and e.__context__:
            print(f"Context: {e.__context__}")
        
        # Print the full traceback for good measure
        traceback.print_exc()
        print("=" * 60)
        
        # Re-raise so your API returns the 500 (we'll fix this later)
        raise


def extract_text_from_txt(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


def extract_text_from_docx(raw_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(raw_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_pdf(raw_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


async def extract_text_from_file(file: UploadFile) -> str:
    """Dispatch to the right extractor based on file extension."""
    filename = (file.filename or "").lower()
    raw_bytes = await file.read()

    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        if filename.endswith(".txt"):
            return extract_text_from_txt(raw_bytes)
        elif filename.endswith(".docx"):
            return extract_text_from_docx(raw_bytes)
        elif filename.endswith(".pdf"):
            return extract_text_from_pdf(raw_bytes)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload .txt, .docx, or .pdf",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")


@app.post("/detect")
async def detect_ai(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    # Resolve input: prefer file if provided, else fall back to text field
    if file is not None and file.filename:
        resolved_text = await extract_text_from_file(file)
    elif text is not None:
        resolved_text = text
    else:
        raise HTTPException(status_code=400, detail="No text or file provided")

    if not resolved_text or len(resolved_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="No text content found to analyze")

    scan_id = str(uuid.uuid4())
    if len(resolved_text.strip()) < 350:
        raise HTTPException(400, "Text must be at least 350 characters (recommend 500+ for accuracy).")
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, run_detection, resolved_text, scan_id)

        print("RAW COPyleAKS RESPONSE:", json.dumps(response, indent=2)) 

        ai_score = int(response["summary"]["ai"] * 100)
        human_score = int(response["summary"]["human"] * 100)
        final_score = 0 if ai_score < 20 else ai_score

        return {
            "percentage": final_score,
            "ai_percent": ai_score,
            "human_percent": human_score,
            "model_version": response.get("modelVersion"),
        }

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=502, detail=f"Unexpected response structure: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")
