"""Local, accessible SVG presentation. All numbers come from submitted inputs/models."""
from html import escape
import math
import base64
import streamlit as st

INK='#30372e'
GREEN='#52725c'
ORANGE='#984728'

CSS='''
<style>
:root{--paper:#faf7ef;--ink:#30372e;--muted:#697063;--line:#d8d7ca;--green:#52725c}
.stApp,[data-testid="stAppViewContainer"]{background:var(--paper);color:var(--ink)}
[data-testid="stHeader"]{background:rgba(250,247,239,.95)}
[data-testid="stMainBlockContainer"]{max-width:1080px;padding:4.5rem 2.5rem 4rem}
[data-testid="stSidebar"]{background:#f0eee4;border-right:1px solid var(--line)}
[data-testid="stSidebar"] h1{font-size:1.25rem!important;letter-spacing:.02em}
h1{font-size:2.65rem!important;letter-spacing:-.055em;line-height:1.25!important;font-weight:650!important;padding-bottom:.4rem!important}
h2,h3{color:var(--ink);letter-spacing:-.025em}
h3{font-size:1.55rem!important}
p,label{line-height:1.65!important}
[data-testid="stCaptionContainer"]{color:#535e4c!important;opacity:1!important}
input:focus-visible,textarea:focus-visible,[role="radio"]:focus-visible,[role="switch"]:focus-visible,summary:focus-visible{outline:3px solid #52725c!important;outline-offset:3px}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:var(--line)!important;border-radius:20px!important}
[data-testid="stNumberInputContainer"],[data-baseweb="select"]>div{background:#fffdf7!important;border-color:#cfcebf!important;border-radius:12px!important;min-height:48px}
[data-testid="stNumberInputContainer"]:focus-within,[data-baseweb="select"]>div:focus-within{outline:2px solid #52725c;outline-offset:2px}
.stButton button,.stDownloadButton button{border-radius:999px!important;min-height:48px;padding:.55rem 1.4rem;border-color:#b8bdad;font-weight:550}
.stButton button[kind="primary"]{background:#354b3b!important;border-color:#354b3b!important;color:#fffdf7!important}
.stButton button[kind="primary"]:hover{background:#48634f!important;border-color:#48634f!important}
.stButton button[kind="secondary"]{background:#fffdf6;color:var(--ink)}
.stButton button:focus-visible{outline:3px solid #984728;outline-offset:3px}
[data-testid="stAlert"]{border-radius:14px;border:1px solid #d6d7c9}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:14px!important;background:#fcfaf4}
[data-testid="stMetric"]{background:#f1f0e7;border-radius:14px;padding:16px}
.brandline{display:flex;align-items:center;gap:10px;color:#596751;font-size:12px;letter-spacing:.14em;margin:4px 0 22px;font-weight:650}
.brandline img{width:26px;height:26px}
.intro{max-width:660px;font-size:18px;line-height:1.8;color:#5a6455;margin:5px 0 20px}
.section-eyebrow{display:flex;justify-content:space-between;gap:12px;margin:24px 0 12px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:#65705f;letter-spacing:.06em}
.feature-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:16px 0 24px}
.feature-tile{padding:26px 20px;min-width:0;border-right:1px dashed #d1d2c4}
.feature-tile:last-child{border-right:0}
.feature-tile img{width:40px;height:40px;display:block;margin-bottom:24px}
.feature-tile .tile-title{font-size:15px;color:#56624e;margin-bottom:5px}
.feature-tile .tile-value{font-size:30px;line-height:1.3;font-weight:600;letter-spacing:-.04em;color:#30372e}
.feature-tile .tile-value small{font-size:13px;font-weight:400;margin-left:6px;letter-spacing:0}
.feature-tile .tile-copy{font-size:13px;color:#6c7365;margin-top:7px;line-height:1.65}
.feature-grid.home .tile-value{font-size:20px;letter-spacing:0}
.result-summary{background:#f0f2e8;border:1px solid #d5ddcd;border-radius:22px;padding:25px 28px;margin:10px 0}
.result-summary.low{background:#f8eee3;border-color:#dfc9b7}
.result-summary .result-kicker{font-size:12px;color:#5a6a52;letter-spacing:.1em;margin-bottom:10px}
.result-summary.low .result-kicker{color:#965137}
.result-summary h3{margin:0 0 12px;font-size:28px!important}
.result-summary p{margin:0;color:#4f5a49;font-size:15px;line-height:1.8}
@media(max-width:700px){
 [data-testid="stMainBlockContainer"]{padding:4rem 1.1rem 3rem}
 h1{font-size:2.05rem!important}
 .feature-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .feature-tile{padding:20px 16px}
 .feature-tile:nth-child(2){border-right:0}
 .feature-tile:nth-child(-n+2){border-bottom:1px dashed #d1d2c4}
 .feature-tile img{margin-bottom:14px;width:32px;height:32px}
 .feature-tile .tile-value{font-size:26px}
 .result-summary{padding:20px}
 .result-summary h3{font-size:23px!important}
}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}}
</style>
'''

ICONS={
 'leaf':'<path d="M12 37C9 19 23 9 43 8c0 23-13 35-31 29Z"/><path d="m10 43 25-25M23 30l-1-11m1 11 12 1"/>',
 'pulse':'<path d="M4 27h11l5-14 10 29 6-15h12"/><path d="M6 14a22 22 0 0 1 38 0M6 40a22 22 0 0 0 38 0" opacity=".35"/>',
 'compass':'<circle cx="26" cy="26" r="21"/><path d="m34 17-4 14-13 4 4-14Z"/><circle cx="26" cy="26" r="2"/>',
 'rings':'<circle cx="26" cy="26" r="20"/><circle cx="26" cy="26" r="12"/><path d="M26 6v9m20 11h-9M26 46v-9M6 26h9"/>',
 'strength':'<path d="M9 17v18m6-22v26m22-26v26m6-22v18M15 26h22M7 17h4M7 35h4m30-18h4m-4 18h4"/>',
 'sun':'<circle cx="26" cy="26" r="9"/><path d="M26 3v8m0 30v8M3 26h8m30 0h8M10 10l6 6m20 20 6 6M10 42l6-6m20-20 6-6"/>',
}

def icon(name):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52" fill="none" stroke="#4b624e" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    return '<img alt="" src="data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()+'">'

def theme():st.html(CSS)

def brand():
    st.html(f'<div class="brandline">{icon("sun")}运动有迹 <span style="opacity:1">/</span> MOVE & UNDERSTAND</div>')

def tiles(rows,home=False):
    body=''.join(f'<section class="feature-tile">{icon(k)}<div class="tile-title">{escape(title)}</div><div class="tile-value">{escape(value)}<small>{escape(unit)}</small></div><div class="tile-copy">{escape(note)}</div></section>' for k,title,value,unit,note in rows)
    st.html(f'<div class="feature-grid {"home" if home else ""}">{body}</div>')

def home_tiles():
    tiles([
      ('compass','01 · 填写','从日常出发','','年龄、身高体重和运动习惯'),
      ('pulse','02 · 理解','读懂这次估计','','先看结论，再了解模型依据'),
      ('rings','03 · 核对','修改，再比较','','填错了也能返回重新提交'),
      ('leaf','04 · 掌握','由你决定','','无需设备，随时清空输入')],True)

def summary_tiles(values):
    tiles([
      ('compass','运动项目',str(int(values['SportVariety'])),'种','相同项目按一种统计'),
      ('leaf','中等强度运动',f"{values['ModerateMinutes30']:g}",'分钟','最近30天 · 次数 × 每次时长'),
      ('pulse','较强运动',f"{values['VigorousMinutes30']:g}",'分钟','最近30天 · 次数 × 每次时长'),
      ('strength','力量训练',f"{values['StrengthTimes30']:g}",'次','最近30天 · 不与运动时长相加')])

FRAME='''<meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}html,body{overflow:hidden}body{margin:0;font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#30372e;background:transparent}
svg{display:block;width:100%;height:auto}text{font-family:inherit}
.fade{animation:reveal .65s ease both}.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.1s .1s ease forwards}.point{transform-box:fill-box;transform-origin:center;animation:pop .65s .2s both}.halo{transform-box:fill-box;transform-origin:center;animation:pulse 1.2s .55s 2}
@keyframes reveal{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
@keyframes draw{to{stroke-dashoffset:0}}@keyframes pop{from{opacity:0;transform:scale(.5)}to{opacity:1;transform:scale(1)}}@keyframes pulse{0%,100%{opacity:.35;transform:scale(.8)}50%{opacity:.8;transform:scale(1.12)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.draw{stroke-dashoffset:0!important}.wheel,.counter{transform:var(--end)!important}}
body.still *{animation:none!important;transition:none!important}body.still .draw{stroke-dashoffset:0}body.still .wheel,body.still .counter{transform:var(--end)!important}
</style>'''

def frame(body,height,motion=True):
    st.iframe(FRAME+f'<body class="{"" if motion else "still"}">{body}</body>',height='content',alt='问卷进度图' if height==185 else '模型判断位置与提交对比图')

def step_orbit(stage,previous,motion=True):
    """Move only in response to navigation; current form remains a native accessible form."""
    current=max(1,min(3,stage));previous=max(1,min(3,previous))
    angles={1:-24,2:0,3:24};angle=angles[current];before=angles[previous]
    labels=['基本信息','日常活动','运动明细']
    nodes=[]
    for i in range(1,4):
        rad=math.radians(angles[i]);x=450+550*math.sin(rad);y=610-550*math.cos(rad)
        nodes.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#b9c6ad"/><text x="{x:.2f}" y="{y+39:.2f}" text-anchor="middle" font-size="17" fill="{"#30372e" if i==current else "#737b6a"}">{labels[i-1]}</text>')
    # CSS transforms in viewBox coordinates keep the marker on a circular track.
    body=f'''<style>
    .wheel{{transform-origin:450px 610px;--end:rotate({angle}deg);transform:rotate({angle}deg);animation:turn .65s cubic-bezier(.2,.8,.2,1) both}}
    .counter{{transform-origin:450px 60px;--end:rotate({-angle}deg);transform:rotate({-angle}deg);animation:counter .65s cubic-bezier(.2,.8,.2,1) both}}
    @keyframes turn{{from{{transform:rotate({before}deg)}}to{{transform:rotate({angle}deg)}}}}
    @keyframes counter{{from{{transform:rotate({-before}deg)}}to{{transform:rotate({-angle}deg)}}}}
    .orbit{{max-width:850px;margin:0 auto}}@media(max-width:700px){{.orbit svg text{{font-size:26px}}}}.step-count{{font-size:12px;letter-spacing:.08em;color:#65715c;text-align:center;margin:0 0 3px}}
    </style><div class="orbit"><div class="step-count">第 {current} / 3 步 · {labels[current-1]}</div>
    <svg viewBox="0 0 900 175" role="img" aria-label="第{current}步，共三步，{labels[current-1]}">
    <path d="M 65 217 A 550 550 0 0 1 835 217" fill="none" stroke="#d2d4c4" stroke-width="1.4"/>
    {''.join(nodes)}<g class="wheel"><g class="counter"><circle cx="450" cy="60" r="22" fill="#3e5946"/><text x="450" y="66" font-size="17" text-anchor="middle" fill="#fffdf7">{current}</text><circle cx="450" cy="60" r="29" fill="none" stroke="#b8c6ac" stroke-width="1"/></g></g>
    </svg></div>'''
    frame(body,185,motion)

def result_chart(cur,threshold,previous=None,motion=True):
    """A linear, left-to-right track with visible three-decimal model scores."""
    score=float(cur['score']);threshold=float(threshold)
    if not 0 < threshold < 1 or not 0 <= score <= 1:
        raise ValueError('Invalid model score or threshold')
    def label(value):
        return '提示可能偏低' if float(value)>=threshold else '未提示偏低'
    color=ORANGE if score>=threshold else GREEN
    position=score*100;boundary=threshold*100
    start=float(previous['score'])*100 if previous else position
    # Keep the label within the frame; the actual dot is never clamped or rescaled.
    label_position=max(14,min(86,position))
    previous_html=''
    if previous:
        old=float(previous['score']);old_label=label(old)
        old_color=ORANGE if old>=threshold else GREEN
        previous_html=f'<div class="previous"><span>上次提交 · {old_label} · 评分 {old:.3f}</span><div class="previous-track" style="--score:{old*100:.8f}%;--color:{old_color}"><i class="previous-dot"></i></div></div>'
    note='越向右，模型越倾向于提示偏低；不是体能分数或患病概率。'
    if previous:note+=' 两次提交的差别不代表实际体能变化。'
    body=f'''<style>
    .judgment{{background:#fcfaf4;border:1px solid #d5d3c5;border-radius:20px;padding:22px 24px 18px;font-size:14px}}
    .judgment h3{{font-size:17px;margin:0 0 8px;font-weight:600}}
    .result-line{{margin:0;color:var(--color);font-size:20px;font-weight:600}}
    .score-line{{margin:8px 0 0;color:#59634f;font-size:14px}}.score-line strong{{color:#30372e;font-size:20px;font-variant-numeric:tabular-nums;margin-left:6px}}
    .legend{{display:flex;gap:16px;flex-wrap:wrap;margin-top:19px;font-size:13px;line-height:1.6}}
    .legend span{{display:flex;align-items:center;gap:6px}}.key{{width:9px;height:9px;border-radius:50%;display:inline-block;flex:none}}
    .plot{{margin:40px 12px 0;position:relative;height:88px}}
    .track,.previous-track{{height:18px;position:relative;background:linear-gradient(to right,#dce7d5 0 var(--boundary),#f2d4bd var(--boundary) 100%);border-radius:9px}}
    .boundary{{position:absolute;left:var(--boundary);top:-11px;height:40px;border-left:2px dashed #6a705f}}
    .boundary-label{{position:absolute;left:var(--boundary);top:-30px;transform:translateX(-50%);font-size:12px;white-space:nowrap;color:#59634f}}
    .marker{{position:absolute;left:var(--score);top:9px;animation:marker-slide .8s ease both}}
    .dot{{display:block;width:20px;height:20px;border-radius:50%;background:var(--color);border:3px solid #fffdf7;box-shadow:0 0 0 5px color-mix(in srgb,var(--color) 18%,transparent);transform:translate(-50%,-50%)}}
    .current-label{{position:absolute;left:var(--label);top:38px;transform:translateX(-50%);white-space:nowrap;color:var(--color);font-weight:600}}
    .previous{{border-top:1px solid #e0dfd3;padding-top:13px;margin:0 0 14px;font-size:13px;color:#616b58}}
    .previous-track{{margin:13px 12px 4px;height:8px;opacity:.8}}
    .previous-track:after{{content:"";position:absolute;left:var(--boundary);top:-3px;height:14px;border-left:1px dashed #6a705f}}
    .previous-dot{{position:absolute;left:var(--score);top:4px;width:12px;height:12px;border:2px solid var(--color);background:#fcfaf4;border-radius:50%;transform:translate(-50%,-50%)}}
    .chart-note{{font-size:12px;color:#59634f;line-height:1.75;margin:0}}
    @keyframes marker-slide{{from{{left:var(--start);opacity:0}}to{{left:var(--score);opacity:1}}}}
    @media(max-width:480px){{.judgment{{padding:18px 14px}}.legend{{gap:6px 14px}}.result-line{{font-size:18px}}}}
    </style><section class="judgment" style="--score:{position:.8f}%;--start:{start:.8f}%;--boundary:{boundary:.8f}%;--label:{label_position:.8f}%;--color:{color}">
    <h3>本次模型判断</h3><p class="result-line">{label(score)}</p><p class="score-line">本次评分<strong>{score:.3f}</strong></p>
    <div class="legend"><span><i class="key" style="background:{GREEN}"></i>左侧：未提示偏低</span><span><i class="key" style="background:{ORANGE}"></i>右侧：提示可能偏低</span></div>
    <div class="plot" role="img" aria-label="本次结果：{label(score)}，模型评分{score:.3f}。圆点越向右，模型越倾向于提示偏低。">
    <div class="boundary-label">判断分界</div><div class="track"><div class="boundary"></div><div class="marker"><i class="dot"></i></div></div><div class="current-label">● 本次结果</div></div>
    {previous_html}<p class="chart-note">{note}</p></section>'''
    frame(body,320,motion)
