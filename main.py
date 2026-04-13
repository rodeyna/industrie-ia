from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil

# Import your LangGraph app
from graph import app as langgraph_pipeline

app = FastAPI(title="INDUSTRIE IA")

# Ensure folders exist and are served
os.makedirs("outputs", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html") as f:
        return f.read()

@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    # 1. Save the incoming file
    temp_path = f"inputs/{file.filename}"
    os.makedirs("inputs", exist_ok=True)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. RUN THE PIPELINE (This creates the files in /outputs)
    # We pass the initial state to LangGraph
    initial_state = {
        "specs": {}, 
        "logs": [f"File {file.filename} received."],
        "pdf_path": temp_path  # Ensure your Module 1 knows where to look
    }
    
    # This runs M1 through M9
    result = langgraph_pipeline.invoke(initial_state)

    # 3. Return success
    return {
        "status": "Pipeline complete", 
        "files": os.listdir("outputs"),
        "logs": result.get("logs", [])
    }

# Specific routes for the main buttons
@app.get("/download/{filename}")
def download_file(filename: str):
    path = f"outputs/{filename}"
    if os.path.exists(path):
        return FileResponse(path)
    return {"detail": "Not Found"}