"""
INDUSTRIE IA — Module 8 : Jumeau Numérique & Maintenance Prédictive
====================================================================
Sorties attendues (doc) : JSON, 3D
- Simulation de capteurs industriels (pression, temp, vibrations, débit)
- Modèle de maintenance prédictive (anomalie, RUL, alertes)
- Export JSON complet + graphes PNG
- Dashboard HTML standalone
- Mise à jour de l'AgentState LangGraph
"""

import os
import json
import math
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
import matplotlib.colors as mcolors

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join("outputs", "jumeau")

DEFAULT_SPECS = {
    "designation":       "Vanne DN100 PN40",
    "diametre_nominal":  100,
    "pression_nominale": 40,
    "materiau":          "Stainless Steel 316L",
    "longueur":          250,
}

# ===========================================================================
# PARAMÈTRES DE SIMULATION
# ===========================================================================

SIMULATION_HOURS = 720          # 30 jours de données
SAMPLE_RATE_MIN  = 15           # une mesure toutes les 15 min
N_POINTS         = SIMULATION_HOURS * 60 // SAMPLE_RATE_MIN   # 2880 points


# ===========================================================================
# SIMULATION DES CAPTEURS
# ===========================================================================

def simulate_sensor_data(specs: dict, seed: int = 42) -> dict:
    """
    Génère des données de capteurs réalistes pour la vanne.
    Inclut des dégradations progressives et des anomalies.
    """
    rng = np.random.default_rng(seed)
    t   = np.linspace(0, SIMULATION_HOURS, N_POINTS)

    pn  = specs.get("pression_nominale", 40)
    dn  = specs.get("diametre_nominal",  100)

    # --- PRESSION (bar) ---
    # Tendance de base + cycle diurne + bruit + dérive progressive
    pression_base  = pn * 0.85
    cycle_diurne_p = pn * 0.08 * np.sin(2 * np.pi * t / 24)
    bruit_p        = rng.normal(0, pn * 0.02, N_POINTS)
    derive_p       = np.linspace(0, pn * 0.05, N_POINTS)   # légère hausse sur 30j
    # Pics de surpression (événements aléatoires)
    pics_p         = np.zeros(N_POINTS)
    for _ in range(12):
        idx = rng.integers(100, N_POINTS - 100)
        pics_p[idx:idx+3] = pn * rng.uniform(0.15, 0.35)

    pression = pression_base + cycle_diurne_p + bruit_p + derive_p + pics_p
    pression = np.clip(pression, 0, pn * 1.5)

    # --- TEMPÉRATURE (°C) ---
    temp_base   = 45.0
    cycle_temp  = 8.0 * np.sin(2 * np.pi * t / 24 - math.pi / 4)
    bruit_temp  = rng.normal(0, 1.2, N_POINTS)
    derive_temp = np.linspace(0, 6.0, N_POINTS)           # échauffement sur 30j
    temperature = temp_base + cycle_temp + bruit_temp + derive_temp

    # --- VIBRATIONS (mm/s RMS) ---
    vib_base    = 1.8
    bruit_vib   = rng.exponential(0.4, N_POINTS)
    # Anomalie vibratoire à partir de j20 (dégradation roulement)
    t_defaut    = SIMULATION_HOURS * 20 / 30
    derive_vib  = np.where(t > t_defaut,
                           (t - t_defaut) * 0.15, 0)
    vibrations  = vib_base + bruit_vib + derive_vib
    # Pics bruyants
    for _ in range(8):
        idx = rng.integers(50, N_POINTS - 50)
        vibrations[idx:idx+2] += rng.uniform(2, 6)
    vibrations = np.clip(vibrations, 0, 20)

    # --- DÉBIT (m³/h) ---
    debit_nominal = math.pi * (dn / 2000) ** 2 * 3.0 * 3600   # v≈3 m/s
    bruit_debit   = rng.normal(0, debit_nominal * 0.03, N_POINTS)
    cycle_debit   = debit_nominal * 0.12 * np.sin(2 * np.pi * t / 24 + math.pi / 6)
    # Chute de débit progressive (encrassement progressif j15→j30)
    t_encras      = SIMULATION_HOURS * 15 / 30
    derive_debit  = np.where(t > t_encras,
                             -(t - t_encras) * 0.008 * debit_nominal, 0)
    debit         = debit_nominal + cycle_debit + bruit_debit + derive_debit
    debit         = np.clip(debit, 0, debit_nominal * 1.3)

    # --- HEURES DE FONCTIONNEMENT cumulées ---
    heures_cumul  = t.copy()   # identique au temps simulé

    # --- TIMESTAMPS ---
    ts_start = datetime.now() - timedelta(hours=SIMULATION_HOURS)
    timestamps = [
        (ts_start + timedelta(minutes=i * SAMPLE_RATE_MIN)).isoformat()
        for i in range(N_POINTS)
    ]

    return {
        "n_points":      N_POINTS,
        "metadata": {
            "equipement":    specs.get("designation", "Vanne DN100"),
            "periode_debut": timestamps[0],
            "periode_fin":   timestamps[-1],
            "n_points":      N_POINTS,
            "intervalle_min": SAMPLE_RATE_MIN,
            "unite_pression": "bar",
            "unite_temp":     "°C",
            "unite_vib":      "mm/s RMS",
            "unite_debit":    "m³/h",
        },
        "timestamps":    timestamps,
        "pression":      pression.tolist(),
        "temperature":   temperature.tolist(),
        "vibrations":    vibrations.tolist(),
        "debit":         debit.tolist(),
        "heures_cumul":  heures_cumul.tolist(),
        "pression_nominale": pn,
        "debit_nominal":     debit_nominal,
    }


# ===========================================================================
# MODÈLE DE MAINTENANCE PRÉDICTIVE
# ===========================================================================

def compute_health_index(sensor_data: dict) -> np.ndarray:
    """
    Calcule un indice de santé (0-100) basé sur plusieurs indicateurs.
    100 = parfait état  /  0 = défaillance imminente
    """
    n   = sensor_data["n_points"]
    pn  = sensor_data["pression_nominale"]
    dn_debit = sensor_data["debit_nominal"]

    p   = np.array(sensor_data["pression"])
    t   = np.array(sensor_data["temperature"])
    v   = np.array(sensor_data["vibrations"])
    d   = np.array(sensor_data["debit"])
    h   = np.array(sensor_data["heures_cumul"])

    # Score pression (dégradation si > 90% PN ou < 70% PN)
    p_norm   = np.where(p > pn * 0.9, 100 * (pn * 1.5 - p) / (pn * 0.6),
               np.where(p < pn * 0.7, 70.0, 100.0))
    p_score  = np.clip(p_norm, 0, 100)

    # Score température (optimal 20-60°C, critique > 80°C)
    t_score  = np.where(t < 60, 100,
               np.where(t < 80, 100 - (t - 60) * 3,
               np.where(t < 100, 40, 0)))
    t_score  = np.clip(t_score, 0, 100)

    # Score vibrations (ISO 10816 : < 2.3 bon, 2.3-4.5 acceptable, > 4.5 alarme)
    v_score  = np.where(v < 2.3, 100,
               np.where(v < 4.5, 100 - (v - 2.3) * 20,
               np.where(v < 7.1, 60 - (v - 4.5) * 10,
               0)))
    v_score  = np.clip(v_score, 0, 100)

    # Score débit (perte > 10% = problème)
    d_ratio  = d / dn_debit
    d_score  = np.where(d_ratio > 0.95, 100,
               np.where(d_ratio > 0.80, 100 - (0.95 - d_ratio) * 400,
               np.where(d_ratio > 0.60, 40, 0)))
    d_score  = np.clip(d_score, 0, 100)

    # Score usure (courbe de Weibull simplifiée)
    h_max    = SIMULATION_HOURS * 5   # durée de vie nominale estimée
    usure    = (h / h_max) ** 2.5
    h_score  = np.clip(100 * (1 - usure), 0, 100)

    # Indice global (pondéré)
    health   = (0.25 * p_score +
                0.20 * t_score +
                0.30 * v_score +
                0.15 * d_score +
                0.10 * h_score)

    # Lissage (fenêtre glissante 12 points = 3h)
    kernel   = np.ones(12) / 12
    health   = np.convolve(health, kernel, mode="same")

    return np.clip(health, 0, 100)


def detect_anomalies(sensor_data: dict, health: np.ndarray) -> list:
    """
    Détecte et classe les anomalies par sévérité.
    Retourne une liste d'événements avec timestamp et description.
    """
    pn    = sensor_data["pression_nominale"]
    p     = np.array(sensor_data["pression"])
    t_arr = np.array(sensor_data["temperature"])
    v     = np.array(sensor_data["vibrations"])
    d     = np.array(sensor_data["debit"])
    ts    = sensor_data["timestamps"]

    anomalies = []

    # Seuils
    thresholds = {
        "pression_haute":  pn * 1.1,
        "pression_basse":  pn * 0.6,
        "temperature_haute": 75.0,
        "vibration_haute": 4.5,
        "debit_bas":       sensor_data["debit_nominal"] * 0.82,
        "sante_critique":  40.0,
        "sante_alerte":    65.0,
    }

    def add_anomaly(idx, level, type_, description, valeur, seuil, unite):
        anomalies.append({
            "timestamp":   ts[idx],
            "index":       int(idx),
            "niveau":      level,           # CRITIQUE / ALERTE / AVERTISSEMENT
            "type":        type_,
            "description": description,
            "valeur":      round(float(valeur), 3),
            "seuil":       round(float(seuil), 3),
            "unite":       unite,
        })

    # Scan des capteurs (on évite les doublons avec un cooldown de 20 points)
    cooldowns = {}
    for i in range(N_POINTS):
        cd = cooldowns.get

        if p[i] > thresholds["pression_haute"] and i - cooldowns.get("ph", -30) > 20:
            add_anomaly(i, "CRITIQUE", "SURPRESSION",
                        f"Pression {p[i]:.1f} bar > seuil {thresholds['pression_haute']:.1f} bar",
                        p[i], thresholds["pression_haute"], "bar")
            cooldowns["ph"] = i

        elif p[i] < thresholds["pression_basse"] and i - cooldowns.get("pl", -30) > 20:
            add_anomaly(i, "ALERTE", "SOUS-PRESSION",
                        f"Pression {p[i]:.1f} bar < seuil {thresholds['pression_basse']:.1f} bar",
                        p[i], thresholds["pression_basse"], "bar")
            cooldowns["pl"] = i

        if t_arr[i] > thresholds["temperature_haute"] and i - cooldowns.get("th", -30) > 20:
            add_anomaly(i, "ALERTE", "SURCHAUFFE",
                        f"Température {t_arr[i]:.1f}°C > seuil {thresholds['temperature_haute']}°C",
                        t_arr[i], thresholds["temperature_haute"], "°C")
            cooldowns["th"] = i

        if v[i] > thresholds["vibration_haute"] and i - cooldowns.get("vh", -30) > 20:
            niv = "CRITIQUE" if v[i] > 7.1 else "ALERTE"
            add_anomaly(i, niv, "VIBRATION_EXCESSIVE",
                        f"Vibrations {v[i]:.2f} mm/s > ISO 10816 seuil {thresholds['vibration_haute']} mm/s",
                        v[i], thresholds["vibration_haute"], "mm/s")
            cooldowns["vh"] = i

        if d[i] < thresholds["debit_bas"] and i - cooldowns.get("dl", -30) > 20:
            add_anomaly(i, "AVERTISSEMENT", "CHUTE_DEBIT",
                        f"Débit {d[i]:.3f} m³/h < seuil {thresholds['debit_bas']:.3f} m³/h",
                        d[i], thresholds["debit_bas"], "m³/h")
            cooldowns["dl"] = i

        if health[i] < thresholds["sante_critique"] and i - cooldowns.get("hc", -30) > 20:
            add_anomaly(i, "CRITIQUE", "SANTE_CRITIQUE",
                        f"Indice de santé {health[i]:.1f} < seuil critique {thresholds['sante_critique']}",
                        health[i], thresholds["sante_critique"], "%")
            cooldowns["hc"] = i
        elif health[i] < thresholds["sante_alerte"] and i - cooldowns.get("ha", -30) > 20:
            add_anomaly(i, "ALERTE", "SANTE_DEGRADEE",
                        f"Indice de santé {health[i]:.1f} < seuil alerte {thresholds['sante_alerte']}",
                        health[i], thresholds["sante_alerte"], "%")
            cooldowns["ha"] = i

    return sorted(anomalies, key=lambda x: x["timestamp"])


def estimate_rul(health: np.ndarray) -> dict:
    """
    Estime le Remaining Useful Life (RUL) en heures.
    Utilise une régression linéaire sur la tendance de l'indice de santé.
    """
    n = len(health)
    # Fenêtre des 25% derniers points pour estimer la tendance récente
    window = max(50, n // 4)
    recent = health[-window:]
    x      = np.arange(window)

    # Régression linéaire
    coeffs = np.polyfit(x, recent, 1)
    slope  = coeffs[0]   # dégradation par point

    current_health = float(health[-1])
    threshold_maint = 60.0   # intervention préventive à 60%
    threshold_crit  = 30.0   # remplacement critique à 30%

    if slope >= 0:
        # Santé stable ou améliorée
        return {
            "rul_heures_maintenance": 9999,
            "rul_heures_critique":    9999,
            "sante_actuelle":         round(current_health, 1),
            "tendance_par_heure":     round(slope * (60 / SAMPLE_RATE_MIN), 4),
            "recommandation":         "Equipement en bon état — surveillance standard",
            "priorite":               "BASSE",
        }

    # Points restants jusqu'au seuil
    pts_maintenance = max(0, (current_health - threshold_maint) / abs(slope))
    pts_critique    = max(0, (current_health - threshold_crit)  / abs(slope))

    rul_maint_h = pts_maintenance * SAMPLE_RATE_MIN / 60
    rul_crit_h  = pts_critique    * SAMPLE_RATE_MIN / 60

    if rul_maint_h < 24 * 7:    # < 1 semaine
        priorite = "CRITIQUE"
        recommandation = (f"INTERVENTION URGENTE dans {rul_maint_h:.0f}h — "
                          "vérification joints, roulements et corps de vanne")
    elif rul_maint_h < 24 * 30:  # < 1 mois
        priorite = "HAUTE"
        recommandation = (f"Maintenance préventive planifier sous {rul_maint_h:.0f}h — "
                          "inspection complète recommandée")
    elif rul_maint_h < 24 * 90:  # < 3 mois
        priorite = "MOYENNE"
        recommandation = (f"Planifier maintenance dans {rul_maint_h:.0f}h — "
                          "augmenter fréquence de surveillance")
    else:
        priorite = "BASSE"
        recommandation = "Equipement en bon état — surveillance standard"

    return {
        "rul_heures_maintenance": round(rul_maint_h, 1),
        "rul_heures_critique":    round(rul_crit_h, 1),
        "sante_actuelle":         round(current_health, 1),
        "tendance_par_heure":     round(slope * (60 / SAMPLE_RATE_MIN), 4),
        "recommandation":         recommandation,
        "priorite":               priorite,
    }


def compute_statistics(sensor_data: dict) -> dict:
    """Statistiques descriptives pour chaque capteur."""
    stats = {}
    for key in ["pression", "temperature", "vibrations", "debit"]:
        arr = np.array(sensor_data[key])
        stats[key] = {
            "min":    round(float(arr.min()), 3),
            "max":    round(float(arr.max()), 3),
            "mean":   round(float(arr.mean()), 3),
            "std":    round(float(arr.std()), 3),
            "p95":    round(float(np.percentile(arr, 95)), 3),
            "p99":    round(float(np.percentile(arr, 99)), 3),
        }
    return stats


# ===========================================================================
# GÉNÉRATION GRAPHES PNG
# ===========================================================================

def generate_dashboard_png(sensor_data: dict,
                             health: np.ndarray,
                             anomalies: list,
                             rul: dict,
                             output_path: str) -> str:
    """Génère le dashboard de monitoring en PNG."""
    n  = sensor_data["n_points"]
    t  = np.arange(n) * SAMPLE_RATE_MIN / 60    # heures

    fig = plt.figure(figsize=(20, 14), dpi=120)
    fig.patch.set_facecolor("#0D1117")

    gs = gridspec.GridSpec(3, 3, figure=fig,
                           hspace=0.45, wspace=0.35,
                           top=0.93, bottom=0.06,
                           left=0.06, right=0.97)

    dark_bg    = "#0D1117"
    panel_bg   = "#161B22"
    text_color = "#E6EDF3"
    grid_color = "#21262D"

    def style_ax(ax, title, ylabel, color):
        ax.set_facecolor(panel_bg)
        ax.set_title(title, color=text_color, fontsize=9, pad=5, fontweight="bold")
        ax.set_ylabel(ylabel, color=text_color, fontsize=7)
        ax.set_xlabel("Heures", color=text_color, fontsize=7)
        ax.tick_params(colors=text_color, labelsize=6)
        ax.grid(True, color=grid_color, linewidth=0.5, alpha=0.8)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363D")
        return ax

    # 1. Pression
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(t, sensor_data["pression"], color="#58A6FF", linewidth=0.7, alpha=0.9)
    pn = sensor_data["pression_nominale"]
    ax1.axhline(pn * 1.1, color="#F85149", linewidth=1, linestyle="--", alpha=0.8, label=f"Seuil critique {pn*1.1:.0f} bar")
    ax1.axhline(pn * 0.6, color="#E3B341", linewidth=1, linestyle="--", alpha=0.8, label=f"Seuil bas {pn*0.6:.0f} bar")
    ax1.legend(fontsize=6, facecolor=panel_bg, labelcolor=text_color, loc="upper right")
    style_ax(ax1, "Pression (bar)", "bar", "#58A6FF")

    # 2. Température
    ax2 = fig.add_subplot(gs[0, 1])
    temps_arr = np.array(sensor_data["temperature"])
    ax2.plot(t, temps_arr, color="#F0883E", linewidth=0.7, alpha=0.9)
    ax2.axhline(75, color="#F85149", linewidth=1, linestyle="--", alpha=0.8)
    ax2.fill_between(t, temps_arr, 75, where=temps_arr > 75,
                     color="#F85149", alpha=0.25)
    style_ax(ax2, "Température (°C)", "°C", "#F0883E")

    # 3. Vibrations
    ax3 = fig.add_subplot(gs[0, 2])
    vib = np.array(sensor_data["vibrations"])
    ax3.plot(t, vib, color="#BC8CFF", linewidth=0.7, alpha=0.9)
    ax3.axhline(4.5, color="#E3B341", linewidth=1, linestyle="--", alpha=0.8, label="ISO 10816 alerte")
    ax3.axhline(7.1, color="#F85149", linewidth=1, linestyle="--", alpha=0.8, label="ISO 10816 critique")
    ax3.legend(fontsize=6, facecolor=panel_bg, labelcolor=text_color)
    style_ax(ax3, "Vibrations (mm/s RMS)", "mm/s", "#BC8CFF")

    # 4. Débit
    ax4 = fig.add_subplot(gs[1, 0])
    d   = np.array(sensor_data["debit"])
    ax4.plot(t, d, color="#3FB950", linewidth=0.7, alpha=0.9)
    ax4.axhline(sensor_data["debit_nominal"], color="#58A6FF",
                linewidth=1, linestyle=":", alpha=0.7, label="Débit nominal")
    ax4.legend(fontsize=6, facecolor=panel_bg, labelcolor=text_color)
    style_ax(ax4, "Débit (m³/h)", "m³/h", "#3FB950")

    # 5. Indice de santé
    ax5 = fig.add_subplot(gs[1, 1])
    cmap = plt.get_cmap("RdYlGn")
    health_norm = health / 100
    for i in range(0, n - 1, 5):
        ax5.plot(t[i:i+6], health[i:i+6],
                 color=cmap(health_norm[i]), linewidth=1.5)
    ax5.axhline(60, color="#E3B341", linewidth=1, linestyle="--", alpha=0.8, label="Seuil maint. 60%")
    ax5.axhline(30, color="#F85149", linewidth=1, linestyle="--", alpha=0.8, label="Seuil critique 30%")
    ax5.set_ylim(0, 105)
    ax5.legend(fontsize=6, facecolor=panel_bg, labelcolor=text_color)
    style_ax(ax5, "Indice de santé (%)", "%", "#FFFFFF")

    # 6. Histogramme anomalies par type
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(panel_bg)
    if anomalies:
        types_count = {}
        for a in anomalies:
            k = a["type"]
            types_count[k] = types_count.get(k, 0) + 1
        colors_bar = {
            "CRITIQUE":  "#F85149",
            "ALERTE":    "#E3B341",
            "AVERTISSEMENT": "#58A6FF"
        }
        labels  = list(types_count.keys())
        values  = list(types_count.values())
        bar_clrs= [colors_bar.get(a["niveau"], "#8B949E")
                   for a in anomalies
                   if a["type"] in labels][:len(labels)]
        bars = ax6.barh(labels, values, color=bar_clrs, edgecolor="none")
        for bar, v in zip(bars, values):
            ax6.text(v + 0.1, bar.get_y() + bar.get_height() / 2,
                     str(v), va="center", ha="left",
                     color=text_color, fontsize=7)
    ax6.set_title("Anomalies par type", color=text_color, fontsize=9,
                  pad=5, fontweight="bold")
    ax6.tick_params(colors=text_color, labelsize=6)
    ax6.set_facecolor(panel_bg)
    for spine in ax6.spines.values():
        spine.set_edgecolor("#30363D")

    # 7. Carte RUL (texte)
    ax7 = fig.add_subplot(gs[2, :2])
    ax7.set_facecolor(panel_bg)
    ax7.axis("off")

    rul_color = {"CRITIQUE": "#F85149", "HAUTE": "#E3B341",
                 "MOYENNE": "#58A6FF", "BASSE": "#3FB950"}.get(rul["priorite"], "#8B949E")

    ax7.text(0.01, 0.92, "ANALYSE RUL — Remaining Useful Life",
             transform=ax7.transAxes, fontsize=10,
             fontweight="bold", color=text_color, va="top")
    ax7.text(0.01, 0.72,
             f"Santé actuelle : {rul['sante_actuelle']}%   |   "
             f"Tendance : {rul['tendance_par_heure']:+.4f}%/h",
             transform=ax7.transAxes, fontsize=9, color="#8B949E", va="top")
    ax7.text(0.01, 0.52,
             f"RUL maintenance : {rul['rul_heures_maintenance']:.0f}h   |   "
             f"RUL critique : {rul['rul_heures_critique']:.0f}h",
             transform=ax7.transAxes, fontsize=9, color="#58A6FF", va="top")
    ax7.text(0.01, 0.30, rul["recommandation"],
             transform=ax7.transAxes, fontsize=9,
             color=rul_color, va="top", fontweight="bold")
    ax7.text(0.01, 0.10,
             f"Priorité : {rul['priorite']}",
             transform=ax7.transAxes, fontsize=10,
             fontweight="bold", color=rul_color, va="top")

    for spine in ax7.spines.values():
        spine.set_edgecolor("#30363D")

    # 8. Dernières alertes
    ax8 = fig.add_subplot(gs[2, 2])
    ax8.set_facecolor(panel_bg)
    ax8.axis("off")
    ax8.text(0.05, 0.95, "Dernières alertes",
             transform=ax8.transAxes, fontsize=9,
             fontweight="bold", color=text_color, va="top")

    crit_alerts = [a for a in anomalies if a["niveau"] == "CRITIQUE"][-5:]
    for i, a in enumerate(reversed(crit_alerts)):
        y = 0.80 - i * 0.15
        clr = {"CRITIQUE": "#F85149", "ALERTE": "#E3B341"}.get(a["niveau"], "#58A6FF")
        ax8.text(0.05, y, f"[{a['niveau']}] {a['type']}",
                 transform=ax8.transAxes, fontsize=7,
                 fontweight="bold", color=clr, va="top")
        ax8.text(0.05, y - 0.07,
                 f"{a['timestamp'][:16]} — {a['valeur']} {a['unite']}",
                 transform=ax8.transAxes, fontsize=6,
                 color="#8B949E", va="top")
    for spine in ax8.spines.values():
        spine.set_edgecolor("#30363D")

    # Titre global
    fig.suptitle(
        f"JUMEAU NUMÉRIQUE — {sensor_data['metadata']['equipement']}  "
        f"|  {N_POINTS} points  |  30 jours",
        color=text_color, fontsize=13, fontweight="bold", y=0.98
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"[M8] Dashboard PNG sauvegardé : {output_path}")
    return output_path


# ===========================================================================
# EXPORT HTML DASHBOARD STANDALONE
# ===========================================================================

def generate_html_dashboard(sensor_data: dict,
                              health: np.ndarray,
                              anomalies: list,
                              rul: dict,
                              stats: dict,
                              output_path: str) -> str:
    """Génère un dashboard HTML standalone avec Chart.js."""

    # Sous-échantillonner pour le HTML (1 point sur 6 = toutes les 1h30)
    step = 6
    t_h  = [round(i * SAMPLE_RATE_MIN / 60, 2) for i in range(0, N_POINTS, step)]
    p_s  = [round(v, 2) for v in sensor_data["pression"][::step]]
    tp_s = [round(v, 2) for v in sensor_data["temperature"][::step]]
    vb_s = [round(v, 2) for v in sensor_data["vibrations"][::step]]
    db_s = [round(v, 2) for v in sensor_data["debit"][::step]]
    hl_s = [round(v, 1) for v in health[::step].tolist()]

    rul_color = {"CRITIQUE": "#F85149", "HAUTE": "#E3B341",
                 "MOYENNE": "#58A6FF", "BASSE": "#3FB950"}.get(rul["priorite"], "#8B949E")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Jumeau Numérique — {sensor_data['metadata']['equipement']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0D1117; color: #E6EDF3; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
  h1 {{ font-size: 1.3rem; font-weight: 600; margin-bottom: 4px; }}
  .subtitle {{ color: #8B949E; font-size: 0.85rem; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
  .card {{ background: #161B22; border: 1px solid #21262D; border-radius: 8px; padding: 16px; }}
  .metric {{ font-size: 1.8rem; font-weight: 700; }}
  .label {{ font-size: 0.75rem; color: #8B949E; margin-top: 4px; }}
  .chart-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; }}
  canvas {{ max-height: 200px; }}
  .alert-list {{ max-height: 280px; overflow-y: auto; }}
  .alert {{ padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-size: 0.8rem; }}
  .alert.CRITIQUE  {{ background: rgba(248,81,73,0.15); border-left: 3px solid #F85149; }}
  .alert.ALERTE    {{ background: rgba(227,179,65,0.15); border-left: 3px solid #E3B341; }}
  .alert.AVERTISSEMENT {{ background: rgba(88,166,255,0.15); border-left: 3px solid #58A6FF; }}
  .badge {{ display:inline-block; padding: 2px 8px; border-radius: 4px; font-size:0.7rem; font-weight:700; }}
  .badge.CRITIQUE  {{ background:#F85149; color:#fff; }}
  .badge.ALERTE    {{ background:#E3B341; color:#0D1117; }}
  .badge.AVERTISSEMENT {{ background:#58A6FF; color:#0D1117; }}
  .rul-box {{ background: #161B22; border: 1px solid #21262D; border-radius: 8px; padding: 20px; }}
  .rul-title {{ font-size: 1rem; font-weight: 600; margin-bottom: 12px; }}
  .rul-value {{ font-size: 2rem; font-weight: 700; color: {rul_color}; }}
</style>
</head>
<body>
<h1>JUMEAU NUMERIQUE — {sensor_data['metadata']['equipement']}</h1>
<div class="subtitle">
  Periode : {sensor_data['metadata']['periode_debut'][:10]} → {sensor_data['metadata']['periode_fin'][:10]}
  &nbsp;|&nbsp; {N_POINTS} points de mesure &nbsp;|&nbsp; Intervalle : {SAMPLE_RATE_MIN} min
</div>

<!-- Metriques KPI -->
<div class="grid">
  <div class="card">
    <div class="metric" style="color:#3FB950">{rul['sante_actuelle']}%</div>
    <div class="label">Indice de sante</div>
  </div>
  <div class="card">
    <div class="metric" style="color:{rul_color}">{int(rul['rul_heures_maintenance'])}h</div>
    <div class="label">RUL maintenance</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#E3B341">{len([a for a in anomalies if a['niveau']=='CRITIQUE'])}</div>
    <div class="label">Alertes critiques</div>
  </div>
  <div class="card">
    <div class="metric" style="color:#58A6FF">{len(anomalies)}</div>
    <div class="label">Total evenements</div>
  </div>
</div>

<!-- Graphes capteurs -->
<div class="chart-grid">
  <div class="card"><canvas id="chartP"></canvas></div>
  <div class="card"><canvas id="chartT"></canvas></div>
  <div class="card"><canvas id="chartV"></canvas></div>
  <div class="card"><canvas id="chartH"></canvas></div>
</div>

<!-- RUL + Alertes -->
<div style="display:grid;grid-template-columns:1fr 2fr;gap:12px">
  <div class="rul-box">
    <div class="rul-title">Analyse RUL</div>
    <div class="rul-value">{rul['priorite']}</div>
    <p style="margin-top:10px;font-size:0.82rem;color:#8B949E;">{rul['recommandation']}</p>
  </div>
  <div class="card">
    <h3 style="margin-bottom:12px;font-size:0.9rem;">Derniers evenements ({len(anomalies)} total)</h3>
    <div class="alert-list">
"""
    for a in reversed(anomalies[-30:]):
        html += f"""      <div class="alert {a['niveau']}">
        <span class="badge {a['niveau']}">{a['niveau']}</span>
        <strong style="margin-left:8px">{a['type']}</strong>
        <span style="color:#8B949E;font-size:0.75rem;margin-left:8px">{a['timestamp'][:16]}</span>
        <div style="color:#8B949E;margin-top:2px">{a['description']}</div>
      </div>
"""

    labels_json   = json.dumps(t_h)
    pression_json = json.dumps(p_s)
    temp_json     = json.dumps(tp_s)
    vib_json      = json.dumps(vb_s)
    health_json   = json.dumps(hl_s)
    pn            = sensor_data["pression_nominale"]

    html += f"""    </div>
  </div>
</div>

<script>
const labels = {labels_json};
const cfg = (label, data, color, seuils=[]) => ({{
  type:'line',
  data:{{ labels, datasets:[
    {{ label, data, borderColor:color, borderWidth:1.5,
      pointRadius:0, fill:false, tension:0.3 }},
    ...seuils.map(s=>({{ label:s.label, data:labels.map(()=>s.val),
      borderColor:s.color, borderWidth:1, borderDash:[4,4],
      pointRadius:0, fill:false }}))
  ]}},
  options:{{ responsive:true, animation:false,
    plugins:{{legend:{{labels:{{color:'#8B949E',font:{{size:10}}}}}}}},
    scales:{{
      x:{{ticks:{{color:'#8B949E',font:{{size:9}},maxTicksLimit:8}},grid:{{color:'#21262D'}}}},
      y:{{ticks:{{color:'#8B949E',font:{{size:9}}}},grid:{{color:'#21262D'}}}}
    }}
  }}
}});

new Chart(document.getElementById('chartP'), cfg('Pression (bar)', {pression_json}, '#58A6FF',
  [{{label:'Seuil haut',val:{pn*1.1},color:'#F85149'}},{{label:'Seuil bas',val:{pn*0.6},color:'#E3B341'}}]));
new Chart(document.getElementById('chartT'), cfg('Temperature (°C)', {temp_json}, '#F0883E',
  [{{label:'Seuil 75°C',val:75,color:'#F85149'}}]));
new Chart(document.getElementById('chartV'), cfg('Vibrations (mm/s)', {vib_json}, '#BC8CFF',
  [{{label:'ISO alerte',val:4.5,color:'#E3B341'}},{{label:'ISO critique',val:7.1,color:'#F85149'}}]));
new Chart(document.getElementById('chartH'), cfg('Sante (%)', {health_json}, '#3FB950',
  [{{label:'Seuil maint',val:60,color:'#E3B341'}},{{label:'Seuil crit',val:30,color:'#F85149'}}]));
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"[M8] Dashboard HTML sauvegardé : {output_path}")
    return output_path


# ===========================================================================
# NŒUD LANGGRAPH
# ===========================================================================

def run_module8(state: dict) -> dict:
    """
    Nœud LangGraph — Module 8.
    Entrée  : state["pdf_specs"] (pour calibrer les seuils sur les specs réelles)
    Sortie  : state enrichi avec sensor_json, dashboard_png, dashboard_html, rul
    """
    logger.info("[M8] Démarrage jumeau numérique...")

    specs = state.get("pdf_specs", DEFAULT_SPECS)
    if not specs:
        specs = DEFAULT_SPECS
        logger.warning("[M8] pdf_specs absent — utilisation des specs par défaut.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = specs.get("designation", "vanne").replace(" ", "_").replace("/", "-")

    # Chemins de sortie
    json_path  = os.path.join(OUTPUT_DIR, f"{safe_name}_sensor_data.json")
    png_path   = os.path.join(OUTPUT_DIR, f"{safe_name}_dashboard.png")
    html_path  = os.path.join(OUTPUT_DIR, f"{safe_name}_dashboard.html")
    rul_path   = os.path.join(OUTPUT_DIR, f"{safe_name}_rul.json")

    # Pipeline analytique
    sensor_data = simulate_sensor_data(specs)
    health      = compute_health_index(sensor_data)
    anomalies   = detect_anomalies(sensor_data, health)
    rul         = estimate_rul(health)
    stats       = compute_statistics(sensor_data)

    # Enrichir sensor_data avec résultats d'analyse
    sensor_data["health_index"]       = health.tolist()
    sensor_data["anomalies"]          = anomalies
    sensor_data["statistiques"]       = stats
    sensor_data["rul"]                = rul
    sensor_data["n_anomalies"]        = len(anomalies)
    sensor_data["n_anomalies_crit"]   = len([a for a in anomalies if a["niveau"] == "CRITIQUE"])
    sensor_data["metadata"]["generated_at"] = datetime.now().isoformat()

    # Sauvegardes
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sensor_data, f, indent=2, ensure_ascii=False)

    with open(rul_path, "w", encoding="utf-8") as f:
        json.dump(rul, f, indent=2, ensure_ascii=False)

    generate_dashboard_png(sensor_data, health, anomalies, rul, png_path)
    generate_html_dashboard(sensor_data, health, anomalies, rul, stats, html_path)

    result = {
        **state,
        "sensor_json":    json_path,
        "dashboard_png":  png_path,
        "dashboard_html": html_path,
        "rul_json":       rul_path,
        "rul":            rul,
        "n_anomalies":    len(anomalies),
        "module8_ok":     True,
    }

    logger.info(
        f"[M8] Terminé — {len(anomalies)} anomalies | "
        f"Santé: {rul['sante_actuelle']}% | RUL: {rul['rul_heures_maintenance']}h"
    )
    return result


# ===========================================================================
# EXÉCUTION DIRECTE
# ===========================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    print("=" * 60)
    print("  INDUSTRIE IA — Module 8 : Jumeau Numérique")
    print("=" * 60)

    test_state = {
        "pdf_specs": {
            "designation":       "Vanne_DN100_PN40",
            "diametre_nominal":  100,
            "pression_nominale": 40,
            "materiau":          "Stainless Steel 316L",
            "longueur":          250,
        }
    }

    result = run_module8(test_state)

    print("\n Résultats générés :")
    print(f"   JSON capteurs → {result['sensor_json']}")
    print(f"   Dashboard PNG → {result['dashboard_png']}")
    print(f"   Dashboard HTML→ {result['dashboard_html']}")
    print(f"   RUL JSON      → {result['rul_json']}")
    print(f"\n Analyse :")
    rul = result["rul"]
    print(f"   Santé actuelle : {rul['sante_actuelle']}%")
    print(f"   RUL maintenance : {rul['rul_heures_maintenance']}h")
    print(f"   Priorité : {rul['priorite']}")
    print(f"   {rul['recommandation']}")
    print(f"   Anomalies détectées : {result['n_anomalies']}")
    print(f"\n Ouvrir {result['dashboard_html']} dans un navigateur pour le dashboard interactif.")
