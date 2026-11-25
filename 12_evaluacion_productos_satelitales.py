import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# =============================================================================
# CONFIGURACIÓN Y RUTAS
# =============================================================================
BASE_DIR = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo"
DIR_QC = os.path.join(BASE_DIR, "resultados_qc_outliers")
ARCHIVO_SATELITES = os.path.join(BASE_DIR, "datos_de_los_satelites.xlsx")

ESTACIONES_QC = {
    "Caxata": os.path.join(DIR_QC, "qc_limpio_dato_diarios_caxata.xlsx"),
    "Circuata": os.path.join(DIR_QC, "qc_limpio_dato_diarios_circuata.xlsx"),
    "Conchamarca": os.path.join(DIR_QC, "qc_limpio_dato_diarios_conchamarca.xlsx")
}

DIR_SALIDA = os.path.join(BASE_DIR, "comparacion_satelites")
os.makedirs(DIR_SALIDA, exist_ok=True)

PRODUCTOS_SAT = ['CHIRPS', 'ERA5', 'MSWEP']
UMBRAL_HUMEDO = 0.1  # mm/día


# =============================================================================
# FUNCIONES DE EVALUACIÓN CONTINUA Y CATEGÓRICA
# =============================================================================
def calcular_metricas_completas(obs: np.ndarray, sim: np.ndarray, umbral: float = 0.1):
    """Calcula métricas continuas y de contingencia (detección)."""
    mask = ~np.isnan(obs) & ~np.isnan(sim)
    o = obs[mask]
    s = sim[mask]

    if len(o) < 30:
        return {}

    n = len(o)
    r, _ = stats.pearsonr(o, s)
    rmse = np.sqrt(np.mean((s - o) ** 2))
    mae = np.mean(np.abs(s - o))
    
    suma_obs = np.sum(o)
    pbias = 100.0 * np.sum(s - o) / suma_obs if suma_obs != 0 else np.nan
    
    # KGE (Kling-Gupta Efficiency 2009)
    std_o = np.std(o)
    std_s = np.std(s)
    mean_o = np.mean(o)
    mean_s = np.mean(s)
    alpha = std_s / std_o if std_o != 0 else np.nan
    beta = mean_s / mean_o if mean_o != 0 else np.nan
    kge = 1.0 - np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2)

    # Contingencia categórica para detección de lluvia
    # H: Hits, F: False Alarms, M: Misses, C: Correct Negatives
    o_rain = o >= umbral
    s_rain = s >= umbral

    hits = np.sum(o_rain & s_rain)
    false_alarms = np.sum(~o_rain & s_rain)
    misses = np.sum(o_rain & ~s_rain)

    pod = hits / (hits + misses) if (hits + misses) > 0 else np.nan
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else np.nan
    csi = hits / (hits + misses + false_alarms) if (hits + misses + false_alarms) > 0 else np.nan

    frec_obs = np.mean(o_rain) * 100.0
    frec_sat = np.mean(s_rain) * 100.0

    return {
        "N_pares": n,
        "r_Pearson": r,
        "RMSE_mm": rmse,
        "MAE_mm": mae,
        "PBIAS_%": pbias,
        "KGE": kge,
        "POD": pod,
        "FAR": far,
        "CSI": csi,
        "Frec_Obs_%": frec_obs,
        "Frec_Sat_%": frec_sat
    }


def graficar_comparativo_estacion(df_pareado: pd.DataFrame, nombre_est: str):
    """Genera panel visual: dispersión y ciclo anual comparativo."""
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    plt.subplots_adjust(wspace=0.25)

    df_pareado['mes'] = df_pareado['fecha'].dt.month

    # 1. Ciclo anual medio mensual
    cols_prom = ['p_obs'] + [f"{p}_drizzle" for p in PRODUCTOS_SAT if f"{p}_drizzle" in df_pareado.columns]
    ciclo = df_pareado.groupby('mes')[cols_prom].mean()

    ax1 = axes[0]
    ax1.plot(ciclo.index, ciclo['p_obs'], marker='o', lw=2.5, color='black', label='Observado')
    
    colores = {'CHIRPS': 'firebrick', 'ERA5': 'darkorange', 'MSWEP': 'royalblue'}
    estilos = {'CHIRPS': '--', 'ERA5': '-.', 'MSWEP': '-'}
    
    for prod in PRODUCTOS_SAT:
        col_prod = f"{prod}_drizzle"
        if col_prod in ciclo.columns:
            ax1.plot(ciclo.index, ciclo[col_prod], marker='s', lw=1.8, 
                     color=colores.get(prod, 'gray'), linestyle=estilos.get(prod, '-'),
                     label=prod)

    ax1.set_title(f"Ciclo Anual Promedio Diario - Estación {nombre_est}", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Mes")
    ax1.set_ylabel("Precipitación Promedio [mm/día]")
    ax1.set_xticks(range(1, 13))
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper left')

    # 2. Diagrama de caja (Boxplot) de los valores diarios en días húmedos
    ax2 = axes[1]
    datos_box = []
    
    # Agregar observado
    sub_obs = df_pareado[df_pareado['p_obs'] >= UMBRAL_HUMEDO]['p_obs']
    for v in sub_obs:
        datos_box.append({'Fuente': 'Observado', 'Precipitacion': v})
        
    for prod in PRODUCTOS_SAT:
        col_p = f"{prod}_drizzle"
        if col_p in df_pareado.columns:
            sub_sat = df_pareado[df_pareado[col_p] >= UMBRAL_HUMEDO][col_p]
            for v in sub_sat:
                datos_box.append({'Fuente': prod, 'Precipitacion': v})

    df_box = pd.DataFrame(datos_box)
    sns.boxplot(x='Fuente', y='Precipitacion', data=df_box, ax=ax2, palette=['gray', 'firebrick', 'darkorange', 'royalblue'], showfliers=False)
    ax2.set_title(f"Distribución de Días Húmedos (P >= 0.1 mm) - {nombre_est}", fontsize=12, fontweight='bold')
    ax2.set_ylabel("P diaria [mm] (sin atípicos para visualización)")
    ax2.grid(True, linestyle=':', alpha=0.5)

    ruta_png = os.path.join(DIR_SALIDA, f"comparativa_{nombre_est.lower()}.png")
    plt.savefig(ruta_png, dpi=300, bbox_inches='tight')
    plt.close()


# =============================================================================
# FLUJO PRINCIPAL
# =============================================================================
def main():
    print("=" * 105)
    print("FASE DE SELECCIÓN: COMPARACIÓN MULTIPRODUCTO (CHIRPS vs ERA5 vs MSWEP)")
    print("=" * 105)

    if not os.path.exists(ARCHIVO_SATELITES):
        raise FileNotFoundError(f"No existe: {ARCHIVO_SATELITES}")

    # Cargar satélites
    df_sat = pd.read_excel(ARCHIVO_SATELITES)
    df_sat.columns = df_sat.columns.str.strip()
    df_sat.rename(columns={'fecha': 'fecha'}, inplace=True)
    df_sat['fecha'] = pd.to_datetime(df_sat['fecha'], errors='coerce')
    df_sat = df_sat.dropna(subset=['fecha']).sort_values('fecha').reset_index(drop=True)

    # Coerción numérica y truncamiento de llovizna preliminar
    for prod in PRODUCTOS_SAT:
        if prod in df_sat.columns:
            df_sat[prod] = pd.to_numeric(df_sat[prod], errors='coerce')
            df_sat[f"{prod}_drizzle"] = df_sat[prod].apply(
                lambda x: 0.0 if (x < UMBRAL_HUMEDO and not np.isnan(x)) else x
            )

    resultados_globales = []

    for nombre_est, ruta_qc in ESTACIONES_QC.items():
        if not os.path.exists(ruta_qc):
            continue

        print(f"\n Procesando cruce y evaluación para: {nombre_est} ...")
        df_qc = pd.read_excel(ruta_qc)
        df_qc.columns = df_qc.columns.str.strip().str.lower()
        df_qc['fecha'] = pd.to_datetime(df_qc['fecha'], errors='coerce')
        df_qc = df_qc.dropna(subset=['fecha']).sort_values('fecha').reset_index(drop=True)

        col_p = 'p_filtrada' if 'p_filtrada' in df_qc.columns else 'p_original'
        df_qc_sub = df_qc[['fecha', col_p]].rename(columns={col_p: 'p_obs'})

        # Merge con los satélites
        df_pareado = pd.merge(df_qc_sub, df_sat, on='fecha', how='inner')
        df_pareado = df_pareado.dropna(subset=['p_obs']).copy()

        # Guardar archivo pareado multiproducto
        ruta_csv = os.path.join(DIR_SALIDA, f"pareado_multisat_{nombre_est.lower()}.csv")
        df_pareado.to_csv(ruta_csv, index=False)

        # Evaluar cada producto frente al observado
        for prod in PRODUCTOS_SAT:
            col_eval = f"{prod}_drizzle"
            if col_eval not in df_pareado.columns:
                continue

            # Máscara concurrente para días con datos válidos en ambos
            sub_eval = df_pareado.dropna(subset=['p_obs', col_eval])
            
            m = calcular_metricas_completas(sub_eval['p_obs'].values, sub_eval[col_eval].values, UMBRAL_HUMEDO)
            if m:
                m['Estación'] = nombre_est
                m['Producto'] = prod
                m['Inicio'] = sub_eval['fecha'].min().strftime('%Y-%m-%d')
                m['Fin'] = sub_eval['fecha'].max().strftime('%Y-%m-%d')
                resultados_globales.append(m)

        graficar_comparativo_estacion(df_pareado, nombre_est)

    # Imprimir tabla comparativa consolidada
    if resultados_globales:
        df_res = pd.DataFrame(resultados_globales)
        cols_orden = [
            'Estación', 'Producto', 'N_pares', 'r_Pearson', 'RMSE_mm', 
            'PBIAS_%', 'KGE', 'POD', 'FAR', 'CSI', 'Frec_Obs_%', 'Frec_Sat_%'
        ]
        df_res = df_res[cols_orden]

        print("\n" + "=" * 115)
        print("RESUMEN COMPARATIVO MULTIPRODUCTO SATELITAL (CRUPO CON TRUNCAMIENTO P >= 0.1 mm)")
        print("=" * 115)
        print(df_res.round(3).to_string(index=False))
        print("=" * 115)

        # Exportar a Excel la tabla comparativa para tesis
        ruta_resumen = os.path.join(DIR_SALIDA, "tabla_comparativa_satelites.xlsx")
        df_res.round(4).to_excel(ruta_resumen, index=False)
        print(f"\n[+] Tabla comparativa exportada a: {ruta_resumen}")


if __name__ == "__main__":
    main()