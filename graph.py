from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Annotated
import operator

# ── The State Box — combines everyone's keys ──
class GraphState(TypedDict):
    # Input
    pdf_path:           str
    # M1 output
    specs:              Optional[dict]
    # M4 output  
    suppliers:          Optional[List[dict]]
    supplier_data:      Optional[List[dict]]  
    # M6 output
    tco:                Optional[dict]
    tco_results:        Optional[dict]       
    # M8 output
    digital_twin:       Optional[dict]
    # M9 output
    catalog_paths:      Optional[dict]
    final_catalog_path: Optional[str]
    # Stubs for modules not ready yet
    cad_path:           Optional[str]
    video_path:         Optional[str]
    negotiation:        Optional[dict]
    business_plan:      Optional[dict]
    # Logs
    logs:               Annotated[List[str], operator.add]
    errors:             Optional[list]

# ── Import working modules ──
from modules.module1_extract   import run_module1_extraction
from modules.module4_sourcing  import run_module4
from modules.module6_tco       import run_module6
from modules.module8_digital_twin import run_module8
from modules.module9_catalog   import run_module9

# ── Stubs for modules not ready yet ──
def run_module2(state):
    print("[M2] Skipped — not ready yet")
    return {**state, "cad_path": None}

def run_module3(state):
    print("[M3] Skipped — not ready yet")
    return {**state, "video_path": None}

def run_module5(state):
    print("[M5] Skipped — picking cheapest supplier")
    suppliers = state.get("suppliers") or state.get("supplier_data") or []
    best = min(suppliers, key=lambda x: x.get("Price_DA", 999999)) if suppliers else {}
    return {**state, "negotiation": {"winner": best, "final_price": best.get("Price_DA", 50000)}}

def run_module7(state):
    print("[M7] Skipped — not ready yet")
    return {**state, "business_plan": {"status": "pending"}}

# ── Error wrapper ──
def safe(fn):
    def wrapper(state):
        try:
            return fn(state)
        except Exception as e:
            errors = state.get("errors") or []
            errors.append({"module": fn.__name__, "error": str(e)})
            print(f"[ERROR] {fn.__name__}: {e}")
            return {**state, "errors": errors}
    return wrapper

# ── Build the graph ──
def build_graph():
    g = StateGraph(GraphState)

    g.add_node("m1", safe(run_module1_extraction))
    g.add_node("m2", safe(run_module2))
    g.add_node("m3", safe(run_module3))
    g.add_node("m4", safe(run_module4))
    g.add_node("m5", safe(run_module5))
    g.add_node("m6", safe(run_module6))
    g.add_node("m7", safe(run_module7))
    g.add_node("m8", safe(run_module8))
    g.add_node("m9", safe(run_module9))

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

def run_pipeline(pdf_path: str) -> dict:
    graph = build_graph()
    return graph.invoke({
        "pdf_path":           pdf_path,
        "specs":              None,
        "suppliers":          None,
        "supplier_data":      None,
        "tco":                None,
        "tco_results":        None,
        "digital_twin":       None,
        "catalog_paths":      None,
        "final_catalog_path": None,
        "cad_path":           None,
        "video_path":         None,
        "negotiation":        None,
        "business_plan":      None,
        "logs":               [],
        "errors":             [],
    })