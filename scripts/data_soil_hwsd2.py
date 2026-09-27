"""
Extract topsoil pH and organic matter from HWSD2, aggregate to county-level means using zonal statistics.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python data_soil_hwsd2.py
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
第2步：从 HWSD2(全球30弧秒土壤制图单元栅格 + Access属性库)提取海南岛18市县的
        土壤 pH(PH_WATER) 与 有机质(ORG_CARBON×1.724)。

方法(可核查、不造假)：
  1) 将18市县(海口/三亚由区级合并)多边形栅格化到HWSD2海南窗口；
  2) 逐市县取像元的制图单元ID(HWSD2_SMU_ID)，以像元真实面积权重 cos(lat) 加权；
  3) 连接 HWSD2_LAYERS：同一SMU内按组分 SHARE% 加权、按土层厚度加权，
     分别计算 0-20cm 表土 与 0-100cm 根区 的 PH_WATER、ORG_CARBON；
  4) 有机质% = 有机碳% × 1.724 (van Bemmelen 转换系数)；
  5) 市县值 = 各SMU值按像元面积加权平均。pH按HWSD惯例做算术平均。

输出：02_市县土壤PH有机质.csv；并缓存SMU→土壤属性中间表。
"""
import os, io
import numpy as np, pandas as pd, geopandas as gpd
import rasterio
from rasterio.windows import Window
from rasterio.features import rasterize
import pyodbc

BIL = r"E:\海南\output\hwssd2\HWSD2.bil"
MDB = r"E:\海南\output\hwssd2\HWSD2.mdb"
SHP = r"E:\海南\海南省县边界数据\海南省_县2.shp"
OUT = r"E:\海南\橡胶产量建模_结果\数据"
os.makedirs(OUT, exist_ok=True)
DX = 1/120.0  # 0.0083333

CANON = ["海口市","三亚市","儋州市","五指山市","文昌市","琼海市","万宁市","定安县",
         "屯昌县","澄迈县","临高县","东方市","乐东县","琼中县","保亭县","陵水县",
         "白沙县","昌江县"]
# 自治县全名 -> 短名
FULL2SHORT = {"琼中黎族苗族自治县":"琼中县","保亭黎族苗族自治县":"保亭县",
              "陵水黎族自治县":"陵水县","乐东黎族自治县":"乐东县",
              "昌江黎族自治县":"昌江县","白沙黎族自治县":"白沙县",
              # 海口市辖区
              "龙华区":"海口市","秀英区":"海口市","美兰区":"海口市","琼山区":"海口市",
              # 三亚市辖区
              "吉阳区":"三亚市","海棠区":"三亚市","天涯区":"三亚市","崖州区":"三亚市"}

# ---------- 1) 18市县多边形 ----------
gdf = gpd.read_file(SHP)  # 默认按latin-1读，实为utf-8
gdf["name"] = gdf["name"].apply(lambda s: s.encode("latin-1").decode("utf-8"))
gdf = gdf[~gdf["name"].isin(["南沙区","西沙区"])].copy()
gdf["county"] = gdf["name"].replace(FULL2SHORT)
# 海口/三亚各区 dissolve 到市
counties = gdf.dissolve(by="county", as_index=False)
counties = counties.set_index("county").reindex(CANON).reset_index()
assert counties["county"].tolist()==CANON
print("市县数:",len(counties))

# ---------- 2) HWSD2 海南窗口 ----------
lon0,lon1,lat0,lat1=108.5,118.0,18.0,20.3
c0=int((lon0+180)/DX)-1; c1=int((lon1+180)/DX)+1
r0=int((90-lat1)/DX)-1; r1=int((90-lat0)/DX)+1
win=Window(c0,r0,c1-c0,r1-r0)
with rasterio.open(BIL) as ds:
    mu = ds.read(1,window=win)
    wt = ds.window_transform(win)
H,Wn = mu.shape
# 市县id栅格(1..18)
shapes=[(geom,i+1) for i,geom in enumerate(counties.geometry)]
cg = rasterize(shapes, out_shape=(H,Wn), transform=wt, fill=0, dtype="uint8")
# 每像元纬度 & 面积权重
rows_idx=np.arange(H)
lat_of_row = 90-(r0+rows_idx+0.5)*DX
coslat = np.cos(np.deg2rad(lat_of_row))[:,None]*np.ones((1,Wn))
print("窗口:",mu.shape,"有效市县像元:",int((cg>0).sum()))

# ---------- 3) 读取属性库，计算SMU层/组分加权 ----------
conn=pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;"%MDB)
lay=pd.read_sql("SELECT HWSD2_SMU_ID,SEQUENCE,SHARE,LAYER,TOPDEP,BOTDEP,"
                "ORG_CARBON,PH_WATER,BULK FROM HWSD2_LAYERS", conn)
conn.close()
lay=lay.rename(columns={"HWSD2_SMU_ID":"smu"})
lay["share"]=pd.to_numeric(lay["SHARE"],errors="coerce").fillna(100)
for c in ["TOPDEP","BOTDEP"]:
    lay[c]=pd.to_numeric(lay[c],errors="coerce")

def smu_aggregate(df, depth_lo, depth_hi):
    """按组分share与目标深度内土层厚度加权，返回 pH, 有机碳%, 容重。"""
    tlo=np.maximum(df["TOPDEP"],depth_lo); thi=np.minimum(df["BOTDEP"],depth_hi)
    thick=(thi-tlo).clip(lower=0)
    w=df["share"]*thick
    out={}
    for col,label in [("PH_WATER","ph"),("ORG_CARBON","oc"),("BULK","bulk")]:
        x=pd.to_numeric(df[col],errors="coerce")
        m=x.notna()&(w>0)
        out[label]=(x[m]*w[m]).sum()/w[m].sum() if m.any() else np.nan
    return out

smu_ids=np.unique(mu[(cg>0)&(mu!=65535)])
recs=[]
for s in smu_ids:
    d=lay[lay["smu"]==s]
    if d.empty: continue
    top=smu_aggregate(d,0,20); root=smu_aggregate(d,0,100)
    recs.append({"smu":s,
        "ph_top":top["ph"],"ph_root":root["ph"],
        "oc_top":top["oc"],"oc_root":root["oc"],
        "om_top":top["oc"]*1.724,"om_root":root["oc"]*1.724,
        "bulk_top":top["bulk"]})
smu_df=pd.DataFrame(recs)
smu_df.to_csv(os.path.join(OUT,"02_SMU土壤属性中间表.csv"),index=False,encoding="utf-8-sig")
print("有效SMU:",len(smu_df))
smu_map=smu_df.set_index("smu")

# ---------- 4) 逐市县按像元面积加权 ----------
out=[]
for i,cn in enumerate(CANON):
    m=(cg==i+1)&(mu!=65535)
    ids=mu[m]; wgt=coslat[m]
    row={"county":cn,"n_pixel":int(m.sum())}
    for col in ["ph_top","ph_root","oc_top","oc_root","om_top","om_root","bulk_top"]:
        vals=smu_map[col].reindex(ids).values
        ok=~np.isnan(vals)
        row[col]=(vals[ok]*wgt[ok]).sum()/wgt[ok].sum() if ok.any() else np.nan
    out.append(row)
soil=pd.DataFrame(out)
soil.to_csv(os.path.join(OUT,"02_市县土壤PH有机质.csv"),index=False,encoding="utf-8-sig")
print(soil[["county","ph_top","ph_root","om_top","om_root","n_pixel"]].round(3).to_string(index=False))
print("\n完成。")
