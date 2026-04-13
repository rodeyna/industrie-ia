"""
INDUSTRIE IA — Orchestration LangGraph (Version Finale Stabilisée)
==================================================================
Ce script gère l'enchaînement des modules 2, 3 et 8.
Correction : Sérialisation NumPy et Checkpointer Memory.
"""

import os
import json
import logging
import numpy as np
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver 

# Imports des modules (Assurez-vous que les fichiers existent dans /modules)
try:
    from modules.module2_generation_plans import run_module2
    from modules.module3_presentation_video import run_module3
    from modules.module8_jumeau_numerique import run_module8
except ImportError as e:
    logging.error(f"Erreur d'importation des modules : {e}")

logger = logging.getLogger(__name__)

# ===========================================================================
# UTILITAIRE DE NETTOYAGE (Correction erreur numpy.float64)
# ===========================================================================

def clean_state(state: Any) -> Any:
    """Convertit récursivement les types NumPy en types Python natifs."""
    if isinstance(state, dict):
        return {k: clean_state(v) for k, v in state.items()}
    elif isinstance(state, list):
        return [clean_state(v) for v in state]
    elif isinstance(state, np.generic):
        return state.item()  # numpy.float64 -> float
    return state

# ===========================================================================
# ÉTAT PARTAGÉ LANGGRAPH
# ===========================================================================

class AgentState(TypedDict):
    pdf_specs:        Optional[dict]
    pdf_path:         Optional[str]
    dxf_path:         Optional[str]
    png_path:         Optional[str]
    ifc_path:         Optional[str]
    specs_path:       Optional[str]
    viewer_url:       Optional[str]
    module2_ok:       Optional[bool]
    mp4_path:         Optional[str]
    avi_path:         Optional[str]
    module3_ok:       Optional[bool]
    sensor_json:      Optional[str]
    dashboard_png:    Optional[str]
    dashboard_html:   Optional[str]
    rul_json:         Optional[str]
    rul:              Optional[dict]
    n_anomalies:      Optional[int]
    module8_ok:       Optional[bool]
    pipeline_errors:  Optional[list]
    pipeline_done:    Optional[bool]

# ===========================================================================
# NŒUDS DE GARDE
# ===========================================================================

def safe_module2(state: AgentState) -> AgentState:
    try:
        res = run_module2(state)
        return clean_state(res)
    except Exception as e:
        logger.error(f"[M2] Erreur : {e}")
        errs = state.get("pipeline_errors") or []
        return {**state, "module2_ok": False, "pipeline_errors": errs + [f"M2: {e}"]}

def safe_module3(state: AgentState) -> AgentState:
    try:
        res = run_module3(state)
        return clean_state(res)
    except Exception as e:
        logger.error(f"[M3] Erreur : {e}")
        errs = state.get("pipeline_errors") or []
        return {**state, "module3_ok": False, "pipeline_errors": errs + [f"M3: {e}"]}

def safe_module8(state: AgentState) -> AgentState:
    try:
        res = run_module8(state)
        return clean_state(res)
    except Exception as e:
        logger.error(f"[M8] Erreur : {e}")
        errs = state.get("pipeline_errors") or []
        return {**state, "module8_ok": False, "pipeline_errors": errs + [f"M8: {e}"]}

def finalize(state: AgentState) -> AgentState:
    logger.info("[GRAPH] Pipeline terminé avec succès.")
    return {**state, "pipeline_done": True}

# ===========================================================================
# CONSTRUCTION DU GRAPHE
# ===========================================================================

def build_graph():
    os.makedirs("outputs", exist_ok=True)
    workflow = StateGraph(AgentState)

    workflow.add_node("module_2", safe_module2)
    workflow.add_node("module_3", safe_module3)
    workflow.add_node("module_8", safe_module8)
    workflow.add_node("finalize", finalize)

    workflow.set_entry_point("module_2")
    workflow.add_edge("module_2", "module_3")
    workflow.add_edge("module_3", "module_8")
    workflow.add_edge("module_8", "finalize")
    workflow.add_edge("finalize", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# ===========================================================================
# RUNNER
# ===========================================================================

def run_pipeline(specs: dict = None, pdf_path: str = None, thread_id: str = "main") -> dict:
    app = build_graph()
    
    # Nettoyage initial des specs
    initial_specs = clean_state(specs or {})
    
    initial_state: AgentState = {
        "pdf_specs": initial_specs, "pdf_path": pdf_path,
        "dxf_path": None, "png_path": None, "ifc_path": None, "specs_path": None,
        "viewer_url": None, "module2_ok": None, "mp4_path": None, "avi_path": None,
        "module3_ok": None, "sensor_json": None, "dashboard_png": None,
        "dashboard_html": None, "rul_json": None, "rul": None, "n_anomalies": None,
        "module8_ok": None, "pipeline_errors": [], "pipeline_done": False,
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    return app.invoke(initial_state, config=config)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test avec des valeurs types
    specs_test = {
        "designation": "Vanne_Industrielle_V3",
        "diametre_nominal": 100,
        "pression_nominale": 40,
        "materiau": "Acier Inox"
    }
    
    print("\n--- LANCEMENT DU TEST INDUSTRIE IA ---")
    result = run_pipeline(specs=specs_test, thread_id="test-demo")
    print(f"\n TERMINÉ")
    print(f"M2 (Plans)  : {result.get('module2_ok')}")
    print(f"M3 (Vidéo)  : {result.get('module3_ok')}")
    print(f"M8 (Jumeau) : {result.get('module8_ok')}")