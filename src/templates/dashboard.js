// ─── Paleta y utilidades ────────────────────────────────────────────────────
const C = {
  red: "#ff3b3b", gold: "#f0c75e", good: "#3dd68c", bad: "#ff6b6b", blue: "#7aa2ff", sky: "#5ad1e6",
  orange: "#ff9f43", violet: "#b48cff", ink: "#d7e0ea", muted: "#9aa7b8", dim: "#5b6676",
};
const LEG_COLORS = { "Anterior": "#5b6676", "XII": "#7aa2ff", "XII-S": "#5ad1e6", "XIV": "#b48cff", "XV": "#ff3b3b" };
const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DAY = 864e5;

const nf = (v, d = 1) => (v == null || Number.isNaN(v)) ? "—"
  : Number(v).toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d = 1) => v == null ? "—" : (v > 0 ? "+" : "") + nf(v, d);
const hexA = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};
const short = (s, n = 34) => s.length > n ? s.slice(0, n - 1) + "…" : s;
const XY = arr => (arr || []).map(([x, y]) => ({ x, y }));
const scale = (arr, k) => (arr || []).map(([x, y]) => [x, y == null ? null : y / k]);
const yms = arr => (arr || []).map(([y, v]) => [Date.UTC(y, 6, 1), v]);
const last = arr => arr && arr.length ? arr[arr.length - 1] : null;
const $ = id => document.getElementById(id);

function inferFreq(pts) {
  if (!pts || pts.length < 3) return "A";
  const d = (pts[pts.length - 1].x - pts[0].x) / (pts.length - 1) / DAY;
  return d < 45 ? "M" : d < 120 ? "Q" : d < 250 ? "S" : "A";
}
function dlabel(ms, freq) {
  const d = new Date(ms), y = d.getUTCFullYear(), m = d.getUTCMonth();
  if (freq === "M" || freq === "S") return `${MES[m]} ${y}`;
  if (freq === "Q") return `T${Math.floor(m / 3) + 1} ${y}`;
  return `${y}`;
}

// ─── Chart.js: defaults, interacción y plugins ──────────────────────────────
Chart.defaults.color = C.muted;
Chart.defaults.font.family = "Instrument Sans, system-ui, sans-serif";
Chart.defaults.font.size = 11.5;
Chart.defaults.borderColor = "rgba(255,255,255,0.06)";
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.boxHeight = 8;
Chart.defaults.plugins.legend.labels.padding = 14;
Object.assign(Chart.defaults.plugins.tooltip, {
  backgroundColor: "rgba(12,16,23,0.96)", borderColor: "rgba(255,255,255,0.12)", borderWidth: 1,
  padding: 10, titleColor: "#eef2f7", bodyColor: "#d7e0ea", cornerRadius: 10, usePointStyle: true, boxPadding: 4,
});
Chart.defaults.animation.duration = 700;

// Tooltip que reúne, para cada serie, el punto más próximo a la fecha bajo el cursor.
Chart.Interaction.modes.nearestX = function (chart, e) {
  const pos = Chart.helpers.getRelativePosition(e, chart);
  const xs = chart.scales.x;
  if (!xs) return [];
  const xv = xs.getValueForPixel(pos.x);
  let best = null;
  chart.data.datasets.forEach((ds, di) => {
    if (!chart.isDatasetVisible(di)) return;
    ds.data.forEach(p => { const d = Math.abs(p.x - xv); if (p.y != null && (!best || d < best.d)) best = { d, x: p.x }; });
  });
  if (!best) return [];
  const items = [];
  chart.data.datasets.forEach((ds, di) => {
    if (!chart.isDatasetVisible(di)) return;
    let bi = -1, bd = Infinity;
    ds.data.forEach((p, i) => { const d = Math.abs(p.x - best.x); if (p.y != null && d < bd) { bd = d; bi = i; } });
    const tol = ds.freq === "A" ? 200 * DAY : ds.freq === "S" ? 100 * DAY : 50 * DAY;
    if (bi >= 0 && bd <= tol) items.push({ element: chart.getDatasetMeta(di).data[bi], datasetIndex: di, index: bi });
  });
  return items;
};

// Sombreado de legislaturas y línea de inicio de la XV en los gráficos temporales.
Chart.register({
  id: "legShade",
  beforeDatasetsDraw(chart, _a, opts) {
    if (!opts || !opts.on) return;
    const { ctx, chartArea: a, scales: { x } } = chart;
    if (!x || x.type !== "linear") return;
    const legs = D.meta.legislatures;
    ctx.save();
    legs.forEach((l, i) => {
      const s = l.ms, e = i < legs.length - 1 ? legs[i + 1].ms : x.max;
      const x0 = Math.max(x.getPixelForValue(s), a.left), x1 = Math.min(x.getPixelForValue(e), a.right);
      if (x1 <= x0) return;
      const isXV = l.id === "XV";
      ctx.fillStyle = isXV ? "rgba(255,59,59,0.075)" : (i % 2 ? "rgba(255,255,255,0.022)" : "rgba(255,255,255,0)");
      ctx.fillRect(x0, a.top, x1 - x0, a.bottom - a.top);
      if (opts.labels !== false && x1 - x0 > 30) {
        ctx.fillStyle = isXV ? "rgba(255,130,130,0.95)" : "rgba(154,167,184,0.55)";
        ctx.font = "600 10px Instrument Sans";
        ctx.fillText(l.id, x0 + 5, a.top + 12);
      }
    });
    const px = x.getPixelForValue(D.meta.xv_ms);
    if (px > a.left && px < a.right) {
      ctx.strokeStyle = "rgba(255,59,59,0.65)"; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
    }
    ctx.restore();
  },
});

// Líneas de referencia horizontales o verticales con etiqueta.
Chart.register({
  id: "refLines",
  afterDatasetsDraw(chart, _a, opts) {
    const lines = opts && opts.lines;
    if (!lines) return;
    const { ctx, chartArea: a } = chart;
    ctx.save();
    for (const l of lines) {
      const axis = l.axis || "y", sc = chart.scales[axis];
      if (!sc || l.value == null) continue;
      const p = sc.getPixelForValue(l.value);
      ctx.strokeStyle = l.color || "rgba(240,199,94,0.85)"; ctx.lineWidth = 1.2; ctx.setLineDash(l.dash || [5, 4]);
      ctx.beginPath();
      if (axis === "y") { if (p < a.top || p > a.bottom) continue; ctx.moveTo(a.left, p); ctx.lineTo(a.right, p); }
      else { if (p < a.left || p > a.right) continue; ctx.moveTo(p, a.top); ctx.lineTo(p, a.bottom); }
      ctx.stroke();
      if (l.label) {
        ctx.setLineDash([]); ctx.fillStyle = l.color || "rgba(240,199,94,0.95)"; ctx.font = "600 10px Instrument Sans";
        if (axis === "y") ctx.fillText(l.label, a.left + 6, p - 5);
        else { ctx.textAlign = "left"; ctx.fillText(l.label, p + 5, a.bottom - 6); }
      }
    }
    ctx.restore();
  },
});

// Etiquetas de texto junto a los puntos de un scatter (CCAA).
Chart.register({
  id: "pointLabels",
  afterDatasetsDraw(chart, _a, opts) {
    if (!opts || !opts.on) return;
    const { ctx } = chart;
    ctx.save(); ctx.font = "10px Instrument Sans"; ctx.fillStyle = "rgba(215,224,234,0.8)";
    chart.data.datasets.forEach((ds, di) => {
      chart.getDatasetMeta(di).data.forEach((pt, i) => { const lab = ds.data[i].name; if (lab) ctx.fillText(lab, pt.x + 6, pt.y + 3); });
    });
    ctx.restore();
  },
});

function yearTicks(axis) {
  const y0 = new Date(axis.min).getUTCFullYear(), y1 = new Date(axis.max).getUTCFullYear();
  const span = y1 - y0, step = span > 9 ? 2 : 1, ticks = [];
  for (let y = y0; y <= y1 + 1; y += step) {
    const t = Date.UTC(y, 0, 1);
    if (t >= axis.min && t <= axis.max) ticks.push({ value: t });
    if (span < 5) { const h = Date.UTC(y, 6, 1); if (h >= axis.min && h <= axis.max) ticks.push({ value: h }); }
  }
  axis.ticks = ticks.sort((a, b) => a.value - b.value);
}
const yearTickLabel = v => { const d = new Date(v); return d.getUTCMonth() === 0 ? d.getUTCFullYear() : MES[d.getUTCMonth()]; };

// ─── Selector global de periodo ─────────────────────────────────────────────
const RANGES = {
  all: Date.UTC(2013, 6, 1), "2019": Date.UTC(2019, 0, 1),
  XIV: D.meta.xiv_ms - 120 * DAY, XV: D.meta.xv_ms - 200 * DAY,
};
let rangeMin = RANGES.all;
const TS = [];
const inRange = (full, min) => full.filter(p => p.x >= min);

function applyRange(chart) {
  const min = chart.$fixedMin ?? rangeMin;
  chart.data.datasets.forEach(ds => { ds.data = inRange(ds.$full, min); });
  chart.options.scales.x.min = min;
  chart.update();
}

// ─── Constructores de gráficos ──────────────────────────────────────────────
function axisFmt(dec, suffix) { return v => nf(v, dec) + (suffix || ""); }

// Gráfico temporal (eje x lineal en milisegundos).
function ts(id, sets, o = {}) {
  const el = $(id); if (!el) return null;
  const min = o.fixedMin ?? rangeMin;
  const datasets = sets.map(s => {
    const full = XY(s.data);
    const isBar = s.type === "bar";
    const color = s.color || C.ink;
    return {
      label: s.label, type: s.type || "line", $full: full, data: inRange(full, min), freq: s.freq || inferFreq(full),
      borderColor: isBar ? "transparent" : color,
      backgroundColor: s.bg || (isBar ? (ctx => ((ctx.raw && ctx.raw.y) || 0) >= 0 ? hexA(s.pos || color, 0.75) : hexA(s.neg || C.bad, 0.75)) : hexA(color, 0.15)),
      borderWidth: s.width ?? 2.2, borderDash: s.dash || [], pointRadius: s.points ? 2.6 : 0, pointHoverRadius: 4,
      pointBackgroundColor: color, tension: s.tension ?? 0.25, fill: s.fill || false, yAxisID: s.y || "y",
      spanGaps: true, order: s.order ?? (isBar ? 2 : 1), hidden: !!s.hidden, borderRadius: isBar ? 2 : 0,
      barThickness: isBar ? "flex" : undefined, barPercentage: 0.9, categoryPercentage: 0.95,
    };
  });
  const scales = {
    x: {
      type: "linear", min, bounds: "data", afterBuildTicks: yearTicks, grid: { color: "rgba(255,255,255,0.035)" },
      ticks: { callback: yearTickLabel, maxRotation: 0, autoSkip: false },
    },
    y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: axisFmt(o.yDec ?? 0, o.ySuffix) }, ...(o.y || {}) },
  };
  if (o.y2) scales.y2 = { position: "right", grid: { display: false }, ticks: { callback: axisFmt(o.y2Dec ?? 0, o.y2Suffix) }, ...o.y2 };
  const chart = new Chart(el, {
    type: "line",
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "nearestX", intersect: false },
      plugins: {
        legend: { display: o.legend ?? datasets.length > 1, position: "top", align: "start" },
        tooltip: {
          callbacks: {
            title: items => items.length ? dlabel(items[0].parsed.x, items[0].dataset.freq) : "",
            label: ctx => ` ${ctx.dataset.label}: ${nf(ctx.parsed.y, o.tipDec ?? 1)}${(ctx.dataset.yAxisID === "y2" ? o.tip2Suffix : o.tipSuffix) || ""}`,
          },
        },
        legShade: { on: o.shade !== false },
        refLines: { lines: o.lines },
      },
      scales,
    },
  });
  chart.$fixedMin = o.fixedMin;
  if (o.fixedMin == null) TS.push(chart);
  return chart;
}

// Barras horizontales ordenadas.
function hbar(id, rows, o = {}) {
  const el = $(id); if (!el) return null;
  const colors = rows.map(r => r.color || (o.colorFn ? o.colorFn(r.value, r) : (r.value >= 0 ? hexA(o.pos || C.red, 0.78) : hexA(o.neg || C.good, 0.78))));
  return new Chart(el, {
    type: "bar",
    data: { labels: rows.map(r => short(r.label, o.trunc || 34)), datasets: [{ data: rows.map(r => r.value), backgroundColor: colors, borderRadius: 5, borderSkipped: false, barPercentage: 0.78 }] },
    options: {
      indexAxis: "y", responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: it => rows[it[0].dataIndex].label, label: ctx => ` ${o.tip ? o.tip(rows[ctx.dataIndex]) : nf(ctx.parsed.x, o.dec ?? 1) + (o.suffix || "")}` } },
        refLines: { lines: o.lines },
      },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: axisFmt(o.axDec ?? 0, o.suffix) }, ...(o.x || {}) },
        y: { grid: { display: false }, ticks: { font: { size: 10.5 }, color: C.ink, autoSkip: false } },
      },
    },
  });
}

// Gráfico de categorías (años, tramos de edad…).
function cat(id, labels, sets, o = {}) {
  const el = $(id); if (!el) return null;
  return new Chart(el, {
    type: o.type || "line",
    data: {
      labels,
      datasets: sets.map(s => ({
        label: s.label, data: s.data, type: s.type, borderColor: s.color, backgroundColor: s.bg || hexA(s.color, s.type === "bar" || o.type === "bar" ? 0.75 : 0.15),
        borderWidth: s.width ?? 2.2, borderDash: s.dash || [], pointRadius: s.points ?? 3, pointHoverRadius: 5, pointBackgroundColor: s.color,
        tension: 0.25, borderRadius: 4, fill: s.fill || false, yAxisID: s.y || "y", order: s.order ?? 1,
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: o.legend ?? sets.length > 1, position: "top", align: "start" },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${nf(ctx.parsed.y, o.tipDec ?? 1)}${o.tipSuffix || ""}` } },
        refLines: { lines: o.lines },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
        y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: axisFmt(o.yDec ?? 0, o.ySuffix) }, ...(o.y || {}) },
        ...(o.y2 ? { y2: { position: "right", grid: { display: false }, ticks: { callback: axisFmt(o.y2Dec ?? 0, o.y2Suffix) }, ...o.y2 } } : {}),
      },
    },
  });
}

// ─── HERO ───────────────────────────────────────────────────────────────────
const K = Object.fromEntries(D.kpis.map(k => [k.key, k]));
function kpiValue(k) {
  if (k.unit === "miles") return [nf(k.latest / 1000, 2), "M"];
  if (k.unit === "€") return [nf(k.latest, 0), "€"];
  if (k.unit === "%") return [nf(k.latest, 1), "%"];
  return [nf(k.latest, 1), k.unit === "índice" ? "" : k.unit];
}
function kpiDelta(k) {
  if (k.delta == null) return "—";
  if (k.unit === "%") return `${sgn(k.delta, 2)} pp`;
  if (k.unit === "miles") return `${sgn(k.delta, 0)} mil (${sgn(k.delta_pct, 1)}%)`;
  if (k.unit === "€") return `${sgn(k.delta, 0)} € (${sgn(k.delta_pct, 1)}%)`;
  return `${sgn(k.delta, 2)}`;
}
const cls = imp => imp === true ? "good" : imp === false ? "bad" : "neutral";
const arrow = d => d == null ? "" : d > 0 ? "▲ " : d < 0 ? "▼ " : "";

function renderHero() {
  const m = D.meta;
  $("heroMeta").innerHTML = [
    `Investidura <strong>16 nov 2023</strong>`, `Último dato <strong>${dlabel(Date.parse(m.last), "M")}</strong>`,
    `<strong>${nf(m.n_series, 0)}</strong> series`, `<strong>${nf(m.n_obs, 0)}</strong> observaciones`,
    `<strong>${m.n_tables}</strong> tablas INE`, `Generado <strong>${m.generated}</strong>`,
  ].map(t => `<div class="chip">${t}</div>`).join("");
  const stats = [
    ["paro", "Tasa de paro", K.paro], ["ocupados", "Ocupados", K.ocupados],
    ["ipc", "Inflación (IPC)", K.ipc], ["ipv", "Precio de la vivienda", K.ipv],
  ];
  $("heroStats").innerHTML = stats.map(([_, l, k]) => {
    const [v, u] = kpiValue(k);
    return `<div class="hero-stat"><div class="n">${v}<small>${u}</small></div><div class="l">${l} · ${k.latest_label}</div>
      <div class="d ${cls(k.improved)}">${arrow(k.delta)}${kpiDelta(k)} en la XV</div></div>`;
  }).join("");
  // Fondo decorativo: paro en rojo y PIB en dorado.
  const p = XY(D.s.paro), g = XY(D.s.pib_indice);
  new Chart($("heroBg"), {
    type: "line",
    data: { datasets: [
      { data: p, borderColor: hexA(C.red, 0.55), borderWidth: 2, pointRadius: 0, tension: 0.35, fill: { target: "origin", above: hexA(C.red, 0.06) }, yAxisID: "y" },
      { data: g, borderColor: hexA(C.gold, 0.4), borderWidth: 1.5, pointRadius: 0, tension: 0.35, yAxisID: "y2" },
    ] },
    options: { responsive: true, maintainAspectRatio: false, animation: { duration: 1800 }, events: [],
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { type: "linear", display: false }, y: { display: false, min: 0 }, y2: { display: false } } },
  });
}

// ─── RESUMEN ────────────────────────────────────────────────────────────────
function renderScorecard() {
  const blocks = [...new Set(D.kpis.map(k => k.block))];
  $("kpiFilter").innerHTML = [`<button class="pill on" data-b="all">Todos</button>`,
    ...blocks.map(b => `<button class="pill" data-b="${b}">${D.meta.blocks[b]}</button>`)].join("");
  $("kpiGrid").innerHTML = D.kpis.map(k => {
    const [v, u] = kpiValue(k);
    const xiv = k.xiv_delta == null ? "" : `<div class="xiv">En la XIV: ${k.unit === "%" ? sgn(k.xiv_delta, 2) + " pp" : k.unit === "miles" ? sgn(k.xiv_delta, 0) + " mil" : sgn(k.xiv_delta, 0) + (k.unit === "€" ? " €" : "")}</div>`;
    return `<article class="kpi" data-b="${k.block}" title="${k.desc || ""}">
      <div class="blk">${k.block_name}</div>
      <div class="label">${k.label}</div>
      <div class="value">${v}<small>${u}</small></div>
      <div class="delta ${cls(k.improved)}">${arrow(k.delta)}${kpiDelta(k)}</div>
      <div class="periodo">${k.start_label} → ${k.latest_label}</div>
      ${xiv}
      <div class="spark"><canvas id="sp_${k.key}"></canvas></div>
    </article>`;
  }).join("");
  D.kpis.forEach(k => {
    const color = k.improved === true ? C.good : k.improved === false ? C.bad : C.muted;
    new Chart($(`sp_${k.key}`), {
      type: "line",
      data: { datasets: [{ data: XY(k.spark), borderColor: color, borderWidth: 1.6, pointRadius: 0, tension: 0.3,
        fill: { target: "origin", above: hexA(color, 0.08), below: hexA(color, 0.08) } }] },
      options: { responsive: true, maintainAspectRatio: false, events: [], animation: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false }, legShade: { on: true, labels: false } },
        scales: { x: { type: "linear", display: false }, y: { display: false, grace: "10%" } } },
    });
  });
  $("kpiFilter").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    document.querySelectorAll("#kpiFilter .pill").forEach(x => x.classList.toggle("on", x === b));
    document.querySelectorAll("#kpiGrid .kpi").forEach(c => c.classList.toggle("hide", b.dataset.b !== "all" && c.dataset.b !== b.dataset.b));
  });

  const scored = D.kpis.filter(k => k.improved != null), good = scored.filter(k => k.improved).length;
  $("scoreN").innerHTML = `${good}<span> / ${scored.length}</span>`;
  $("scoreBar").style.width = `${good / scored.length * 100}%`;

  const z = D.kpis.filter(k => k.z != null).sort((a, b) => b.z - a.z);
  hbar("chBalance", z.map(k => ({ label: k.label, value: k.z, k })), {
    pos: C.good, neg: C.bad, dec: 2, axDec: 1, trunc: 30,
    tip: r => `${nf(r.value, 2)} σ · ${kpiDelta(r.k)}`,
  });

  $("insights").innerHTML = D.insights.map(i => `<article class="insight ${i.tone}">
    <div class="blk">${D.meta.blocks[i.block] || i.block}</div><h4>${i.title}</h4><p>${i.body}</p></article>`).join("");
}

// ─── EMPLEO ─────────────────────────────────────────────────────────────────
function renderEmpleo() {
  const s = D.s, E = D.empleo;
  ts("chParo", [
    { label: "Total", data: s.paro, color: C.red, width: 2.8 },
    { label: "Mujeres", data: s.paro_mujeres, color: C.gold, width: 1.6 },
    { label: "Hombres", data: s.paro_hombres, color: C.blue, width: 1.6 },
  ], { ySuffix: "%", tipSuffix: "%", tipDec: 2 });
  ts("chParoJuv", [
    { label: "< 25 años", data: s.paro_juvenil, color: C.gold, width: 2.6, fill: "origin" },
    { label: "Total", data: s.paro, color: C.muted, width: 1.4, dash: [4, 4] },
  ], { ySuffix: "%", tipSuffix: "%", tipDec: 2 });
  ts("chOcupados", [{ label: "Ocupados (M)", data: scale(s.ocupados, 1000), color: C.good, width: 2.6, fill: "origin" }],
    { yDec: 1, tipDec: 2, tipSuffix: " M" });
  $("sectorSub").textContent = `Variación del empleo por rama, ${E.sector_since} → ${E.sector_to} (%) · CNTR`;
  hbar("chSector", [...E.sector].reverse().map(r => ({ label: r.name, value: r.pct, abs: r.abs })), {
    pos: C.good, neg: C.bad, suffix: "%", trunc: 30, tip: r => `${sgn(r.value, 1)}% (${sgn(r.abs, 0)} mil puestos)`,
    lines: [{ axis: "x", value: E.sector_total, label: "Total" }],
  });
  ts("chTemp", [{ label: "Temporalidad", data: s.temporalidad, color: C.blue, width: 2.6, points: true }],
    { ySuffix: "%", tipSuffix: "%" });

  const legs = [...new Set(E.beveridge.map(p => p.leg))];
  const bev = $("chBeveridge");
  new Chart(bev, {
    type: "scatter",
    data: { datasets: legs.map(l => ({
      label: l, data: E.beveridge.filter(p => p.leg === l), showLine: true, borderColor: hexA(LEG_COLORS[l], 0.6),
      backgroundColor: LEG_COLORS[l], pointRadius: l === "XV" ? 4 : 3, borderWidth: 1.2, tension: 0.2,
    })) },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { tooltip: { callbacks: { label: ctx => ` ${ctx.raw.label}: paro ${nf(ctx.raw.x, 2)}% · ${nf(ctx.raw.y, 0)} vacantes` } } },
      scales: { x: { title: { display: true, text: "Tasa de paro (%)" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { title: { display: true, text: "Vacantes" }, ticks: { callback: v => nf(v / 1000, 0) + " mil" }, grid: { color: "rgba(255,255,255,0.05)" } } } },
  });

  const P = E.productividad, pick = n => Object.keys(P).find(k => k.startsWith(n));
  ts("chProd", [
    { label: "Coste laboral unitario", data: P[pick("Coste laboral")], color: C.red, width: 2.2 },
    { label: "Productividad por hora", data: P[pick("Productividad por hora")], color: C.good, width: 2.4 },
    { label: "Remuneración por asalariado", data: P[pick("Remuneración")], color: C.gold, width: 1.6 },
  ], { ySuffix: "%", tipSuffix: "%", lines: [{ value: 0, color: "rgba(255,255,255,0.3)", dash: [2, 3] }] });
  const L = E.paro_ld, lc = [C.gold, C.blue, C.red];
  ts("chParoLd", Object.keys(L).map((k, i) => ({ label: k.replace("De ", "").replace(" años", ""), data: L[k], color: lc[i] })),
    { ySuffix: "%", tipSuffix: "%" });
}

// ─── PRECIOS ────────────────────────────────────────────────────────────────
function renderPrecios() {
  const s = D.s, P = D.precios;
  ts("chIpc", [
    { label: "General", data: s.ipc, color: C.ink, width: 2.6 },
    { label: "Subyacente", data: s.ipc_subyacente, color: C.blue, width: 2.2 },
  ], { ySuffix: "%", tipSuffix: "%", lines: [{ value: 2, label: "Objetivo BCE 2%", color: hexA(C.good, 0.9) }] });
  ts("chIpcComp", [
    { label: "Energía", data: s.ipc_energia, color: C.red, width: 1.6, y: "y2" },
    { label: "Alimentos, bebidas y tabaco", data: s.ipc_alimentos, color: C.gold, width: 2.2 },
    { label: "Servicios", data: s.ipc_servicios, color: C.sky, width: 2.2 },
  ], { ySuffix: "%", tipSuffix: "%", tip2Suffix: "%", y2: { title: { display: true, text: "Energía (%)", color: C.red } }, y2Suffix: "%" });
  const g = Object.entries(P.grupos.values).filter(([k]) => !/general/i.test(k)).sort((a, b) => b[1] - a[1]);
  $("ipcGruposSub").textContent = `Variación anual (%) · ${P.grupos.date}`;
  hbar("chIpcGrupos", g.map(([k, v]) => ({ label: k, value: v })), { suffix: "%", trunc: 32, lines: [{ axis: "x", value: K.ipc.latest, label: "General" }] });
  const cc = Object.entries(P.ccaa.values).sort((a, b) => b[1] - a[1]);
  $("ipcCcaaSub").textContent = `Variación anual (%) · ${P.ccaa.date}`;
  hbar("chIpcCcaa", cc.map(([k, v]) => ({ label: k, value: v })), { suffix: "%", lines: [{ axis: "x", value: K.ipc.latest, label: "España" }] });

  const H = P.heat, cols = H.years.length;
  const color = v => v == null ? "transparent" : v >= 0 ? hexA(C.red, Math.min(0.85, 0.08 + v / 12)) : hexA(C.blue, Math.min(0.85, 0.15 - v / 6));
  let html = `<div class="heat" style="grid-template-columns: minmax(170px, 230px) repeat(${cols}, minmax(38px, 1fr))"><div class="hh"></div>`;
  html += H.years.map(y => `<div class="hh">${y}</div>`).join("");
  H.groups.forEach((gname, gi) => {
    html += `<div class="hl" title="${gname}">${short(gname, 34)}</div>`;
    html += H.values[gi].map((v, yi) => `<div style="background:${color(v)}" title="${gname} · ${H.years[yi]}: ${nf(v, 1)}%">${nf(v, 1)}</div>`).join("");
  });
  $("heatIpc").innerHTML = html + "</div>";
}

// ─── SALARIOS ───────────────────────────────────────────────────────────────
function renderSalarios() {
  const W = D.salarios;
  ts("chReal", [
    { label: "Salario nominal", data: W.nominal_idx, color: C.gold, width: 2 },
    { label: "Precios (IPC)", data: W.ipc_idx, color: C.red, width: 2 },
    { label: "Salario real", data: W.real_idx, color: C.good, width: 3 },
  ], { yDec: 0, tipDec: 1, lines: [{ value: 100, color: "rgba(255,255,255,0.35)", dash: [2, 3] }] });
  const ln = last(W.nominal_idx)[1], li = last(W.ipc_idx)[1], lr = last(W.real_idx)[1];
  $("realNote").innerHTML = `Desde el inicio de la XV el salario nominal crece un <strong>${sgn(ln - 100, 1)}%</strong> y los precios un
    <strong>${sgn(li - 100, 1)}%</strong>: el salario real varía un <strong>${sgn(lr - 100, 1)}%</strong>. Antes de 2023 la línea verde muestra la
    pérdida de poder adquisitivo acumulada durante el episodio inflacionario.`;
  ts("chRealYoy", [
    { label: "Salario real (pp)", data: W.real_yoy, type: "bar", color: C.good, pos: C.good, neg: C.bad },
    { label: "Salario nominal (%)", data: W.nominal_yoy, color: C.gold, width: 1.4 },
    { label: "IPC (%)", data: W.ipc_yoy, color: C.red, width: 1.4, dash: [4, 3] },
  ], { ySuffix: "", tipDec: 1 });
  $("distSub").textContent = `Ganancia anual por trabajador · índice 100 = ${W.dist_base}`;
  const lab = { p10: "Percentil 10", mediana: "Mediana", medio: "Media", p90: "Percentil 90" };
  const col = { p10: C.good, mediana: C.gold, medio: C.ink, p90: C.blue };
  ts("chDist", Object.keys(W.dist_idx).map(k => ({ label: lab[k], data: W.dist_idx[k], color: col[k], points: true, dash: k === "medio" ? [4, 3] : [] })),
    { fixedMin: Date.UTC(2008, 6, 1), tipDec: 1, lines: [{ value: 100, color: "rgba(255,255,255,0.3)", dash: [2, 3] }] });
  ts("chP9010", [{ label: "P90 / P10", data: W.p90p10, color: C.violet, width: 2.6, points: true, fill: "origin" }],
    { fixedMin: Date.UTC(2008, 6, 1), yDec: 1, tipDec: 2, y: { min: 3.5 } });
}

// ─── GÉNERO ─────────────────────────────────────────────────────────────────
function renderGenero() {
  const G = D.genero;
  const lh = last(G.gap.por_hora), la = last(G.gap.anual_media), lm = last(G.gap.anual_mediana), fh = G.gap.por_hora[0], lp = last(G.paro_gap);
  const y = ms => new Date(ms).getUTCFullYear();
  $("genderKpis").innerHTML = [
    [nf(lh[1], 1) + "%", `Brecha por hora (${y(lh[0])}) · ${nf(fh[1], 1)}% en ${y(fh[0])}`],
    [nf(la[1], 1) + "%", `Brecha en ganancia anual media (${y(la[0])})`],
    [nf(lm[1], 1) + "%", `Brecha en ganancia anual mediana (${y(lm[0])})`],
    [sgn(lp[1], 2) + " pp", `Paro mujeres − hombres (${dlabel(lp[0], "Q")})`],
  ].map(([n, l]) => `<div class="mini"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");
  const opt = { fixedMin: Date.UTC(2008, 6, 1), ySuffix: "%", tipSuffix: "%", tipDec: 1, y: { min: 0 } };
  ts("chGap", [
    { label: "Ganancia anual media", data: G.gap.anual_media, color: C.red, width: 2.6, points: true },
    { label: "Ganancia anual mediana", data: G.gap.anual_mediana, color: C.orange, width: 1.8, points: true, dash: [4, 3] },
    { label: "Salario por hora", data: G.gap.por_hora, color: C.gold, width: 2.6, points: true },
  ], opt);
  ts("chGapSal", [
    { label: "Hombres", data: G.salario_h, color: C.blue, width: 2.4, points: true },
    { label: "Mujeres", data: G.salario_m, color: C.gold, width: 2.4, points: true },
  ], { fixedMin: Date.UTC(2008, 6, 1), yDec: 0, tipDec: 0, tipSuffix: " €", ySuffix: " €" });
  const gapColor = v => v < 0 ? hexA(C.good, 0.8) : hexA(C.gold, 0.3 + Math.min(0.6, v / 40));
  const tipGap = r => `${nf(r.value, 1)}% · H ${nf(r.h, r.h < 100 ? 2 : 0)} € · M ${nf(r.m, r.m < 100 ? 2 : 0)} €`;
  $("gapOccSub").textContent = `% · ganancia media anual · ${G.year}`;
  $("gapActSub").textContent = `% · ganancia media anual · ${G.year}`;
  hbar("chGapOcc", G.occupation.map(r => ({ label: r.name, value: r.gap, h: r.h, m: r.m })), { colorFn: gapColor, suffix: "%", trunc: 38, tip: tipGap, lines: [{ axis: "x", value: la[1], label: "Total" }] });
  hbar("chGapAct", G.activity.map(r => ({ label: r.name, value: r.gap, h: r.h, m: r.m })), { colorFn: gapColor, suffix: "%", trunc: 38, tip: tipGap, lines: [{ axis: "x", value: la[1], label: "Total" }] });
  hbar("chGapCcaa", [...G.ccaa].reverse().map(r => ({ label: r.name, value: r.gap })), { colorFn: gapColor, suffix: "%", lines: [{ axis: "x", value: G.ccaa_spain, label: "España" }] });
  ts("chGapParo", [{ label: "Brecha de paro (pp)", data: G.paro_gap, color: C.gold, width: 2.4, fill: "origin" }], { yDec: 1, tipDec: 2, tipSuffix: " pp" });
  cat("chGapSector", G.sector_hour.map(r => r.name), [
    { label: "Hombres €/h", data: G.sector_hour.map(r => r.h), color: C.blue },
    { label: "Mujeres €/h", data: G.sector_hour.map(r => r.m), color: C.gold },
  ], { type: "bar", tipDec: 2, tipSuffix: " €/h", ySuffix: " €" });
}

// ─── CRECIMIENTO ────────────────────────────────────────────────────────────
function renderCrecimiento() {
  const s = D.s, F = D.macro.flows;
  ts("chPib", [
    { label: "Var. anual", data: s.pib, type: "bar", color: C.good, pos: C.good, neg: C.bad },
    { label: "Var. trimestral", data: s.pib_trimestral, color: C.gold, width: 1.8 },
  ], { ySuffix: "%", tipSuffix: "%", tipDec: 2 });
  ts("chPibIdx", [{ label: "PIB real (índice)", data: s.pib_indice, color: C.good, width: 2.8, fill: "origin" }], { y: { min: 80 }, tipDec: 1 });
  const pre = D.s.pib_indice.filter(p => p[0] <= Date.UTC(2019, 11, 31)).pop(), lp = last(D.s.pib_indice);
  $("pibNote").innerHTML = `El PIB real está un <strong>${sgn((lp[1] / pre[1] - 1) * 100, 1)}%</strong> por encima del nivel previo a la pandemia (T4 2019). La caída
    de 2020 fue la mayor de la serie y la recuperación del nivel no llegó hasta finales de 2022.`;
  ts("chTur", [
    { label: "Turistas (M)", data: scale(F.turistas, 1e6), color: C.blue, width: 2.4 },
    { label: "Gasto (miles de M€)", data: scale(F.gasto_turistas, 1000), color: C.gold, width: 2.4, y: "y2" },
  ], { yDec: 0, tipDec: 1, tipSuffix: " M", tip2Suffix: " mil M€", y2Dec: 0 });
  ts("chIpi", [
    { label: "IPI var. anual (%)", data: s.ipi, color: C.sky, width: 1.4 },
    { label: "Sociedades constituidas (12m, miles)", data: scale(F.sociedades, 1000), color: C.violet, width: 2.4, y: "y2" },
  ], { ySuffix: "%", tipDec: 1, y2Dec: 0 });
}

// ─── VIVIENDA ───────────────────────────────────────────────────────────────
function renderVivienda() {
  const s = D.s, M = D.macro, F = M.flows;
  ts("chIpv", [
    { label: "General", data: s.ipv, color: C.gold, width: 2.8 },
    { label: "Nueva", data: s.ipv_nueva, color: C.orange, width: 1.5 },
    { label: "Segunda mano", data: s.ipv_segunda, color: C.red, width: 1.5 },
  ], { ySuffix: "%", tipSuffix: "%", lines: [{ value: 0, color: "rgba(255,255,255,0.3)", dash: [2, 3] }] });
  const E = M.esfuerzo;
  ts("chEsfuerzo", [
    { label: "Precio vivienda (IPV)", data: E.ipv_idx, color: C.red, width: 2.6 },
    { label: "Salario (ETCL)", data: E.salario_idx, color: C.good, width: 2.6 },
    { label: "Alquiler (IPVA)", data: E.alquiler_idx, color: C.gold, width: 1.8, dash: [4, 3] },
    { label: "Índice de esfuerzo", data: E.esfuerzo, color: C.ink, width: 1.4, dash: [2, 3] },
  ], { fixedMin: Date.UTC(2015, 0, 1), tipDec: 1, lines: [{ value: 100, color: "rgba(255,255,255,0.3)", dash: [2, 3] }] });
  const li = last(E.ipv_idx)[1], ls = last(E.salario_idx)[1], le = last(E.esfuerzo)[1];
  $("esfuerzoNote").innerHTML = `Desde 2015 la vivienda se ha encarecido un <strong>${sgn(li - 100, 0)}%</strong> y los salarios han subido un <strong>${sgn(ls - 100, 0)}%</strong>.
    El índice de esfuerzo está en <strong>${nf(le, 0)}</strong>: comprar cuesta un ${nf(le - 100, 0)}% más «salarios» que en 2015.`;
  const ic = Object.entries(M.ipv_ccaa.values).sort((a, b) => b[1] - a[1]);
  $("ipvCcaaSub").textContent = `IPV, variación anual (%) · ${M.ipv_ccaa.date}`;
  hbar("chIpvCcaa", ic.map(([k, v]) => ({ label: k, value: v })), { suffix: "%", lines: [{ axis: "x", value: K.ipv.latest, label: "España" }] });
  ts("chHip", [
    { label: "Hipotecas (12m, miles)", data: scale(F.hipotecas, 1000), color: C.blue, width: 2.6, fill: "origin" },
    { label: "Tipo de interés (%)", data: s.tipo_hipoteca, color: C.gold, width: 2, y: "y2" },
  ], { yDec: 0, tipDec: 1, tip2Suffix: "%", y2Suffix: "%", y2Dec: 1, y: { min: 0 } });
}

// ─── BIENESTAR ──────────────────────────────────────────────────────────────
function renderBienestar() {
  const s = D.s;
  ts("chArope", [
    { label: "AROPE", data: s.arope, color: C.red, width: 2.6, points: true },
    { label: "AROPE menores de 16", data: s.arope_infantil, color: C.orange, width: 1.8, points: true },
    { label: "Riesgo de pobreza", data: s.pobreza, color: C.gold, width: 2.2, points: true },
    { label: "Carencia material severa", data: s.carencia_severa, color: C.blue, width: 1.8, points: true },
  ], { ySuffix: "%", tipSuffix: "%", y: { min: 0 } });
  ts("chGini", [
    { label: "Gini", data: s.gini, color: C.blue, width: 2.6, points: true },
    { label: "S80/S20", data: s.s80s20, color: C.gold, width: 2.2, points: true, y: "y2" },
  ], { yDec: 0, tipDec: 1, y2Dec: 1 });
  const ac = Object.entries(D.macro.arope_ccaa.values).sort((a, b) => b[1] - a[1]);
  $("aropeCcaaSub").textContent = `% de la población · ECV ${D.macro.arope_ccaa.date}`;
  hbar("chAropeCcaa", ac.map(([k, v]) => ({ label: k, value: v })), {
    suffix: "%", colorFn: v => hexA(C.red, 0.25 + Math.min(0.65, v / 50)), lines: [{ axis: "x", value: K.arope.latest, label: "España" }],
  });
}

// ─── DEMOGRAFÍA ─────────────────────────────────────────────────────────────
function renderDemografia() {
  const P = D.demografia, F = D.macro.flows;
  ts("chPob", [
    { label: "Población (M)", data: yms(P.pop), color: C.blue, width: 2.8, points: true, freq: "A" },
    { label: "% extranjeros", data: yms(P.foreign_pct), color: C.gold, width: 2.2, points: true, y: "y2", freq: "A" },
  ], { fixedMin: Date.UTC(2010, 0, 1), yDec: 1, tipDec: 2, tipSuffix: " M", tip2Suffix: "%", y2Suffix: "%", y2Dec: 0 });
  const lp = last(P.pop), lf = last(P.foreign_pct), mf = P.foreign_pct.reduce((a, b) => b[1] < a[1] ? b : a);
  $("pobNote").innerHTML = `<strong>${nf(lp[1], 2)} millones</strong> de residentes de media en ${lp[0]}. El peso de la población extranjera pasa del
    <strong>${nf(mf[1], 1)}%</strong> (${mf[0]}, su mínimo) al <strong>${nf(lf[1], 1)}%</strong>.`;
  $("pyrSub").textContent = `Personas · ${P.pyramid_date}`;
  const rows = [...P.pyramid].reverse();
  new Chart($("chPyr"), {
    type: "bar",
    data: {
      labels: rows.map(r => r.group),
      datasets: [
        { label: "Hombres · española", data: rows.map(r => -r.Hombres_esp), backgroundColor: hexA(C.blue, 0.75), stack: "s" },
        { label: "Hombres · extranjera", data: rows.map(r => -r.Hombres_ext), backgroundColor: hexA(C.gold, 0.9), stack: "s" },
        { label: "Mujeres · española", data: rows.map(r => r.Mujeres_esp), backgroundColor: hexA(C.red, 0.6), stack: "s" },
        { label: "Mujeres · extranjera", data: rows.map(r => r.Mujeres_ext), backgroundColor: hexA(C.gold, 0.9), stack: "s" },
      ],
    },
    options: {
      indexAxis: "y", responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "top", align: "start" }, tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${nf(Math.abs(ctx.parsed.x), 0)}` } } },
      scales: {
        x: { stacked: true, ticks: { callback: v => nf(Math.abs(v) / 1e6, 1) + " M" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { stacked: true, grid: { display: false }, ticks: { font: { size: 9.5 } } },
      },
    },
  });
  ts("chNac", [{ label: "Nacimientos (12m, miles)", data: scale(F.nacimientos, 1000), color: C.violet, width: 2.6, fill: "origin" }],
    { yDec: 0, tipDec: 1, tipSuffix: " mil", y: { min: 250 } });
  const mig = D.s.saldo_migratorio || [], migx = D.s.saldo_exterior || [];
  cat("chMig", mig.map(p => new Date(p[0]).getUTCFullYear()), [
    { label: "Saldo total", data: mig.map(p => p[1]), color: C.good },
    { label: "Saldo con el extranjero", data: migx.map(p => p[1]), color: C.blue },
  ], { type: "bar", tipDec: 0, y: { ticks: { callback: v => nf(v / 1000, 0) + " mil" } } });
}

// ─── JUSTICIA ───────────────────────────────────────────────────────────────
function renderJusticia() {
  const J = D.justicia, yrs = J.years, R = J.rates, li = yrs.length - 1;
  const re = R["extranjera"], rs = R["española"];
  const rb = J.ratios.ratio_bruta[li], ra = J.ratios.ratio_edad[li], ras = J.ratios.ratio_edad_sexo[li];
  const fs = J.foreign_share.find(p => p[0] === J.last) || last(J.foreign_share);
  $("crimeKpis").innerHTML = [
    [nf(re.tasa_bruta[li], 1), `Condenados por 1.000 adultos extranjeros (${J.last}, bruta)`],
    [nf(rs.tasa_bruta[li], 1), `Condenados por 1.000 adultos españoles (${J.last}, bruta)`],
    [nf(rb, 2) + "×", "Ratio bruto extranjeros / españoles"],
    [nf(ras, 2) + "×", "Ratio ajustado por edad y sexo"],
    [nf(fs[1], 1) + "%", `Peso de los extranjeros en la población adulta (${fs[0]})`],
  ].map(([n, l]) => `<div class="mini"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

  cat("chCrRates", yrs, [
    { label: "Extranjera · bruta", data: re.tasa_bruta, color: C.gold, dash: [5, 4], width: 1.6 },
    { label: "Extranjera · ajustada", data: re.tasa_edad_sexo, color: C.gold, width: 3 },
    { label: "Española · bruta", data: rs.tasa_bruta, color: C.blue, dash: [5, 4], width: 1.6 },
    { label: "Española · ajustada", data: rs.tasa_edad_sexo, color: C.blue, width: 3 },
  ], { tipDec: 2, y: { min: 0 } });
  cat("chCrRatio", yrs, [
    { label: "Bruto", data: J.ratios.ratio_bruta, color: C.muted, width: 2 },
    { label: "Ajustado por edad", data: J.ratios.ratio_edad, color: C.gold, width: 2 },
    { label: "Ajustado por edad y sexo", data: J.ratios.ratio_edad_sexo, color: C.red, width: 3 },
  ], { tipDec: 2, yDec: 1, tipSuffix: "×", y: { min: 0, max: 3.2 }, lines: [{ value: 1, label: "Misma tasa", color: "rgba(255,255,255,0.55)" }] });
  const peakI = J.ratios.ratio_edad_sexo.reduce((bi, v, i, a) => v > a[bi] ? i : bi, 0);
  $("ratioNote").innerHTML = `En ${J.last} la tasa bruta de los extranjeros es <strong>${nf(rb, 2)} veces</strong> la de los españoles. Ajustando por edad baja a
    <strong>${nf(ra, 2)}</strong> y por edad y sexo a <strong>${nf(ras, 2)}</strong>: el exceso pasa de +${nf((rb - 1) * 100, 0)}% a +${nf((ras - 1) * 100, 0)}%,
    así que <strong>casi la mitad de la diferencia bruta es demográfica</strong>. El ratio ajustado ha bajado desde su máximo (${nf(J.ratios.ratio_edad_sexo[peakI], 2)} en ${yrs[peakI]})
    mientras el peso de los extranjeros en la población crecía.`;
  $("ageSub").textContent = `% de la población adulta de cada nacionalidad · ${J.age_year}`;
  cat("chCrAge", J.bands, [
    { label: "Española", data: J.age_structure["española"], color: C.blue },
    { label: "Extranjera", data: J.age_structure["extranjera"], color: C.gold },
  ], { type: "bar", tipDec: 1, tipSuffix: "%", ySuffix: "%" });
  $("ageRateSub").textContent = `Condenados por 1.000 residentes de cada tramo de edad · ${J.last}`;
  cat("chCrAgeRates", J.bands, [
    { label: "Española", data: J.age_rates["española"], color: C.blue, width: 2.6 },
    { label: "Extranjera", data: J.age_rates["extranjera"], color: C.gold, width: 2.6 },
  ], { tipDec: 1, y: { min: 0 } });
  $("typesSub").textContent = `% de delitos en sentencias condenatorias atribuidos a extranjeros · ${J.types_year} · línea = peso en la población adulta`;
  const types = [...J.types].sort((a, b) => b.pct - a.pct);
  hbar("chCrTypes", types.map(t => ({ label: t.name, value: t.pct, total: t.total })), {
    colorFn: v => hexA(C.gold, 0.25 + Math.min(0.65, (v - 10) / 35)), suffix: "%", trunc: 36, x: { min: 0 },
    tip: r => `${nf(r.value, 1)}% de ${nf(r.total, 0)} delitos`,
    lines: [{ axis: "x", value: J.foreign_share_ref, label: `${nf(J.foreign_share_ref, 1)}% población`, color: "rgba(255,255,255,0.7)" }],
  });
  const fshare = Object.fromEntries(J.foreign_share);
  cat("chCrShare", yrs, [
    { label: "% de la población adulta", data: yrs.map(y => fshare[y] ?? null), color: C.blue, width: 2.6 },
    { label: "% de los condenados", data: yrs.map((y, i) => R.total.condenados[i] ? re.condenados[i] / R.total.condenados[i] * 100 : null), color: C.gold, width: 2.6 },
  ], { tipDec: 1, tipSuffix: "%", ySuffix: "%", y: { min: 0 } });
  const MS = J.men_share, ky = Object.keys(MS);
  const mc = { "Española": C.blue, "Extranjera": C.gold, "Total": C.muted };
  cat("chCrMen", MS[ky[0]].map(p => p[0]), ky.map(k => ({ label: k, data: MS[k].map(p => p[1]), color: mc[k] || C.ink, width: k === "Total" ? 1.4 : 2.4, dash: k === "Total" ? [4, 3] : [] })),
    { tipDec: 1, tipSuffix: "%", ySuffix: "%", y: { min: 70, max: 95 } });

  $("crimeVerdict").innerHTML = `<strong>Conclusión del bloque.</strong> Los datos muestran una <strong>sobrerrepresentación real pero mucho menor</strong> de lo que
    sugieren las cifras brutas (${nf(ras, 2)}× ajustado frente a ${nf(rb, 2)}× bruto) y <strong>decreciente</strong> en la última década, pese al fuerte aumento de la
    población extranjera. La diferencia residual no puede atribuirse a la nacionalidad en sí: incluye a no residentes, posibles sesgos de detección y
    enjuiciamiento y diferencias socioeconómicas. Cualquier uso de estas cifras en el debate público debería, como mínimo, <strong>ajustar por edad y explicitar
    que son condenas</strong>, no delitos.`;
}

// ─── TERRITORIO ─────────────────────────────────────────────────────────────
const METRICS = {
  paro: { label: "Tasa de paro (%)", better: "down", dec: 1, suf: "%" },
  paro_delta: { label: "Δ paro desde el inicio de la XV (pp)", better: "down", dec: 2, suf: " pp" },
  empleo: { label: "Tasa de empleo 20-64 (%)", better: "up", dec: 1, suf: "%" },
  arope: { label: "AROPE (%)", better: "down", dec: 1, suf: "%" },
  salario: { label: "Ganancia media anual (€)", better: "up", dec: 0, suf: " €" },
  brecha: { label: "Brecha salarial de género (%)", better: "down", dec: 1, suf: "%" },
  ipc: { label: "IPC interanual (%)", better: "down", dec: 1, suf: "%" },
  ipv: { label: "Precio vivienda, var. anual (%)", better: "down", dec: 1, suf: "%" },
  alquiler: { label: "Alquiler, var. anual (%)", better: "down", dec: 1, suf: "%" },
};
let ccaaChart = null, sortKey = "paro", sortDir = 1;

function renderTerritorio() {
  const rows = D.territorio.rows, es = rows.find(r => r.name === "España");
  const regions = rows.filter(r => r.name !== "España");
  // Color relativo a España: rojo si es peor que la media nacional, verde si es mejor.
  const spread = Object.fromEntries(Object.keys(METRICS).map(k => [k,
    Math.max(...regions.map(r => r[k] == null || es?.[k] == null ? 0 : Math.abs(r[k] - es[k])), 1e-9)]));
  const relColor = (k, v, base, span) => {
    if (v == null || es?.[k] == null) return hexA(C.muted, base);
    const d = v - es[k], worse = METRICS[k].better === "down" ? d > 0 : d < 0;
    return hexA(worse ? C.bad : C.good, base + span * Math.min(1, Math.abs(d) / spread[k]));
  };
  const sel = $("ccaaMetric");
  sel.innerHTML = Object.entries(METRICS).map(([k, m]) => `<option value="${k}">${m.label}</option>`).join("");
  const draw = key => {
    const m = METRICS[key];
    const data = regions.filter(r => r[key] != null).sort((a, b) => b[key] - a[key]);
    $("ccaaTitle").textContent = m.label;
    if (ccaaChart) ccaaChart.destroy();
    ccaaChart = hbar("chCcaa", data.map(r => ({ label: r.name, value: r[key] })), {
      dec: m.dec, axDec: m.dec === 2 ? 1 : 0, suffix: m.suf,
      colorFn: v => relColor(key, v, 0.35, 0.55),
      lines: es && es[key] != null ? [{ axis: "x", value: es[key], label: "España" }] : [],
      x: key === "salario" ? { min: 15000 } : {},
    });
  };
  sel.addEventListener("change", e => draw(e.target.value));
  draw("paro");

  // Tabla ordenable con escala de color por columna.
  const keys = Object.keys(METRICS);
  const cellBg = (k, v) => v == null ? "" : `background:${relColor(k, v, 0.04, 0.32)}`;
  const thead = document.querySelector("#tableCcaa thead"), tbody = document.querySelector("#tableCcaa tbody");
  const renderTable = () => {
    thead.innerHTML = `<tr><th class="sortable ${sortKey === "name" ? "sorted" : ""}" data-k="name">Comunidad</th>${keys.map(k =>
      `<th class="num sortable ${sortKey === k ? "sorted" : ""}" data-k="${k}">${METRICS[k].label.replace(/ \(.*\)/, "")}${sortKey === k ? (sortDir > 0 ? " ↓" : " ↑") : ""}</th>`).join("")}</tr>`;
    const sorted = [...regions].sort((a, b) => sortKey === "name" ? a.name.localeCompare(b.name) * sortDir : ((b[sortKey] ?? -1e9) - (a[sortKey] ?? -1e9)) * sortDir);
    const row = (r, isEs) => `<tr class="${isEs ? "es" : ""}"><td>${r.name}</td>${keys.map(k =>
      `<td class="num" style="${isEs ? "" : cellBg(k, r[k])}">${r[k] == null ? "—" : nf(r[k], METRICS[k].dec)}</td>`).join("")}</tr>`;
    tbody.innerHTML = (es ? row(es, true) : "") + sorted.map(r => row(r, false)).join("");
  };
  thead.addEventListener("click", e => {
    const th = e.target.closest("th"); if (!th) return;
    const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : 1; sortKey = k; renderTable();
  });
  renderTable();

  const pts = regions.filter(r => r.paro != null && r.arope != null && !/Ceuta|Melilla/.test(r.name)).map(r => ({ x: r.paro, y: r.arope, name: r.name }));
  new Chart($("chScatter"), {
    type: "scatter",
    data: { datasets: [{ data: pts, backgroundColor: hexA(C.gold, 0.85), pointRadius: 5, pointHoverRadius: 7 }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, pointLabels: { on: true },
        tooltip: { callbacks: { label: ctx => ` ${ctx.raw.name}: paro ${nf(ctx.raw.x, 1)}% · AROPE ${nf(ctx.raw.y, 1)}%` } } },
      scales: { x: { title: { display: true, text: "Paro (%)" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { title: { display: true, text: "AROPE (%)" }, grid: { color: "rgba(255,255,255,0.05)" } } } },
  });
  const n = pts.length, mx = pts.reduce((a, p) => a + p.x, 0) / n, my = pts.reduce((a, p) => a + p.y, 0) / n;
  const r = pts.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / Math.sqrt(pts.reduce((a, p) => a + (p.x - mx) ** 2, 0) * pts.reduce((a, p) => a + (p.y - my) ** 2, 0));
  $("scatterNote").innerHTML = `Correlación entre comunidades: <strong>r = ${nf(r, 2)}</strong>. El empleo es el principal canal de reducción de la pobreza:
    de ahí la importancia de que la mejora laboral llegue a las regiones del sur.`;
  ts("chSigma", [{ label: "Dispersión del paro (pp)", data: D.territorio.sigma, color: C.good, width: 2.6, fill: "origin" }], { yDec: 0, tipDec: 2, tipSuffix: " pp", y: { min: 0 } });
}

// ─── COMPARATIVA ────────────────────────────────────────────────────────────
function renderComparativa() {
  const M = D.macro, ev = M.events, keys = Object.keys(ev);
  $("eventPills").innerHTML = keys.map((k, i) => `<button class="pill ${i === 0 ? "on" : ""}" data-k="${k}">${ev[k].label.replace(/ \(.*\)/, "")}</button>`).join("");
  const evChart = new Chart($("chEvent"), {
    type: "line", data: { datasets: [] },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "nearest", axis: "x", intersect: false },
      plugins: { legend: { position: "top", align: "start" },
        tooltip: { callbacks: { title: it => `Mes ${it[0].parsed.x} desde la investidura`, label: ctx => ` ${ctx.dataset.label}: ${nf(ctx.parsed.y, 2)}` } } },
      scales: { x: { type: "linear", min: 0, max: 48, ticks: { stepSize: 6 }, grid: { color: "rgba(255,255,255,0.04)" }, title: { display: true, text: "Meses desde la investidura" } },
        y: { grid: { color: "rgba(255,255,255,0.06)" } } } },
  });
  const drawEvent = k => {
    const e = ev[k];
    $("eventTitle").textContent = e.label;
    evChart.data.datasets = [
      { label: "XIV (desde ene 2020)", data: XY(e.XIV), borderColor: LEG_COLORS.XIV, backgroundColor: LEG_COLORS.XIV, borderWidth: 2.4, pointRadius: 2, tension: 0.25 },
      { label: "XV (desde nov 2023)", data: XY(e.XV), borderColor: LEG_COLORS.XV, backgroundColor: LEG_COLORS.XV, borderWidth: 3, pointRadius: 2.5, tension: 0.25 },
    ];
    evChart.options.plugins.refLines = { lines: e.mode === "index" ? [{ value: 100, color: "rgba(255,255,255,0.35)", dash: [2, 3] }] : [] };
    evChart.update();
  };
  $("eventPills").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    document.querySelectorAll("#eventPills .pill").forEach(x => x.classList.toggle("on", x === b));
    drawEvent(b.dataset.k);
  });
  drawEvent(keys[0]);

  const legs = [...new Set(M.phillips.map(p => p.leg))];
  new Chart($("chPhillips"), {
    type: "scatter",
    data: { datasets: legs.map(l => ({
      label: l, data: M.phillips.filter(p => p.leg === l), backgroundColor: hexA(LEG_COLORS[l], l === "XV" ? 1 : 0.75),
      borderColor: hexA(LEG_COLORS[l], 0.5), showLine: l === "XV", borderWidth: 1.2, pointRadius: l === "XV" ? 5 : 4, pointHoverRadius: 7,
    })) },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "top", align: "start" }, tooltip: { callbacks: { label: ctx => ` ${ctx.raw.label} (${ctx.raw.leg}): paro ${nf(ctx.raw.x, 1)}% · subyacente ${nf(ctx.raw.y, 1)}%` } } },
      scales: { x: { title: { display: true, text: "Tasa de paro (%)" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { title: { display: true, text: "Inflación subyacente (%)" }, grid: { color: "rgba(255,255,255,0.05)" } } } },
  });
  ts("chMis", [{ label: "Índice de miseria", data: M.misery, color: C.orange, width: 2.6, fill: "origin" }], { yDec: 0, tipDec: 1, tipSuffix: "%", y: { min: 0 } });
  const ml = M.misery_leg, order = ["Anterior", "XII", "XII-S", "XIV", "XV"].filter(k => ml[k] != null);
  new Chart($("chMisLeg"), {
    type: "bar",
    data: { labels: order.map(k => k === "Anterior" ? "2013-16" : k), datasets: [{ data: order.map(k => ml[k]), backgroundColor: order.map(k => hexA(LEG_COLORS[k], 0.8)), borderRadius: 6 }] },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` Media: ${nf(ctx.parsed.y, 1)}` } } },
      scales: { x: { grid: { display: false } }, y: { min: 0, grid: { color: "rgba(255,255,255,0.06)" }, title: { display: true, text: "Media por legislatura" } } } },
  });
  const lm = last(M.misery), minM = M.misery.reduce((a, b) => b[1] < a[1] ? b : a);
  $("misNote").innerHTML = `La XV tiene el <strong>índice de miseria medio más bajo</strong> de la muestra (${nf(ml.XV, 1)}, frente a ${nf(ml.XIV, 1)} en la XIV).
    Tocó mínimo en ${dlabel(minM[0], "Q")} (${nf(minM[1], 1)}) y el repunte energético lo devuelve a ${nf(lm[1], 1)}.`;

  const R = M.corr, lbl = { paro: "Paro", pib: "PIB", ipc: "IPC", ipc_subyacente: "IPC sub.", ipv: "Vivienda", salario_yoy: "Salarios", ocupados_yoy: "Empleo", tipo_hipoteca: "Tipo hip.", ipi: "IPI" };
  const n2 = R.labels.length;
  let h = `<div class="heat" style="grid-template-columns: 80px repeat(${n2}, minmax(42px, 1fr))"><div class="hh"></div>`;
  h += R.labels.map(l => `<div class="hh">${lbl[l] || l}</div>`).join("");
  R.values.forEach((row, i) => {
    h += `<div class="hl">${lbl[R.labels[i]] || R.labels[i]}</div>`;
    h += row.map(v => `<div style="background:${v >= 0 ? hexA(C.red, Math.abs(v) * 0.8) : hexA(C.blue, Math.abs(v) * 0.8)}">${nf(v, 2)}</div>`).join("");
  });
  $("heatCorr").innerHTML = h + "</div>";
}

// ─── FUENTES ────────────────────────────────────────────────────────────────
function renderFuentes() {
  const m = D.meta;
  $("sourcesLead").innerHTML = `<strong>${m.n_tables} tablas</strong>, <strong>${m.n_indicators} indicadores</strong> y <strong>${nf(m.n_series, 0)} series</strong>
    (${nf(m.n_obs, 0)} observaciones) descargadas de la API del INE. Cada enlace abre la tabla original en ine.es.`;
  const FQ = { M: "Mensual", Q: "Trimestral", S: "Semestral", A: "Anual" };
  document.querySelector("#tableSources tbody").innerHTML = D.sources.map(s => `<tr>
    <td><a href="${s.url}" target="_blank" rel="noopener">${s.table}</a></td><td>${s.source}</td><td>${s.block}</td>
    <td style="color:var(--muted);font-size:0.82rem">${s.indicators.join(" · ")}</td><td class="num">${s.n_series}</td>
    <td style="white-space:nowrap">${FQ[s.freq] || s.freq} · ${s.first} → ${s.last}</td></tr>`).join("");
  $("footMeta").innerHTML = `Generado el ${m.generated} · datos hasta ${dlabel(Date.parse(m.last), "M")} · regenera con <code>python run_all.py</code>.`;
}

// ─── Interacción global ─────────────────────────────────────────────────────
function wireUi() {
  $("rangeSeg").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    document.querySelectorAll("#rangeSeg button").forEach(x => x.classList.toggle("on", x === b));
    rangeMin = RANGES[b.dataset.r];
    TS.forEach(applyRange);
  });
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.04 });
  document.querySelectorAll(".reveal").forEach(el => io.observe(el));
  const links = [...document.querySelectorAll("#navLinks a")];
  const spy = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) links.forEach(a => a.classList.toggle("active", a.getAttribute("href") === `#${e.target.id}`));
  }), { rootMargin: "-45% 0px -50% 0px" });
  document.querySelectorAll("section[id]").forEach(s => spy.observe(s));
}

[renderHero, renderScorecard, renderEmpleo, renderPrecios, renderSalarios, renderGenero, renderCrecimiento,
 renderVivienda, renderBienestar, renderDemografia, renderJusticia, renderTerritorio, renderComparativa, renderFuentes, wireUi]
  .forEach(fn => { try { fn(); } catch (err) { console.error(fn.name, err); } });
