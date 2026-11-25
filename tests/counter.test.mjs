import test from 'node:test';
import assert from 'node:assert/strict';
import {RaiseCounter, classifyPose, poseGuides, CONFIG} from '../app/raise_counter/counter.mjs';

function frames(c, pose, from, until) {for (let t=from;t<=until;t+=60) c.frame(pose,t);}
function ready() {const c=new RaiseCounter();c.start(0);frames(c,'down',0,240);return c;}
test('held raise counts once, returning down allows next repetition', () => {
  const c=ready(); frames(c,'up',300,3600); assert.equal(c.total,1);
  frames(c,'down',3660,3960); frames(c,'up',4020,4320); assert.equal(c.total,2);
});
test('starting with raised hand is not a new repetition', () => {
  const c=new RaiseCounter();c.start(0);frames(c,'up',0,3000);assert.equal(c.total,0);
});
test('occlusion disarms; reacquisition in raised pose never counts', () => {
  const c=ready();c.frame('unknown',300,'blocked');frames(c,'up',360,900);assert.equal(c.total,0);
  frames(c,'down',960,1260);frames(c,'up',1320,1620);assert.equal(c.total,1);
});
test('brief pose spikes and the neutral band do not count', () => {
  const c=ready();c.frame('up',300);c.frame('middle',360);c.frame('up',420);c.frame('middle',480);assert.equal(c.total,0);
});
test('pause freezes count and resume requires a fresh lowered pose', () => {
  const c=ready();c.pause(300);frames(c,'up',360,960);assert.equal(c.total,0);c.resume(1020);
  frames(c,'up',1080,1440);assert.equal(c.total,0);frames(c,'down',1500,1800);frames(c,'up',1860,2100);assert.equal(c.total,1);
});
test('a stalled stream cannot finish an old movement', () => {
  const c=ready();frames(c,'up',1200,1500);assert.equal(c.total,0);
});
test('manual corrections remain separate from automatic results and cannot go negative', () => {
  const c=ready();assert.equal(c.correct(-1,300),false);frames(c,'up',300,600);
  assert.equal(c.correct(-1,660),true);assert.equal(c.total,0);assert.equal(c.auto,1);
  assert.equal(c.correct(-1,720),false);c.correct(1,780);c.end(840);c.correct(1,900);
  assert.deepEqual([c.auto,c.adjustment,c.total],[1,1,2]);assert.equal(c.report().events.filter(e=>e.type==='auto_count').length,1);
});
test('ending blocks recognition, restarting clears the previous session', () => {
  const c=ready();c.end(300);frames(c,'up',360,900);assert.equal(c.total,0);
  c.correct(1,960);c.start(1020);assert.equal(c.total,0);assert.equal(c.report().events.length,1);
});
function points() {
  const p=Array.from({length:33},()=>({x:.5,y:.5,visibility:.95,presence:.95}));
  p[11]={...p[11],x:.65,y:.45};p[12]={...p[12],x:.35,y:.45};
  p[14]={...p[14],x:.3,y:.55};p[16]={...p[16],x:.25,y:.7};return p;
}
test('actual landmark geometry selects right wrist, not the other hand', () => {
  const p=points();p[15].y=.1;assert.equal(classifyPose(p,640,480).pose,'down');
  p[16].y=.2;assert.equal(classifyPose(p,640,480).pose,'up');
  p[16].y=.45;assert.equal(classifyPose(p,640,480).pose,'middle');
});
test('missing, uncertain, cropped and distant landmarks suspend counting', () => {
  assert.equal(classifyPose([],640,480).pose,'unknown');
  for (const mutate of [p=>p[16].visibility=.2,p=>p[16].x=1.1,p=>p[11].x=.37,p=>p[16].presence=.1]) {
    const p=points();mutate(p);assert.equal(classifyPose(p,640,480).pose,'unknown');
  }
});
test('uncertain elbow does not block counting when both shoulders and wrist are visible', () => {
  const p=points();p[14].visibility=.1;p[14].presence=.1;
  assert.equal(classifyPose(p,640,480).pose,'down');
  p[16].y=.2;assert.equal(classifyPose(p,640,480).pose,'up');
});
test('video pause retains the lowered pose because source time has not advanced', () => {
  const c=ready();c.pause(240,true);c.resume(240,true);
  frames(c,'up',300,600);assert.equal(c.total,1);
});
test('video reports use source timestamps and include provenance', () => {
  const c=new RaiseCounter();c.start(0,{type:'video',file_name:'test.webm',duration_ms:2000});
  frames(c,'down',0,240);frames(c,'up',300,600);
  const r=c.report();assert.equal(r.source.file_name,'test.webm');assert.match(r.time_origin,/视频/);
  assert.equal(r.events.find(e=>e.type==='auto_count').time_ms,480);
});
test('left shoulder at screen-left gives a specific rightward instruction in mirror view', () => {
  const p=points();p[11].x=1.03;
  const r=classifyPose(p,640,480,{mirrored:true});
  assert.equal(r.pose,'unknown');assert.match(r.reason,/左肩/);assert.match(r.reason,/向画面右侧移动/);assert.doesNotMatch(r.reason,/右臂/);
  p[11].x=.96;p[11].visibility=.1;
  assert.match(classifyPose(p,640,480,{mirrored:true}).reason,/左肩暂未看清，请向画面右侧移动/);
});
test('right elbow outside or missing blocks counting and names the elbow', () => {
  for(const mutate of [p=>{p[14].x=-.1},p=>{p[14].y=1.1;p[14].visibility=.1},p=>{p[14]=undefined}]){
    const p=points();mutate(p);const r=classifyPose(p,640,480,{mirrored:true});
    assert.equal(r.pose,'unknown');assert.match(r.reason,/右肘/);
  }
});
test('top and bottom edge give a vertical/framing instruction instead of wrong horizontal move', () => {
  const p=points();p[14].y=1.1;const r=classifyPose(p,640,480,{mirrored:true});
  assert.match(r.reason,/下方/);assert.match(r.reason,/调整镜头上下角度/);assert.doesNotMatch(r.reason,/向画面[左右]侧移动/);
});
test('opposite edge failures ask the user to step back rather than move in contradictory directions', () => {
  const p=points();p[11].x=1.03;p[12].x=-.03;
  assert.match(classifyPose(p,640,480,{mirrored:true}).reason,/后退一点/);
});
test('recorded video names the right body part without asking its viewer to move', () => {
  const p=points();p[11].x=1.03;
  const r=classifyPose(p,640,480,{source:'video',mirrored:false});
  assert.match(r.reason,/左肩靠近画面右侧/);assert.match(r.reason,/本段不计数/);assert.doesNotMatch(r.reason,/向画面[左右]侧移动/);
  assert.match(classifyPose(p,640,480,{source:'video',mirrored:true}).reason,/左肩靠近画面左侧/);
});
test('elbow exit disarms the counter; returning raised cannot create a false count', () => {
  const c=ready(),p=points();p[14].x=1.1;p[16].y=.2;
  for(let t=300;t<=600;t+=60){const r=classifyPose(p,640,480);c.frame(r.pose,t,r.reason);}
  assert.equal(c.total,0);assert.equal(c.phase,'unclear');assert.match(c.events.find(e=>e.type==='tracking_lost').reason,/右肘/);
  frames(c,'up',660,960);assert.equal(c.total,0);
  frames(c,'down',1020,1320);frames(c,'up',1380,1680);assert.equal(c.total,1);
});

test('visible guide lines match the actual decision boundary at different aspect ratios', () => {
  for(const [width,height,tilt] of [[640,480,0],[1920,1080,.04],[480,640,-.03]]){
    const p=points();p[11].y+=tilt;
    const g=poseGuides(p,width,height),epsilon=.000001;
    assert.ok(Math.abs((g.lowerY-g.shoulderY)*height/g.scale-CONFIG.margin)<1e-12);
    for(const [y,expected] of [[g.lowerY+epsilon,'down'],[g.lowerY-epsilon,'middle'],[g.raiseY-epsilon,'up'],[g.raiseY+epsilon,'middle']]){
      p[16].y=y;const r=classifyPose(p,width,height);
      assert.equal(r.pose,expected);assert.deepEqual(r.guides,g);
    }
  }
});

test('partial lowering to the middle band does not rearm; crossing the lower line for 180 ms does', () => {
  const c=ready(),p=points(),g=poseGuides(p,640,480);
  frames(c,'up',300,600);assert.equal(c.total,1);
  p[16].y=g.shoulderY;frames(c,classifyPose(p,640,480).pose,660,960);
  frames(c,'up',1020,1320);assert.equal(c.total,1);
  // The wrist is just beyond the line, still near the shoulder; a fully hanging arm is unnecessary.
  p[16].y=g.lowerY+.001;
  for(let t=1380;t<=1500;t+=60)c.frame(classifyPose(p,640,480).pose,t);
  assert.equal(c.armed,false);
  c.frame(classifyPose(p,640,480).pose,1560);assert.equal(c.armed,true);
  frames(c,'up',1620,1860);assert.equal(c.total,2);
});

test('guides are withheld when tracking is invalid', () => {
  const p=points();p[14].x=1.1;
  assert.equal(classifyPose(p,640,480).guides,undefined);
  assert.equal(poseGuides([],640,480),null);
  assert.equal(poseGuides(points(),0,480),null);
});
