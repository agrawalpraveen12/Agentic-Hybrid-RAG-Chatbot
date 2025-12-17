
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import shutil
import uuid
import logging
import json
from dotenv import load_dotenv

# Local modules
# Local modules (Relative imports for 'app' package)
from .rag_utils import RAGIndex
from .memory_graph import (
    save_turn,
    load_history,
    clear_history,
    save_profile,
    get_profile,
    save_fact,
    get_facts,
    get_recent_threads
)
from . import agent_hub
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nova - Agentic RAG Chatbot")

# Directories
# Since we are in app/, and run from root as module, or run from app/ dir... 
# Best to make paths absolute relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../app
PROJECT_ROOT = os.path.dirname(BASE_DIR)              # .../Agentic_Rag_chatbot

TMP_DIR = os.path.join(PROJECT_ROOT, "tmp_uploads")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "data", "chroma_db")
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# Static & Templates
# Assumes 'static' folder is in PROJECT_ROOT
app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "static"))

# LLM Setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in .env")

llm = ChatGroq(groq_api_key=GROQ_API_KEY, model=MODEL)
rag = RAGIndex(persist_dir=CHROMA_DIR)

# Models
class ChatRequest(BaseModel):
    message: str
    thread_id: str

class ProfileRequest(BaseModel):
    name: str

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    user_text = req.message
    thread_id = req.thread_id

    # Lightweight memory capture (same as original app.py)
    lower = user_text.lower()
    try:
        if "friend" in lower and "name is" in lower:
            name = user_text.split("name is")[-1].strip().split()[0]
            save_fact("friend", "friend_name", name)
            # Short circuit response
            return StreamingResponse(iter([f"Got it — I’ll remember your friend's name is {name}."]), media_type="text/plain")
        if "teacher" in lower and ("is" in lower or "sir" in lower):
            teacher = user_text.split("is")[-1].strip() if "is" in lower else user_text
            save_fact("teacher", "teacher_name", teacher)
            return StreamingResponse(iter([f"Thanks — I’ll remember that {teacher} is your teacher."]), media_type="text/plain")
    except Exception as e:
        logger.error(f"Memory extract error: {e}")

    # Agent Execution
    async def generate():
        try:
            # Check rag count
            try:
                rag_count = rag.count()
            except:
                rag_count = 0
            
            # Using agent_hub logic
            # Note: agent_hub.run_agent returns a generator/iterator
            streamer = agent_hub.run_agent(
                user_text=user_text,
                llm=llm,
                rag_index=rag,
                get_profile_fn=get_profile,
                get_facts_fn=get_facts,
                top_k=3
            )
            
            full_response = ""
            for chunk in streamer:
                full_response += chunk
                yield chunk
            
            # Save turn
            save_turn(thread_id, user_text, full_response)
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        uid = uuid.uuid4().hex[:8]
        safe_name = f"{os.path.splitext(file.filename)[0]}_{uid}.pdf"
        dest_path = os.path.join(TMP_DIR, safe_name)
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Index
        rag.load_pdf(dest_path)
        return {"status": "success", "filename": file.filename, "message": "Indexed successfully"}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history(thread_id: str):
    msgs = load_history(thread_id)
    # Convert to simple list
    history_data = []
    for m in msgs:
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        history_data.append({"role": role, "content": m.content})
    return history_data

@app.delete("/api/history")
async def delete_history(thread_id: str):
    clear_history(thread_id)
    return {"status": "success"}

@app.get("/api/threads")
async def get_threads_endpoint():
    return get_recent_threads()

@app.get("/api/memory")
async def get_memory_data():
    name = get_profile("name")
    facts = get_facts()
    return {"name": name, "facts": facts}

@app.post("/api/profile")
async def set_profile(req: ProfileRequest):
    save_profile("name", req.name)
    return {"status": "success", "name": req.name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
