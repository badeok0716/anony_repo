/* Inference-time tempo section (rebuilt 2026-10-11).
   1) task tabs switch the split video (speedometer + engine sound are inside the MP4s);
   2) chunk explorer: video on the selected clock (q50 ghost overlaid), one 3D view with the q50 runner and the
      selected runner on their current pick/place segment, and a quantile scale (50..100, positions to scale). */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);

  /* ---------- 1. split videos ---------- */
  const split = $("#split-video");
  document.querySelectorAll(".tempo-tabs button").forEach((b) => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".tempo-tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      const vol = split.volume, muted = split.muted;
      split.pause();
      split.src = `static/tempo/split_${b.dataset.task}.mp4?v=2`;
      split.volume = vol; split.muted = muted;
      split.load();
    });
  });

  /* ---------- 2. chunk explorer ---------- */
  const COLORS = { q50: "#0ea5e9", q90: "#8b5cf6", q95: "#16a34a", q99: "#d97706" };
  const STOPS = [50, 90, 95, 99];
  const video = $("#chunk-video"), svg = $("#chunk-svg"), readout = $("#chunk-readout"), label = $("#chunk-video-label");
  const scale = $("#qscale"), ticks = scale.querySelector(".qscale-ticks"), thumb = scale.querySelector(".qscale-thumb"),
        fill = scale.querySelector(".qscale-fill");
  const NS = "http://www.w3.org/2000/svg";
  let D = null, sel = 50, vb = null, planT = [];

  const frac = (q) => (q - 50) / 50;                       // 50 -> 0, 100 -> 1 (to scale)
  const vertical = () => window.matchMedia("(min-width: 761px)").matches;
  STOPS.forEach((q) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = "q" + q; b.dataset.q = q;
    b.addEventListener("pointerdown", (e) => e.stopPropagation());
    b.addEventListener("click", (e) => { e.stopPropagation(); choose(q); });
    ticks.appendChild(b);
  });
  [60, 70, 80].forEach((q) => { const s = document.createElement("span"); s.className = "axis"; s.textContent = q; s.dataset.q = q; ticks.appendChild(s); });
  function placeScale() {
    const v = vertical();
    ticks.querySelectorAll("[data-q]").forEach((e) => {
      const f = frac(+e.dataset.q) * 100;
      e.style.bottom = v ? f + "%" : ""; e.style.left = v ? "" : f + "%";
    });
    const f = frac(sel) * 100;
    thumb.style.bottom = v ? f + "%" : ""; thumb.style.left = v ? "" : f + "%";
    fill.style.height = v ? f + "%" : ""; fill.style.width = v ? "" : f + "%";
    ticks.querySelectorAll("button").forEach((b) => b.classList.toggle("on", +b.dataset.q === sel));
    scale.setAttribute("aria-valuenow", sel); scale.setAttribute("aria-valuetext", "q" + sel);
  }
  const nearest = (q) => STOPS.reduce((a, b) => (Math.abs(b - q) < Math.abs(a - q) ? b : a));
  function qFromPointer(e) {
    const r = scale.querySelector(".qscale-track").getBoundingClientRect();
    const f = vertical() ? (r.bottom - e.clientY) / r.height : (e.clientX - r.left) / r.width;
    return 50 + 50 * Math.min(1, Math.max(0, f));
  }
  let dragging = false;
  scale.addEventListener("pointerdown", (e) => { dragging = true; scale.setPointerCapture(e.pointerId); choose(nearest(qFromPointer(e))); });
  scale.addEventListener("pointermove", (e) => { if (dragging) choose(nearest(qFromPointer(e))); });
  scale.addEventListener("pointerup", () => { dragging = false; });
  scale.addEventListener("keydown", (e) => {
    const i = STOPS.indexOf(sel);
    if (e.key === "ArrowUp" || e.key === "ArrowRight") { choose(STOPS[Math.min(3, i + 1)]); e.preventDefault(); }
    if (e.key === "ArrowDown" || e.key === "ArrowLeft") { choose(STOPS[Math.max(0, i - 1)]); e.preventDefault(); }
  });
  window.addEventListener("resize", () => { placeScale(); if (D) { setupView(); draw(); } });

  function choose(q) {
    if (q === sel) return;
    sel = q; placeScale(); setLabel();
    const t = video.currentTime, playing = !video.paused && !video.ended, vol = video.volume, muted = video.muted;
    video.src = `static/tempo/chunk_q${q}.mp4?v=2`;
    video.volume = vol; video.muted = muted;
    video.addEventListener("loadedmetadata", function once() {
      video.removeEventListener("loadedmetadata", once);
      video.currentTime = Math.min(t, Math.max(0, video.duration - 0.05));
      if (playing) video.play().catch(() => {});
      draw();
    });
    video.load();
  }
  function setLabel() {
    label.innerHTML = sel === 50 ? "q50 · one action per 1/15 s"
      : `<b style="color:${COLORS["q" + sel]}">q${sel}</b> · with the q50 ghost`;
  }

  /* data helpers (per-frame arrays sampled at D.fps from T = 0, T = time since the policy start) */
  function at(arr, T) {
    const x = Math.min(Math.max(T * D.fps, 0), arr.length - 1), i = Math.floor(x), a = x - i;
    return i + 1 < arr.length ? arr[i] * (1 - a) + arr[i + 1] * a : arr[i];
  }
  function bsearch(a, x) { let lo = 0, hi = a.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (a[m] <= x) lo = m; else hi = m - 1; } return lo; }
  function pointAt(tc) {
    const i = bsearch(D.path_t, tc), j = Math.min(i + 1, D.path.length - 1);
    const a = j > i ? Math.min(1, Math.max(0, (tc - D.path_t[i]) / (D.path_t[j] - D.path_t[i]))) : 0;
    return [D.path[i][0] * (1 - a) + D.path[j][0] * a, D.path[i][1] * (1 - a) + D.path[j][1] * a];
  }
  const segOf = (tc) => Math.min(bsearch(D.seg_bounds, tc), D.seg_names.length - 1);
  const planOf = (tc) => (tc < planT[0] ? null : D.plans[bsearch(planT, tc)][1]);

  function setupView() {
    const xs = D.path.map((p) => p[0]), ys = D.path.map((p) => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const w = x1 - x0, h = y1 - y0, pad = 0.06 * Math.max(w, h), top = 0.22 * h;   // room for the readout
    let W = w + 2 * pad, Hh = h + 2 * pad + top;
    const bb = svg.getBoundingClientRect(), ar = bb.width > 0 && bb.height > 0 ? bb.width / bb.height : 1.5;
    if (W / Hh < ar) W = Hh * ar; else Hh = W / ar;
    vb = [(x0 + x1) / 2 - W / 2, y1 + pad - Hh, W, Hh];
    svg.setAttribute("viewBox", vb.join(" ")); svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  }
  function el(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

  let forcedT = null;                                       // test hook (headless browsers without H.264)
  window.tempoChunkAt = (T, q) => { forcedT = T; if (q) choose(q); draw(); };
  function draw() {
    if (!D) return;
    const T = forcedT !== null ? forcedT : (video.currentTime || 0), u = vb[2] / 140;
    const shown = sel === 50 ? [0] : [0, STOPS.indexOf(sel)];
    const runners = shown.map((k) => { const tc = at(D.tc[k], T); return { k, name: D.names[k], tc, si: segOf(tc), col: COLORS[D.names[k]], done: T >= D.done[k] }; });
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    runners.forEach((rn, idx) => {        // current pick/place segment, its action dots, the chunk running now
      const b0 = D.seg_bounds[rn.si], b1 = D.seg_bounds[rn.si + 1];
      const pts = D.path.filter((_, i) => D.path_t[i] >= b0 && D.path_t[i] <= b1);
      if (pts.length > 1) svg.appendChild(el("polyline", { points: pts.map((p) => p.join(",")).join(" "), fill: "none", stroke: rn.col,
        "stroke-width": u * 0.5, "stroke-opacity": idx ? 0.9 : 0.6, "stroke-linecap": "round", "stroke-linejoin": "round" }));
      D.tick_t.forEach((tt, i) => { if (tt >= b0 && tt <= b1)
        svg.appendChild(el("circle", { cx: D.ticks[i][0], cy: D.ticks[i][1], r: u * 0.6, fill: "#fff", stroke: rn.col, "stroke-width": u * 0.24 })); });
    });
    runners.forEach((rn) => { const p = pointAt(rn.tc);
      svg.appendChild(el("circle", { cx: p[0], cy: p[1], r: u * 1.6, fill: rn.col, stroke: "#111827", "stroke-width": u * 0.3 })); });
    let html = `<div class="clock">${T.toFixed(2)} s</div>`;
    runners.forEach((rn) => {
      const r = D.rate[rn.k][Math.min(Math.round(T * D.fps), D.rate[rn.k].length - 1)];
      html += `<div class="row"><span class="sw" style="background:${rn.col}"></span><b style="color:${rn.col}">${rn.name}</b>` +
        (rn.done ? `<span class="done">done ${D.done[rn.k].toFixed(2)} s</span>`
                 : `<span class="t">×${r.toFixed(2)}</span><span>${D.seg_names[rn.si]}</span>`) + `</div>`;
    });
    readout.innerHTML = html;
  }
  function loop() { draw(); if (!video.paused && !video.ended) requestAnimationFrame(loop); }
  video.addEventListener("play", () => { forcedT = null; requestAnimationFrame(loop); });
  ["seeked", "timeupdate", "loadeddata", "pause"].forEach((ev) => video.addEventListener(ev, draw));

  placeScale(); setLabel();
  fetch("static/data/chunk.json").then((r) => r.json()).then((j) => { D = j; planT = D.plans.map((p) => p[0]); setupView(); draw(); })
    .catch((e) => { readout.textContent = "Could not load chunk data: " + e; });
})();
