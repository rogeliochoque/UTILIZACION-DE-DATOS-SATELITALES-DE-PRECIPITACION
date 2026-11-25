import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. PARÁMETROS DE ENTRADA
T = 100               # Tiempo de retorno en años (puedes cambiarlo a 25 o 50)
duracion_total = 120  # Duración de la tormenta en minutos (2 horas)
dt = 10                # Intervalo de tiempo en minutos

# 2. DEFINICIÓN DE TIEMPOS
tiempos = np.arange(dt, duracion_total + dt, dt) 

# 3. FUNCIÓN IDF DEL PROYECTO
def calcular_intensidad(T, D):
    return 65.7167 * (T**0.204) / (D**0.636)

# 4. CÁLCULO DE PRECIPITACIÓN ACUMULADA Y PARCIAL
intensidades_acum = calcular_intensidad(T, tiempos)
P_acum = intensidades_acum * (tiempos / 60.0)

# Precipitación en cada bloque (parcial en mm)
P_parcial = np.zeros(len(P_acum))
P_parcial[0] = P_acum[0]
for i in range(1, len(P_acum)):
    P_parcial[i] = P_acum[i] - P_acum[i - 1]

# 5. ALGORITMO DEL BLOQUE ALTERNO (Aplicado directamente a la precipitación en mm)
indices_ordenados = np.argsort(P_parcial)[::-1]
P_ordenada = P_parcial[indices_ordenados]

hietograma_mm = np.zeros(len(P_parcial))
centro = len(P_parcial) // 2

izq = centro - 1
der = centro
ir_a_la_derecha = True

for i in range(len(P_ordenada)):
    if ir_a_la_derecha:
        if der < len(hietograma_mm):
            hietograma_mm[der] = P_ordenada[i]
            der += 1
        else:
            hietograma_mm[izq] = P_ordenada[i]
            izq -= 1
        ir_a_la_derecha = False
    else:
        if izq >= 0:
            hietograma_mm[izq] = P_ordenada[i]
            izq -= 1
        else:
            hietograma_mm[der] = P_ordenada[i]
            der += 1
        ir_a_la_derecha = True

# 6. CREACIÓN DE DATAFRAME CORREGIDO (En mm enteros de tiempo)
minutos_inicio = np.linspace(0, duracion_total - dt, len(hietograma_mm), dtype=int)
minutos_fin = minutos_inicio + dt

df_resultados = pd.DataFrame({
    'Minuto_Inicio': minutos_inicio,
    'Minuto_Fin': minutos_fin,
    'Precipitacion_mm': hietograma_mm
})

print(f"--- HIETOGRAMA DE DISEÑO PARA T = {T} AÑOS ---")
print(df_resultados.to_string(index=False))
print(f"\nPrecipitación total de la tormenta: {hietograma_mm.sum():.2f} mm")

# 7. GRÁFICO EN MILÍMETROS
plt.figure(figsize=(10, 5), dpi=150)
plt.bar(df_resultados['Minuto_Inicio'] + dt/2, df_resultados['Precipitacion_mm'], 
        width=dt, color='#1f77b4', edgecolor='black', alpha=0.85, label=f'Lluvia por bloque (T = {T} años)')

plt.title(f'Hietograma de Diseño - Bloque Alterno (Precipitación en mm)', fontsize=13, fontweight='bold', pad=15)
plt.xlabel('Tiempo (minutos)', fontsize=11)
plt.ylabel('Precipitación por bloque (mm)', fontsize=11)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.xlim(0, duracion_total)
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()