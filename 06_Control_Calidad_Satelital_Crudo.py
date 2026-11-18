import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ==========================================
# 1. CARGA Y PREPARACIÓN DE DATOS
# ==========================================
ruta_carpeta = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\datos_senamhi"
archivo_excel = "datos_de_los_satelites.xlsx"
ruta_completa = os.path.join(ruta_carpeta, archivo_excel)

print(f"Cargando datos desde: {ruta_completa} ...")
df = pd.read_excel(ruta_completa)

# Limpieza de nombres y tipos
df.columns = df.columns.str.strip()
df["fecha"] = pd.to_datetime(df["fecha"])

for col in ["CHIRPS", "ERA5", "MSWEP"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.sort_values("fecha").reset_index(drop=True)

# Umbral de inconsistencia física
umbral_anomalo = 200.0

# ==========================================
# 2. CONFIGURACIÓN GRÁFICA COMPARATIVA
# ==========================================
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    }
)

fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True, sharey=True)

# Configuración de cada fuente: (Columna, Color, Etiqueta)
fuentes = [
    ("CHIRPS", "#2ca02c", "CHIRPS (Crudo)"),
    ("ERA5", "#ff7f0e", "ERA5 (Crudo)"),
    ("MSWEP", "#1f77b4", "MSWEP (Crudo)"),
]

# Determinar el límite superior común para que la comparación sea en escala real
max_general = max(df["CHIRPS"].max(), df["ERA5"].max(), df["MSWEP"].max())

for i, (col, color, etiqueta) in enumerate(fuentes):
    ax = axes[i]

    # Serie diaria
    ax.plot(
        df["fecha"],
        df[col],
        color=color,
        linewidth=0.55,
        alpha=0.8,
        label=etiqueta,
    )

    # Línea de referencia de 200 mm en todos los paneles
    ax.axhline(
        y=umbral_anomalo,
        color="#d62728",
        linestyle="--",
        linewidth=1.2,
        alpha=0.85,
        label=f"Umbral límite ({umbral_anomalo:.0f} mm)",
    )

    # Resaltado especial en MSWEP para eventos > 200 mm
    if col == "MSWEP":
        anomalias = df[df["MSWEP"] >= umbral_anomalo]
        if not anomalias.empty:
            ax.scatter(
                anomalias["fecha"],
                anomalias["MSWEP"],
                color="#d62728",
                s=40,
                edgecolor="black",
                linewidth=0.6,
                zorder=5,
                label=f"Picos anómalos (n={len(anomalias)})",
            )
        # Sombreado de la franja superior anómala
        ax.axhspan(
            umbral_anomalo,
            max_general * 1.05,
            color="#ffcccc",
            alpha=0.35,
            label="Zona de inconsistencias",
        )

    ax.set_ylabel("P diaria (mm)", fontsize=10, fontweight="bold")
    ax.legend(
        loc="upper right",
        frameon=True,
        facecolor="white",
        framealpha=0.9,
        fontsize=9,
    )
    ax.set_title(
        f"({chr(97 + i)}) Serie temporal diaria: {col}",
        fontsize=11,
        fontweight="bold",
        loc="left",
    )

# Configuración final de ejes
axes[2].set_xlabel("Fecha", fontsize=15, fontweight="bold")
axes[0].set_xlim(df["fecha"].min(), df["fecha"].max())
axes[0].set_ylim(0, max_general * 1.05)

plt.tight_layout()

# ==========================================
# 3. GUARDAR FIGURA
# ==========================================
ruta_salida = os.path.join(ruta_carpeta, "comparacion_series_crudas_3sat.png")
plt.savefig(ruta_salida, dpi=300, bbox_inches="tight")
print(f"Gráfica guardada exitosamente en:\n{ruta_salida}")

plt.show()