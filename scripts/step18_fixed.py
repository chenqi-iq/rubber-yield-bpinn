# -*- coding: utf-8 -*-
"""
第18step：出版级figure（PNG + 矢量PDF；Morandi色盲友好；英文标注；字号8-9pt）。
 Fig1 性能对比(点R2 + 自助95%CI + n)；Fig2 BPINN hexbin密度scatter(1:1, R2/RMSE)；
 Fig3 parameter后验森林Figure；Fig4 parameter后验小提琴(with prior feasible range/均值/95)；
 Fig5 Danzhou区间(无泄漏共形 + 认知)；Fig6 鲁棒性(均值±SD, 正=degraded)；
 Fig7 相关性热力Figure；FigS1 消融(补充材料)。
"""
import os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.edgecolor":"#5a5a5a",
    "axes.linewidth":.7,"figure.dpi":130,"xtick.labelsize":8,"ytick.labelsize":8})
# 学 CSGRN：ranking 6色 + 中性灰baseline + BPINN深靛蓝（突出所提模型）
MOR=["#C05A4A","#7FA56A","#5E86A6","#8C7CA8","#63A39E","#D9A24C","#9E9A92","#B8B4AC","#454C96"]
DATA=r"E:\海南\橡胶产量建模_结果\数据"; FIG=r"E:\海南\橡胶产量建模_结果\figure"
b06=pd.read_csv(DATA+r"\06_基线预测明细.csv")
g16=pd.read_csv(DATA+r"\16g_物理消融_逐行明细.csv")
c16=pd.read_csv(DATA+r"\16b_无泄漏共形_明细.csv")
post=pd.read_csv(DATA+r"\07_物理参数后验.csv")
th=pd.read_csv(DATA+r"\07b_集成参数样本.csv")
d17=pd.read_csv(DATA+r"\17d_鲁棒性均值SD.csv")
cm=pd.read_csv(DATA+r"\12b_关键变量相关矩阵.csv",index_col=0)
det07=pd.read_csv(DATA+r"\07_PINN预测明细.csv")
abl=pd.read_csv(DATA+r"\16e_消融_物理.csv")
seq=LinearSegmentedColormap.from_list("seq",["#F4F7FB","#A9B6D6","#454C96"])
div=LinearSegmentedColormap.from_list("div",["#454C96","#F7F7F7","#C05A4A"])
def SF(fig,name):
    fig.savefig(os.path.join(FIG,name+".png"),dpi=600,bbox_inches="tight")
    fig.savefig(os.path.join(FIG,name+".pdf"),bbox_inches="tight"); plt.close()
def R2(yt,yp):
    return 1-((yt-yp)**2).sum()/((yt-yt.mean())**2).sum()
def boot_ci(df,col,true="true",B=1000,seed=0):
    rng=np.random.default_rng(seed); yt=df[true].values; yp=df[col].values; n=len(df); out=[]
    for _ in range(B):
        ix=rng.integers(0,n,n); out.append(R2(yt[ix],yp[ix]))
    return R2(yt,yp), np.percentile(out,2.5), np.percentile(out,97.5)

regmap=[("S_LOCO","Spatial LOCO"),("T_EndHoldout","Temporal hold-out"),("ST_Blocked","Spatiotemporal block")]
mdl_order=["ElasticNet","RandomForest","XGBoost","LightGBM","SVR","KNN","Persistence","Climatology","BPINN"]
# ---- Fig1 performance with CI ----
fig,ax=plt.subplots(figsize=(8.6,4.4)); x=np.arange(3); w=.095
for mi,md in enumerate(mdl_order):
    pts=[]; lo=[]; hi=[]
    for rk,_ in regmap:
        base=b06[b06.regime==rk].copy()
        if md!="BPINN":
            df=base.rename(columns={"true":"true"}); col=md
        else:
            gf=g16[(g16.regime==dict(regmap)[rk])&(g16.variant=="Full")][["county","year","pred_total"]]
            df=base.merge(gf,on=["county","year"]); df=df.rename(columns={"pred_total":"BPINN"}); col="BPINN"
        p,l,h=boot_ci(df,col,seed=mi)
        pts.append(p); lo.append(p-l); hi.append(h-p)
    ax.bar(x+(mi-4)*w,pts,w,color=MOR[mi%len(MOR)],label=md,
        yerr=[lo,hi],error_kw=dict(ecolor="#555",elinewidth=.6,capsize=1.5))
ax.axhline(0,color="#888",lw=.7); ax.set_xticks(x)
ax.set_xticklabels([rn for _,rn in regmap]); ax.set_ylabel("$R^2$ (pooled; bars show bootstrap 95% CI)")
ax.legend(ncol=5,frameon=False,fontsize=7,loc="lower center",bbox_to_anchor=(.5,-.32))
for xi,(_,rn) in enumerate(regmap):
    n=len(b06[b06.regime==regmap[xi][0]]); ax.text(xi,ax.get_ylim()[1]*.96,f"n={n}",ha="center",fontsize=7.5)
SF(fig,"Fig1_性能对比_withCI")

# ---- Fig2 hexbin ----
fig,axes=plt.subplots(1,3,figsize=(10.5,3.5))
for ax,(rk,rn) in zip(axes,regmap):
    gf=g16[(g16.regime==rn)&(g16.variant=="Full")]
    yt=gf.true_total.values; yp=gf.pred_total.values
    hb=ax.hexbin(yt,yp,gridsize=26,cmap=seq,mincnt=1,linewidths=.2)
    cb=fig.colorbar(hb,ax=ax,fraction=.046,pad=.04); cb.set_label("count",fontsize=7); cb.ax.tick_params(labelsize=6.5)
    lim=np.nanmax([yt,yp]); ax.plot([0,lim],[0,lim],color="#8a8a8a",lw=.8,ls="--")
    rmse=np.sqrt(((yt-yp)**2).mean())
    ax.text(.05,.92,f"$R^2$={R2(yt,yp):.3f}\nRMSE={rmse:,.0f} t",transform=ax.transAxes,
        fontsize=7.5,va="top"); ax.set_title(rn,fontsize=9)
    ax.set_xlabel("Observed (t)"); 
axes[0].set_ylabel("Predicted (t)")
fig.tight_layout(); SF(fig,"Fig2_预测hexbin")

# ---- Fig3 forest (separate x-scale per parameter) ----
pt=post[post.regime=="T_EndHoldout"].set_index("param")
items=[("Topt","Opt. canopy temp. (°C)"),("PHopt","Opt. soil pH"),("LAIopt","Opt. LAI (m$^2$ m$^{-2}$)")]
fig,axes=plt.subplots(1,3,figsize=(9.6,2.0))
for ax,(p,lab) in zip(axes,items):
    r=pt.loc[p]
    ax.errorbar(r["mean"],0,xerr=[[r["mean"]-r.lo],[r.hi-r["mean"]]],fmt="o",color=MOR[5],
        ecolor=MOR[5],capsize=4,ms=7)
    pad=(r.hi-r.lo)*1.6+1e-3
    ax.set_xlim(r.lo-pad,r.hi+pad); ax.set_yticks([]); ax.set_title(lab,fontsize=8.5)
    ax.text(.5,-.42,f"{r['mean']:.2f} [{r.lo:.2f}, {r.hi:.2f}]",transform=ax.transAxes,
        ha="center",fontsize=8); ax.text(.5,1.12,f"prior feasible {dict([('Topt','[20,32]'),('PHopt','[4.5,6]'),('LAIopt','[2,7]')])[p]}",
        transform=ax.transAxes,ha="center",fontsize=6.5,color="#777"); ax.grid(axis="x",ls=":",lw=.5)
fig.tight_layout(); SF(fig,"Fig3_parameter后验森林Figure")

# ---- Fig4 violin with prior band ----
fig,axes=plt.subplots(1,3,figsize=(9.5,3.4))
specs=[("Topt","Opt. canopy temp. (°C)",(20,32)),("PHopt","Opt. soil pH",(4.5,6)),
       ("LAIopt","Opt. LAI",(2,7))]
for ax,(p,lab,prior) in zip(axes,specs):
    d=th[p].values
    ax.axvspan(prior[0],prior[1],color=MOR[7],alpha=.25,zorder=0)
    parts=ax.violinplot(d,positions=[0],showmedians=True,widths=.8)
    for pc in parts["bodies"]: pc.set_facecolor(MOR[5]); pc.set_alpha(.75)
    for k in ["cmins","cmaxes","cmedians","cbars"]: parts[k].set_color("#5a5a5a")
    ax.boxplot(d,positions=[0],widths=.12,showfliers=False,patch_artist=True,
        boxprops=dict(facecolor="white",color="#3a3a3a",linewidth=.8),
        medianprops=dict(color="#3a3a3a",linewidth=.9),whiskerprops=dict(color="#3a3a3a",linewidth=.8),
        capprops=dict(color="#3a3a3a",linewidth=.8),zorder=4)
    ax.scatter(np.zeros(len(d))+np.random.uniform(-.06,.06,len(d)),d,color=MOR[3],s=10,zorder=3)
    ax.set_xticks([]); ax.set_xlabel(f"{lab}\nmean {d.mean():.2f}; 95% {np.percentile(d,2.5):.2f}–{np.percentile(d,97.5):.2f}",fontsize=8)
fig.tight_layout(); SF(fig,"Fig4_parameter后验小提琴")

# ---- Fig5 Danzhou ----
gg=c16[(c16.regime=="Spatial LOCO")&(c16.county=="Danzhou")].sort_values("year")
ep=det07[(det07.regime=="S_LOCO")&(det07.county=="Danzhou")].sort_values("year")
fig,ax=plt.subplots(figsize=(7.6,4.2))
ax.fill_between(gg.year,gg.lo,gg.hi,color=MOR[0],alpha=.22,label="Leakage-free conformal 95%")
ax.fill_between(ep.year,ep.lo,ep.hi,color=MOR[5],alpha=.18,label="Epistemic 95%")
ax.plot(gg.year,gg.pred_total,color=MOR[5],lw=1.7,marker="o",ms=3.5,label="BPINN")
ax.plot(gg.year,gg.true_total,color=MOR[3],lw=1.7,marker="s",ms=3.5,label="Observed")
ax.annotate("2022 low",xy=(2022,gg[gg.year==2022].true_total.iloc[0]),
    xytext=(2018.3,28000),fontsize=7.5,arrowprops=dict(arrowstyle="->",lw=.7))
ax.set_xlabel("Year"); ax.set_ylabel("Danzhou rubber total (t)")
ax.legend(frameon=False,fontsize=8,ncol=2,loc="upper left")
fig.tight_layout(); SF(fig,"Fig5_Danzhou区间")

# ---- Fig6 robustness mean±SD ----
fig,ax=plt.subplots(figsize=(7.4,4.2))
for i,md in enumerate(["ElasticNet","RandomForest","XGBoost","LightGBM","BPINN"]):
    s=d17[d17.model==md].sort_values("k")
    ax.errorbar(s.k,s["RMSE_change_%"],yerr=s["RMSE_change_SD%"],marker="o",color=MOR[i],
        lw=1.5,ms=4.5,capsize=2.5,label=md)
ax.axhline(0,color="#8a8a8a",lw=.8,ls="--")
ax.set_xlabel("Perturbation $k$ ($\\sigma=k\\,s$)"); ax.set_ylabel("RMSE change (%) [positive = worse]")
ax.legend(frameon=False,fontsize=8)
fig.tight_layout(); SF(fig,"Fig6_鲁棒性_误差棒")

# ---- Fig7 correlation heatmap (clustered + significance) ----
from scipy.stats import pearsonr
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import squareform
mm=pd.read_csv(DATA+r"\05_主表_年度面板.csv")
ccols=['yield','area_total','area_new','area_harvest','post_reform','ph_top','om_top','LAI_ann_max',
 'LAI_tapping','NDVI_ann_max','NDVI_tapping','PRI_ann_min','PRI_tapping','Tc_summer_max',
 'Tc_winter_min','Recover_NDVI','LowTemp_Recovery']
clab=['yield','area_total','area_new','area_harvest','post_reform','pH','SOM','LAI_annmax','LAI_tap',
 'NDVI_annmax','NDVI_tap','PRI_annmin','PRI_tap','Tc_summax','Tc_winmin','Recover_NDVI','LowTemp_Rec']
D2=mm[ccols].dropna(); kk=len(ccols); R=np.zeros((kk,kk)); P=np.ones((kk,kk))
for i in range(kk):
    for j in range(kk):
        if i!=j:
            R[i,j],P[i,j]=pearsonr(D2[ccols[i]],D2[ccols[j]])
dist=1-np.abs(R); np.fill_diagonal(dist,0)
ordr=leaves_list(linkage(squareform(dist),method="average"))
R2=R[np.ix_(ordr,ordr)]; P2=P[np.ix_(ordr,ordr)]; labs2=[clab[i] for i in ordr]
fig,ax=plt.subplots(figsize=(9.8,8.4))
im=ax.imshow(R2,cmap=div,vmin=-1,vmax=1)
ax.set_xticks(range(kk)); ax.set_xticklabels(labs2,rotation=60,ha="right",fontsize=7.5)
ax.set_yticks(range(kk)); ax.set_yticklabels(labs2,fontsize=7.5)
for i in range(kk):
    for j in range(kk):
        if i!=j:
            star="**" if P2[i,j]<.01 else ("*" if P2[i,j]<.05 else "")
            ax.text(j,i,f"{R2[i,j]:.2f}{star}",ha="center",va="center",fontsize=6.3,
                color="#3a3a3a" if abs(R2[i,j])<.7 else "white")
cb=fig.colorbar(im,ax=ax,fraction=.046,pad=.04); cb.set_label("Pearson r (* p<.05, ** p<.01)")
fig.tight_layout(); SF(fig,"Fig7_相关性热力Figure")

# ---- FigS1 ablation (supplement) ----
fig,axes=plt.subplots(1,3,figsize=(10,3.4))
for ax,(rn,title) in zip(axes,[("Spatial LOCO","Spatial LOCO"),("Temporal hold-out","Temporal hold-out"),("Spatiotemporal block","Spatiotemporal block")]):
    s=abl[abl.regime==rn].set_index("variant").reindex(["NN-only","Physics-only","Full"])
    ax.bar(range(3),s.R2.values,color=[MOR[2],MOR[1],MOR[0]])
    ax.set_xticks(range(3)); ax.set_xticklabels(["NN-only","Physics-only","Full"],rotation=20,fontsize=7.5)
    ax.set_title(title,fontsize=8.5); ax.set_ylabel("$R^2$")
fig.tight_layout(); SF(fig,"FigS1_消融_补充")
print("出版级figure完成：Fig1-7 + FigS1（均with600dpi PNG与矢量PDF）")


