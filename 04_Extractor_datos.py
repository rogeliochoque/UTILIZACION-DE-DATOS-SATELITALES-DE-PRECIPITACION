import os
import numpy as np
import xarray as xr
import rasterio
import csv

from rasterio.features import rasterize, shapes
from shapely.geometry import shape
from shapely.ops import unary_union
from pyproj import Transformer
from affine import Affine

# ==============================
# CONFIGURACIÓN
# ==============================

CARPETA_NC = r"D:\diarios_11_03_2026\nc"
RASTER_CUENCA = r"D:\diarios_11_03_2026\lamuma.tif"
CSV_SALIDA = r"D:\diarios_11_03_2026\precipitaciones\precipitacion_2022.csv"

os.makedirs(os.path.dirname(CSV_SALIDA), exist_ok=True)

# ==============================
# 1 LEER CUENCA
# ==============================

print("Leyendo cuenca...")

with rasterio.open(RASTER_CUENCA) as src:

    data = src.read(1)
    transform = src.transform
    crs_raster = src.crs

    geoms = []

    for geom, value in shapes(data, transform=transform):

        if value > 0:
            geoms.append(shape(geom))

cuenca = unary_union(geoms)

print("Cuenca cargada.")

# ==============================
# 2 REPROYECTAR CUENCA
# ==============================

print("Reproyectando cuenca a lat/lon...")

transformer = Transformer.from_crs(crs_raster, "EPSG:4326", always_xy=True)

def reproyectar(geom):

    x, y = geom.exterior.coords.xy
    coords = [transformer.transform(xi, yi) for xi, yi in zip(x, y)]

    from shapely.geometry import Polygon
    return Polygon(coords)

cuenca_ll = reproyectar(cuenca)

print("Reproyección terminada.")

# ==============================
# 3 LEER GRILLA NETCDF
# ==============================

archivos = sorted([f for f in os.listdir(CARPETA_NC) if f.endswith(".nc")])

primer_nc = os.path.join(CARPETA_NC, archivos[0])

ds = xr.open_dataset(primer_nc)

lat = ds["lat"].values
lon = ds["lon"].values

ds.close()

print("Resolución grilla:", lat.size, "x", lon.size)

# ==============================
# 4 CREAR TRANSFORMACION
# ==============================

res_lat = abs(lat[1] - lat[0])
res_lon = abs(lon[1] - lon[0])

transform_nc = Affine.translation(lon.min() - res_lon/2, lat.max() + res_lat/2) * Affine.scale(res_lon, -res_lat)

# ==============================
# 5 RASTERIZAR CUENCA
# ==============================

print("Rasterizando cuenca en grilla satelital...")

mask = rasterize(
    [(cuenca_ll, 1)],
    out_shape=(len(lat), len(lon)),
    transform=transform_nc,
    fill=0,
    dtype="uint8"
)

mask = mask.astype(bool)

print("Pixeles dentro de la cuenca:", mask.sum())

# ==============================
# 6 PROCESAR ARCHIVOS
# ==============================

print("Procesando precipitación diaria...")

with open(CSV_SALIDA, "w", newline="") as f:

    writer = csv.writer(f)
    writer.writerow(["fecha", "precipitacion_mm"])

    for archivo in archivos:

        ruta = os.path.join(CARPETA_NC, archivo)

        ds = xr.open_dataset(ruta)

        fecha = str(ds["time"].values[0])[:10]

        p = ds["precipitation"].values[0]

        valor = np.nanmean(p[mask])

        writer.writerow([fecha, round(float(valor), 3)])

        print(fecha, round(float(valor),2),"mm")

        ds.close()

print("Proceso terminado.")
print("Archivo guardado en:")
print(CSV_SALIDA)