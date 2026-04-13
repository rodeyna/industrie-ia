import os
import json
import pandas as pd # For Excel

def calculate_roi(revenue, cost):
    if cost == 0: return 0
    return (revenue - cost) / cost

def calculate_van(initial_investment, cash_flow, rate=0.1):
    van = -initial_investment
    for year in range(1, 4):
        van += cash_flow / ((1 + rate) ** year)
    return van

def generate_swot_prompt(material, quantity, cost):
    return f"""
    SWOT Analysis for {quantity} valves ({material}).
    Total Cost: {cost} DZD.
    1. Strengths: High quality material.
    2. Weaknesses: Initial setup cost.
    3. Opportunities: Industrial growth in Algeria.
    4. Threats: Material price fluctuation.
    """

def run_module_7(shared_state=None):
    print("🚀 Module 7: Generating Final Business Plan...")

    # --- MOCK DATA (Update these 4 lines when friends are done) ---
    material_name = "Inox 316L"
    valves_count = 200
    cost_from_module6 = 45000.0  # TCO
    revenue_estimate = 85000.0
    # --------------------------------------------------------------

    # 1. MATH CALCULATIONS
    roi = calculate_roi(revenue_estimate, cost_from_module6)
    van = calculate_van(cost_from_module6, 20000.0) # Assume 20k profit/year
    swot_text = generate_swot_prompt(material_name, valves_count, cost_from_module6)

    # 2. CREATE EXCEL REPORT (Using Pandas)
    report_data = {
        "Metric": ["Material", "Quantity", "Total Cost (TCO)", "Estimated Revenue", "ROI", "VAN (3-Year)"],
        "Value": [material_name, valves_count, cost_from_module6, revenue_estimate, f"{roi:.2%}", f"{van:,.2f}"]
    }
    df = pd.DataFrame(report_data)
    excel_file = "Business_Plan_Calculations.xlsx"
    df.to_excel(excel_file, index=False)
    print(f"📊 Excel Report Created: {excel_file}")

    # 3. CREATE PDF TEXT (Summary)
    pdf_content = f"""
    INDUSTRIAL BUSINESS PLAN
    -------------------------
    Project: {valves_count} Industrial Valves
    Material: {material_name}
    
    FINANCIAL SUMMARY:
    ROI: {roi:.2%}
    VAN: {van:,.2f} DZD
    
    {swot_text}
    """
    
    # Save a text version of the PDF content for the jury
    with open("Business_Plan_Summary.txt", "w") as f:
        f.write(pdf_content)
    print("📄 Business Plan Summary (Text version) Created.")

    return {
        "status": "Success",
        "roi": roi,
        "excel_path": excel_file
    }

if __name__ == "__main__":
    run_module_7()