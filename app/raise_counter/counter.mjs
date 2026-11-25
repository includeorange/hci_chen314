// Counting rules are separate from the vision model, so each can be evaluated.
export const CONFIG = Object.freeze({visibility: 0.65, margin: 0.15, stableMs: 180, maxGapMs: 300});

export const JOINTS = Object.freeze([{id:11,name:'左肩'},{id:12,name:'右肩'},{id:14,name:'右肘'},{id:16,name:'右手腕'}]);

// Directions refer to the image the user sees, including camera mirroring.
export function inspectJoints(landmarks, {mirrored = false} = {}) {
  return JOINTS.map(({id,name}) => {
    const p = landmarks?.[id];
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) return {id,name,issue:'missing',edges:[],label:'未定位到'};
    const x = mirrored ? 1-p.x : p.x, edges=[];
    if (x < .02) edges.push('left'); else if (x > .98) edges.push('right');
    if (p.y < .02) edges.push('top'); else if (p.y > .98) edges.push('bottom');
    if (edges.length) return {id,name,issue:'outside',edges,label:'靠近画面'+edges.map(e=>({left:'左侧',right:'右侧',top:'上方',bottom:'下方'}[e])).join('、')+'或出画'};
    const weak = !Number.isFinite(p.visibility) || p.visibility < CONFIG.visibility || (p.presence !== undefined && p.presence < CONFIG.visibility);
    // The elbow must be positioned in frame, but its visibility score alone
    // must not recreate the over-strict 5.0 gate when shoulder/wrist are valid.
    if (weak) {
      const near=[];if(x<.1)near.push('left');else if(x>.9)near.push('right');
      if(p.y<.1)near.push('top');else if(p.y>.9)near.push('bottom');
      return {id,name,issue:id===14?null:'unclear',edges:near,label:id===14?'位置在画面内，可见性偏低':'暂未看清'};
    }
    return {id,name,issue:null,edges:[],label:'在画面内'};
  });
}
export function framingFeedback(joints, {source = 'camera'} = {}) {
  const issues=joints.filter(j=>j.issue);
  if(!issues.length)return '';
  const names=issues.map(j=>j.name).join('、');
  if(source==='video')return issues.map(j=>`${j.name}${j.label}`).join('；')+'。本段不计数，继续检测后续画面；复测时请使用双肩、右肘和右手腕完整入镜的片段。';
  const edges=new Set(issues.flatMap(j=>j.edges));
  if(edges.has('left')&&edges.has('right'))return `${names}未完整入镜：请后退一点，让双肩和右臂都回到画面中。`;
  const first=issues[0], moves=[];
  if(first.edges.includes('left'))moves.push('向画面右侧移动');
  if(first.edges.includes('right'))moves.push('向画面左侧移动');
  if(first.edges.includes('top')||first.edges.includes('bottom'))moves.push('稍微后退，或调整镜头上下角度');
  const action=moves.length?moves.join('，'):first.id===14?'把右肘收回画面内，必要时稍微后退':first.id===16?'把右手放在胸前、低于肩部，让手腕入镜':'让双肩正对摄像头，并移开遮挡';
  return `${first.name}${first.label}，请${action}。`+(issues.length>1?`同时请让${issues.slice(1).map(j=>j.name).join('、')}完整入镜。`:'');
}
export function poseGuides(landmarks, width, height) {
  const left=landmarks?.[11],right=landmarks?.[12];
  if(!left||!right||!(width>0&&height>0)||![left.x,left.y,right.x,right.y].every(Number.isFinite))return null;
  const scale=Math.hypot((left.x-right.x)*width,(left.y-right.y)*height);
  if(scale<width*.10)return null;
  const gap=CONFIG.margin*scale/height;
  return {shoulderY:right.y,raiseY:right.y-gap,lowerY:right.y+gap,scale};
}
export function classifyPose(landmarks, width, height, options = {}) {
  const joints=inspectJoints(landmarks,options);
  if (!landmarks?.length) return {pose:'unknown',reason:options.source==='video'?'本段未检测到人体，暂不计数并继续检测后续画面。':'请让双肩、右肘和右手腕完整出现在画面中。',joints};
  if(joints.some(j=>j.issue)) return {pose:'unknown',reason:framingFeedback(joints,options),joints};
  const [right, wrist] = [landmarks[12],landmarks[16]];
  const guides=poseGuides(landmarks,width,height);
  if (!guides) return {pose:'unknown',reason:options.source==='video'?'视频中的肩部距离过小，人物可能过远或侧转。本段不计数，继续检测后续画面。':'距离太远或身体侧转，请靠近一点并正对摄像头。',joints};
  const scale=guides.scale;
  const offset = (right.y-wrist.y)*height / scale;
  return {pose: offset >= CONFIG.margin ? 'up' : offset <= -CONFIG.margin ? 'down' : 'middle', offset,joints,guides};
}

export class RaiseCounter {
  constructor() { this.mode = 'idle'; this.reset(); }
  reset() {
    this.auto = 0; this.adjustment = 0; this.events = []; this.origin = 0;
    this.armed = false; this.candidate = null; this.candidateSince = 0;
    this.lastFrame = null; this.phase = 'ready'; this.reason = ''; this.sequence = 0;
  }
  get total() { return this.auto + this.adjustment; }
  log(type, time, extra = {}) {
    const event = {id: ++this.sequence, type, time_ms: Math.round(time-this.origin), ...extra};
    this.events.push(event); return event;
  }
  start(time, source = {type: 'camera'}) { this.reset(); this.source = source; this.origin = time; this.mode = 'running'; this.phase = 'need_down'; this.log('start', time); }
  pause(time, preservePose = false) {
    if (this.mode !== 'running') return;
    this.mode = 'paused'; this.savedPhase = this.phase; if (!preservePose) this.disarm(); this.phase = 'paused'; this.log('pause', time);
  }
  resume(time, preservePose = false) {
    if (this.mode !== 'paused') return;
    this.mode = 'running'; if (!preservePose) this.disarm(); this.phase = preservePose ? this.savedPhase : 'need_down'; this.log('resume', time);
  }
  end(time) {
    if (this.mode === 'idle' || this.mode === 'ended') return;
    this.mode = 'ended'; this.disarm(); this.phase = 'ended'; this.log('end', time);
  }
  disarm() { this.armed = false; this.candidate = null; this.lastFrame = null; }
  correct(delta, time) {
    if (!['running','paused','ended'].includes(this.mode) || ![-1,1].includes(delta) || this.total+delta < 0) return false;
    this.adjustment += delta;
    this.log(delta === 1 ? 'manual_add' : 'manual_remove', time, {total: this.total});
    return true;
  }
  frame(pose, time, reason = '') {
    if (this.mode !== 'running') return null;
    if (!['up','down','middle'].includes(pose)) {
      if (this.phase !== 'unclear' || this.reason !== reason) this.log('tracking_lost', time, {reason});
      this.disarm(); this.phase = 'unclear'; this.reason = reason; return null;
    }
    if (this.lastFrame !== null && (time-this.lastFrame > CONFIG.maxGapMs || time < this.lastFrame)) this.disarm();
    this.lastFrame = time;
    this.reason = '';
    if (pose === 'middle') {
      this.candidate = null;
      this.phase = this.armed ? 'raise' : 'need_down';
      return null;
    }
    if (pose !== this.candidate) { this.candidate = pose; this.candidateSince = time; }
    if (time-this.candidateSince < CONFIG.stableMs) {
      this.phase = this.armed ? 'raise' : 'need_down'; return null;
    }
    if (pose === 'down') { this.armed = true; this.phase = 'raise'; return null; }
    if (this.armed) {
      this.armed = false; this.phase = 'counted'; this.auto++;
      return this.log('auto_count', time, {auto: this.auto, total: this.total, qualifying_frame_ms: Math.round(this.candidateSince-this.origin)});
    }
    this.phase = 'lower';
    return null;
  }
  report() {
    return {schema_version: 2, app_version: '5.5', rules: CONFIG, model: 'MediaPipe Pose Landmarker Lite float16 v1', source: this.source || {type: 'camera'},
      automatic_count: this.auto, manual_adjustment: this.adjustment, final_count: this.total,
      time_origin: this.source?.type === 'video' ? '原视频起点；毫秒，暂停检测不推进视频时间' : '本次摄像头计数开始；毫秒', events: this.events};
  }
}
