"""
Proyecto: Tesis de Maestría - PCH Río La Muma, Municipio de Ichoca
Script: rellena_datos.py
Ubicación: D:\tesis hidrologia\CAP_4\ANALISIS4_1\datos_senamhi
Descripción: Diagnóstico de completitud e imputación de datos diarios faltantes
             en la estación Quime (1993-2002) mediante el Método de la Razón Normal (OMM).
"""

import os
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE RUTAS Y CONSTANTES
# ---------------------------------------------------------
DIR_TRABAJO = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\datos_senamhi"
FECHA_INICIO = "1993-01-01"
FECHA_FIN = "2002-12-31"
ESTACION_OBJETIVO = "Quime"

ARCHIVOS_ESTACIONES = [
    "dato_diarios_capinata.xlsx",
    "dato_diarios_caxata.xlsx",
    "dato_diarios_chorocona.xlsx",
    "dato_diarios_circuata.xlsx",
    "dato_diarios_conchamarca.xlsx",
    "dato_diarios_luribay.xlsx",
    "dato_diarios_quime.xlsx"
]

def cargar_y_estandarizar(ruta_archivo):
    """Lee el archivo Excel del SENAMHI y construye una serie con índice de fecha diario."""
    df = pd.read_excel(ruta_archivo)
    
    # Normalizar nombres de columnas eliminando espacios y acentos comunes
    df.columns = df.columns.str.strip()
    col_precip = [c for c in df.columns if "precip" in c.lower()][0]
    
    # Construcción de la columna Fecha
    df["Fecha"] = pd.to_datetime(
        df["gestion"].astype(str) + "-" + 
        df["mes"].astype(str) + "-" + 
        df["dia"].astype(str), 
        format="%Y-%m-%d", 
        errors="coerce"
    )
    
    df = df.dropna(subset=["Fecha"])
    nombre_est = str(df["estacion"].iloc[0]).strip()
    
    # Convertir precipitación a numérico (trata vacíos, -99.9, strings como NaN)
    df[col_precip] = pd.to_numeric(df[col_precip], errors="coerce")
    df.loc[df[col_precip] < 0, col_precip] = np.nan
    
    serie_diaria = df.set_index("Fecha")[col_precip].rename(nombre_est)
    
    # Metadatos
    cota = df["altura"].iloc[0] if "altura" in df.columns else np.nan
    lat = df["latitud"].iloc[0] if "latitud" in df.columns else np.nan
    lon = df["longitud"].iloc[0] if "longitud" in df.columns else np.nan
    
    return serie_diaria, {"nombre": nombre_est, "cota": cota, "lat": lat, "lon": lon}

# ---------------------------------------------------------
# 2. CONSOLIDACIÓN DE LA MATRIZ DE PRECIPITACIÓN (1993-2002)
# ---------------------------------------------------------
print("=" * 75)
print("  PROCESANDO ESTACIONES METEOROLÓGICAS - SENAMHI (1993 - 2002)")
print("=" * 75)

rango_completo = pd.date_range(start=FECHA_INICIO, end=FECHA_FIN, freq="D")
matriz_precip = pd.DataFrame(index=rango_completo)
metadatos = {}

for archivo in ARCHIVOS_ESTACIONES:
    ruta_completa = os.path.join(DIR_TRABAJO, archivo)
    if os.path.exists(ruta_completa):
        serie, meta = cargar_y_estandarizar(ruta_completa)
        matriz_precip = matriz_precip.join(serie, how="left")
        metadatos[meta["nombre"]] = meta
        print(f" -> Cargada con éxito: {meta['nombre']:<15} (Cota: {meta['cota']} m s.n.m.)")
    else:
        print(f" [!] Advertencia: No se encontró el archivo: {archivo}")

# Buscar la columna exacta de Quime
col_quime = [c for c in matriz_precip.columns if ESTACION_OBJETIVO.lower() in c.lower()]
if not col_quime:
    raise ValueError(f"No se encontró la estación {ESTACION_OBJETIVO} en los archivos procesados.")
col_quime = col_quime[0]

# ---------------------------------------------------------
# 3. DIAGNÓSTICO DE FACTIBILIDAD Y COMPLETITUD SEGÚN LA OMM
# ---------------------------------------------------------
total_dias = len(matriz_precip)
dias_quime_validos = matriz_precip[col_quime].notna().sum()
dias_quime_nulos = matriz_precip[col_quime].isna().sum()
pct_nulos = (dias_quime_nulos / total_dias) * 100

print("\n" + "-" * 75)
print("  EVALUACIÓN DE FACTIBILIDAD DE QUIME (CRITERIOS TÉCNICOS OMM)")
print("-" * 75)
print(f" * Periodo de análisis          : {FECHA_INICIO} al {FECHA_FIN} (10 años)")
print(f" * Total de días teóricos       : {total_dias}")
print(f" * Días con registro observado  : {dias_quime_validos} ({(dias_quime_validos/total_dias)*100:.2f} %)")
print(f" * Días con vacíos / faltantes  : {dias_quime_nulos} ({pct_nulos:.2f} %)")

# Diagnóstico por año
resumen_anual = matriz_precip[col_quime].isna().groupby(matriz_precip.index.year).agg(
    dias_totales="count",
    dias_faltantes="sum"
)
resumen_anual["pct_faltante"] = (resumen_anual["dias_faltantes"] / resumen_anual["dias_totales"]) * 100

print("\n Desglose Anual de Faltantes en Quime:")
for anio, fila in resumen_anual.iterrows():
    print(f"   - Año {anio}: {int(fila['dias_faltantes']):>3} días faltantes ({fila['pct_faltante']:>5.1f} %)")

# Dictamen
print("\n" + "=" * 75)
if pct_nulos < 25.0:
    print(" [DICTAMEN OMM: FACTIBLE Y RECOMENDADO]")
    print(f" La estación {col_quime} presenta un porcentaje de vacíos del {pct_nulos:.2f}% (< 25%),")
    print(" lo que permite la reconstrucción robusta mediante el Método de la Razón Normal.")
else:
    print(" [DICTAMEN OMM: PRECAUCIÓN]")
    print(f" La estación {col_quime} presenta un porcentaje de vacíos elevado ({pct_nulos:.2f}%).")
print("=" * 75)

# ---------------------------------------------------------
# 4. IMPUTACIÓN MEDIANTE EL MÉTODO DE LA RAZÓN NORMAL (NR)
# ---------------------------------------------------------
print("\nIniciando proceso de imputación de datos diarios...")

# Medias anuales observadas (Nx y Ni) para el factor de escala
medias_anuales = matriz_precip.mean(axis=0)
Nx = medias_anuales[col_quime]
estaciones_vecinas = [c for c in matriz_precip.columns if c != col_quime]

# Crear DataFrame con serie original y serie imputada
resultado_df = pd.DataFrame(index=matriz_precip.index)
resultado_df["P_original"] = matriz_precip[col_quime]
resultado_df["P_completada"] = matriz_precip[col_quime]
resultado_df["Metodo_Flag"] = "Observado"

dias_rellenados = 0
dias_sin_apoyo = 0

for fecha, fila in matriz_precip.iterrows():
    if pd.isna(fila[col_quime]):
        # Buscar estaciones vecinas con datos válidos en la fecha
        vecinas_validas = [est for est in estaciones_vecinas if pd.notna(fila[est]) and medias_anuales[est] > 0]
        
        if len(vecinas_validas) >= 1:
            # Fórmula de la Razón Normal: Px = (1 / m) * sum((Nx / Ni) * Pi)
            terminos = [(Nx / medias_anuales[est]) * fila[est] for est in vecinas_validas]
            px_estimado = np.mean(terminos)
            
            # Limitar a valores físicamente posibles (>= 0)
            px_estimado = max(0.0, round(px_estimado, 2))
            
            resultado_df.loc[fecha, "P_completada"] = px_estimado
            resultado_df.loc[fecha, "Metodo_Flag"] = f"Razón_Normal (m={len(vecinas_validas)})"
            dias_rellenados += 1
        else:
            # Si ninguna vecina tiene dato ese día, asignar 0.0 o bandera para respaldo satelital
            resultado_df.loc[fecha, "P_completada"] = np.nan
            resultado_df.loc[fecha, "Metodo_Flag"] = "Sin_Datos_Regional"
            dias_sin_apoyo += 1

print(f" -> Días imputados mediante Razón Normal : {dias_rellenados}")
if dias_sin_apoyo > 0:
    print(f" -> Días sin estaciones vecinas disponibles: {dias_sin_apoyo} (requieren respaldo satelital)")

# ---------------------------------------------------------
# 5. EXPORTACIÓN DE RESULTADOS
# ---------------------------------------------------------
ruta_salida_xlsx = os.path.join(DIR_TRABAJO, "quime_diario_1993_2002_completado.xlsx")
ruta_salida_csv = os.path.join(DIR_TRABAJO, "quime_diario_1993_2002_completado.csv")

# Formatear salida con columnas explícitas
salida_final = resultado_df.reset_index().rename(columns={"index": "Fecha"})
salida_final["gestion"] = salida_final["Fecha"].dt.year
salida_final["mes"] = salida_final["Fecha"].dt.month
salida_final["dia"] = salida_final["Fecha"].dt.day
salida_final["estacion"] = col_quime

columnas_orden = ["Fecha", "gestion", "mes", "dia", "estacion", "P_original", "P_completada", "Metodo_Flag"]
salida_final = salida_final[columnas_orden]

salida_final.to_excel(ruta_salida_xlsx, index=False)
salida_final.to_csv(ruta_salida_csv, index=False, sep=";")

print("\n" + "=" * 75)
print(f" ARCHIVOS GENERADOS CORRECTAMENTE EN:")
print(f" [Excel] {ruta_salida_xlsx}")
print(f" [CSV]   {ruta_salida_csv}")
print("=" * 75)