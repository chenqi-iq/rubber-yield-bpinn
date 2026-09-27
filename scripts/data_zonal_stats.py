"""
Compute monthly zonal statistics (LAI, NDVI, PRI, canopy temperature) from GeoTIFFs using Hainan county boundaries.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python data_zonal_stats.py
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
第3步：提取海南岛18市县 2010-2023 年 LAI/NDVI/PRI/冠层温度 的月度分区均值。
        共 4 变量 × 14 年 × 12 月 = 672 个 GeoTIFF；结果 4×14×12×18 = 12096 行。

效率与正确性：
  * 每个变量的所有月份栅格几何一致(已核对)，故市县多边形只栅格化一次并复用；
  * 按市县bbox窗口读取(不读整张全球/大区背景)，用 np.bincount 一次算18市县的和与计数；
  * 记录每个市县-年-月有效像元数 n_pixel，便于识别整月缺失/云污染(后续科学插补依据)；
  * 数值已是物理单位(LAI m²/m²；NDVI/PRI 指数；冠层温度 ℃)，nodata=-9999，不做任何缩放。

输出：03_遥感月度面板_long.csv (county,year,month,variable,value,n_pixel)
"""
import os
import numpy as np, pandas as pd, geopandas as gpd
import rasterio
from rasterio.windows import Window
from rasterio.warp import transform_bounds
from rasterio.features import rasterize

OUT = r"E:\海南\橡胶产量建模_结果\数据"
SHP = r"E:\海南\海南省县边界数据\海南省_县2.shp"
os.makedirs(OUT, exist_ok=True)

CANON = ["海口市","三亚市","儋州市","五指山市","文昌市","琼海市","万宁市","定安县",
         "屯昌县","澄迈县","临高县","东方市","乐东县","琼中县","保亭县","陵水县",
         "白沙县","昌江县"]
FULL2SHORT = {"琼中黎族苗族自治县":"琼中县","保亭黎族苗族自治县":"保亭县",
              "陵水黎族自治县":"陵水县","乐东黎族自治县":"乐东县",
              "昌江黎族自治县":"昌江县","白沙黎族自治县":"白沙县",
              "龙华区":"海口市","秀英区":"海口市","美兰区":"海口市","琼山区":"海口市",
              "吉阳区":"三亚市","海棠区":"三亚市","天涯区":"三亚市","崖州区":"三亚市"}
VARS = {"LAI":r"E:\海南\LAI","NDVI":r"E:\海南\NDVI",
        "PRI":r"E:\海南\PRI","Canopy":r"E:\海南\冠层温度"}

# 18市县多边形(4326)
g=gpd.read_file(SHP)
g["name"]=g["name"].apply(lambda s:s.encode("latin-1").decode("utf-8"))
g=g[~g["name"].isin(["南沙区","西沙区"])].copy()
g["county"]=g["name"].replace(FULL2SHORT)
counties=g.dissolve(by="county").reindex(CANON)
assert counties.index.tolist()==CANON

def build_county_grid(ds):
    """在该栅格CRS下，按市县bbox窗口栅格化18市县，返回 cid窗口网格, 窗口, 变换。"""
    dst_crs=ds.crs
    cnt=counties.to_crs(dst_crs)
    minx,miny,maxx,maxy=cnt.total_bounds
    # 用栅格自身方法把边界转成窗口
    win=ds.window(minx,miny,maxx,maxy).round_offsets().round_lengths()
    # 略微外扩1像元
    win=Window(win.col_off-1,win.row_off-1,win.width+2,win.height+2)
    wt=ds.window_transform(win)
    H,W=int(win.height),int(win.width)
    shapes=[(geom,i+1) for i,geom in enumerate(cnt.geometry)]
    cid=rasterize(shapes,out_shape=(H,W),transform=wt,fill=0,dtype="uint8")
    return cid,win

records=[]
for vname,vroot in VARS.items():
    files=[]
    for y in range(2010,2024):
        for m in range(1,13):
            f=os.path.join(vroot,f"{y}年",f"{y}_{m:02d}.tif")
            files.append((y,m,f))
    with rasterio.open(files[0][2]) as ds0:
        cid,win=build_county_grid(ds0)
        base_trans=ds0.window_transform(win)
    flat_cid=cid.ravel()
    cmax=flat_cid.max()
    print(f"[{vname}] 窗口网格 {cid.shape}, 市县像元 {int((cid>0).sum())}, 文件 {len(files)}")
    for k,(y,m,f) in enumerate(files):
        with rasterio.open(f) as ds:
            arr=ds.read(1,window=win,boundless=True,fill_value=-9999)
            nod=ds.nodata if ds.nodata is not None else -9999
        a=arr.astype("float64").ravel()
        valid=(flat_cid>0)&(a!=nod)&np.isfinite(a)
        cids=flat_cid[valid]; aa=a[valid]
        sums=np.bincount(cids,weights=aa,minlength=19)
        cnts=np.bincount(cids,minlength=19)
        for i,cn in enumerate(CANON):
            cidv=i+1
            if cnts[cidv]>0:
                records.append((cn,y,m,vname,sums[cidv]/cnts[cidv],int(cnts[cidv])))
            else:
                records.append((cn,y,m,vname,np.nan,0))
        if (k+1)%48==0: print(f"   {vname} 已处理 {k+1}/{len(files)}")

rs=pd.DataFrame(records,columns=["county","year","month","variable","value","n_pixel"])
rs.to_csv(os.path.join(OUT,"03_遥感月度面板_long.csv"),index=False,encoding="utf-8-sig")
print("\n总行数:",len(rs))
print("缺失(整月无像元)统计:")
print(rs[rs.n_pixel==0].groupby("variable").size())
print(rs.groupby("variable")["value"].agg(["count","min","mean","max"]).round(3))
print("完成。")
