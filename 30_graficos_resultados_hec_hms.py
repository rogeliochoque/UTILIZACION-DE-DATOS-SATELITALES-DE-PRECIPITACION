import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# 1. RUTA Y CARGA DEL ARCHIVO EXCEL DE HEC-HMS
# ==============================================================================
ruta_directorio = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales maximos\6_HEC HMS"
nombre_archivo = "Hidrogramas_CHUQUIÑA_25_50_100.xlsx"  #"Hidrogramas_25_50_100.xlsx"
ruta_completa = os.path.join(ruta_directorio, nombre_archivo)

print("=" * 75)
print(f"Cargando archivo: {ruta_completa}")
print("=" * 75)

# Cargar el archivo Excel
df = pd.read_excel(ruta_completa)

# Limpiar nombres de columnas eliminando espacios en blanco en los extremos
df.columns = [c.strip() for c in df.columns]

# Mapeo de columnas esperadas
col_25 = "Caudal para T=25 años (m3/s)"
col_50 = "Caudal para T=50 años (m3/s)"
col_100 = "Caudal para T=100 años (m3/s)"

columnas_tr = {
    25: col_25,
    50: col_50,
    100: col_100
}

# Conversión de caudales a flotante (manejo de coma decimal si viniera como texto)
for tr, col in columnas_tr.items():
    if col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".").astype(float)
        else:
            df[col] = df[col].astype(float)
    else:
        raise KeyError(f"No se encontró la columna '{col}' en la hoja Excel.")

# ==============================================================================
# 2. CONSTRUCCIÓN DE LA VARIABLE DE TIEMPO (HORAS)
# ==============================================================================
# Intentar procesar fechas y horas para calcular el delta t exacto
if "Date" in df.columns and "Time" in df.columns:
    try:
        # Combinar Date y Time en una serie datetime
        dt_str = df["Date"].astype(str).str.strip() + " " + df["Time"].astype(str).str.strip()
        # Mapeo común de nombres de meses en español por si el parser no los detecta directamente
        meses_es = {
            "ene.": "Jan", "feb.": "Feb", "mar.": "Mar", "abr.": "Apr",
            "may.": "May", "jun.": "Jun", "jul.": "Jul", "ago.": "Aug",
            "sep.": "Sep", "oct.": "Oct", "nov.": "Nov", "dic.": "Dec",
            "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
            "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
            "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec"
        }
        for es, en in meses_es.items():
            dt_str = dt_str.str.replace(es, en, regex=False)

        tiempos = pd.to_datetime(dt_str, errors="coerce")
        if tiempos.notna().all():
            delta_segundos = (tiempos - tiempos.iloc[0]).dt.total_seconds().values
            t_horas = delta_segundos / 3600.0
            dt_hr = (delta_segundos[1] - delta_segundos[0]) / 3600.0 if len(delta_segundos) > 1 else (10.0 / 60.0)
        else:
            raise ValueError("Inconsistencias al convertir Date/Time.")
    except Exception:
        # Si ocurre alguna excepción en el parseo, se asume el intervalo estándar de 10 min (0.1667 h)
        dt_hr = 10.0 / 60.0
        t_horas = np.arange(len(df)) * dt_hr
else:
    dt_hr = 10.0 / 60.0
    t_horas = np.arange(len(df)) * dt_hr

# ==============================================================================
# 3. PROCESAMIENTO E INTERPRETACIÓN EN TERMINAL
# ==============================================================================
resumen = []
graficos = {}

for Tr, col in columnas_tr.items():
    q_serie = df[col].values
    q_max = float(np.nanmax(q_serie))
    idx_pico = int(np.nanargmax(q_serie))
    t_pico = float(t_horas[idx_pico])
    
    # Cálculo del volumen escurrido total (integral trapezoidal en hm³)
    volumen_m3 = np.trapezoid(q_serie, t_horas * 3600.0)
    volumen_hm3 = volumen_m3 / 1e6

    resumen.append({
        "Tr (años)": Tr,
        "Q_pico (m³/s)": round(q_max, 2),
        "t_pico (h)": round(t_pico, 2),
        "Volumen (hm³)": round(volumen_hm3, 3)
    })
    
    graficos[Tr] = (t_horas, q_serie, q_max)

df_resumen = pd.DataFrame(resumen)

print("\n--- RESUMEN DE RESULTADOS HEC-HMS (CRECIDAS DE DISEÑO) ---")
print(df_resumen.to_string(index=False))
print("-" * 75)

# ==============================================================================
# 4. GRAFICACIÓN DE HIDROGRAMAS DE CRECIDA
# ==============================================================================
plt.figure(figsize=(9, 4.5))

colores = {25: "#1f77b4", 50: "#ff7f0e", 100: "#2ca02c"}

for Tr in [25, 50, 100]:
    t_plot, q_plot, q_max = graficos[Tr]
    plt.plot(
        t_plot,
        q_plot,
        lw=2,
        color=colores[Tr],
        label=f"Tr = {Tr} años (Qmax = {q_max:.2f} m³/s)"
    )

plt.title("Hidrogramas de Crecida Simulados en HEC-HMS (SCS - Bloques Alternos, AMC III)", fontsize=11, fontweight="bold")
plt.xlabel("Tiempo transcurrido (horas)", fontsize=10)
plt.ylabel("Caudal de crecida (m³/s)", fontsize=10)
plt.xlim(left=0, right=np.max(t_horas))
plt.ylim(bottom=0)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend(frameon=True, loc="upper right")
plt.tight_layout()

# Guardar figura opcionalmente en el mismo directorio y mostrar
salida_png = os.path.join(ruta_directorio, "Hidrogramas_CHUQUIÑA_HEC_HMS_25_50_100.png")
try:
    plt.savefig(salida_png, dpi=300)
    print(f"\n[OK] Gráfico exportado en: {salida_png}")
except Exception as e:
    print(f"\n[Info] No se pudo guardar automáticamente la imagen: {e}")

plt.show()