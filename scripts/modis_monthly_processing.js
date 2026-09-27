var HAINAN_ASSET = 'projects/cellular-arbor-505708-h7/assets/hainan';

var START_YEAR = 2010;
var END_YEAR = 2023;

var CRS = 'EPSG:32649';

var CANOPY_SCALE = 1000;
var PRI_SCALE = 1000;
var LAI_SCALE = 500;
var NDVI_SCALE = 500;

var CANOPY_FOLDER = '冠层温度';
var PRI_FOLDER = 'PRI';
var LAI_FOLDER = 'LAI';
var NDVI_FOLDER = 'NDVI';

var LAI_THRESHOLD = 0.5;

var EXPORT_NDVI = true;

// Replace with your own Hainan boundary asset path in GEE
var regionFc = ee.FeatureCollection(HAINAN_ASSET);
var region = regionFc.geometry();

var startDate = ee.Date.fromYMD(START_YEAR, 1, 1);
var endDate = ee.Date.fromYMD(END_YEAR + 1, 1, 1);

Map.centerObject(regionFc, 8);
Map.addLayer(
  regionFc.style({
    color: 'red',
    fillColor: '00000000',
    width: 2
  }),
  {},
  '海南省研究区'
);

var lstRaw = ee.ImageCollection('MODIS/061/MOD11A1')
  .filterBounds(region)
  .filterDate(startDate, endDate);

var laiRaw = ee.ImageCollection('MODIS/061/MCD15A3H')
  .filterBounds(region)
  .filterDate(startDate, endDate);

var priRaw = ee.ImageCollection('MODIS/006/MODOCGA')
  .filterBounds(region)
  .filterDate(startDate, endDate);

var ndviRaw = ee.ImageCollection('MODIS/061/MOD09A1')
  .filterBounds(region)
  .filterDate(startDate, endDate);

function processLST(img) {

  var qc = img.select('QC_Day');

  var mandatory = qc.bitwiseAnd(3).lte(1);

  var dataQuality = qc.rightShift(2).bitwiseAnd(3).lte(1);

  var emissivityError = qc.rightShift(4).bitwiseAnd(3).lte(1);

  var lstError = qc.rightShift(6).bitwiseAnd(3).lte(1);

  var raw = img.select('LST_Day_1km');

  var validRange = raw.gte(7500).and(raw.lte(65535));

  var lstCelsius = raw
    .multiply(0.02)
    .subtract(273.15);

  var mask = mandatory
    .and(dataQuality)
    .and(emissivityError)
    .and(lstError)
    .and(validRange);

  return lstCelsius
    .updateMask(mask)
    .rename('LST')
    .copyProperties(img, ['system:time_start']);
}

function processLAI(img) {

  var qc = img.select('FparLai_QC');

  var modland = qc.bitwiseAnd(1).eq(0);

  var deadDetector = qc.rightShift(2).bitwiseAnd(1).eq(0);

  var cloudState = qc.rightShift(3).bitwiseAnd(3).eq(0);

  var scf = qc.rightShift(5).bitwiseAnd(7).lte(1);

  var raw = img.select('Lai');

  var validRange = raw.gte(0).and(raw.lte(100));

  var laiValue = raw.multiply(0.1);

  var mask = modland
    .and(deadDetector)
    .and(cloudState)
    .and(scf)
    .and(validRange);

  return laiValue
    .updateMask(mask)
    .rename('LAI')
    .copyProperties(img, ['system:time_start']);
}

function processPRI(img) {

  var qc = img.select('QC_b8_15_1km');

  var q11 = qc.rightShift(12).bitwiseAnd(15).eq(0);

  var q12 = qc.rightShift(16).bitwiseAnd(15).eq(0);

  var raw11 = img.select('sur_refl_b11');
  var raw12 = img.select('sur_refl_b12');

  var validRaw = raw11.gte(-100)
    .and(raw11.lte(16000))
    .and(raw12.gte(-100))
    .and(raw12.lte(16000));

  var b11 = raw11.multiply(0.0001);
  var b12 = raw12.multiply(0.0001);

  var denominator = b11.add(b12);

  var validReflectance = b11.gt(0)
    .and(b12.gt(0))
    .and(b11.lte(1.6))
    .and(b12.lte(1.6))
    .and(denominator.gt(0.001));

  var mask = q11
    .and(q12)
    .and(validRaw)
    .and(validReflectance);

  // PRI from Band 11 (531 nm) and Band 12 (556 nm)
  var priValue = b11
    .subtract(b12)
    .divide(denominator)
    .updateMask(mask);

  priValue = priValue.updateMask(
    priValue.gte(-1).and(priValue.lte(1))
  );

  return priValue
    .rename('PRI')
    .copyProperties(img, ['system:time_start']);
}

function processNDVI(img) {

  var qa = img.select('QA');
  var state = img.select('StateQA');

  var modland = qa.bitwiseAnd(3).eq(0);

  var band1Quality = qa.rightShift(2).bitwiseAnd(15).eq(0);

  var band2Quality = qa.rightShift(6).bitwiseAnd(15).eq(0);

  var clear = state.bitwiseAnd(3).eq(0);

  var noCloudShadow = state.rightShift(2).bitwiseAnd(1).eq(0);

  var noCirrus = state.rightShift(8).bitwiseAnd(3).eq(0);

  var noInternalCloud = state.rightShift(10).bitwiseAnd(1).eq(0);

  var noSnowIce = state.rightShift(12).bitwiseAnd(1).eq(0);

  var notAdjacentCloud = state.rightShift(13).bitwiseAnd(1).eq(0);

  var noInternalSnow = state.rightShift(15).bitwiseAnd(1).eq(0);

  var rawRed = img.select('sur_refl_b01');
  var rawNir = img.select('sur_refl_b02');

  var red = rawRed.multiply(0.0001);
  var nir = rawNir.multiply(0.0001);

  var denominator = nir.add(red);

  var validReflectance = red.gt(0)
    .and(nir.gt(0))
    .and(red.lte(1.6))
    .and(nir.lte(1.6))
    .and(denominator.gt(0.001));

  // QA bitmask: remove cloud, shadow, snow and low-quality pixels
  var mask = modland
    .and(band1Quality)
    .and(band2Quality)
    .and(clear)
    .and(noCloudShadow)
    .and(noCirrus)
    .and(noInternalCloud)
    .and(noSnowIce)
    .and(notAdjacentCloud)
    .and(noInternalSnow)
    .and(validReflectance);

  var ndviValue = nir
    .subtract(red)
    .divide(denominator)
    .updateMask(mask);

  ndviValue = ndviValue.updateMask(
    ndviValue.gte(-1).and(ndviValue.lte(1))
  );

  return ndviValue
    .rename('NDVI')
    .copyProperties(img, ['system:time_start']);
}

var lst = lstRaw.map(processLST);
var lai = laiRaw.map(processLAI);
var pri = priRaw.map(processPRI);
var ndvi = ndviRaw.map(processNDVI);

function monthlyLAI(start, end) {
  // Monthly aggregation: mean of valid pixels per month
  return lai
    .filterDate(start, end)
    .mean()
    .clip(region)
    .rename('LAI')
    .toFloat();
}

function monthlyPRI(start, end) {
  return pri
    .filterDate(start, end)
    .mean()
    .clip(region)
    .rename('PRI')
    .toFloat();
}

function monthlyNDVI(start, end) {
  return ndvi
    .filterDate(start, end)
    .mean()
    .clip(region)
    .rename('NDVI')
    .toFloat();
}

function monthlyCanopy(start, end) {

  var monthlyLST = lst
    .filterDate(start, end)
    .mean();

  var monthlyLAIImage = lai
    .filterDate(start, end)
    .mean();

  // Vegetation mask: retain pixels with LAI > 0.5
  var vegetationMask = monthlyLAIImage.gte(LAI_THRESHOLD);

  return monthlyLST
    .updateMask(vegetationMask)
    .clip(region)
    .rename('CanopyTemp')
    .toFloat();
}

function pad2(n) {
  return n < 10 ? '0' + n : '' + n;
}

for (var year = START_YEAR; year <= END_YEAR; year++) {

  for (var month = 1; month <= 12; month++) {

    var mm = pad2(month);
    var fileName = year + '_' + mm;

    var start = ee.Date.fromYMD(year, month, 1);
    var end = start.advance(1, 'month');

    Export.image.toDrive({
      image: monthlyLAI(start, end),
      description: 'LAI_' + fileName,
      folder: LAI_FOLDER,
      fileNamePrefix: fileName,
      region: region,
      crs: CRS,
      scale: LAI_SCALE,
      maxPixels: 1e13,
      fileFormat: 'GeoTIFF'
    });

    Export.image.toDrive({
      image: monthlyPRI(start, end),
      description: 'PRI_' + fileName,
      folder: PRI_FOLDER,
      fileNamePrefix: fileName,
      region: region,
      crs: CRS,
      scale: PRI_SCALE,
      maxPixels: 1e13,
      fileFormat: 'GeoTIFF'
    });

    if (EXPORT_NDVI) {
      Export.image.toDrive({
        image: monthlyNDVI(start, end),
        description: 'NDVI_' + fileName,
        folder: NDVI_FOLDER,
        fileNamePrefix: fileName,
        region: region,
        crs: CRS,
        scale: NDVI_SCALE,
        maxPixels: 1e13,
        fileFormat: 'GeoTIFF'
      });
    }

    Export.image.toDrive({
      image: monthlyCanopy(start, end),
      description: 'Canopy_' + fileName,
      folder: CANOPY_FOLDER,
      fileNamePrefix: fileName,
      region: region,
      crs: CRS,
      scale: CANOPY_SCALE,
      maxPixels: 1e13,
      fileFormat: 'GeoTIFF'
    });

  }
}

var previewStart = ee.Date.fromYMD(2023, 7, 1);
var previewEnd = previewStart.advance(1, 'month');

Map.addLayer(
  monthlyLAI(previewStart, previewEnd),
  {
    min: 0,
    max: 7,
    palette: ['ffffcc', 'c2e699', '78c679', '31a354', '006837']
  },
  '2023-07 LAI',
  false
);

Map.addLayer(
  monthlyNDVI(previewStart, previewEnd),
  {
    min: 0,
    max: 1,
    palette: ['ffffff', 'd9f0a3', '78c679', '238443', '004529']
  },
  '2023-07 NDVI',
  false
);

Map.addLayer(
  monthlyPRI(previewStart, previewEnd),
  {
    min: -0.2,
    max: 0.2,
    palette: ['313695', 'ffffff', 'a50026']
  },
  '2023-07 PRI',
  false
);

Map.addLayer(
  monthlyCanopy(previewStart, previewEnd),
  {
    min: 15,
    max: 40,
    palette: ['313695', '74add1', 'ffffbf', 'f46d43', 'a50026']
  },
  '2023-07 冠层温度',
  true
);

var totalMonths = (END_YEAR - START_YEAR + 1) * 12;
var totalProducts = EXPORT_NDVI ? 4 : 3;
var totalTasks = totalMonths * totalProducts;

print('============================================================');
print('海南省 MODIS 月尺度处理脚本');
print('============================================================');
print('研究区：', HAINAN_ASSET);
print('年份：', START_YEAR + '—' + END_YEAR);
print('输出坐标系：', CRS);
print('LAI 植被阈值：LAI >= ' + LAI_THRESHOLD);
print('LAI 分辨率：' + LAI_SCALE + ' m');
print('PRI 分辨率：' + PRI_SCALE + ' m');
print('NDVI 分辨率：' + NDVI_SCALE + ' m');
print('冠层温度分辨率：' + CANOPY_SCALE + ' m');
print('月份数量：', totalMonths);
print('是否导出 NDVI：', EXPORT_NDVI);
print('预计导出任务总数：', totalTasks);
print('文件命名：YYYY_MM.tif');
print('起始文件：' + START_YEAR + '_01.tif');
print('结束文件：' + END_YEAR + '_12.tif');

print('MOD11A1 原始影像数：', lstRaw.size());
print('MCD15A3H 原始影像数：', laiRaw.size());
print('MODOCGA 原始影像数：', priRaw.size());
print('MOD09A1 原始影像数：', ndviRaw.size());

print('说明：运行脚本后，到右侧 Tasks 面板逐个点击 Run 开始导出。');
