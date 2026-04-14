from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, shutil

app = FastAPI(title="INDUSTRIE IA - M1 University of Boumerdes")

# Création du dossier de sortie s'il n'existe pas
os.makedirs("outputs", exist_ok=True)

# Montage du dossier outputs pour l'accès statique
app.mount("/static_outputs", StaticFiles(directory="outputs"), name="outputs")

# --- Door 1: Serve l'interface UI/UX ---
@app.get("/", response_class=HTMLResponse)
def home():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erreur : templates/index.html non trouvé."

# --- Door 2: Pipeline Principal ---
@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    # 1. Sauvegarde du PDF entrant
    pdf_path = os.path.join("outputs", file.filename)
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    print(f"[FastAPI] PDF sauvegardé → {pdf_path}")

    # 2. Lancement du cerveau (LangGraph)
    from graph import run_pipeline
    try:
        result = run_pipeline(pdf_path)
        print(f"[FastAPI] Pipeline terminé. Erreurs: {result.get('errors')}")

        # 3. Retour des données à l'interface
        return {
            "status": "done",
            "specs": result.get("specs"),
            "suppliers": result.get("suppliers"),
            "tco_total": result.get("tco", {}).get("total_10yr") or result.get("tco", {}).get("total"),
            "catalog_files": result.get("catalog_paths"),
            "dxf_path": result.get("dxf_path"),    # Chemin M2
            "video_path": result.get("video_path"),# Chemin M3
            "errors": result.get("errors", [])
        }
    except Exception as e:
        print(f"[ERREUR] Pipeline Crash: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Door 3: Route de Téléchargement Universelle (CORRECTION 404) ---
@app.get("/download/{filename}")
async def download_file(filename: str):
    """Permet de télécharger n'importe quel fichier généré."""
    file_path = os.path.join("outputs", filename)
    if os.path.exists(file_path):
        # On force le nom du fichier pour le téléchargement
        return FileResponse(path=file_path, filename=filename)
    else:
        print(f"[Erreur] Fichier non trouvé : {file_path}")
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

# --- Door 4: Administration ---
@app.get("/outputs-list")
def list_outputs():
    return {"files": os.listdir("outputs")}