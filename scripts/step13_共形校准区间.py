# -*- coding: utf-8 -*-
"""
第13步：共形预测(conformal)校准区间，修正MC Dropout区间覆盖率过低(过度自信)问题。
原始区间仅含认知不确定性，PICP远低于95%。加入数据驱动残差宽度：
 (A) 时间外推 split-conformal：训练<=2018，2019-2020为校准集(不参与训练)，
     由强度(t/ha)残差求95%分位q，预测2021-2023：区间=预测±q·收获面积。
 (B) 空间LOCO / 时空块 cross-conformal：用全部252个诚实LOCO强度残差求q
     (留一县、样本外)，对各regime统一校准(按面积异方差)。
输出：13a_共形校准_时间.csv；13b_共形校准_各regime覆盖率.csv；
      13c_校准后预测明细(含共形区间).csv
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, torch
DATA=r"E:\海南\橡胶产量建模_结果\数据"
m=pd.read_csv(DATA+r"\05_主表_年度面板.csv")
det=pd.read_csv(DATA+r"\07_PINN预测明细.csv")

# 载入step7对象
src=open(r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py",encoding="utf-8").read()
g={"__name__":"x"}; exec(src.split("idx=np.arange(len(m))")[0],g)
MLAI=g["MLAI"];MPRI=g["MPRI"];MTc=g["MTc"]; AREA=g["AREA"]; Xann=g["Xann"]
train_model=g["train_model"]; predict=g["predict"]
idx=np.arange(len(m))

def q95(resid):
    n=len(resid); a=np.ceil((n+1)*.95)/n
    return np.quantile(np.abs(resid),min(a,1.0))

# ---------- (A) 时间 split-conformal ----------
tr=idx[m.year.values<=2018]; cal=idx[(m.year.values>=2019)&(m.year.values<=2020)]
te=idx[m.year.values>=2021]
md,p=train_model(tr,seed=42)
mu_cal,_=predict(md,cal,p,K=1)
r_cal=(mu_cal-m.intensity.values[cal])  # 强度残差 t/ha
qt=q95(r_cal)
mu_te,_=predict(md,te,p,K=1)
pred=mu_te*AREA[te]
half=qt*AREA[te]
A=pd.DataFrame({"county":m.county.values[te],"year":m.year.values[te],
    "true_total":m["yield"].values[te],"pred_total":pred,
    "lo_conformal":pred-half,"hi_conformal":pred+half})
A.to_csv(DATA+r"\13a_共形校准_时间.csv",index=False,encoding="utf-8-sig")
picp=((A.true_total>=A.lo_conformal)&(A.true_total<=A.hi_conformal)).mean()
mpw=(A.hi_conformal-A.lo_conformal).mean()
print(f"[时间split-conformal] q={qt:.3f} t/ha  PICP={picp:.3f}  MPIW={mpw:,.0f}")

# ---------- (B) cross-conformal (LOCO强度残差) ----------
loco=det[det.regime=="S_LOCO"].copy()
r_loco=(loco.pred_total.values-loco.true_total.values)/ \
       m.set_index(["county","year"]).loc[list(zip(loco.county,loco.year)),"area_harvest"].values
ql=q95(r_loco)
print(f"[cross-conformal] q={ql:.3f} t/ha (基于{len(r_loco)}个LOCO强度残差)")

rows=[]; frames=[]
for rg,gg in det.groupby("regime"):
    area=m.set_index(["county","year"]).loc[list(zip(gg.county,gg.year)),"area_harvest"].values
    half=ql*area
    lo=gg.pred_total.values-half; hi=gg.pred_total.values+half
    picp=((gg.true_total.values>=lo)&(gg.true_total.values<=hi)).mean()
    mpw=(hi-lo).mean(); rng=gg.true_total.max()-gg.true_total.min()
    rows.append({"regime":rg,"q_t/ha":ql,"PICP95_conformal":picp,
        "MPIW_conformal":mpw,"NMPIW":mpw/rng})
    f=gg.copy(); f["lo_conformal"]=lo; f["hi_conformal"]=hi; frames.append(f)
Bm=pd.DataFrame(rows)
Bm.to_csv(DATA+r"\13b_共形校准_各regime覆盖率.csv",index=False,encoding="utf-8-sig")
pd.concat(frames).to_csv(DATA+r"\13c_校准后预测明细.csv",index=False,encoding="utf-8-sig")
print("\n各regime共形校准后覆盖率：")
print(Bm.round(3).to_string(index=False))
print("完成。")
