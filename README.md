       INDUSTRIE IA: Sovereign Industrial Intelligence
OpenIndustry Algeria 

An end-to-end agentic orchestration platform designed to transform raw industrial datasheets into comprehensive project dossiers (Engineering, Finance and Strategy). This system leverages LangGraph to pilot 9 specialized modules in a synchronized workflow.

Architecture Diagram:
The system operates like a digital assembly line where each module enriches a shared "state" (the briefcase).

Data Flow:
1. Ingestion: PDF upload via FastAPI.

2. Orchestration (LangGraph) 
   Technical Branch: Extraction (M1) → CAD Plans (M2) → 3D Rendering (M3).

   Economic Branch: Sourcing (M4) → Negotiation (M5) → TCO Analysis (M6) via World Bank API.

   Strategic Branch: SWOT/Business Plan (M7) → Digital Twin (M8).

3. Output: Final compilation by the Catalog module (M9).

Deployment Guide:
1. Prerequisites: 
 - Python 3.12+
 - Linux environment (recommended for Blender/WeasyPrint) or GitHub Codespaces.

2. Environment Setup:
Clone the repository and install critical dependencies:
# Update pip
pip install --upgrade pip

# Install core libraries
pip install fastapi uvicorn langgraph openpyxl requests python-multipart

# Install document and CAD generators
pip install xhtml2pdf pdfplumber ezdxf jinja2

API Configuration:
Module 6 requires an internet connection to query the World Bank API (api.worldbank.org). No API key is required for public data access.

Execution:
Web Dashboard Mode:
python -m uvicorn main:app --reload

The dashboard will be available at http://localhost:8000.

Terminal Test Mode (Headless):
python test_flight.py

Project Structure:
├── main.py              # Web Server & API
├── graph.py             # LangGraph Brain (Node Logic)
├── modules/             # Source code for modules (M1-M9)
├── templates/           # HTML/CSS for Dashboard & PDF reports
├── outputs/             # Generated industrial assets
└── inputs/              # Storage for uploaded source PDFs