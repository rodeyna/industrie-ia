import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

def generate_catalog_node(state: dict):
    print("\n--- [NODE] Executing Module 9: Catalog Generation ---")

    base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "templates")
    output_path  = os.path.join(base_dir, "outputs", "catalog.pdf")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        env      = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("catalog_report.html")

        context = {
            "specs":        state.get("specs",        {"component": "Unknown", "material": "N/A"}),
            "tco":          state.get("tco_results")  or state.get("tco",          {"total": 0}),
            "suppliers":    state.get("supplier_data") or state.get("suppliers",   []),
            "digital_twin": state.get("digital_twin", {}),
        }

        rendered_html = template.render(context)
        HTML(string=rendered_html).write_pdf(output_path)
        print(f"✅ Catalog PDF generated at {output_path}")

    except Exception as e:
        print(f"❌ Exception in M9: {str(e)}")

    return {
        **state,
        "catalog_paths":      {"pdf": output_path},
        "final_catalog_path": output_path
    }

# alias so graph.py can import it
run_module9 = generate_catalog_node