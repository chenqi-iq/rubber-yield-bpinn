# -*- coding: utf-8 -*-
"""
第14step：新增与改进figure（PNG + 矢量PDF，Morandi配色，英文标注）。
  Fig8 关键变量相关性热力Figure（with多重共线性）
  Fig9 物理parameter后验小提琴Figure（12个时间集成模型的parameter分布，显示中位数/四分位）
  Fig6 Danzhou时间序列：叠加认知区间与【共形校准】区间
  Fig7 噪声鲁棒性：加误差棒(±SD)，定义正=RMSE增大(degraded)
另保存时间集成parameter样本 07b_集成parameter样本.csv。
"""
import os, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.edgecolor":"#6b6b6b",
    "axes.linewidth":.8,"figure.dpi":120})
MOR=["#8A9A8C","#B0A18F","#8E9AAB","#B99C94","#A8B5A0","#9C8F99","#7E8C96"]
DATA=r"E:\海南\橡胶产量建模_结果\数据"; FIG=r"E:\海南\橡胶产量建模_结果\figure"
cm=pd.read_csv(DATA+r"\12b_关键变量相关矩阵.csv",index_col=0)
cal=pd.read_csv(DATA+r"\13c_校准后预测明细.csv")
c8=pd.read_csv(DATA+r"\08_噪声鲁棒性_MC.csv")

def SF(fig,name):
    fig.savefig(os.path.join(FIG,name+".png"),dpi=300,bbox_inches="tight")
    fig.savefig(os.path.join(FIG,name+".pdf"),bbox_inches="tight"); plt.close()

# ---- 收集时间集成parameter样本 ----
src=open(r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py",encoding="utf-8").read()
g={"__name__":"x"}; exec(src.split("idx=np.arange(len(m))")[0],g)
m=g["m"]; idx=np.arange(len(m)); tr=idx[m.year.values<=2020]; te=idx[m.year.values>=2021]
thetas=[]
for e in range(12):
    md,p=g["train_model"](tr,seed=100+e)
    th={k:v.item() for k,v in md.phys(g["torch"].tensor(g["MLAI"][te]),
        g["torch"].tensor(g["MPRI"][te]),g["torch"].tensor(g["MTc"][te]),
        g["torch"].tensor(g["PH"][te]),p[1],p[2])[1].items()}
    thetas.append(th)
thdf=pd.DataFrame(thetas); thdf.to_csv(DATA+r"\07b_集成parameter样本.csv",index=False,encoding="utf-8-sig")

# ---- Fig8 correlation heatmap ----
div=LinearSegmentedColormap.from_list("mor",["#8E9AAB","#F2F0EC","#B99C94"])
fig,ax=plt.subplots(figsize=(9.5,8))
im=ax.imshow(cm.values,cmap=div,vmin=-1,vmax=1)
ax.set_xticks(range(len(cm.columns))); ax.set_xticklabels(cm.columns,rotation=60,
    ha="right",fontsize=8); ax.set_yticks(range(len(cm.index))); ax.set_yticklabels(cm.index,fontsize=8)
for i in range(len(cm.index)):
    for j in range(len(cm.columns)):
        v=cm.values[i,j]
        ax.text(j,i,f"{v:.2f}",ha="center",va="center",fontsize=6.3,
            color="#3a3a3a" if abs(v)<.7 else "white")
cb=fig.colorbar(im,ax=ax,fraction=.046,pad=.04); cb.set_label("Pearson r")
ax.set_title("Correlation among key predictors and yield",fontsize=11)
fig.tight_layout(); SF(fig,"Fig8_相关性热力Figure")

# ---- Fig9 posterior violin ----
items=[("Topt","Opt. canopy temp. (°C)"),("PHopt","Opt. soil pH"),
       ("LAIopt","Opt. LAI (m$^2$ m$^{-2}$)")]
fig,axes=plt.subplots(1,3,figsize=(9.5,3.6))
for ax,(p,lab) in zip(axes,items):
    d=thdf[p].values
    parts=ax.violinplot(d,positions=[0],showmedians=True,showextrema=True,widths=.8)
    for k,pc in enumerate(parts["bodies"]): pc.set_facecolor(MOR[5]); pc.set_alpha(.7)
    for k in ["cmins","cmaxes","cmedians","cbars"]:
        if k in parts: parts[k].set_color("#6b6b6b"); parts[k].set_linewidth(1)
    ax.scatter(np.zeros(len(d))+np.random.uniform(-.06,.06,len(d)),d,color=MOR[3],s=12,zorder=3)
    ax.set_xticks([]); ax.set_xlabel(lab); ax.grid(axis="x",visible=False)
fig.tight_layout(); SF(fig,"Fig9_parameter后验小提琴")

# ---- Fig6 Danzhou with conformal band ----
gg=cal[(cal.regime=="S_LOCO")&(cal.county=="Danzhou")].sort_values("year")
fig,ax=plt.subplots(figsize=(7.6,4.2))
ax.fill_between(gg.year,gg.lo_conformal,gg.hi_conformal,color=MOR[0],alpha=.22,
    label="Conformal 95% interval")
ax.fill_between(gg.year,gg.lo,gg.hi,color=MOR[5],alpha=.18,label="Epistemic 95% interval")
ax.plot(gg.year,gg.pred_total,color=MOR[5],lw=1.8,marker="o",ms=4,label="BPINN prediction")
ax.plot(gg.year,gg.true_total,color=MOR[3],lw=1.8,marker="s",ms=4,label="Observed")
ax.set_xlabel("Year"); ax.set_ylabel("Danzhou rubber total (t)")
ax.legend(frameon=False,fontsize=8.5,ncol=2,loc="upper left")
fig.tight_layout(); SF(fig,"Fig6_Danzhou不确定性时间序列")

# ---- Fig7 robustness with error bars ----
fig,ax=plt.subplots(figsize=(7,4.2))
for i,md in enumerate(["ElasticNet","RandomForest","XGBoost","LightGBM","BPINN"]):
    s=c8[c8.model==md]; base=float(s[s.cond=="clean"].RMSE_mean.iloc[0])
    ns=s[s.cond=="noise"]
    chg=np.array([(float(r.RMSE_mean)/base-1)*100 for _,r in ns.iterrows()])
    sd =np.array([(float(r.RMSE_sd)/base)*100 for _,r in ns.iterrows()])
    kk=ns.k.values
    ax.errorbar(kk,chg,yerr=sd,marker="o",color=MOR[i],lw=1.6,ms=5,
        capsize=3,label=md)
ax.axhline(0,color="#8a8a8a",lw=.9,ls="--")
ax.set_xlabel("Perturbation level $k$ ($\\sigma=k\\,s$)")
ax.set_ylabel("RMSE change (%)  [positive = worse]")
ax.legend(frameon=False,fontsize=8.6)
fig.tight_layout(); SF(fig,"Fig7_噪声鲁棒性")
print("完成。新增/改进Figure：Fig8,Fig9,Fig6,Fig7（均withPDF）")
