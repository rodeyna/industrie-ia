"""
INDUSTRIE IA — Module 3 : Rendu Ultra-Premium (V3.4)
====================================================
MODIFICATION : Ligne de scan dynamique sur TOUTE la zone de texte.
"""

import os
import math
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import animation

logger = logging.getLogger(__name__)

# --- CONFIGURATION STYLE ---
OUTPUT_DIR = os.path.join("outputs", "cad")
TOTAL_FRAMES = 200 
FPS = 30
CYAN = "#00E5FF"
GOLD = "#FFD700" # La couleur de la ligne de scan
BG_DARK = "#050508"

def _draw_industrial_masterpiece(ax, frame_idx, specs):
    """Génère la scène 3D avec mise à l'échelle dynamique."""
    dn = float(specs.get("diametre_nominal", 100))
    scale = dn / 100.0
    body_r, flange_r, h = 2.0 * scale, 3.8 * scale, 5.0 * scale
    
    color_body = (0.33, 0.43, 0.48, 0.9)
    color_flange = (0.81, 0.85, 0.86, 0.8)
    color_safety = (0.72, 0.11, 0.11, 1.0)

    u, v = np.mgrid[0:2*np.pi:30j, 0:np.pi:15j]
    x, y, z = body_r * np.cos(u) * np.sin(v), body_r * np.sin(u) * np.sin(v), (h/2) * np.cos(v) + (h/2)
    ax.plot_surface(x, y, z, color=color_body, antialiased=True, linewidth=0)

    theta = np.linspace(0, 2*np.pi, 40)
    for p_z in [0.15 * h, 0.85 * h]:
        ax.plot(flange_r * np.cos(theta), flange_r * np.sin(theta), p_z, color=color_flange, lw=2)

    ax.plot([0, 0], [0, 0], [h, h + 3.5*scale], color=(0.2, 0.3, 0.3), lw=5)
    wheel_theta = np.linspace(0, 2*np.pi, 50)
    ax.plot(2.5*scale * np.cos(wheel_theta), 2.5*scale * np.sin(wheel_theta), h + 3.5*scale, color=color_safety, lw=7)
    
    grid_range = np.linspace(-12*scale, 12*scale, 12)
    gx, gy = np.meshgrid(grid_range, grid_range)
    ax.plot_wireframe(gx, gy, np.zeros_like(gx), color=CYAN, alpha=0.1, lw=0.5)

    zoom = 13 * scale + 1.2 * math.sin(frame_idx / 25)
    ax.set_xlim(-zoom, zoom); ax.set_ylim(-zoom, zoom); ax.set_zlim(0, zoom*1.2)
    ax.axis('off')
    ax.view_init(elev=22 + 3 * math.cos(frame_idx / 40), azim=frame_idx * 2.2)

def generate_video(specs, output_path):
    fig = plt.figure(figsize=(19.2, 10.8), facecolor=BG_DARK)
    gs = gridspec.GridSpec(1, 2, width_ratios=[2.4, 1], figure=fig)
    ax3d = fig.add_subplot(gs[0], projection='3d', facecolor=BG_DARK)
    ax_hud = fig.add_subplot(gs[1], facecolor=BG_DARK)

    def update(i):
        ax3d.clear()
        _draw_industrial_masterpiece(ax3d, i, specs)
        ax_hud.clear()
        ax_hud.axis('off')
        
        # --- HUD TEXTE ---
        chars_to_show = i // 2
        title_text = ">> DIGITAL TWIN ANALYZER v3.4"
        ax_hud.text(0, 0.95, title_text[:chars_to_show], color=CYAN, fontsize=14, fontweight='bold', family='monospace')
        
        y_pos_start = 0.80
        info_data = [
            ("MODEL", specs.get('designation', 'VALVE_ALPHA')),
            ("NOMINAL DIAM.", f"DN{specs.get('diametre_nominal', '100')}"),
            ("PRESSURE", f"PN{specs.get('pression_nominale', '40')}"),
            ("MATERIAL", specs.get('materiau', 'STEEL').upper()),
            ("CERTIF.", "ISO 9001 / EN 1092")
        ]
        
        for j, (label, value) in enumerate(info_data):
            delay = 15 + (j * 12)
            y_current = y_pos_start - (j * 0.10)
            if i > delay:
                show_len = (i - delay) // 2
                ax_hud.text(0, y_current, label, color=CYAN, fontsize=8, alpha=0.6, family='monospace')
                cursor = "_" if (i // 5) % 2 == 0 else " "
                ax_hud.text(0, y_current-0.035, value[:show_len] + cursor, color="white", fontsize=12, fontweight='bold', family='monospace')

        # --- LIGNE DE SCAN DYNAMIQUE (FULL RANGE) ---
        # Elle parcourt de y=0.98 à y=0.05
        scan_y = 0.5 + 0.45 * math.sin(i / 15) # Mouvement sinusoïdal sur tout le HUD
        ax_hud.axhline(scan_y, color=GOLD, lw=1.5, alpha=0.4)
        
        # Petit indicateur de scan à côté de la ligne
        ax_hud.text(0.8, scan_y + 0.01, "SCAN", color=GOLD, fontsize=7, family='monospace', alpha=0.6)

        if (i // 15) % 2 == 0:
            ax_hud.text(0, 0.05, "SYSTEM STATUS: ACTIVE", color=CYAN, fontsize=9, family='monospace', alpha=0.5)

    writer = animation.FFMpegWriter(fps=FPS, codec="libx264", extra_args=['-pix_fmt', 'yuv420p', '-crf', '18'])
    anim = animation.FuncAnimation(fig, update, frames=TOTAL_FRAMES)
    anim.save(output_path, writer=writer)
    plt.close()

def run_module3(state):
    logger.info("🎬 Génération du rendu avec scan dynamique intégral...")
    specs = state.get("pdf_specs", {"designation": "Industrial Valve Alpha", "diametre_nominal": 100})
    path = os.path.join(OUTPUT_DIR, f"DigitalTwin_DynamicScan.mp4")
    generate_video(specs, path)
    return {**state, "mp4_path": path, "module3_ok": True}

if __name__ == "__main__":
    run_module3({})
