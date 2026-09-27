"""
Train and evaluate baseline models (ElasticNet, KNN, SVR, RandomForest, XGBoost, persistence, climatology) under three validation regimes.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python model_baselines.py
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
第6步：基线模型在三种"无泄漏"验证regime下评估(目标=橡胶总产量, 吨)。
  Regime S 空间LOCO   ：18折，每次 hold 出1个市县的【全部年份】，17市县训练。
  Regime T 时间外推   ：训练年<=2020，测试2021-2023(多年未来hindcast)；并做2016-2023逐年滚动1年提前。
  Regime ST 时空块    ：18折，训练=17市县且年<=2020，测试=被hold市县的2021-2023(最严格)。
关键：所有标准化器只在训练折拟合；重叠窗口不跨折；市县-年为最小组，杜绝原方法的泄漏/伪重复。
预报基准：气候态(该县训练年均值)/持续性(上一年)，用于判断模型是否真有预报技巧。

输出：06_模型对比_各regime.csv；06_基线预测明细.csv
"""
import os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

OUT=r"E:\海南\橡胶产量建模_结果\数据"
SEED=42
m=pd.read_csv(os.path.join(OUT,"05_主表_年度面板.csv"))

DROP=["county","year","yield","intensity"]
XCOLS=[c for c in m.columns if c not in DROP]
print("特征数:",len(XCOLS))

def make_models():
    return {
      "ElasticNet":ElasticNet(alpha=0.03,l1_ratio=0.2,max_iter=5000),
      "KNN":KNeighborsRegressor(n_neighbors=7,weights="distance"),
      "SVR":SVR(C=10,gamma="scale",epsilon=0.05),
      "RandomForest":RandomForestRegressor(n_estimators=500,max_depth=12,
                       min_samples_leaf=2,random_state=SEED,n_jobs=-1),
      "XGBoost":XGBRegressor(n_estimators=400,learning_rate=0.03,max_depth=4,
                       subsample=0.8,colsample_bytree=0.8,min_child_weight=3,
                       random_state=SEED,n_jobs=-1,verbosity=0),
      "LightGBM":LGBMRegressor(n_estimators=400,learning_rate=0.03,num_leaves=31,
                       min_child_samples=5,reg_lambda=1.0,random_state=SEED,
                       n_jobs=-1,verbose=-1),
    }

def metrics(yt,yp):
    yt=np.asarray(yt,float); yp=np.asarray(yp,float)
    r2=1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum()
    rmse=np.sqrt(((yt-yp)**2).mean()); mae=np.abs(yt-yp).mean()
    mape=(np.abs((yt-yp)/yt).mean())*100
    return dict(R2=r2,RMSE=rmse,MAE=mae,MAPE=mape)

def fit_predict(train_idx,test_idx):
    Xtr=m.loc[train_idx,XCOLS].values; ytr=m.loc[train_idx,"yield"].values
    Xte=m.loc[test_idx,XCOLS].values;  yte=m.loc[test_idx,"yield"].values
    xs=StandardScaler().fit(Xtr); ys=StandardScaler().fit(ytr.reshape(-1,1))
    Xtr_s=xs.transform(Xtr); Xte_s=xs.transform(Xte)
    ytr_s=ys.transform(ytr.reshape(-1,1)).ravel()
    preds={}
    for name,mdl in make_models().items():
        mdl.fit(Xtr_s,ytr_s)
        preds[name]=ys.inverse_transform(mdl.predict(Xte_s).reshape(-1,1)).ravel()
    # 气候态 & 持续性基准
    tr_df=m.loc[train_idx]
    clim=m.loc[test_idx,"county"].map(tr_df.groupby("county")["yield"].mean())
    preds["Climatology"]=clim.fillna(tr_df["yield"].mean()).values
    # 持续性：取该县在训练中的最后一年
    last=tr_df.sort_values("year").groupby("county")["yield"].last()
    preds["Persistence"]=m.loc[test_idx,"county"].map(last).fillna(tr_df["yield"].mean()).values
    return yte,preds,test_idx

rows=[]; detail=[]
def collect(regime,test_idx,yte,preds):
    for name,p in preds.items():
        mt=metrics(yte,p); mt.update(model=name,regime=regime); rows.append(mt)
    info=m.loc[test_idx,["county","year"]].copy()
    info["true"]=yte; info["regime"]=regime
    for name,p in preds.items():
        info[name]=p
    detail.append(info)

idx=m.index.values
# --- Regime S: LOCO ---
for c in m.county.unique():
    te=idx[m.county.values==c]; tr=idx[m.county.values!=c]
    yte,preds,_=fit_predict(tr,te); collect("S_LOCO",te,yte,preds)
# --- Regime T: end holdout ---
tr=idx[m.year.values<=2020]; te=idx[m.year.values>=2021]
yte,preds,_=fit_predict(tr,te); collect("T_EndHoldout",te,yte,preds)
# --- Regime T: rolling 1-year ahead ---
for ty in range(2016,2024):
    tr=idx[m.year.values<ty]; te=idx[m.year.values==ty]
    yte,preds,_=fit_predict(tr,te); collect("T_Rolling1y",te,yte,preds)
# --- Regime ST: blocked ---
for c in m.county.unique():
    tr=idx[(m.county.values!=c)&(m.year.values<=2020)]
    te=idx[(m.county.values==c)&(m.year.values>=2021)]
    yte,preds,_=fit_predict(tr,te); collect("ST_Blocked",te,yte,preds)

res=pd.DataFrame(rows)[["regime","model","R2","RMSE","MAE","MAPE"]]
# 对多折regime合并指标(已在collect按折记录，这里按regime+model聚合需重算：改为平均会失真，
# 故对S/ST/T_Rolling用明细重算整体指标)
det=pd.concat(detail,ignore_index=True)
def pooled(g,model):
    return metrics(g["true"],g[model])
regimes=det.regime.unique(); models=[c for c in det.columns if c not in
        ["county","year","true","regime"]]
out=[]
for rg in regimes:
    g=det[det.regime==rg]
    for mm in models:
        mt=pooled(g,mm); mt.update(regime=rg,model=mm); out.append(mt)
res=pd.DataFrame(out)[["regime","model","R2","RMSE","MAE","MAPE"]]
res.to_csv(os.path.join(OUT,"06_模型对比_各regime.csv"),index=False,encoding="utf-8-sig")
det.to_csv(os.path.join(OUT,"06_基线预测明细.csv"),index=False,encoding="utf-8-sig")
pd.set_option("display.width",200)
for rg in ["S_LOCO","T_EndHoldout","T_Rolling1y","ST_Blocked"]:
    print("\n===",rg,"===")
    print(res[res.regime==rg].sort_values("R2",ascending=False).round(3).to_string(index=False))
print("\n完成。")
