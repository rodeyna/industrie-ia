"""
INDUSTRIE IA — FastAPI Backend
================================
Endpoints :
  POST /run          → lance le pipeline complet
  GET  /view/plan    → viewer 2D/3D (M2)
  GET  /view/video   → player vidéo (M3)
  GET  /view/jumeau  → dashboard jumeau numérique (M8)
  GET  /status       → état du pipeline
  GET  /outputs/{filename} → téléchargement fichiers
"""

import os
import json
import base64
import logging
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import run_pipeline

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="INDUSTRIE IA",
    description="Pipeline LangGraph — Génération plans, vidéo, jumeau numérique",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# État global du pipeline (en prod → stocker en DB)
pipeline_state: dict = {}
pipeline_running: bool = False

os.makedirs("outputs/cad",   exist_ok=True)
os.makedirs("outputs/jumeau", exist_ok=True)
app.mount("/static", StaticFiles(directory="outputs"), name="static")


# ===========================================================================
# MODÈLES PYDANTIC
# ===========================================================================

class PipelineRequest(BaseModel):
    specs: dict = {
        "designation":       "Vanne_DN100_PN40",
        "diametre_nominal":  100,
        "pression_nominale": 40,
        "longueur":          250,
        "materiau":          "Stainless Steel 316L",
        "epaisseur_paroi":   8,
        "nb_boulons":        8,
        "diametre_boulon":   16,
        "diametre_bride":    220,
        "hauteur_corps":     160,
        "diametre_actuateur":60,
        "hauteur_actuateur": 80,
        "tolerance":         "±0.1 mm",
        "norme":             "EN 1092-1",
    }
    thread_id: str = "main"


# ===========================================================================
# ENDPOINTS
# ===========================================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<html><body style="font-family:sans-serif;padding:30px;background:#0D1117;color:#E6EDF3">
    <h1>INDUSTRIE IA — Pipeline</h1>
    <ul style="line-height:2.2">
      <li><a href="/docs" style="color:#58A6FF">API Swagger</a></li>
      <li><a href="/view/plan" style="color:#58A6FF">Viewer Plan 2D/3D</a></li>
      <li><a href="/view/video" style="color:#58A6FF">Vidéo présentation</a></li>
      <li><a href="/view/jumeau" style="color:#58A6FF">Dashboard Jumeau Numérique</a></li>
      <li><a href="/status" style="color:#58A6FF">État pipeline JSON</a></li>
    </ul>
    <p style="margin-top:20px;color:#8B949E">POST /run pour lancer le pipeline complet</p>
    </body></html>"""


@app.post("/run")
async def run(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Lance le pipeline LangGraph en arrière-plan."""
    global pipeline_running, pipeline_state

    if pipeline_running:
        raise HTTPException(status_code=409, detail="Pipeline déjà en cours")

    def _run():
        global pipeline_running, pipeline_state
        pipeline_running = True
        try:
            pipeline_state = run_pipeline(
                specs=req.specs,
                thread_id=req.thread_id
            )
        finally:
            pipeline_running = False

    background_tasks.add_task(_run)
    return {"message": "Pipeline lancé", "thread_id": req.thread_id,
            "endpoints": {
                "plan":   "GET /view/plan",
                "video":  "GET /view/video",
                "jumeau": "GET /view/jumeau",
                "status": "GET /status"
            }}


@app.get("/status")
async def status():
    """Retourne l'état courant du pipeline."""
    return {
        "running": pipeline_running,
        "modules": {
            "module2": pipeline_state.get("module2_ok"),
            "module3": pipeline_state.get("module3_ok"),
            "module8": pipeline_state.get("module8_ok"),
        },
        "outputs": {
            "dxf":      pipeline_state.get("dxf_path"),
            "png_3d":   pipeline_state.get("png_path"),
            "mp4":      pipeline_state.get("mp4_path"),
            "dashboard":pipeline_state.get("dashboard_html"),
        },
        "errors":    pipeline_state.get("pipeline_errors", []),
        "done":      pipeline_state.get("pipeline_done", False),
    }


@app.get("/view/plan", response_class=HTMLResponse)
async def view_plan():
    """Viewer 2D/3D du plan généré par le module 2."""
    png_path = pipeline_state.get("png_path", "")
    dxf_path = pipeline_state.get("dxf_path", "")
    specs    = pipeline_state.get("pdf_specs", {})

    if not png_path or not os.path.exists(png_path):
        return HTMLResponse("""<html><body style="font-family:sans-serif;padding:30px;background:#0D1117;color:#E6EDF3">
        <h2>Plan non encore généré</h2>
        <p style="color:#8B949E">Lancez d'abord le pipeline : <code>POST /run</code></p>
        </body></html>""", status_code=202)

    with open(png_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # Convertir DXF en SVG si ezdxf disponible
    svg_content = ""
    if dxf_path and os.path.exists(dxf_path):
        try:
            import ezdxf
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.svg import SVGBackend
            doc = ezdxf.readfile(dxf_path)
            backend = SVGBackend()
            Frontend(RenderContext(doc), backend).draw_layout(doc.modelspace())
            svg_content = backend.get_string()
        except Exception as e:
            svg_content = f"<p style='color:#E3B341'>DXF viewer non disponible : {e}</p>"

    designation = specs.get("designation", "Vanne DN100 PN40")
    dn  = specs.get("diametre_nominal",  100)
    pn  = specs.get("pression_nominale", 40)
    mat = specs.get("materiau", "316L")
    lon = specs.get("longueur", 250)

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Plan — {designation}</title>
<style>
  body {{ font-family:'Segoe UI',sans-serif; background:#0D1117; color:#E6EDF3; margin:0; padding:20px; }}
  h1 {{ font-size:1.2rem; margin-bottom:4px; }}
  .meta {{ color:#8B949E; font-size:0.85rem; margin-bottom:20px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
  .card {{ background:#161B22; border:1px solid #21262D; border-radius:8px; padding:16px; }}
  img {{ max-width:100%; border-radius:6px; }}
  .dxf-viewer {{ overflow:auto; max-height:600px; background:#fff; border-radius:6px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  td {{ padding:6px 8px; font-size:0.85rem; border-bottom:1px solid #21262D; }}
  td:first-child {{ color:#8B949E; }}
  a.btn {{ display:inline-block; margin-top:12px; padding:8px 16px;
           background:#238636; color:#fff; border-radius:6px; text-decoration:none;
           font-size:0.85rem; }}
</style>
</head><body>
<h1>{designation}</h1>
<div class="meta">DN{dn} / PN{pn} bar — {mat} — Longueur : {lon} mm</div>

<div class="grid">
  <div class="card">
    <h3 style="margin-bottom:12px;font-size:0.9rem">Vue 3D</h3>
    <img src="data:image/png;base64,{img_b64}" alt="Rendu 3D"/>
    <a class="btn" href="/static/cad/{os.path.basename(png_path)}" download>
      Télécharger PNG
    </a>
  </div>

  <div class="card">
    <h3 style="margin-bottom:12px;font-size:0.9rem">Plan 2D (DXF)</h3>
    <div class="dxf-viewer">{svg_content if svg_content else "<p style='color:#8B949E;padding:20px'>SVG non disponible — téléchargez le DXF</p>"}</div>
    {"<a class='btn' href='/static/cad/" + os.path.basename(dxf_path) + "' download>Télécharger DXF</a>" if dxf_path else ""}
  </div>
</div>

<div class="card" style="margin-top:20px">
  <h3 style="margin-bottom:10px;font-size:0.9rem">Spécifications techniques</h3>
  <table>
    <tr><td>Désignation</td><td>{designation}</td></tr>
    <tr><td>Diamètre nominal</td><td>DN {dn} mm</td></tr>
    <tr><td>Pression nominale</td><td>PN {pn} bar</td></tr>
    <tr><td>Matériau</td><td>{mat}</td></tr>
    <tr><td>Longueur face/face</td><td>{lon} mm</td></tr>
    <tr><td>Norme</td><td>{specs.get("norme","EN 1092-1")}</td></tr>
    <tr><td>Tolérance</td><td>{specs.get("tolerance","±0.1 mm")}</td></tr>
  </table>
</div>
</body></html>"""


@app.get("/view/video", response_class=HTMLResponse)
async def view_video():
    """Player vidéo de présentation (module 3)."""
    mp4 = pipeline_state.get("mp4_path", "")

    if not mp4 or not os.path.exists(mp4):
        return HTMLResponse("""<html><body style="font-family:sans-serif;padding:30px;background:#0D1117;color:#E6EDF3">
        <h2>Vidéo non encore générée</h2>
        <p style="color:#8B949E">Lancez d'abord le pipeline : <code>POST /run</code></p>
        </body></html>""", status_code=202)

    filename = os.path.basename(mp4)
    ext = Path(mp4).suffix.lower()
    mime = "video/mp4" if ext == ".mp4" else "image/gif" if ext == ".gif" else "video/x-msvideo"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Vidéo présentation</title>
<style>
  body {{ font-family:'Segoe UI',sans-serif; background:#0D1117;
         color:#E6EDF3; padding:30px; text-align:center; }}
  h1 {{ margin-bottom:20px; font-size:1.2rem; }}
  video, img {{ max-width:900px; width:100%; border-radius:8px; }}
  .meta {{ color:#8B949E; font-size:0.85rem; margin-top:10px; }}
  a.btn {{ display:inline-block; margin-top:16px; padding:8px 16px;
           background:#238636; color:#fff; border-radius:6px; text-decoration:none; }}
</style>
</head><body>
<h1>Vidéo de présentation — INDUSTRIE IA</h1>
{"<video controls autoplay muted loop><source src='/static/cad/" + filename + "' type='" + mime + "'></video>"
 if ext in [".mp4", ".avi"] else
 "<img src='/static/cad/" + filename + "' alt='Animation'/>"}
<div class="meta">Fichier : {filename} — {os.path.getsize(mp4)/1024/1024:.1f} MB</div>
<a class="btn" href="/static/cad/{filename}" download>Télécharger {ext.upper()}</a>
</body></html>"""


@app.get("/view/jumeau", response_class=HTMLResponse)
async def view_jumeau():
    """Redirige vers le dashboard HTML du jumeau numérique (module 8)."""
    html_path = pipeline_state.get("dashboard_html", "")

    if not html_path or not os.path.exists(html_path):
        return HTMLResponse("""<html><body style="font-family:sans-serif;padding:30px;background:#0D1117;color:#E6EDF3">
        <h2>Jumeau numérique non encore généré</h2>
        <p style="color:#8B949E">Lancez d'abord le pipeline : <code>POST /run</code></p>
        </body></html>""", status_code=202)

    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/outputs/{filename}")
async def download_output(filename: str):
    """Téléchargement d'un fichier généré."""
    for folder in ["outputs/cad", "outputs/jumeau", "outputs"]:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return FileResponse(path, filename=filename)
    raise HTTPException(status_code=404, detail=f"Fichier {filename} non trouvé")


# ===========================================================================
# LANCEMENT
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)