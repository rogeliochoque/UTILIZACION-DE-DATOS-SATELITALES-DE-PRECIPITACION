import os
import numpy as np
import pandas as pd
from scipy import stats

# =============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y CARGA DEL ARCHIVO PROCESADO
# =============================================================================
directorio = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios"
archivo_diario = os.path.join(directorio, "temperatura_era5land_diaria_filtrada_corregida.xlsx")
archivo_salida_stats = os.path.join(directorio, "resumen_estadistico_control_temperatura.xlsx")

print(f"Cargando datos desde:\n{archivo_diario} ...")
df = pd.read_excel(archivo_diario)
print("Datos cargados correctamente.\n")

# =============================================================================
# 2. TABLA DE ESTADÍSTICOS DESCRIPTIVOS CLAVE (ANTES VS. DESPUÉS)
# =============================================================================
stats_data = []
variables = [
    ('Tmean (°C)', 'Tmean_raw', 'Tmean_corr'),
    ('Tmin (°C)', 'Tmin_raw', 'Tmin_corr'),
    ('Tmax (°C)', 'Tmax_raw', 'Tmax_corr'),
]

for nombre, col_raw, col_corr in variables:
    stats_data.append({
        'Variable': nombre,
        'Media (Antes)': df[col_raw].mean(),
        'Media (Después)': df[col_corr].mean(),
        'Diferencia (°C)': df[col_corr].mean() - df[col_raw].mean(),
        'Desv. Est. (Antes)': df[col_raw].std(),
        'Desv. Est. (Después)': df[col_corr].std(),
        'Mínimo (Después)': df[col_corr].min(),
        'Máximo (Después)': df[col_corr].max()
    })

# Análisis de amplitud térmica diaria (DTR = Tmax - Tmin)
df['DTR_raw'] = df['Tmax_raw'] - df['Tmin_raw']
df['DTR_corr'] = df['Tmax_corr'] - df['Tmin_corr']

stats_data.append({
    'Variable': 'Amplitud (Tmax - Tmin)',
    'Media (Antes)': df['DTR_raw'].mean(),
    'Media (Después)': df['DTR_corr'].mean(),
    'Diferencia (°C)': df['DTR_corr'].mean() - df['DTR_raw'].mean(),
    'Desv. Est. (Antes)': df['DTR_raw'].std(),
    'Desv. Est. (Después)': df['DTR_corr'].std(),
    'Mínimo (Después)': df['DTR_corr'].min(),
    'Máximo (Después)': df['DTR_corr'].max()
})

df_tabla = pd.DataFrame(stats_data).round(2)

print("=" * 70)
print("         TABLA COMPARATIVA DE CONTROL HIDROLÓGICO (1980 - 2020)")
print("=" * 70)
print(df_tabla.to_string(index=False))
print("=" * 70)

# =============================================================================
# 3. PRUEBAS DE HIPÓTESIS FORMALES
# =============================================================================
# A. Prueba t de Student emparejada sobre Tmean
t_stat, p_student = stats.ttest_rel(df['Tmean_raw'], df['Tmean_corr'], nan_policy='omit')

# B. Kolmogorov-Smirnov de dos muestras (serie centrada para evaluar forma de distribución)
tmean_corr_centrada = df['Tmean_corr'] - (df['Tmean_corr'].mean() - df['Tmean_raw'].mean())
ks_stat, p_ks = stats.ks_2samp(df['Tmean_raw'].dropna(), tmean_corr_centrada.dropna())

print("\n" + "=" * 70)
print("                   PRUEBAS ESTADÍSTICAS FORMALES")
print("=" * 70)
print(f"1. Prueba t de Student emparejada (Significancia del ajuste por cota):")
print(f"   - Estadístico t : {t_stat:.2f}")
print(f"   - p-valor       : {p_student:.3e}")
if p_student < 0.05:
    print("   -> Conclusión   : El ajuste altitudinal es estadísticamente significativo (p < 0.05).")
else:
    print("   -> Conclusión   : No se detecta diferencia estadísticamente significativa.")

print(f"\n2. Prueba Kolmogorov-Smirnov (Preservación de forma de la distribución):")
print(f"   - Estadístico D : {ks_stat:.4f}")
print(f"   - p-valor       : {p_ks:.4f}")
if p_ks > 0.05:
    print("   -> Conclusión   : Se acepta la hipótesis nula (p > 0.05). La forma y variabilidad")
    print("                     probabilística de la serie térmica se conservan intactas.")
else:
    print("   -> Conclusión   : La forma de la distribución muestra variaciones.")
print("=" * 70)

# =============================================================================
# 4. EXPORTACIÓN A EXCEL
# =============================================================================
df_tabla.to_excel(archivo_salida_stats, index=False)
print(f"\nResumen exportado exitosamente a:\n{archivo_salida_stats}")