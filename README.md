[01_extraccion_exploratoria_chirps.js](https://github.com/user-attachments/files/34975469/01_extraccion_exploratoria_chirps.js)
// ===============================
// PRUEBA CHIRPS - CUENCA LA MUMA
// AÑO: 2020
// ===============================

// 1. Cargar la cuenca (asset subido)
var cuenca = ee.FeatureCollection('projects/helical-mile-444620-n3/assets/lamuma');

// Visualizar la cuenca
Map.centerObject(cuenca, 9);
Map.addLayer(cuenca, {color: 'red'}, 'Cuenca La Muma');

// 2. Definir periodo de análisis
var inicio = '2024-01-01';
var fin    = '2024-12-31';

// 3. Cargar colección CHIRPS diaria
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
  .filterDate(inicio, fin);

// 4. Calcular precipitación media areal diaria
var precipitacionDiaria = chirps.map(function(image) {
  var media = image.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: cuenca,
    scale: 5000,   // CHIRPS ~5 km
    maxPixels: 1e13
  });

  return ee.Feature(null, {
    'fecha': image.date().format('YYYY-MM-dd'),
    'precip_mm': media.get('precipitation')
  });
});

// 5. Visualizar una muestra de la tabla
print('Precipitación diaria CHIRPS - 2020', precipitacionDiaria.limit(10));

// 6. Exportar a Google Drive (CSV)
Export.table.toDrive({
  collection: precipitacionDiaria,
  description: 'CHIRPS_LaMuma_2024',
  fileFormat: 'CSV'
});
