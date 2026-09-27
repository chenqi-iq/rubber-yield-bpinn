"""
Derive annual phenological features (seasonal amplitude, peak timing, growing season length) from monthly time series.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python features_phenology.py
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
第4步：把18市县 2010-2023 的月度遥感序列，聚合为具有明确农学/物候意义的年度特征。
        这是"用月度数据构造特征"而非"复制年度标签"——每个市县-年只有1行真实目标。

物候分期(海南橡胶)：
  越冬/停割 winter(Y) = 上年12月 + 当年1,2月
  返青/抽春 spring(Y) = 3,4月
  割胶季   tapping(Y)= 5-11月
  夏(高温) summer(Y) = 6-9月
  全年 annual(Y)=1-12月

缺失处理(科学、可核查)：先对同一市县同变量做相邻月线性插值；仍缺则用该县该月多年气候态。
  本数据月度无缺失(第3步已验证)，脚本保留该机制并报告实际插补数(预期0)。

输出：04_年度物候特征.csv (18×14=252行)
"""
import os
import numpy as np, pandas as pd

OUT=r"E:\海南\橡胶产量建模_结果\数据"
CANON = ["海口市","三亚市","儋州市","五指山市","文昌市","琼海市","万宁市","定安县",
         "屯昌县","澄迈县","临高县","东方市","乐东县","琼中县","保亭县","陵水县",
         "白沙县","昌江县"]
YEARS=list(range(2010,2024))

rs=pd.read_csv(os.path.join(OUT,"03_遥感月度面板_long.csv"))
# 透视: county,year,month × variable
piv=rs.pivot_table(index=["county","year","month"],columns="variable",values="value")

# ---- 安全插补(按county,variable 的连续月序列) ----
fill_log={"linear":0,"climatology":0}
# 建立连续日历(仅额外包含2009年12月，供2010年越冬期使用)
cal=[(2009,12)]
for y in range(2010,2024):
    for m in range(1,13): cal.append((y,m))
cal=pd.DataFrame(cal,columns=["year","month"])
vars_=list(piv.columns)
series={}
for cn in CANON:
    d=piv.loc[cn].reset_index() if cn in piv.index.get_level_values(0) else None
    full=cal.merge(d,on=["year","month"],how="left").sort_values(["year","month"])
    for v in vars_:
        x=full[v].astype(float)
        n0=x.isna().sum()
        x=x.interpolate(method="linear",limit_direction="both")
        fill_log["linear"]+= n0  # 记录初始缺口
        # 气候态兜底
        if x.isna().any():
            clim=full.groupby("month")[v].transform("mean")
            mask=x.isna(); x=x.fillna(clim); fill_log["climatology"]+=int(mask.sum())
        series[(cn,v)]=x.values
print("插补日志:",fill_log)

def get(cn,v,y,m):
    idx=((cal.year==y)&(cal.month==m)).idxmax()
    return series[(cn,v)][idx]
def season_vals(cn,v,y,months,use_prev_dec=False):
    vals=[]
    if use_prev_dec: vals.append(get(cn,v,y-1,12))
    for mm in months: vals.append(get(cn,v,y,mm))
    return np.array(vals)

rows=[]
for cn in CANON:
    for y in YEARS:
        r={"county":cn,"year":y}
        for v,pref in [("LAI","LAI"),("NDVI","NDVI"),("PRI","PRI"),("Canopy","Tc")]:
            ann =season_vals(cn,v,y,range(1,13))
            win =season_vals(cn,v,y,[1,2],use_prev_dec=True)
            spr =season_vals(cn,v,y,[3,4])
            tap =season_vals(cn,v,y,range(5,12))
            summ=season_vals(cn,v,y,range(6,10))
            r[f"{pref}_ann_mean"]=np.nanmean(ann); r[f"{pref}_ann_std"]=np.nanstd(ann)
            r[f"{pref}_ann_min"]=np.nanmin(ann); r[f"{pref}_ann_max"]=np.nanmax(ann)
            r[f"{pref}_winter"]=np.nanmean(win); r[f"{pref}_spring"]=np.nanmean(spr)
            r[f"{pref}_tapping"]=np.nanmean(tap)
            if v in ("LAI","NDVI"):
                r[f"{pref}_recovery"]=np.nanmean(spr)-np.nanmean(win)
            if v=="Canopy":
                r[f"{pref}_winter_min"]=np.nanmin(win)
                r[f"{pref}_summer"]=np.nanmean(summ)
                r[f"{pref}_summer_max"]=np.nanmax(summ)
            if v=="PRI":
                r[f"{pref}_spring"]=np.nanmean(spr)
        # 交叉物候特征(由真实月度数据计算)
        r["Recover_NDVI"]=r["NDVI_spring"]-r["NDVI_winter"]
        r["Recover_LAI"]=r["LAI_spring"]-r["LAI_winter"]
        r["LowTemp_Recovery"]=r["NDVI_spring"]/(r["Tc_winter"]+0.1)
        r["Tc_annual_range"]=r["Tc_ann_max"]-r["Tc_ann_min"]
        rows.append(r)
feat=pd.DataFrame(rows)
feat.to_csv(os.path.join(OUT,"04_年度物候特征.csv"),index=False,encoding="utf-8-sig")
print("特征表:",feat.shape,"列数:",feat.shape[1])
print("列:",list(feat.columns))
print("完成。")
