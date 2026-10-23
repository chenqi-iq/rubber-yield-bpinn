# -*- coding: utf-8 -*-
"""
第16步(v2)：无泄漏共形校准 + 公平消融（真实计算；修复泄漏、混淆与逐折R2错误）。
无泄漏共形：校准集严格不含测试县/测试年（见下）。
公平消融：固定测试/特征、报告n；物理消融的指标在【跨折池化】后计算（不在单县内算R2）。
输出：
 16a 无泄漏共形覆盖率；16b 无泄漏共形明细；
 16c 数据长度；16d 特征消融；16e 物理消融(池化)；
 16f 空间逐市县预测；16g 物理消融_逐行预测明细。
"""
import os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, torch
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from xgboost import XGBRegressor
DATA=r"E:\海南\橡胶产量建模_结果\数据"
src=open(r"E:\海南\橡胶产量建模_结果\代码\step7_改进PINN_BPINN.py",encoding="utf-8").read()
g={"__name__":"x"}; exec(src.split("idx=np.arange(len(m))")[0],g)
m=g["m"]; PINN=g["PINN"]; scale_fit=g["scale_fit"]
MLAI,MPRI,MTc=g["MLAI"],g["MPRI"],g["MTc"]; PH=g["PH"]; AREA=g["AREA"]
INT=g["INT"]; Y=g["Y"]; Xann=g["Xann"]; XCOLS=g["XCOLS"]
idx=np.arange(len(m)); years=m.year.values; counties=m.county.values
ANNCOLS=["area_total","area_new","area_harvest","post_reform","ph_top","om_top"]+\
        [c for c in XCOLS if "ann_" in c]
# 池化预测累积：ACC[regime][mode] -> list of DataFrame(true_total,pred_total)
ACC={"Spatial LOCO":{k:[] for k in ["full","phys","nn"]},
     "Spatiotemporal block":{k:[] for k in ["full","phys","nn"]},
     "Temporal hold-out":{k:[] for k in ["full","phys","nn"]}}

def q95(r):
    n=len(r); a=min(np.ceil((n+1)*.95)/n,1.0); return np.quantile(np.abs(r),a)
def Mtot(yt,yp):
    yt=np.asarray(yt,float); yp=np.asarray(yp,float); ss=((yt-yt.mean())**2).sum()
    return dict(R2=1-((yt-yp)**2).sum()/ss if ss>0 else np.nan,
        RMSE=np.sqrt(((yt-yp)**2).mean()), MAE=np.abs(yt-yp).mean(),
        MAPE=np.abs((yt-yp)/yt).mean()*100)
def train_mode(tr,seed,mode,epochs=260):
    torch.manual_seed(seed); model=PINN(); params=scale_fit(tr)
    xs,pri_mu,pri_sd,t_mu,t_sd=params
    opt=torch.optim.Adam(model.parameters(),lr=.02)
    sch=torch.optim.lr_scheduler.StepLR(opt,120,gamma=.5)
    X=torch.tensor(xs(Xann[tr])); lai=torch.tensor(MLAI[tr]); pri=torch.tensor(MPRI[tr])
    tc=torch.tensor(MTc[tr]); ph=torch.tensor(PH[tr]); tgt=torch.tensor(INT[tr])
    ww=torch.tensor(AREA[tr]/AREA[tr].mean())
    for ep in range(epochs):
        yphys=model.phys(lai,pri,tc,ph,pri_mu,pri_sd)[0]
        d=model.net(X).squeeze(1); nn=d*t_sd; full=yphys+nn
        if mode=="full": loss=((ww*(full-tgt))**2).mean()+.05*(d**2).mean()
        elif mode=="phys": loss=((ww*(yphys-tgt))**2).mean()
        else: loss=((ww*(nn-tgt))**2).mean()
        opt.zero_grad(); loss.backward(); opt.step(); sch.step()
    return model,params
def eval_outs(model,te,params):
    xs,pri_mu,pri_sd,t_mu,t_sd=params
    X=torch.tensor(xs(Xann[te])); lai=torch.tensor(MLAI[te]); pri=torch.tensor(MPRI[te])
    tc=torch.tensor(MTc[te]); ph=torch.tensor(PH[te]); model.eval()
    with torch.no_grad():
        yphys=model.phys(lai,pri,tc,ph,pri_mu,pri_sd)[0]
        d=model.net(X).squeeze(1); nn=d*t_sd
    return (yphys+nn).numpy(), yphys.numpy(), nn.numpy()
def accumulate(rg,te,outs):
    base=pd.DataFrame({"county":counties[te],"year":years[te],"true_total":Y[te]})
    for mode,oi in [("full",0),("phys",1),("nn",2)]:
        f=base.copy(); f["pred_total"]=outs[mode][oi]*AREA[te]
        ACC[rg][mode].append(f)

# ===== Spatial LOCO =====
print("Spatial LOCO ..."); S_pool=[]; S_county_pred=[]
for c in sorted(set(counties)):
    tr=idx[counties!=c]; te=idx[counties==c]
    models={mode:train_mode(tr,seed={"full":7,"phys":17,"nn":27}[mode],mode=mode) for mode in ["full","phys","nn"]}
    outs={mode:eval_outs(models[mode][0],te,models[mode][1]) for mode in models}
    accumulate("Spatial LOCO",te,outs)
    fi=outs["full"][0]
    S_pool.append(pd.DataFrame({"county":counties[te],"resid":fi-INT[te]}))
    S_county_pred.append(pd.DataFrame({"county":counties[te],"year":years[te],
        "pred_intensity":fi,"true_intensity":INT[te]}))
S_pool=pd.concat(S_pool,ignore_index=True)
pd.concat(S_county_pred).to_csv(DATA+r"\16f_空间逐市县预测.csv",index=False,encoding="utf-8-sig")

# ===== Spatiotemporal block =====
print("Spatiotemporal block ..."); ST_pool=[]; ST_county_pred=[]
for c in sorted(set(counties)):
    tr=idx[(counties!=c)&(years<=2020)]; te=idx[(counties==c)&(years>=2021)]; cal_i=idx[(counties==c)&(years<=2020)]
    models={mode:train_mode(tr,seed={"full":37,"phys":47,"nn":57}[mode],mode=mode) for mode in ["full","phys","nn"]}
    outs={mode:eval_outs(models[mode][0],te,models[mode][1]) for mode in models}
    accumulate("Spatiotemporal block",te,outs)
    cf=eval_outs(models["full"][0],cal_i,models["full"][1])[0]
    ST_pool.append(pd.DataFrame({"county":counties[cal_i],"resid":cf-INT[cal_i]}))
    ST_county_pred.append(pd.DataFrame({"county":counties[te],"year":years[te],
        "pred_intensity":outs["full"][0],"true_intensity":INT[te]}))
ST_pool=pd.concat(ST_pool,ignore_index=True)

# ===== Temporal =====
print("Temporal hold-out ...")
tr=idx[years<=2020]; te=idx[years>=2021]
T_models={mode:train_mode(tr,seed={"full":67,"phys":77,"nn":87}[mode],mode=mode) for mode in ["full","phys","nn"]}
T_outs={mode:eval_outs(T_models[mode][0],te,T_models[mode][1]) for mode in T_models}
accumulate("Temporal hold-out",te,T_outs)

# ===== 物理消融：跨折池化后计算 =====
phys_rows=[]; detail_frames=[]
name_map={"full":"Full","phys":"Physics-only","nn":"NN-only"}
for rg in ACC:
    for mode in ["full","phys","nn"]:
        f=pd.concat(ACC[rg][mode],ignore_index=True)
        f["regime"]=rg; f["variant"]=name_map[mode]; detail_frames.append(f)
        mt=Mtot(f.true_total,f.pred_total)
        phys_rows.append({"regime":rg,"variant":name_map[mode],"n":len(f),**mt})
phys_abl=pd.DataFrame(phys_rows)
phys_abl.to_csv(DATA+r"\16e_消融_物理.csv",index=False,encoding="utf-8-sig")
pd.concat(detail_frames).to_csv(DATA+r"\16g_物理消融_逐行明细.csv",index=False,encoding="utf-8-sig")
print("\n物理消融（跨折池化）："); print(phys_abl.round(3).to_string(index=False))

# ===== 无泄漏共形 =====
conf=[]
# Spatial：q 排除测试县
for c in sorted(set(counties)):
    te=idx[counties==c]; q=q95(S_pool[S_pool.county!=c].resid.values)
    pi=pd.concat(S_county_pred); pi=pi[pi.county==c].sort_values("year"); pv=pi.pred_intensity.values; area=AREA[te]
    conf.append(pd.DataFrame({"county":counties[te],"year":years[te],"regime":"Spatial LOCO",
        "true_total":Y[te],"pred_total":pv*area,"lo":(pv-q)*area,"hi":(pv+q)*area}))
# ST：q 排除测试县（池内已全<=2020）
for c in sorted(set(counties)):
    te=idx[(counties==c)&(years>=2021)]; q=q95(ST_pool[ST_pool.county!=c].resid.values)
    pi=pd.concat(ST_county_pred); pi=pi[pi.county==c].sort_values("year"); pv=pi.pred_intensity.values; area=AREA[te]
    conf.append(pd.DataFrame({"county":counties[te],"year":years[te],"regime":"Spatiotemporal block",
        "true_total":Y[te],"pred_total":pv*area,"lo":(pv-q)*area,"hi":(pv+q)*area}))
# Temporal split-conformal
tr0=idx[years<=2018]; cal=idx[(years>=2019)&(years<=2020)]; teT=idx[years>=2021]
m0,p0=train_mode(tr0,seed=42,mode="full")
r_cal=eval_outs(m0,cal,p0)[0]-INT[cal]; qt=q95(r_cal)
pv=T_outs["full"][0]
conf.append(pd.DataFrame({"county":counties[teT],"year":years[teT],"regime":"Temporal hold-out",
    "true_total":Y[teT],"pred_total":pv*AREA[teT],"lo":(pv-qt)*AREA[teT],"hi":(pv+qt)*AREA[teT]}))
conf=pd.concat(conf,ignore_index=True)
summ=[]
for rg,g0 in conf.groupby("regime"):
    inside=((g0.true_total>=g0.lo)&(g0.true_total<=g0.hi)).mean()
    w=(g0.hi-g0.lo); rng=g0.true_total.max()-g0.true_total.min()
    summ.append({"regime":rg,"n":len(g0),"PICP95":inside,"MPIW":w.mean(),"NMPIW":w.mean()/rng})
summ=pd.DataFrame(summ)
summ.to_csv(DATA+r"\16a_无泄漏共形_覆盖率.csv",index=False,encoding="utf-8-sig")
conf.to_csv(DATA+r"\16b_无泄漏共形_明细.csv",index=False,encoding="utf-8-sig")
print("\n无泄漏共形覆盖率："); print(summ.round(3).to_string(index=False))

# ===== E1 数据长度（Temporal, 年度特征） =====
def sk_learners():
    return {"ElasticNet":ElasticNet(alpha=.03,l1_ratio=.2,max_iter=5000),
            "XGBoost":XGBRegressor(n_estimators=400,learning_rate=.03,max_depth=4,subsample=.8,
                colsample_bytree=.8,min_child_weight=3,random_state=1,n_jobs=-1,verbosity=0)}
te=idx[years>=2021]; yte=Y[te]
windows={"last5 (2016-20)":idx[(years>=2016)&(years<=2020)],
         "last10 (2011-20)":idx[(years>=2011)&(years<=2020)],
         "all (2010-20)":idx[years<=2020]}
rows=[]
for wn,wi in windows.items():
    Xtr=m.loc[wi,ANNCOLS].values; Xte_=m.loc[te,ANNCOLS].values; sc=StandardScaler().fit(Xtr)
    for ln,mdl in sk_learners().items():
        mdl.fit(sc.transform(Xtr),Y[wi]); rows.append({"window":wn,"n_train":len(wi),"learner":ln,**Mtot(yte,mdl.predict(sc.transform(Xte_)))})
pd.DataFrame(rows).to_csv(DATA+r"\16c_消融_数据长度.csv",index=False,encoding="utf-8-sig")
print("\n数据长度："); print(pd.DataFrame(rows).round(3).to_string(index=False))

# ===== E2 特征消融 =====
def feat_folds(kind):
    if kind=="T": return [(idx[years<=2020],idx[years>=2021])]
    if kind=="S": return [(idx[counties!=c],idx[counties==c]) for c in sorted(set(counties))]
    return [(idx[(counties!=c)&(years<=2020)],idx[(counties==c)&(years>=2021)]) for c in sorted(set(counties))]
rows=[]
for kind,rn in [("T","Temporal hold-out"),("S","Spatial LOCO"),("ST","Spatiotemporal block")]:
    for fset,fn in [(ANNCOLS,"Annual only"),(XCOLS,"Annual + monthly phenology")]:
        pred_by={ln:[] for ln in sk_learners()}; trues=[]
        for trf,tef in feat_folds(kind):
            Xtr=m.loc[trf,fset].values; Xte_=m.loc[tef,fset].values; sc=StandardScaler().fit(Xtr)
            for ln,mdl in sk_learners().items():
                mdl.fit(sc.transform(Xtr),Y[trf]); pred_by[ln].append(mdl.predict(sc.transform(Xte_)))
            trues.append(Y[tef])
        T=np.concatenate(trues)
        for ln in pred_by:
            P=np.concatenate(pred_by[ln]); rows.append({"regime":rn,"features":fn,"learner":ln,"n":len(T),**Mtot(T,P)})
pd.DataFrame(rows).to_csv(DATA+r"\16d_消融_特征.csv",index=False,encoding="utf-8-sig")
print("\n特征消融："); print(pd.DataFrame(rows).round(3).to_string(index=False))
print("\n第16步(v2)完成。")
