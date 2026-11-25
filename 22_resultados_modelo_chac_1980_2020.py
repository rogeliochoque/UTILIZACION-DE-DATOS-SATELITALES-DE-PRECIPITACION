import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# 1. PARÁMETROS Y RUTAS DE ARCHIVOS
# ==============================================================================
BASE_DIR = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios\CHAC"
PATH_EXCEL_CHAC = os.path.join(BASE_DIR, "caudales_simulados_CHAC.xlsx")
PATH_OUT_EXCEL = os.path.join(BASE_DIR, "caudales_mensuales_chac_procesados.xlsx")

# ==============================================================================
# 2. CARGA Y REESTRUCTURACIÓN DE DATOS CHAC
# ==============================================================================
print("Cargando resultados simulados del modelo CHAC...")
df_raw = pd.read_excel(PATH_EXCEL_CHAC)

# Limpieza de espacios en los nombres de columnas
df_raw.columns = [str(col).strip() for col in df_raw.columns]

# Meses presentes en la cabecera del archivo generado por CHAC
COLUMNAS_MESES = ['Ene', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Transformación de formato tabular ancho a serie temporal continua (formato largo)
df_largo = df_raw.melt(
    id_vars=['Año'],
    value_vars=COLUMNAS_MESES,
    var_name='Mes_Nombre',
    value_name='Q_m3s'
)

# Mapeo a número de mes
mapa_meses = {mes: i + 1 for i, mes in enumerate(COLUMNAS_MESES)}
df_largo['Mes_Num'] = df_largo['Mes_Nombre'].map(mapa_meses)

# Construcción de la fecha como índice temporal (primer día de cada mes)
df_largo['Fecha'] = pd.to_datetime(
    df_largo['Año'].astype(str) + '-' + df_largo['Mes_Num'].astype(str) + '-01'
)
df_mensual = df_largo.sort_values('Fecha').set_index('Fecha')
df_mensual['Q_m3s'] = pd.to_numeric(df_mensual['Q_m3s'], errors='coerce')

# Exportar serie temporal procesada
df_mensual[['Año', 'Mes_Num', 'Q_m3s']].to_excel(PATH_OUT_EXCEL)
print(f"Serie continua mensual guardada en:\n{PATH_OUT_EXCEL}")

# ==============================================================================
# 3. ESTADÍSTICAS Y VALIDACIÓN CON AFOROS DE CAMPO
# ==============================================================================
q_sorted = np.sort(df_mensual['Q_m3s'].dropna().values)[::-1]
prob_excedencia = (np.arange(1, len(q_sorted) + 1) / (len(q_sorted) + 1)) * 100

q50 = np.percentile(df_mensual['Q_m3s'].dropna(), 100 - 50)
q75 = np.percentile(df_mensual['Q_m3s'].dropna(), 100 - 75)
q90 = np.percentile(df_mensual['Q_m3s'].dropna(), 100 - 90)
q95 = np.percentile(df_mensual['Q_m3s'].dropna(), 100 - 95)

print("\n" + "="*58)
print("   RESULTADOS MODELO CHAC - RÍO LA MUMA")
print("="*58)
print(f"Caudal Promedio Multianual: {df_mensual['Q_m3s'].mean():.3f} m³/s")
print(f"Caudal Mínimo Mensual:     {df_mensual['Q_m3s'].min():.3f} m³/s")
print(f"Caudal Máximo Mensual:     {df_mensual['Q_m3s'].max():.3f} m³/s")
print(f"Caudal de Garantía Q50%:   {q50:.3f} m³/s")
print(f"Caudal de Garantía Q75%:   {q75:.3f} m³/s")
print(f"Caudal de Garantía Q90%:   {q90:.3f} m³/s")
print(f"Caudal de Garantía Q95%:   {q95:.3f} m³/s")

# Validación en los meses de aforo de campo
q_jun_2011 = df_mensual.loc['2011-06-01', 'Q_m3s'] if '2011-06-01' in df_mensual.index else np.nan
q_oct_2013 = df_mensual.loc['2013-10-01', 'Q_m3s'] if '2013-10-01' in df_mensual.index else np.nan

print("\n" + "="*58)
print("   VALIDACIÓN CON AFOROS DE CAMPO")
print("="*58)
if not np.isnan(q_jun_2011):
    print(f"Junio 2011:")
    print(f"  - Medido (Aforo 08/06/2011): 0.171 m³/s")
    print(f"  - Modelado CHAC:            {q_jun_2011:.3f} m³/s")
    print(f"  - Error relativo:           {abs(q_jun_2011 - 0.171) / 0.171 * 100:.1f} %")

if not np.isnan(q_oct_2013):
    print(f"\nOctubre 2013:")
    print(f"  - Medido (Aforo 08/10/2013): 0.194 m³/s")
    print(f"  - Modelado CHAC:            {q_oct_2013:.3f} m³/s")
    print(f"  - Error relativo:           {abs(q_oct_2013 - 0.194) / 0.194 * 100:.1f} %")
print("="*58)

# ==============================================================================
# 4. GRÁFICOS (ESTILO COMPATIBLE CON LUTZ SCHOLZ)
# ==============================================================================
fig, axs = plt.subplots(3, 1, figsize=(12, 12))

# Subplot 1: Hidrograma Serie Completa
axs[0].plot(df_mensual.index, df_mensual['Q_m3s'], color='#1f77b4', lw=1.2, label='Caudal Simulado CHAC (m³/s)')
axs[0].axhline(df_mensual['Q_m3s'].mean(), color='firebrick', linestyle='--', lw=1.0, 
              label=f"Media Multianual ({df_mensual['Q_m3s'].mean():.3f} m³/s)")
axs[0].set_title('Hidrograma Mensual Modelo CHAC - Río La Muma', fontsize=12, fontweight='bold')
axs[0].set_ylabel('Caudal (m³/s)')
axs[0].grid(True, linestyle=':', alpha=0.6)
axs[0].legend(loc='upper right')

# Subplot 2: Régimen Medio Mensual Multianual
df_mensual['Mes'] = df_mensual.index.month
regimen_total = df_mensual.groupby('Mes')['Q_m3s'].mean()
meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

axs[1].bar(meses_nombres, regimen_total.values, color='#4682b4', alpha=0.85, edgecolor='black', label='Caudal Total CHAC')
axs[1].plot(meses_nombres, regimen_total.values, color='#d95f02', marker='o', lw=2, label='Perfil Medio Mensual')
axs[1].set_title('Régimen Medio Mensual Multianual (m³/s) - CHAC', fontsize=12, fontweight='bold')
axs[1].set_ylabel('Caudal Medio (m³/s)')
axs[1].grid(True, axis='y', linestyle=':', alpha=0.6)
axs[1].legend(loc='upper right')

# Subplot 3: Curva de Duración de Caudales (FDC)
axs[2].plot(prob_excedencia, q_sorted, color='#2ca02c', lw=2.2)
axs[2].axvline(50, color='gray', linestyle='--', alpha=0.7, label=f'Q50 = {q50:.3f} m³/s')
axs[2].axvline(75, color='orange', linestyle='--', alpha=0.7, label=f'Q75 = {q75:.3f} m³/s')
axs[2].axvline(90, color='red', linestyle='--', alpha=0.7, label=f'Q90 = {q90:.3f} m³/s')
axs[2].axvline(95, color='purple', linestyle='--', alpha=0.7, label=f'Q95 = {q95:.3f} m³/s')
axs[2].set_title('Curva de Duración de Caudales (FDC) - Modelo CHAC', fontsize=12, fontweight='bold')
axs[2].set_xlabel('Probabilidad de Excedencia (%)')
axs[2].set_ylabel('Caudal (m³/s)')
axs[2].grid(True, linestyle=':', alpha=0.6)
axs[2].legend(loc='upper right')

plt.tight_layout()
plt.subplots_adjust(hspace=0.35, top=0.95, bottom=0.08)
plt.show()