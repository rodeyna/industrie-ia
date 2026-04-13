from modules.module9_catalog import generate_catalog_node
import os

# 1. Create a fake "state" like LangGraph would provide
mock_state = {
    "specs": {
        "component": "Industrial Ball Valve",
        "material": "Stainless Steel 316L",
        "diameter_mm": "100",
        "pressure_bar": "40"
    },
    "tco_results": {
        "total": "2,450,000"
    },
    "supplier_data": [
        {"name": "SteelCorp Algeria", "price": "5000 DZD"},
        {"name": "Global Valves Ltd", "price": "4500 DZD"}
    ],
    "logs": []
}

if __name__ == "__main__":
    print("🚀 Starting Module 9 Isolated Test...")
    
    # Run the node function directly
    result = generate_catalog_node(mock_state)
    
    # Check if the file was created
    pdf_path = result.get("final_catalog_path")
    if os.path.exists(pdf_path):
        print(f"✨ SUCCESS! PDF created at: {pdf_path}")
        print(f"📁 Check your 'outputs' folder in the sidebar.")
    else:
        print("❌ FAILED: PDF was not found in the outputs folder.")