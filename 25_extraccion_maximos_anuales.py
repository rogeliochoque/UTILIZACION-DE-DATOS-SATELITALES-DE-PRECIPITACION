import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. CONFIGURACIÓN DINÁMICA DE RUTAS
carpeta_actual = os.path.dirname(os.path.abspath(__file__))

# Nombre del archivo Excel
nombre_archivo_entrada = "datos_mswep_corregidos.xlsx"
ruta_entrada = os.path.join(carpeta_actual, nombre_archivo_entrada)

carpeta_salida = carpeta_actual
ruta_csv_salida = os.path.join(carpeta_salida, "maximos_anuales_24h.csv")
ruta_grafico_salida = os.path.join(
    carpeta_salida, "grafico_maximos_anuales.png"
)

# 2. VERIFICACIÓN DE EXISTENCIA
if not os.path.exists(ruta_entrada):
  print(f"❌ No se encontró el archivo de entrada en:\n👉 {ruta_entrada}")
  print(
      f"Verifica que '{nombre_archivo_entrada}' esté en la misma carpeta que"
      " este script."
  )
  exit()

# 3. LECTURA Y PROCESAMIENTO
print("⏳ Leyendo serie temporal de MSWEP desde Excel...")
# Lectura usando read_excel
df = pd.read_excel(ruta_entrada)

# Convertir columna fecha
df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True)
df["Anio"] = df["fecha"].dt.year

# Extraer el máximo anual de precipitación en 24 horas
print("🌧️ Filtrando las tormentas máximas por año...")
maximos_anuales = df.groupby("Anio")["MSWEP_corr"].max().reset_index()
maximos_anuales.columns = ["Anio", "P_max_24h_mm"]

# Guardar la serie procesada en CSV
maximos_anuales.to_csv(ruta_csv_salida, index=False)
print(f"📁 Archivo de datos guardado con éxito en:\n👉 {ruta_csv_salida}")

# 4. GENERACIÓN DEL GRÁFICO
print("📊 Generando gráfico para el cuerpo de la tesis...")
plt.style.use(
    "seaborn-v0_8-whitegrid"
    if "seaborn-v0_8-whitegrid" in plt.style.available
    else "default"
)
fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

# Gráfico de barras de máximos anuales
bars = ax.bar(
    maximos_anuales["Anio"],
    maximos_anuales["P_max_24h_mm"],
    color="#1f77b4",
    alpha=0.8,
    edgecolor="black",
    linewidth=0.7,
    label="P max 24h",
)

# Línea de tendencia
z = np.polyfit(maximos_anuales["Anio"], maximos_anuales["P_max_24h_mm"], 1)
p = np.poly1d(z)
ax.plot(
    maximos_anuales["Anio"],
    p(maximos_anuales["Anio"]),
    "r--",
    linewidth=1.5,
    label="Tendencia lineal",
)

# Ajustes de formato
ax.set_title(
    "Evolución Cronológica de Precipitaciones Máximas Anuales en 24h (MSWEP"
    " Corregido)",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
ax.set_xlabel("Año", fontsize=12, labelpad=10)
ax.set_ylabel("Precipitación Máxima en 24h (mm)", fontsize=12, labelpad=10)
ax.set_xlim(
    maximos_anuales["Anio"].min() - 1, maximos_anuales["Anio"].max() + 1
)
ax.tick_params(labelsize=10)
ax.legend(
    loc="upper left",
    fontsize=11,
    frameon=True,
    facecolor="white",
    edgecolor="none",
)
ax.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig(ruta_grafico_salida, bbox_inches="tight")
plt.close()

print(f"🖼️ Gráfico guardado en:\n👉 {ruta_grafico_salida}")
print("\n🚀 ¡Serie de máximos anuales generada correctamente!")