import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# 1. PARÁMETROS DE LA CUENCA (RÍO LA MUMA)
# ==============================================================================
AREA_KM2 = 48.65                  # Área en km²
LATITUD = -17.087238              # Latitud obra de toma
ELEVACION_M = 3290                # Elevación obra de toma (m.s.n.m.)
CN_II = 77.0                      # Curva número ponderado

# Retención potencial máxima del complejo suelo-vegetación (SCS-CN)
S_MAX = (25400.0 / CN_II) - 254.0 # S_max ≈ 75.8 mm

# Rutas de archivos
BASE_DIR = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios"
PATH_PRECIP = os.path.join(BASE_DIR, "datos_satelites_depurados_1980_2020_MSWEP.xlsx")
PATH_TEMP = os.path.join(BASE_DIR, "temperatura_era5land_diaria_filtrada_corregida_final.xlsx")
PATH_OUT_EXCEL = os.path.join(BASE_DIR, "caudales_mensuales_lutz_scholz_1980_2020.xlsx")

# ==============================================================================
# 2. CARGA Y AGREGACIÓN MENSUAL DE SERIES (1980 - 2020)
# ==============================================================================
print("Cargando series hidrometeorológicas...")
df_p = pd.read_excel(PATH_PRECIP)
df_p.rename(columns={'fecha': 'Fecha', 'MSWEP_corr': 'P_diaria'}, inplace=True)
df_p['Fecha'] = pd.to_datetime(df_p['Fecha'])
df_p.set_index('Fecha', inplace=True)

df_t = pd.read_excel(PATH_TEMP)
df_t['Fecha'] = pd.to_datetime(df_t['Fecha'])
df_t.set_index('Fecha', inplace=True)

df_diario = df_p.join(df_t, how='inner')

df_mensual = df_diario.resample('MS').agg({
    'P_diaria': 'sum',
    'Tmean_corr': 'mean',
    'Tmin_corr': 'mean',
    'Tmax_corr': 'mean'
}).rename(columns={'P_diaria': 'P_mm', 'Tmean_corr': 'Tmean', 'Tmin_corr': 'Tmin', 'Tmax_corr': 'Tmax'})

df_mensual['Dias_mes'] = df_mensual.index.days_in_month

# ==============================================================================
# 3. RADIACIÓN SOLAR EXTRATERRESTRE (Ra) Y ETP (HARGREAVES)
# ==============================================================================
lat_rad = np.radians(LATITUD)

def calcular_ra_diaria(lat_rad, doy):
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    delta = 0.409 * np.sin((2 * np.pi * doy / 365) - 1.39)
    ws_arg = -np.tan(lat_rad) * np.tan(delta)
    ws = np.arccos(np.clip(ws_arg, -1.0, 1.0))
    ra_mj = (24 * 60 / np.pi) * 0.0820 * dr * (
        ws * np.sin(lat_rad) * np.sin(delta) +
        np.cos(lat_rad) * np.cos(delta) * np.sin(ws)
    )
    return ra_mj / 2.45

ra_mensual = []
for fecha, row in df_mensual.iterrows():
    dias = row['Dias_mes']
    doy_central = fecha.dayofyear + int(dias / 2)
    ra_dia = calcular_ra_diaria(lat_rad, doy_central)
    ra_mensual.append(ra_dia * dias)

df_mensual['Ra_mm'] = ra_mensual
df_mensual['DT'] = np.maximum(df_mensual['Tmax'] - df_mensual['Tmin'], 0.1)
df_mensual['ETP_mm'] = 0.0023 * df_mensual['Ra_mm'] * (df_mensual['Tmean'] + 17.8) * np.sqrt(df_mensual['DT'])

# ==============================================================================
# 4. BALANCE ANUAL Y COEFICIENTE DE ESCORRENTÍA (MÉTODO TURC / SCHOLZ)
# ==============================================================================
p_anual_media = df_mensual['P_mm'].groupby(df_mensual.index.year).sum().mean()
t_anual_media = df_mensual['Tmean'].groupby(df_mensual.index.year).mean().mean()

L_temp = 300 + 25 * t_anual_media + 0.05 * (t_anual_media**3)
deficit_anual_turc = p_anual_media / np.sqrt(0.9 + (p_anual_media / L_temp)**2)
escorrentia_anual_estimada = max(p_anual_media - deficit_anual_turc, 0.20 * p_anual_media)
C_anual = escorrentia_anual_estimada / p_anual_media
C_anual = float(np.clip(C_anual, 0.28, 0.42))

print(f"Precipitación Anual Media: {p_anual_media:.1f} mm")
print(f"Temperatura Anual Media:   {t_anual_media:.1f} °C")
print(f"Coeficiente de Escorrentía Anual (C): {C_anual:.3f}")

# ==============================================================================
# 5. MODELO FINAL CALIBRADO DE GENERACIÓN DE CAUDALES (LUTZ SCHOLZ)
# ==============================================================================
C_dir = C_anual * 0.35             # Partición escorrentía directa 0.50
C_rec = C_anual * 0.65             # Partición recarga subterránea 0.50
A_DIARIO = 0.005                  # Tasa de recesión calibrada (días^-1) 0.0032
RESERVA_INICIAL = 80.0             # Almacenamiento freático inicial (mm) 60.0
RESERVA_MINIMA = 70.0              # Reserva freática base permanente (mm) 35.0
DEFICIT_MAX_SUELO = 0.30 * S_MAX   # Capacidad máxima de déficit acumulable en estiaje (~34 mm) 0.45

n_meses = len(df_mensual)
q_dir_mm = np.zeros(n_meses)
q_base_mm = np.zeros(n_meses)
escorrentia_tot_mm = np.zeros(n_meses)
almacenamiento_acuifero = np.zeros(n_meses)
deficit_suelo = np.zeros(n_meses)

reserva_sub = RESERVA_INICIAL
deficit_actual = 0.0               # Déficit inicial

for i in range(n_meses):
    P_i = df_mensual['P_mm'].iloc[i]
    ETP_i = df_mensual['ETP_mm'].iloc[i]
    dias_i = df_mensual['Dias_mes'].iloc[i]
    k_mes = np.exp(-A_DIARIO * dias_i)
    
    # 1. Umbral dinámico dependiente del déficit de humedad antecedente
    # En meses secos el suelo se seca; las primeras lluvias de primavera sacian este déficit
    if P_i < ETP_i:
        # Se incrementa el déficit de humedad del suelo
        deficit_actual = min(deficit_actual + (ETP_i - P_i) * 0.20, DEFICIT_MAX_SUELO)
    else:
        # La lluvia reduce el déficit existente
        recuperacion = min(deficit_actual, P_i - ETP_i)
        deficit_actual = max(deficit_actual - recuperacion, 0.0)
    
    # Umbral efectivo para generación de escorrentía directa
    P_umbral = (0.10 * ETP_i) + (0.30 * deficit_actual)    # P_umbral = (0.15 * ETP_i) + (0.50 * deficit_actual)
    
    if P_i > P_umbral:
        lluvia_neta = P_i - P_umbral
        q_dir_i = C_dir * lluvia_neta
        recarga_i = C_rec * lluvia_neta
    else:
        q_dir_i = 0.0
        recarga_i = 0.0
    
    # 2. Dinámica del acuífero y flujo base
    reserva_disponible = reserva_sub + recarga_i
    q_base_i = reserva_disponible * (1.0 - k_mes)
    reserva_sub = max(reserva_disponible - q_base_i, RESERVA_MINIMA)
    
    # 3. Escorrentía total mensual
    escorrentia_i = q_dir_i + q_base_i
    
    q_dir_mm[i] = q_dir_i
    q_base_mm[i] = q_base_i
    escorrentia_tot_mm[i] = escorrentia_i
    almacenamiento_acuifero[i] = reserva_sub
    deficit_suelo[i] = deficit_actual

df_mensual['Q_dir_mm'] = q_dir_mm
df_mensual['Q_base_mm'] = q_base_mm
df_mensual['Escorrentia_mm'] = escorrentia_tot_mm
df_mensual['Reserva_mm'] = almacenamiento_acuifero
df_mensual['Deficit_mm'] = deficit_suelo

# Conversión a caudal en m³/s
df_mensual['Q_m3s'] = (df_mensual['Escorrentia_mm'] * AREA_KM2) / (86.4 * df_mensual['Dias_mes'])
df_mensual['Q_base_m3s'] = (df_mensual['Q_base_mm'] * AREA_KM2) / (86.4 * df_mensual['Dias_mes'])
df_mensual['Q_dir_m3s'] = (df_mensual['Q_dir_mm'] * AREA_KM2) / (86.4 * df_mensual['Dias_mes'])

# Exportación a Excel
df_mensual.to_excel(PATH_OUT_EXCEL)
print(f"Resultados guardados exitosamente en:\n{PATH_OUT_EXCEL}")

# ==============================================================================
# 6. ESTADÍSTICAS Y VALIDACIÓN CON AFOROS DE CAMPO
# ==============================================================================
q_sorted = np.sort(df_mensual['Q_m3s'].values)[::-1]
prob_excedencia = (np.arange(1, len(q_sorted) + 1) / (len(q_sorted) + 1)) * 100

q50 = np.percentile(df_mensual['Q_m3s'], 100 - 50)
q75 = np.percentile(df_mensual['Q_m3s'], 100 - 75)
q90 = np.percentile(df_mensual['Q_m3s'], 100 - 90)
q95 = np.percentile(df_mensual['Q_m3s'], 100 - 95)

print("\n" + "="*58)
print("   RESULTADOS FINALES CALIBRADOS - RÍO LA MUMA")
print("="*58)
print(f"Caudal Promedio Multianual: {df_mensual['Q_m3s'].mean():.3f} m³/s")
print(f"Caudal Mínimo Mensual:     {df_mensual['Q_m3s'].min():.3f} m³/s")
print(f"Caudal Máximo Mensual:     {df_mensual['Q_m3s'].max():.3f} m³/s")
print(f"Caudal de Garantía Q50%:   {q50:.3f} m³/s")
print(f"Caudal de Garantía Q75%:   {q75:.3f} m³/s")
print(f"Caudal de Garantía Q90%:   {q90:.3f} m³/s")
print(f"Caudal de Garantía Q95%:   {q95:.3f} m³/s")

# Validación en los meses de aforo
q_jun_2011 = df_mensual.loc['2011-06-01', 'Q_m3s']
q_oct_2013 = df_mensual.loc['2013-10-01', 'Q_m3s']

print("\n" + "="*58)
print("   VALIDACIÓN CON AFOROS DE CAMPO")
print("="*58)
print(f"Junio 2011:")
print(f"  - Medido (Aforo 08/06/2011): 0.171 m³/s")
print(f"  - Modelado Lutz Scholz:     {q_jun_2011:.3f} m³/s")
print(f"  - Error relativo:           {abs(q_jun_2011 - 0.171) / 0.171 * 100:.1f} %")

print(f"\nOctubre 2013:")
print(f"  - Medido (Aforo 08/10/2013): 0.194 m³/s")
print(f"  - Modelado Lutz Scholz:     {q_oct_2013:.3f} m³/s")
print(f"  - Error relativo:           {abs(q_oct_2013 - 0.194) / 0.194 * 100:.1f} %")
print("="*58)

# ==============================================================================
# 7. GRÁFICOS
# ==============================================================================
fig, axs = plt.subplots(3, 1, figsize=(12, 12))

# Subplot 1: Hidrograma Serie Completa
axs[0].plot(df_mensual.index, df_mensual['Q_m3s'], color='#1f77b4', lw=1.2, label='Caudal Total (m³/s)')
axs[0].plot(df_mensual.index, df_mensual['Q_base_m3s'], color='#ff7f0e', lw=1.0, ls='--', label='Caudal Base (m³/s)')
axs[0].set_title('Hidrograma Mensual Lutz Scholz Calibrado (1980 - 2020) - Río La Muma', fontsize=12, fontweight='bold')
axs[0].set_ylabel('Caudal (m³/s)')
axs[0].grid(True, linestyle=':', alpha=0.6)
axs[0].legend(loc='upper right')

# Subplot 2: Régimen Medio Mensual Multianual
df_mensual['Mes'] = df_mensual.index.month
regimen_total = df_mensual.groupby('Mes')['Q_m3s'].mean()
regimen_base = df_mensual.groupby('Mes')['Q_base_m3s'].mean()
meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

axs[1].bar(meses_nombres, regimen_total.values, color='#4682b4', alpha=0.85, edgecolor='black', label='Caudal Total')
axs[1].plot(meses_nombres, regimen_base.values, color='#d95f02', marker='o', lw=2, label='Caudal Base')
axs[1].set_title('Régimen Medio Mensual Multianual (m³/s)', fontsize=12, fontweight='bold')
axs[1].set_ylabel('Caudal Medio (m³/s)')
axs[1].grid(True, axis='y', linestyle=':', alpha=0.6)
axs[1].legend(loc='upper right')

# Subplot 3: Curva de Duración de Caudales (FDC)
axs[2].plot(prob_excedencia, q_sorted, color='#2ca02c', lw=2.2)
axs[2].axvline(50, color='gray', linestyle='--', alpha=0.7, label=f'Q50 = {q50:.3f} m³/s')
axs[2].axvline(75, color='orange', linestyle='--', alpha=0.7, label=f'Q75 = {q75:.3f} m³/s')
axs[2].axvline(90, color='red', linestyle='--', alpha=0.7, label=f'Q90 = {q90:.3f} m³/s')
axs[2].axvline(95, color='purple', linestyle='--', alpha=0.7, label=f'Q95 = {q95:.3f} m³/s')
axs[2].set_title('Curva de Duración de Caudales (FDC) - Aprovechamiento Hidroeléctrico', fontsize=12, fontweight='bold')
axs[2].set_xlabel('Probabilidad de Excedencia (%)')
axs[2].set_ylabel('Caudal (m³/s)')
axs[2].grid(True, linestyle=':', alpha=0.6)
axs[2].legend(loc='upper right')

plt.tight_layout()
plt.subplots_adjust(hspace=0.35, top=0.95, bottom=0.08)  # hspace regula la separación vertical
plt.show()