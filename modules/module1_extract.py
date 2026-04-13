import pdfplumber
import json
import os
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

def extract_specs(pdf_path):
    """
    Core Logic: Reads the technical PDF and uses Llama 3.2 to extract 
    highly detailed industrial specifications.
    """
    print(f"--- Detailed Technical Audit Started: {pdf_path} ---")
    
    raw_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Analyze the first 4 pages to capture all technical data
            for page in pdf.pages[:4]:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"
    except Exception as e:
        return {"error": f"Failed to read PDF: {str(e)}"}

    # Initialize Local LLM (Llama 3.2)
    llm = ChatOllama(model="llama3.2", temperature=0)

    # Master Engineering Prompt
    prompt = ChatPromptTemplate.from_template("""
    SYSTEM: You are a Senior Mechanical Engineer. Extract a HIGH-PRECISION technical profile from the following text.
    
    TEXT: {text}

    Return ONLY a single valid JSON object. Do not include any other text.
    
    REQUIRED STRUCTURE:
    {{
      "identity": {{
        "brand": "Manufacturer name",
        "series": "Model/Series number",
        "valve_type": "Full technical description"
      }},
      "materials": {{
        "body_stainless_steel": "Grade (e.g. ASTM A351-CF8M)",
        "body_carbon_steel": "Grade (e.g. ASTM A216-WCC)",
        "ball_stem": "Material code (e.g. UNS S31600)",
        "seats": "Seat material (e.g. PTFE/Carbon reinforced)"
      }},
      "ratings": {{
        "pressure_class": "e.g. ASME Class 800",
        "max_temperature": "Maximum operating temp",
        "fire_safe": "Certification status"
      }},
      "selected_model_specs": {{
        "dn_size": 50,
        "nps_size": "2 inch",
        "dimensions_mm": {{
          "H": "Value",
          "G": "Value",
          "C": "Value",
          "D": "Value",
          "F": "Value",
          "K": "Value"
        }},
        "mass_kg": 4.8
      }},
      "compliance": ["List all standards found: NACE, API 608, API 607, ISO, etc."]
    }}
    """)

    chain = prompt | llm
    print("--- AI is analyzing technical tables... ---")
    response = chain.invoke({"text": raw_text})
    
    # Cleaning the output to extract JSON from any conversational text
    content = response.content
    match = re.search(r'(\{.*\})', content, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except Exception:
            return {"error": "JSON Parse Error", "raw": json_str}
    
    return {"error": "No JSON detected", "raw": content}

# --- LANGGRAPH NODE INTEGRATION (Following The Rule) ---

def run_module1_extraction(state: dict) -> dict:
    """
    Pattern: run_moduleX(state) -> state
    This function is what the LangGraph orchestrator will call.
    """
    print("\n--- [NODE] Starting Module 1: Extraction ---")
    
    # STEP 1 — Read what you need from the box
    # In this case, we need the file path of the PDF
    pdf_path = state.get("pdf_path", "test.pdf")
    
    # STEP 2 — Do your work
    extracted_specs = extract_specs(pdf_path)
    
    # STEP 3 — Return the FULL box + your new thing
    # We add the 'specs' key to the state for all other modules to use
    return {**state, "specs": extracted_specs}

# --- TEST BLOCK ---
if __name__ == "__main__":
    file_path = "test.pdf" 
    if os.path.exists(file_path):
        # We simulate the graph by creating an initial state dictionary
        initial_state = {"pdf_path": file_path}
        
        # Run the node
        final_state = run_module1_extraction(initial_state)
        
        # Save output for reference
        with open("specs.json", "w") as f:
            json.dump(final_state["specs"], f, indent=4)
            
        print("\n--- EXTRACTION COMPLETE ---")
        print(json.dumps(final_state["specs"], indent=2))
    else:
        print(f"Error: {file_path} not found.")