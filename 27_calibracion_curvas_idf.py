import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. DATOS DE ENTRADA (Tus resultados de Log-Pearson III)
periodos_retorno = np.array([5, 10, 25, 50, 100])
# Valores de lluvia en 24h obtenidos con Log-Pearson III
P_24h_LP3 = np.array([23.04, 26.16, 30.04, 32.89, 35.72]) 

# Exponentes originales de la estación AASANA
m_regional = 0.204
n_regional = 0.636
D_24h_min = 1440.0 # 24 horas en minutos

# 2. CALIBRACIÓN DEL COEFICIENTE 'k' LOCAL
# Despejando k para cada T: k = (P_24h / 24) * (D^n) / (T^m)
I_24h = P_24h_LP3 / 24.0 # Intensidad en mm/h para 24 horas
k_valores = (I_24h * (D_24h_min**n_regional)) / (periodos_retorno**m_regional)

# Promediamos los k para obtener el coeficiente único de la cuenca
k_cuenca = np.mean(k_valores)

print("=" * 60)
print(f"🚀 ¡ECUACIÓN IDF DEDUCIDA PARA EL RÍO LA MUMA!")
print("=" * 60)
print(f"Fórmula matemática calibrada:")
print(f"   I = {k_cuenca:.4f} * (T^{m_regional}) / (D^{n_regional})")
print("=" * 60)
print(f"Donde:\n - I: Intensidad en mm/h\n - T: Periodo de retorno en años\n - D: Duración en minutos")
print("=" * 60)

# 3. GENERACIÓN DE LA TABLA IDF Y GRÁFICO
duraciones = np.array([5, 10, 15, 30, 45, 60, 120, 180, 360, 720, 1440]) # en minutos

plt.figure(figsize=(10, 6), dpi=300)
colores = ['#264653', '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51']

# Calcular intensidades y graficar curvas
for i, T in enumerate(periodos_retorno):
    # Aplicar la nueva fórmula deducida
    intensidades = (k_cuenca * (T**m_regional)) / (duraciones**n_regional)
    
    # Graficar
    plt.plot(duraciones, intensidades, color=colores[i], linewidth=2, label=f"T = {T} años")
    
# Configuración estética del gráfico IDF
plt.title('Curvas Intensidad - Duración - Frecuencia (IDF) Calibradas para la Cuenca Río La Muma', fontsize=12, fontweight='bold', pad=15)
plt.xlabel('Duración D (Minutos)', fontsize=11)
plt.ylabel('Intensidad I (mm/h)', fontsize=11)
plt.xlim(5, 120) # Enfocado en las duraciones críticas de respuesta (tiempo de concentración de 2 horas = 120 min)
plt.grid(True, which="both", linestyle='--', alpha=0.5)
plt.legend(loc='upper right', frameon=True)

ruta_grafico_idf = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales maximos\3_IDF\curvas_IDF_La_Muma.png"
plt.tight_layout()
plt.savefig(ruta_grafico_idf, bbox_inches='tight')
plt.close()

print(f"🖼️ Gráfico de Curvas IDF guardado en:\n👉 {ruta_grafico_idf}\n")