def run_module1_extraction(state: dict):
    print("\n--- [NODE] Starting Module 1: Extraction (MODE SOUTENANCE) ---")
    
    # On crée des données techniques réalistes que les autres modules vont utiliser
    mock_specs = {
        "component": "Vanne de Régulation Intelligente V15",
        "material": "Acier Inoxydable 316L / PTFE",
        "power": "2.5 kW",
        "pressure": "16 bar",
        "flow_rate": "120 m3/h",
        "quantity": 50,
        "temperature_max": "180°C"
    }
    
    print("✅ [M1] IA Simulation: Données extraites du PDF avec succès.")
    
    # On met à jour l'état pour que M4, M6, M8 et M9 reçoivent ces infos
    return {
        **state,
        "specs": mock_specs,
        "pdf_specs": mock_specs
    }