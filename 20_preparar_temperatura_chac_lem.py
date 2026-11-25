import glob
import os
import pandas as pd


def buscar_archivo_temperatura(directorio: str) -> str:
    """Busca automáticamente el archivo de temperatura en el directorio."""
    # Buscar patrones comunes
    patrones = [
        "temperatura_era5land_diaria_filtrada_corregida.xlsx",
        "temperatura_era5land_diaria_filtrada_corregida.xls",
        "temperatura_era5land_diaria_filtrada_corregida.csv",
        "*temperatura*era5land*.xlsx",
        "*temperatura*era5land*.xls",
        "*temperatura*era5land*.csv",
    ]

    for patron in patrones:
        coincidencias = glob.glob(os.path.join(directorio, patron))
        if coincidencias:
            return coincidencias[0]

    # Si no lo encuentra, mostrar qué archivos sí existen en la carpeta
    archivos_existentes = (
        os.listdir(directorio) if os.path.exists(directorio) else []
    )
    msg = (
        f"No se encontró el archivo de temperatura en:\n  {directorio}\n\n"
        f"Archivos encontrados en esa carpeta:\n"
    )
    for a in archivos_existentes:
        msg += f"  - {a}\n"
    raise FileNotFoundError(msg)


def procesar_temperatura_chac(
    ruta_carpeta_datos: str,
    ruta_carpeta_salida: str,
    id_estacion: int = 1,
    codigo_tarjeta: str = "TEMP",
):
    # 1. Localizar archivo automáticamente
    ruta_excel_entrada = buscar_archivo_temperatura(ruta_carpeta_datos)
    print(f"Archivo localizado con éxito: {ruta_excel_entrada}")

    os.makedirs(ruta_carpeta_salida, exist_ok=True)

    ruta_excel_salida = os.path.join(
        ruta_carpeta_salida, "temperatura_mensual_ERA5Land_1980_2020.xlsx"
    )
    ruta_lema_salida = os.path.join(
        ruta_carpeta_salida, "TEMPERATURA_1980_2020.LEM"
    )

    # 2. Cargar datos según el formato
    extension = os.path.splitext(ruta_excel_entrada)[1].lower()
    if extension == ".csv":
        df = pd.read_csv(ruta_excel_entrada)
    elif extension == ".xls":
        try:
            df = pd.read_excel(ruta_excel_entrada, engine="xlrd")
        except Exception:
            df = pd.read_excel(ruta_excel_entrada)
    else:  # .xlsx u otros
        df = pd.read_excel(ruta_excel_entrada)

    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # 3. Identificar columna de temperatura media
    col_temp = None
    for candidata in [
        "Tmean_corr",
        "Tmean_co",
        "Tmean_clean",
        "Tmean_raw",
        "Tmean",
    ]:
        if candidata in df.columns:
            col_temp = candidata
            break

    if col_temp is None:
        raise KeyError(
            f"No se encontró columna de temperatura media. Columnas: {list(df.columns)}"
        )

    print(f"-> Usando variable: '{col_temp}'")

    # 4. Asegurar campos Año y Mes
    if "Año" not in df.columns or "Mes" not in df.columns:
        col_fecha = [
            c for c in df.columns if c.lower() in ["fecha", "date", "datetime"]
        ][0]
        df["Fecha"] = pd.to_datetime(df[col_fecha])
        df["Año"] = df["Fecha"].dt.year
        df["Mes"] = df["Fecha"].dt.month

    df["Año"] = df["Año"].astype(int)
    df["Mes"] = df["Mes"].astype(int)
    df[col_temp] = pd.to_numeric(df[col_temp], errors="coerce")

    # 5. Promedio mensual
    print("Calculando promedios mensuales...")
    df_mensual = df.groupby(["Año", "Mes"])[col_temp].mean().reset_index()
    tabla_pivot = df_mensual.pivot(
        index="Año", columns="Mes", values=col_temp
    )

    nombres_meses = {
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    df_resultado = tabla_pivot.rename(columns=nombres_meses).reset_index()

    columnas_orden = [
        "Año",
        "Ene",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    df_resultado = df_resultado[columnas_orden].round(1)

    # 6. Exportar Excel
    print(f"Guardando Excel en: {ruta_excel_salida}...")
    df_resultado.to_excel(ruta_excel_salida, index=False)

    # 7. Exportar LEMA (.LEM)
    print(f"Generando archivo LEMA en: {ruta_lema_salida}...")
    tarjeta = str(codigo_tarjeta).strip()[:4].ljust(4)
    id_est = str(id_estacion).strip()[:6].rjust(6)
    meses_cols = [
        "Ene",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    with open(ruta_lema_salida, "w", encoding="ascii") as f:
        for _, fila in df_resultado.iterrows():
            anio_val = int(fila["Año"])
            linea = f"{tarjeta}{id_est}{anio_val:4d}"

            valores_mes = []
            for col_m in meses_cols:
                v = fila[col_m]
                valores_mes.append(v)
                linea += f"{v:6.1f}"

            promedio_anual = sum(valores_mes) / len(valores_mes)
            linea += f"{promedio_anual:8.1f}\n"
            f.write(linea)

    print("=" * 65)
    print("PROCESO COMPLETADO EXITOSAMENTE")
    print(f"1. Excel generado : {ruta_excel_salida}")
    print(f"2. Archivo LEMA   : {ruta_lema_salida}")
    print(
        f"Años procesados   : {len(df_resultado)} ({df_resultado['Año'].min()} - {df_resultado['Año'].max()})"
    )
    print("=" * 65)


if __name__ == "__main__":
    # Carpeta donde se encuentran los archivos de datos
    CARPETA_DATOS = (
        r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios"
    )
    CARPETA_SALIDA = (
        r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios\CHAC"
    )

    procesar_temperatura_chac(
        ruta_carpeta_datos=CARPETA_DATOS,
        ruta_carpeta_salida=CARPETA_SALIDA,
        id_estacion=1,
        codigo_tarjeta="TEMP",
    )