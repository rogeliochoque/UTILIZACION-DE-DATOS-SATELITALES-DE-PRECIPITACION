import os
import pandas as pd


def procesar_precipitacion_mswep(
    ruta_excel_entrada: str,
    ruta_carpeta_salida: str,
    id_estacion: int = 1,
    codigo_tarjeta: str = "LEMA",
):
    """Lee la serie diaria corregida de MSWEP, acumula a totales mensuales y

    genera:
    1. Archivo Excel (.xlsx) con columnas: Año, Ene, Feb, Mar, Apr, May, Jun,
    Jul, Aug, Sep, Oct, Nov, Dec.
    2. Archivo de texto con formato estándar LEMA (.LEM) para CHAC.
    """
    # 1. Verificar archivo de entrada y crear carpeta destino
    if not os.path.exists(ruta_excel_entrada):
        raise FileNotFoundError(
            f"No se encontró el archivo de entrada en: {ruta_excel_entrada}"
        )

    os.makedirs(ruta_carpeta_salida, exist_ok=True)

    ruta_excel_salida = os.path.join(
        ruta_carpeta_salida, "precipitacion_mensual_MSWEP_1980_2020.xlsx"
    )
    ruta_lema_salida = os.path.join(
        ruta_carpeta_salida, "MSWEP_1980_2020.LEM"
    )

    print(f"Leyendo archivo Excel de entrada: {ruta_excel_entrada}...")
    df = pd.read_excel(ruta_excel_entrada)
    df.columns = [c.strip() for c in df.columns]

    if "fecha" not in df.columns or "MSWEP_corr" not in df.columns:
        raise ValueError(
            "El archivo Excel debe contener las columnas 'fecha' y 'MSWEP_corr'."
        )

    # 2. Convertir fechas y calcular acumulados mensuales
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["Año"] = df["fecha"].dt.year
    df["Mes"] = df["fecha"].dt.month

    print("Calculando acumulados mensuales...")
    df_mensual = (
        df.groupby(["Año", "Mes"])["MSWEP_corr"].sum().reset_index()
    )

    # Pivotar: Filas = Año, Columnas = Meses (1 al 12)
    tabla_pivot = df_mensual.pivot(
        index="Año", columns="Mes", values="MSWEP_corr"
    ).fillna(0.0)

    # 3. Mapear y renombrar a las columnas requeridas
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

    # Asegurar el orden de columnas solicitado
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
    df_resultado = df_resultado[columnas_orden]

    # Redondear a 1 decimal (consistente con el formato hidrológico)
    df_resultado = df_resultado.round(1)

    # 4. Guardar archivo Excel
    print(f"Guardando archivo Excel en: {ruta_excel_salida}...")
    df_resultado.to_excel(ruta_excel_salida, index=False)

    # 5. Guardar archivo en formato LEMA (.LEM)
    print(f"Generando archivo LEMA en: {ruta_lema_salida}...")
    tarjeta = str(codigo_tarjeta).strip()[:4].ljust(4)
    id_est = str(id_estacion).strip()[:6].rjust(6)

    meses_abreviados = [
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

            suma_anual = 0.0
            for col_mes in meses_abreviados:
                val = fila[col_mes]
                suma_anual += val
                linea += f"{val:6.1f}"

            linea += f"{suma_anual:8.1f}\n"
            f.write(linea)

    print("=" * 65)
    print("PROCESO FINALIZADO CON ÉXITO")
    print(f"1. Archivo Excel generado: {ruta_excel_salida}")
    print(f"2. Archivo LEMA generado : {ruta_lema_salida}")
    print(
        f"Años procesados          : {len(df_resultado)} ({df_resultado['Año'].min()} - {df_resultado['Año'].max()})"
    )
    print("=" * 65)


if __name__ == "__main__":
    RUTA_ENTRADA = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios\datos_satelites_depurados_1980_2020_MSWEP.xlsx"
    RUTA_SALIDA = (
        r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios\CHAC"
    )

    procesar_precipitacion_mswep(
        ruta_excel_entrada=RUTA_ENTRADA,
        ruta_carpeta_salida=RUTA_SALIDA,
        id_estacion=1,
        codigo_tarjeta="LEMA",
    )