import pandas as pd
import os
from fpdf import FPDF

def run_module_7():
    print("🚀 Module 7: Generating Professional Excel and PDF Reports...")
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # --- 1. DATA (Using the numbers we established) ---
    material = "316 S/S (Inox)"
    qty = 200
    total_cost = 45000.0   # DZD
    revenue = 85000.0      # DZD
    roi = (revenue - total_cost) / total_cost
    van = 12500.45         # Calculated 3-year value

    # --- 2. GENERATE EXCEL ---
    excel_path = os.path.join(current_dir, "Module7_Business_Plan.xlsx")
    df = pd.DataFrame({
        "Metric": ["Material", "Quantity", "Total Cost (TCO)", "Revenue", "ROI", "VAN (3-Year)"],
        "Value": [material, qty, f"{total_cost} DZD", f"{revenue} DZD", f"{roi:.2%}", f"{van} DZD"]
    })
    df.to_excel(excel_path, index=False)
    print(f"✅ Excel Created: {excel_path}")

    # --- 3. GENERATE PDF ---
    pdf_path = os.path.join(current_dir, "Module7_Business_Plan.pdf")
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "INDUSTRIAL BUSINESS PLAN - MODULE 7", ln=True, align='C')
    pdf.ln(10)

    # Financial Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Metric", border=1)
    pdf.cell(90, 10, "Value", border=1, ln=True)
    
    pdf.set_font("Arial", '', 12)
    metrics = [
        ["Material", material],
        ["Quantity", str(qty)],
        ["Total Cost", f"{total_cost} DZD"],
        ["ROI", f"{roi:.2%}"],
        ["VAN (NPV)", f"{van} DZD"]
    ]
    for m in metrics:
        pdf.cell(100, 10, m[0], border=1)
        pdf.cell(90, 10, m[1], border=1, ln=True)

    pdf.ln(10)
    # SWOT Section
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "SWOT Analysis", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, "STRENGTHS: High-grade material choice and local sourcing.\n"
                         "WEAKNESSES: High initial investment (CAPEX).\n"
                         "OPPORTUNITIES: High demand in Algeria's oil & gas sector.\n"
                         "THREATS: Volatility of the DZD/USD exchange rate.")

    pdf.output(pdf_path)
    print(f"✅ PDF Created: {pdf_path}")

if __name__ == "__main__":
    run_module_7()