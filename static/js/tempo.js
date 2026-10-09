/* Both lanes are already synchronized in the split MP4. Playback rate stays 1. */
'use strict';
const byId = id => document.getElementById(id);
const video = byId('motion');
let data, task, audio, enabled = false, generation = 0;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const gaugeAngle = rate => 110 * clamp(Math.log(Math.max(rate, .001)) / Math.log(data.gauge_max), -1, 1);
function sample(rows, t) {
  if (t <= rows[0][0]) return rows[0][1];
  let lo = 0, hi = rows.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (rows[m][0] <= t) lo = m; else hi = m; }
  const a = rows[lo], b = rows[hi];
  return a[1] + (b[1] - a[1]) * clamp((t - a[0]) / (b[0] - a[0]), 0, 1);
}
function soundLevel(rate, active) {
  if (!audio) return;
  const now = audio.ctx.currentTime;
  audio.source.playbackRate.setTargetAtTime(clamp(.8 * rate, .4, 2.4), now, .08);
  audio.filter.frequency.setTargetAtTime(2200 + 2500 * clamp(rate - .5, 0, 3), now, .08);
  audio.gain.gain.setTargetAtTime(enabled && active ? Number(byId('volume').value) / 100 * .35 : 0, now, .025);
}
function update() {
  if (!data || !task) return;
  const t = video.currentTime, policyTime = t + task.lag_s;
  const active = policyTime >= task.policy_start_s && policyTime < task.completion_s;
  const rate = sample(task.samples, t);
  byId('needle').style.transform = `rotate(${gaugeAngle(rate)}deg)`;
  byId('needle').style.opacity = active ? '1' : '.25';
  byId('rate').textContent = active ? `${rate.toFixed(2)}×` : '—';
  byId('state').textContent = !active ? (policyTime < task.policy_start_s ? 'Waiting for policy' : 'Ours complete') : rate > 1.08 ? 'Faster motion' : rate < .92 ? 'Below fixed-clock pace' : 'Near fixed-clock pace';
  byId('clock').textContent = `${Math.max(0, policyTime).toFixed(2)} s`;
  const duration = Number.isFinite(video.duration) ? video.duration : task.samples.at(-1)[0];
  const x = clamp(t / duration, 0, 1) * byId('history').viewBox.baseVal.width;
  byId('cursor').setAttribute('x1', x); byId('cursor').setAttribute('x2', x);
  soundLevel(rate, active && !video.paused && !video.ended && !video.seeking && !document.hidden && video.readyState >= 3);
}
function chart() {
  if (!task) return;
  const width = byId('history').clientWidth || 1000;
  byId('history').setAttribute('viewBox', `0 0 ${width} 160`);
  const duration = Number.isFinite(video.duration) ? video.duration : task.samples.at(-1)[0];
  const y = rate => 140 - 115 * clamp(rate / data.gauge_max, 0, 1);
  const points = task.samples.filter(row => row[0] + task.lag_s >= task.policy_start_s && row[0] + task.lag_s < task.completion_s);
  byId('trace').innerHTML = `<line x1="0" x2="${width}" y1="${y(1)}" y2="${y(1)}"/><text x="4" y="${y(1)-7}">1×</text><path d="${points.map((r,i)=>`${i?'L':'M'}${(width*r[0]/duration).toFixed(2)},${y(r[1]).toFixed(2)}`).join(' ')}"/>`;
  byId('duration').textContent = `${duration.toFixed(2)} s video`;
}
function select(name) {
  video.pause(); task = data.tasks[name];
  clearTrail(); byId('trail-enabled').disabled = name !== 'cup';
  video.src = task.video; video.load();
  byId('download').href = task.video;
  byId('done').textContent = `${task.completion_s.toFixed(2)} s`;
  byId('fixed').textContent = `${task.fixed_completion_s.toFixed(2)} s`;
  byId('average').textContent = `${(task.fixed_completion_s/task.completion_s).toFixed(2)}×`;
  document.querySelectorAll('[data-task]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.task === name)));
  chart(); update();
}
function animate() {
  const token = ++generation;
  function tick() {
    if (token !== generation) return;
    update();
    drawTrail();
    if (!video.paused && !video.ended) {
      if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(tick);
      else requestAnimationFrame(tick);
    }
  }
  tick();
}
byId('sound').addEventListener('click', async () => {
  byId('sound').disabled = true;
  try {
    if (!audio) {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) throw new Error('Web Audio is unavailable in this browser.');
      const ctx = new Audio(), source = ctx.createBufferSource(), filter = ctx.createBiquadFilter(), gain = ctx.createGain();
      await ctx.resume();
      const response = await fetch('static/audio/f1-engine.mp3');
      if (!response.ok) { await ctx.close(); throw new Error('Engine audio unavailable.'); }
      source.buffer = await ctx.decodeAudioData(await response.arrayBuffer());
      source.loop = true; source.loopStart = 3; source.loopEnd = Math.min(11,source.buffer.duration);
      filter.type = 'lowpass'; gain.gain.value = 0;
      source.connect(filter).connect(gain).connect(ctx.destination); source.start(0,3); audio = {ctx,source,filter,gain};
    }
    await audio.ctx.resume(); enabled = !enabled;
    byId('sound').setAttribute('aria-pressed', String(enabled));
    byId('sound').textContent = enabled ? 'Mute tempo sound' : 'Enable tempo sound'; update();
  } catch (e) { byId('error').hidden = false; byId('error').textContent = e.message; }
  finally { byId('sound').disabled = false; }
});
byId('volume').addEventListener('input', update);
byId('replay').addEventListener('click', () => { video.currentTime = 0; video.play().catch(e => { byId('error').hidden = false; byId('error').textContent = e.message; }); });
document.querySelectorAll('[data-task]').forEach(b => b.addEventListener('click', () => { if (data) select(b.dataset.task); }));
video.addEventListener('play', animate);
video.addEventListener('seeking', clearTrail);
byId('trail-enabled').addEventListener('change', clearTrail);
for (const event of ['pause','ended','timeupdate','seeking','seeked','waiting','playing']) video.addEventListener(event, update);
video.addEventListener('loadedmetadata', () => { chart(); update(); });
video.addEventListener('error', () => { byId('error').hidden = false; byId('error').textContent = 'Video could not be loaded. Serve this page over HTTP and check the media files.'; });
document.addEventListener('visibilitychange', update);
window.addEventListener('pagehide', () => soundLevel(1,false));
new ResizeObserver(() => { chart(); update(); }).observe(byId('history'));
byId('history').addEventListener('click', e => { if (Number.isFinite(video.duration)) { const r=e.currentTarget.getBoundingClientRect(); video.currentTime=clamp((e.clientX-r.left)/r.width,0,1)*video.duration; } });
fetch('static/data/tempo.json').then(r => { if (!r.ok) throw new Error(`Telemetry HTTP ${r.status}`); return r.json(); }).then(result => {
  data = result; const ticks = [];
  for (const value of [1/data.gauge_max,.5,.75,1,1.5,2,data.gauge_max]) {
    const angle=gaugeAngle(value)*Math.PI/180;
    const xy = radius => [160+radius*Math.sin(angle),129-radius*Math.cos(angle)];
    const a=xy(109), b=xy(119), label=xy(88);
    ticks.push(`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/><text x="${label[0]}" y="${label[1]+4}" text-anchor="middle">${Number(value.toFixed(2))}×</text>`);
  }
  byId('ticks').innerHTML=ticks.join(''); select('cup');
}).catch(e => { byId('error').hidden=false; byId('error').textContent=`Telemetry unavailable: ${e.message}. Open using an HTTP server, not file://.`; });

// Cup pilot: short-lived, feathered patches around red gripper fingers in preceding frames.
// Never paint on the fixed-clock lane; no historical scene-wide overlay.
let trailFrames = [], lastTrailTime = -1;
const trailCanvas = byId('ghost-trail'), trailCtx = trailCanvas.getContext('2d');
const detector = document.createElement('canvas'); detector.width=128; detector.height=128;
const detectCtx=detector.getContext('2d',{willReadFrequently:true});
function clearTrail() { trailFrames=[];lastTrailTime=-1;trailCtx.clearRect(0,0,trailCanvas.width,trailCanvas.height); }
function drawTrail() {
  if (!byId('trail-enabled').checked || byId('trail-enabled').disabled || video.readyState<2 || video.seeking) { clearTrail(); return; }
  const w=video.videoWidth,h=video.videoHeight,t=video.currentTime;
  if (!w || !h || Math.abs(t-lastTrailTime)<1/30) return;
  if (t<lastTrailTime || t-lastTrailTime>.3) clearTrail();
  trailCanvas.width=w;trailCanvas.height=h;
  detectCtx.drawImage(video,w/2,0,w/2,h,0,0,128,128);
  const pixels=detectCtx.getImageData(0,0,128,128).data;
  let x=0,y=0,n=0;
  for(let j=12;j<112;j++) for(let i=6;i<122;i++){
    const k=(j*128+i)*4,r=pixels[k],g=pixels[k+1],b=pixels[k+2];
    if(r>100 && r>g*1.55 && r>b*1.35){x+=i;y+=j;n++;}
  }
  if(n<4){clearTrail();return;}
  x=w/2+(x/n/128)*w/2;y=y/n/128*h;
  const radius=h*.085;
  for(const old of trailFrames){
    const age=t-old.t;
    if(age<.035 || age>.17)continue;
    trailCtx.save();trailCtx.globalAlpha=.4*(1-age/.20);
    trailCtx.drawImage(old.patch,old.x-radius,old.y-radius);trailCtx.restore();
  }
  const patch=document.createElement('canvas');patch.width=patch.height=Math.ceil(radius*2);
  const c=patch.getContext('2d');c.drawImage(video,x-radius,y-radius,radius*2,radius*2,0,0,patch.width,patch.height);
  c.globalCompositeOperation='destination-in';const mask=c.createRadialGradient(radius,radius,radius*.2,radius,radius,radius);
  mask.addColorStop(0,'rgba(0,0,0,1)');mask.addColorStop(1,'rgba(0,0,0,0)');c.fillStyle=mask;c.fillRect(0,0,patch.width,patch.height);
  trailFrames.push({patch,x,y,t});trailFrames=trailFrames.filter(f=>t-f.t<.17).slice(-4);lastTrailTime=t;
}

let chunkData, quantile='q99', chunkGeneration=0;
function chunkPosition(clock,t){
  const rows=clock.map((time,i)=>[time,i]);return sample(rows,t);
}
function drawChunk(t=0){
  if(!chunkData)return;
  const view=byId('chunk-view').value, axes={xz:[0,2],xy:[0,1],yz:[1,2]}[view];
  const pts=chunkData.xyz.map(p=>view==='iso'?[.866*(p[0]-p[1]),p[2]-.5*(p[0]+p[1])]:axes.map(i=>p[i]));
  const min=[0,1].map(i=>Math.min(...pts.map(p=>p[i]))),max=[0,1].map(i=>Math.max(...pts.map(p=>p[i])));
  const scale=Math.min(510/Math.max(max[0]-min[0],.01),230/Math.max(max[1]-min[1],.01));
  const project=p=>[310+(p[0]-(max[0]+min[0])/2)*scale,170-(p[1]-(max[1]+min[1])/2)*scale];
  const xy=pts.map(project),selected=chunkPosition(chunkData.clocks[quantile],t),base=chunkPosition(chunkData.clocks.q50,t);
  const at=index=>{const a=Math.floor(index),b=Math.min(a+1,xy.length-1),f=index-a;return xy[a].map((v,i)=>v+(xy[b][i]-v)*f)};
  const a=at(selected),b=at(base);
  byId('chunk-plot').innerHTML=`<path d="${xy.map((p,i)=>`${i?'L':'M'}${p.join(',')}`).join(' ')}" fill="none" stroke="#64748b" stroke-width="2"/>${xy.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#64748b"/>`).join('')}<circle cx="${b[0]}" cy="${b[1]}" r="13" fill="#147ba4" opacity=".25"/><circle cx="${b[0]}" cy="${b[1]}" r="10" fill="none" stroke="#147ba4" stroke-width="2"/><circle cx="${a[0]}" cy="${a[1]}" r="6" fill="#b46b00"/><text x="20" y="28" fill="#147ba4" font-size="14">○ q50 / 1× reference</text><text x="390" y="28" fill="#965b00" font-size="14">● ${quantile} selected</text><text x="20" y="320" fill="#64748b" font-size="12">${byId('chunk-view').selectedOptions[0].text} projection · equal spatial scale</text>`;
  byId('chunk-time').textContent=`Elapsed ${t.toFixed(2)} s · reference ${chunkData.clocks.q50.at(-1).toFixed(2)} s · ${quantile} ${chunkData.clocks[quantile].at(-1).toFixed(2)} s`;
}
function stopChunk(){chunkGeneration++;byId('chunk-play').textContent='▶ Run chunk';}
document.querySelectorAll('[data-quantile]').forEach(button=>button.addEventListener('click',()=>{
  stopChunk();quantile=button.dataset.quantile;document.querySelectorAll('[data-quantile]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));drawChunk();
}));
byId('chunk-view').addEventListener('change',()=>{stopChunk();drawChunk();});
byId('chunk-play').addEventListener('click',()=>{
  if(!chunkData)return;
  const token=++chunkGeneration,start=performance.now(),end=Math.max(chunkData.clocks.q50.at(-1),chunkData.clocks[quantile].at(-1));
  byId('chunk-play').textContent='↺ Restart';
  const tick=now=>{if(token!==chunkGeneration)return;const t=Math.min((now-start)/1000,end);drawChunk(t);if(t<end)requestAnimationFrame(tick);else stopChunk();};requestAnimationFrame(tick);
});
fetch('static/data/chunk.json').then(r=>{if(!r.ok)throw new Error('Chunk data unavailable');return r.json();}).then(d=>{chunkData=d;byId('chunk-context').src=d.context_video;drawChunk();}).catch(e=>{byId('chunk-time').textContent=e.message;});
