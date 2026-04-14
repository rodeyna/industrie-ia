import re
from langchain_ollama import ChatOllama

# ============================================================
# MODULE 5 — AUTONOMOUS AI-VS-AI NEGOTIATION SIMULATOR
# ============================================================

def run_module5_negotiation(state: dict) -> dict:
    """
    LANGGRAPH NODE:
    Takes the specs from State, runs an autonomous negotiation simulation 
    between two AI personas, and outputs the final price to the State.
    """
    print("\n" + "="*50)
    print("🤖 MODULE 5: AUTONOMOUS AI NEGOTIATION STARTED")
    print("="*50)

    # 1. READ FROM THE BOX (STATE)
    specs = state.get("specs", {})
    product = specs.get("product_name", "Industrial Ball Valve")
    quantity = specs.get("quantity", 200)
    
    # 2. SETUP AI AGENTS
    # We use low temperature so they act like serious businessmen
    llm = ChatOllama(model="llama3.2", temperature=0.2, num_ctx=4096)
    
    # Simulation Parameters
    supplier_name = "Global Steel & Valves Co."
    buyer_name = "OpenIndustry Algeria"
    transcript = []

    # 3. THE SIMULATION LOOP (Buyer vs Supplier)
    
    # --- TURN 1: BUYER OPENS ---
    prompt_buyer_1 = f"""
    You are the Procurement Manager for {buyer_name}.
    Write a 1-sentence email to {supplier_name} requesting a quote for {quantity} units of {product}.
    Do not mention a price yet.
    """
    msg1 = llm.invoke(prompt_buyer_1).content.strip()
    transcript.append(f"BUYER: {msg1}")
    print(f"\n🟢 BUYER: {msg1}")

    # --- TURN 2: SUPPLIER QUOTES ---
    prompt_supplier_1 = f"""
    You are the Sales Director at {supplier_name}.
    The buyer said: "{msg1}"
    Write a 1-sentence reply offering a price of 35000 DA per unit. Mention high material costs.
    """
    msg2 = llm.invoke(prompt_supplier_1).content.strip()
    transcript.append(f"SUPPLIER: {msg2}")
    print(f"\n🔴 SUPPLIER: {msg2}")

    # --- TURN 3: BUYER COUNTERS ---
    prompt_buyer_2 = f"""
    You are the Buyer. Your maximum budget is 25000 DA per unit.
    The supplier said: "{msg2}"
    Write a 2-sentence reply. Reject their price, leverage your bulk volume ({quantity} units), and counter-offer exactly 22000 DA.
    """
    msg3 = llm.invoke(prompt_buyer_2).content.strip()
    transcript.append(f"BUYER: {msg3}")
    print(f"\n🟢 BUYER: {msg3}")

    # --- TURN 4: SUPPLIER COUNTERS ---
    prompt_supplier_2 = f"""
    You are the Supplier. Your absolute lowest price floor is 24000 DA.
    The buyer said: "{msg3}"
    Write a 2-sentence reply. Reject 22000 DA, but offer a final compromise of 24500 DA.
    """
    msg4 = llm.invoke(prompt_supplier_2).content.strip()
    transcript.append(f"SUPPLIER: {msg4}")
    print(f"\n🔴 SUPPLIER: {msg4}")

    # --- TURN 5: BUYER CLOSES ---
    prompt_buyer_3 = f"""
    You are the Buyer. The supplier's final offer is: "{msg4}"
    Write a 1-sentence reply officially accepting their final price.
    """
    msg5 = llm.invoke(prompt_buyer_3).content.strip()
    transcript.append(f"BUYER: {msg5}")
    print(f"\n🟢 BUYER: {msg5}")

    # 4. THE EXTRACTION (THE JUDGE)
    # We ask the LLM to read the transcript and extract the final agreed number
    full_chat = "\n".join(transcript)
    extraction_prompt = f"""
    Read this negotiation transcript:
    {full_chat}
    
    What was the final agreed unit price in DA?
    Return ONLY the raw integer number (e.g., 24500). Do not write any words.
    """
    raw_price_str = llm.invoke(extraction_prompt).content.strip()
    
    # Clean the output just in case the AI added words
    nums = re.findall(r'\d+', raw_price_str)
    final_price = int(nums[0]) if nums else 25000

    print("\n" + "="*50)
    print(f"✅ SIMULATION COMPLETE. Final Negotiated Price: {final_price} DA")
    print("="*50)

    # 5. WRITE TO THE BOX (STATE)
    negotiation_data = {
        "unit_price_da": final_price,
        "total_order_value_da": final_price * quantity,
        "currency": "DA",
        "supplier_name": supplier_name,
        "transcript": transcript
    }

    return {**state, "negotiation_data": negotiation_data}


# --- QUICK TEST FOR YOUR LOCAL TERMINAL ---
if __name__ == "__main__":
    # This mocks the data coming from Module 1
    mock_state = {
        "specs": {
            "product_name": "High-Pressure Industrial Valve",
            "quantity": 200
        }
    }
    
    # Run the module
    final_state = run_module5_negotiation(mock_state)
    
    # Show the data that will be passed to Module 6
    print("\n📦 DATA PASSED TO MODULE 6:")
    import json
    print(json.dumps(final_state["negotiation_data"], indent=2))