[LEAME.txt](https://github.com/user-attachments/files/34972161/LEAME.txt)
# 💧 Estimación de Caudales mediante Datos Satelitales de Precipitación para Pequeñas Centrales Hidroeléctricas (Caso de Estudio: Río La Muma, Ichoca - Bolivia)

Repositorio oficial con los scripts de extracción geoespacial, control de calidad, corrección de sesgo y modelación hidrológica desarrollados para la tesis de maestría:

> **"UTILIZACIÓN DE DATOS SATELITALES DE PRECIPITACIÓN PARA LA ESTIMACIÓN DE CAUDALES EN PEQUEÑAS CENTRALES HIDROELÉCTRICAS. CASO DE ESTUDIO EN EL RÍO LA MUMA, MUNICIPIO DE ICHOCA"**

---

## 🎯 Objetivo del Proyecto
Desarrollar una metodología reproducible en cuencas andinas de alta montaña con escasa instrumentación meteorológica (3,290 – 5,194 m s.n.m.) para estimar series históricas de caudales medios, curvas de duración de caudales (CDC), crecidas de diseño y potencial hidroenergético mediante productos satelitales y de reanálisis (MSWEP v2.0, CHIRPS, ERA5-Land).

## 📍 Área de Estudio
* **Cuenca:** Río La Muma (Municipio de Ichoca, Provincia Inquisivi, Departamento de La Paz, Bolivia).
* **Ubicación de obra de toma:** Latitud $-17.087238^\circ$, Longitud $-67.180081^\circ$ (Elevación: $3,290\text{ m s.n.m.}$).
* **Superficie de aporte:** $\approx 17\text{ km}^2$ (ambiente altoandino de Puna/Páramo).

---

## 📂 Estructura y Scripts del Repositorio

### 1. Extracción Geoespacial (Google Earth Engine - JavaScript)
* **`01_extraccion_chirps_lamuma.js`**: Extracción de series diarias de precipitación media areal ($\text{mm/día}$) del producto **CHIRPS Daily v2.0** (`UCSB-CHG/CHIRPS/DAILY`) sobre el polígono vectorial delimitado de la cuenca del Río La Muma y exportación tabular en formato `.csv` hacia Google Drive.
* *(Próximamente)* Scripts de extracción para **MSWEP v2.0**, **ERA5-Land** (precipitación y temperatura) y Modelo Digital de Elevación (**SRTM 30m**).

### 2. Procesamiento, Control de Calidad y Modelación Hidrológica (Python)
*(En proceso de carga)*
* Control de calidad (QC), detección de valores atípicos (*outliers*) e imputación de series pluviométricas y térmicas (ajuste por gradiente altitudinal).
* Validación estadística multi-satélite (métricas continuas: $R$, $KGE$, $NSE$, $PBIAS$, $RMSE$, $MAE$; métricas categóricas: $POD$, $FAR$, $CSI$) y corrección de sesgo mediante **Mapeo de Cuantiles Empíricos (EQM)**.
* Balance hídrico mensual y generación de caudales medios (1980–2020) mediante los modelos **Lutz Scholz** y **Témez (CHAC)**, calibrados con aforos de campo.
* Análisis de frecuencia de precipitaciones máximas, hietogramas de bloques alternos y modelación de crecidas ($T_r = 25, 50, 100\text{ años}$) acoplados a **HEC-HMS 4.12**.

---

## 🛠️ Tecnologías y Herramientas Utilizadas
* **Plataformas en la nube:** Google Earth Engine (GEE JavaScript API).
* **Lenguajes y librerías:** Python 3.13+ (`pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `statsmodels`, `openpyxl`).
* **SIG e Hidrología:** QGIS 3.34, SAGA GIS 9.5, HEC-HMS 4.12.

---

## 👨‍🔬 Autor
**Ing. Rogelio José Choque Castro**  
Ingeniero Electricista (SIB) | Maestrando en Recursos Hídricos, Hidráulica e Ingeniería Sanitaria  
La Paz, Bolivia
