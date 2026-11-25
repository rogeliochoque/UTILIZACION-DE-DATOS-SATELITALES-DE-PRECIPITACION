import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# 1. CONFIGURACIÓN DE RUTA Y ARCHIVO
# ==============================================================================
RUTA_ARCHIVO = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo\comparacion_satelites\resultados_correccion_MSWEP\MSWEP_corregido_conchamarca_14976dias_1980_2020.xlsx"
DIR_SALIDA = os.path.dirname(RUTA_ARCHIVO)
IMG_SALIDA = os.path.join(DIR_SALIDA, "comparacion_MSWEP_crudo_vs_EQM_conchamarca.png")

print(f"Cargando archivo: {RUTA_ARCHIVO}")
df = pd.read_excel(RUTA_ARCHIVO)
df.columns = [str(c).strip() for c in df.columns]

# Normalizar fechas y tipos
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)
df["MSWEP"] = pd.to_numeric(df["MSWEP"], errors="coerce")
df["MSWEP_EQM"] = pd.to_numeric(df["MSWEP_EQM"], errors="coerce")
df["p_obs"] = pd.to_numeric(df["p_obs"], errors="coerce")
df["mes"] = df["fecha"].dt.month
df["anio"] = df["fecha"].dt.year

print(f"Total registros cargados: {len(df)} días ({df['fecha'].min().strftime('%Y-%m-%d')} a {df['fecha'].max().strftime('%Y-%m-%d')})")

# ==============================================================================
# 2. ESTADÍSTICAS COMPARATIVAS GLOBALES
# ==============================================================================
media_crudo = df["MSWEP"].mean()
media_eqm = df["MSWEP_EQM"].mean()
max_crudo = df["MSWEP"].max()
max_eqm = df["MSWEP_EQM"].max()
acum_crudo = df["MSWEP"].sum()
acum_eqm = df["MSWEP_EQM"].sum()

print("\n--- RESUMEN ESTADÍSTICO (14,976 DÍAS) ---")
print(f"Precipitación media diaria  -> Crudo: {media_crudo:.3f} mm/día | Corregido (EQM): {media_eqm:.3f} mm/día")
print(f"Precipitación máxima diaria -> Crudo: {max_crudo:.2f} mm     | Corregido (EQM): {max_eqm:.2f} mm")
print(f"Acumulado total (1980-2020) -> Crudo: {acum_crudo:,.1f} mm | Corregido (EQM): {acum_eqm:,.1f} mm")
print(f"Reducción global de sesgo volumétrico: {((acum_eqm - acum_crudo) / acum_crudo) * 100:.2f}%")

# ==============================================================================
# 3. GENERACIÓN DE FIGURA COMPARATIVA
# ==============================================================================
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, axes = plt.subplots(2, 2, figsize=(16, 11))
fig.suptitle("Evaluación Comparativa: MSWEP Crudo vs. MSWEP Corregido (EQM) [1980-2020]\nEstación Conchamarca (14,976 días continuos)", 
             fontsize=14, fontweight="bold", y=0.98)

# ------------------------------------------------------------------------------
# Panel A: Curva de Masa Acumulada Multianual (1980 - 2020)
# ------------------------------------------------------------------------------
ax_a = axes[0, 0]
cum_crudo = df["MSWEP"].cumsum()
cum_eqm = df["MSWEP_EQM"].cumsum()

# Acumulado observado donde hay datos
df_obs_cum = df[["fecha", "p_obs"]].dropna().copy()
df_obs_cum["cum_obs"] = df_obs_cum["p_obs"].cumsum()

ax_a.plot(df["fecha"], cum_crudo, label=f"MSWEP Crudo ({acum_crudo:,.0f} mm)", color="#d62728", linewidth=1.8, linestyle="--")
ax_a.plot(df["fecha"], cum_eqm, label=f"MSWEP EQM Corregido ({acum_eqm:,.0f} mm)", color="#1f77b4", linewidth=2.0)
ax_a.set_title("A) Curva de Masa Acumulada Continua (Balance Hídrico)", fontsize=11, fontweight="bold")
ax_a.set_xlabel("Año", fontsize=10)
ax_a.set_ylabel("Precipitación Acumulada (mm)", fontsize=10)
ax_a.grid(True, linestyle="--", alpha=0.6)
ax_a.legend(loc="upper left", frameon=True)

# ------------------------------------------------------------------------------
# Panel B: Ciclo Estacional Medio Diario (Régimen Mensual)
# ------------------------------------------------------------------------------
ax_b = axes[0, 1]
ciclo = df.groupby("mes")[["MSWEP", "MSWEP_EQM", "p_obs"]].mean()
meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

ax_b.plot(meses_nombres, ciclo["MSWEP"], label="MSWEP Crudo", color="#d62728", marker="s", linestyle="--", linewidth=1.8)
ax_b.plot(meses_nombres, ciclo["MSWEP_EQM"], label="MSWEP EQM Corregido", color="#1f77b4", marker="o", linewidth=2.2)
ax_b.plot(meses_nombres, ciclo["p_obs"], label="Observado en Tierra (p_obs)", color="black", marker="^", linestyle=":", linewidth=1.5, alpha=0.8)
ax_b.set_title("B) Ciclo Estacional Medio Diario por Mes", fontsize=11, fontweight="bold")
ax_b.set_xlabel("Mes", fontsize=10)
ax_b.set_ylabel("Precipitación Media (mm/día)", fontsize=10)
ax_b.grid(True, linestyle="--", alpha=0.6)
ax_b.legend(loc="upper right", frameon=True)

# ------------------------------------------------------------------------------
# Panel C: Curva de Duración de Precipitación (PDC / Cuantiles Empíricos)
# ------------------------------------------------------------------------------
ax_c = axes[1, 0]
pth = 0.1  # umbral día húmedo

# Extraer y ordenar días húmedos
wet_crudo = np.sort(df.loc[df["MSWEP"] >= pth, "MSWEP"].values)[::-1]
wet_eqm = np.sort(df.loc[df["MSWEP_EQM"] >= pth, "MSWEP_EQM"].values)[::-1]
wet_obs = np.sort(df.loc[df["p_obs"] >= pth, "p_obs"].dropna().values)[::-1]

if len(wet_crudo) > 0:
    prob_c = np.arange(1, len(wet_crudo) + 1) / len(wet_crudo) * 100.0
    ax_c.semilogy(prob_c, wet_crudo, label="MSWEP Crudo", color="#d62728", linestyle="--", linewidth=1.5)

if len(wet_eqm) > 0:
    prob_e = np.arange(1, len(wet_eqm) + 1) / len(wet_eqm) * 100.0
    ax_c.semilogy(prob_e, wet_eqm, label="MSWEP EQM Corregido", color="#1f77b4", linewidth=2.0)

if len(wet_obs) > 0:
    prob_o = np.arange(1, len(wet_obs) + 1) / len(wet_obs) * 100.0
    ax_c.semilogy(prob_o, wet_obs, label="Observado (p_obs)", color="black", linestyle=":", linewidth=1.5, alpha=0.7)

ax_c.set_title("C) Curva de Duración de Precipitación (Días >= 0.1 mm)", fontsize=11, fontweight="bold")
ax_c.set_xlabel("Probabilidad de Excedencia (%)", fontsize=10)
ax_c.set_ylabel("Precipitación Diaria (mm, log)", fontsize=10)
ax_c.grid(True, which="both", linestyle="--", alpha=0.6)
ax_c.legend(loc="upper right", frameon=True)

# ------------------------------------------------------------------------------
# Panel D: Comparación de Acumulados Anuales (1980 - 2020)
# ------------------------------------------------------------------------------
ax_d = axes[1, 1]
df_anual = df.groupby("anio")[["MSWEP", "MSWEP_EQM"]].sum()

ax_d.plot(df_anual.index, df_anual["MSWEP"], label="MSWEP Crudo", color="#d62728", linestyle="--", marker=".", alpha=0.7)
ax_d.plot(df_anual.index, df_anual["MSWEP_EQM"], label="MSWEP EQM Corregido", color="#1f77b4", marker="o", linewidth=2.0)
ax_d.fill_between(df_anual.index, df_anual["MSWEP_EQM"], df_anual["MSWEP"], color="#d62728", alpha=0.15, label="Sesgo Positivo Eliminado")

ax_d.set_title("D) Precipitación Anual Acumulada Interanual", fontsize=11, fontweight="bold")
ax_d.set_xlabel("Año", fontsize=10)
ax_d.set_ylabel("Precipitación Anual (mm/año)", fontsize=10)
ax_d.grid(True, linestyle="--", alpha=0.6)
ax_d.legend(loc="upper left", frameon=True)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(IMG_SALIDA, dpi=300)
print(f"\n-> Gráfico generado exitosamente en:\n   {IMG_SALIDA}")
plt.show()