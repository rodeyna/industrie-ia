from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
import operator

# Define the Shared State (The "Briefcase")
class GraphState(TypedDict):
    specs: dict
    cad_path: str
    supplier_data: List[dict]
    tco_results: dict
    final_catalog_path: str
    logs: Annotated[List[str], operator.add] 

# --- MOCK NODE (Replaces the incomplete Module 1) ---
def mock_extract_node(state: GraphState):
    print("\n--- [MOCK] Injecting Industrial Specs for Testing ---")
    return {
        "specs": {
            "component": "Industrial Ball Valve",
            "material": "Stainless Steel 316L",
            "pressure_bar": 40,
            "diameter_mm": 100,
            "base_price": 550000
        },
        "logs": ["Mock: Manual specs injected successfully."]
    }

# Import working modules
# from modules.module1_extract import extract_specs_node # <-- Skip this for now
from modules.module6_tco import calculate_tco_node  
from modules.module9_catalog import generate_catalog_node

# Initialize the Graph
workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("extractor", mock_extract_node) # <--- Point to the Mock
workflow.add_node("calculator", calculate_tco_node) 
workflow.add_node("publisher", generate_catalog_node)

# DEFINE THE FLOW
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "calculator")   
workflow.add_edge("calculator", "publisher")  
workflow.add_edge("publisher", END)

# Compile the graph
app = workflow.compile()