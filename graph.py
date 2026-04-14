import os
import logging
import json
import numpy as np
import operator
from typing import TypedDict, List, Optional, Annotated, Any

from langgraph.graph import StateGraph, END

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================================================
# TOOL: NUMPY CLEANER
# ===========================================================================
def clean_state(obj: Any) -> Any:
    """Nettoie les types de données NumPy pour la sérialisation JSON."""
    if isinstance(obj, dict):
        return {k: clean_state(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_state(v) for v in obj]
    elif isinstance(obj, (np.integer, np.floating, np.ndarray)):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj

# ===========================================================================
# UNIFIED STATE
# ===========================================================================
class GraphState(TypedDict):
    pdf_path:           str
    specs:              Optional[dict]
    pdf_specs:          Optional[dict]
    # M2 / M3
    cad_path:           Optional[str]
    dxf_path:           Optional[str]
    video_path:         Optional[str]
    # M4 / M5
    suppliers:          Optional[List[dict]]
    supplier_data:      Optional[List[dict]]
    negotiation:        Optional[dict]
    # M6 / M7
    tco:                Optional[dict]
    tco_results:        Optional[dict]
    business_plan:      Optional[dict]
    # M8
    digital_twin:       Optional[dict]
    # M9
    catalog_paths:      Optional[dict]
    final_catalog_path: Optional[str]
    # Système
    logs:               Annotated[List[str], operator.add]
    errors:             Annotated[List[dict], operator.add]
    pipeline_done:      Optional[bool]

# ===========================================================================
# IMPORTS DES MODULES
# ===========================================================================
from modules.module1_extract       import run_module1_extraction
from modules.module4_sourcing      import run_module4
from modules.module6_tco           import calculate_tco_node
from modules.module7_business_plan import run_module_7
from modules.module8_digital_twin  import run_module8
from modules.module9_catalog       import generate_catalog_node

# Modules M2 et M3 (Gestion dynamique)
try:
    from modules.module2_generation_plans import run_module2
    from modules.module3_presentation_video import run_module3
    HAS_M2_M3 = True
except ImportError:
    HAS_M2_M3 = False
    print("[LOG] Modules M2 ou M3 manquants - Passage en mode simulation pour ces étapes.")

# ===========================================================================
# NODE WRAPPERS
# ===========================================================================

def node_m1(state):
    print("\n--- [M1] IA : Extraction ---")
    res = run_module1_extraction(state)
    res["pdf_specs"] = res.get("specs")
    return clean_state(res)

def node_m2(state):
    print("\n--- [M2] DESIGN : Plans CAD ---")
    if HAS_M2_M3:
        try:
            return clean_state(run_module2(state))
        except Exception as e:
            return {**state, "errors": [{"module": "m2", "error": str(e)}]}
    return state

def node_m3(state):
    print("\n--- [M3] MEDIA : Vidéo ---")
    if HAS_M2_M3:
        try:
            return clean_state(run_module3(state))
        except Exception as e:
            return {**state, "errors": [{"module": "m3", "error": str(e)}]}
    return state

def node_m4(state):
    print("\n--- [M4] SOURCING ---")
    try:
        return clean_state(run_module4(state))
    except Exception as e:
        return {**state, "errors": [{"module": "m4", "error": str(e)}]}

def node_m6(state):
    print("\n--- [M6] FINANCE : TCO ---")
    try:
        return clean_state(calculate_tco_node(state))
    except Exception as e:
        return {**state, "errors": [{"module": "m6", "error": str(e)}]}

def node_m7(state):
    print("\n--- [M7] STRATEGIE : Business Plan ---")
    try:
        res = run_module_7(state)
        return {**state, "business_plan": res}
    except Exception as e:
        return {**state, "errors": [{"module": "m7", "error": str(e)}]}

def node_m8(state):
    print("\n--- [M8] IA PREDICTIVE ---")
    try:
        return clean_state(run_module8(state))
    except Exception as e:
        return {**state, "errors": [{"module": "m8", "error": str(e)}]}

def node_m9(state):
    print("\n--- [M9] LIVRABLE : Catalogue ---")
    try:
        return clean_state(generate_catalog_node(state))
    except Exception as e:
        return {**state, "errors": [{"module": "m9", "error": str(e)}]}

# ===========================================================================
# CONSTRUCTION DU WORKFLOW
# ===========================================================================
def build_graph():
    os.makedirs("outputs", exist_ok=True)
    g = StateGraph(GraphState)

    g.add_node("m1", node_m1)
    g.add_node("m2", node_m2)
    g.add_node("m3", node_m3)
    g.add_node("m4", node_m4)
    g.add_node("m5", lambda state: {**state, "negotiation": {"winner": (state.get("suppliers") or [{}])[0]}})
    g.add_node("m6", node_m6)
    g.add_node("m7", node_m7)
    g.add_node("m8", node_m8)
    g.add_node("m9", node_m9)

    g.set_entry_point("m1")
    g.add_edge("m1", "m2")
    g.add_edge("m2", "m3")
    g.add_edge("m3", "m4")
    g.add_edge("m4", "m5")
    g.add_edge("m5", "m6")
    g.add_edge("m6", "m7")
    g.add_edge("m7", "m8")
    g.add_edge("m8", "m9")
    g.add_edge("m9", END)

    return g.compile()

# ===========================================================================
# POINT D'ENTREE EXPORTE (Crucial pour main.py)
# ===========================================================================
def run_pipeline(pdf_path: str) -> dict:
    """Lance le pipeline complet et renvoie le dictionnaire d'état final."""
    workflow = build_graph()
    initial_input = {
        "pdf_path": pdf_path,
        "logs": [f"Démarrage du pipeline pour {pdf_path}"],
        "errors": [],
        "pipeline_done": False
    }
    # Exécution du graphe
    final_state = workflow.invoke(initial_input)
    return final_state