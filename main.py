from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="INDUSTRIE IA")

# Serve the outputs folder (so files can be downloaded)
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Serve the UI at the root URL
@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html") as f:
        return f.read()

# Upload PDF and run pipeline
@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    with open("uploaded.pdf", "wb") as f:
        f.write(pdf_bytes)
    return {"status": "received", "filename": file.filename}

# Download final catalog
@app.get("/catalog")
def get_catalog():
    path = "outputs/catalog.pdf"
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "not generated yet"}