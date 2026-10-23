# -*- coding: utf-8 -*-
"""
第17步：统计补强（真实计算；修复P0统计项）。
 (1) 鲁棒性按【市县】配对(n=18)：每市县测试年(2021-23)平均绝对误差 clean vs 噪声(B=80均值)，
     配对t、Cohen dz，并以配对差自助(bootstrap 2000次)给dz的95%CI。
 (2) 逐市县R2(空间，每县14年, 来自16f) 与 逐年R2(每年18县, 来自16b空间) 的分布(中位/IQR/极差)。
 (3) 表6：RMSE变化% 同时给均值与SD(来自08)。
输出：17a_市县配对鲁棒性.csv；17b_逐市县R2.csv；17c_逐年R2.csv；17d_鲁棒性均值SD.csv；
      17e_配对dz的CI汇总.csv
"""
import os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, torch
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
DATA=r"E:\海南\橡胶产量建模_结果\数据"; B=80; KS=[.01,.05,.10]
m=pd.read_csv(DATA+r"\05_主表_年度面板.csv")
c8=pd.read_csv(DATA+r"\08_噪声鲁棒性_MC.csv")
sp=pd.read_csv(DATA+r"\16f_空间逐市县预测.csv")
conf=pd.read_csv(DATA+r"\16b_无泄漏共形_明细.csv")
DROP=["county","year","yield","intensity"]; XCOLS=[c for c in m.columns if c not in DROP]
tr=m.year.values<=2020; te=m.year.values>=2021
counties=sorted(m.county.unique())

def dz_ci(d,n_boot=2000,seed=0):
    d=np.asarray(d,float); dz=d.mean()/d.std(ddof=1)
    rng=np.random.default_rng(seed); bs=[]
    for _ in range(n_boot):
        x=d[rng.integers(0,len(d),len(d))]
        bs.append(x.mean()/x.std(ddof=1) if x.std(ddof=1)>0 else np.nan)
    bs=np.asarray(bs); bs=bs[~np.isnan(bs)]
    return dz, np.percentile(bs,2.5), np.percentile(bs,97.5)

# ---------- sklearn 市县配对 ----------
Xtr=m.loc[tr,XCOLS].values; Xte=m.loc[te,XCOLS].values
ytr=m.loc[tr,"yield"].values; yte=m.loc[te,"yield"].values
sc=StandardScaler().fit(Xtr); sdj=Xtr.std(0)
sk={"ElasticNet":ElasticNet(alpha=.03,l1_ratio=.2,max_iter=5000),
    "RandomForest":RandomForestRegressor(400,max_depth=12,min_samples_leaf=2,random_state=1,n_jobs=-1),
    "XGBoost":XGBRegressor(n_estimators=400,learning_rate=.03,max_depth=4,subsample=.8,
        colsample_bytree=.8,min_child_weight=3,random_state=1,n_jobs=-1,verbosity=0),
    "LightGBM":LGBMRegressor(n_estimators=400,learning_rate=.03,num_leaves=31,
        min_child_samples=5,random_state=1,n_jobs=-1,verbose=-1)}
def county_mae(pred_tot):
    df=pd.DataFrame({"county":m.loc[te,"county"],"ae":np.abs(pred_tot-yte)})
    return df.groupby("county").ae.mean().reindex(counties).values
rows=[]; ci_rows=[]
for name,mdl in sk.items():
    mdl.fit(sc.transform(Xtr),ytr)
    clean=county_mae(mdl.predict(sc.transform(Xte)))
    rng=np.random.default_rng(1)
    for k in KS:
        acc=np.zeros(len(counties))
        for b in range(B):
            noise=rng.normal(0,1,Xte.shape)*(sdj[None]*k)
            acc+=county_mae(mdl.predict(sc.transform(Xte+noise)))
        noise_mae=acc/B; d=noise_mae-clean
        t,p=stats.ttest_rel(noise_mae,clean); dz,lo,hi=dz_ci(d,seed=int(k*1000))
        rows.append({"model":name,"k":k,"n_pairs":len(d),"t":t,"p":p,"cohen_dz":dz})
        ci_rows.append({"model":name,"k":k,"dz":dz,"CI_lo":lo,"CI_hi":hi})

# ---------- BPINN 市县配对 ----------
src=open(r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py",encoding="utf-8").read()
g={"__name__":"x"}; exec(src.split("idx=np.arange(len(m))")[0],g)
MLAI,MPRI,MTc=g["MLAI"],g["MPRI"],g["MTc"]; AREA=g["AREA"]; Xann=g["Xann"]; PH=g["PH"]
idx=np.arange(len(m)); tridx=idx[tr]; teidx=idx[te]
md,params=g["train_model"](tridx,seed=200)
xs,pri_mu,pri_sd,t_mu,t_sd=params
sLAI=MLAI[tridx].std(); sPRI=MPRI[tridx].std(); sTc=MTc[tridx].std()
def bp_intensity(ti,lnoise=None):
    lai=MLAI[ti].copy(); pri=MPRI[ti].copy(); tc=MTc[ti].copy()
    if lnoise is not None:
        rng,k=lnoise
        lai=np.clip(lai+rng.normal(0,sLAI*k,lai.shape),.05,None)
        pri=pri+rng.normal(0,sPRI*k,pri.shape); tc=tc+rng.normal(0,sTc*k,tc.shape)
    x=torch.tensor(xs(Xann[ti]))
    out=md(x,torch.tensor(lai),torch.tensor(pri),torch.tensor(tc),torch.tensor(PH[ti]),
           pri_mu,pri_sd,t_mu,t_sd)[0]
    return out.detach().numpy()
def bp_county_mae(ti,intensity):
    pred=intensity*AREA[ti]; true=g["Y"][ti]
    df=pd.DataFrame({"county":g["m"].county.values[ti],"ae":np.abs(pred-true)})
    return df.groupby("county").ae.mean().reindex(counties).values
clean=bp_county_mae(teidx,bp_intensity(teidx))
for k in KS:
    acc=np.zeros(len(counties)); rng=np.random.default_rng(300)
    for b in range(B):
        acc+=bp_county_mae(teidx,bp_intensity(teidx,(rng,k)))
    noise_mae=acc/B; d=noise_mae-clean
    t,p=stats.ttest_rel(noise_mae,clean); dz,lo,hi=dz_ci(d,seed=int(k*1000)+5)
    rows.append({"model":"BPINN","k":k,"n_pairs":len(d),"t":t,"p":p,"cohen_dz":dz})
    ci_rows.append({"model":"BPINN","k":k,"dz":dz,"CI_lo":lo,"CI_hi":hi})
pa=pd.DataFrame(rows); pa.to_csv(DATA+r"\17a_市县配对鲁棒性.csv",index=False,encoding="utf-8-sig")
pd.DataFrame(ci_rows).to_csv(DATA+r"\17e_配对dz_CI.csv",index=False,encoding="utf-8-sig")

# ---------- 逐市县 R2（空间） ----------
rr=[]
for c,g0 in sp.groupby("county"):
    yt=g0.true_intensity.values; yp=g0.pred_intensity.values
    R2=1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum(); rr.append({"county":c,"R2":R2})
cr=pd.DataFrame(rr); cr.to_csv(DATA+r"\17b_逐市县R2.csv",index=False,encoding="utf-8-sig")
R=cr.R2
print("逐市县R2: 中位%.3f IQR %.3f–%.3f 极差 %.3f–%.3f"%(R.median(),R.quantile(.25),R.quantile(.75),R.min(),R.max()))
# ---------- 逐年 R2（空间预测） ----------
S=conf[conf.regime=="Spatial LOCO"]; yr=[]
for y,g0 in S.groupby("year"):
    yt=g0.true_total.values; yp=g0.pred_total.values
    yr.append({"year":y,"R2":1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum()})
cy=pd.DataFrame(yr); cy.to_csv(DATA+r"\17c_逐年R2.csv",index=False,encoding="utf-8-sig")
print("逐年R2: 中位%.3f IQR %.3f–%.3f 极差 %.3f–%.3f"%(cy.R2.median(),cy.R2.quantile(.25),
    cy.R2.quantile(.75),cy.R2.min(),cy.R2.max()))
# ---------- 表6 均值±SD ----------
out=[]
for mdl in ["ElasticNet","RandomForest","XGBoost","LightGBM","BPINN"]:
    s=c8[c8.model==mdl]; base=float(s[s.cond=="clean"].RMSE_mean.iloc[0])
    for k in KS:
        r=s[(s.cond=="noise")&(s.k==k)].iloc[0]
        out.append({"model":mdl,"k":k,"RMSE_change_%":(r.RMSE_mean/base-1)*100,
            "RMSE_change_SD%":(r.RMSE_sd/base)*100})
pd.DataFrame(out).to_csv(DATA+r"\17d_鲁棒性均值SD.csv",index=False,encoding="utf-8-sig")
print("\n市县配对（n=18）："); print(pa.round(3).to_string(index=False))
print("\n第17步完成。")
