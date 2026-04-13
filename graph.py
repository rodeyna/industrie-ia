from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Annotated
import operator

# 1. Define the Shared State (The "Briefcase")
class GraphState(TypedDict):
    specs: dict
    cad_path: str
    supplier_data: List[dict]
    tco_results: dict
    final_catalog_path: str
    logs: Annotated[List[str], operator.add] 

# 2. Import your module functions
from modules.module1_extract import extract_specs_node
from modules.module9_catalog import generate_catalog_node
# (Import other modules as you finish them)

# 3. Initialize the Graph
workflow = StateGraph(GraphState)

# 4. Add Nodes
workflow.add_node("extractor", extract_specs_node)
workflow.add_node("publisher", generate_catalog_node)

# 5. Define the Flow (Edges)
workflow.set_entry_point("extractor")

workflow.add_edge("extractor", "publisher")
workflow.add_edge("publisher", END)

# 6. Compile the Graph
app = workflow.compile()