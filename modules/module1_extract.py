import pdfplumber
import json
import os
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

def extract_specs(pdf_path):
    """
    General-purpose industrial extractor optimized for downstream CAD, 
    Sourcing, and Financial modules.
    """
    print(f"--- [Module 1] Analyzing Technical Document: {pdf_path} ---")
    
    # 1. Robust Text Extraction
    raw_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # We read the first 6 pages (enough for any technical datasheet)
            pages_to_read = pdf.pages[:6]
            for page in pages_to_read:
                text = page.extract_text()
                if text: raw_text += text + "\n"
    except Exception as e:
        return {"error": f"PDF Read Failure: {str(e)}"}

    # 2. Local AI Setup
    llm = ChatOllama(model="llama3.2", temperature=0)

    # 3. THE "GENERAL PURPOSE" PROMPT
    # We tell the AI to map whatever it finds to the roles needed by other modules
    prompt = ChatPromptTemplate.from_template("""
    You are an Industrial Systems Architect. Extract all technical data from this text:
    
    TEXT:
    {text}

    TASK:
    Identify the main product and extract data for the following downstream departments:
    
    1. FOR CAD (Module 2): Extract all physical dimensions. Map them to clear names like 
       'total_length', 'total_height', 'center_to_top', 'flange_diameter'. Use mm if available.
    2. FOR SOURCING (Module 4): Extract specific material grades for every part 
       (Body, Stem, Ball/Disc, Seats, Seals).
    3. FOR FINANCE (Module 6/7): Extract Pressure Class (PN/ASME), Temperature Limits, 
       and Weight.
    4. FOR CATALOG (Module 9): Extract Product Name, Series, and Certifications (ISO, API, EN).

    OUTPUT FORMAT:
    Return ONLY a valid JSON object with these keys:
    - identification: (name, manufacturer, series)
    - bill_of_materials: (part_name: material_grade)
    - mechanical_specs: (pressure_rating, temperature_range, connections_type)
    - cad_dimensions: (A dictionary of all numerical dimensions found)
    - design_standards: (List of API, ISO, or EN standards)
    - manufacturing_notes: (Any tolerances or special instructions)

    If a value is missing, use "Unknown". Return ONLY JSON.
    """)

    # 4. Process with AI
    chain = prompt | llm
    response = chain.invoke({"text": raw_text[:12000]})
    
    # 5. The "Unbreakable" JSON Cleaner
    content = response.content
    match = re.search(r'(\{.*\})', content, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return {"error": "JSON parse failed", "raw": content}
    return {"error": "No data found", "raw": content}

if __name__ == "__main__":
    # This will work with ANY pdf named test.pdf in the folder
    target_pdf = "test.pdf" 
    if os.path.exists(target_pdf):
        final_specs = extract_specs(target_pdf)
        with open("extracted_specs.json", "w") as f:
            json.dump(final_specs, f, indent=4)
        print("✅ Extraction Complete. Data saved to extracted_specs.json")
    else:
        print("❌ Please provide a test.pdf file.")