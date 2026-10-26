"""Detailed activity questionnaire; session-only input, no health-data writes."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import streamlit as st
st.set_page_config(page_title='我的运动习惯与体能',page_icon='🏃',layout='wide')
from loading_ui import show_opening,show_relaxation
opening_notice=show_opening()
from visual_design import theme
from support_ui import load_screen
from common import *
from artifact_store import load_artifacts,sync_session_version
theme()
PACK,R,VERSION=load_screen(load_artifacts,OUT/'models/model_bundle.joblib',OUT/'results/results.json',opening_notice)
if sync_session_version(st.session_state,VERSION):st.info('分析已更新，请重新提交填写内容。')

CN_METRICS={'Accuracy':'准确率','Precision':'精确率','Recall':'召回率（同TPR）','TPR':'检出率','FNR':'漏判率','FPR':'误判率','F1':'F1','BalancedAccuracy':'平衡准确率','SelectionRate':'预测偏低比例'}
GROUP_CN={'Sex':'性别','AgeGroup':'年龄段','Intersection':'性别 × 年龄段'}
MODEL_CN={'LR':'详细问卷·逻辑回归（界面模型）','RF':'详细问卷·随机森林','ThreeFeatureLR':'三特征·同人群重新训练','V1SavedSamePeople':'v1已保存模型·相同评估人群','All_non_low':'全部预测非偏低'}
BASE_FIELDS=['age','height','weight','daily','transport','transport_times','transport_minutes','strength','strength_times','sports_status','n_sports']
FIELDS=BASE_FIELDS+[f'sport_{i}_{k}' for i in range(20) for k in ['code','level','times','minutes']]
UNKNOWN='不知道／暂时无法判断'

def remember(key=None):
    draft=st.session_state.setdefault('input_draft',{})
    # Only the changed widget may update its draft; hidden widgets can be cleared
    # by Streamlit and must not overwrite the saved values of conditional questions.
    if key is not None:draft[key]=st.session_state['form_'+key]
    if key is not None:st.session_state['flow_errors']=[]

def example():
    clear()
    values={'age':25,'height':170.,'weight':65.,'daily':DAILY_LABELS[0],'transport':'有','transport_times':20.,'transport_minutes':30.,'strength':'有','strength_times':4.,'sports_status':'有','n_sports':2,
        'sport_0_code':23,'sport_0_level':2,'sport_0_times':8.,'sport_0_minutes':30.,'sport_1_code':42,'sport_1_level':1,'sport_1_times':12.,'sport_1_minutes':30.}
    for k,v in values.items():st.session_state['form_'+k]=v
    st.session_state['input_draft']=values.copy()

def clear():
    for k in FIELDS:st.session_state['form_'+k]=1 if k=='n_sports' else None
    st.session_state['input_draft']={k:(1 if k=='n_sports' else None) for k in FIELDS}
    for k in ['history','invalid_current','input_errors','analysis_failed','analysis_example','feedback_record','feedback_choice','feedback_note']:st.session_state.pop(k,None)
    st.session_state['flow_stage']=0
    st.session_state['flow_previous_stage']=1
    st.session_state['flow_errors']=[]

def restore():
    draft=st.session_state.setdefault('input_draft',{})
    for k in FIELDS:
        st.session_state['form_'+k]=draft.get(k,1 if k=='n_sports' else None)

def payload():
    remember();d=st.session_state['input_draft'];r={k:d.get(k) for k in BASE_FIELDS if k!='n_sports'}
    if r['transport']!='有':r['transport_times']=None;r['transport_minutes']=None
    if r['strength']!='有':r['strength_times']=None
    r['sports']=[]
    if r['sports_status']=='有':
        for i in range(int(d.get('n_sports') or 1)):r['sports'].append({k:d.get(f'sport_{i}_{k}') for k in ['code','level','times','minutes']})
    return r

def num(label,key,col=None,integer=False):
    return (col or st).number_input(label,value=None,step=1 if integer else 1.,key='form_'+key,on_change=remember,args=(key,))

def yesno(label,key):return st.radio(label,['有','没有',UNKNOWN],index=None,horizontal=True,key='form_'+key,on_change=remember,args=(key,))

def predict_page():
    from experience import render
    render(PACK,example,clear,restore,payload,num,yesno,remember)


def audit_page():
    st.title('不同人群的估计同样可靠吗？')
    st.write('漏判：原测试分层为偏低，模型却未识别；误判：原测试分层非偏低，模型却判为偏低。')
    st.caption('审核的是原测试参考标签，不是疾病诊断；标签本身已按年龄性别分层。')
    st.info('本页比较性别、年龄和交叉群体。性别差异缩小的同时，年龄及交叉群体差异扩大；不能概括为所有群体都更公平。')
    with st.expander('各审核属性的改进前后总览'):
        total=[]
        for a in ATTRS:
            b=R['baseline_audit'][a];f=R['fairness_expected_audit'][a]
            total.append({'审核属性':GROUP_CN[a],'基线EO':b['EO'],'约束EO':f['EO'],'EO变化':f['EO']-b['EO'],'基线DP':b['DP'],'约束DP':f['DP']})
        st.dataframe(pd.DataFrame(total),hide_index=True)
        st.caption('总览固定使用混合策略期望口径。EO看错误率差异，DP看预测比例差异；数值变化的区间见下方。')
    with st.expander('分组依据与用户影响'):
        st.write('按记录中的性别作基础审核，按十年年龄段及性别×年龄作补充审核；年龄分界是分析选择，不是医学界限。标签本身按年龄、性别参考标准分层。')
        st.write('漏判可能让偏低者过度相信结果，误判可能造成不必要的担忧。标签比例不同会影响预测比例，不能单凭DP认定歧视。')
        st.write('1999–2000年数据用于训练，2001–2002年验证集用于选择参数、分类阈值及公平性约束强度，2003–2004年测试集用于比较基线与改进模型；三期参与者互不重叠，预处理仅在训练集拟合。')
    sel=R['selection']['fairness']
    if not sel['eligible']:st.warning('公平性方案未通过验证集性能门槛，本页展示失败尝试，不建议替换基线。')
    elif not sel['validation_EO_improved']:st.info('方案达到性能门槛，但验证集组间差异未缩小；不能只凭名称认定它更公平。')
    attr=st.selectbox('选择群体',ATTRS,format_func=lambda x:GROUP_CN[x],key='audit_group')
    mode=st.radio('比较口径',['混合策略期望表现','固定种子的一次分类'],horizontal=True,key='audit_mode')
    cmode='expected' if mode.startswith('混合') else 'hard'
    base=R['baseline_audit'][attr];fair=R['fairness_expected_audit' if cmode=='expected' else 'fairness_hard_audit'][attr]
    delta=fair['EO']-base['EO']
    st.write(f"**在本次测试评估中，{GROUP_CN[attr]}组间错误差异{'缩小' if delta<0 else '扩大' if delta>0 else '不变'}。**")
    c1,c2,c3=st.columns(3)
    c1.metric('基线组间差异',f"{base['EO']:.3f}");c2.metric('约束方案组间差异',f"{fair['EO']:.3f}");c3.metric('差异变化',f'{delta:+.3f}',delta_color='off')
    st.caption('这里取各组检出率差值、误判率差值中较大的一个（EO）；越小表示两类错误率更接近，不代表每组都预测得好。')
    rows=[]
    for group,b in base['groups'].items():
        f=fair['groups'][group]
        rows.append({'群体':group,'人数':b['n'],'偏低':b['positive'],'非偏低':b['negative'],'原漏判率':b['FNR'],'改后漏判率':f['FNR'],'原误判率':b['FPR'],'改后误判率':f['FPR']})
        if b['n']<100 or min(b['positive'],b['negative'])<20:st.warning(group+'：'+b['reliability'])
    st.dataframe(pd.DataFrame(rows),hide_index=True)
    st.subheader('差异变化的同时，整体表现怎样？')
    fields=['F1','BalancedAccuracy','TPR','FPR','SelectionRate']
    st.dataframe(pd.DataFrame([{'模型':label,**{CN_METRICS[k]:a['overall'][k] for k in fields}} for label,a in [('基线',base),('约束方案',fair)]]),hide_index=True)
    st.write('判断是否值得采用，需要同时看两类错误与整体性能。差异缩小可能来自原本较好的一组变差，不等于所有人都受益。主体验页仍使用基线模型。')
    with st.expander('完整分组指标及训练样本'):
        st.dataframe(pd.DataFrame([{'模型':name,'群体':g,**v} for name,a in [('基线',base),('约束方案',fair)] for g,v in a['groups'].items()]).rename(columns=CN_METRICS),hide_index=True)
        split=st.selectbox('查看集合',['train','val','test'],key='audit_split')
        st.dataframe(pd.DataFrame([{'群体':g,**v} for g,v in R['summary']['split_group_stats'][split][attr].items()]),hide_index=True)
    with st.expander('变化有多确定？'):
        st.write(f'当前口径：{GROUP_CN[attr]}；{mode}减去基线。F1与平衡准确率为整体指标，EO对应当前群体。')
        ci=R['paired_bootstrap_by_attribute'][attr][cmode]
        st.dataframe(pd.DataFrame([{'指标':k,'变化':v['delta'],'区间下限':v['CI95'][0],'区间上限':v['CI95'][1]} for k,v in ci.items()]),hide_index=True)
        st.caption('1000次个体配对重抽样。区间跨0，不能确认变化方向；不是人口总体区间，也不包含重新训练的不确定性。')
    with st.expander('方案如何选出？'):
        st.write('仅使用2001–2002验证集选约束强度；2003–2004测试集不参与训练或方案选择，用于同一人群的改进前后比较。混合策略采用期望混淆量，另一口径是seed42的一次分类。')
        st.dataframe(pd.DataFrame(R['fairness_candidates']),hide_index=True)
        st.write('同成本、未加公平约束的机制对照（性别口径）：')
        st.json({'EO':R['cost_matched_control']['EO'],**R['cost_matched_control']['overall']})
        st.caption('如果对照也能缩小差异，就不能把所有变化归因于公平约束。更多敏感性结果见作业二报告。')
    st.subheader('检查是否读懂')
    questions=[('整体准确率高，能说明每个人群都表现好吗？',['能','不能，还要查看分组错误率'],1),('预测偏低的比例不同，能直接认定歧视吗？',['能','不能，需要结合标签定义和错误率'],1),('差异变小但各组检出率下降，就一定值得替换吗？',['是','否，还需要评估预测性能的代价'],1)]
    for i,(q,options,correct) in enumerate(questions):
        ans=st.radio(q,options,index=None,key=f'quiz_{i}')
        if st.button('核对理解',key=f'answer_{i}'):
            if ans is None:st.info('先选择，再核对。')
            elif ans==options[correct]:st.success('理解正确。'+options[correct])
            else:st.error('请重新考虑：'+options[correct])

def experiments_page():
    st.title('这次增加信息，有帮助吗？')
    summary=R['summary'];counts=summary['splits']
    st.write(f"新增6份详细运动问卷；{summary['n']}名独立参与者。训练{counts['train']}人、验证{counts['val']}人、测试评估{counts['test']}人。")
    st.info('新增信息让运动习惯表达更细致，但逻辑回归尚未显示稳定的预测提升。不能把问得更多当作更可靠。')
    st.dataframe(pd.DataFrame([{'模型':MODEL_CN[k],**{m:v for m,v in d.items() if m!='Confusion'}} for k,d in R['test_models'].items()]).rename(columns=CN_METRICS),hide_index=True)
    st.write('以上模型在相同评估人群上比较。主页面预先采用可精确解释的逻辑回归；随机森林仅作对照，没有看到评估结果后切换模型。')
    st.dataframe(pd.DataFrame([{'扩展减三特征':k,'变化':v['delta'],'区间下限':v['CI95'][0],'区间上限':v['CI95'][1]} for k,v in R['feature_comparison_ci'].items()]),hide_index=True)
    st.caption('区间跨0，不能确认差异方向；不是对中国大学生的验证，也不包含重新训练的误差。')
    for name in ['model_comparison','confusion','importance']:
        p=OUT/f'figures/{name}.png'
        if p.exists():st.image(str(p))
    with st.expander('数据来源、处理和实验范围'):
        st.markdown('[详细活动问卷](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/PAQ_C.htm) · [运动项目明细](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/PAQIAF_C.htm) · [体能标签](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/CVX_C.htm)')
        st.write('同一NHANES调查增加新数据表，未增加新的独立参与者。按人汇总运动记录；没有活动才补零，不知道或缺失不当零。日常活动一个分类问题编码成3列，最终13个特征。')
        st.write('1999–2000训练、2001–2002验证集选参数；2003–2004测试集用于方案确定后的评价，不用于调参。更多细节和缺失人数见报告。')
        st.write('原标签由跑步机测试心率与负荷外推，不是问卷直接算出的标签。只用于原年龄性别参考分层，不能替代实测体能。')
        st.write(f"本次训练与统计分析实际用时 {R['training_runtime']['seconds']:.1f} 秒，不含下载、界面开发和测试。")
    with st.expander('本次用户反馈与改动'):
        st.write('P01测试v1.0，认为输入太少，推动v2.0详细问卷；P02测试v2.0，认为结论难懂，推动v2.1结果解释；P03测试v2.1，认为流程不清且冗长，推动v2.2三步填写与精简展示。P04测试v2.2，对部分因素贡献小、增加问题的价值提出疑问，本次补充报告回应。记录为同学原话，仅调整人称。')
        st.write('已实施：F01对应详细数据与问卷；F02对应结果页直接解释心肺耐力、分类含义、依据、局限和如何核对输入。F03认为首次流程不清、阅读负担重，v2.2改为三步填写、先简短结论再按需展开分析。已确认反馈来自4位不同同学；P04对应报告解释补充，问卷和模型版本保持不变。')
        st.write('4人均报告完成填写：1人不到一分钟，2人约一分半，P04约两分钟；均无需帮助，也均认为整体准确率高不意味着各群体表现都好。P04是v2.2补充记录，不代表版本对照验证或本次报告改后的复测。')
    for name in ['作业一实验报告.md','作业二实验报告.md']:
        p=ROOT/'reports'/name
        if p.exists():st.download_button('下载'+name,p.read_bytes(),file_name=name)

st.sidebar.title('运动有迹')
page=st.sidebar.radio('入口',['体验体能估计','实验与审核'],key='navigation',label_visibility='collapsed')
st.sidebar.toggle('动态效果',value=True,key='visual_motion',help='关闭后减少动画。')
with st.sidebar.expander('使用帮助'):
    st.write('键盘操作：Tab 移动，方向键选择，Enter 确认。')
    st.write('填写中可返回修改；提交后可查看结果，或清空重填。')
show_relaxation()
if page=='体验体能估计':predict_page()
else:
    section=st.sidebar.radio('查看内容',['人群公平性','模型与数据'],key='review_section',label_visibility='collapsed')
    if section=='人群公平性':audit_page()
    else:experiments_page()
opening_notice.empty()
st.session_state['_page_opened']=True
