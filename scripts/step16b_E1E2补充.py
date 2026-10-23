# -*- coding: utf-8 -*-
"""第16步补充：仅计算 E1数据长度(16c) 与 E2特征消融(16d)，避免重复训练。"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from xgboost import XGBRegressor
DATA=r"E:\海南\橡胶产量建模_结果\数据"
m=pd.read_csv(DATA+r"\05_主表_年度面板.csv")
DROP=["county","year","yield","intensity"]; XCOLS=[c for c in m.columns if c not in DROP]
ANNCOLS=["area_total","area_new","area_harvest","post_reform","ph_top","om_top"]+\
        [c for c in XCOLS if "ann_" in c]
years=m.year.values; idx=np.arange(len(m))
def Mtot(yt,yp):
    yt=np.asarray(yt,float); yp=np.asarray(yp,float); ss=((yt-yt.mean())**2).sum()
    return dict(R2=1-((yt-yp)**2).sum()/ss, RMSE=np.sqrt(((yt-yp)**2).mean()),
        MAE=np.abs(yt-yp).mean(), MAPE=np.abs((yt-yp)/yt).mean()*100)
def sk_learners():
    return {"ElasticNet":ElasticNet(alpha=.03,l1_ratio=.2,max_iter=5000),
            "XGBoost":XGBRegressor(n_estimators=400,learning_rate=.03,max_depth=4,subsample=.8,
                colsample_bytree=.8,min_child_weight=3,random_state=1,n_jobs=-1,verbosity=0)}
# E1
te=idx[years>=2021]; yte=m["yield"].values[te]
windows={"last5 (2016-20)":idx[(years>=2016)&(years<=2020)],
         "last10 (2011-20)":idx[(years>=2011)&(years<=2020)],
         "all (2010-20)":idx[years<=2020]}
rows=[]
for wn,wi in windows.items():
    Xtr=m.loc[wi,ANNCOLS].values; Xte_=m.loc[te,ANNCOLS].values; sc=StandardScaler().fit(Xtr)
    for ln,mdl in sk_learners().items():
        mdl.fit(sc.transform(Xtr),m["yield"].values[wi])
        rows.append({"window":wn,"n_train":len(wi),"learner":ln,**Mtot(yte,mdl.predict(sc.transform(Xte_)))})
pd.DataFrame(rows).to_csv(DATA+r"\16c_消融_数据长度.csv",index=False,encoding="utf-8-sig")
print("数据长度："); print(pd.DataFrame(rows).round(3).to_string(index=False))
# E2
def feat_folds(kind):
    if kind=="T": return [(idx[years<=2020],idx[years>=2021])]
    if kind=="S": return [(idx[m.county.values!=c],idx[m.county.values==c]) for c in sorted(m.county.unique())]
    return [(idx[(m.county.values!=c)&(years<=2020)],idx[(m.county.values==c)&(years>=2021)]) for c in sorted(m.county.unique())]
rows=[]
for kind,rn in [("T","Temporal hold-out"),("S","Spatial LOCO"),("ST","Spatiotemporal block")]:
    for fset,fn in [(ANNCOLS,"Annual only"),(XCOLS,"Annual + monthly phenology")]:
        pred_by={ln:[] for ln in sk_learners()}; trues=[]
        for trf,tef in feat_folds(kind):
            Xtr=m.loc[trf,fset].values; Xte_=m.loc[tef,fset].values; sc=StandardScaler().fit(Xtr)
            for ln,mdl in sk_learners().items():
                mdl.fit(sc.transform(Xtr),m["yield"].values[trf]); pred_by[ln].append(mdl.predict(sc.transform(Xte_)))
            trues.append(m["yield"].values[tef])
        T=np.concatenate(trues)
        for ln in pred_by:
            P=np.concatenate(pred_by[ln])
            rows.append({"regime":rn,"features":fn,"learner":ln,"n":len(T),**Mtot(T,P)})
pd.DataFrame(rows).to_csv(DATA+r"\16d_消融_特征.csv",index=False,encoding="utf-8-sig")
print("\n特征消融："); print(pd.DataFrame(rows).round(3).to_string(index=False))
print("完成。")
