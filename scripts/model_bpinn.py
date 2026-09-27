"""
Train the Bayesian Physics-Informed Neural Network (BPINN) with carbon-balance physical module and neural network residuals. MC Dropout for uncertainty.

Data paths (configure DATA_ROOT to match your local setup):
  - Remote sensing GeoTIFFs: <DATA_ROOT>/LAI, <DATA_ROOT>/NDVI, <DATA_ROOT>/PRI, <DATA_ROOT>/冠层温度
  - County boundary shapefile: <DATA_ROOT>/海南省县边界数据/海南省_县2.shp
  - Rubber statistics Excel: <DATA_ROOT>/海南省各市县主要热带作物面积和产量.xls
  - HWSD2 soil database: <DATA_ROOT>/output/hwssd2/
  - Output directory: <DATA_ROOT>/橡胶产量建模_结果/数据/

Usage:
  python model_bpinn.py
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
第7步：改进的物理信息神经网络 PINN / 贝叶斯 BPINN(PyTorch)。
相对原模型的实质性升级：
  (1) 用【月度】LAI/PRI/冠层温度显式积分碳平衡(日历年内逐月)，而非把年度产量复制到4季
      再滑窗造样本——模型真正"随时间演算"；
  (2) GEP新增【冠层温度钟形热响应 f_T】，呼吸改为随温度的 Q10 维持呼吸
      (原模型没有温度对光合/呼吸的非线性作用)；
  (3) 以"单产 intensity(t/ha)"为建模对象，total=intensity×收获面积(精确)，
      对2010→2011农垦口径断点稳健；
  (4) 物理在【真实物理单位】下学习(LAI_opt m²/m², T_opt ℃, pH_opt)，参数可农学解读；
  (5) 贝叶斯：MC Dropout(K次随机前向,认知不确定性)+ 多年份集成(E个独立训练)给参数后验。
损失：面积加权单产误差(等价优化总产量)+NN残差收缩(物理主导)。全批量训练(n小)。
Regime：S_LOCO / T_EndHoldout(集成,出后验) / ST_Blocked(确定性)。
输出：07_PINN预测明细.csv；07_物理参数后验.csv；07_PINN各regime指标.csv
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import torch, torch.nn as nn, torch.nn.functional as F
torch.manual_seed(0)

OUT=r"E:\海南\橡胶产量建模_结果\数据"
DAYS=torch.tensor([31,28.3,31,30,31,30,31,31,30,31,30,31],dtype=torch.float32)

m=pd.read_csv(os.path.join(OUT,"05_主表_年度面板.csv")).sort_values(["county","year"]).reset_index(drop=True)
mon=pd.read_csv(os.path.join(OUT,"05b_主表_月度长面板.csv"))
CANON=list(m.county.unique())

def monthly_col(v):
    p=mon.pivot_table(index=["county","year"],columns="month",values=v)
    return p.reindex(list(zip(m.county,m.year))).values.astype("float32")
MLAI,MNDVI,MPRI,MTc=[monthly_col(v) for v in ["LAI","NDVI","PRI","Canopy"]]
PH=m.ph_top.values.astype("float32"); OM=m.om_top.values.astype("float32")
AREA=m.area_harvest.values.astype("float32")
INT=m.intensity.values.astype("float32"); Y=m["yield"].values.astype("float32")

DROP=["county","year","yield","intensity"]
XCOLS=[c for c in m.columns if c not in DROP]
Xann=m[XCOLS].values.astype("float32")

class StandardScale:
    def __init__(self,x): self.mu=x.mean(0); self.sd=x.std(0)+1e-6
    def __call__(self,x): return (x-self.mu)/self.sd

def scale_fit(tr):
    return StandardScale(Xann[tr]), MPRI[tr].mean(), MPRI[tr].std()+1e-6, \
           INT[tr].mean(), INT[tr].std()+1e-6

class PINN(nn.Module):
    def __init__(self):
        super().__init__()
        self.rLAI=nn.Parameter(torch.tensor(-0.4)); self.sLAI=nn.Parameter(torch.tensor(0.6))
        self.rPH =nn.Parameter(torch.tensor(0.4));  self.sPH =nn.Parameter(torch.tensor(0.5))
        self.rT  =nn.Parameter(torch.tensor(0.0));  self.sT =nn.Parameter(torch.tensor(0.3))
        self.eta =nn.Parameter(torch.tensor(-0.2)); self.P0  =nn.Parameter(torch.tensor(0.0))
        self.rho =nn.Parameter(torch.tensor(-5.4)); self.aPRI=nn.Parameter(torch.tensor(0.3))
        self.b0  =nn.Parameter(torch.tensor(0.0))
        self.net=nn.Sequential(nn.Linear(len(XCOLS),48),nn.Tanh(),nn.Dropout(0.1),
                               nn.Linear(48,48),nn.Tanh(),nn.Dropout(0.1),
                               nn.Linear(48,1))
    def phys(self,lai,pri,tc,ph,pri_mu,pri_sd):
        LAIopt=2+5*torch.sigmoid(self.rLAI); sLAI=0.5+2*F.softplus(self.sLAI)
        PHopt =4.5+1.5*torch.sigmoid(self.rPH); sPH=0.2+F.softplus(self.sPH)
        Topt  =20+12*torch.sigmoid(self.rT); sT=3+10*F.softplus(self.sT)
        etaR  =0.1+0.5*torch.sigmoid(self.eta); P0=0.5+1.5*F.softplus(self.P0)
        fLAI=torch.exp(-(lai-LAIopt)**2/(2*sLAI**2))
        fPH =torch.exp(-(ph[:,None]-PHopt)**2/(2*sPH**2))
        fT  =torch.exp(-(tc-Topt)**2/(2*sT**2))
        fPRI=torch.clamp(1+self.aPRI*((pri-pri_mu)/pri_sd),0.2,2.0)
        gep=P0*fLAI*fPH*fPRI*fT
        r=etaR*gep*torch.pow(2.0,(tc-25)/10)
        C=self.b0+((gep-r)*DAYS[None,:]).sum(1)
        rho=F.softplus(self.rho)+1e-3
        return rho*C, dict(LAIopt=LAIopt,sLAI=sLAI,PHopt=PHopt,sPH=sPH,Topt=Topt,
                           sT=sT,etaR=etaR,P0=P0,rho=rho,aPRI=self.aPRI)
    def forward(self,xann,lai,pri,tc,ph,pri_mu,pri_sd,t_mu,t_sd):
        yphys,_=self.phys(lai,pri,tc,ph,pri_mu,pri_sd)
        dstd=self.net(xann).squeeze(1)
        return yphys+dstd*t_sd, yphys, dstd

def train_model(tr,seed,epochs=260,use_nn=True):
    torch.manual_seed(seed); model=PINN()
    xs,pri_mu,pri_sd,t_mu,t_sd=scale_fit(tr)
    opt=torch.optim.Adam(model.parameters(),lr=0.02)
    sch=torch.optim.lr_scheduler.StepLR(opt,step_size=120,gamma=0.5)
    x=torch.tensor(xs(Xann[tr])); lai=torch.tensor(MLAI[tr]); pri=torch.tensor(MPRI[tr])
    tc=torch.tensor(MTc[tr]); ph=torch.tensor(PH[tr])
    tgt=torch.tensor(INT[tr]); ww=torch.tensor(AREA[tr]/AREA[tr].mean())
    for ep in range(epochs):
        yp,yphys,dstd=model(x,lai,pri,tc,ph,pri_mu,pri_sd,t_mu,t_sd)
        loss=((ww*(yp-tgt))**2).mean()+0.05*(dstd**2).mean() if use_nn else \
             ((ww*(yphys-tgt))**2).mean()
        opt.zero_grad(); loss.backward(); opt.step(); sch.step()
    return model,(xs,pri_mu,pri_sd,t_mu,t_sd)

def predict(model,te,params,K=1):
    xs,pri_mu,pri_sd,t_mu,t_sd=params
    x=torch.tensor(xs(Xann[te])); lai=torch.tensor(MLAI[te]); pri=torch.tensor(MPRI[te])
    tc=torch.tensor(MTc[te]); ph=torch.tensor(PH[te])
    if K==1:
        model.eval()
        with torch.no_grad():
            yp,_,_=model(x,lai,pri,tc,ph,pri_mu,pri_sd,t_mu,t_sd)
        return yp.numpy(),None
    model.train()
    with torch.no_grad():
        ps=[model(x,lai,pri,tc,ph,pri_mu,pri_sd,t_mu,t_sd)[0].numpy() for _ in range(K)]
    ps=np.array(ps); return ps.mean(0),ps

def metrics(yt,yp):
    yt=np.asarray(yt,float); yp=np.asarray(yp,float)
    return dict(R2=1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum(),
                RMSE=np.sqrt(((yt-yp)**2).mean()),
                MAE=np.abs(yt-yp).mean(),
                MAPE=np.abs((yt-yp)/yt).mean()*100)

idx=np.arange(len(m)); detail=[]; metric_rows=[]; post=[]
def run_folds(regime,folds,ensemble=1,K=50):
    for tr,te in folds:
        if ensemble>1:
            pss=[]; theta=[]
            for e in range(ensemble):
                md,p=train_model(tr,seed=100+e)
                mu,ps=predict(md,te,p,K=K if e==0 else 1)
                pss.append(ps if ps is not None else mu[None])
                theta.append({k:v.item() for k,v in md.phys(torch.tensor(MLAI[te]),
                    torch.tensor(MPRI[te]),torch.tensor(MTc[te]),torch.tensor(PH[te]),
                    p[1],p[2])[1].items()})
            P=np.concatenate(pss,0)
            detail.append(pd.DataFrame({"county":m.county.values[te],"year":m.year.values[te],
                "regime":regime,"true_total":Y[te],"pred_total":P.mean(0)*AREA[te],
                "pred_sd":P.std(0)*AREA[te],"lo":np.percentile(P,2.5,0)*AREA[te],
                "hi":np.percentile(P,97.5,0)*AREA[te]}))
            th=pd.DataFrame(theta)
            for c in th.columns:
                post.append({"regime":regime,"param":c,"mean":th[c].mean(),"sd":th[c].std(),
                    "lo":th[c].quantile(.025),"hi":th[c].quantile(.975)})
        else:
            md,p=train_model(tr,seed=7); mu,ps=predict(md,te,p,K=K)
            detail.append(pd.DataFrame({"county":m.county.values[te],"year":m.year.values[te],
                "regime":regime,"true_total":Y[te],"pred_total":mu*AREA[te],
                "pred_sd":ps.std(0)*AREA[te] if ps is not None else np.nan,
                "lo":np.percentile(ps,2.5,0)*AREA[te] if ps is not None else np.nan,
                "hi":np.percentile(ps,97.5,0)*AREA[te] if ps is not None else np.nan}))

print("S_LOCO ...")
run_folds("S_LOCO",[(idx[m.county.values!=c],idx[m.county.values==c]) for c in CANON])
print("T_EndHoldout (ensemble) ...")
run_folds("T_EndHoldout",[(idx[m.year.values<=2020],idx[m.year.values>=2021])],ensemble=12,K=50)
print("ST_Blocked ...")
run_folds("ST_Blocked",[(idx[(m.county.values!=c)&(m.year.values<=2020)],
        idx[(m.county.values==c)&(m.year.values>=2021)]) for c in CANON])

det=pd.concat(detail,ignore_index=True)
det.to_csv(os.path.join(OUT,"07_PINN预测明细.csv"),index=False,encoding="utf-8-sig")
pd.DataFrame(post).to_csv(os.path.join(OUT,"07_物理参数后验.csv"),index=False,encoding="utf-8-sig")
for rg in det.regime.unique():
    g=det[det.regime==rg]; mt=metrics(g.true_total,g.pred_total)
    mt.update(regime=rg,model="BPINN"); metric_rows.append(mt)
mr=pd.DataFrame(metric_rows)
mr.to_csv(os.path.join(OUT,"07_PINN各regime指标.csv"),index=False,encoding="utf-8-sig")
print(mr.round(3).to_string(index=False))
print("\n物理参数后验(T_EndHoldout):")
print(pd.DataFrame(post)[pd.DataFrame(post).regime=="T_EndHoldout"].round(3).to_string(index=False))
print("完成。")
