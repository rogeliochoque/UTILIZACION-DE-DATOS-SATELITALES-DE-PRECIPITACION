import os
import pandas as pd
import numpy as np

# =============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y ARCHIVOS LOCALES
# =============================================================================
ruta_principal = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1"
ruta_senamhi = os.path.join(ruta_principal, "datos_senamhi")

# Nombre real del archivo y su hoja interna según tus precisiones
archivo_satelite = os.path.join(ruta_principal, "datos_de_los_satelites.xlsx")
hoja_satelite = "datos"

ruta_resultados = ruta_principal

# Ventana temporal de coincidencia simultánea (Contiene tus aforos de 2011 y 2013)
fecha_inicio = "2011-01-01"
fecha_fin = "2013-12-31"
periodo_ventana = pd.date_range(start=fecha_inicio, end=fecha_fin)

print(f"Verificando archivo satelital en: {archivo_satelite}")
print("=== CRUCE DE PÍXEL DE OBRA DE TOMA VS TIERRA (2011-2013) ===")

# =============================================================================
# 2. LECTURA DE DATOS SATELITALES (PÍXEL DE LA OBRA DE TOMA)
# =============================================================================
if not os.path.exists(archivo_satelite):
    # Si no está en la principal, intentamos en la subcarpeta por si acaso
    archivo_satelite = os.path.join(ruta_senamhi, "datos_de_los_satelites.xlsx")
    if not os.path.exists(archivo_satelite):
        raise FileNotFoundError(f"No se encontró el archivo 'datos_de_los_satelites.xlsx' en ninguna de las rutas.")

# Cargar la hoja "datos" del archivo satelital
df_sat = pd.read_excel(archivo_satelite, sheet_name=hoja_satelite)

# Limpiar espacios en los nombres de las columnas (fecha, CHIRPS, ERA5, MSWEP)
df_sat.columns = df_sat.columns.str.strip()

# Asegurar que la primera columna se llame 'fecha' en minúsculas para indexar
if 'fecha' in df_sat.columns:
    df_sat['fecha'] = pd.to_datetime(df_sat['fecha'])
    df_sat.set_index('fecha', inplace=True)
else:
    # Si la primera columna tiene otro nombre (ej. 'Fecha'), la forzamos
    df_sat.iloc[:, 0] = pd.to_datetime(df_sat.iloc[:, 0])
    df_sat.set_index(df_sat.columns[0], inplace=True)
    df_sat.index.name = 'fecha'

# Filtrar el satélite estrictamente para el trienio de diseño
df_sat_ventana = df_sat.loc[fecha_inicio:fecha_fin, ['CHIRPS', 'ERA5', 'MSWEP']].copy()

# =============================================================================
# 3. LECTURA DE LAS ESTACIONES TERRESTRES
# =============================================================================
estaciones_interes = ['capinata', 'caxata', 'chorocona', 'circuata', 'conchamarca', 'luribay', 'quime']
df_tierra_consolidado = pd.DataFrame(index=periodo_ventana)

for est in estaciones_interes:
    archivo_tierra = os.path.join(ruta_senamhi, f"dato_diarios_{est}.xlsx")
    if os.path.exists(archivo_tierra):
        # Leer usando la hoja 'datos' compartida por SENAMHI
        df_t_raw = pd.read_excel(archivo_tierra, sheet_name='datos')
        
        # Reconstruir fecha nativa uniendo columnas del SENAMHI
        df_t_raw['Fecha'] = pd.to_datetime(pd.DataFrame({
            'year': df_t_raw['gestion'],
            'month': df_t_raw['mes'],
            'day': df_t_raw['dia']
        }))
        
        col_p = 'Precipitación' if 'Precipitación' in df_t_raw.columns else 'Precipitacion'
        df_t_fil = df_t_raw[['Fecha', col_p]].copy()
        df_t_fil.columns = ['Fecha', est.upper()]
        df_t_fil.set_index('Fecha', inplace=True)
        
        # Unir a la matriz temporal de tierra
        df_tierra_consolidado = df_tierra_consolidado.join(df_t_fil, how='left')
    else:
        print(f"⚠️ Archivo no encontrado para la estación: dato_diarios_{est}.xlsx")

# =============================================================================
# 4. CONSOLIDACIÓN DE MATRIZ MAESTRA Y ESTADÍSTICA ANUAL
# =============================================================================
df_maestra = df_sat_ventana.join(df_tierra_consolidado, how='left')

# Guardar la serie limpia en tu carpeta de resultados para el modelo de caudales
archivo_final_xlsx = os.path.join(ruta_resultados, "serie_maestra_calibracion_2011_2013.xlsx")
df_maestra.to_excel(archivo_final_xlsx)
print(f"\n[Éxito] ¡Excelente! Serie diaria 2011-2013 guardada en:\n-> {archivo_final_xlsx}")

# Calcular e imprimir los acumulados promedio anuales en la consola
print("\n========================================================")
print(" ACUMULADOS ANUALES PROMEDIO EN TU VENTANA (mm/año)")
print("========================================================")
resumen_anual = df_maestra.resample('YE').sum()
resumen_promedio = resumen_anual.mean()

for col, val in resumen_promedio.items():
    # Detectar si una estación física no tiene datos continuos en este trienio específico
    # (Como Quime, Caxata o Capiñata si se confirmara que cerraron antes)
    dias_validos_trienio = df_maestra[col].notna().sum()
    
    # Si tiene menos del 50% de días en los 3 años, sus sumas anuales no reflejan la realidad
    if col not in ['CHIRPS', 'ERA5', 'MSWEP'] and dias_validos_trienio < 500:
        print(f"-> Estación {col:<12}: Inactiva o con vacíos severos en este trienio.")
    else:
        print(f"-> {col:<15}: {round(val, 1)} mm/año")
print("========================================================")
