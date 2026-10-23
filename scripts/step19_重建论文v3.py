# -*- coding: utf-8 -*-
"""
第19步：重建论文 v3（中文；修复P0/P1硬核项）。所有数字取自 step16-18 最终CSV。
生成：修订版论文_SCI规范_v3.docx
"""
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
DATA=r"E:\海南\橡胶产量建模_结果\数据"; FIG=r"E:\海南\橡胶产量建模_结果\图表"; ROOT=r"E:\海南\橡胶产量建模_结果"
b06=pd.read_csv(DATA+r"\06_模型对比_各regime.csv")
c16a=pd.read_csv(DATA+r"\16a_无泄漏共形_覆盖率.csv")
abl_phys=pd.read_csv(DATA+r"\16e_消融_物理.csv")
abl_feat=pd.read_csv(DATA+r"\16d_消融_特征.csv")
abl_len=pd.read_csv(DATA+r"\16c_消融_数据长度.csv")
post=pd.read_csv(DATA+r"\07_物理参数后验.csv")
d12=pd.read_csv(DATA+r"\12d_区间校准PICP_MPIW.csv")
p17a=pd.read_csv(DATA+r"\17a_市县配对鲁棒性.csv")
p17e=pd.read_csv(DATA+r"\17e_配对dz_CI.csv")

d=Document()
st=d.styles["Normal"]; st.font.name="Arial"; st.font.size=Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"),"宋体")
st.paragraph_format.line_spacing=1.5
for nm,sz in [("Heading 1",15),("Heading 2",13),("Heading 3",12)]:
    s=d.styles[nm]; s.font.size=Pt(sz); s.font.bold=True; s.font.color.rgb=RGBColor(0,0,0)
    s.font.name="Arial"; s.element.rPr.rFonts.set(qn("w:eastAsia"),"黑体")
for sec in d.sections:
    sec.top_margin=Cm(2.5); sec.bottom_margin=Cm(2.5); sec.left_margin=Cm(2.5); sec.right_margin=Cm(2.5)
def H(t,l=1):
    h=d.add_heading(t,level=l); h.paragraph_format.space_before=Pt(10); h.paragraph_format.space_after=Pt(5)
def P(t,indent=True,bold=False,align=None,size=12):
    p=d.add_paragraph(); r=p.add_run(t); r.bold=bold; r.font.size=Pt(size); r.font.name="Arial"
    r._element.rPr.rFonts.set(qn("w:eastAsia"),"宋体")
    if indent: p.paragraph_format.first_line_indent=Pt(24)
    if align: p.alignment=align
def CAP(t):
    p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(t); r.font.size=Pt(10.5); r.font.name="Arial"; r._element.rPr.rFonts.set(qn("w:eastAsia"),"宋体")
    p.paragraph_format.space_after=Pt(6)
def FIGP(path,w=15.5):
    d.add_picture(path,width=Cm(w)); d.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
def _b(cell):
    tcPr=cell._tc.get_or_add_tcPr(); b=OxmlElement("w:tcBorders")
    for e in ["top","bottom"]:
        el=OxmlElement(f"w:{e}"); el.set(qn("w:val"),"single"); el.set(qn("w:sz"),"10"); el.set(qn("w:color"),"555555"); b.append(el)
    tcPr.append(b)
def TBL(headers,rows,note=None,small=9.5):
    t=d.add_table(rows=1,cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; hc=t.rows[0].cells
    for i,h in enumerate(headers):
        hc[i].text=""; pr=hc[i].paragraphs[0]; pr.alignment=WD_ALIGN_PARAGRAPH.CENTER
        run=pr.add_run(str(h)); run.bold=True; run.font.size=Pt(small); run.font.name="Arial"
        run._element.rPr.rFonts.set(qn("w:eastAsia"),"宋体"); _b(hc[i])
        sh=OxmlElement("w:shd"); sh.set(qn("w:fill"),"F4F4F4"); hc[i]._tc.get_or_add_tcPr().append(sh)
    for ri,row in enumerate(rows):
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=""; pr=cells[i].paragraphs[0]; pr.alignment=WD_ALIGN_PARAGRAPH.CENTER
            run=pr.add_run(str(v)); run.font.size=Pt(small); run.font.name="Arial"
            run._element.rPr.rFonts.set(qn("w:eastAsia"),"宋体")
            if ri==len(rows)-1: _b(cells[i])
    if note: CAP(note)

# ===== 封面 =====
p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run("多源遥感融合贝叶斯物理信息神经网络的海南岛橡胶产量估测")
r.bold=True; r.font.size=Pt(17); r.font.name="Arial"; r._element.rPr.rFonts.set(qn("w:eastAsia"),"黑体")
P("作者：【请填写】    单位：【请填写】    通信作者邮箱：【请填写】",indent=False,align=WD_ALIGN_PARAGRAPH.CENTER,size=10.5)

H("研究亮点（Highlights）")
for s in [
 "● 海南岛18市县2010—2023年真实面板（252市县—年份、3024市县—年—月），统一农垦口径。",
 "● 月度LAI/PRI/冠层温度显式积分碳平衡，含冠层温度热响应与温度依赖维持呼吸。",
 "● 无泄漏共形校准将95%区间覆盖率由6%—14%提升至89%—100%。",
 "● BPINN在空间/时间/时空验证R²为0.882/0.855/0.821，跨场景R²极差0.061。"]:
    P(s,indent=False,size=10.5)

H("摘要")
P("天然橡胶产量统计存在农垦体制改革带来的口径调整，多源遥感与产量之间为非线性关系；以滑动窗口复制年度目标、"
 "并使同一市县相邻年份同时进入训练与验证的评估会系统性偏乐观。本文以海南岛18市县2010—2023年真实面板"
 "（252市县—年份、3024市县—年—月）为基础，融合叶面积指数（LAI）、归一化植被指数（NDVI）、光化学反射"
 "指数（PRI）、冠层温度与HWSD2土壤pH、有机质，构建按月份显式积分的碳平衡模型，以神经网络学习小的单产"
 "残差，并通过MC Dropout与多模型集成实现贝叶斯推断（BPINN）。在空间留一（LOCO）、时间外推（训练≤2020、"
 "测试2021—2023）与时空块验证下，BPINN的R²分别为0.882、0.855和0.821，跨场景R²极差0.061；空间LOCO以"
 "ElasticNet最高（0.911），时间外推以持续性基准最高（0.910）。识别的最适冠层温度28.5 ℃、最适土壤pH 5.43、"
 "最适LAI 3.20，与橡胶喜高温、微酸土壤、中等郁闭林冠的已有研究一致。原始MC Dropout区间覆盖率仅6%—14%"
 "（过度自信）；采用逐折、校准集不含测试县/测试年的无泄漏共形校准后，覆盖率提升至0.952/1.000/0.889（空间/"
 "时间/时空）。按18市县配对，10%输入扰动下BPINN的误差变化不显著（p=0.18，Cohen dz=0.33），而ElasticNet在"
 "5%—10%扰动下显著退化（dz=0.77—1.08）。逐年R²中位0.887，但逐市县R²中位为负，表明模型主要解释市县间差异与"
 "年份共性，对市县特异的年际异常预测能力有限，需纳入极端事件与管理数据。")
P("关键词：橡胶产量；多源遥感；物理信息神经网络；贝叶斯不确定性；冠层温度；LAI；海南岛",indent=False)

H("1 引言")
P("天然橡胶是重要工业原料与战略物资，海南岛是我国天然橡胶主产区。橡胶生长受光照、温度、土壤与林冠结构共同"
 "控制，产量形成具有显著非线性与季节动态。遥感可在区域尺度连续获取植被结构与生理信息，但统计产量存在农垦"
 "体制改革带来的口径调整，遥感—产量关系亦难以用简单线性关系刻画。已有研究常以滑动窗口扩充样本并以留一法"
 "评估，当年度目标被复制到多个重叠窗口、同一市县相邻年份同时进入训练与验证时，评估会系统性偏乐观。本文以"
 "真实市县—年份为独立样本，建立月度显式积分碳平衡模型，引入冠层温度热响应与温度依赖呼吸，以单产为建模"
 "对象，并以MC Dropout、多模型集成与无泄漏共形校准给出可信的贝叶斯区间，在空间、时间、时空三种验证下结合"
 "基线、公平消融与鲁棒性给出诚实评估。")

H("2 研究区与数据")
H("2.1 研究区",2)
P("研究区为海南岛18市县（海口、三亚所辖各区分别合并），属热带季风气候，空间边界采用海南省县界矢量（EPSG:4326）。")
H("2.2 数据来源",2)
TBL(["数据/产品","来源","空间/口径","时间范围","处理与用途"],
 [["橡胶面积与产量","市县热带作物统计（年度出版物）","市县；年末/新种/收获面积、总产量","数据年2009—2023","目标变量"],
  ["土壤pH、有机质","HWSD2（SMU栅格+Access属性库）","30弧秒；按组分SHARE、土层厚度加权","静态背景","土壤特征"],
  ["LAI/NDVI/PRI","月度遥感栅格","市县分区均值","2010—2023逐月","物候+物理驱动"],
  ["冠层温度","月度遥感栅格","市县分区均值(℃)","2010—2023逐月","热响应/呼吸驱动"]],
 note="表1 数据与来源（三线表）")
H("2.3 预处理与口径统一",2)
P("统计文件出版年P对应数据年P−1，覆盖2009—2023，源中不存在2024年实际值。2009—2010年含“地方+农垦”，2011"
 "年起农垦并入市县；本文以2010→2011各县增量占比将农垦分摊回18市县，分摊后全省合计误差为0。HWSD2以PH_WATER、"
 "ORG_CARBON按组分SHARE与土层厚度加权，有机质=有机碳×1.724。四类遥感672个tif无缺失；仅2010越冬期所需2009年12月"
 "（72值）采用线性边界外推；年度新种面积官方空白39处按0处理。")
H("2.4 相关性与多重共线性",2)
P("总产量与收获、年末面积高度相关（r=0.953、0.951），与新种面积及NDVI、LAI年际特征中等相关（约0.40—0.50）。"
 "预测子间存在51对|r|≥0.85高共线（有机质与有机碳完全相关），普通最小二乘系数不稳定，为ElasticNet正则化与特征"
 "精简提供依据。")
FIGP(FIG+r"\Fig7_相关性热力图.png"); CAP("图1 关键预测变量与产量相关矩阵")

H("3 方法")
H("3.1 总体框架",2)
P("模型由月度碳平衡物理路径与神经网络残差路径组成。物理路径在真实单位下由月度LAI、PRI、冠层温度与静态pH计算"
 "总初级生产力GPP与维持呼吸，按月份天数积分得到相对碳累积并转换为单产；神经网络仅学习小的单产残差。最终单产"
 "=物理单产+残差，总产量=单产×收获面积。")
H("3.2 月度物候特征",2)
P("按越冬（上年12—2月）、返青（3—4月）、割胶季（5—11月）、夏季（6—9月）窗口，对四变量计算均值、极值与标准差，"
 "共39个物候特征，连同面积与土壤特征构成年度特征集。")
H("3.3 月度积分碳平衡",2)
P("对月份m：")
P("GPP_m = P0·f_LAI(LAI_m)·f_pH(pH)·f_PRI(PRI_m)·f_T(Tc_m)                 （式1）",indent=False)
P("R_m = η_R·GPP_m·Q10^((Tc_m−25)/10)，Q10=2、参考温度25 ℃                  （式2）",indent=False)
P("f_LAI=exp[−(LAI−LAI_opt)²/(2σ_LAI²)]，f_T=exp[−(Tc−T_opt)²/(2σ_T²)]，"
  "f_pH=exp[−(pH−pH_opt)²/(2σ_pH²)]，f_PRI=clip[1+α_PRI·z(PRI), 0.2, 2.0]。",indent=False)
P("相对碳累积 C = Σ_m d_m(GPP_m−R_m)，d_m为该月天数；物理单产 y_phys=ρ·C（t/ha），其中C为无量纲相对碳量，"
 "ρ单位为t/ha。")
P("说明：σ_LAI、σ_T、σ_pH为【可学习】的容差参数，分别约束在σ_LAI∈[0.5,2.5]、σ_T∈[3,13]、σ_pH∈[0.2,1.2]，"
 "与最适值共同反演；f_PRI的clip[0.2,2.0]将效率乘子限制在0.2—2倍，防止标准化PRI极端值产生非物理的负GPP或发散。")
H("3.4 神经网络残差与耦合",2)
P("神经网络为两层各48单元Tanh网络（每层后Dropout 0.1），输出标准化单产残差δ；预测单产y=y_phys+δ·s_y。损失为：")
P("L = mean_i [ w_i²·(y_i−ŷ_i)² ] + λ_δ·mean_i[δ_i²]，w_i=area_i/mean(area)，λ_δ=0.05。   （式3）",indent=False)
H("3.5 训练设置",2)
P("Adam（lr=0.02），StepLR第120轮γ=0.5，全批量260轮；物理参数经sigmoid/softplus约束：LAI_opt∈[2,7]、pH_opt∈[4.5,6]、"
 "T_opt∈[20,32]、η_R∈[0.1,0.6]；固定随机种子，CPU。")
H("3.6 贝叶斯推断与无泄漏共形校准",2)
P("测试时保持Dropout开启做K=50次前向刻画认知不确定性；时间场景训练12个独立模型集成，汇总参数与预测后验。MC Dropout"
 "仅含认知不确定性、覆盖率过低，故以共形校准按强度残差构造异方差（按面积）加性宽度，且校准集严格不含测试县/测试年：")
TBL(["验证","训练集","校准集","测试集"],
 [["空间LOCO","其他17县（全年份）","其他17县的交叉拟合残差（不含测试县）","测试县全部年份"],
  ["时间外推","≤2018","2019—2020（不参与训练）","2021—2023"],
  ["时空块","其他县且≤2020","其他县且≤2020交叉拟合残差（不含测试县、不含≥2021）","测试县2021—2023"]],
 note="表2 无泄漏共形的训练/校准/测试划分")
P("时间序列不完全满足共形所需的可交换性，在分布漂移下覆盖率保证为近似，本文如实报告经验覆盖率。")
H("3.7 验证设计、对照模型与指标",2)
P("空间LOCO为18折；时间外推训练≤2020、测试2021—2023；时空块为18折。不采用随机5折，因空间自相关会使其偏乐观。"
 "对照：ElasticNet（Ridge L2+Lasso L1组合惩罚的线性回归）、KNN（k近邻平均）、SVR（ε不敏感核回归）、随机森林（袋装"
 "回归树）、XGBoost（二阶梯度提升树）、LightGBM（直方图叶子优先生长提升树），以及气候态与持续性基准。指标R²、RMSE、"
 "MAE、MAPE按测试样本池化。")
H("3.8 鲁棒性与公平消融",2)
P("鲁棒性：对原始输入加σ=k·s（k=0.01/0.05/0.10），仅在固定测试集做B=80次传播。消融均固定测试、报告n：数据长度"
 "（年度特征、固定测试，训练窗last5/last10/all）、特征（年度 vs 年度+月度）、物理（同架构NN-only/Physics-only/Full）。")

H("4 结果")
H("4.1 描述性统计",2)
P("主表252×53无缺失；总产量1655—79311 t，单产0.420—1.905 t/ha（均值0.910），收获面积1830—83741 ha，表土pH "
 "4.68—5.39、有机质2.03—4.33%。月度LAI 0.296—5.367、NDVI 0.308—0.876、PRI −0.087—−0.010、冠层16.95—36.17 ℃。")
H("4.2 基线三种验证",2)
rows=[]; order=["ElasticNet","XGBoost","RandomForest","LightGBM","SVR","KNN","Persistence","Climatology"]
regs=[("S_LOCO","空间LOCO"),("T_EndHoldout","时间外推"),("ST_Blocked","时空块")]
for rk,rn in regs:
    for md in order:
        x=b06[(b06.regime==rk)&(b06.model==md)]
        if len(x): rows.append([rn,md,f"{x.R2.iloc[0]:.3f}",f"{x.RMSE.iloc[0]:,.0f}",f"{x.MAE.iloc[0]:,.0f}",f"{x.MAPE.iloc[0]:.1f}%"])
    g=abl_phys
    x=g[(g.regime==dict([("S_LOCO","Spatial LOCO"),("T_EndHoldout","Temporal hold-out"),("ST_Blocked","Spatiotemporal block")])[rk])&(g.variant=="Full")]
    if len(x): rows.append([rn,"BPINN",f"{x.R2.iloc[0]:.3f}",f"{x.RMSE.iloc[0]:,.0f}","—","—"])
TBL(["验证","模型","R²","RMSE","MAE","MAPE"],rows,note="表3 各模型三种验证指标（池化）",small=9)
FIGP(FIG+r"\Fig1_性能对比_含CI.png"); CAP("图2 R²（误差棒为自助95%CI）")
P("空间LOCO以ElasticNet最高（0.911），灵活树跨空间下降；时间外推以持续性最强（0.910）；时空块BPINN（0.821）与"
 "ElasticNet接近、高于灵活树。可迁移结构比模型灵活性更重要。")
H("4.3 BPINN估测",2)
FIGP(FIG+r"\Fig2_预测hexbin.png",w=16); CAP("图3 BPINN预测密度（hexbin，虚线1:1）")
H("4.4 物理参数后验",2)
pt=post[post.regime=="T_EndHoldout"].set_index("param"); rows=[]
for p,nm in [("Topt","最适冠层温度(℃)"),("PHopt","最适土壤pH"),("LAIopt","最适LAI(m²/m²)"),("etaR","η_R"),("rho","ρ(t/ha)")]:
    r=pt.loc[p]; rows.append([nm,f"{r['mean']:.3f}",f"{r.lo:.3f}—{r.hi:.3f}"])
TBL(["参数","后验均值","95%区间"],rows,note="表4 物理参数后验（12模型集成）")
FIGP(FIG+r"\Fig3_参数后验森林图.png",w=15); CAP("图4 参数后验森林图（独立尺度）")
FIGP(FIG+r"\Fig4_参数后验小提琴.png",w=15); CAP("图5 参数后验小提琴（灰带为先验可行域）")
P("最适冠层温度28.5 ℃、pH 5.43、LAI 3.20，区间窄，与橡胶生理研究一致（Priyadarshan, 2011；Webster & Baulkwill, 1989）。")
H("4.5 不确定性与无泄漏共形校准",2)
rows=[[r.regime,f"{r.PICP95:.3f}",f"{r.MPIW:,.0f}",f"{r.NMPIW:.3f}"] for _,r in d12.iterrows()]
TBL(["验证","原始PICP","MPIW","NMPIW"],rows,note="表5 原始MC Dropout区间（覆盖率过低）")
rows=[[r.regime,f"{r.PICP95:.3f}",f"{r.MPIW:,.0f}",f"{r.NMPIW:.3f}"] for _,r in c16a.iterrows()]
TBL(["验证","共形PICP","MPIW","NMPIW"],rows,note="表6 无泄漏共形校准后区间")
FIGP(FIG+r"\Fig5_儋州区间.png",w=14.5); CAP("图6 儋州预测与认知区间、无泄漏共形区间")
P("原始区间覆盖率仅6%—14%；无泄漏共形后空间0.952、时间1.000、时空0.889。儋州2022低产被共形区间覆盖、不被认知区间覆盖。")
H("4.6 输入鲁棒性（按市县配对）",2)
rows=[]
for _,r in p17a.iterrows():
    ci=p17e[(p17e.model==r.model)&(p17e.k==r.k)].iloc[0]
    rows.append([r.model,f"{r.k:.2f}",f"{r.p:.3f}",f"{r.cohen_dz:.2f}",f"{ci.CI_lo:.2f}—{ci.CI_hi:.2f}"])
TBL(["模型","k","p","Cohen dz","dz 95%CI"],rows,note="表7 鲁棒性市县配对检验（n=18）")
FIGP(FIG+r"\Fig6_鲁棒性_误差棒.png",w=12.5); CAP("图7 RMSE变化（正=变差，误差棒±SD，B=80）")
P("BPINN各水平均不显著（dz 0.24—0.33）；树模型多数不显著；ElasticNet在5%/10%显著退化（dz 0.77/1.08）。")
H("4.7 公平消融",2)
rows=[[r.window,r.n_train,r.learner,f"{r.R2:.3f}",f"{r.RMSE:,.0f}"] for _,r in abl_len.iterrows()]
TBL(["训练窗","n_train","学习者","R²","RMSE"],rows,note="表8 数据长度（时间外推，测试2021—23固定）")
rows=[[r.regime,r.features,r.learner,f"{r.R2:.3f}"] for _,r in abl_feat.iterrows()]
TBL(["验证","特征","学习者","R²"],rows,note="表9 特征消融（同折同测试）",small=9)
rows=[[r.regime,r.variant,f"{r.R2:.3f}",f"{r.RMSE:,.0f}"] for _,r in abl_phys.iterrows()]
TBL(["验证","变体","R²","RMSE"],rows,note="表10 物理消融（同架构，跨折池化）",small=9)
P("时间外推Full（0.855）优于Physics-only（0.794）与NN-only（0.818）；空间NN-only略高（0.912）但MAPE更大；"
 "时空三者接近。物理机制的增益主要体现在时间外推与跨场景一致性。消融图见补充材料Fig S1。")
H("4.8 空间与时间分解",2)
P("逐年R²中位0.887（IQR 0.838—0.931），逐市县R²中位−0.576（IQR −2.531—−0.194）。模型主要解释市县间差异与"
 "年份共性，对市县特异的年际异常解释力弱，这也解释了池化R²可能掩盖的局限。")

H("5 讨论")
H("5.1 参数的农学意义",2)
P("识别的温度、pH与LAI最适值与橡胶喜高温、微酸土壤、中等郁闭林冠的已有认识一致（Priyadarshan, 2011；Forests, 2024），"
 "为区域适应性管理提供可量化参考。")
H("5.2 增量价值",2)
P("短预见期产量高自相关，持续性基准很强。BPINN的增量价值在于对异常环境的机制响应、跨市县/年份的可迁移性与可校准的"
 "不确定性，而非在稳定窗口追求更高R²。")
H("5.3 局限",2)
P("模型未纳入极端高温、台风、干旱与管理（树龄、更新、割制）驱动，难以预测市县特异极端减产；土壤为静态；尺度为市县"
 "均值。未来将引入事件尺度气候与管理数据、地块观测，并与过程型作物模型对比。")

H("6 结论")
P("基于海南岛18市县2010—2023真实面板，月度积分BPINN在空间/时间/时空验证R²为0.882/0.855/0.821（极差0.061），识别"
 "出与生理研究一致的温度、pH、LAI最适参数；无泄漏共形校准将95%区间覆盖率由6%—14%提升至89%—100%，10%扰动下性能"
 "无显著变化。纳入极端事件与管理变量是提升市县特异、极端年份预测能力的关键。")

H("数据与代码可用性")
P("数据来自海南省市县热带作物年度出版物、HWSD2（FAO & IIASA, 2023）与月度遥感栅格，许可依各来源；处理后主表、长表"
 "与中间结果随补充材料提供。全部脚本（step1—step19）按作用命名、可独立重跑；审稿期间将提供匿名访问链接，录用后公开"
 "GitHub并经Zenodo归档（链接/DOI【待填写】）。环境：Python 3.14.7、PyTorch 2.14.0、scikit-learn 1.9.1、pandas 3.0.5、"
 "rasterio 1.5.1（均为本机实测版本）；随机种子固定。Lead Contact：【请填写】。")

H("方法的统计分析")
P("独立样本为市县—年份（n=252）。空间LOCO 18折、时间外推训练≤2020/测试2021—23、时空块18折；指标池化。鲁棒性B=80、"
 "按18市县配对，报告p、Cohen dz及dz自助95%CI（表7）；区间以PICP、MPIW、NMPIW评价（表5、表6）；图2的R²置信区间由"
 "1000次自助得到。")

H("补充材料（编号）")
for s in ["Table S1 年度主表；Table S2 月度长表；Table S3 市县土壤表；Table S4 遥感月度面板；",
          "Table S5 预测明细与参数后验/集成样本；Table S6 相关性与共线表；",
          "Figure S1 公平消融图；Script S1 step1—step19脚本清单；全部主图含矢量PDF。"]:
    P(s,indent=False,size=10.5)

H("致谢、基金与声明")
P("致谢：【请填写】。基金：【请填写项目名称与编号】。")
P("作者贡献（CRediT）：【请逐一对应作者：概念化、方法、软件、数据整理、形式分析、写作—初稿、写作—审阅与编辑、监督、经费获取】。")
P("利益冲突：作者声明不存在利益冲突（或【请填写】）。")
P("生成式AI声明：本工作准备过程中使用豆包（Doubao，字节跳动）辅助语言表达与结构整理；作者对全部内容进行了审阅修改，"
 "并承担全部责任（如实际使用其他工具请据实修改）。")
P("伦理声明：不涉及人类受试者或动物实验，不适用。")

H("参考文献")
refs=[
"Tucker C J. Red and photographic infrared linear combinations for monitoring vegetation. Remote Sensing of Environment, 1979, 8(2): 127–150. doi:10.1016/0034-4257(79)90013-0.",
"Myneni R B, Hoffman S, Knyazikhin Y, et al. Global products of vegetation leaf area and fraction absorbed PAR from year one of MODIS data. Remote Sensing of Environment, 2002, 83(1–2): 214–231. doi:10.1016/S0034-4257(02)00092-5.",
"Gamon J A, Peñuelas J, Field C B. A narrow-waveband spectral index that tracks diurnal changes in photosynthetic efficiency. Remote Sensing of Environment, 1992, 41(1): 35–44. doi:10.1016/0034-4257(92)90059-S.",
"Garbulsky M F, Peñuelas J, Gamon J, et al. The photochemical reflectance index (PRI) and the remote sensing of leaf, canopy and ecosystem radiation use efficiencies: a review and meta-analysis. Remote Sensing of Environment, 2011, 115(2): 281–296. doi:10.1016/j.rse.2010.08.023.",
"Monteith J L. Solar radiation and productivity in tropical ecosystems. Journal of Applied Ecology, 1972, 9(3): 747–766. doi:10.2307/2401901.",
"Lloyd J, Taylor J A. On the temperature dependence of soil respiration. Functional Ecology, 1994, 8(3): 315–323. doi:10.2307/2389824.",
"Davidson E A, Janssens I A. Temperature sensitivity of soil carbon decomposition and feedbacks to climate change. Nature, 2006, 440(7081): 165–173. doi:10.1038/nature04514.",
"Atkin O K, Tjoelker M G. Thermal acclimation and the dynamic response of plant respiration to temperature. Trends in Plant Science, 2003, 8(7): 343–351. doi:10.1016/S1360-1385(03)00136-5.",
"Raich J W, Schlesinger W H. The global carbon dioxide flux in soil respiration and its relationship to vegetation and climate. Tellus B, 1992, 44(2): 81–99.",
"Beer C, Reichstein M, Tomelleri E, et al. Terrestrial gross carbon dioxide uptake: global distribution and covariation with climate. Science, 2010, 329(5993): 834–838. doi:10.1126/science.1184984.",
"Sellers P J. Canopy reflectance, photosynthesis and transpiration. International Journal of Remote Sensing, 1985, 6(8): 1335–1372. doi:10.1080/01431168508948283.",
"Rouse J W, Haas R H, Schell J A, Deering D W. Monitoring vegetation systems in the Great Plains with ERTS. Third ERTS Symposium, 1974, 1: 309–317.",
"Jackson R D, Idso S B, Reginato R J, Pinter P J. Canopy temperature as a crop water stress indicator. Water Resources Research, 1981, 17(4): 1133–1138. doi:10.1029/WR017i004p01133.",
"Raissi M, Perdikaris P, Karniadakis G E. Physics-informed neural networks. Journal of Computational Physics, 2019, 378: 686–707. doi:10.1016/j.jcp.2018.10.045.",
"Karniadakis G E, Kevrekidis I G, Lu L, et al. Physics-informed machine learning. Nature Reviews Physics, 2021, 3(6): 422–440. doi:10.1038/s42254-021-00314-5.",
"Yang L, Meng X, Karniadakis G E. B-PINNs: Bayesian physics-informed neural networks for forward and inverse PDE problems with noisy data. Journal of Computational Physics, 2021, 425: 109913. doi:10.1016/j.jcp.2020.109913.",
"Gal Y, Ghahramani Z. Dropout as a Bayesian approximation: representing model uncertainty in deep learning. ICML, PMLR, 2016, 48: 1050–1059.",
"Kendall A, Gal Y. What uncertainties do we need in Bayesian deep learning for computer vision? NeurIPS, 2017, 30: 5574–5584.",
"Lakshminarayanan B, Pritzel A, Blundell C. Simple and scalable predictive uncertainty estimation using deep ensembles. NeurIPS, 2017, 30.",
"Angelopoulos A N, Bates S. A gentle introduction to conformal prediction and distribution-free uncertainty quantification. Foundations and Trends in Machine Learning, 2023, 16(4): 494–591.",
"Vovk V, Gammerman A, Shafer G. Algorithmic Learning in a Random World. Springer, 2005.",
"Zou H, Hastie T. Regularization and variable selection via the elastic net. Journal of the Royal Statistical Society B, 2005, 67(2): 301–320. doi:10.1111/j.1467-9868.2005.00503.x.",
"Tibshirani R. Regression shrinkage and selection via the lasso. Journal of the Royal Statistical Society B, 1996, 58(1): 267–288.",
"Hoerl A E, Kennard R W. Ridge regression: biased estimation for nonorthogonal problems. Technometrics, 1970, 12(1): 55–67.",
"Breiman L. Random forests. Machine Learning, 2001, 45(1): 5–32.",
"Chen T, Guestrin C. XGBoost: a scalable tree boosting system. KDD, 2016: 785–794. doi:10.1145/2939672.2939785.",
"Ke G, Meng Q, Finley T, et al. LightGBM: a highly efficient gradient boosting decision tree. NeurIPS, 2017, 30: 3146–3154.",
"Drucker H, Burges C J C, Kaufman L, et al. Support vector regression machines. NeurIPS, 1997, 9: 155–161.",
"Cover T, Hart P. Nearest neighbor pattern classification. IEEE Transactions on Information Theory, 1967, 13(1): 21–27. doi:10.1109/TIT.1967.1053964.",
"Hastie T, Tibshirani R, Friedman J. The Elements of Statistical Learning. 2nd ed. Springer, 2009.",
"Goodfellow I, Bengio Y, Courville A. Deep Learning. MIT Press, 2016.",
"Bates J M, Granger C W J. The combination of forecasts. Operational Research Quarterly, 1969, 20(4): 451–468.",
"FAO, IIASA. Harmonized World Soil Database version 2.0. Rome; Laxenburg, 2023. ISBN 978-92-5-137499-3.",
"Pribyl D W. A critical review of the conventional SOC to SOM conversion factor. Geoderma, 2010, 156(3–4): 75–83. doi:10.1016/j.geoderma.2010.02.003.",
"Priyadarshan P M. Biology of Hevea Rubber. CABI, 2011. ISBN 9781845936662.",
"Webster C C, Baulkwill W J. Rubber. Longman Scientific & Technical, 1989.",
"Photosynthesis and latex burst characteristics in different rubber tree varieties under chilling stress. Forests, 2024, 15(8): 1408. doi:10.3390/f15081408.",
"刘少军, 车秀芬. 基于FY-3遥感数据的海南橡胶林NDVI变化研究. 热带作物学报, 2014, 35(10): 2059–2065.",
"李海亮, 戴声佩, 陈帮乾, 等. 基于HJ-1A/1B数据的天然橡胶干旱监测. 农业工程学报, 2016, 32(23): 176–182. doi:10.11975/j.issn.1002-6819.2016.23.024.",
"李海亮, 罗微, 李世池, 等. 基于净初级生产力的天然橡胶产胶潜力研究. 资源科学, 2012, 34(2): 337–344.",
"Spatiotemporal dynamics and climatic responses of rubber plantations' aboveground biomass in western 海南 Island based on multi-source remote sensing and explainable machine learning. Remote Sensing, 2026, 18(17): 2856. doi:10.3390/rs18172856.",
"王利溥. 橡胶树气象. 北京: 气象出版社, 1989.",
"何康, 黄宗道. 热带北缘天然橡胶树栽培. 广州: 广东科技出版社, 1987.",
"Ryan M G. Effects of climate change on plant respiration. Ecological Applications, 1991, 1(2): 157–167.",
"Amthor J S. The McCree–de Wit–Penning de Vries–Thornley respiration paradigms: three apices. Annals of Botany, 2000, 86(1): 1–20. doi:10.1006/anbo.2000.1160.",
"Luo Y. Terrestrial Carbon-Cycle Modeling. Springer, 2007."]
for i,x in enumerate(refs,1):
    pp=d.add_paragraph(); rr=pp.add_run(f"[{i}] {x}"); rr.font.size=Pt(10); rr.font.name="Arial"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"),"宋体"); pp.paragraph_format.line_spacing=1.15; pp.paragraph_format.space_after=Pt(2)
d.save(ROOT+r"\修订版论文_SCI规范_v3.docx")
print("已生成 v3；参考文献",len(refs),"条")
