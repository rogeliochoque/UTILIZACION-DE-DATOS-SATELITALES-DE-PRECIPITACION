import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gumbel_r, genextreme, pearson3, lognorm, kstest

# 1. CONFIGURACIÓN DE RUTAS
ruta_max_anuales = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales maximos\pruebas de bondad\maximos_anuales_24h.csv"
carpeta_salida = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales maximos\pruebas de bondad"
ruta_reporte = os.path.join(carpeta_salida, "reporte_bondad_ajuste_ampliado.txt")
ruta_grafico = os.path.join(carpeta_salida, "grafico_ajuste_5_distribuciones.png")

# Leer datos
df = pd.read_csv(ruta_max_anuales)
datos = np.sort(df['P_max_24h_mm'].values)
n = len(datos)

# Periodos de retorno a calcular
periodos_retorno = np.array([2, 5, 10, 25, 50, 100])
prob_acum = 1.0 - (1.0 / periodos_retorno)

# =============================================================================
# 2. AJUSTE DE LAS 5 DISTRIBUCIONES Y PRUEBA K-S
# =============================================================================

# A) GUMBEL
p_gumbel = gumbel_r.fit(datos)
ks_gumbel, pval_gumbel = kstest(datos, 'gumbel_r', args=p_gumbel)
q_gumbel = gumbel_r.ppf(prob_acum, *p_gumbel)

# B) GEV
p_gev = genextreme.fit(datos)
ks_gev, pval_gev = kstest(datos, 'genextreme', args=p_gev)
q_gev = genextreme.ppf(prob_acum, *p_gev)

# C) LOG-PEARSON III
log_datos = np.log10(datos)
p_lp3 = pearson3.fit(log_datos)
ks_lp3, pval_lp3 = kstest(log_datos, 'pearson3', args=p_lp3)
q_lp3 = 10**(pearson3.ppf(prob_acum, *p_lp3))

# D) LOG-NORMAL (2 Parámetros)
p_lognorm = lognorm.fit(datos, floc=0) # Fijamos loc=0 para la forma estándar
ks_lognorm, pval_lognorm = kstest(datos, 'lognorm', args=p_lognorm)
q_lognorm = lognorm.ppf(prob_acum, *p_lognorm)

# E) PEARSON III (Normal)
p_p3 = pearson3.fit(datos)
ks_p3, pval_p3 = kstest(datos, 'pearson3', args=p_p3)
q_p3 = pearson3.ppf(prob_acum, *p_p3)

# =============================================================================
# 3. COMPILAR REPORTE Y CONSOLA
# =============================================================================
tabla_res = pd.DataFrame({
    'T_años': periodos_retorno,
    'Gumbel_mm': q_gumbel,
    'GEV_mm': q_gev,
    'LogPearson3_mm': q_lp3,
    'LogNormal_mm': q_lognorm,
    'Pearson3_mm': q_p3
})

print("\n🏆 RESULTADOS DEL ANÁLISIS DE FRECUENCIA AMPLIADO 🏆")
print("=" * 85)
print(f"-> Gumbel:       KS = {ks_gumbel:.4f} | p-valor = {pval_gumbel:.4f}")
print(f"-> GEV:          KS = {ks_gev:.4f} | p-valor = {pval_gev:.4f}")
print(f"-> Log-Pearson3: KS = {ks_lp3:.4f} | p-valor = {pval_lp3:.4f}")
print(f"-> Log-Normal:   KS = {ks_lognorm:.4f} | p-valor = {pval_lognorm:.4f}")
print(f"-> Pearson3:     KS = {ks_p3:.4f} | p-valor = {pval_p3:.4f}")
print("=" * 85)
print(tabla_res.to_string(index=False, formatters={
    'Gumbel_mm': '{:.2f}'.format, 'GEV_mm': '{:.2f}'.format, 'LogPearson3_mm': '{:.2f}'.format,
    'LogNormal_mm': '{:.2f}'.format, 'Pearson3_mm': '{:.2f}'.format
}))
print("=" * 85)

# Guardar TXT
with open(ruta_reporte, 'w', encoding='utf-8') as f:
    f.write("=== REPORTE COMPARATIVO DE DISTRIBUCIONES HIDROLÓGICAS ===\n\n")
    f.write(f"Gumbel:       KS = {ks_gumbel:.4f}, p-val = {pval_gumbel:.4f}\n")
    f.write(f"GEV:          KS = {ks_gev:.4f}, p-val = {pval_gev:.4f}\n")
    f.write(f"Log-Pearson3: KS = {ks_lp3:.4f}, p-val = {pval_lp3:.4f}\n")
    f.write(f"Log-Normal:   KS = {ks_lognorm:.4f}, p-val = {pval_lognorm:.4f}\n")
    f.write(f"Pearson3:     KS = {ks_p3:.4f}, p-val = {pval_p3:.4f}\n\n")
    f.write(tabla_res.to_string(index=False))

# =============================================================================
# 4. GRÁFICO COMPARATIVO DE ALTA CALIDAD
# =============================================================================
pos_grafica = (np.arange(1, n + 1) - 0.4) / (n + 0.2)
T_empiricos = 1.0 / (1.0 - pos_grafica)

plt.figure(figsize=(11, 6), dpi=300)
plt.scatter(T_empiricos, datos, color='black', edgecolor='white', s=60, zorder=5, label='Datos MSWEP Saneados')

T_cont = np.linspace(1.1, 120, 200)
p_cont = 1.0 - (1.0 / T_cont)

plt.plot(T_cont, gumbel_r.ppf(p_cont, *p_gumbel), color='#e74c3c', linewidth=2, label='Gumbel')
plt.plot(T_cont, genextreme.ppf(p_cont, *p_gev), color='#2ecc71', linewidth=2, label='GEV')
plt.plot(T_cont, 10**(pearson3.ppf(p_cont, *p_lp3)), color='#f1c40f', linewidth=2, linestyle='--', label='Log-Pearson III')
plt.plot(T_cont, lognorm.ppf(p_cont, *p_lognorm), color='#3498db', linewidth=1.5, linestyle=':', label='Log-Normal')
plt.plot(T_cont, pearson3.ppf(p_cont, *p_p3), color='#9b59b6', linewidth=1.5, linestyle='-.', label='Pearson III')

plt.xscale('log')
plt.xlim(1, 150)
plt.xticks(ticks_T := [2, 5, 10, 25, 50, 100], [str(t) for t in ticks_T])
plt.title('Comparación de Modelos Teóricos de Frecuencia Extrema (Río La Muma)', fontsize=13, fontweight='bold', pad=15)
plt.xlabel('Periodo de Retorno T (Años)', fontsize=11)
plt.ylabel('Precipitación Máxima en 24h (mm)', fontsize=11)
plt.grid(True, which="both", linestyle='--', alpha=0.4)
plt.legend(loc='upper left', frameon=True, facecolor='white')

plt.tight_layout()
plt.savefig(ruta_grafico, bbox_inches='tight')
plt.close()

print(f"🖼️ Gráfico de 5 distribuciones guardado en:\n👉 {ruta_grafico}")