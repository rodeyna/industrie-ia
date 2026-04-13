from graph import app

# Initial state - empty because the Mock will fill it
inputs = {"specs": {}, "logs": []}

print("🚀 Starting Pipeline Test...")
config = {"configurable": {"thread_id": "1"}}
result = app.invoke(inputs, config)

print("\n--- TEST SUMMARY ---")
print(f"TCO Calculated: {result['tco_results']['total']} DZD")
print(f"Catalog Path: {result.get('final_catalog_path', 'Not generated')}")
print("✅ Check your 'outputs/' folder for the Excel and PDF!")