"""
FastAPI Backend for AKGP Legal Intelligence Engine
=================================================
Serves the Vanilla HTML frontend and exposes a REST API for the LangGraph agent swarm.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys
import shutil
import uuid
from PIL import Image
import pytesseract
from agents.contract_analyzer import analyze_contract_text
from rag.ingest_pdfs import extract_text_from_pdf
import sys

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Suppress LangChain / LangGraph warnings for cleaner logs
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

# Import our LangGraph app
from orchestrator import build_legal_graph, create_initial_state

app = FastAPI(title="AKGP Legal Intelligence Engine")

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway to verify the app is ready."""
    return {"status": "ok"}

# Pre-compile the graph for speed
agent_swarm = build_legal_graph()

class QueryRequest(BaseModel):
    query: str
    mode: str = "citizen"

@app.post("/api/analyze")
async def analyze_query(request: QueryRequest):
    """Executes the multi-agent legal reasoning pipeline."""
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        # Initialize the LangGraph state
        initial_state = create_initial_state(request.query, request.mode)
        
        # Run the multi-agent pipeline
        # Note: Since this is synchronous, it will block the worker.
        # In a real production system, use agent_swarm.ainvoke() if agents support async.
        final_state = agent_swarm.invoke(initial_state)
        
        # Extract cases from parallel expert drafts
        verified_cases, cautioned_cases, rejected_cases = [], [], []
        classification = {}
        for ed in final_state.get("expert_drafts", []):
            verified_cases.extend(ed.get("verified_cases", []))
            cautioned_cases.extend(ed.get("cautioned_cases", []))
            rejected_cases.extend(ed.get("rejected_cases", []))
            
        return {
            "query": request.query,
            "routed_domains": final_state.get("routed_domains", []),
            "final_draft": final_state.get("final_draft", "No output generated."),
            "revisions_made": final_state.get("revision_count", 0),
            "pipeline_summary": {
                "verified_cases": len(verified_cases),
                "cautioned_cases": len(cautioned_cases),
                "rejected_cases": len(rejected_cases),
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), mode: str = Form("citizen")):
    """Upload a PDF or Image of a contract to find risks and pitfalls."""
    try:
        os.makedirs("rag/uploads", exist_ok=True)
        ext = file.filename.split(".")[-1].lower()
        temp_id = str(uuid.uuid4())
        temp_path = f"rag/uploads/temp_{temp_id}.{ext}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        extracted_text = ""
        if ext == "pdf":
            extracted_text = extract_text_from_pdf(temp_path)
        elif ext in ["png", "jpg", "jpeg"]:
            img = Image.open(temp_path)
            extracted_text = pytesseract.image_to_string(img)
        else:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Only PDF, PNG, JPG, and JPEG are supported.")
            
        os.remove(temp_path)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract any readable text from the file.")
            
        analysis = analyze_contract_text(extracted_text, mode)
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
            
        return analysis
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Mount the frontend directory
os.makedirs("frontend", exist_ok=True)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    """Serve the main UI."""
    return FileResponse("frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
