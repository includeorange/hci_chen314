"""Assignment 4: fixed validation experiment, selectable global importance."""
import json
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

LABELS={0:'非偏低',1:'偏低'}

def read_result(root):
 return json.loads((Path(root)/'output/results/feature_importance.json').read_text('utf-8'))

def importance_chart(result,selected):
 rows=[]
 for r in sorted(result['importance'],key=lambda x:-x['mean']):
  rows.append({**r,'mean_pp':r['mean']*100,'lower_pp':r['lower']*100,'upper_pp':r['upper']*100,'std_pp':r['std']*100})
 df=pd.DataFrame(rows);order=df['name'].tolist()
 choose=alt.selection_point(name='feature_pick',fields=['feature'],on='click',toggle=False,clear=False)
 base=alt.Chart(df).encode(y=alt.Y('name:N',sort=order,title=None,axis=alt.Axis(labelLimit=240,labelFontSize=13)))
 # A wide, invisible row target keeps zero and tiny negative values selectable.
 targets=base.mark_rect(opacity=0).encode(x=alt.value(0),x2=alt.value(alt.ExprRef(expr='width'))).add_params(choose)
 bars=base.mark_bar(size=23,cornerRadiusEnd=3).encode(
  x=alt.X('mean_pp:Q',title='平衡准确率平均下降（百分点）',scale=alt.Scale(zero=True)),
  color=alt.condition(alt.datum.feature==selected,alt.value('#365b46'),alt.value('#91a38a')),
  tooltip=[alt.Tooltip('name:N',title='输入'),alt.Tooltip('mean_pp:Q',title='平均下降（百分点）',format='.3f'),alt.Tooltip('std_pp:Q',title='标准差（百分点）',format='.3f')])
 errors=base.mark_rule(color='#344738',strokeWidth=1.6).encode(x='lower_pp:Q',x2='upper_pp:Q')
 low=base.mark_tick(color='#344738',size=10,thickness=1.6).encode(x='lower_pp:Q')
 high=base.mark_tick(color='#344738',size=10,thickness=1.6).encode(x='upper_pp:Q')
 zero=alt.Chart(pd.DataFrame({'zero':[0]})).mark_rule(strokeDash=[4,4],color='#888').encode(x='zero:Q')
 # Attach the selection to bars too: clicks on visible marks carry their feature.
 bars=bars.add_params(choose)
 return alt.layer(zero,targets,bars,errors,low,high).properties(height=265).configure_view(stroke=None)

def render_model_judgment(root):
 try:r=read_result(root)
 except (OSError,ValueError):
  st.error('实验结果尚未准备好，请按计算说明生成图表后重新打开。');return
 st.title('模型判断')
 st.write('模型用了哪些输入？打乱哪项输入后，预测表现下降更多？')
 st.caption(f"{r['sample_name']} · {r['n']}条记录 · 与作业三相同的已训练模型")
 meta={x['feature']:x for x in r['importance']}
 st.subheader('这次查看的五项输入')
 st.dataframe(pd.DataFrame([{'输入':x['name'],'单位':x['unit']} for x in r['importance']]),hide_index=True,width='stretch')
 st.caption('模型共使用13项输入，这里选取5项展示；点击图中的条形或所在行，可查看含义和数据分布。')
 st.subheader('打乱哪项输入后，模型表现下降更多？')
 st.write(f"未打乱时的平衡准确率：**{r['baseline']:.1%}**。它是“偏低”和“非偏低”两类各自识别正确率的平均值。")
 selected=st.session_state.setdefault('judgment_selected','Age')
 def on_pick():
  event=st.session_state.get('judgment_chart',{})
  rows=event.get('selection',{}).get('feature_pick',[])
  if rows and rows[0].get('feature') in meta:
   st.session_state['judgment_selected']=rows[0]['feature']
   st.session_state['judgment_selector']=rows[0]['feature']
 st.altair_chart(importance_chart(r,selected),width='stretch',key='judgment_chart',on_select=on_pick,selection_mode='feature_pick',alt='五项输入的置换重要性，横轴为平衡准确率下降百分点，含零点和正负波动。')
 st.caption('每项随机打乱30次。条形为平均下降，细线为±1个标准差（不是置信区间）。右侧下降越多，说明本模型在这批数据上越依赖该输入；零或负值表示本次实验未观察到稳定下降。')
 top=max(r['importance'],key=lambda row:row['mean'])['name']
 st.write(f'这五项输入中，**打乱{top}后平均下降最多**，说明当前模型在这批数据上更依赖它；不能据此认定它与心肺能力关系最强、单独预测最准，或是心肺能力偏低的原因。')
 with st.expander('计算方法与解释范围'):
  st.write('每次只打乱一项输入，其他输入、真实标签、模型和0.15判断阈值保持不变。用原平衡准确率减去打乱后的平衡准确率，得到本次下降值。')
  st.write('负值表示打乱后分数反而上升，不代表这项输入“有害”。特征之间可能相关，较小的重要性也不等于这个问题没有价值。')
  st.write('这是整批验证记录上的模型依赖程度，不能单独解释某一条记录为什么被分类，更不能确定个人患病原因。模型的目标是原体能测试的偏低分层，不是疾病诊断。')
 def on_selector():st.session_state['judgment_selected']=st.session_state['judgment_selector']
 st.selectbox('查看某项输入（也可点击上图）',list(meta),index=list(meta).index(selected),format_func=lambda k:meta[k]['name'],key='judgment_selector',on_change=on_selector)
 selected=st.session_state.get('judgment_selected',selected);item=meta[selected];d=r['distributions'][selected]
 st.subheader(item['name']+'：含义与分布')
 st.write(item['meaning']+' 单位：'+item['unit']+'。')
 a,b,c=st.columns(3)
 a.metric('有效样本',str(d['n']))
 b.metric('缺失记录',str(d['missing']))
 c.metric('中位数',f"{d['median']:g}")
 df=pd.DataFrame(d['bins'])
 dist=alt.Chart(df).mark_bar(color='#52715b',cornerRadiusTopLeft=3,cornerRadiusTopRight=3).encode(x=alt.X('label:N',sort=df.label.tolist(),title=item['unit'],axis=alt.Axis(labelAngle=0,labelLimit=130)),y=alt.Y('count:Q',title='人数'),tooltip=[alt.Tooltip('label:N',title='区间'),alt.Tooltip('count:Q',title='人数')]).properties(height=230)
 st.altair_chart(dist,width='stretch',key='judgment_distribution',alt=item['name']+'的验证集分布，各区间人数总计1195。')
 st.caption(f"取值范围：{d['min']:g}–{d['max']:g} {item['unit']}。各区间合计{d['n']}条，全部来自同一验证集。"+(' BMI区间仅用于展示分布。' if selected=='BMI' else ''))
 st.subheader('原始输入下的两个预测案例')
 st.write('**两条不同记录，输入都未打乱。** 左边预测正确，右边预测错误。')
 st.write('上方重要性图比较“模型依赖哪项输入”；这里核对“具体预测与真实标签是否一致”。这两个案例不能比较输入的重要性，也不能解释个人原因。')
 for col,case in zip(st.columns(2),r['cases']):
  with col:
   with st.container(border=True):
    st.markdown('**原始输入 · '+case['kind']+' · '+case['record_id']+'**')
    st.write('真实标签：**'+LABELS[case['label']]+'**')
    st.write('模型输出：**'+LABELS[case['prediction']]+'**')
    st.write(f"模型评分：**{case['score']:.3f}**")
    st.dataframe(pd.DataFrame([{'输入':x['name'],'取值':f"{case['inputs'][f]:g}",'单位':x['unit']} for f,x in meta.items()]),hide_index=True,width='stretch')
    st.caption('当前查看：'+item['name']+f" = {case['inputs'][selected]:g} "+item['unit'])
 with st.expander('两条记录的完整13项输入'):
  cases=r['cases']
  st.dataframe(pd.DataFrame([{'输入':r['input_names'][f],'正确案例':cases[0]['inputs'][f],'错误案例':cases[1]['inputs'][f]} for f in r['features']]),hide_index=True,width='stretch')
  st.caption('日常活动的三列是同一个分类问题的编码：符合该状态为1，否则为0；三列均0表示“大多坐着”。')
 st.caption('真实标签来自原调查的体能测试参考分级。评分≥0.15判为偏低；评分不是体能分数或患病概率。'+r['case_rule'])
