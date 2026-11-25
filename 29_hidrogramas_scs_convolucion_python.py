import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==============================================================================
# 1. DATOS DE ENTRADA Y PARÁMETROS FISIOGRÁFICOS
# ==============================================================================
A_km2 = 48.65
tc_hr = 2.0
dt_min = 10
dt_hr = dt_min / 60.0

# Hietogramas de diseño (Precipitación incremental en mm cada 10 min)
tiempo_min = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])
hietogramas = {
    25:  np.array([0.38, 0.42, 0.49, 0.60, 0.80, 1.40, 4.88, 1.00, 0.68, 0.54, 0.46, 0.40]),
    50:  np.array([0.43, 0.49, 0.57, 0.69, 0.93, 1.61, 5.62, 1.15, 0.79, 0.62, 0.53, 0.46]),
    100: np.array([0.50, 0.56, 0.66, 0.80, 1.07, 1.86, 6.48, 1.33, 0.91, 0.72, 0.61, 0.53])
}

# ==============================================================================
# 2. PARÁMETROS SCS (CONDICIÓN AMC III - SUELO HÚMEDO / SATURADO)
# ==============================================================================
CN_II = 77.0
CN_III = CN_II / (0.427 + 0.00573 * CN_II)  # CN_III ≈ 88.7
S_mm = (25400.0 / CN_III) - 254.0           # S ≈ 32.37 mm
Ia_mm = 0.20 * S_mm                         # Ia ≈ 6.47 mm

# ==============================================================================
# 3. HIDROGRAMA UNITARIO SINTÉTICO SCS
# ==============================================================================
t_lag_hr = 0.6 * tc_hr
tp_hr = (dt_hr / 2.0) + t_lag_hr
tb_hr = 5.0 * tp_hr
qp_unit = (0.208 * A_km2) / tp_hr

# Coordenadas adimensionales estándar SCS (curva gamma discretizada)
t_adim = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 
                   2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.5, 4.0, 4.5, 5.0])
q_adim = np.array([0.0, 0.05, 0.17, 0.43, 0.77, 1.00, 0.93, 0.76, 0.58, 0.42, 
                   0.30, 0.21, 0.15, 0.10, 0.07, 0.045, 0.02, 0.007, 0.001, 0.0])

t_hu = np.arange(0, tb_hr + dt_hr, dt_hr)
hu_ordenadas = np.interp(t_hu / tp_hr, t_adim, q_adim) * qp_unit

# Conservación de masa: Volumen HU = 1 mm * Área
vol_teorico = 1.0 * (A_km2 * 1e6) * 1e-3
vol_hu = np.sum(hu_ordenadas) * (dt_hr * 3600.0)
hu_ordenadas = hu_ordenadas * (vol_teorico / vol_hu)

# ==============================================================================
# 4. CONVOLUCIÓN DISCRETA Y RESULTADOS
# ==============================================================================
res = []
graficos = {}

for Tr, hietograma in hietogramas.items():
    P_acum = np.cumsum(hietograma)
    Pe_acum = np.zeros_like(P_acum)
    
    for i, p in enumerate(P_acum):
        if p > Ia_mm:
            Pe_acum[i] = ((p - Ia_mm) ** 2) / (p - Ia_mm + S_mm)
        else:
            Pe_acum[i] = 0.0
            
    Pe_inc = np.diff(np.insert(Pe_acum, 0, 0.0))
    
    # Convolución
    Q_crecida = np.convolve(Pe_inc, hu_ordenadas)
    t_crecida = np.arange(0, len(Q_crecida)) * dt_hr
    
    Q_max = np.max(Q_crecida)
    t_pico = t_crecida[np.argmax(Q_crecida)]
    
    res.append({
        "Tr (años)": Tr,
        "P_total (mm)": round(np.sum(hietograma), 2),
        "Pe_total (mm)": round(np.sum(Pe_inc), 2),
        "Q_pico (m³/s)": round(Q_max, 2),
        "t_pico (h)": round(t_pico, 2)
    })
    graficos[Tr] = (t_crecida, Q_crecida)

df = pd.DataFrame(res)
print(df.to_string(index=False))

# Visualización
plt.figure(figsize=(9, 4.5))
for Tr in [25, 50, 100]:
    t_plot, q_plot = graficos[Tr]
    plt.plot(t_plot, q_plot, lw=2, label=f"Tr = {Tr} años (Qmax = {np.max(q_plot):.2f} m³/s)")

plt.title("Hidrogramas de Crecida de Diseño (SCS - Bloques Alternos, AMC III)", fontsize=12)
plt.xlabel("Tiempo (horas)", fontsize=10)
plt.ylabel("Caudal de crecida (m³/s)", fontsize=10)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.show()