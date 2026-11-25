import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTA Y ARCHIVO
# ==============================================================================
RUTA_EXCEL = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo\comparacion_satelites\resultados_correccion_MSWEP\MSWEP_corregido_conchamarca_14976dias_1980_2020.xlsx"
DIR_SALIDA = os.path.dirname(RUTA_EXCEL)
IMG_SALIDA = os.path.join(DIR_SALIDA, "serie_temporal_diaria_MSWEP_crudo_vs_EQM_1980_2020.png")

print(f"Leyendo archivo: {RUTA_EXCEL}")
df = pd.read_excel(RUTA_EXCEL)
df.columns = [str(c).strip() for c in df.columns]

# Estandarizar fecha y tipos numéricos
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)
df["MSWEP"] = pd.to_numeric(df["MSWEP"], errors="coerce")
df["MSWEP_EQM"] = pd.to_numeric(df["MSWEP_EQM"], errors="coerce")

# Métricas descriptivas para las anotaciones
media_crudo = df["MSWEP"].mean()
max_crudo = df["MSWEP"].max()
acum_crudo = df["MSWEP"].sum()

media_eqm = df["MSWEP_EQM"].mean()
max_eqm = df["MSWEP_EQM"].max()
acum_eqm = df["MSWEP_EQM"].sum()

print(f"Total registros: {len(df)} días")
print(f"MSWEP Crudo    -> Media: {media_crudo:.3f} mm/día | Max: {max_crudo:.2f} mm | Acum: {acum_crudo:,.1f} mm")
print(f"MSWEP EQM      -> Media: {media_eqm:.3f} mm/día | Max: {max_eqm:.2f} mm | Acum: {acum_eqm:,.1f} mm")

# ==============================================================================
# 2. GENERACIÓN DEL GRÁFICO (2 PANELES VERTICALES)
# ==============================================================================
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 9), sharex=True, sharey=False)

fig.suptitle(
    "Comparación de la Serie Temporal Diaria de Precipitación (1980–2020)\n"
    "Estación Conchamarca – 14,976 días continuos",
    fontsize=13,
    fontweight="bold",
    y=0.98
)

# ------------------------------------------------------------------------------
# PANEL 1 (SUPERIOR): MSWEP CRUDO (SIN CORREGIR)
# ------------------------------------------------------------------------------
ax1.plot(df["fecha"], df["MSWEP"], color="#c0392b", linewidth=0.6, alpha=0.85, label="MSWEP Crudo (Diario)")
ax1.axhline(media_crudo, color="#78281f", linestyle="--", linewidth=1.2, 
            label=f"Media diaria = {media_crudo:.2f} mm/día")

# Cuadro de texto con estadísticas
texto_panel1 = (
    f"MSWEP Crudo (Sin Corregir)\n"
    f"• Acumulado total: {acum_crudo:,.1f} mm\n"
    f"• Precipitación media: {media_crudo:.2f} mm/día\n"
    f"• Precipitación máxima: {max_crudo:.2f} mm/día"
)
ax1.text(0.015, 0.92, texto_panel1, transform=ax1.transAxes, fontsize=9.5,
         verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#c0392b', alpha=0.9))

ax1.set_ylabel("Precipitación (mm/día)", fontsize=10, fontweight="bold")
ax1.set_title("A) Serie Diaria MSWEP Crudo (Original)", fontsize=11, fontweight="bold", loc="left")
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.legend(loc="upper right", frameon=True, facecolor="white")
ax1.set_ylim(-2, max_crudo * 1.08)

# ------------------------------------------------------------------------------
# PANEL 2 (INFERIOR): MSWEP CORREGIDO (EQM)
# ------------------------------------------------------------------------------
ax2.plot(df["fecha"], df["MSWEP_EQM"], color="#1f618d", linewidth=0.6, alpha=0.85, label="MSWEP EQM Corregido (Diario)")
ax2.axhline(media_eqm, color="#154360", linestyle="--", linewidth=1.2, 
            label=f"Media diaria = {media_eqm:.2f} mm/día")

# Cuadro de texto con estadísticas
texto_panel2 = (
    f"MSWEP Corregido (EQM)\n"
    f"• Acumulado total: {acum_eqm:,.1f} mm (-43.45%)\n"
    f"• Precipitación media: {media_eqm:.2f} mm/día\n"
    f"• Precipitación máxima: {max_eqm:.2f} mm/día"
)
ax2.text(0.015, 0.92, texto_panel2, transform=ax2.transAxes, fontsize=9.5,
         verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#1f618d', alpha=0.9))

ax2.set_ylabel("Precipitación (mm/día)", fontsize=10, fontweight="bold")
ax2.set_title("B) Serie Diaria MSWEP Corregido mediante Empirical Quantile Mapping (EQM)", fontsize=11, fontweight="bold", loc="left")
ax2.grid(True, linestyle="--", alpha=0.5)
ax2.legend(loc="upper right", frameon=True, facecolor="white")
ax2.set_ylim(-1, max_eqm * 1.15)

# Formato temporal del eje X compartido (cada 5 años)
ax2.xaxis.set_major_locator(mdates.YearLocator(5))
ax2.xaxis.set_minor_locator(mdates.YearLocator(1))
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax2.set_xlim(pd.Timestamp("1980-01-01"), pd.Timestamp("2020-12-31"))
ax2.set_xlabel("Año", fontsize=10, fontweight="bold")

plt.tight_layout(rect=[0, 0.02, 1, 0.95])
plt.savefig(IMG_SALIDA, dpi=300)
print(f"\n-> Gráfico guardado exitosamente en:\n   {IMG_SALIDA}")
plt.show()