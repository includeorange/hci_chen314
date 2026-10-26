"""F03: guided questionnaire with a concise, self-contained result."""
import streamlit as st
from common import *
from result_copy import result_copy,DEFINITION,REFERENCE
from support_ui import feedback_panel
from visual_design import brand,home_tiles,summary_tiles,step_orbit,result_chart

STAGES=['开始','基本信息','日常活动','运动明细','结果']
SHORT_DAILY=['大多坐着','站立、走动较多','常搬轻物、爬坡或走楼梯','经常做重体力劳动']
UNKNOWN='不知道／暂时无法判断'

def step_errors(raw,stage):
    if stage==1:
        raw={k:raw.get(k) for k in ['age','height','weight']}
        raw.update(daily=DAILY_LABELS[0],transport='没有',strength='没有',sports_status='没有',sports=[])
    elif stage==2:raw={**raw,'sports_status':'没有','sports':[]}
    return expanded_form_values(raw)[1]

def submit(pack,raw,is_example=False):
    values,errors=expanded_form_values(raw)
    st.session_state['flow_errors']=errors
    if errors:return
    try:
        with st.spinner('正在分析本次填写，请稍候……'):
            z,ref,cs=local_explanation(pack,pd.DataFrame([values]));score=float(pack['baseline'].predict_proba(z)[0,1])
            if not np.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('invalid prediction')
    except Exception:
        st.session_state['analysis_failed']=True
        st.session_state['analysis_example']=is_example
        st.session_state['flow_stage']=3
        return
    st.session_state['analysis_failed']=False
    for key in ['feedback_record','feedback_choice','feedback_note']:
        st.session_state.pop(key,None)
    entry={'raw':raw,'inputs':values,'score':score,'prediction':int(score>=pack['threshold']),'reference':ref,'contributions':cs.tolist(),'is_example':is_example}
    st.session_state['history']=(st.session_state.get('history',[])+[entry])[-2:]
    st.session_state['flow_previous_stage']=st.session_state.get('flow_stage',3)
    st.session_state['flow_stage']=4

def go(stage):
    st.session_state['flow_previous_stage']=st.session_state.get('flow_stage',1)
    st.session_state['flow_stage']=stage
    st.session_state['flow_errors']=[]

def render(pack,example,clear,restore,payload,num,yesno,remember):
    stage=st.session_state.setdefault('flow_stage',0)
    restore()
    motion=st.session_state.get('visual_motion',True)
    brand()
    st.title('我的运动习惯与体能')
    if stage==0:
        st.html('<p class="intro">了解运动习惯，估计持续运动的能力。</p>')
        st.caption('适用于20–49岁，仅供参考，不能代替体测。')
        with st.container(border=True):
            st.markdown('**① 基本信息 → ② 日常活动 → ③ 运动明细 → 查看结果**')
            st.write('填写年龄、身高体重和最近30天的运动情况。')
        a,b=st.columns(2)
        a.button('开始填写',type='primary',key='start',on_click=go,args=(1,))
        def demo():example();submit(pack,payload(),is_example=True)
        b.button('先看一个示例',key='example',on_click=demo)
        home_tiles()
        st.caption('输入会发送到云端，在当前会话中处理。原型不主动写入数据库或文件，可随时清空。')
        with st.expander('数据来源与使用范围'):
            st.write('模型来自NHANES历史调查，未在中国大学生中验证；详细运动问卷也没有证明主模型更准确。它不评价力量、柔韧性或整体健康。')
        return
    if stage==4:
        history=st.session_state.get('history',[])
        if not history:go(0);st.rerun()
        cur=history[-1];explanation=result_copy(cur['prediction'])
        if payload()!=cur['raw']:st.info('你修改的内容尚未提交。下面仍是上次结果，点击“修改填写内容”继续填写并提交。')
        if cur.get('is_example'):st.caption('演示示例，不是你的个人结果。')
        with st.container(border=True):
            st.subheader('心肺耐力可能偏低' if cur['prediction'] else '本次未提示心肺耐力偏低')
            st.write('心肺耐力指持续运动的能力。本结果根据填写内容估计，可能有误，不能代替体测。')
            st.write('建议先核对填写的次数和时长，再决定是否重新估计。' if cur['prediction'] else '这不等于体能优秀；模型目前不能区分你的耐力是中等还是较好。')
        # A real submission is never compared against a demonstration persona.
        previous=history[-2] if len(history)>1 and not history[-2].get('is_example') and not cur.get('is_example') else None
        result_chart(cur,pack['threshold'],previous,motion)
        v=cur['inputs']
        st.html('<div class="section-eyebrow"><span>你填写的运动画像</span><span>最近 30 天</span></div>')
        summary_tiles(v)
        if abs(cur['score']-pack['threshold'])<.03:st.info('结果接近分界线，小幅输入变化可能改变判断。请先核对填写内容。')
        rare=[CN[k] for k,(lo,hi) in pack['train_quantiles'].items() if not lo<=v[k]<=hi]
        if rare:st.warning('部分输入在训练数据中较少见，估计依据较弱。具体项目见下方详细说明。')
        a,b=st.columns(2)
        a.button('修改填写内容',type='primary',key='edit',on_click=go,args=(1,))
        b.button('清空并重新开始',key='clear',on_click=clear)
        contrib=question_contributions(cur['contributions'],cur['raw']['daily'])
        with st.expander('为什么得到这个结果？'):
            st.write(explanation['meaning'])
            for positive,label in [(True,'较支持偏低判断'),(False,'较支持非偏低判断')]:
                rows=contrib[contrib['贡献']>0] if positive else contrib[contrib['贡献']<0]
                rows=rows.iloc[np.argsort(-rows['贡献'].abs().to_numpy())].head(3)
                if len(rows):st.write(label+'：'+'、'.join(rows['因素'])+'。')
            st.caption('这些是模型依据，不是因果关系；改变某项输入不代表实际体能会随之改变。')
        with st.expander('查看填写内容、评分与局限'):
            st.write(DEFINITION);st.write(REFERENCE);st.write(explanation['boundary'])
            st.write('模型预测能力有限；问得更详细，并未证明主模型更准确。')
            st.json(cur['raw']);st.metric('偏低标签评分',f"{cur['score']:.3f}")
            st.write(f"评分低于{pack['threshold']:.2f}时未提示偏低；达到或超过此值时提示可能偏低。横条圆点按评分从左到右排列。它不是体能分数或疾病概率。")
            if rare:st.write('较少见的输入：'+'、'.join(rare))
            st.bar_chart(contrib.set_index('因素'),horizontal=True)
            st.caption('贡献单位为log-odds，日常状态的三个编码列已合并。')
        if previous is not None:
            with st.expander('与上次结果比较'):
                prev=history[-2];changes=[{'输入':CN[k],'上次':prev['inputs'][k],'本次':v[k]} for k in FEATURES if prev['inputs'][k]!=v[k]]
                if changes:st.dataframe(pd.DataFrame(changes),hide_index=True)
                else:st.write('两次提交的模型特征相同。')
                st.write(f"上次：{'提示偏低' if prev['prediction'] else '未提示偏低'} → 本次：{'提示偏低' if cur['prediction'] else '未提示偏低'}")
                st.caption('这是不同输入的模型结果，不是锻炼前后的实际测量。')
        feedback_panel(cur)
        return
    step_orbit(stage,st.session_state.get('flow_previous_stage',stage),motion)
    if st.session_state.get('history'):st.caption('提交后更新结果，修改期间保留上次结果。')
    if stage==1:
        st.subheader('先填写基本信息')
        a,b,c=st.columns(3)
        num('年龄（岁）','age',a,True);num('身高（厘米）','height',b);num('体重（千克）','weight',c)
        st.caption('年龄范围：20–49岁。')
    elif stage==2:
        st.subheader('最近30天，平时怎么活动？')
        st.selectbox('日常活动状态',DAILY_LABELS+[UNKNOWN],format_func=lambda x:SHORT_DAILY[DAILY_LABELS.index(x)] if x in DAILY_LABELS else x,index=None,placeholder='请选择最接近的一项',key='form_daily',on_change=remember,args=('daily',))
        transport=yesno('有步行或骑车上学、上班、办事吗？','transport')
        if transport=='有':
            a,b=st.columns(2);num('30天里约多少次？','transport_times',a);num('有这种活动那天，共多少分钟？','transport_minutes',b)
        strength=yesno('有力量训练吗？如俯卧撑、举重','strength')
        if strength=='有':num('30天里约练了多少次？','strength_times')
        st.caption('不确定时选“不知道”，不要选“没有”。')
        with st.expander('次数、分钟怎么填？'):
            st.write('次数不是天数，同一天可以有多次活动。通勤分钟填写有通勤活动那天的总时间。力量训练也可在下一步填写；模型分别参考，不会相加为总时长。')
    elif stage==3:
        st.subheader('最后，填写具体运动')
        st.caption('最近30天，每次至少10分钟、让呼吸或心跳加快的休闲锻炼；通勤不重复计入。')
        active=yesno('有这样的运动吗？','sports_status')
        if active=='有':
            count=int(st.session_state['input_draft'].get('n_sports') or 1)
            with st.expander('怎样选强度？同一运动怎么合并？'):
                st.write('中等：稍出汗或呼吸稍加快。较强：大量出汗或呼吸、心率明显加快。同项目同强度请合并次数；强度不同可分开填写。')
            common=[42,23,29,12,13,38,34,43,55,58]
            choices=common+[k for k in SPORTS if k not in common]
            for i in range(count):
                with st.container(border=True):
                    st.markdown(f'**运动 {i+1}**');a,b=st.columns(2)
                    a.selectbox('项目',choices,format_func=lambda x:SPORTS[x],index=None,placeholder='请选择',key=f'form_sport_{i}_code',on_change=remember,args=(f'sport_{i}_code',))
                    b.selectbox('强度',[1,2],format_func=lambda x:'中等' if x==1 else '较强',index=None,placeholder='请选择',key=f'form_sport_{i}_level',on_change=remember,args=(f'sport_{i}_level',))
                    c,d=st.columns(2);num('30天次数',f'sport_{i}_times',c);num('每次分钟',f'sport_{i}_minutes',d)
            def resize(delta):
                n=max(1,min(20,count+delta));st.session_state['input_draft']['n_sports']=n;st.session_state['form_n_sports']=n;st.session_state['flow_errors']=[]
            a,b=st.columns(2)
            a.button('＋ 添加另一项运动',key='add_sport',on_click=resize,args=(1,),disabled=count>=20)
            if count>1:b.button('移除最后一项',key='remove_sport',on_click=resize,args=(-1,))
        elif active=='没有':st.caption('无需填写运动明细，可以直接查看结果。')
    if st.session_state.get('analysis_failed'):
        st.error('本次分析未完成，结果没有更新。填写内容和上次结果均已保留。')
        st.write('可以重试，也可以先修改填写内容；不需要从头填写。')
        st.button('重试本次分析',key='retry_analysis',on_click=submit,
                  args=(pack,payload(),st.session_state.get('analysis_example',False)))
    errors=st.session_state.get('flow_errors',[])
    if errors: st.warning(f'本步还有 {len(errors)} 处需要核对，修改后再继续。')
    for error in errors:st.error(error)
    def advance():
        raw=payload();errors=step_errors(raw,stage);st.session_state['flow_errors']=errors
        if not errors:
            if stage==3:submit(pack,raw)
            else:go(stage+1)
    a,b=st.columns(2)
    a.button('返回首页' if stage==1 else '上一步',key='back',on_click=go,args=(stage-1,))
    b.button({1:'下一步：日常活动',2:'下一步：运动明细',3:'查看结果'}[stage],key='next',type='primary',on_click=advance)
    if st.session_state.get('history'):st.button('查看上次提交的结果',key='last_result',on_click=go,args=(4,))
    st.button('清空并重新开始',key='clear_form',on_click=clear)
