# -*- coding: utf-8 -*-
"""
第12步：SCI统计补强（真实计算）。
 (1) 相关性/多重共线性：各预测变量与总产量的Pearson相关(排序)；关键预测子之间相关矩阵；
     报告高共线对(|r|>=0.85)，为采用ElasticNet等正则化提供依据。
 (2) 区间校准：PICP(95%区间覆盖率)、MPIW(平均区间宽度)、归一化MPIW，逐regime。
 (3) 配对t检验效应量：Cohen dz = t/sqrt(n)，并对3个水平做Holm校正。
输出：12a_变量与产量相关.csv；12b_关键变量相关矩阵.csv；12c_高共线对.csv；
      12d_区间校准PICP_MPIW.csv；12e_配对效应量Holm.csv
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
DATA=r"E:\海南\橡胶产量建模_结果\数据"
m=pd.read_csv(DATA+r"\05_主表_年度面板.csv")
det=pd.read_csv(DATA+r"\07_PINN预测明细.csv")
pair=pd.read_csv(DATA+r"\08_配对检验.csv")

DROP=["county","year","yield","intensity"]
XCOLS=[c for c in m.columns if c not in DROP]

# (1a) 与总产量相关
cors={c:np.corrcoef(m[c],m["yield"])[0,1] for c in XCOLS}
cor_y=(pd.Series(cors).rename("r_with_yield").sort_values(key=lambda s:s.abs(),ascending=False)
       .reset_index().rename(columns={"index":"variable"}))
cor_y["abs_r"]=cor_y.r_with_yield.abs()
cor_y.to_csv(DATA+r"\12a_变量与产量相关.csv",index=False,encoding="utf-8-sig")

# (1b) 关键变量相关矩阵（代表性子集，控制图幅）
key=["yield","area_total","area_new","area_harvest","ph_top","om_top",
     "LAI_tap_mean","LAI_win_mean","NDVI_tap_mean","PRI_tap_mean","PRI_win_mean",
     "Tc_tap_mean","Tc_win_min","Tc_summer_max",
     "LAI_ann_max","NDVI_ann_max","PRI_ann_min","Tc_ann_max"]
key=[k for k in key if k in m.columns]
cm=m[key].corr(method="pearson")
cm.to_csv(DATA+r"\12b_关键变量相关矩阵.csv",encoding="utf-8-sig")

# (1c) 高共线对
hi=[]
for i,a in enumerate(XCOLS):
    for b in XCOLS[i+1:]:
        r=np.corrcoef(m[a],m[b])[0,1]
        if abs(r)>=0.85: hi.append({"var1":a,"var2":b,"r":r})
pd.DataFrame(hi).sort_values("r",key=lambda s:s.abs(),ascending=False).to_csv(
    DATA+r"\12c_高共线对.csv",index=False,encoding="utf-8-sig")

# (2) PICP / MPIW
rows=[]
for rg,g in det.groupby("regime"):
    inside=((g.true_total>=g.lo)&(g.true_total<=g.hi)).mean()
    mpw=(g.hi-g.lo).mean()
    rng=g.true_total.max()-g.true_total.min()
    rows.append({"regime":rg,"n":len(g),"PICP95":inside,"MPIW":mpw,
        "NMPIW":mpw/rng,"target_mean":g.true_total.mean()})
pd.DataFrame(rows).to_csv(DATA+r"\12d_区间校准PICP_MPIW.csv",index=False,encoding="utf-8-sig")

# (3) 配对效应量 + Holm
n=8
e=pair.copy(); e["cohen_dz"]=e.t/np.sqrt(n); e["abs_t"]=e.t.abs()
e=e.sort_values("abs_t",ascending=False).reset_index(drop=True)
m_tests=len(e); adj=[]
for i in range(m_tests):
    p=e.p.iloc[i]; holm=min(1,p*(m_tests-i)); adj.append(holm)
e["p_holm"]=adj
e.to_csv(DATA+r"\12e_配对效应量Holm.csv",index=False,encoding="utf-8-sig")

print("与产量|相关|最高的前10：")
print(cor_y.head(10).round(3).to_string(index=False))
print(f"\n高共线对(|r|>=0.85)数量：{len(hi)}")
print(pd.DataFrame(hi).head(12).round(3).to_string(index=False))
print("\n区间校准：")
print(pd.DataFrame(rows).round(3).to_string(index=False))
print("\n配对效应量/Holm：")
print(e[["k","t","p","cohen_dz","p_holm"]].round(4).to_string(index=False))
print("完成。")
