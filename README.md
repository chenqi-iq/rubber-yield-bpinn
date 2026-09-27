# Bayesian Physics-Informed Neural Network for Rubber Yield Estimation in Hainan, China

This repository contains the code and data processing pipeline for the paper *"Estimation of Rubber Yield in Hainan Island Using a Multi-source Remote Sensing Fusion Bayesian Approximate Physics-Informed Neural Network"*.

We develop a Bayesian physics-informed neural network (BPINN) that couples a monthly carbon-balance module with neural-network residuals to estimate rubber yield across 18 county-level units of Hainan Island, China, for the period 2010–2023.

---

## Data Sources

### Remote Sensing Data (processed via Google Earth Engine)

| Variable | MODIS Product | Temporal Resolution | Spatial Resolution |
|---|---|---|---|
| Canopy temperature (LST) | MOD11A1 V6.1 | Daily | 1000 m |
| Leaf Area Index (LAI) | MCD15A3H V6.1 | 4-day | 500 m |
| Photochemical Reflectance Index (PRI) | MCD19A1 V6.1 | Daily | 1000 m |
| NDVI | MOD09A1 V6.1 | 8-day | 500 m |

All remote sensing products are publicly available through [NASA LAADS](https://ladsweb.modaps.eosdis.nasa.gov/) or the [Google Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets).

### Soil Data

- **HWSD2 (Harmonized World Soil Database version 2)**: topsoil pH and organic matter, available from the [Food and Agriculture Organization (FAO)](https://www.fao.org/soils-portal/data-hub/soil-maps-and-databases/harmonized-world-soil-database-v2/en/).

### Statistical Data

- **Rubber area and production statistics** (2010–2023): city/county-level harvested area and total production, publicly available from the [Hainan Provincial Bureau of Statistics](http://tjj.hainan.gov.cn/).

### Administrative Boundary

- Hainan Island county-level boundaries: available from the [National Geomatics Center of China](http://www.ngcc.cn/) or standard GADM datasets.

---

## Repository Structure

```
rubber-yield-bpinn/
├── README.md                          # This file
├── scripts/
│   ├── modis_monthly_processing.js    # GEE script for MODIS monthly aggregation
│   ├── data_preprocessing.py          # Zonal statistics and table construction
│   ├── bpinn_model.py                 # BPINN model definition and training
│   └── evaluation.py                  # Validation metrics and conformal intervals
├── data/
│   ├── README.md                      # Data description and download instructions
│   └── sample/                        # Sample data (first 3 counties, 3 years)
└── results/
    ├── figures/                       # Generated figures
    └── tables/                        # Generated tables
```

---

## Step-by-Step Reproduction

### Step 1: Remote Sensing Data Processing (Google Earth Engine)

1. Open the [Google Earth Engine Code Editor](https://code.earthengine.google.com/).
2. Upload a Hainan boundary shapefile as a GEE asset and note its asset path.
3. Copy `scripts/modis_monthly_processing.js` into the Code Editor.
4. Replace `HAINAN_ASSET` with your own Hainan boundary asset path.
5. Adjust parameters at the top of the script if needed:
   - `START_YEAR`, `END_YEAR`: time range (default: 2010–2023)
   - `LAI_THRESHOLD`: vegetation mask threshold (default: 0.5)
   - `EXPORT_NDVI`: set to `false` to skip NDVI export
6. Click **Run**. The script will create export tasks for each month and each variable.
7. Go to the **Tasks** panel and run each export task. Outputs are saved to Google Drive in folders `LAI/`, `PRI/`, `NDVI/`, `冠层温度/`.
8. Download the GeoTIFF files from Google Drive.

**Output**: 168 months × 4 variables = 672 GeoTIFF files (or 504 if NDVI is skipped), named `YYYY_MM.tif`, in EPSG:32649 projection.

### Step 2: Soil Data Processing

1. Download HWSD2 from the FAO website.
2. Extract topsoil pH (`T_PH_H2O`) and organic matter (`T_OC`) for Hainan Island.
3. Aggregate to county-level means using zonal statistics.

### Step 3: Statistical Data Compilation

1. Download rubber area and production statistics from the Hainan Provincial Bureau of Statistics.
2. Compile into a county–year table (18 counties × 14 years = 252 records).

### Step 4: Data Integration

1. Run `scripts/data_preprocessing.py` to:
   - Extract zonal statistics from monthly remote sensing GeoTIFFs
   - Merge with soil data and statistical data
   - Construct the final analysis table (county–month: n = 3,024; county–year: n = 252)

### Step 5: Model Training and Evaluation

1. Run `scripts/bpinn_model.py` to train the BPINN with 12 independent initializations.
2. Run `scripts/evaluation.py` to compute:
   - R², RMSE, MAE, MAPE under spatial LOCO, temporal extrapolation, and spatiotemporal block validation
   - Conformal prediction intervals (PICP, MPIW, NMPIW)
   - Physical parameter approximate posteriors

---

## Key Parameters

| Parameter | Value | Description |
|---|---|---|
| Study area | 18 county-level units, Hainan Island | |
| Time period | 2010–2023 | |
| LAI vegetation threshold | ≥ 0.5 | Pixels below this are masked for canopy temperature |
| Network architecture | 2 hidden layers × 48 units, Tanh activation | |
| Dropout rate | 0.1 | MC Dropout for variational inference |
| Ensemble size | M = 12 | Independent initializations for physical parameter posteriors |
| λ_δ | 0.05 | L2 regularization on neural network residuals |
| Q10 | 2 | Temperature sensitivity of respiration (reference: 25 °C) |

---

## Limitations

1. **Within-county interannual prediction is limited**: Pooled yield-per-hectare R² is negative under all three validation schemes, indicating that the model primarily captures cross-county differences rather than within-county interannual variation.

2. **Temporal prediction intervals are wide**: NMPIW = 0.76 under temporal extrapolation, reflecting high uncertainty for unseen years.

3. **ρ–P₀ scale coupling**: Only the product ρP₀ is identifiable from yield data; individual values of ρ and P₀ depend on initialization and should not be interpreted physiologically.

4. **PRI band approximation**: MODIS lacks a narrow band at 570 nm; Band 12 (~551 nm) is used as a substitute for the classic PRI reference band.

5. **Canopy temperature is an approximation**: The "canopy temperature" variable is actually daytime land surface temperature (LST) masked to vegetated pixels (LAI ≥ 0.5), not direct leaf temperature measurement.

6. **Data availability**: Rubber production statistics are aggregated to county level; field-level measurements are not available, which limits the spatial resolution of validation.

---

## Citation

If you use this code or data, please cite:

> Chen, Q., Zhai, Y., Wang, H. (2026). Estimation of Rubber Yield in Hainan Island Using a Multi-source Remote Sensing Fusion Bayesian Approximate Physics-Informed Neural Network. *Ecological Modelling*. (under review)

---

## Contact

- **Qi Chen** — School of Mathematics and Statistics, Hainan University
- **Haohua Wang** (corresponding author) — wanghaohua@hainan.edu.cn

---

## License

This project is licensed under the MIT License — see the LICENSE file for details.
