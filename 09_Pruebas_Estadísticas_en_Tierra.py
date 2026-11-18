import os
import pandas as pd
import numpy as np
from scipy import stats

# Configuración de rutas
ruta_principal = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1"
archivo_maestro = os.path.join(ruta_principal, "serie_maestra_calibracion_2011_2013.xlsx")

# Cargar la serie maestra que creamos antes
df = pd.read_excel(archivo_maestro, index_col=0, parse_dates=True)

# Seleccionar solo las estaciones en tierra activas para evaluar
estaciones_activas = ['CHOROCONA', 'CIRCUATA', 'CONCHAMARCA', 'LURIBAY']

print("=========================================================================")
print("  EJECUTANDO PRUEBAS ESTADÍSTICAS DE CALIDAD EN TIERRA (VENTANA 2011-2013)")
print("=========================================================================")

resultados_estadisticos = []

for est in estaciones_activas:
    # Eliminar valores faltantes (NaN) solo para la prueba estadística de esa estación
    serie_limpia = df[est].dropna()
    
    if len(serie_limpia) < 100:
        print(f"-> {est}: Datos insuficientes para pruebas estadísticas.")
        continue
        
    # --- 1. PRUEBA DE ALEATORIEDAD (Runs Test / Prueba de Rachas) ---
    # Clasificamos los datos según estén por encima o por debajo de la mediana
    mediana = serie_limpia.median()
    dicotómico = (serie_limpia > mediana).astype(int)
    
    # Contamos las rachas (bloques continuos de 0s o 1s)
    cambios = dicotómico.diff().fillna(0) != 0
    num_rachas = cambios.sum() + 1
    n1 = (dicotómico == 1).sum()
    n2 = (dicotómico == 0).sum()
    
    # Esperanza matemática y varianza de las rachas
    mu_r = ((2 * n1 * n2) / (n1 + n2)) + 1
    var_r = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / (((n1 + n2)**2) * (n1 + n2 - 1))
    z_stat = (num_rachas - mu_r) / np.sqrt(var_r)
    p_value_rachas = 2 * (1 - stats.norm.cdf(abs(z_stat))) # P-valor bilateral
    
    status_rachas = "Aleatoria (Confiable)" if p_value_rachas > 0.05 else "No Aleatoria (Revisar)"
    
    # --- 2. PRUEBA DE HOMOGENEIDAD PRELIMINAR (Diferencia de Medias de dos periodos) ---
    # Dividimos la serie de 3 años en dos mitades y comparamos si sus medias cambiaron drásticamente
    mitad = len(serie_limpia) // 2
    grupo1 = serie_limpia.iloc[:mitad]
    grupo2 = serie_limpia.iloc[mitad:]
    
    stat_t, p_value_homog = stats.ttest_ind(grupo1, grupo2, equal_var=False)
    status_homog = "Homogénea (Confiable)" if p_value_homog > 0.05 else "No Homogénea (Quiebre sospechoso)"
    
    # Guardar resultados
    resultados_estadisticos.append({
        'Estación': est,
        'P-Valor Rachas': round(p_value_rachas, 4),
        'Estado Aleatoriedad': status_rachas,
        'P-Valor Homogeneidad': round(p_value_homog, 4),
        'Estado Homogeneidad': status_homog
    })

# Mostrar resultados tabulados en la consola
df_pruebas = pd.DataFrame(resultados_estadisticos)
df_pruebas.to_excel(os.path.join(ruta_principal, "tabla_4_1_pruebas_estadisticas.xlsx"), index=False)
print(df_pruebas.to_string(index=False))
print("=========================================================================")
print("[Éxito] Tabla guardada como 'tabla_4_1_pruebas_estadisticas.xlsx' para tu documento.")
