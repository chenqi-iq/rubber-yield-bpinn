"""
Evaluate model robustness under input perturbation (Gaussian noise at multiple levels) using Monte Carlo repeats.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python eval_noise_robustness.py
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
第8步：修正后的"噪声扰动"——输入不确定性/鲁棒性的蒙特卡洛分析(不伪造样本、不抬高评估)。
原方法错误：对PCA【零均值】主成分按"特征均值"取σ，均值≈0 → 实际没加噪声，且把噪声样本混入训练。
本步正确做法：
  * 对【原始物理输入】加高斯噪声，σ = k × 该特征在【训练集】上的标准差(s)，k=0.01/0.05/0.10
    分别代表低/中/高相对扰动；
  * 模型只在干净训练集训练一次；扰动仅在【固定测试集】上传播(B次抽样)，统计R²/RMSE分布；
  * 不向训练集加入任何噪声副本，因此不会虚增样本或泄漏。
  * sklearn模型扰动年度特征矩阵；PINN扰动月度物理序列(LAI/PRI/冠层温度)。
  * PINN因随机初始化：N次独立训练，对同一模型"干净 vs 各噪声"做配对t检验(报告RMSE均值±SD)。

输出：08_噪声鲁棒性_MC.csv；08_配对检验.csv
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, torch
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

OUT=r"E:\海南\橡胶产量建模_结果\数据"
SEED=1; KS=[0.01,0.05,0.10]; B=80
m=pd.read_csv(os.path.join(OUT,"05_主表_年度面板.csv"))
DROP=["county","year","yield","intensity"]
XCOLS=[c for c in m.columns if c not in DROP]
tr=m.year.values<=2020; te=m.year.values>=2021
Xtr=m.loc[tr,XCOLS].values; Xte=m.loc[te,XCOLS].values
ytr=m.loc[tr,"yield"].values; yte=m.loc[te,"yield"].values
xs=StandardScaler().fit(Xtr); Xtr_s=xs.transform(Xtr); Xte_s=xs.transform(Xte)
sd_j=Xtr.std(0)  # 每特征训练std(物理单位)

def sk_models():
    return {"ElasticNet":ElasticNet(alpha=.03,l1_ratio=.2,max_iter=5000),
            "RandomForest":RandomForestRegressor(400,max_depth=12,min_samples_leaf=2,
                random_state=SEED,n_jobs=-1),
            "XGBoost":XGBRegressor(n_estimators=400,learning_rate=.03,max_depth=4,
                subsample=.8,colsample_bytree=.8,min_child_weight=3,
                random_state=SEED,n_jobs=-1,verbosity=0),
            "LightGBM":LGBMRegressor(n_estimators=400,learning_rate=.03,num_leaves=31,
                min_child_samples=5,random_state=SEED,n_jobs=-1,verbose=-1)}
def metr(yt,yp):
    R2=1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum()
    return R2,np.sqrt(((yt-yp)**2).mean())

rows=[]
fitted={}
for name,mdl in sk_models().items():
    mdl.fit(Xtr_s,ytr); fitted[name]=mdl
    base=mdl.predict(Xte_s)
    r20,rm0=metr(yte,base)
    rows.append((name,"clean",0,r20,0,rm0,0))
    rng=np.random.default_rng(SEED)
    for k in KS:
        r2s=[];rms=[]
        for b in range(B):
            noise=rng.normal(0,1,Xte.shape)* (sd_j[None,:]*k)
            Xp=xs.transform(Xte+noise)
            p=mdl.predict(Xp); r2,rm=metr(yte,p); r2s.append(r2);rms.append(rm)
        rows.append((name,"noise",k,np.mean(r2s),np.std(r2s),np.mean(rms),np.std(rms)))

# ---- PINN：复用step7结构，N次训练 × 干净/噪声 配对 ----
import importlib.util
spec=importlib.util.spec_from_file_location("s7",r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py")
s7=importlib.util.module_from_spec(spec)
# 手动执行会重跑整个step7；为避免，这里直接内联加载其数据与类
g={"__name__":"s7notmain"}
src=open(r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py").read()
# 只取到主程序之前(类与数据准备)
head=src.split('idx=np.arange(len(m))')[0]
exec(head,g)
PINN=g['PINN']; scale_fit=g['scale_fit']
MLAI=g['MLAI'];MPRI=g['MPRI'];MTc=g['MTc']; Xann=g['Xann']; AREA=g['AREA']; INT=g['INT']
train_model=g['train_model']
idx=np.arange(len(m))
tridx=idx[tr]; teidx=idx[te]
sLAI=MLAI[tridx].std(); sPRI=MPRI[tridx].std(); sTc=MTc[tridx].std()
N=8
clean_rm=[]; noise_rm={k:[] for k in KS}
for n in range(N):
    md,p=train_model(tridx,seed=200+n)
    params=p
    def pin_pred(ti,monthly_noise=None):
        xsc,pri_mu,pri_sd,t_mu,t_sd=params
        lai=MLAI[ti].copy();pri=MPRI[ti].copy();tc=MTc[ti].copy()
        if monthly_noise is not None:
            rng,kk=monthly_noise
            lai=np.clip(lai+rng.normal(0,sLAI*kk,lai.shape),0.05,None)
            pri=pri+rng.normal(0,sPRI*kk,pri.shape)
            tc =tc +rng.normal(0,sTc*kk,tc.shape)
        x=torch.tensor(xsc(Xann[ti]))
        yp,_,_=md(x,torch.tensor(lai),torch.tensor(pri),torch.tensor(tc),
                  torch.tensor(g['PH'][ti]),pri_mu,pri_sd,t_mu,t_sd)
        return yp.detach().numpy()*AREA[ti]
    pc=pin_pred(teidx); _,rm=metr(yte,pc); clean_rm.append(rm)
    for k in KS:
        rng=np.random.default_rng(300+n)
        rms=[]
        for b in range(40):
            pp=pin_pred(teidx,(rng,k)); _,rm=metr(yte,pp); rms.append(rm)
        noise_rm[k].append(np.mean(rms))
rows.append(("BPINN","clean",0,np.nan,0,np.mean(clean_rm),np.std(clean_rm)))
for k in KS:
    rows.append(("BPINN","noise",k,np.nan,0,np.mean(noise_rm[k]),np.std(noise_rm[k])))

res=pd.DataFrame(rows,columns=["model","cond","k","R2_mean","R2_sd","RMSE_mean","RMSE_sd"])
res.to_csv(os.path.join(OUT,"08_噪声鲁棒性_MC.csv"),index=False,encoding="utf-8-sig")

# 配对t检验(BPINN clean vs 各噪声；以及sklearn通过MC分布)
pair=[]
for k in KS:
    t,pv=stats.ttest_rel(noise_rm[k],clean_rm)
    pair.append({"model":"BPINN","k":k,"t":t,"p":pv,
        "RMSE_clean":np.mean(clean_rm),"RMSE_noise":np.mean(noise_rm[k])})
pd.DataFrame(pair).to_csv(os.path.join(OUT,"08_配对检验.csv"),index=False,encoding="utf-8-sig")
print(res.round(3).to_string(index=False))
print("\n配对t检验:")
print(pd.DataFrame(pair).round(4).to_string(index=False))
print("完成。")
