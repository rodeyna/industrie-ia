
import pdfplumber
import json
import os
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

def extract_specs(pdf_path):
    print(f"--- Reading PDF: {pdf_path} ---")
    raw_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text: raw_text += text + "\n"
    except Exception as e:
        return {"error": f"Failed to read PDF: {str(e)}"}

    llm = ChatOllama(model="llama3.2", temperature=0)

    prompt = ChatPromptTemplate.from_template("""
    Extract technical specs from this text: {text}
    Return exactly ONE JSON object. If there are multiple sections, nest them inside one root object.
    """)

    chain = prompt | llm
    response = chain.invoke({"text": raw_text[:8000]})
    
    # --- UPDATED SMART CLEANER ---
    # This finds every {} block and merges them into one
    content = response.content
    json_blocks = re.findall(r'(\{.*?\})', content, re.DOTALL)
    
    final_data = {}
    if json_blocks:
        for block in json_blocks:
            try:
                # Load each block and merge it into the main dictionary
                data = json.loads(block)
                final_data.update(data)
            except:
                continue
        return final_data
    
    return {"error": "No JSON found", "raw": content}

if __name__ == "__main__":
    test_pdf = "test.pdf" 
    if os.path.exists(test_pdf):
        results = extract_specs(test_pdf)
        print(json.dumps(results, indent=2))
    else:
        print(f"File {test_pdf} not found.")