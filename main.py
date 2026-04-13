from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, shutil

app = FastAPI(title="INDUSTRIE IA")

# Serve output files for download
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Door 1 — Serve the UI
@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html") as f:
        return f.read()

# Door 2 — Receive PDF and run the full pipeline
@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    
    # Save the uploaded PDF
    pdf_path = f"outputs/{file.filename}"
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    print(f"[FastAPI] PDF saved → {pdf_path}")

    # Run the full LangGraph pipeline
    from graph import run_pipeline
    result = run_pipeline(pdf_path)
    print(f"[FastAPI] Pipeline done. Errors: {result.get('errors')}")

    # Return results to the browser
    return {
        "status":        "done",
        "specs":         result.get("specs"),
        "suppliers":     result.get("suppliers"),
        "tco_total":     result.get("tco", {}).get("total_10yr"),
        "catalog_files": result.get("catalog_paths"),
        "errors":        result.get("errors", [])
    }

# Door 3 — Download catalog PDF
@app.get("/catalog")
def get_catalog():
    path = "outputs/catalog.pdf"
    if os.path.exists(path):
        return FileResponse(path, filename="catalog.pdf")
    return {"error": "not generated yet — run /process first"}

# Door 4 — See all generated files
@app.get("/outputs-list")
def list_outputs():
    return {"files": os.listdir("outputs")}