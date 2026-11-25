import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

# ==============================================================================
# CONFIGURACIÓN DE RUTAS
# ==============================================================================
DIR_BASE = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo"
DIR_PAREADOS = os.path.join(DIR_BASE, "comparacion_satelites")
DIR_SALIDA = os.path.join(DIR_PAREADOS, "resultados_correccion_MSWEP")
os.makedirs(DIR_SALIDA, exist_ok=True)

RUTA_SAT_CRUDO = os.path.join(DIR_BASE, "datos_de_los_satelites.xlsx")

ESTACIONES = {
    "conchamarca": "pareado_multisat_conchamarca.xlsx",
    "caxata": "pareado_multisat_caxata.xlsx",
    "circuata": "pareado_multisat_circuata.xlsx"
}

CAL_MAESTRO = pd.date_range("1980-01-01", "2020-12-31", freq="D")
PTH_OBS = 0.1

# ==============================================================================
# FUNCIONES DE AJUSTE (RETORNAN ARREGLOS NUMPY LIMPIOS)
# ==============================================================================
def fit_transform_ls(obs_cal, sat_cal, sat_target):
    m_obs = np.nanmean(obs_cal)
    m_sat = np.nanmean(sat_cal)
    factor = 1.0 if (np.isnan(m_sat) or m_sat == 0 or np.isnan(m_obs)) else (m_obs / m_sat)
    res = sat_target * factor
    return np.maximum(np.nan_to_num(res, nan=0.0), 0.0)

def fit_transform_loci(obs_cal, sat_cal, sat_target, pth_obs=PTH_OBS):
    valid = (~np.isnan(obs_cal)) & (~np.isnan(sat_cal))
    o_v, s_v = obs_cal[valid], sat_cal[valid]
    if len(o_v) < 10 or len(s_v) < 10:
        return np.maximum(np.nan_to_num(sat_target, nan=0.0), 0.0)

    prob_dry = np.mean(o_v < pth_obs)
    pth_sat = np.percentile(s_v, prob_dry * 100.0)

    wet_o = o_v[o_v >= pth_obs]
    wet_s = s_v[s_v > pth_sat]
    m_wo = np.mean(wet_o) if len(wet_o) > 0 else 0.0
    m_ws = np.mean(wet_s) if len(wet_s) > 0 else 0.0

    s_factor = (m_wo - pth_obs) / (m_ws - pth_sat) if ((m_ws - pth_sat) > 0 and m_wo > 0) else 1.0

    res = np.zeros_like(sat_target, dtype=float)
    mask_wet = sat_target > pth_sat
    res[mask_wet] = pth_obs + (sat_target[mask_wet] - pth_sat) * s_factor
    return np.maximum(np.nan_to_num(res, nan=0.0), 0.0)

def fit_transform_eqm(obs_cal, sat_cal, sat_target, n_quantiles=1000):
    valid = (~np.isnan(obs_cal)) & (~np.isnan(sat_cal))
    o_v, s_v = obs_cal[valid], sat_cal[valid]
    if len(o_v) < 10 or len(s_v) < 10:
        return np.maximum(np.nan_to_num(sat_target, nan=0.0), 0.0)

    quantiles = np.linspace(0.0, 1.0, n_quantiles)
    q_obs = np.percentile(o_v, quantiles * 100.0)
    q_sat = np.percentile(s_v, quantiles * 100.0)

    q_sat_u, idx_u = np.unique(q_sat, return_index=True)
    q_obs_u = q_obs[idx_u]

    if len(q_sat_u) < 2:
        return np.maximum(np.nan_to_num(sat_target, nan=0.0), 0.0)

    interp_func = interp1d(q_sat_u, q_obs_u, kind='linear', bounds_error=False, fill_value="extrapolate")
    res = interp_func(sat_target)
    return np.maximum(np.nan_to_num(res, nan=0.0), 0.0)

# ==============================================================================
# PROCESAMIENTO
# ==============================================================================
xls_sat = pd.ExcelFile(RUTA_SAT_CRUDO)

for est_name, arch_pareado in ESTACIONES.items():
    print(f"\n=======================================================")
    print(f"Procesando y reparando: {est_name.upper()}")
    print(f"=======================================================")

    # 1. Leer satélite continuo crudo
    hoja_a_leer = 0
    for h in xls_sat.sheet_names:
        if est_name in h.lower():
            hoja_a_leer = h
            break

    df_sat = pd.read_excel(RUTA_SAT_CRUDO, sheet_name=hoja_a_leer)
    df_sat.columns = [str(c).strip() for c in df_sat.columns]

    # Identificar columna fecha y estandarizar a 'fecha'
    col_f_sat = [c for c in df_sat.columns if "fech" in c.lower() or "date" in c.lower()][0]
    df_sat["fecha"] = pd.to_datetime(df_sat[col_f_sat], errors="coerce")
    df_sat = df_sat.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)
    df_sat["MSWEP"] = pd.to_numeric(df_sat["MSWEP"], errors="coerce")

    # Calendario base de 14,976 días continuos
    df_final = pd.DataFrame({"fecha": CAL_MAESTRO})
    df_final = pd.merge(df_final, df_sat[["fecha", "MSWEP"]], on="fecha", how="left")

    # Rellenar cualquier día faltante en el satélite continuo (si lo hubiera)
    if df_final["MSWEP"].isna().sum() > 0:
        df_final["MSWEP"] = df_final["MSWEP"].interpolate(method="linear").bfill().ffill()

    # 2. Leer pares de calibración de tierra
    df_cal = pd.read_excel(os.path.join(DIR_PAREADOS, arch_pareado))
    df_cal.columns = [str(c).strip() for c in df_cal.columns]
    col_fc = [c for c in df_cal.columns if "fech" in c.lower()][0]
    df_cal["fecha"] = pd.to_datetime(df_cal[col_fc], errors="coerce", dayfirst=True)
    df_cal["p_obs"] = pd.to_numeric(df_cal["p_obs"], errors="coerce")
    df_cal["MSWEP"] = pd.to_numeric(df_cal["MSWEP"], errors="coerce")

    # Acoplar p_obs a df_final sobre la clave estándar 'fecha'
    df_final = pd.merge(df_final, df_cal[["fecha", "p_obs"]], on="fecha", how="left")

    df_final["mes"] = df_final["fecha"].dt.month
    df_cal["mes"] = df_cal["fecha"].dt.month

    # Arrays de destino para evitar desalineación de índices
    arr_ls = np.zeros(len(df_final), dtype=float)
    arr_loci = np.zeros(len(df_final), dtype=float)
    arr_eqm = np.zeros(len(df_final), dtype=float)

    # 3. Calibrar por mes y transformar la serie completa de 41 años
    for m in range(1, 13):
        # Muestra de calibración: pares válidos
        mask_c = (df_cal["mes"] == m) & (~df_cal["p_obs"].isna()) & (~df_cal["MSWEP"].isna())
        o_c = df_cal.loc[mask_c, "p_obs"].values
        s_c = df_cal.loc[mask_c, "MSWEP"].values

        # Muestra objetivo continuo: los 41 años completos
        idx_target = np.where(df_final["mes"].values == m)[0]
        s_target = df_final.loc[df_final["mes"] == m, "MSWEP"].values

        if len(o_c) >= 10 and len(s_target) > 0:
            arr_ls[idx_target] = fit_transform_ls(o_c, s_c, s_target)
            arr_loci[idx_target] = fit_transform_loci(o_c, s_c, s_target, PTH_OBS)
            arr_eqm[idx_target] = fit_transform_eqm(o_c, s_c, s_target)
        else:
            arr_ls[idx_target] = s_target
            arr_loci[idx_target] = s_target
            arr_eqm[idx_target] = s_target

    df_final["MSWEP_LS"] = arr_ls
    df_final["MSWEP_LOCI"] = arr_loci
    df_final["MSWEP_EQM"] = arr_eqm

    # 4. Verificación de vacíos
    print(f"Total filas: {len(df_final)}")
    print(f"Días observados en p_obs: {df_final['p_obs'].notna().sum()} (Vacíos: {df_final['p_obs'].isna().sum()})")
    print(f"Vacíos en MSWEP Crudo: {df_final['MSWEP'].isna().sum()}")
    print(f"Vacíos en MSWEP_EQM: {df_final['MSWEP_EQM'].isna().sum()}")

    # 5. Exportar archivo Excel
    cols_salida = ["fecha", "p_obs", "MSWEP", "MSWEP_LS", "MSWEP_LOCI", "MSWEP_EQM"]
    out_path = os.path.join(DIR_SALIDA, f"MSWEP_corregido_{est_name}_14976dias_1980_2020.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_final[cols_salida].to_excel(writer, sheet_name="Serie_Completa_1980_2020", index=False)
    print(f"-> Archivo guardado con éxito: {out_path}")

print("\n¡Proceso finalizado! Las 3 estaciones tienen sus 14,976 días completos sin vacíos en MSWEP_EQM.")