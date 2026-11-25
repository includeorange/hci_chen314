// Feedback does not infer missing actions or alter automatic counts.
export function actionFeedback(engine, {source='camera', recentCount=false}={}) {
  const recorded=source==='video';
  if(engine.phase==='unclear')return {
    title:recorded?'此段画面不清，暂不计数':'暂不计数，请调整位置',
    detail:engine.reason,warning:true,step:null,ready:false,
    readiness:recorded?'等待清晰的放下动作':'未就绪 · 调整后先保持放下',
  };
  if(engine.armed)return {
    title:recorded?'已确认放下，等待举起':'已就绪，可以举手了',
    detail:recorded?'已识别到稳定的放下动作，继续检测手腕举过上方“举起线”。':'现在把手腕举过上方“举起线”，停一下，记 1 次。',
    warning:false,step:'stepUp',ready:true,readiness:recorded?'起点已确认':'已就绪 · 可以举手了',
  };
  if(recentCount&&engine.auto>0)return {
    title:'已记 1 次',detail:'保持举起不会重复计数；手腕降过“放下线”并停一下，才能准备下一次。',
    warning:false,step:'stepCount',ready:false,readiness:'本次已计数 · 等待放下',
  };
  if(engine.auto===0&&engine.candidate==='up')return {
    title:'未确认放下，未自动计数',
    detail:recorded?'此前没有识别到稳定的放下位置，无法确认完整动作。继续等待后续放下；核对视频后，确有漏计可用“补记一次”。':'此前没有识别到稳定的放下位置。请先降过“放下线”，等“可以举手了”再举；确有漏计可用“补记一次”。',
    warning:true,step:'stepDown',ready:false,readiness:'起点未确认 · 暂不计数',
  };
  return {
    title:engine.auto===0?'先确认放下，再开始':'先放下，准备下一次',
    detail:recorded?'等待手腕低于“放下线”并停留约 0.2 秒；两线之间不算放下。':'手腕保持在“放下线”以下，等提示“可以举手了”再举起。不必将整条手臂垂到底。',
    warning:false,step:'stepDown',ready:false,readiness:engine.auto===0?'准备中 · 等待确认放下':'等待放下 · 准备下一次',
  };
}

// A coarse image-brightness reminder, not a lighting diagnosis or confidence score.
// It never gates counting: clothing, skin tone and exposure also affect pixel values.
export const LIGHT_CONFIG=Object.freeze({darkBelow:35,clearAbove:50,stableMs:300});
export function meanLuma(rgba){
  if(!rgba?.length||rgba.length%4)return null;
  let sum=0;
  for(let i=0;i<rgba.length;i+=4)sum+=.2126*rgba[i]+.7152*rgba[i+1]+.0722*rgba[i+2];
  return sum/(rgba.length/4);
}
export class LightMonitor {
  constructor(){this.reset();}
  reset(){this.dark=false;this.since=null;this.last=null;}
  update(level,time){
    if(!Number.isFinite(level)||!Number.isFinite(time))return this.dark;
    if(this.last!==null&&(time<this.last||time-this.last>1000))this.since=null;
    this.last=time;
    const changing=this.dark?level>=LIGHT_CONFIG.clearAbove:level<LIGHT_CONFIG.darkBelow;
    if(!changing){this.since=null;return this.dark;}
    if(this.since===null)this.since=time;
    if(time-this.since>=LIGHT_CONFIG.stableMs){this.dark=!this.dark;this.since=null;}
    return this.dark;
  }
}
