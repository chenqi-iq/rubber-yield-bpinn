"""
Ablation study: data length ablation, feature ablation (remove remote sensing / soil / phenology), and physical module ablation.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python eval_ablation.py
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
第9步：消融实验——无歧义回答"数据量/月度特征/物理机制是否、在多大程度上提升精度"。
配置：
  C0 原5年(2019-2023)·仅年度特征 : 复现原研究时间跨度，但用诚实年度样本(不滑窗造假)
  C1 14年(2010-2023)·仅年度特征  : 只增加年份，不使用月度物候
  C2 14年·完整月度物候特征       : 再加入月度物候(=第6步特征)
  C3 C2 + 物理机制(BPINN)        : 读取第7步结果
学习者代表：ElasticNet(线性/物理可迁移) 与 XGBoost(灵活黑箱)；C3为BPINN。
Regime：时间外推 / 空间LOCO / 时空块(同前)。所有数字真实计算。

输出：09_消融实验.csv
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from xgboost import XGBRegressor

OUT=r"E:\海南\橡胶产量建模_结果\数据"
m=pd.read_csv(os.path.join(OUT,"05_主表_年度面板.csv"))
DROP=["county","year","yield","intensity"]
XCOLS=[c for c in m.columns if c not in DROP]
ANNCOL=["area_total","area_new","area_harvest","post_reform","ph_top","om_top"]+\
       [c for c in XCOLS if "ann_" in c]

def learners():
    return {"ElasticNet":ElasticNet(alpha=.03,l1_ratio=.2,max_iter=5000),
            "XGBoost":XGBRegressor(n_estimators=400,learning_rate=.03,max_depth=4,
                subsample=.8,colsample_bytree=.8,min_child_weight=3,
                random_state=1,n_jobs=-1,verbosity=0)}
def metr(yt,yp):
    yt=np.asarray(yt,float);yp=np.asarray(yp,float)
    return dict(R2=1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum(),
        RMSE=np.sqrt(((yt-yp)**2).mean()))

def eval_folds(df,cols,folds):
    # 返回 pooled 预测 by learner
    preds={ln:[] for ln in learners()}; trues=[]; order=[]
    df=df.reset_index(drop=True)
    for tr,te in folds:
        Xtr=df.loc[tr,cols].values; ytr=df.loc[tr,"yield"].values
        Xte=df.loc[te,cols].values; yte=df.loc[te,"yield"].values
        xs=StandardScaler().fit(Xtr)
        for ln,mdl in learners().items():
            mdl.fit(xs.transform(Xtr),ytr)
            preds[ln].append(mdl.predict(xs.transform(Xte)))
        trues.append(yte); order.append(te)
    out={}
    T=np.concatenate(trues)
    for ln in preds:
        P=np.concatenate(preds[ln]); out[ln]=metr(T,P)
    return out

def folds_in(df,kind):
    idx=df.index.values; years=df.year.values; counties=df.county.values
    if kind=="T":
        # 用该配置内最大可能：最后3年为测试(若不足则最后1年)
        uy=sorted(df.year.unique())
        cut=uy[-3] if len(uy)>=4 else uy[-1]
        return [(idx[years<cut],idx[years>=cut])]
    if kind=="S":
        return [(idx[counties!=c],idx[counties==c]) for c in df.county.unique()]
    if kind=="ST":
        uy=sorted(df.year.unique()); cut=uy[-3]
        return [(idx[(counties!=c)&(years<cut)],idx[(counties==c)&(years>=cut)])
                for c in df.county.unique()]

rows=[]
configs={"C0_5年仅年度":(m[m.year>=2019],ANNCOL),
         "C1_14年仅年度":(m,ANNCOL),
         "C2_14年完整":(m,XCOLS)}
for cname,(df0,cols) in configs.items():
    df=df0.reset_index(drop=True)
    for kind in ["T","S","ST"]:
        r=eval_folds(df,cols,folds_in(df,kind))
        for ln,mt in r.items():
            rows.append({"config":cname,"learner":ln,"regime":kind,**mt})
# C3 BPINN 从第7步
p7=pd.read_csv(os.path.join(OUT,"07_PINN各regime指标.csv"))
mapr={"S_LOCO":"S","T_EndHoldout":"T","ST_Blocked":"ST"}
for _,r in p7.iterrows():
    if r.regime in mapr:
        rows.append({"config":"C3_完整+物理BPINN","learner":"BPINN",
            "regime":mapr[r.regime],"R2":r.R2,"RMSE":r.RMSE})
res=pd.DataFrame(rows)
res.to_csv(os.path.join(OUT,"09_消融实验.csv"),index=False,encoding="utf-8-sig")
pd.set_option("display.width",200)
for kind in ["T","S","ST"]:
    print("\n=== Regime",kind,"===")
    print(res[res.regime==kind].round(3).to_string(index=False))
print("完成。")
