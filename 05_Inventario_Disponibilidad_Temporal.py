import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# =============================================================================
# 1. CONFIGURACIÓN DE RUTAS Y ENTORNO
# =============================================================================
# Definimos la ruta de trabajo proporcionada
ruta_datos = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\datos_senamhi"
os.chdir(ruta_datos)

print(f"Dirección de trabajo establecida en: {os.getcwd()}")

# =============================================================================
# 2. CONSOLIDACIÓN AUTOMÁTICA DE ARCHIVOS EXCEL
# =============================================================================
# Buscamos todos los archivos que empiecen con 'dato_diarios_' y terminen en .xlsx o .xls
archivos_excel = glob.glob(os.path.join(ruta_datos, "dato_diarios_*.xlsx")) + \
                 glob.glob(os.path.join(ruta_datos, "dato_diarios_*.xls"))

if not archivos_excel:
    raise FileNotFoundError("No se encontraron archivos con el patrón 'dato_diarios_' en la ruta especificada.")

listado_dfs = []
catalogo_estaciones = []

print("\nCargando y procesando estaciones del SENAMHI:")
for archivo in archivos_excel:
    # Leer el archivo (asumimos primera hoja, si varía cambiar 'sheet_name')
    df_temp = pd.read_excel(archivo, sheet_name=0)
    
    # Extraer el nombre de la estación desde la primera fila válida de la columna 'estacion'
    nombre_estacion = df_temp['estacion'].dropna().iloc[0].strip()
    print(f"-> Procesando estación: {nombre_estacion}")
    
    # Extraer y guardar metadatos geográficos únicos
    lat = df_temp['latitud'].dropna().iloc[0]
    lon = df_temp['longitud'].dropna().iloc[0]
    alt = df_temp['altura'].dropna().iloc[0]
    catalogo_estaciones.append({
        'Estacion': nombre_estacion, 'Latitud': lat, 'Longitud': lon, 'Altura_msnm': alt
    })
    
    # Construir columna de Fecha uniendo gestion, mes y dia
    df_temp['Fecha'] = pd.to_datetime(pd.DataFrame({
        'year': df_temp['gestion'],
        'month': df_temp['mes'],
        'day': df_temp['dia']
    }))
    
    # Quedarnos solo con Fecha y Precipitación, renombrando la columna con el nombre de la estación
    df_filtrado = df_temp[['Fecha', 'Precipitación']].copy() if 'Precipitación' in df_temp.columns else df_temp[['Fecha', 'Precipitacion']].copy()
    df_filtrado.columns = ['Fecha', nombre_estacion]
    
    # Manejar posibles duplicados de fechas si existieran
    df_filtrado = df_filtrado.drop_duplicates(subset=['Fecha']).set_index('Fecha')
    listado_dfs.append(df_filtrado)

# Crear la Gran Matriz de Precipitación en Tierra (Indexada por fechas desde el mínimo al máximo global)
df_precip_total = pd.concat(listado_dfs, axis=1)
df_precip_total = df_precip_total.sort_index()

# Salvar catálogo de metadatos
df_catalogo = pd.DataFrame(catalogo_estaciones)
df_catalogo.to_excel("tabla_4_1_catalogo_estaciones.xlsx", index=False)

# =============================================================================
# 3. ANÁLISIS DE COMPLETITUD Y DIAGNÓSTICO (PUNTO 4.1.1)
# =============================================================================
resumen_calidad = []
for est in df_precip_total.columns:
    serie_estacion = df_precip_total[est]
    fechas_con_datos = serie_estacion.dropna().index
    
    inicio = fechas_con_datos.min().strftime('%Y-%m-%d') if not fechas_con_datos.empty else "N/A"
    fin = fechas_con_datos.max().strftime('%Y-%m-%d') if not fechas_con_datos.empty else "N/A"
    
    total_dias_periodo = len(serie_estacion)
    vacios = serie_estacion.isna().sum()
    pct_vacios = (vacios / total_dias_periodo) * 100
    
    resumen_calidad.append({
        'Estación': est, 'Inicio Registro': inicio, 'Fin Registro': fin,
        'Días Totales': total_dias_periodo, 'Días Faltantes': vacios, '% Faltantes': round(pct_vacios, 2)
    })

df_resumen_final = pd.DataFrame(resumen_calidad)
df_resumen_final.to_excel("tabla_4_1_1_diagnostico_completitud.xlsx", index=False)

print("\n=== TABLA METODOLÓGICA DE COMPLETITUD GENERADA ===")
print(df_resumen_final.to_string(index=False))

# =============================================================================
# 4. GRÁFICO CIENTÍFICO DE DISPONIBILIDAD TEMPORAL (PUNTO 4.1.2)
# =============================================================================
plt.figure(figsize=(14, 7))
# Estilos tipográficos y visuales de alta calidad para la tesis
plt.rcParams['font.family'] = 'sans-serif'

estaciones_ordenadas = list(df_precip_total.columns)[::-1]

for idx, est in enumerate(estaciones_ordenadas):
    dias_validos = df_precip_total[est].dropna().index
    # Pintamos una línea densa por cada día que tiene registro efectivo
    plt.scatter(dias_validos, [idx] * len(dias_validos), 
                marker='|', color='#1f77b4', alpha=0.6, s=150, label=est if idx==0 else "")

plt.yticks(range(len(estaciones_ordenadas)), estaciones_ordenadas, fontsize=11, fontweight='bold', color='#2c3e50')
plt.xlabel("Línea de Tiempo Pluviométrica (Registros Diarios)", fontsize=12, fontweight='bold', labelpad=12)
plt.title("ANÁLISIS DE DISPONIBILIDAD TEMPORAL HISTÓRICA (PERIODO 1975 - 2020)\nEstaciones Meteorológicas de la Red de Control Regional - Caso Río La Muma", 
          fontsize=13, pad=18, fontweight='bold', color='#2c3e50')

plt.gca().xaxis.set_major_locator(mdates.YearLocator(5))
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
plt.grid(axis='x', linestyle='--', alpha=0.5, color='gray')

plt.xlim(pd.to_datetime('1975-01-01'), pd.to_datetime('2020-12-31'))
plt.tight_layout()

# Guardar vectorizado o en alta densidad (300 DPI) directo en la carpeta
plt.savefig("grafico_4_1_2_disponibilidad_temporal.png", dpi=300)
print("\n[Éxito] Gráfico de disponibilidad guardado como 'grafico_4_1_2_disponibilidad_temporal.png'")
plt.show()
