import os
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa 

def generate_catalog_node(state: dict):
    print("\n--- [NODE] Executing Module 9: Catalog Generation ---")

    # path logic (sidebar-aware)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')
    output_path = os.path.join(base_dir, 'outputs', 'catalog.pdf')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # configure Jinja2
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('catalog_report.html')

        context = {
            "specs": state.get("specs", {"component": "Unknown", "material": "N/A"}),
            "tco": state.get("tco_results", {"total": 0}),
            "suppliers": state.get("supplier_data", []),
        }

        rendered_html = template.render(context)

        # PLACE THE PDF GENERATION BLOCK HERE
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_file)

        if pisa_status.err:
            print("❌ Error generating PDF")
        else:
            print(f"✅ Success: Catalog generated at {output_path}")
        
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

    return {"final_catalog_path": output_path, "logs": ["Module 9 complete."]}