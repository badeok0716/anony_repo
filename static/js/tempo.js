/* Both lanes are already synchronized in the split MP4. Playback rate stays 1. */
'use strict';
const byId = id => document.getElementById(id);
const video = byId('motion');
let data, task, audio, enabled = false, generation = 0;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
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
  audio.osc.frequency.setTargetAtTime(85 * Math.pow(clamp(rate, .2, 5), 1.3), now, .06);
  audio.filter.frequency.setTargetAtTime(260 + 600 * clamp(rate - .5, 0, 4), now, .08);
  audio.gain.gain.setTargetAtTime(enabled && active ? Number(byId('volume').value) / 100 * .12 : 0, now, .025);
}
function update() {
  if (!data || !task) return;
  const t = video.currentTime, policyTime = t + task.lag_s;
  const active = policyTime >= task.policy_start_s && policyTime < task.completion_s;
  const rate = sample(task.samples, t);
  byId('needle').style.transform = `rotate(${-110 + 220 * clamp(rate / data.gauge_max, 0, 1)}deg)`;
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
  try {
    if (!audio) {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) throw new Error('Web Audio is unavailable in this browser.');
      const ctx = new Audio(), osc = ctx.createOscillator(), filter = ctx.createBiquadFilter(), gain = ctx.createGain();
      osc.type = 'triangle'; filter.type = 'lowpass'; gain.gain.value = 0;
      osc.connect(filter).connect(gain).connect(ctx.destination); osc.start(); audio = {ctx,osc,filter,gain};
    }
    await audio.ctx.resume(); enabled = !enabled;
    byId('sound').setAttribute('aria-pressed', String(enabled));
    byId('sound').textContent = enabled ? 'Mute tempo sound' : 'Enable tempo sound'; update();
  } catch (e) { byId('error').hidden = false; byId('error').textContent = e.message; }
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
  for (let i=0;i<=data.gauge_max*2;i++) {
    const value=i/2, angle=(-110+220*value/data.gauge_max)*Math.PI/180;
    const xy = radius => [160+radius*Math.sin(angle),129-radius*Math.cos(angle)];
    const a=xy(109), b=xy(119), label=xy(88);
    ticks.push(`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/><text x="${label[0]}" y="${label[1]+4}" text-anchor="middle">${value}</text>`);
  }
  byId('ticks').innerHTML=ticks.join(''); select('cup');
}).catch(e => { byId('error').hidden=false; byId('error').textContent=`Telemetry unavailable: ${e.message}. Open using an HTTP server, not file://.`; });
