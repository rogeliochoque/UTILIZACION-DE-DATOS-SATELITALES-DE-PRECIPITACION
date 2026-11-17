// ===============================
// ERA5 (HOURLY) → DIARIO
// CUENCA LA MUMA - AÑO 2020
// ===============================

// 1. Cargar cuenca
var cuenca = ee.FeatureCollection('projects/helical-mile-444620-n3/assets/lamuma');

Map.centerObject(cuenca, 9);
Map.addLayer(cuenca, {color: 'purple'}, 'Cuenca La Muma');

// 2. Definir periodo
var inicio = ee.Date('2020-01-01');
var fin    = ee.Date('2021-01-01');

// 3. Cargar ERA5 horario
var era5 = ee.ImageCollection('ECMWF/ERA5/HOURLY')
  .filterDate(inicio, fin)
  .select('total_precipitation');

// 4. Crear lista de días
var dias = ee.List.sequence(0, fin.difference(inicio, 'day').subtract(1));

// 5. Agregar a diario
var era5Diario = ee.FeatureCollection(
  dias.map(function(d) {

    var fechaInicio = inicio.advance(d, 'day');
    var fechaFin = fechaInicio.advance(1, 'day');

    // Suma horaria → acumulado diario (en m)
    var diario = era5
      .filterDate(fechaInicio, fechaFin)
      .sum()
      .multiply(1000); // m → mm

    // Media areal
    var media = diario.reduceRegion({
      reducer: ee.Reducer.mean(),
      geometry: cuenca,
      scale: 31000,   // ERA5 ~31 km
      maxPixels: 1e13
    });

    return ee.Feature(null, {
      'fecha': fechaInicio.format('YYYY-MM-dd'),
      'precip_mm': media.get('total_precipitation')
    });
  })
);

// 6. Ver muestra
print('ERA5 diario - La Muma (2020)', era5Diario.limit(10));

// 7. Exportar a Drive
Export.table.toDrive({
  collection: era5Diario,
  description: 'ERA5_LaMuma_2020',
  fileFormat: 'CSV'
});
