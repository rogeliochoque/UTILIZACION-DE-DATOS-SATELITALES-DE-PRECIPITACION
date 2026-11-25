import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# =============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y PARÁMETROS FÍSICOS
# =============================================================================
directorio = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios"
archivo_entrada = os.path.join(directorio, "temperatura_era5land_diaria_1980_2020.xlsx")
archivo_salida_diario = os.path.join(directorio, "temperatura_era5land_diaria_filtrada_corregida.xlsx")
archivo_salida_mensual = os.path.join(directorio, "temperatura_era5land_mensual_lutz_scholz.xlsx")

# Parámetros altitudinales y de gradiente térmico
Z_era5    = 3326.3   # Cota deducida de la presión de ERA5-Land en GEE (m.s.n.m.)
Z_toma    = 3290.0   # Cota real de la obra de toma / captación (m.s.n.m.)
gamma     = 0.0065   # Gradiente térmico vertical (°C/m -> 6.5 °C / 1000 m)

# Desnivel y ajuste: al estar la toma más baja, se suma temperatura
delta_z = Z_era5 - Z_toma         # +36.3 m
delta_T = gamma * delta_z         # +0.24 °C

print(f"Cota ERA5-Land:   {Z_era5:.1f} m.s.n.m.")
print(f"Cota Obra de Toma: {Z_toma:.1f} m.s.n.m.")
print(f"Ajuste térmico por desnivel: {delta_T:+.2f} °C\n")

# =============================================================================
# 2. CARGA DE DATOS
# =============================================================================
df = pd.read_excel(archivo_entrada)

# Detección flexible de nombres de columnas
col_fecha = [c for c in df.columns if c.lower() in ['fecha', 'date', 'datetime']][0]
col_tmean = [c for c in df.columns if 'tmean' in c.lower() or 'mean' in c.lower()][0]
col_tmin  = [c for c in df.columns if 'tmin' in c.lower() or 'min' in c.lower()][0]
col_tmax  = [c for c in df.columns if 'tmax' in c.lower() or 'max' in c.lower()][0]

df['Fecha'] = pd.to_datetime(df[col_fecha])
df = df.sort_values('Fecha').reset_index(drop=True)

# Guardar copia de valores brutos originales
df['Tmean_raw'] = df[col_tmean]
df['Tmin_raw']  = df[col_tmin]
df['Tmax_raw']  = df[col_tmax]

# =============================================================================
# 3. CONTROL DE CALIDAD FÍSICO Y DETECCIÓN DE OUTLIERS POR IQR MENSUAL
# =============================================================================
df['Mes_num'] = df['Fecha'].dt.month

# A. Control de inconsistencia física básica (Tmin <= Tmean <= Tmax)
inconsistentes = (df['Tmin_raw'] > df['Tmean_raw']) | (df['Tmean_raw'] > df['Tmax_raw'])
print(f"Registros con inconsistencias físicas (Tmin > Tmean o Tmean > Tmax): {inconsistentes.sum()}")

for col in ['Tmean_raw', 'Tmin_raw', 'Tmax_raw']:
    df.loc[inconsistentes, col] = np.nan

# B. Detección de outliers estadísticos mediante IQR por mes (estacional)
def filtrar_outliers_iqr(df_in, columna, factor=2.5):
    serie_limpia = df_in[columna].copy()
    conteo_outliers = 0
    
    for mes in range(1, 13):
        idx_mes = df_in['Mes_num'] == mes
        q1 = df_in.loc[idx_mes, columna].quantile(0.25)
        q3 = df_in.loc[idx_mes, columna].quantile(0.75)
        iqr = q3 - q1
        
        lim_inf = q1 - factor * iqr
        lim_sup = q3 + factor * iqr
        
        cond_outlier = idx_mes & ((df_in[columna] < lim_inf) | (df_in[columna] > lim_sup))
        conteo_outliers += cond_outlier.sum()
        serie_limpia.loc[cond_outlier] = np.nan
        
    print(f"Outliers detectados e imputados en {columna}: {conteo_outliers}")
    return serie_limpia

df['Tmean_clean'] = filtrar_outliers_iqr(df, 'Tmean_raw')
df['Tmin_clean']  = filtrar_outliers_iqr(df, 'Tmin_raw')
df['Tmax_clean']  = filtrar_outliers_iqr(df, 'Tmax_raw')

# Imputación de huecos por interpolación lineal continua (resuelve el error)
for col in ['Tmean_clean', 'Tmin_clean', 'Tmax_clean']:
    df[col] = df[col].interpolate(method='linear', limit_direction='both')

# =============================================================================
# 4. CORRECCIÓN DE SESGO POR GRADIENTE ALTITUDINAL
# =============================================================================
df['Tmean_corr'] = df['Tmean_clean'] + delta_T
df['Tmin_corr']  = df['Tmin_clean']  + delta_T
df['Tmax_corr']  = df['Tmax_clean']  + delta_T

# =============================================================================
# 5. AGREGACIÓN MENSUAL (BASE PARA LUTZ SCHOLZ / ETP)
# =============================================================================
df['Año'] = df['Fecha'].dt.year
df['Mes'] = df['Fecha'].dt.month

df_mensual = df.groupby(['Año', 'Mes']).agg({
    'Tmean_corr': 'mean',
    'Tmin_corr': 'mean',
    'Tmax_corr': 'mean',
    'Tmean_raw': 'mean',
    'Tmin_raw': 'mean',
    'Tmax_raw': 'mean'
}).reset_index()

# Guardar resultados en Excel
df.to_excel(archivo_salida_diario, index=False)
df_mensual.to_excel(archivo_salida_mensual, index=False)
print(f"\nArchivos generados con éxito en:\n- {archivo_salida_diario}\n- {archivo_salida_mensual}")

# =============================================================================
# 6. GENERACIÓN DE GRÁFICOS DIAGNÓSTICOS (ANTES VS. DESPUÉS)
# =============================================================================
sns.set_theme(style="ticks")
fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=False)

# Gráfico 1: Serie diaria completa (Tmean Bruta vs Tmean Corregida)
axes[0].plot(df['Fecha'], df['Tmean_raw'], color='darkgray', alpha=0.6, label='Tmean Bruta (ERA5-Land)', lw=0.8)
axes[0].plot(df['Fecha'], df['Tmean_corr'], color='#1f77b4', alpha=0.85, label='Tmean Filtrada y Corregida (Cuenca)', lw=0.9)
axes[0].set_title("Serie Temporal Diaria de Temperatura Media (1980 - 2020)", fontsize=11, fontweight='bold')
axes[0].set_ylabel("Temperatura (°C)")
axes[0].legend(loc="upper right", frameon=True)
axes[0].grid(True, linestyle="--", alpha=0.5)

# Gráfico 2: Ciclo anual medio mensual climatológico
meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
ciclo_raw = df.groupby('Mes_num')['Tmean_raw'].mean()
ciclo_corr = df.groupby('Mes_num')['Tmean_corr'].mean()
ciclo_min_corr = df.groupby('Mes_num')['Tmin_corr'].mean()
ciclo_max_corr = df.groupby('Mes_num')['Tmax_corr'].mean()

axes[1].plot(meses_nombres, ciclo_raw, 'o--', color='crimson', label='Tmean Media Mensual Bruta', lw=1.5)
axes[1].plot(meses_nombres, ciclo_corr, 's-', color='navy', label='Tmean Media Mensual Corregida', lw=2)
axes[1].fill_between(meses_nombres, ciclo_min_corr, ciclo_max_corr, color='navy', alpha=0.15, label='Banda Tmin-Tmax Corregida')
axes[1].set_title("Régimen Térmico Medio Anual (Ciclo Estacional)", fontsize=11, fontweight='bold')
axes[1].set_ylabel("Temperatura (°C)")
axes[1].legend(loc="lower left", frameon=True)
axes[1].grid(True, linestyle="--", alpha=0.5)

# Gráfico 3: Función de densidad de probabilidad / Distribución acumulada
sns.kdeplot(df['Tmean_raw'], ax=axes[2], color='red', label='Distribución Bruta (ERA5)', fill=True, alpha=0.2)
sns.kdeplot(df['Tmean_corr'], ax=axes[2], color='blue', label='Distribución Corregida por Cota', fill=True, alpha=0.2)
axes[2].axvline(df['Tmean_raw'].mean(), color='red', linestyle=':', label=f"Media Bruta: {df['Tmean_raw'].mean():.2f} °C")
axes[2].axvline(df['Tmean_corr'].mean(), color='blue', linestyle=':', label=f"Media Corregida: {df['Tmean_corr'].mean():.2f} °C")
axes[2].set_title("Desplazamiento de la Función de Densidad de Probabilidad (Corrección de Sesgo)", fontsize=11, fontweight='bold')
axes[2].set_xlabel("Temperatura Media Diaria (°C)")
axes[2].set_ylabel("Densidad")
axes[2].legend(loc="upper right", frameon=True)
axes[2].grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
grafico_path = os.path.join(directorio, "diagnostico_temperatura_antes_despues.png")
plt.savefig(grafico_path, dpi=300)
plt.show()

print(f"Gráfico de diagnóstico guardado en: {grafico_path}")