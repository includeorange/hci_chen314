"""A browser-only waiting interaction; no rerun, network or model access."""
import streamlit as st

FIDGET_HTML = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}html,body{margin:0;overflow:hidden}
body{font-family:"Microsoft YaHei",sans-serif;color:#30372e;background:transparent}
.card{border:1px solid #d4d9ca;background:#f7f8ef;border-radius:20px;padding:20px 24px;display:flex;align-items:center;gap:28px}
.copy{flex:1}h2{font-size:18px;margin:0 0 8px}p{font-size:14px;line-height:1.7;margin:4px 0;color:#535e4c}
.play{display:flex;flex-direction:column;align-items:center;min-width:130px}
button{width:88px;height:88px;border-radius:50%;border:2px solid #68856a;background:#e1ead7;color:#354b3b;font:600 15px "Microsoft YaHei",sans-serif;box-shadow:0 6px 0 #bdcbb2;cursor:pointer;touch-action:manipulation}
button:hover{background:#d3e3c5}button:focus-visible{outline:3px solid #984728;outline-offset:5px}
button:active{transform:translateY(4px);box-shadow:0 2px 0 #bdcbb2}
.pop{animation:pop .28s ease-out}@keyframes pop{0%{transform:scale(.9) translateY(4px)}60%{transform:scale(1.04)}100%{transform:scale(1)}}
#count{font-size:13px;color:#535e4c;min-height:24px;margin-top:13px;text-align:center}
@media(max-width:440px){.card{padding:18px 14px;gap:12px}.play{min-width:96px}h2{font-size:16px}button{width:76px;height:76px}}
@media(prefers-reduced-motion:reduce){button{animation:none!important;transform:none!important}}
body.still button{animation:none!important;transform:none!important}
</style></head><body class="MOTION_CLASS">
<section class="card" aria-label="等待时的小互动">
 <div class="copy"><h2>点点放松</h2><p>等待时，可以轻轻按一下泡泡。</p><p>这是可选的小互动，不影响页面加载。</p></div>
 <div class="play"><button id="bubble" type="button" aria-label="按一下泡泡">点一下</button><div id="count" role="status" aria-live="polite">支持鼠标或空格键</div></div>
</section>
<script>
(() => {
 const bubble = document.getElementById('bubble');
 const counter = document.getElementById('count');
 let taps = 0;
 bubble.addEventListener('click', () => {
   taps += 1;
   counter.textContent = '轻轻点了 ' + taps + ' 下';
   bubble.classList.remove('pop');
   void bubble.offsetWidth;
   bubble.classList.add('pop');
 });
 bubble.addEventListener('animationend', () => bubble.classList.remove('pop'));
})();
</script></body></html>'''


def show_opening():
    notice = st.empty()
    if st.session_state.get('_page_opened'):
        return notice
    with notice.container():
        st.info('正在准备页面，请稍候。准备好后会自动显示，你不需要进行其他操作。')
        st.iframe(FIDGET_HTML.replace('MOTION_CLASS','' if st.session_state.get('visual_motion',True) else 'still'),
                  height='content',alt='等待时可选的点泡泡互动，不影响加载')
    return notice


def show_relaxation():
    """Keep the optional interaction accessible even when startup is too fast."""
    with st.sidebar.expander('点点放松 · 随时可玩', expanded=False):
        html = FIDGET_HTML.replace('MOTION_CLASS', '' if st.session_state.get('visual_motion', True) else 'still')
        html = html.replace('等待时的小互动', '可选的放松小互动')
        html = html.replace('等待时，可以轻轻按一下泡泡。', '想歇一下时，轻轻按一下泡泡。')
        html = html.replace('这是可选的小互动，不影响页面加载。', '可随时收起，不影响问卷填写。')
        html = html.replace('.card{border:', '.card{flex-direction:column;text-align:center;border:')
        st.iframe(html, height='content', alt='随时可玩的点泡泡互动，不影响问卷填写')
