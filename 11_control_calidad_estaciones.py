import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# =============================================================================
# CONFIGURACIÓN GENERAL Y RUTAS
# =============================================================================
BASE_DIR = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo"
ARCHIVOS_ESTACIONES = [
    "dato_diarios_conchamarca.xlsx",
    "dato_diarios_caxata.xlsx",
    "dato_diarios_circuata.xlsx"
]

OUTPUT_DIR = os.path.join(BASE_DIR, "resultados_qc_outliers")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Parámetros de Control de Calidad (QC)
P_MIN_FISICO = 0.0          # mm/día
P_MAX_FISICO = 150.0        # mm/día (umbral físico regional máximo admisible)
IQR_FACTOR = 3.0            # Factor intercuartílico para outliers extremos (Tukey)
UMBRAL_HUMEDO = 0.1         # mm/día para considerar día con precipitación


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas eliminando espacios y tildes."""
    mapeo = {
        'gestión': 'gestion',
        'año': 'gestion',
        'ano': 'gestion',
        'precipitación': 'precipitacion',
        'precipitacion': 'precipitacion',
        'día': 'dia'
    }
    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns=mapeo, inplace=True)
    return df


def cargar_y_estructurar(filepath: str) -> pd.DataFrame:
    """Carga el Excel y genera índice temporal continuo diario."""
    df = pd.read_excel(filepath)
    df = normalizar_columnas(df)

    # Identificar columna de precipitación
    col_p = [c for c in df.columns if 'precip' in c]
    if not col_p:
        raise ValueError(f"No se encontró la columna de precipitación en {filepath}")
    col_p = col_p[0]
    df.rename(columns={col_p: 'p_original'}, inplace=True)

    # Coerción numérica
    df['p_original'] = pd.to_numeric(df['p_original'], errors='coerce')

    # Construir columna de fecha
    df['fecha'] = pd.to_datetime(dict(year=df['gestion'], month=df['mes'], day=df['dia']), errors='coerce')
    df = df.dropna(subset=['fecha']).sort_values('fecha').reset_index(drop=True)

    # Completar serie temporal completa (detectar días faltantes)
    rango_completo = pd.date_range(start=df['fecha'].min(), end=df['fecha'].max(), freq='D')
    nombre_est = df['estacion'].iloc[0] if 'estacion' in df.columns else os.path.basename(filepath)
    
    df = df.set_index('fecha').reindex(rango_completo)
    df.index.name = 'fecha'
    df['estacion'] = df['estacion'].bfill().ffill()
    df['gestion'] = df.index.year
    df['mes'] = df.index.month
    df['dia'] = df.index.day

    return df.reset_index()


def detectar_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica filtros de calidad físicos y estadísticos condicionales al ciclo mensual.
    """
    df['qc_flag'] = 'VALIDO'
    df['p_filtrada'] = df['p_original']

    # 1. Filtro físico: valores negativos
    mask_neg = df['p_original'] < P_MIN_FISICO
    df.loc[mask_neg, 'qc_flag'] = 'ERROR_NEGATIVO'

    # 2. Filtro físico: límite regional superior
    mask_max = df['p_original'] > P_MAX_FISICO
    df.loc[mask_max, 'qc_flag'] = 'OUTLIER_FISICO_MAX'

    # 3. Filtro estadístico por mes (solo sobre días húmedos)
    df['umbral_iqr_mes'] = np.nan
    for m in range(1, 13):
        idx_mes = (df['mes'] == m) & (df['p_original'] >= UMBRAL_HUMEDO) & (df['p_original'] <= P_MAX_FISICO)
        datos_humedos = df.loc[idx_mes, 'p_original']

        if len(datos_humedos) >= 20:
            q25 = datos_humedos.quantile(0.25)
            q75 = datos_humedos.quantile(0.75)
            iqr = q75 - q25
            corte_sup = q75 + (IQR_FACTOR * iqr)
            df.loc[df['mes'] == m, 'umbral_iqr_mes'] = corte_sup

            # Marcar sospechosos que superen el corte IQR
            mask_iqr = (df['mes'] == m) & (df['p_original'] > corte_sup) & (df['qc_flag'] == 'VALIDO')
            df.loc[mask_iqr, 'qc_flag'] = 'OUTLIER_IQR'

    # Los detectados como outliers o errores se asignan a NaN en la serie limpia
    df.loc[df['qc_flag'] != 'VALIDO', 'p_filtrada'] = np.nan
    return df


def graficar_control_calidad(df: pd.DataFrame, nombre_est: str):
    """Genera panel diagnóstico de control de calidad."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=False)
    plt.subplots_adjust(hspace=0.35)

    # Panel 1: Serie Temporal Completa y Outliers
    ax1 = axes[0]
    ax1.plot(df['fecha'], df['p_original'], color='royalblue', lw=0.7, alpha=0.7, label='P Observada')
    
    anomalos = df[df['qc_flag'] != 'VALIDO']
    if not anomalos.empty:
        colores = {'ERROR_NEGATIVO': 'black', 'OUTLIER_FISICO_MAX': 'red', 'OUTLIER_IQR': 'orange'}
        for motivo, sub in anomalos.groupby('qc_flag'):
            ax1.scatter(sub['fecha'], sub['p_original'], color=colores.get(motivo, 'magenta'), 
                        s=35, zorder=5, label=f'Detectado: {motivo} (n={len(sub)})')

    ax1.axhline(P_MAX_FISICO, color='crimson', linestyle='--', lw=1.2, label=f'Límite Físico ({P_MAX_FISICO} mm)')
    ax1.set_title(f"Control de Calidad y Outliers - Estación: {nombre_est.upper()}", fontsize=13, fontweight='bold')
    ax1.set_ylabel("P diaria [mm]")
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', framealpha=0.9)

    # Panel 2: Distribución mensual (Boxplot) de días húmedos
    ax2 = axes[1]
    df_humedo = df[df['p_original'] >= UMBRAL_HUMEDO].copy()
    sns.boxplot(x='mes', y='p_original', data=df_humedo, ax=ax2, color='lightblue', showfliers=True)
    ax2.set_title("Variabilidad Mensual de Días Húmedos (P >= 0.1 mm) y Dispersión de Extremos", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Mes")
    ax2.set_ylabel("P diaria [mm]")
    ax2.grid(True, linestyle=':', alpha=0.5)

    # Panel 3: Comparación Serie Original vs Serie Depurada (Acumulado Anual)
    ax3 = axes[2]
    anual_orig = df.set_index('fecha')['p_original'].resample('YE').sum(min_count=300)
    anual_filt = df.set_index('fecha')['p_filtrada'].resample('YE').sum(min_count=300)

    ax3.plot(anual_orig.index.year, anual_orig, color='gray', linestyle='--', marker='o', label='Anual Original')
    ax3.plot(anual_filt.index.year, anual_filt, color='forestgreen', marker='s', label='Anual QC Depurada')
    ax3.set_title("Impacto del Filtrado en el Acumulado Anual", fontsize=11, fontweight='bold')
    ax3.set_ylabel("P Anual [mm]")
    ax3.set_xlabel("Año")
    ax3.grid(True, linestyle=':', alpha=0.6)
    ax3.legend(loc='upper right')

    out_png = os.path.join(OUTPUT_DIR, f"qc_outliers_{nombre_est}.png")
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   [+] Gráfico guardado: {out_png}")


# =============================================================================
# EJECUCIÓN PRINCIPAL
# =============================================================================
def main():
    print("=" * 80)
    print("INICIANDO CONTROL DE CALIDAD Y FILTRADO DE OUTLIERS (FASE 1)")
    print("=" * 80)

    resumen_global = []

    for archivo in ARCHIVOS_ESTACIONES:
        ruta_completa = os.path.join(BASE_DIR, archivo)
        if not os.path.exists(ruta_completa):
            print(f"\n[!] Advertencia: Archivo no encontrado -> {ruta_completa}")
            continue

        print(f"\n Procesando: {archivo} ...")
        df = cargar_y_estructurar(ruta_completa)
        nombre_estacion = str(df['estacion'].dropna().iloc[0]).strip()

        df_qc = detectar_outliers(df)

        # Estadísticas del QC
        total_dias = len(df_qc)
        dias_nan_original = df_qc['p_original'].isna().sum()
        dias_negativos = (df_qc['qc_flag'] == 'ERROR_NEGATIVO').sum()
        outliers_fisicos = (df_qc['qc_flag'] == 'OUTLIER_FISICO_MAX').sum()
        outliers_iqr = (df_qc['qc_flag'] == 'OUTLIER_IQR').sum()
        dias_humedos = (df_qc['p_original'] >= UMBRAL_HUMEDO).sum()
        max_registrado = df_qc['p_original'].max()

        resumen_global.append({
            'Estación': nombre_estacion,
            'Inicio': df_qc['fecha'].min().strftime('%Y-%m-%d'),
            'Fin': df_qc['fecha'].max().strftime('%Y-%m-%d'),
            'Total Días': total_dias,
            'Faltantes (NoData)': dias_nan_original,
            'P_max Registrada (mm)': max_registrado,
            'Negativos': dias_negativos,
            'P > P_max': outliers_fisicos,
            'Outliers IQR': outliers_iqr,
            'Días Húmedos': dias_humedos
        })

        # Mostrar tabla de outliers identificados en terminal
        outliers_detectados = df_qc[df_qc['qc_flag'] != 'VALIDO'][['fecha', 'gestion', 'mes', 'dia', 'p_original', 'qc_flag']]
        if not outliers_detectados.empty:
            print(f"\n--- Outliers y errores detectados en {nombre_estacion} (Total: {len(outliers_detectados)}) ---")
            print(outliers_detectados.head(15).to_string(index=False))
            if len(outliers_detectados) > 15:
                print(f"... y {len(outliers_detectados) - 15} registros adicionales.")
        else:
            print(f" No se encontraron outliers físicos ni estadísticos en {nombre_estacion}.")

        # Guardar archivo Excel limpio con flags
        ruta_salida_excel = os.path.join(OUTPUT_DIR, f"qc_limpio_{archivo}")
        df_qc.to_excel(ruta_salida_excel, index=False)
        print(f"   [+] Archivo depurado guardado: {ruta_salida_excel}")

        # Generar gráfico diagnóstico
        graficar_control_calidad(df_qc, nombre_estacion)

    # Imprimir cuadro resumen comparativo en terminal
    if resumen_global:
        df_resumen = pd.DataFrame(resumen_global)
        print("\n" + "=" * 80)
        print("RESUMEN GENERAL DEL CONTROL DE CALIDAD")
        print("=" * 80)
        print(df_resumen.to_string(index=False))
        print("=" * 80)


if __name__ == "__main__":
    main()