import test from 'node:test';
import assert from 'node:assert/strict';
import {RaiseCounter} from '../app/raise_counter/counter.mjs';
import {actionFeedback,LightMonitor,meanLuma} from '../app/raise_counter/feedback.mjs';

test('missing starting wrist then raised wrist never shows completion or invents a count',()=>{
  const c=new RaiseCounter();c.start(0);c.frame('unknown',0,'右手腕暂未看清');
  for(let t=60;t<=360;t+=60)c.frame('up',t);
  const f=actionFeedback(c);
  assert.equal(c.total,0);assert.equal(f.step,'stepDown');assert.equal(f.ready,false);
  assert.match(f.title,/未确认放下/);assert.match(f.detail,/补记一次/);
  assert.equal(actionFeedback(c,{source:'video'}).step,'stepDown');
  assert.match(actionFeedback(c,{source:'video'}).detail,/核对视频/);
  for(let t=420;t<=660;t+=60)c.frame('down',t);
  assert.equal(actionFeedback(c).ready,true);
  for(let t=720;t<=960;t+=60)c.frame('up',t);
  assert.equal(c.auto,1);
});

test('ready signal appears only after a stable lowered pose; subsequent raise counts once',()=>{
  const c=new RaiseCounter();c.start(0);
  for(const t of [0,60,120]){c.frame('down',t);assert.equal(actionFeedback(c).ready,false);}
  c.frame('down',180);assert.equal(actionFeedback(c).ready,true);
  assert.match(actionFeedback(c).readiness,/可以举手了/);
  for(let t=240;t<=600;t+=60)c.frame('up',t);
  assert.equal(c.total,1);assert.equal(actionFeedback(c,{recentCount:true}).step,'stepCount');
  assert.equal(actionFeedback(c).ready,false);
});

test('tracking loss clears readiness even immediately after counting; correction remains distinct',()=>{
  const c=new RaiseCounter();c.start(0);
  c.frame('down',0);c.frame('down',180);c.frame('up',240);c.frame('up',420);
  c.frame('unknown',480,'右手腕暂未看清');
  assert.equal(actionFeedback(c,{recentCount:true}).ready,false);
  assert.equal(actionFeedback(c,{recentCount:true}).title,'暂不计数，请调整位置');
  c.correct(1,540);assert.deepEqual([c.auto,c.adjustment,c.total],[1,1,2]);
});

test('brightness measures pixels without storing them',()=>{
  assert.equal(meanLuma([]),null);assert.equal(meanLuma([0,0,0]),null);
  assert.equal(meanLuma([0,0,0,255]),0);
  assert.ok(Math.abs(meanLuma([255,255,255,255])-255)<1e-10);
});

test('darkness hint uses sustained brightness and hysteresis rather than flickering',()=>{
  const l=new LightMonitor();
  assert.equal(l.update(20,0),false);assert.equal(l.update(20,200),false);
  assert.equal(l.update(20,400),true);
  assert.equal(l.update(40,600),true);
  assert.equal(l.update(60,800),true);assert.equal(l.update(60,1200),false);
  l.update(20,1400);l.update(60,1600);assert.equal(l.update(20,1800),false);
  l.reset();assert.equal(l.dark,false);
});

test('backwards time and long gaps cannot satisfy continuous dark evidence',()=>{
  const l=new LightMonitor();l.update(20,500);
  assert.equal(l.update(20,0),false);assert.equal(l.update(20,2000),false);
  assert.equal(l.update(20,2200),false);assert.equal(l.update(20,2400),true);
});

test('brightness alone does not prohibit an otherwise valid counted movement',()=>{
  const l=new LightMonitor();l.update(20,0);l.update(20,400);assert.equal(l.dark,true);
  const c=new RaiseCounter();c.start(0);c.frame('down',0);c.frame('down',180);
  c.frame('up',240);c.frame('up',420);assert.equal(c.auto,1);
});
