"""Shared schema, metrics and explanations. No file writes on import."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score,precision_score,recall_score,f1_score,
    balanced_accuracy_score,roc_auc_score,average_precision_score,confusion_matrix)
from fairlearn.metrics import MetricFrame
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
SEED=42
NUM=['Age','BMI','Daily2','Daily3','Daily4','TransportTimes30','TransportMinutesDay','StrengthTimes30','ModerateTimes30','ModerateMinutes30','VigorousTimes30','VigorousMinutes30','SportVariety']
BIN=[]
FEATURES=NUM
CN={'Age':'年龄','BMI':'身高体重换算的BMI','Daily2':'日常站走较多','Daily3':'日常搬运轻物或爬坡楼梯','Daily4':'日常重体力劳动','TransportTimes30':'步行骑车通勤次数','TransportMinutesDay':'通勤活动日分钟','StrengthTimes30':'力量训练次数','ModerateTimes30':'中等活动次数','ModerateMinutes30':'中等活动总分钟','VigorousTimes30':'较强活动次数','VigorousMinutes30':'较强活动总分钟','SportVariety':'运动项目种类数'}
BOUNDS={'Age':(20,49),'BMI':(10,80),'Daily2':(0,1),'Daily3':(0,1),'Daily4':(0,1),'TransportTimes30':(0,9000),'TransportMinutesDay':(0,600),'StrengthTimes30':(0,300),'ModerateTimes30':(0,15000),'ModerateMinutes30':(0,9000000),'VigorousTimes30':(0,15000),'VigorousMinutes30':(0,9000000),'SportVariety':(0,50)}
ATTRS=["Sex","AgeGroup","Intersection"]
TARGET="是否属于原年龄性别参考标准下的低心肺适能等级"
ACTIVITY_LABELS=["很少规律活动，也尽量避免走路或费力活动", "很少规律活动，但会散步、走楼梯或偶尔锻炼", "规律较轻活动：每周10–60分钟", "规律较轻活动：每周超过60分钟", "规律较强活动：每周不足30分钟", "规律较强活动：每周30–60分钟", "规律较强活动：每周超过60分钟至3小时", "规律较强活动：每周超过3小时"]
def dump(obj,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    def normal(x):
        if isinstance(x,dict): return {str(k):normal(v) for k,v in x.items()}
        if isinstance(x,(list,tuple,np.ndarray)):return [normal(v) for v in x]
        if isinstance(x,(np.integer,)):return int(x)
        if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
        return x
    path.write_text(json.dumps(normal(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def metrics(y,pred,score=None):
    m={"Accuracy":accuracy_score(y,pred),"Precision":precision_score(y,pred,zero_division=0),
       "Recall":recall_score(y,pred,zero_division=0),"F1":f1_score(y,pred,zero_division=0),
       "BalancedAccuracy":balanced_accuracy_score(y,pred),"Confusion":confusion_matrix(y,pred,labels=[0,1]).tolist()}
    if score is not None and len(np.unique(y))==2:
        m.update(ROC_AUC=roc_auc_score(y,score),PR_AUC=average_precision_score(y,score))
    return m
def expected(y,p,weights=None):
    """Expected confusion counts for stochastic decisions; not disease probabilities."""
    y=np.asarray(y);p=np.asarray(p)
    w=np.ones(len(y)) if weights is None else np.asarray(weights,dtype=float)
    pos=float(w[y==1].sum());neg=float(w[y==0].sum())
    tp=float(np.sum(w*y*p));fp=float(np.sum(w*(1-y)*p))
    fn=pos-tp;tn=neg-fp
    tpr=tp/pos if pos else np.nan;fpr=fp/neg if neg else np.nan
    return {"Accuracy":(tp+tn)/(pos+neg),"Precision":tp/(tp+fp) if tp+fp else 0.,
      "Recall":tpr,"TPR":tpr,"FNR":1-tpr,"FPR":fpr,
      "F1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,
      "BalancedAccuracy":(tpr+1-fpr)/2,"SelectionRate":(tp+fp)/(pos+neg)}
def reliability(y):
    n=len(y);pos=int(np.sum(y));neg=n-pos
    flags=[]
    if n<100:flags.append("组内少于100条")
    if pos<20:flags.append("正类少于20，检出/漏判率估计不稳")
    if neg<20:flags.append("负类少于20，误判率估计不稳")
    if pos==0:flags.append("TPR/FNR无法估计")
    if neg==0:flags.append("FPR无法估计")
    return {"n":n,"positive":pos,"negative":neg,"label_rate":pos/n if n else None,
       "reliability":"；".join(flags) or "样本量达到本项目显示门槛，仍需查看区间"}
def exp_audit(y,p,groups,weights=None):
    groups=np.asarray(groups);y=np.asarray(y);p=np.asarray(p);by={}
    for g in sorted(np.unique(groups)):
        mask=groups==g;w=None if weights is None else np.asarray(weights)[mask]
        by[str(g)]={**reliability(y[mask]),**expected(y[mask],p[mask],w)}
    tpr=[v["TPR"] for v in by.values()];fpr=[v["FPR"] for v in by.values()]
    valid=np.all(np.isfinite(tpr)) and np.all(np.isfinite(fpr))
    eo=max(np.ptp(tpr),np.ptp(fpr)) if valid else None
    return {"overall":expected(y,p,weights),"groups":by,"EO":eo,
      "DP":float(np.ptp([v["SelectionRate"] for v in by.values()]))}
def hard_audit(y,pred,groups):
    # Explicit NaNs for undefined group rates; Fairlearn is the audit engine.
    names=["Accuracy","Precision","Recall","F1","BalancedAccuracy","TPR","FNR","FPR","SelectionRate"]
    mf=MetricFrame(metrics={k:(lambda yt,yp,k=k:expected(yt,yp)[k]) for k in names},
        y_true=y,y_pred=pred,sensitive_features=groups)
    result=exp_audit(y,pred,groups)
    for g,row in mf.by_group.iterrows():result["groups"][str(g)].update(row.to_dict())
    result["overall"]=mf.overall.to_dict()
    return result
def mixture_probability(eg,X):
    # Public constituent estimators and weights; no private _pmf_predict API.
    return sum(float(w)*model.predict(X) for w,model in zip(eg.weights_,eg.predictors_) if w>0)
def validate(v):
    errors=[]
    for c,(lo,hi) in BOUNDS.items():
        val=v.get(c)
        if val is None or pd.isna(val):
            errors.append(CN[c]+"必须填写")
        elif not np.isfinite(val) or not lo<=val<=hi:errors.append(f"{CN[c]}应在 {lo}–{hi} 范围")
    for c in BIN:
        if v.get(c) is not None and not pd.isna(v[c]) and v[c] not in [0,1]:errors.append(CN[c]+"须为是/否/不知道")
    return errors

def form_values(age,height,weight,activity):
    errors=[]
    for value,lo,hi,label in [(age,20,49,"年龄"),(height,100,230,"身高（厘米）"),(weight,25,200,"体重（千克）")]:
        if value is None or not np.isfinite(value) or not lo<=value<=hi:errors.append(f"{label}应在{lo}–{hi}范围")
    if activity is None or activity not in range(8):errors.append("请选择最接近通常情况的活动选项；不知道时不能生成个人估计")
    if errors:return None,errors
    values={"Age":float(age),"BMI":float(weight)/(float(height)/100)**2,"Activity":int(activity)}
    return values,validate(values)
def local_explanation(pack,frame):
    z=pack["pre"].transform(frame[FEATURES])
    coef=pack["baseline"].coef_[0]
    contributions=(z[0]-pack["reference"])*coef
    base=float(pack["baseline"].intercept_[0]+pack["reference"]@coef)
    return z,base,contributions
def feature_cn(name):
    name=name.split("__")[-1]
    if name.startswith("missingindicator_"):return CN.get(name[17:],name[17:])+"（缺失标记）"
    return CN.get(name,name)

def read_xport(path):
    # In this pandas runtime SAS zero may decode as ~5.3976e-79. These NHANES
    # fields have no legitimate values at this scale; normalize only such residues.
    d=pd.read_sas(path,format="xport")
    numeric=d.select_dtypes(include="number").columns
    d[numeric]=d[numeric].mask(d[numeric].abs()<1e-50,0.)
    return d

DAILY_LABELS=['大多坐着，走动不多','站立或走动较多，但不经常搬提物品','经常搬提轻物，或经常爬坡、走楼梯','经常做重体力劳动或搬提重物']
SPORTS={10:'健身操',11:'棒球',12:'篮球',13:'骑自行车',14:'保龄球',15:'舞蹈',16:'钓鱼',17:'美式橄榄球',18:'园艺',19:'高尔夫',20:'徒步',21:'冰球',22:'狩猎',23:'慢跑',24:'皮划艇',25:'俯卧撑',26:'壁球类运动',27:'轮滑',28:'划船',29:'跑步',30:'仰卧起坐',31:'滑冰',32:'越野滑雪',33:'高山滑雪',34:'足球',35:'垒球',36:'爬楼梯锻炼',37:'拉伸',38:'游泳',39:'网球',40:'跑步机',41:'排球',42:'步行锻炼',43:'举重/负重训练',44:'庭院劳动',50:'拳击',51:'飞盘',52:'骑马',53:'武术',54:'摔跤',55:'瑜伽',56:'体操/啦啦操',57:'儿童游戏',58:'跳绳',59:'滑板',60:'冲浪',61:'蹦床',71:'其他活动'}

def question_contributions(contributions,daily_label):
    """Group one-hot levels back into the one question the person answered."""
    daily=0.;rows=[]
    for feature,value in zip(FEATURES,contributions):
        if feature in ['Daily2','Daily3','Daily4']:daily+=float(value)
        else:rows.append({'因素':CN[feature],'贡献':float(value)})
    rows.append({'因素':'日常活动状态（'+daily_label+'）','贡献':daily})
    return pd.DataFrame(rows)

def expanded_form_values(raw):
    """Map easy-to-answer questions to exactly the training feature semantics."""
    errors=[]
    def number(key,lo,hi,label,integer=False):
        value=raw.get(key)
        if value is None or not isinstance(value,(int,float,np.number)) or not np.isfinite(value) or not lo<=value<=hi or (integer and int(value)!=value):
            errors.append(f'{label}请填{lo}–{hi}'+('之间的整数' if integer else '之间的数值'));return None
        return float(value)
    age=number('age',20,49,'年龄',True);height=number('height',100,230,'身高（厘米）');weight=number('weight',25,200,'体重（千克）')
    daily=raw.get('daily')
    if daily not in DAILY_LABELS:errors.append('请选择能描述日常活动状态的一项')
    v={'Age':age,'BMI':weight/(height/100)**2 if height and weight else None}
    for k in [2,3,4]:v[f'Daily{k}']=float(daily==DAILY_LABELS[k-1])
    for key,label in [('transport','步行/骑车通勤'),('strength','力量训练'),('sports_status','休闲运动')]:
        if raw.get(key) not in ['有','没有']:errors.append(label+'尚不确定，不能按没有活动处理')
    if raw.get('transport')=='有':
        v['TransportTimes30']=number('transport_times',1,300,'过去30天通勤次数')
        v['TransportMinutesDay']=number('transport_minutes',1,600,'有通勤活动那天的总分钟')
    else:v.update(TransportTimes30=0.,TransportMinutesDay=0.)
    if raw.get('strength')=='有':v['StrengthTimes30']=number('strength_times',1,300,'过去30天力量训练次数')
    else:v['StrengthTimes30']=0.
    for prefix in ['Moderate','Vigorous']:v[prefix+'Times30']=0.;v[prefix+'Minutes30']=0.
    rows=raw.get('sports',[])
    active_rows=rows if raw.get('sports_status')=='有' else []
    if raw.get('sports_status')=='有' and not active_rows:errors.append('至少填写一项运动')
    codes=set();pairs=set()
    for i,row in enumerate(active_rows):
        code=row.get('code');level=row.get('level');times=row.get('times');minutes=row.get('minutes')
        if code not in SPORTS or level not in [1,2]:errors.append(f'第{i+1}项运动的项目或强度未选完整');continue
        if (code,level) in pairs:errors.append(f'第{i+1}项与前面项目和强度相同，请合并次数并填写加权平均时长');continue
        pairs.add((code,level));codes.add(code)
        if times is None or minutes is None or not np.isfinite(times) or not np.isfinite(minutes) or not 1<=times<=300 or not 10<=minutes<=600:
            errors.append(f'第{i+1}项运动：次数需1–300，每次时长需10–600分钟');continue
        prefix='Moderate' if level==1 else 'Vigorous'
        v[prefix+'Times30']+=float(times);v[prefix+'Minutes30']+=float(times)*float(minutes)
    v['SportVariety']=float(len(codes))
    if errors:return None,errors
    return v,validate(v)
