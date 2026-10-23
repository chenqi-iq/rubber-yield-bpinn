# -*- coding: utf-8 -*-
"""
第10step：SCI出版级figure(英文标注, 300 dpi, Morandi莫兰迪低饱和配色)。
Figure：
 Fig1 多regime模型对比(R²)
 Fig2 消融实验(C0-C3 × 3 regimes)
 Fig3 物理parameter后验95%CI(Topt/pHopt/LAIopt)
 Fig4 BPINN 预测vs真实(三regime)
 Fig5 Canopy temp钟形热响应曲线 f_T
 Fig6 Danzhou产量时间序列+95%不确定性带(LOCO)
 Fig7 噪声鲁棒性(RMSEwith perturbationk)
output to figure/ 目录。
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":"#6b6b6b",
    "axes.linewidth":.8,"axes.grid":True,"grid.color":"#d9d5cf","grid.linewidth":.7,
    "axes.axisbelow":True,"xtick.color":"#444","ytick.color":"#444","axes.labelcolor":"#333",
    "figure.dpi":120})
MOR=["#8A9A8C","#B0A18F","#8E9AAB","#B99C94","#A8B5A0","#9C8F99","#7E8C96","#C2A98F"]
DATA=r"E:\海南\橡胶产量建模_结果\数据"; FIG=r"E:\海南\橡胶产量建模_结果\figure"
os.makedirs(FIG,exist_ok=True)

c6=pd.read_csv(os.path.join(DATA,"06_模型对比_各regime.csv"))
c7=pd.read_csv(os.path.join(DATA,"07_PINN各regime指标.csv"))
c9=pd.read_csv(os.path.join(DATA,"09_消融实验.csv"))
post=pd.read_csv(os.path.join(DATA,"07_物理parameter后验.csv"))
det=pd.read_csv(os.path.join(DATA,"07_PINN预测明细.csv"))
c8=pd.read_csv(os.path.join(DATA,"08_噪声鲁棒性_MC.csv"))

# ---------- Fig1 ----------
models=["ElasticNet","XGBoost","RandomForest","LightGBM","Persistence","BPINN"]
regs=["S_LOCO","T_EndHoldout","ST_Blocked"]
def get_r2(model,reg):
    if model=="BPINN":
        x=c7[c7.regime==reg]; return float(x.R2.iloc[0]) if len(x) else np.nan
    x=c6[(c6.model==model)&(c6.regime==reg)]; return float(x.R2.iloc[0]) if len(x) else np.nan
fig,ax=plt.subplots(figsize=(8.2,4.4))
x=np.arange(len(regs)); w=.13
for i,md in enumerate(models):
    vals=[get_r2(md,r) for r in regs]
    ax.bar(x+(i-2.5)*w,vals,w,label=md,color=MOR[i],edgecolor="white",linewidth=.5)
ax.set_xticks(x); ax.set_xticklabels(["Spatial LOCO","Temporal hold-out","Spatiotemporal block"])
ax.set_ylabel("$R^2$ (pooled)"); ax.set_ylim(0,1.0); ax.legend(ncol=3,frameon=False,
    loc="upper center",bbox_to_anchor=(.5,1.16),fontsize=9)
ax.axhline(0,color="#6b6b6b",lw=.8)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig1_模型多regime对比.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig1_模型多regime对比.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig2 ablation ----------
fig,axes=plt.subplots(1,3,figsize=(11,3.6),sharey=True)
conf=["C0_5yearly only","C1_14yearly only","C2_14年完整","C3_完整+物理BPINN"]
regmap={"T":"Temporal","S":"Spatial","ST":"Spatiotemporal"}
regmap2={"S_LOCO":"Spatial LOCO","T_EndHoldout":"Temporal hold-out","ST_Blocked":"Spatiotemporal block"}
for ax,rg in zip(axes,["T","S","ST"]):
    def val(c,ln):
        x=c9[(c9.regime==rg)&(c9.config==c)&(c9.learner==ln)].R2
        return float(x.iloc[0]) if len(x) else np.nan
    en=[val(c,"ElasticNet") for c in conf[:3]]
    xg=[val(c,"XGBoost") for c in conf[:3]]
    bp=val(conf[3],"BPINN")
    xx=np.arange(4)
    ax.bar(xx-.13,en+[np.nan],.25,label="ElasticNet",color=MOR[0],edgecolor="white")
    ax.bar(xx+.13,xg+[np.nan],.25,label="XGBoost",color=MOR[2],edgecolor="white")
    ax.bar(3,bp,.25,label="BPINN",color=MOR[5],edgecolor="white")
    ax.set_xticks(xx); ax.set_xticklabels(["C0","C1","C2","C3"],fontsize=9)
    ax.set_title(regmap[rg],fontsize=10); ax.set_ylim(0,1)
axes[0].set_ylabel("$R^2$"); axes[0].legend(frameon=False,fontsize=8,loc="lower left")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig2_消融实验.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig2_消融实验.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig3 physical posterior ----------
pt=post[post.regime=="T_EndHoldout"].set_index("param")
items=[("Topt","Opt. canopy temp. (°C)",20,34),
       ("PHopt","Opt. soil pH",4.5,6.5),
       ("LAIopt","Opt. LAI (m$^2$ m$^{-2}$)",0,6)]
fig,axes=plt.subplots(1,3,figsize=(10,3.2))
for ax,(p,lab,lo,hi) in zip(axes,items):
    r=pt.loc[p]; m_,l,h=r["mean"],r.lo,r.hi
    ax.errorbar(m_,0,xerr=[[m_-l],[h-m_]],fmt="o",color=MOR[5],ecolor=MOR[3],
        elinewidth=2,capsize=5,markersize=8)
    ax.set_xlim(lo,hi); ax.set_yticks([]); ax.set_xlabel(lab)
    ax.grid(axis="y",visible=False)
    ax.spines[["left","top","right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig3_物理parameter后验.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig3_物理parameter后验.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig4 pred vs true ----------
fig,axes=plt.sub.subplots(1,3,figsize=(11.5,3.9)) if False else plt.subplots(1,3,figsize=(11.5,3.9))
for ax,rg in zip(axes,regs):
    g=det[det.regime==rg]
    ax.scatter(g.true_total,g.pred_total,s=22,color=MOR[5],alpha=.75,edgecolor="white",linewidth=.4)
    lim=max(g.true_total.max(),g.pred_total.max())*1.05
    ax.plot([0,lim],[0,lim],color="#8a8a8a",ls="--",lw=1)
    r2=1-((g.true_total-g.pred_total)**2).sum()/((g.true_total-g.true_total.mean())**2).sum()
    rm=np.sqrt(((g.true_total-g.pred_total)**2).mean())
    ax.text(.05,.92,f"$R^2$={r2:.3f}\nRMSE={rm:,.0f}",transform=ax.transAxes,fontsize=9,
        va="top",bbox=dict(boxstyle="round,pad=.3",fc="white",ec="#cfc9c2",alpha=.85))
    ax.set_xlim(0,lim); ax.set_ylim(0,lim); ax.set_title(regmap2[rg],fontsize=10)
    ax.set_xlabel("Observed total (t)")
axes[0].set_ylabel("Predicted total (t)")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig4_预测vs真实.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig4_预测vs真实.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig5 thermal response ----------
Tcopt=float(pt.loc["Topt","mean"]); sT=float(pt.loc["sT","mean"]); 
LAIopt=float(pt.loc["LAIopt","mean"]); sLAI=float(pt.loc["sLAI","mean"])
fig,axes=plt.subplots(1,2,figsize=(9.5,3.6))
tt=np.linspace(12,40,300)
axes[0].plot(tt,np.exp(-(tt-Tcopt)**2/(2*sT**2)),color=MOR[5],lw=2)
axes[0].axvline(Tcopt,color=MOR[3],ls="--",lw=1.2)
axes[0].text(Tcopt+.4,.05,f"$T_{{opt}}$={Tcopt:.1f}°C",fontsize=9,color=MOR[3])
mon=pd.read_csv(os.path.join(DATA,"05b_主表_月度长面板.csv"))
axes[0].hist(mon.Canopy,bins=40,density=True,color=MOR[0],alpha=.35)
axes[0].set_xlabel("Canopy temperature (°C)"); axes[0].set_ylabel("$f_T$ / density")
axes[0].set_title("Thermal response $f_T$",fontsize=10)
ll=np.linspace(0,6,300)
axes[1].plot(ll,np.exp(-(ll-LAIopt)**2)/(2*sLAI**2) if False else
             np.exp(-(ll-LAIopt)**2/(2*sLAI**2)),color=MOR[5],lw=2)
axes[1].axvline(LAIopt,color=MOR[3],ls="--",lw=1.2)
axes[1].text(LAIopt+.1,.05,f"$LAI_{{opt}}$={LAIopt:.1f}",fontsize=9,color=MOR[3])
axes[1].hist(mon.LAI,bins=40,density=True,color=MOR[0],alpha=.35)
axes[1].set_xlabel("LAI (m$^2$ m$^{-2}$)"); axes[1].set_ylabel("$f_{LAI}$ / density")
axes[1].set_title("Canopy response $f_{LAI}$",fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig5_热响应曲线.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig5_热响应曲线.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig6 Danzhou time series with CI ----------
g=det[(det.regime=="S_LOCO")&(det.county=="Danzhou")].sort_values("year")
fig,ax=plt.subplots(figsize=(7.2,4))
ax.fill_between(g.year,g.lo,g.hi,color=MOR[5],alpha=.2,label="95% interval")
ax.plot(g.year,g.pred_total,color=MOR[5],lw=1.8,marker="o",ms=4,label="BPINN prediction")
ax.plot(g.year,g.true_total,color=MOR[3],lw=1.8,marker="s",ms=4,label="Observed")
ax.set_xlabel("Year"); ax.set_ylabel("Danzhou rubber total (t)")
ax.legend(frameon=False,fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig6_Danzhou不确定性时间序列.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig6_Danzhou不确定性时间序列.pdf"),bbox_inches="tight"); plt.close()

# ---------- Fig7 noise robustness ----------
fig,ax=plt.subplots(figsize=(6.8,4))
for i,md in enumerate(["ElasticNet","RandomForest","XGBoost","LightGBM","BPINN"]):
    s=c8[c8.model==md]
    base=float(s[s.cond=="clean"].RMSE_mean.iloc[0])
    chg=[(float(r.RMSE_mean)/base-1)*100 for _,r in s[s.cond=="noise"].iterrows()]
    ax.plot([.01,.05,.10],chg,marker="o",color=MOR[i],lw=1.6,label=md,ms=5)
ax.axhline(0,color="#8a8a8a",lw=.8,ls="--")
ax.set_xlabel("Perturbation level $k$ ($\\sigma=k\\,s$)")
ax.set_ylabel("RMSE change (%)"); ax.legend(frameon=False,fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"Fig7_噪声鲁棒性.png"),dpi=300,bbox_inches="tight"); fig.savefig(os.path.join(FIG,"Fig7_噪声鲁棒性.pdf"),bbox_inches="tight"); plt.close()
print("figures generated：",os.listdir(FIG))
