import {RaiseCounter, classifyPose} from './counter.mjs?v=5.5';
import {actionFeedback, LightMonitor, meanLuma} from './feedback.mjs?v=5.5';
const $=id=>document.getElementById(id), engine=new RaiseCounter();
const video=$('video'), canvas=$('overlay'), ctx=canvas.getContext('2d');
const mirror=document.createElement('canvas'), mirrorCtx=mirror.getContext('2d'), STEP=50;
const lightCanvas=document.createElement('canvas');lightCanvas.width=64;lightCanvas.height=48;
const lightCtx=lightCanvas.getContext('2d',{willReadFrequently:true}),light=new LightMonitor();
let lastLightTime=-Infinity,lightReadable=true;
let source='camera', file=null, fileUrl=null, fileReady=false, stream=null;
let model=null, modelPromise=null, generation=0, opening=false, mediaWait=null, wake=null;
let lastVideoTime=-1,lastStatus='',lastTotal=0,lastCount=-Infinity,modelTime=-1,modelEpoch=0;
let processed=0,samples=0,completed=false,wallOrigin=0,elapsed=0;
const active=()=>['running','paused'].includes(engine.mode);
const now=()=>source==='video'?processed:performance.now();
const format=ms=>`${Math.floor(ms/60000)}:${((ms/1000)%60).toFixed(1).padStart(4,'0')}`;
const resize=()=>window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:document.body.scrollHeight+8},'*');
window.addEventListener('message',e=>{if(e.source===window.parent&&e.data?.type==='streamlit:render')resize();});
window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');
new ResizeObserver(resize).observe(document.body);
function message(title,detail,warning=false){
  const key=title+detail+warning;if(key===lastStatus)return;lastStatus=key;
  $('statusTitle').textContent=title;$('statusDetail').textContent=detail;$('statusBox').classList.toggle('warning',warning);
}
function controls(){
  const on=!!stream?.getVideoTracks().some(t=>t.readyState==='live');
  $('cameraStatus').textContent=on?(engine.mode==='paused'?'摄像头开启 · 计数暂停':'摄像头开启'):'摄像头已关闭';
  $('cameraStatus').classList.toggle('on',on);$('liveBadge').hidden=source==='camera'?!on:!fileReady;
  $('liveBadge').textContent=source==='camera'?'镜像画面 · 使用你的右手':'视频原画面 · 检测人物的右手';
  $('placeholder').hidden=on||(source==='video'&&fileReady);
  $('start').disabled=opening||active()||(source==='video'&&!fileReady);
  $('start').textContent=opening?'正在准备…':source==='video'?(engine.mode==='ended'?'重新检测视频':'开始检测视频'):(engine.mode==='ended'?'开始新一轮':'开启摄像头并准备');
  $('pause').disabled=!active();$('pause').textContent=engine.mode==='paused'?'继续':'暂停';
  $('stop').disabled=!opening&&!active();$('stop').textContent=source==='video'?'结束检测':'结束并关闭';
  $('videoFile').disabled=opening||active();$('mirroredFile').disabled=opening||active();
  document.querySelectorAll('input[name=source]').forEach(x=>x.disabled=opening||active());
  $('add').disabled=engine.mode==='idle'||opening;$('remove').disabled=engine.mode==='idle'||opening||engine.total===0;
  $('export').disabled=!engine.events.length;$('total').textContent=engine.total;
  $('countBreakdown').textContent=`自动计数 ${engine.auto} 次 · 手动调整 ${engine.adjustment>0?'+':''}${engine.adjustment} 次`;
  if(lastTotal!==engine.total){$('total').classList.remove('pulse');void $('total').offsetWidth;$('total').classList.add('pulse');lastTotal=engine.total;}
}
function phase(){
  ['stepDown','stepUp','stepCount'].forEach(id=>$(id).classList.remove('active'));
  const feedback=actionFeedback(engine,{source,recentCount:performance.now()-lastCount<1200});
  if(feedback.step)$(feedback.step).classList.add('active');
  $('readiness').textContent=feedback.readiness;$('readiness').classList.toggle('ready',feedback.ready);
  message(feedback.title,feedback.detail,feedback.warning);
}
async function prepareModel(){
  if(model)return model;
  if(!modelPromise)modelPromise=(async()=>{
    const {FilesetResolver,PoseLandmarker}=await import('./vendor/vision_bundle.mjs');
    const files=await FilesetResolver.forVisionTasks(new URL('./vendor/wasm',import.meta.url).href);
    return PoseLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:new URL('./vendor/pose_landmarker_lite.task',import.meta.url).href,delegate:'CPU'},runningMode:'VIDEO',numPoses:1,minPoseDetectionConfidence:.6,minPosePresenceConfidence:.6,minTrackingConfidence:.6});
  })().catch(e=>{modelPromise=null;throw e;});
  model=await modelPromise;return model;
}
function closeCamera(){
  stream?.getTracks().forEach(t=>{t.onended=null;t.stop();});stream=null;video.pause();video.srcObject=null;
  $('jointStatus').textContent='当前识别情况：检测已停止。';
}
function reset(){
  engine.reset();engine.mode='idle';processed=0;samples=0;completed=false;elapsed=0;
  light.reset();lastLightTime=-Infinity;lightReadable=true;$('lightHint').hidden=true;
  $('readiness').classList.remove('ready');$('readiness').textContent='尚未开始';
  $('progress').value=0;$('progressText').textContent='等待开始';$('correctionNote').textContent='撤销多记的，补上漏记的。';ctx.clearRect(0,0,canvas.width,canvas.height);
}
function finish(detail,success=false){
  generation++;mediaWait?.abort();wake?.();wake=null;opening=false;elapsed=wallOrigin?performance.now()-wallOrigin:0;
  engine.end(now());closeCamera();completed=success;if(source==='camera')ctx.clearRect(0,0,canvas.width,canvas.height);controls();
  $('readiness').classList.remove('ready');$('readiness').textContent='检测已结束';$('lightHint').hidden=true;
  message(source==='camera'?'已结束，摄像头已关闭':success?'视频检测完成':'视频检测已结束',detail||(source==='video'?'已保留检测到当前位置的结果；可以修正次数或从头重新检测。':'本次计数已保留，可修正次数或保存记录。开始新一轮会归零。'));
  ['stepDown','stepUp','stepCount'].forEach(id=>$(id).classList.remove('active'));
}
function releaseFile(){video.pause();video.removeAttribute('src');video.load();if(fileUrl)URL.revokeObjectURL(fileUrl);fileUrl=null;fileReady=false;file=null;}
function size(){canvas.width=mirror.width=video.videoWidth;canvas.height=mirror.height=video.videoHeight;document.querySelector('.view').style.aspectRatio=`${video.videoWidth}/${video.videoHeight}`;}
function waitMedia(event,action,signal){
  return new Promise((resolve,reject)=>{
    const cleanup=()=>{clearTimeout(timer);video.removeEventListener(event,ok);video.removeEventListener('error',bad);signal?.removeEventListener('abort',cancel);};
    const ok=()=>{cleanup();resolve();},bad=()=>{cleanup();reject(Error('VIDEO_DECODE'));},cancel=()=>{cleanup();reject(new DOMException('Cancelled','AbortError'));};
    const timer=setTimeout(bad,15000);video.addEventListener(event,ok,{once:true});video.addEventListener('error',bad,{once:true});signal?.addEventListener('abort',cancel,{once:true});
    if(signal?.aborted){cancel();return;}try{action();}catch(e){cleanup();reject(e);}
  });
}
async function seek(seconds,signal){
  if(Math.abs(video.currentTime-seconds)<.00001&&video.readyState>=2)return;
  await waitMedia('seeked',()=>{video.currentTime=seconds;},signal);
  if(video.readyState<2)await waitMedia('loadeddata',()=>{},signal);
}
document.querySelectorAll('input[name=source]').forEach(input=>input.onchange=()=>{
  if(active()||opening)return;generation++;closeCamera();releaseFile();source=input.value;reset();
  document.body.dataset.source=source;$('filePanel').hidden=source!=='video';$('videoFile').value='';$('fileInfo').textContent='尚未选择视频';$('mirroredFile').checked=false;
  $('placeholder').querySelector('strong').textContent=source==='video'?'选择一段抬手动作视频':'让双肩、右肘和右手腕入镜';
  $('placeholder').querySelector('span').textContent=source==='video'?'在本机检测，无需打开摄像头。':'先把右手放在胸前、低于肩部。';
  controls();message(source==='video'?'先选择视频':'先确认放下，再开始',source==='video'?'选择文件后，点击“开始检测视频”。':'开启后先把手腕保持在放下线以下，等“可以举手了”再做第一次动作。');
});
$('videoFile').onchange=async()=>{
  const selected=$('videoFile').files[0];if(!selected||active()||opening)return;
  const token=++generation;mediaWait?.abort();mediaWait=new AbortController();closeCamera();releaseFile();reset();opening=true;controls();message('正在读取视频','正在检查视频能否播放。');
  try{
    if(!selected.size||(!selected.type.startsWith('video/')&&!/\.(mp4|webm|mov|m4v)$/i.test(selected.name)))throw Error('VIDEO_DECODE');
    fileUrl=URL.createObjectURL(selected);await waitMedia('loadeddata',()=>{video.src=fileUrl;video.load();},mediaWait.signal);
    if(!Number.isFinite(video.duration))await seek(1e10,mediaWait.signal);
    if(!Number.isFinite(video.duration)||video.duration<=0||!video.videoWidth)throw Error('VIDEO_DECODE');
    await seek(0,mediaWait.signal);if(token!==generation)return;
    file=selected;fileReady=true;opening=false;size();$('fileInfo').textContent=`${file.name} · ${format(video.duration*1000)} · ${(file.size/1024/1024).toFixed(1)} MB`;
    controls();message('视频已就绪','点击“开始检测视频”，查看画面、进度与抬手次数。');
  }catch(e){if(token!==generation)return;releaseFile();opening=false;$('videoFile').value='';$('fileInfo').textContent='视频读取失败';controls();message('无法读取这段视频','请检查文件是否完整，或改用 MP4（H.264）／WebM。转换格式后可以重新选择。',true);}
};
function draw(points,guides){
  ctx.clearRect(0,0,canvas.width,canvas.height);if(!points)return;
  if(guides){
    const rect=canvas.getBoundingClientRect(),shownWidth=Math.min(rect.width,rect.height*canvas.width/canvas.height);
    const unit=canvas.width/Math.max(1,shownWidth);
    ctx.save();
    // The camera canvas is mirrored with CSS. Counter-mirror labels so text stays readable.
    if(source==='camera'){ctx.translate(canvas.width,0);ctx.scale(-1,1);}
    ctx.lineWidth=2*unit;ctx.font=`600 ${14*unit}px "Microsoft YaHei",sans-serif`;ctx.textBaseline='middle';
    for(const [yNorm,label,color,side] of [[guides.raiseY,'举起线','#285b39',-1],[guides.lowerY,'放下线','#8b482c',1]]){
      const y=yNorm*canvas.height;
      if(y<0||y>canvas.height)continue;
      ctx.strokeStyle=color;ctx.setLineDash([7*unit,5*unit]);ctx.beginPath();ctx.moveTo(12*unit,y);ctx.lineTo(canvas.width-12*unit,y);ctx.stroke();ctx.setLineDash([]);
      const textY=Math.min(canvas.height-13*unit,Math.max(13*unit,y+side*16*unit)),w=ctx.measureText(label).width;
      ctx.fillStyle='#faf7eff2';ctx.fillRect(12*unit,textY-11*unit,w+12*unit,22*unit);ctx.fillStyle=color;ctx.fillText(label,18*unit,textY);
    }
    ctx.restore();
  }
  ctx.lineWidth=4;ctx.strokeStyle='#e8eebf';ctx.fillStyle='#e5ab70';
  for(const [a,b] of [[11,12],[12,14],[14,16]]){const p=points[a],q=points[b];if(!p||!q||p.visibility<.65||q.visibility<.65)continue;ctx.beginPath();ctx.moveTo(p.x*canvas.width,p.y*canvas.height);ctx.lineTo(q.x*canvas.width,q.y*canvas.height);ctx.stroke();}
  for(const i of [11,12,14,16]){const p=points[i];if(!p||p.visibility<.65)continue;ctx.beginPath();ctx.arc(p.x*canvas.width,p.y*canvas.height,6,0,Math.PI*2);ctx.fill();}
}
function updateLighting(image,time){
  if(!lightReadable||time-lastLightTime<200)return;
  lastLightTime=time;
  try{
    const w=video.videoWidth,h=video.videoHeight;
    lightCtx.drawImage(image,w*.15,h*.1,w*.7,h*.7,0,0,64,48);
    const dark=light.update(meanLuma(lightCtx.getImageData(0,0,64,48).data),time);
    $('lightHint').hidden=!dark;
    $('lightHint').textContent=source==='video'?'视频画面偏暗，手腕位置可能不稳。可暂停核对，确有漏计再补记；重新拍摄时请补光。':'画面偏暗。若手腕圆点漂移，请开灯或面向光源，让右手腕清楚入镜。';
  }catch{lightReadable=false;$('lightHint').hidden=true;}
}
function processFrame(time){
  const started=performance.now();let image=video;
  if(source==='video'&&$('mirroredFile').checked){mirrorCtx.setTransform(-1,0,0,1,mirror.width,0);mirrorCtx.drawImage(video,0,0);mirrorCtx.resetTransform();image=mirror;}
  updateLighting(image,time);
  modelTime=Math.max(modelTime+1,source==='video'?modelEpoch+time:started);
  const result=model.detectForVideo(image,modelTime),points=result.landmarks[0];
  const state=classifyPose(points,video.videoWidth,video.videoHeight,{source,mirrored:source==='camera'||$('mirroredFile').checked});
  $('jointStatus').textContent=points?'当前识别情况：'+state.joints.map(j=>`${j.name}：${j.label}`).join('；')+'。':'当前识别情况：未检测到人体。';
  const event=engine.frame(state.pose,time,state.reason);
  const drawable=state.pose==='unknown'?null:points;
  draw(source==='video'&&$('mirroredFile').checked?drawable?.map(p=>({...p,x:1-p.x})):drawable,state.guides);samples++;
  if(event){lastCount=performance.now();event.inference_ms=Math.round(lastCount-started);controls();
    if(source==='video')event.processing_elapsed_ms=Math.round(lastCount-wallOrigin);
    else{const origin=engine.origin;requestAnimationFrame(()=>{event.ui_frame_callback_ms=Math.round(performance.now()-origin);});}}
  phase();
}
function cameraLoop(token){
  if(token!==generation||!stream)return;
  if(engine.mode==='running'&&video.readyState>=2&&video.currentTime!==lastVideoTime){lastVideoTime=video.currentTime;try{processFrame(performance.now());}catch(e){console.error(e);finish('识别中断。摄像头已关闭，请重新开始。');return;}}
  if(token===generation)requestAnimationFrame(()=>cameraLoop(token));
}
async function videoLoop(token){
  const end=Math.max(0,video.duration*1000-1),signal=mediaWait.signal;
  try{
    for(let n=0;;n++){
      if(token!==generation)return;if(engine.mode==='paused')await new Promise(resolve=>{wake=resolve;});if(token!==generation)return;
      const time=Math.min(n*STEP,end);await seek(time/1000,signal);if(token!==generation)return;
      if(engine.mode==='paused')await new Promise(resolve=>{wake=resolve;});if(token!==generation)return;
      processed=time;processFrame(time);$('progress').value=Math.min(100,100*time/(video.duration*1000));$('progressText').textContent=`${format(time)} / ${format(video.duration*1000)}`;
      if(time>=end)break;await new Promise(resolve=>setTimeout(resolve,0));
    }
    $('progress').value=100;finish(`已检测完整视频，自动计数 ${engine.auto} 次。可撤销误计、补记漏计，或保存记录。`,true);
  }catch(e){if(token!==generation)return;console.error(e);finish('视频检测中断，当前结果仅覆盖已处理部分。可从头重试，或更换可正常播放的视频。');}
}
$('start').onclick=async()=>{
  if(opening||active()||(source==='video'&&!fileReady))return;
  const token=++generation;mediaWait?.abort();mediaWait=new AbortController();reset();opening=true;controls();message('正在准备识别','正在加载本机模型，请稍候。');
  try{
    // Independent runs begin with a fresh tracker. Asset downloads are served locally.
    if(model){model.close?.();model=null;modelPromise=null;}
    await prepareModel();if(token!==generation)return;
    if(source==='camera'){
      if(!navigator.mediaDevices?.getUserMedia)throw Error('INSECURE_CONTEXT');
      message('请允许使用摄像头','在浏览器提示中允许摄像头访问；也可以点击“结束并关闭”取消。');
      const acquired=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480},facingMode:'user'},audio:false});
      if(token!==generation){acquired.getTracks().forEach(t=>t.stop());return;}
      stream=acquired;video.srcObject=stream;await video.play();if(token!==generation)return;size();stream.getVideoTracks().forEach(t=>{t.onended=()=>finish('摄像头连接已断开，本次计数已保留。');});
    }else await seek(0,mediaWait.signal);
    if(token!==generation)return;
    processed=0;samples=0;completed=false;wallOrigin=performance.now();modelEpoch=Math.max(wallOrigin,modelTime+1);
    engine.start(source==='video'?0:wallOrigin,source==='video'?{type:'video',file_name:file.name,duration_ms:Math.round(video.duration*1000),sample_interval_ms:STEP,mirror_restored:$('mirroredFile').checked}:{type:'camera'});
    lastVideoTime=-1;lastCount=-Infinity;opening=false;$('progress').value=0;$('correctionNote').textContent='撤销多记的，补上漏记的。';controls();phase();
    if(source==='video')void videoLoop(token);else cameraLoop(token);
  }catch(e){if(token!==generation)return;closeCamera();opening=false;controls();
    const detail=source==='video'?'模型或视频未能启动。检查文件是否完整后重试。':e.name==='NotAllowedError'?'未获得摄像头权限。请在浏览器地址栏的权限设置中允许摄像头，再重新开始。':e.name==='NotFoundError'?'未找到摄像头，请连接设备后重新开始。':e.name==='NotReadableError'?'摄像头可能被其他应用占用，请关闭其他摄像头应用后重试。':e.message==='INSECURE_CONTEXT'?'请通过本机 localhost 地址或 HTTPS 链接打开应用。':'模型或摄像头未能启动。请检查模型文件，并使用较新的 Chrome 或 Edge。';
    message('还没有开始计数',detail,true);console.error(e);}
};
function pauseRun(){engine.pause(now(),source==='video');$('readiness').classList.remove('ready');$('readiness').textContent='已暂停 · 不计数';message(source==='video'?'视频检测已暂停':'计数已暂停',source==='video'?'画面停在当前位置，点击“继续”接着检测。':'摄像头仍开启。点击“继续”后，请先放下右手。');controls();}
$('pause').onclick=()=>{if(engine.mode==='running')pauseRun();else if(engine.mode==='paused'){engine.resume(now(),source==='video');wake?.();wake=null;phase();controls();}};
$('stop').onclick=()=>finish();
for(const [id,delta] of [['remove',-1],['add',1]])$(id).onclick=()=>{if(engine.correct(delta,now())){$('correctionNote').textContent=`${delta>0?'已补记':'已撤销'} 1 次，当前共 ${engine.total} 次。`;controls();}};
$('export').onclick=()=>{
  const report={...engine.report(),processed_samples:samples};
  if(engine.source?.type==='video')Object.assign(report,{completed,processed_until_ms:Math.round(processed),processing_elapsed_ms:Math.round(engine.mode==='ended'?elapsed:performance.now()-wallOrigin)});
  const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=source==='video'?'视频抬手计数记录.json':'抬手计数记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);
};
document.addEventListener('visibilitychange',()=>{if(!document.hidden)return;if(source==='camera'&&(stream||opening))finish('离开页面时已自动关闭摄像头，本次计数已保留。');else if(source==='video'&&engine.mode==='running')pauseRun();});
window.addEventListener('pagehide',()=>{generation++;mediaWait?.abort();wake?.();closeCamera();releaseFile();});
controls();resize();
