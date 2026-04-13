"""
INDUSTRIE IA — Module 2 : Génération de plans 2D/3D
====================================================
Sorties attendues (doc) : DXF, DWG, IFC
- Plan 2D complet en DXF (ezdxf)
- Rendu 3D PNG (matplotlib + mpl_toolkits)
- Export IFC simplifié (ifcopenshell si dispo, sinon stub)
- Mise à jour de l'AgentState LangGraph
"""

import os
import json
import math
import logging
from typing import Optional
from datetime import datetime

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment

import numpy as np
import matplotlib
matplotlib.use("Agg")                      # pas de fenêtre GUI — compatible headless
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes par défaut (utilisées si module 1 n'a pas extrait les specs)
# ---------------------------------------------------------------------------
DEFAULT_SPECS = {
    "designation":       "Vanne DN100 PN40",
    "diametre_nominal":  100,      # mm
    "pression_nominale": 40,       # bar
    "longueur":          250,      # mm
    "materiau":          "Stainless Steel 316L",
    "epaisseur_paroi":   8,        # mm
    "nb_boulons":        8,
    "diametre_boulon":   16,       # mm
    "diametre_bride":    220,      # mm
    "hauteur_corps":     160,      # mm
    "diametre_actuateur":60,       # mm
    "hauteur_actuateur": 80,       # mm
    "tolerance":         "±0.1 mm",
    "norme":             "EN 1092-1",
}

OUTPUT_DIR = os.path.join("outputs", "cad")


# ===========================================================================
# HELPERS GÉOMÉTRIQUES
# ===========================================================================

def _cylinder_mesh(cx, cy, cz, radius, height, n=40):
    """Retourne (x, y, z) arrays pour une surface cylindrique."""
    theta = np.linspace(0, 2 * np.pi, n)
    z_bot = np.full_like(theta, cz)
    z_top = np.full_like(theta, cz + height)
    x = cx + radius * np.cos(theta)
    y = cy + radius * np.sin(theta)

    X = np.vstack([x, x])
    Y = np.vstack([y, y])
    Z = np.vstack([z_bot, z_top])
    return X, Y, Z


def _disk_mesh(cx, cy, cz, r_inner, r_outer, n=40):
    """Retourne les faces d'un anneau (bride) pour Poly3DCollection."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    faces = []
    for i in range(n):
        t0, t1 = theta[i], theta[(i + 1) % n]
        p0 = [cx + r_outer * math.cos(t0), cy + r_outer * math.sin(t0), cz]
        p1 = [cx + r_outer * math.cos(t1), cy + r_outer * math.sin(t1), cz]
        p2 = [cx + r_inner * math.cos(t1), cy + r_inner * math.sin(t1), cz]
        p3 = [cx + r_inner * math.cos(t0), cy + r_inner * math.sin(t0), cz]
        faces.append([p0, p1, p2, p3])
    return faces


# ===========================================================================
# PLAN 2D DXF
# ===========================================================================

def generate_dxf(specs: dict, output_path: str) -> str:
    """
    Génère un plan 2D DXF d'une vanne industrielle.
    Vue de face conforme dessin technique :
      - Corps centré, brides latérales, actuateur centré en haut
      - Alésage interne (tirets) limité au corps uniquement
      - Boulons répartis uniformément sur toute la hauteur de bride
      - Axe central traversant, cotations claires, cartouche complet
    """
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4   # millimètres
    ezdxf.setup_linetypes(doc)
    msp = doc.modelspace()

    # --- Calques ---
    doc.layers.add("CORPS",     color=colors.WHITE)
    doc.layers.add("BRIDES",    color=colors.CYAN)
    doc.layers.add("ACTUATEUR", color=colors.YELLOW)
    doc.layers.add("COTES",     color=colors.GREEN)
    doc.layers.add("CARTOUCHE", color=colors.RED)
    doc.layers.add("AXE",       color=colors.MAGENTA)

    # --- Paramètres géométriques ---
    L       = float(specs.get("longueur",          250))
    DN      = float(specs.get("diametre_nominal",  100))
    DB      = float(specs.get("diametre_bride",    220))
    HC      = float(specs.get("hauteur_corps",     160))
    DA      = float(specs.get("diametre_actuateur", 60))
    HA      = float(specs.get("hauteur_actuateur",  80))
    NB      = int(specs.get("nb_boulons",            8))
    DB_bolt = float(specs.get("diametre_boulon",    16))
    ep      = float(specs.get("epaisseur_paroi",     8))

    # Épaisseur bride (vue de face = largeur visible)
    bride_w = max(ep * 3, 30.0)

    # Origine : le corps commence à (ox, oy)
    # On centre verticalement corps + brides par rapport à HC
    # Les brides sont plus hautes (DB > HC) → bride_bot négatif par rapport à corps
    ox = 80.0
    oy = 100.0   # espace sous le dessin pour cotations

    # Y bas et haut du corps
    corps_bot = oy
    corps_top = oy + HC

    # Y bas et haut des brides (DB >= HC, centré sur le corps)
    bride_bot = oy + (HC - DB) / 2.0
    bride_top = bride_bot + DB

    # Centre vertical (axe hydraulique)
    y_axe = oy + HC / 2.0

    # -----------------------------------------------------------------------
    # AXE CENTRAL (ligne chaînette CENTER)
    # -----------------------------------------------------------------------
    axe_ext = 25.0   # dépassement de l'axe à gauche et droite
    msp.add_line(
        (ox - bride_w - axe_ext, y_axe),
        (ox + L + bride_w + axe_ext, y_axe),
        dxfattribs={"layer": "AXE", "linetype": "CENTER", "ltscale": 8}
    )

    # -----------------------------------------------------------------------
    # CORPS (rectangle plein trait fort)
    # -----------------------------------------------------------------------
    msp.add_lwpolyline(
        [(ox, corps_bot), (ox + L, corps_bot),
         (ox + L, corps_top), (ox, corps_top)],
        close=True,
        dxfattribs={"layer": "CORPS", "lineweight": 50}
    )

    # Alésage interne — tirets STRICTEMENT dans le corps (ox → ox+L)
    alez_bot = oy + (HC - DN) / 2.0
    alez_top = oy + (HC + DN) / 2.0
    msp.add_line(
        (ox + 5, alez_bot), (ox + L - 5, alez_bot),
        dxfattribs={"layer": "CORPS", "linetype": "DASHED", "ltscale": 4}
    )
    msp.add_line(
        (ox + 5, alez_top), (ox + L - 5, alez_top),
        dxfattribs={"layer": "CORPS", "linetype": "DASHED", "ltscale": 4}
    )

    # -----------------------------------------------------------------------
    # BRIDES GAUCHE ET DROITE
    # -----------------------------------------------------------------------
    for side in ["left", "right"]:
        if side == "left":
            bx = ox - bride_w
        else:
            bx = ox + L

        # Rectangle bride
        msp.add_lwpolyline(
            [(bx, bride_bot), (bx + bride_w, bride_bot),
             (bx + bride_w, bride_top), (bx, bride_top)],
            close=True,
            dxfattribs={"layer": "BRIDES", "lineweight": 50}
        )

        # Boulons : NB/2 par bride, répartis uniformément sur toute la hauteur DB
        # On place le 1er et dernier boulon à 1.5*DB_bolt du bord
        n_bolts = NB // 2
        margin  = DB_bolt * 2.0
        usable  = DB - 2 * margin
        step    = usable / (n_bolts - 1) if n_bolts > 1 else 0
        bolt_cx = bx + bride_w / 2.0
        for i in range(n_bolts):
            bolt_y = bride_bot + margin + i * step
            msp.add_circle(
                (bolt_cx, bolt_y), DB_bolt / 2.0,
                dxfattribs={"layer": "BRIDES"}
            )

    # -----------------------------------------------------------------------
    # ACTUATEUR (centré sur le corps, posé sur le dessus)
    # -----------------------------------------------------------------------
    act_x  = ox + L / 2.0 - DA / 2.0
    act_y  = corps_top          # base de l'actuateur = haut du corps

    msp.add_lwpolyline(
        [(act_x, act_y),        (act_x + DA, act_y),
         (act_x + DA, act_y + HA), (act_x, act_y + HA)],
        close=True,
        dxfattribs={"layer": "ACTUATEUR", "lineweight": 35}
    )

    # Tige de commande + chapeau rond
    stem_x  = ox + L / 2.0
    stem_h  = HA * 0.3
    stem_r  = DA * 0.12
    msp.add_line(
        (stem_x, act_y + HA),
        (stem_x, act_y + HA + stem_h),
        dxfattribs={"layer": "ACTUATEUR"}
    )
    msp.add_circle(
        (stem_x, act_y + HA + stem_h),
        DA * 0.22,
        dxfattribs={"layer": "ACTUATEUR"}
    )

    # Axe vertical actuateur (CENTER)
    msp.add_line(
        (stem_x, corps_bot - 10),
        (stem_x, act_y + HA + stem_h + DA * 0.3),
        dxfattribs={"layer": "AXE", "linetype": "CENTER", "ltscale": 6}
    )

    # -----------------------------------------------------------------------
    # COTATIONS
    # -----------------------------------------------------------------------
    doc.dimstyles.new("IND",
        dxfattribs={"dimtxt": 5, "dimasz": 4, "dimexe": 2,
                    "dimexo": 3, "dimdli": 8})

    # Longueur corps (en bas)
    cot_y = corps_bot - 40.0
    msp.add_linear_dim(
        base=(ox + L / 2, cot_y),
        p1=(ox, corps_bot),
        p2=(ox + L, corps_bot),
        dimstyle="IND",
        dxfattribs={"layer": "COTES"}
    ).render()

    # Longueur entre brides (en bas, plus bas)
    cot_y2 = corps_bot - 65.0
    msp.add_linear_dim(
        base=(ox + L / 2, cot_y2),
        p1=(ox - bride_w, corps_bot),
        p2=(ox + L + bride_w, corps_bot),
        dimstyle="IND",
        dxfattribs={"layer": "COTES"}
    ).render()

    # Hauteur corps (à droite)
    cot_x = ox + L + bride_w + 50.0
    msp.add_linear_dim(
        base=(cot_x, corps_bot + HC / 2),
        p1=(ox + L + bride_w, corps_bot),
        p2=(ox + L + bride_w, corps_top),
        angle=90,
        dimstyle="IND",
        dxfattribs={"layer": "COTES"}
    ).render()

    # Hauteur bride (à droite, plus à droite)
    cot_x2 = cot_x + 35.0
    msp.add_linear_dim(
        base=(cot_x2, bride_bot + DB / 2),
        p1=(ox + L + bride_w, bride_bot),
        p2=(ox + L + bride_w, bride_top),
        angle=90,
        dimstyle="IND",
        dxfattribs={"layer": "COTES"}
    ).render()

    # DN (diamètre alésage, cotation verticale sur l'alésage)
    cot_x3 = ox - bride_w - 45.0
    msp.add_linear_dim(
        base=(cot_x3, y_axe),
        p1=(ox - bride_w, alez_bot),
        p2=(ox - bride_w, alez_top),
        angle=90,
        dimstyle="IND",
        dxfattribs={"layer": "COTES"}
    ).render()

    # -----------------------------------------------------------------------
    # CARTOUCHE  (en bas à droite, bien séparé du dessin)
    # -----------------------------------------------------------------------
    cw  = 220.0
    ch  = 90.0
    cx0 = ox + L + bride_w + 110.0
    cy0 = corps_bot - ch / 2        # centré verticalement sur le corps

    def add_cart_line(x0, y0, x1, y1):
        msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "CARTOUCHE"})

    def add_cart_text(txt, x, y, h=4.5):
        msp.add_text(txt, dxfattribs={
            "layer": "CARTOUCHE", "height": h,
            "insert": (x, y), "color": colors.RED
        })

    # Bordure extérieure
    msp.add_lwpolyline(
        [(cx0, cy0), (cx0 + cw, cy0),
         (cx0 + cw, cy0 + ch), (cx0, cy0 + ch)],
        close=True,
        dxfattribs={"layer": "CARTOUCHE"}
    )

    # Lignes internes horizontales
    row1 = cy0 + ch * 0.68
    row2 = cy0 + ch * 0.45
    row3 = cy0 + ch * 0.25
    add_cart_line(cx0, row1, cx0 + cw, row1)
    add_cart_line(cx0, row2, cx0 + cw, row2)
    add_cart_line(cx0, row3, cx0 + cw, row3)

    # Ligne verticale milieu (colonne droite)
    mid_x = cx0 + cw * 0.55
    add_cart_line(mid_x, cy0, mid_x, row2)

    # Textes
    designation = specs.get("designation", "Vanne DN100 PN40")
    add_cart_text(designation[:28], cx0 + 5, row1 + 6, h=5.5)

    add_cart_text(
        f"DN{int(specs.get('diametre_nominal',100))} / PN{int(specs.get('pression_nominale',40))} bar",
        cx0 + 5, row2 + 5, h=4.5
    )

    add_cart_text(
        f"Mat.: {specs.get('materiau','Stainless Steel 316L')[:22]}",
        cx0 + 5, row3 + 5, h=4.0
    )
    add_cart_text(
        f"Norme: {specs.get('norme','EN 1092-1')}",
        cx0 + 5, cy0 + 5, h=4.0
    )
    add_cart_text(
        f"Long.: {int(L)} mm",
        mid_x + 5, row3 + 5, h=4.0
    )
    add_cart_text(
        f"Tol.: {specs.get('tolerance','±0.1 mm')}",
        mid_x + 5, cy0 + 5, h=4.0
    )
    add_cart_text(
        f"Date: {datetime.now().strftime('%d/%m/%Y')}",
        cx0 + 5, row2 + 5 - 14, h=3.8
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"[M2] DXF sauvegardé : {output_path}")
    return output_path


# ===========================================================================
# RENDU 3D PNG
# ===========================================================================

def generate_3d_render(specs: dict, output_path: str) -> str:
    """
    Génère un rendu 3D réaliste d'une vanne industrielle en PNG.
    Utilise matplotlib + mpl_toolkits.mplot3d.
    """
    fig = plt.figure(figsize=(10, 8), dpi=150)
    ax  = fig.add_subplot(111, projection="3d")

    L   = specs.get("longueur",           250) / 10  # → cm pour échelle visuelle
    R   = specs.get("diametre_nominal",   100) / 20
    RB  = specs.get("diametre_bride",     220) / 20
    HC  = specs.get("hauteur_corps",      160) / 20
    RA  = specs.get("diametre_actuateur",  60) / 20
    HA  = specs.get("hauteur_actuateur",   80) / 20
    ep  = specs.get("epaisseur_paroi",      8) / 10

    grey_body  = "#9E9E9E"
    grey_bride = "#BDBDBD"
    grey_act   = "#78909C"
    alpha_surf = 0.85

    # --- Corps cylindrique ---
    X, Y, Z = _cylinder_mesh(0, 0, 0, R, HC)
    ax.plot_surface(X, Y, Z, color=grey_body, alpha=alpha_surf,
                   linewidth=0, antialiased=True)

    # Bouchons haut/bas du corps
    for zz in [0, HC]:
        faces = _disk_mesh(0, 0, zz, R * 0.3, R)
        pc = Poly3DCollection(faces, alpha=alpha_surf)
        pc.set_facecolor(grey_body)
        pc.set_edgecolor("none")
        ax.add_collection3d(pc)

    # --- Brides (disques) ---
    for zz in [-ep * 1.5, HC + ep * 1.5]:
        faces = _disk_mesh(0, 0, zz, R, RB)
        pc = Poly3DCollection(faces, alpha=0.9)
        pc.set_facecolor(grey_bride)
        pc.set_edgecolor("#616161")
        pc.set_linewidth(0.3)
        ax.add_collection3d(pc)

    # Trous de boulons sur brides
    NB = specs.get("nb_boulons", 8)
    r_bolt = (RB + R) / 2
    for i in range(NB):
        angle = 2 * math.pi * i / NB
        bx = r_bolt * math.cos(angle)
        by = r_bolt * math.sin(angle)
        for zz in [-ep * 1.5, HC + ep * 1.5]:
            theta = np.linspace(0, 2 * np.pi, 16)
            rb = 0.15
            xs = bx + rb * np.cos(theta)
            ys = by + rb * np.sin(theta)
            ax.plot(xs, ys, zz, color="#424242", linewidth=0.8, zorder=5)

    # --- Actuateur ---
    Xa, Ya, Za = _cylinder_mesh(0, 0, HC, RA, HA)
    ax.plot_surface(Xa, Ya, Za, color=grey_act, alpha=alpha_surf,
                   linewidth=0, antialiased=True)

    # Capuchon actuateur
    faces_cap = _disk_mesh(0, 0, HC + HA, 0, RA)
    pc_cap = Poly3DCollection(faces_cap, alpha=0.95)
    pc_cap.set_facecolor(grey_act)
    pc_cap.set_edgecolor("none")
    ax.add_collection3d(pc_cap)

    # --- Tige de commande ---
    stem_r = RA * 0.18
    Xs, Ys, Zs = _cylinder_mesh(0, 0, HC + HA, stem_r, HA * 0.35)
    ax.plot_surface(Xs, Ys, Zs, color="#37474F", alpha=1.0,
                   linewidth=0, antialiased=True)

    # --- Axes et mise en forme ---
    ax.set_xlabel("X (cm)", fontsize=8, labelpad=5)
    ax.set_ylabel("Y (cm)", fontsize=8, labelpad=5)
    ax.set_zlabel("Z (cm)", fontsize=8, labelpad=5)

    margin = max(RB, L / 2) * 1.3
    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    ax.set_zlim(-2, HC + HA + 3)

    ax.view_init(elev=25, azim=45)
    ax.set_facecolor("#F0F0F0")
    fig.patch.set_facecolor("#FAFAFA")

    # Titre et légende
    title = (f"{specs.get('designation','Vanne industrielle')}\n"
             f"DN{specs.get('diametre_nominal',100)} / PN{specs.get('pression_nominale',40)} — "
             f"{specs.get('materiau','316L')}")
    ax.set_title(title, fontsize=10, pad=12, fontweight="bold", color="#212121")

    legend_elements = [
        mpatches.Patch(facecolor=grey_body,  label="Corps"),
        mpatches.Patch(facecolor=grey_bride, label="Brides"),
        mpatches.Patch(facecolor=grey_act,   label="Actuateur"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=8)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"[M2] Rendu 3D sauvegardé : {output_path}")
    return output_path


# ===========================================================================
# EXPORT IFC (stub complet si ifcopenshell absent)
# ===========================================================================

def generate_ifc(specs: dict, output_path: str) -> str:
    """
    Génère un fichier IFC minimal décrivant la vanne.
    Utilise ifcopenshell si disponible, sinon écrit un IFC texte valide.
    """
    try:
        import ifcopenshell
        import ifcopenshell.api

        model = ifcopenshell.file(schema="IFC4")
        project = ifcopenshell.api.run("root.create_entity", model,
                                       ifc_class="IfcProject",
                                       name="INDUSTRIE IA")
        site = ifcopenshell.api.run("root.create_entity", model,
                                    ifc_class="IfcSite",
                                    name="Site Algérie")
        product = ifcopenshell.api.run("root.create_entity", model,
                                       ifc_class="IfcFlowFitting",
                                       name=specs.get("designation", "Vanne DN100"))

        model.write(output_path)
        logger.info(f"[M2] IFC (ifcopenshell) sauvegardé : {output_path}")

    except ImportError:
        # Stub IFC valide (STEP format)
        ifc_content = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('INDUSTRIE IA - Vanne industrielle'),'2;1');
FILE_NAME('{os.path.basename(output_path)}','{datetime.now().isoformat()}',('INDUSTRIE IA'),('OpenIndustry Algerie'),'','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('1hqIFCProject00',#2,'INDUSTRIE IA',$,$,$,$,(#20),#7);
#2=IFCOWNERHISTORY(#3,#6,$,.ADDED.,$,$,$,0);
#3=IFCPERSONANDORGANIZATION(#4,#5,$);
#4=IFCPERSON($,'INDUSTRIE','IA',$,$,$,$,$);
#5=IFCORGANIZATION($,'OpenIndustry Algerie',$,$,$);
#6=IFCAPPLICATION(#5,'1.0','INDUSTRIE IA Pipeline','IndustrieIA');
#7=IFCUNITASSIGNMENT((#8,#9,#10));
#8=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#9=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#10=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#20=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#21,$);
#21=IFCAXIS2PLACEMENT3D(#22,$,$);
#22=IFCCARTESIANPOINT((0.,0.,0.));
#30=IFCFLOWFITTING('2hqIFCValve000',#2,
  '{specs.get("designation","Vanne DN100 PN40")}','Vanne industrielle haute pression',
  'DN{specs.get("diametre_nominal",100)}/PN{specs.get("pression_nominale",40)}',$,$,$,$);
#31=IFCPROPERTYSINGLEVALUE('NominalDiameter',$,
  IFCLENGTHMEASURE({specs.get("diametre_nominal",100)}.0),$);
#32=IFCPROPERTYSINGLEVALUE('NominalPressure',$,
  IFCPRESSUREMEASURE({specs.get("pression_nominale",40) * 100000}.0),$);
#33=IFCPROPERTYSINGLEVALUE('Material',$,
  IFCLABEL('{specs.get("materiau","Stainless Steel 316L")}'),$);
#34=IFCPROPERTYSINGLEVALUE('Length',$,
  IFCLENGTHMEASURE({specs.get("longueur",250)}.0),$);
#35=IFCPROPERTYSET('3hqIFCPSet000',#2,'Pset_ValveTypeCommon',$,(#31,#32,#33,#34));
ENDSEC;
END-ISO-10303-21;
"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ifc_content)
        logger.info(f"[M2] IFC (stub) sauvegardé : {output_path}")

    return output_path


# ===========================================================================
# NŒUD LANGGRAPH
# ===========================================================================

def run_module2(state: dict) -> dict:
    """
    Nœud LangGraph — Module 2.
    Entrée  : state["pdf_specs"] (dict issu du module 1)
    Sortie  : state enrichi avec dxf_path, png_path, ifc_path, viewer_url
    """
    logger.info("[M2] Démarrage génération plans...")

    specs = state.get("pdf_specs", DEFAULT_SPECS)
    if not specs:
        logger.warning("[M2] pdf_specs absent, utilisation des specs par défaut.")
        specs = DEFAULT_SPECS

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Noms de fichiers basés sur la désignation
    safe_name = specs.get("designation", "vanne").replace(" ", "_").replace("/", "-")

    dxf_path   = os.path.join(OUTPUT_DIR, f"{safe_name}.dxf")
    png_path   = os.path.join(OUTPUT_DIR, f"{safe_name}_3d.png")
    ifc_path   = os.path.join(OUTPUT_DIR, f"{safe_name}.ifc")
    specs_path = os.path.join(OUTPUT_DIR, f"{safe_name}_specs.json")

    # Génération des 3 formats
    generate_dxf(specs, dxf_path)
    generate_3d_render(specs, png_path)
    generate_ifc(specs, ifc_path)

    # Sauvegarder les specs utilisées (traçabilité)
    with open(specs_path, "w", encoding="utf-8") as f:
        json.dump(specs, f, indent=2, ensure_ascii=False)

    result = {
        **state,
        "dxf_path":    dxf_path,
        "png_path":    png_path,
        "ifc_path":    ifc_path,
        "specs_path":  specs_path,
        "viewer_url":  "http://localhost:8000/view/plan",
        "module2_ok":  True,
    }

    logger.info(f"[M2] Terminé — DXF:{dxf_path} | PNG:{png_path} | IFC:{ifc_path}")
    return result


# ===========================================================================
# EXÉCUTION DIRECTE (test standalone)
# ===========================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    print("=" * 60)
    print("  INDUSTRIE IA — Module 2 : Génération Plans")
    print("=" * 60)

    # Simuler un state LangGraph entrant
    test_state = {
        "pdf_specs": {
            "designation":       "Vanne_DN100_PN40",
            "diametre_nominal":  100,
            "pression_nominale": 40,
            "longueur":          250,
            "materiau":          "Stainless Steel 316L",
            "epaisseur_paroi":   8,
            "nb_boulons":        8,
            "diametre_boulon":   16,
            "diametre_bride":    220,
            "hauteur_corps":     160,
            "diametre_actuateur":60,
            "hauteur_actuateur": 80,
            "tolerance":         "±0.1 mm",
            "norme":             "EN 1092-1",
        }
    }

    result = run_module2(test_state)

    print("\n Résultats générés :")
    print(f"   DXF  → {result['dxf_path']}")
    print(f"   PNG  → {result['png_path']}")
    print(f"   IFC  → {result['ifc_path']}")
    print(f"   JSON → {result['specs_path']}")
    print(f"\n Viewer : {result['viewer_url']}")
    print("\nLancer 'python main.py' puis ouvrir l'URL ci-dessus pour visualiser.")
