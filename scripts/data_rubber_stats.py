"""
Extract and clean rubber area/production statistics from Hainan Bureau of Statistics Excel file.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python data_rubber_stats.py
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
第1步：从《海南省各市县主要热带作物面积和产量》(实为含15个年度文件的文件夹)
提取海南岛18个市县橡胶(年末面积/当年新种/收获面积/总产量)的年度面板。

关键事实(已通过"市县合计与各年全省合计比对"无歧义验证)：
  * 出版年 P 的文件，其市县分块对应"数据年 = P-1"；15个文件(出版2010-2024)覆盖数据年 2009-2023。
  * 因此源数据中【没有2024年实际数据】——本流程不编造2024，只输出真实存在的2009-2023。
  * 2009、2010两年橡胶分"18市县(地方)+农垦"两块；2011年起农垦并入市县(海南农垦统计口径改革)。
  * 2013-2019的.xls为默认保护密码(VelvetSweatshop)加密，用msoffcrypto解密读取。

输出(数据目录)：
  01a_橡胶原始面板_含农垦.csv   —— 忠实于原始文件(2009/2010含"农垦"行)
  01b_橡胶18市县面板_农垦已分摊.csv —— 用"2010→2011增量法"把农垦分摊回18市县(2010年)，口径统一
  01_农垦分摊权重.csv           —— 农垦→市县的分摊权重，便于核查
"""
import os, io, sys
import numpy as np, pandas as pd

BASE = r"E:\海南\海南省各市县主要热带作物面积和产量.xls"
OUT  = r"E:\海南\橡胶产量建模_结果\数据"
os.makedirs(OUT, exist_ok=True)

# 18市县标准短名(与遥感/土壤统一)
CANON = ["海口市","三亚市","儋州市","五指山市","文昌市","琼海市","万宁市","定安县",
         "屯昌县","澄迈县","临高县","东方市","乐东县","琼中县","保亭县","陵水县",
         "白沙县","昌江县"]

def _num(v):
    try:
        if v is None or (isinstance(v,str) and v.strip()==""):
            return np.nan
        x=float(v); return x
    except Exception:
        return np.nan

def _norm_name(s):
    s=str(s).replace(" ","").replace("\u3000","")
    return s

def get_all_rows(p):
    """读取文件，返回整张表的原始二维表(不做作物区块切分)。"""
    if p.lower().endswith(".xlsx"):
        import openpyxl
        wb=openpyxl.load_workbook(p,data_only=True); sh=wb[wb.sheetnames[0]]
        rows=[[c for c in row] for row in sh.iter_rows(values_only=True)]
    else:
        import xlrd, msoffcrypto
        try:
            wb=xlrd.open_workbook(p); sh=wb.sheet_by_index(0)
        except xlrd.biffh.XLRDError:
            with open(p,"rb") as f:
                of=msoffcrypto.OfficeFile(f); of.load_key(password="VelvetSweatshop")
                buf=io.BytesIO(); of.decrypt(buf); buf.seek(0)
            wb=xlrd.open_workbook(file_contents=buf.read()); sh=wb.sheet_by_index(0)
        rows=[[sh.cell_value(r,c) for c in range(sh.ncols)] for r in range(sh.nrows)]
    return rows

def parse_file(p, data_year):
    rows=get_all_rows(p)
    aliases = CANON + ["农垦","洋浦","儋州地区"]
    def match_region(v0):
        for a in aliases:
            if v0==a or v0.startswith(a): return a
        return None
    cand=[]
    for i,row in enumerate(rows):
        v0=_norm_name(row[0]) if row and row[0] is not None else ""
        if not v0 or v0[:4].isdigit(): continue
        m=match_region(v0)
        if m is None: continue
        cand.append((i,{"unit":m,"area_total":_num(row[2]),"area_new":_num(row[3]),
                        "area_harvest":_num(row[4]),"yield":_num(row[5])}))
    # 第一组连续市县行 = 橡胶(允许<=2行空行间隔)
    cluster=[]; last=None
    for i,rec in cand:
        if last is None or i-last<=2:
            cluster.append(rec); last=i
        else:
            break
    df=pd.DataFrame(cluster)
    if df.empty: return df
    # 处理儋州地区/儋州市/洋浦嵌套
    names=set(df["unit"])
    if "儋州市" in names:
        df=df[df["unit"]!="儋州地区"]
    elif "儋州地区" in names:
        df.loc[df["unit"]=="儋州地区","unit"]="儋州市"
    df=df[df["unit"]!="洋浦"]
    df["year"]=data_year
    return df

# ---- 主循环：文件出版年 P -> 数据年 P-1 ----
frames=[]
for fn in sorted(os.listdir(BASE)):
    p=os.path.join(BASE,fn)
    if not os.path.isfile(p): continue
    P=int(fn[:4]); data_year=P-1
    df=parse_file(p,data_year)
    frames.append(df)
    units=df["unit"].tolist()
    print("出版%d/数据%d: %d 行, 农垦=%s"%(P,data_year,len(df),"农垦" in units))

raw=pd.concat(frames,ignore_index=True)
raw=raw[["year","unit","area_total","area_new","area_harvest","yield"]]
raw.to_csv(os.path.join(OUT,"01a_橡胶原始面板_含农垦.csv"),index=False,encoding="utf-8-sig")
print("\n原始面板行数:",len(raw),"年份:",sorted(raw.year.unique()))

# ---- 农垦分摊(增量法)：以2010(地方)→2011(并垦)各县增量占比作为农垦地理分布权重 ----
def wide_measure(col):
    d=raw[raw["unit"].isin(CANON)].pivot_table(index="unit",columns="year",values=col)
    return d

w_tot = wide_measure("area_total")
# 县均有2010、2011
inc = (w_tot[2011]-w_tot[2010]).clip(lower=0)
weights = inc/inc.sum()
weights_df=pd.DataFrame({"county":weights.index,"weight":weights.values})
weights_df.to_csv(os.path.join(OUT,"01_农垦分摊权重.csv"),index=False,encoding="utf-8-sig")
print("\n农垦分摊权重(前5):"); print(weights_df.head().to_string(index=False))

# 对需要分摊的年份(2009,2010)，把农垦各指标按权重加到18市县
harm = raw[raw["unit"].isin(CANON)].copy().reset_index(drop=True)
wmap = dict(zip(weights.index, weights.values))
farm = raw[raw["unit"]=="农垦"].set_index("year")
for y in sorted(farm.index):
    sub = harm["year"]==y
    for col in ["area_total","area_new","area_harvest","yield"]:
        fv=farm.loc[y,col]
        if pd.isna(fv): continue
        add = harm.loc[sub,"unit"].map(lambda u: wmap.get(u,0.0))*fv
        harm.loc[sub,col] = harm.loc[sub,col].values + add.values
harm=harm.sort_values(["year","unit"]).reset_index(drop=True)
harm=harm[["year","unit","area_total","area_new","area_harvest","yield"]]
harm.to_csv(os.path.join(OUT,"01b_橡胶18市县面板_农垦已分摊.csv"),index=False,encoding="utf-8-sig")

# 校验：分摊后全省合计应≈原始(地方+农垦)合计
chk=harm.groupby("year")["area_total"].sum().round(0)
orig_tot=raw.groupby("year")["area_total"].sum().round(0)
print("\n校验 年末面积合计 (分摊后 vs 原始):")
for y in chk.index:
    print("  %d: %.0f vs %.0f  差%.1f"%(y,chk[y],orig_tot[y],chk[y]-orig_tot[y]))
print("\n完成。输出目录:",OUT)
