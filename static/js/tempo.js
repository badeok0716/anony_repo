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
  const pace = clamp(rate, .35, 3);
  const dt=Math.max(.016,now-(audio.lastTime||now));
  const acceleration=clamp((pace-(audio.lastPace||pace))/dt,0,2);
  audio.boost=Math.max(acceleration,(audio.boost||0)*Math.exp(-dt/.35));
  audio.lastTime=now;audio.lastPace=pace;
  // Detuned low engine layers: fixed tone filter, audible rising rev and swell.
  audio.voices.forEach((voice,i)=>voice.frequency.setTargetAtTime((48+48*pace)*[.5,1,1.008,2,2.012][i],now,.10));
  const rev=clamp((pace-.8)/1.2,0,1);
  audio.gain.gain.setTargetAtTime(enabled && active ? Number(byId('volume').value)/100*(.28+.48*rev+.16*audio.boost) : 0,now,active?.09:.035);
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
      const ctx = new Audio(), filter = ctx.createBiquadFilter(), gain = ctx.createGain();
      filter.type='lowpass'; filter.Q.value=.7; filter.frequency.value=850; gain.gain.value=0;
      const compressor=ctx.createDynamicsCompressor();
      compressor.threshold.value=-12; compressor.ratio.value=4;
      filter.connect(gain).connect(compressor).connect(ctx.destination);
      const voices=[.32,.25,.20,.13,.10].map((level,i)=>{
        const osc=ctx.createOscillator(), mix=ctx.createGain();
        osc.type=i===0?'sine':i<3?'triangle':'sawtooth'; osc.frequency.value=96*[.5,1,1.008,2,2.012][i];
        mix.gain.value=level; osc.connect(mix).connect(filter); osc.start(); return osc;
      });
      audio={ctx,voices,filter,gain};
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

let chunkData, atlas, chunkGeneration=0;
const channels=['q90','q95','q99'], channelColors=['#9460cc','#169470','#bf7908'];
function clockIndex(name,t){return sample(chunkData.clocks[name].map((v,i)=>[v,i]),t);}
function positionAt(points,index){
  const a=Math.floor(index),b=Math.min(a+1,points.length-1),f=index-a;
  return points[a].map((v,i)=>v+(points[b][i]-v)*f);
}
function drawChunk(t=0){
  if(!chunkData || !atlas)return;
  const pts=chunkData.xyz.map(p=>[.866*(p[0]-p[1]),p[2]-.5*(p[0]+p[1])]);
  const min=[0,1].map(i=>Math.min(...pts.map(p=>p[i]))),max=[0,1].map(i=>Math.max(...pts.map(p=>p[i])));
  const scale=Math.min(300/Math.max(max[0]-min[0],.01),180/Math.max(max[1]-min[1],.01));
  const project=p=>[190+(p[0]-(max[0]+min[0])/2)*scale,125-(p[1]-(max[1]+min[1])/2)*scale];
  const xy=pts.map(project),base=clockIndex('q50',t);
  channels.forEach((name,k)=>{
    const index=clockIndex(name,t),a=positionAt(xy,index),b=positionAt(xy,base),color=channelColors[k];
    byId('chunk-'+name).innerHTML=`<path d="${xy.map((p,i)=>`${i?'L':'M'}${p.join(',')}`).join(' ')}" fill="none" stroke="#b6bec9" stroke-width="2"/>${xy.filter((_,i)=>i%8===0).map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="2.5" fill="#778494"/>`).join('')}<circle cx="${b[0]}" cy="${b[1]}" r="12" fill="#147ba4" opacity=".22"/><circle cx="${b[0]}" cy="${b[1]}" r="9" fill="none" stroke="#147ba4" stroke-width="2"/><circle cx="${a[0]}" cy="${a[1]}" r="6" fill="${color}"/><path d="M25 222 l23 13 M25 222 l-14 14 M25 222 v-27" fill="none" stroke="#778494"/><text x="49" y="239" font-size="11">X</text><text x="3" y="248" font-size="11">Y</text><text x="21" y="189" font-size="11">Z</text>`;
    const canvas=byId('frames-'+name),ctx=canvas.getContext('2d'),spec=chunkData.atlas;
    [base,index].forEach((idx,lane)=>{
      const clip=sample(chunkData.clip_time.map((v,i)=>[i,v]),idx);
      const frame=Math.min(spec.count-1,Math.round(clip*spec.fps));
      ctx.drawImage(atlas,(frame%spec.columns)*spec.width,Math.floor(frame/spec.columns)*spec.height,spec.width,spec.height,lane*spec.width,0,spec.width,spec.height);
    });
    byId('time-'+name).textContent=`q50 ${chunkData.clocks.q50.at(-1).toFixed(2)} s · ${name} ${chunkData.clocks[name].at(-1).toFixed(2)} s`;
    canvas.dataset.progress=index.toFixed(2);
  });
  byId('chunk-time').textContent=`Shared clock: ${t.toFixed(2)} s`;
}
byId('chunk-play').addEventListener('click',()=>{
  if(!chunkData || !atlas)return;
  const token=++chunkGeneration,start=performance.now(),end=Math.max(...Object.values(chunkData.clocks).map(c=>c.at(-1)));
  byId('chunk-play').textContent='↺ Restart all';
  const tick=now=>{
    if(token!==chunkGeneration)return;
    const t=Math.min((now-start)/1000,end);drawChunk(t);
    if(t<end)requestAnimationFrame(tick);else byId('chunk-play').textContent='▶ Run full Cup';
  };requestAnimationFrame(tick);
});
fetch('static/data/segment.json').then(r=>{if(!r.ok)throw new Error('Segment data unavailable');return r.json();}).then(async d=>{
  chunkData=d;atlas=new Image();atlas.src=d.atlas.src;await atlas.decode();drawChunk();byId('chunk-play').disabled=false;
}).catch(e=>{byId('chunk-time').textContent=e.message;});
