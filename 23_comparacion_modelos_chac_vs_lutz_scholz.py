import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# Configuración estética para figuras de reporte/tesis
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9.5,
        "figure.titlesize": 13,
    }
)


def cargar_chac(ruta_chac: str) -> pd.DataFrame:
    """Carga el archivo de CHAC (formato horizontal con meses en columnas)

    y lo transforma a serie cronológica continua (Año, Mes, Q_CHAC).
    """
    df = pd.read_excel(ruta_chac)
    df.columns = [str(c).strip() for c in df.columns]

    col_anio = [c for c in df.columns if c.lower() in ["año", "anio", "year"]][
        0
    ]

    meses_std = [
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

    # Convertir formato matricial a largo
    df_largo = df.melt(
        id_vars=[col_anio],
        value_vars=meses_std,
        var_name="Mes_Nom",
        value_name="Q_CHAC",
    )
    meses_num = {m: i + 1 for i, m in enumerate(meses_std)}
    df_largo["Mes"] = df_largo["Mes_Nom"].map(meses_num)
    df_largo = df_largo.rename(columns={col_anio: "Año"})
    df_largo["Año"] = df_largo["Año"].astype(int)
    df_largo["Mes"] = df_largo["Mes"].astype(int)

    df_largo = df_largo.sort_values(by=["Año", "Mes"]).reset_index(drop=True)
    return df_largo[["Año", "Mes", "Q_CHAC"]]


def cargar_lutz_scholz(ruta_lutz: str) -> pd.DataFrame:
    """Carga el archivo de Lutz Scholz (formato vertical por Fecha)

    y extrae (Año, Mes, Q_LutzScholz).
    """
    df = pd.read_excel(ruta_lutz)
    df.columns = [str(c).strip() for c in df.columns]

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Año"] = df["Fecha"].dt.year
    df["Mes"] = df["Fecha"].dt.month
    df["Q_LutzScholz"] = pd.to_numeric(df["Q_m3s"], errors="coerce")

    return df[["Año", "Mes", "Q_LutzScholz"]].sort_values(by=["Año", "Mes"])


def calcular_fdc(serie_caudales: np.ndarray):
    """Calcula la Curva de Duración de Caudales (FDC) y percentiles clave."""
    q_ordenado = np.sort(serie_caudales)[::-1]
    n = len(q_ordenado)
    prob_excedencia = (np.arange(1, n + 1) / (n + 1)) * 100

    q_50 = np.percentile(serie_caudales, 50)
    q_75 = np.percentile(serie_caudales, 25)  # Caudal excedido el 75%
    q_90 = np.percentile(serie_caudales, 10)  # Caudal excedido el 90%
    q_95 = np.percentile(serie_caudales, 5)  # Caudal excedido el 95%

    return prob_excedencia, q_ordenado, {
        "Q50": q_50,
        "Q75": q_75,
        "Q90": q_90,
        "Q95": q_95,
    }


def ejecutar_comparacion(ruta_chac: str, ruta_lutz: str, carpeta_salida: str):
    os.makedirs(carpeta_salida, exist_ok=True)

    print("Cargando y procesando serie simulada de CHAC...")
    df_chac = cargar_chac(ruta_chac)

    print("Cargando y procesando serie de Lutz Scholz...")
    df_lutz = cargar_lutz_scholz(ruta_lutz)

    # 1. Emparejamiento por Año y Mes (1980 - 2020)
    df_comp = pd.merge(df_chac, df_lutz, on=["Año", "Mes"]).dropna()

    q_chac = df_comp["Q_CHAC"].values
    q_lutz = df_comp["Q_LutzScholz"].values

    # 2. Métricas Estadísticas de Ajuste
    r, _ = stats.pearsonr(q_chac, q_lutz)
    r2 = r**2
    nse = 1 - (
        np.sum((q_chac - q_lutz) ** 2) / np.sum((q_lutz - np.mean(q_lutz)) ** 2)
    )
    pbias = 100 * np.sum(q_chac - q_lutz) / np.sum(q_lutz)
    rmse = np.sqrt(np.mean((q_chac - q_lutz) ** 2))
    mae = np.mean(np.abs(q_chac - q_lutz))

    print("\n" + "=" * 68)
    print("MÉTRICAS ESTADÍSTICAS DE COMPARACIÓN (CHAC vs. LUTZ SCHOLZ):")
    print("-" * 68)
    print(f"  Registros mensuales comparados     : {len(df_comp)} meses (1980–2020)")
    print(f"  Caudal Medio Multianual CHAC       : {np.mean(q_chac):.3f} m³/s")
    print(f"  Caudal Medio Multianual Lutz Scholz: {np.mean(q_lutz):.3f} m³/s")
    print(f"  Coeficiente de Determinación (R²)  : {r2:.4f}")
    print(f"  Eficiencia Nash-Sutcliffe (NSE)    : {nse:.4f}")
    print(f"  Sesgo Porcentual (PBIAS)           : {pbias:+.2f} %")
    print(f"  Error Cuadrático Medio (RMSE)      : {rmse:.3f} m³/s")
    print(f"  Error Absoluto Medio (MAE)         : {mae:.3f} m³/s")
    print("=" * 68)

    # 3. Curvas de Duración de Caudales (FDC)
    prob_chac, fdc_chac, p_chac = calcular_fdc(q_chac)
    prob_lutz, fdc_lutz, p_lutz = calcular_fdc(q_lutz)

    print("\nCAUDALES DE PERSISTENCIA / CURVA DE DURACIÓN:")
    print("-" * 68)
    print(
        f"  Q50 (Mediana)  : CHAC = {p_chac['Q50']:.3f} m³/s | Lutz Scholz = {p_lutz['Q50']:.3f} m³/s"
    )
    print(
        f"  Q75 (Diseño)   : CHAC = {p_chac['Q75']:.3f} m³/s | Lutz Scholz = {p_lutz['Q75']:.3f} m³/s"
    )
    print(
        f"  Q90 (Garantía) : CHAC = {p_chac['Q90']:.3f} m³/s | Lutz Scholz = {p_lutz['Q90']:.3f} m³/s"
    )
    print(
        f"  Q95 (Ecológico): CHAC = {p_chac['Q95']:.3f} m³/s | Lutz Scholz = {p_lutz['Q95']:.3f} m³/s"
    )
    print("=" * 68)

    # 4. Hidrograma Medio Mensual
    hidro_df = (
        df_comp.groupby("Mes")[["Q_CHAC", "Q_LutzScholz"]].mean().reset_index()
    )
    meses_etiquetas = [
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    ]
    hidro_df["Mes_Nom"] = meses_etiquetas

    # 5. Generación de Gráficos (4 Paneles)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel A: Hidrograma Medio Mensual
    ax_hidro = axes[0, 0]
    ax_hidro.plot(
        hidro_df["Mes"],
        hidro_df["Q_CHAC"],
        marker="o",
        color="#1f77b4",
        linewidth=2,
        label="Modelo CHAC",
    )
    ax_hidro.plot(
        hidro_df["Mes"],
        hidro_df["Q_LutzScholz"],
        marker="s",
        color="#d62728",
        linewidth=2,
        linestyle="--",
        label="Modelo Lutz Scholz",
    )
    # Aforos históricos en campo
    ax_hidro.scatter(
        [6], [0.171], color="black", zorder=5, s=70, label="Aforo Jun 2011 (0.171 m³/s)"
    )
    ax_hidro.scatter(
        [10], [0.194], color="green", zorder=5, s=70, label="Aforo Oct 2013 (0.194 m³/s)"
    )
    ax_hidro.set_xticks(range(1, 13))
    ax_hidro.set_xticklabels(meses_etiquetas)
    ax_hidro.set_ylabel("Caudal Medio (m³/s)")
    ax_hidro.set_title("A. Hidrograma Medio Mensual Multianual (1980–2020)")
    ax_hidro.grid(True, linestyle=":", alpha=0.6)
    ax_hidro.legend(loc="upper right")

    # Panel B: Curva de Duración de Caudales (FDC)
    ax_fdc = axes[0, 1]
    ax_fdc.plot(
        prob_chac, fdc_chac, color="#1f77b4", linewidth=2, label="CHAC"
    )
    ax_fdc.plot(
        prob_lutz,
        fdc_lutz,
        color="#d62728",
        linewidth=2,
        linestyle="--",
        label="Lutz Scholz",
    )
    ax_fdc.axvline(75, color="gray", linestyle=":", alpha=0.7)
    ax_fdc.axvline(90, color="gray", linestyle=":", alpha=0.7)
    ax_fdc.axvline(95, color="gray", linestyle=":", alpha=0.7)
    ax_fdc.set_xlabel("Probabilidad de Excedencia (%)")
    ax_fdc.set_ylabel("Caudal (m³/s)")
    ax_fdc.set_title("B. Curva de Duración de Caudales (FDC)")
    ax_fdc.grid(True, linestyle=":", alpha=0.6)
    ax_fdc.legend(loc="upper right")

    # Panel C: Diagrama de Dispersión
    ax_scat = axes[1, 0]
    ax_scat.scatter(
        q_lutz, q_chac, color="#2ca02c", alpha=0.45, edgecolors="none"
    )
    max_val = max(np.max(q_lutz), np.max(q_chac)) * 1.05
    ax_scat.plot(
        [0, max_val],
        [0, max_val],
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="Línea 1:1",
    )
    slope, intercept = np.polyfit(q_lutz, q_chac, 1)
    ax_scat.plot(
        [0, max_val],
        [intercept, slope * max_val + intercept],
        color="blue",
        linestyle="-",
        label=f"Ajuste: y={slope:.2f}x + {intercept:.2f}",
    )
    ax_scat.set_xlabel("Caudal Lutz Scholz (m³/s)")
    ax_scat.set_ylabel("Caudal CHAC (m³/s)")
    ax_scat.set_title(
        f"C. Correlación Mensual (R² = {r2:.3f}, NSE = {nse:.3f})"
    )
    ax_scat.grid(True, linestyle=":", alpha=0.6)
    ax_scat.legend(loc="lower right")

    # Panel D: Serie Continua Reciente (2010–2020)
    ax_serie = axes[1, 1]
    df_zoom = df_comp[df_comp["Año"] >= 2010].copy()
    fechas = pd.to_datetime(
        df_zoom["Año"].astype(str) + "-" + df_zoom["Mes"].astype(str) + "-01"
    )
    ax_serie.plot(
        fechas,
        df_zoom["Q_CHAC"],
        label="CHAC",
        color="#1f77b4",
        linewidth=1.5,
    )
    ax_serie.plot(
        fechas,
        df_zoom["Q_LutzScholz"],
        label="Lutz Scholz",
        color="#d62728",
        linestyle="--",
        linewidth=1.5,
    )
    ax_serie.set_ylabel("Caudal (m³/s)")
    ax_serie.set_title("D. Comparación de Series Temporales (2010–2020)")
    ax_serie.grid(True, linestyle=":", alpha=0.6)
    ax_serie.legend(loc="upper right")

    plt.tight_layout()
    ruta_figura = os.path.join(
        carpeta_salida, "comparacion_CHAC_vs_LutzScholz.png"
    )
    plt.savefig(ruta_figura, dpi=300)
    plt.close()
    print(f"\nGráfico comparativo generado en:\n  -> {ruta_figura}")

    # 6. Exportar Resultados a Excel Consolidado
    ruta_excel_out = os.path.join(
        carpeta_salida, "resumen_comparativo_CHAC_vs_LutzScholz.xlsx"
    )
    with pd.ExcelWriter(ruta_excel_out) as writer:
        df_comp.to_excel(writer, sheet_name="Series_1980_2020", index=False)

        hidro_df[
            [
                "Mes",
                "Mes_Nom",
                "Q_CHAC",
                "Q_LutzScholz",
            ]
        ].to_excel(writer, sheet_name="Hidrograma_Medio", index=False)

        df_metricas = pd.DataFrame(
            [
                {
                    "Métrica": "Caudal Medio Multianual (m³/s)",
                    "CHAC": np.mean(q_chac),
                    "Lutz_Scholz": np.mean(q_lutz),
                },
                {
                    "Métrica": "Q50 - Mediana (m³/s)",
                    "CHAC": p_chac["Q50"],
                    "Lutz_Scholz": p_lutz["Q50"],
                },
                {
                    "Métrica": "Q75 - Diseño PCH (m³/s)",
                    "CHAC": p_chac["Q75"],
                    "Lutz_Scholz": p_lutz["Q75"],
                },
                {
                    "Métrica": "Q90 - Firmeza/Garantía (m³/s)",
                    "CHAC": p_chac["Q90"],
                    "Lutz_Scholz": p_lutz["Q90"],
                },
                {
                    "Métrica": "Q95 - Caudal Ecológico (m³/s)",
                    "CHAC": p_chac["Q95"],
                    "Lutz_Scholz": p_lutz["Q95"],
                },
                {
                    "Métrica": "Coeficiente de Determinación (R²)",
                    "CHAC vs LS": r2,
                },
                {
                    "Métrica": "Eficiencia Nash-Sutcliffe (NSE)",
                    "CHAC vs LS": nse,
                },
                {"Métrica": "Sesgo Porcentual PBIAS (%)", "CHAC vs LS": pbias},
                {"Métrica": "RMSE (m³/s)", "CHAC vs LS": rmse},
                {"Métrica": "MAE (m³/s)", "CHAC vs LS": mae},
            ]
        )
        df_metricas.to_excel(writer, sheet_name="Metricas_y_FDC", index=False)

    print(f"Resumen Excel consolidado en:\n  -> {ruta_excel_out}\n")


if __name__ == "__main__":
    CARPETA_BASE = r"D:\tesis hidrologia\CAP_4\ANALISIS4_1\caudales medios"

    RUTA_CHAC = os.path.join(
        CARPETA_BASE, "CHAC", "caudales_simulados_CHAC.xlsx"
    )
    RUTA_LUTZ = os.path.join(
        CARPETA_BASE, "caudales_mensuales_lutz_scholz_1980_2020.xlsx"
    )
    CARPETA_SALIDA = os.path.join(CARPETA_BASE, "COMPARACION_MODELOS")
    

    ejecutar_comparacion(
        ruta_chac=RUTA_CHAC,
        ruta_lutz=RUTA_LUTZ,
        carpeta_salida=CARPETA_SALIDA,
    )