import os
from pathlib import Path
import warnings
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ==============================================================================
# 1. RUTAS Y CONFIGURACIÓN GENERAL
# ==============================================================================
DIR_BASE = Path(r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\correccion_sesgo")
FILE_CORR = DIR_BASE / "series_satelitales_corregidas_1980_2020.xlsx"

ESTACIONES_ANCLA = [
    "dato_diarios_conchamarca.xlsx",
    "dato_diarios_caxata.xlsx",
    "dato_diarios_circuata.xlsx",
]

CAL_INICIO, CAL_FIN = "2000-01-01", "2020-12-31"
INDEX_CAL = pd.date_range(start=CAL_INICIO, end=CAL_FIN, freq="D")
UMBRAL_LLUVIA = 0.1  # mm/día

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "figure.autolayout": False,
    "grid.alpha": 0.3,
})


# ==============================================================================
# 2. FUNCIONES ESTADÍSTICAS: FASE A (CONSISTENCIA HISTÓRICA)
# ==============================================================================
def prueba_rachas(serie: pd.Series):
    """Prueba de Wald-Wolfowitz (Runs Test) respecto a la mediana."""
    s = serie.dropna().values
    mediana = np.median(s)
    signos = np.where(s >= mediana, 1, -1)
    signos = signos[signos != 0]

    n1 = np.sum(signos == 1)
    n2 = np.sum(signos == -1)
    cambios = np.where(signos[:-1] != signos[1:])[0]
    R = len(cambios) + 1

    mu_R = ((2 * n1 * n2) / (n1 + n2)) + 1
    var_R = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / (
        ((n1 + n2) ** 2) * (n1 + n2 - 1)
    )

    if var_R <= 0:
        return np.nan, np.nan, "Indeterminado"

    Z = (R - mu_R) / np.sqrt(var_R)
    p_val = 2 * (1 - stats.norm.cdf(abs(Z)))
    conclusion = "Aleatorio" if p_val >= 0.05 else "No aleatorio"
    return Z, p_val, conclusion


def mann_kendall(serie: pd.Series):
    """Test de tendencia monótona de Mann-Kendall."""
    x = serie.dropna().values
    n = len(x)
    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1 :] - x[k]))

    _, count = np.unique(x, return_counts=True)
    var_s = (
        n * (n - 1) * (2 * n + 5)
        - np.sum(count * (count - 1) * (2 * count + 5))
    ) / 18

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p_val = 2 * (1 - stats.norm.cdf(abs(z)))
    tendencia = (
        "Significativa" if p_val < 0.05 else "Sin tendencia significativa"
    )
    return z, p_val, tendencia


def pettitt_test(serie: pd.Series):
    """Test no paramétrico de Pettitt para detección de puntos de quiebre."""
    x = serie.dropna().values
    n = len(x)
    r = stats.rankdata(x)
    y = 2 * np.cumsum(r) - np.arange(1, n + 1) * (n + 1)
    k_tau = np.max(np.abs(y))
    tau = np.where(np.abs(y) == k_tau)[0][0]
    p_val = 2 * np.exp((-6 * (k_tau**2)) / (n**3 + n**2))
    p_val = min(p_val, 1.0)
    
    # Obtener el año según el índice sea entero o DatetimeIndex
    if hasattr(serie.dropna().index[tau], "year"):
        año_quiebre = serie.dropna().index[tau].year
    else:
        año_quiebre = serie.dropna().index[tau]
        
    homogeneo = "Homogénea" if p_val >= 0.05 else f"Quiebre en {año_quiebre}"
    return año_quiebre, k_tau, p_val, homogeneo


# ==============================================================================
# 3. FUNCIONES DE EVALUACIÓN: FASE B (BONDAD DE AJUSTE Y DETECCIÓN)
# ==============================================================================
def calcular_metricas_desempeño(
    obs: pd.Series, sim: pd.Series, umbral: float = 0.1
):
    """Calcula indicadores cuantitativos de error, sincronía y detección binaria."""
    df_par = pd.DataFrame({"obs": obs, "sim": sim}).dropna()
    o = df_par["obs"].values
    s = df_par["sim"].values

    if len(o) == 0:
        return {}

    # 1. Métricas Cuantitativas
    bias = np.mean(s - o)
    sum_o = np.sum(o)
    pbias = ((np.sum(s - o)) / sum_o) * 100 if sum_o != 0 else np.nan
    rmse = np.sqrt(np.mean((s - o) ** 2))
    mae = np.mean(np.abs(s - o))

    # 2. Correlación y Varianza
    if np.std(s) > 0 and np.std(o) > 0:
        r_pearson, _ = stats.pearsonr(o, s)
        r2 = r_pearson**2
    else:
        r_pearson, r2 = np.nan, np.nan

    # 3. Contingencia y Detección Binaria
    hits = np.sum((o >= umbral) & (s >= umbral))
    false_alarms = np.sum((o < umbral) & (s >= umbral))
    misses = np.sum((o >= umbral) & (s < umbral))

    pod = hits / (hits + misses) if (hits + misses) > 0 else np.nan
    far = (
        false_alarms / (hits + false_alarms)
        if (hits + false_alarms) > 0
        else np.nan
    )
    csi = (
        hits / (hits + misses + false_alarms)
        if (hits + misses + false_alarms) > 0
        else np.nan
    )

    return {
        "BIAS (mm/d)": bias,
        "PBIAS (%)": pbias,
        "RMSE (mm/d)": rmse,
        "MAE (mm/d)": mae,
        "Pearson (r)": r_pearson,
        "R2": r2,
        "POD": pod,
        "FAR": far,
        "CSI": csi,
    }


def cargar_patron_ancla(
    directorio: Path, archivos: list, index_cal: pd.DatetimeIndex
) -> pd.Series:
    series_est = {}
    for archivo in archivos:
        p = directorio / archivo
        if not p.exists():
            continue
        df = pd.read_excel(p)
        fechas = pd.to_datetime(
            dict(year=df["gestion"], month=df["mes"], day=df["dia"]),
            errors="coerce",
        )
        nombre = str(df["estacion"].dropna().iloc[0]).strip()
        s = pd.Series(df["Precipitación"].values, index=fechas, name=nombre)
        s = s[~s.index.duplicated(keep="first")]
        series_est[nombre] = s.reindex(index_cal)
    return pd.DataFrame(series_est).mean(axis=1, skipna=True)


# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
def main():
    print("=" * 80)
    print(" PROGRAMA DE EVALUACIÓN ESTADÍSTICA: PREVIO Y POSTERIOR AL SESGO")
    print("=" * 80)

    if not FILE_CORR.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {FILE_CORR}")

    df_todo = pd.read_excel(FILE_CORR, sheet_name="Precipitacion_Diaria")
    df_todo["fecha"] = pd.to_datetime(df_todo.iloc[:, 0])
    df_todo = df_todo.set_index("fecha").sort_index()

    obs_cal = cargar_patron_ancla(DIR_BASE, ESTACIONES_ANCLA, INDEX_CAL)

    # --------------------------------------------------------------------------
    # FASE A: CONSISTENCIA HISTÓRICA MULTIDECADAL (1980 - 2020)
    # --------------------------------------------------------------------------
    print("\n>>> FASE A: Evaluación de Consistencia Histórica Anual (1980-2020)")
    resultados_fase_a = []
    sat_list = ["CHIRPS", "ERA5", "MSWEP"]

    for sat in sat_list:
        col = f"{sat}_RAW"
        if col not in df_todo.columns:
            continue
        
        # Agrupación por año robusta ante cualquier versión de Pandas
        serie_anual = df_todo[col].groupby(df_todo.index.year).sum()

        z_r, p_r, conc_r = prueba_rachas(serie_anual)
        z_mk, p_mk, conc_mk = mann_kendall(serie_anual)
        yr_p, k_p, p_pet, conc_pet = pettitt_test(serie_anual)

        resultados_fase_a.append({
            "Producto": sat,
            "Z_Rachas": round(z_r, 3),
            "p_Rachas": round(p_r, 4),
            "Aleatoriedad": conc_r,
            "Z_MK": round(z_mk, 3),
            "p_MK": round(p_mk, 4),
            "Tendencia": conc_mk,
            "Año_Quiebre": yr_p,
            "p_Pettitt": round(p_pet, 4),
            "Homogeneidad": conc_pet,
        })

    df_a = pd.DataFrame(resultados_fase_a)
    print(df_a.to_string(index=False))
    df_a.to_csv(DIR_BASE / "resumen_consistencia_historica_1980_2020.csv", index=False)

    # --------------------------------------------------------------------------
    # FASE B: COMPARATIVO PREVIO VS POSTERIOR AL SESGO (2000 - 2020)
    # --------------------------------------------------------------------------
    print("\n>>> FASE B: Evaluación Previo vs Posterior a Corrección (2000-2020)")
    metodos = ["RAW", "LS", "LOCI", "EQM"]
    resultados_fase_b = []

    for sat in sat_list:
        for met in metodos:
            col = f"{sat}_{met}"
            if col not in df_todo.columns:
                continue

            sim_cal = df_todo.loc[INDEX_CAL, col]
            m = calcular_metricas_desempeño(obs_cal, sim_cal, umbral=UMBRAL_LLUVIA)
            m["Producto"] = sat
            m["Método"] = met
            resultados_fase_b.append(m)

    cols_orden = [
        "Producto",
        "Método",
        "PBIAS (%)",
        "RMSE (mm/d)",
        "MAE (mm/d)",
        "Pearson (r)",
        "R2",
        "POD",
        "FAR",
        "CSI",
    ]
    df_b = pd.DataFrame(resultados_fase_b)[cols_orden]
    df_b = df_b.round(3)
    print(df_b.to_string(index=False))
    df_b.to_csv(DIR_BASE / "resumen_metricas_calibracion_2000_2020.csv", index=False)

    # --------------------------------------------------------------------------
    # FASE C: GENERACIÓN DE GRÁFICOS
    # --------------------------------------------------------------------------
    print("\nGenerando figuras diagnósticas de alta resolución...")

    # Gráfico 1: Barras de PBIAS y RMSE comparativo
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    colores = ["#9e9e9e", "#42a5f5", "#66bb6a", "#ab47bc"]

    pivot_pbias = df_b.pivot(index="Producto", columns="Método", values="PBIAS (%)")[metodos]
    pivot_pbias.plot(kind="bar", ax=axes[0], color=colores, width=0.8, edgecolor="black", linewidth=0.5)
    axes[0].axhline(0, color="black", linestyle="--", linewidth=0.8)
    axes[0].set_title("(a) Sesgo Porcentual Relativo (PBIAS)", fontweight="bold", pad=10)
    axes[0].set_ylabel("PBIAS (%)")
    axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=0)
    axes[0].grid(True, axis="y", linestyle="--")
    axes[0].legend(title="Método", frameon=True)

    pivot_rmse = df_b.pivot(index="Producto", columns="Método", values="RMSE (mm/d)")[metodos]
    pivot_rmse.plot(kind="bar", ax=axes[1], color=colores, width=0.8, edgecolor="black", linewidth=0.5)
    axes[1].set_title("(b) Raíz del Error Cuadrático Medio (RMSE)", fontweight="bold", pad=10)
    axes[1].set_ylabel("RMSE (mm/día)")
    axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=0)
    axes[1].grid(True, axis="y", linestyle="--")
    axes[1].legend(title="Método", frameon=True)

    plt.tight_layout()
    salida_fig1 = DIR_BASE / "evaluacion_metricas_error.png"
    plt.savefig(salida_fig1, dpi=300)
    plt.show()

    # Gráfico 2: Diagrama de Dispersión de Detección Categórica (POD vs FAR)
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=300)
    markers = {"RAW": "o", "LS": "s", "LOCI": "^", "EQM": "D"}
    colores_sat = {"CHIRPS": "#2e7d32", "ERA5": "#e65100", "MSWEP": "#0d47a1"}

    for _, row in df_b.iterrows():
        sat = row["Producto"]
        met = row["Método"]
        ax.scatter(
            row["FAR"],
            row["POD"],
            label=f"{sat}_{met}",
            color=colores_sat[sat],
            marker=markers[met],
            s=85,
            edgecolors="black",
            linewidth=0.6,
            alpha=0.9,
        )
        ax.annotate(
            f" {met}",
            (row["FAR"], row["POD"]),
            fontsize=8,
            ha="left",
            va="center",
        )

    ax.set_title("Capacidad de Detección Binaria de Lluvia (POD vs. FAR)", fontweight="bold", pad=12)
    ax.set_xlabel("Tasa de Falsa Alarma (FAR)  -->  [Ideal = 0]")
    ax.set_ylabel("Probabilidad de Detección (POD)  -->  [Ideal = 1]")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, linestyle="--")

    # Referencia de esquina ideal
    ax.plot(0, 1, marker="*", markersize=14, color="gold", markeredgecolor="black")
    ax.text(0.02, 0.97, "Óptimo Ideal (0, 1)", fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    salida_fig2 = DIR_BASE / "evaluacion_deteccion_pod_far.png"
    plt.savefig(salida_fig2, dpi=300)
    plt.show()

    print("\n" + "=" * 80)
    print("PROCESAMIENTO Y GENERACIÓN DE REPORTES COMPLETADA CON ÉXITO.")
    print(f"Archivos exportados en: {DIR_BASE}")
    print("=" * 80)


if __name__ == "__main__":
    main()