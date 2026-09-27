"""
Merge rubber stats, soil data, remote sensing features, and phenological features into the final analysis table (county-year and county-month).

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python data_merge_table.py
"""

import os

# ============================================================
# CONFIG: Change this to your local data root directory
# ============================================================
DATA_ROOT = r"E:\海南"

# Derived paths (all scripts use these)
REMOTE_SENSING_DIR = os.path.join(DATA_ROOT)
SHAPEFILE_PATH = os.path.join(DATA_ROOT, "海南省县边界数据", "海南省_县2.shp")
RUBBER_STATS_PATH = os.path.join(DATA_ROOT, "海南省各市县主要热带作物面积和产量.xls")
HWSD2_DIR = os.path.join(DATA_ROOT, "output", "hwssd2")
OUTPUT_DIR = os.path.join(DATA_ROOT, "橡胶产量建模_结果", "数据")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===== Original script below =====

# -*- coding: utf-8 -*-
"""
第5步：合并为"一张大表"。
  主表(年度, 建模用)：18市县×14年(2010-2023)=252行
        = 橡胶(面积/产量) + 土壤(PH/有机质,静态) + 39个年度物候特征
  月度长面板(备查)：12096行，4个遥感变量为列 + 静态土壤；并附当年橡胶(年度值,仅参照)。

说明：
  * 橡胶采用农垦已分摊的统一口径(01b)；目标同时保留总产量 yield 与单产 intensity(t/ha)。
  * 2024年橡胶在源数据中不存在，主表止于2023，不做任何外推/编造。
输出：05_主表_年度面板.csv；05b_主表_月度长面板.csv
"""
import os
import numpy as np, pandas as pd

OUT=r"E:\海南\橡胶产量建模_结果\数据"

rub=pd.read_csv(os.path.join(OUT,"01b_橡胶18市县面板_农垦已分摊.csv"))
rub=rub.rename(columns={"unit":"county"})
# 当年新种空白：2014年后海南橡胶扩种基本停止(统计上空白=无新种记录)，据实填0
n_fill=int(rub["area_new"].isna().sum())
rub["area_new"]=rub["area_new"].fillna(0)
print("area_new 空白填0(无新种记录):",n_fill,"处")
rub["intensity"]=rub["yield"]/rub["area_harvest"]
rub["post_reform"]=(rub["year"]>=2011).astype(int)

soil=pd.read_csv(os.path.join(OUT,"02_市县土壤PH有机质.csv"))
soil=soil.rename(columns={"county":"county"})

feat=pd.read_csv(os.path.join(OUT,"04_年度物候特征.csv"))

# 年度主表
m=feat.merge(rub,on=["county","year"],how="inner")
m=m.merge(soil,on="county",how="left")

front=["county","year",
       "area_total","area_new","area_harvest","yield","intensity","post_reform",
       "ph_top","ph_root","om_top","om_root","oc_top","oc_root","bulk_top","n_pixel"]
rest=[c for c in m.columns if c not in front]
m=m[front+rest]
m=m.sort_values(["county","year"]).reset_index(drop=True)
m.to_csv(os.path.join(OUT,"05_主表_年度面板.csv"),index=False,encoding="utf-8-sig")
print("年度主表:",m.shape)
print("缺失值合计:",int(m.isna().sum().sum()))

# 月度长面板（遥感宽表 + 土壤 + 当年橡胶参照）
mon=pd.read_csv(os.path.join(OUT,"03_遥感月度面板_long.csv"))
monw=mon.pivot_table(index=["county","year","month"],columns="variable",values="value").reset_index()
monw=monw.merge(soil[["county","ph_top","om_top"]],on="county",how="left")
monw=monw.merge(rub[["county","year","yield","intensity","area_harvest"]],on=["county","year"],how="left")
monw=monw.sort_values(["county","year","month"]).reset_index(drop=True)
monw.to_csv(os.path.join(OUT,"05b_主表_月度长面板.csv"),index=False,encoding="utf-8-sig")
print("月度长面板:",monw.shape)
print("\n主表列:",list(m.columns))
print("完成。")
