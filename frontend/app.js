// Frontend for the multi-agent analyst.
//
// By default it calls same-origin /api, which vercel.json rewrites to the
// Render service; ?api=http://localhost:8000 points it at a local backend.
// All copy comes from i18n.js; all text is inserted as text nodes, never HTML.

const API = new URLSearchParams(location.search).get("api") || "";

const $ = (id) => document.getElementById(id);
const chat = $("chat");
const form = $("composer");
const input = $("question");
const send = $("send");
const statusEl = $("status");
const tooltip = $("tooltip");

let lang = detectLang();
let t = STRINGS[lang];
let stats = null;

/* ————————————————— theme ————————————————— */

const applyTheme = (v) => {
  if (v) document.documentElement.dataset.theme = v;
  else delete document.documentElement.dataset.theme;
};

applyTheme(localStorage.getItem("theme"));

$("theme").addEventListener("click", () => {
  const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
  const current = document.documentElement.dataset.theme || (prefersDark ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("theme", next);
});

/* ————————————————— language ————————————————— */

function buildLangSwitch() {
  const box = $("lang");
  box.replaceChildren();
  for (const code of Object.keys(STRINGS)) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = code.toUpperCase();
    b.title = STRINGS[code]._name;
    b.className = code === lang ? "active" : "";
    b.setAttribute("aria-pressed", String(code === lang));
    b.addEventListener("click", () => setLang(code));
    box.append(b);
  }
}

function setLang(code) {
  lang = code;
  t = STRINGS[code];
  localStorage.setItem("lang", code);
  document.documentElement.lang = code;
  buildLangSwitch();
  applyStaticCopy();
  chat.replaceChildren();
  highlightPipeline([]);
  if (stats) renderDashboard(stats);
  checkHealth();
}

function applyStaticCopy() {
  $("brand-sub").textContent = t.brandSub;
  $("ask-h").textContent = t.askTitle;
  $("ask-sub").textContent = t.askSub;
  $("kpi-h").textContent = t.kpiTitle;
  $("kpi-sub").textContent = t.kpiSub;
  $("drivers-h").textContent = t.driversTitle;
  $("drivers-sub").textContent = t.driversSub;
  $("source-link").textContent = t.source;
  input.placeholder = t.placeholder;
  send.textContent = t.sendBtn;

  const ex = $("examples");
  ex.replaceChildren();
  for (const q of t.examples) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = q;
    ex.append(b);
  }
}

/* ————————————————— tooltip ————————————————— */

function bindTooltip(el, title, lines) {
  const show = (e) => {
    tooltip.replaceChildren();
    const h = document.createElement("strong");
    h.textContent = title;
    tooltip.append(h, document.createTextNode(lines.join(" · ")));
    tooltip.hidden = false;
    const pad = 12;
    const r = tooltip.getBoundingClientRect();
    tooltip.style.left = `${Math.min(e.clientX + pad, innerWidth - r.width - pad)}px`;
    tooltip.style.top = `${Math.max(e.clientY - r.height - pad, pad)}px`;
  };
  el.addEventListener("mouseenter", show);
  el.addEventListener("mousemove", show);
  el.addEventListener("mouseleave", () => { tooltip.hidden = true; });
}

/* ————————————————— chart primitives ————————————————— */

// Magnitude gets one hue, light→dark by rank: darker always means more.
function seqColor(value, values) {
  const sorted = [...new Set(values)].sort((a, b) => a - b);
  const step = sorted.length < 2 ? 4 : Math.round((sorted.indexOf(value) / (sorted.length - 1)) * 4);
  return `var(--seq-${step + 1})`;
}

function card(title, sub) {
  const el = document.createElement("div");
  el.className = "card";
  const h = document.createElement("h3");
  h.textContent = title;
  const p = document.createElement("p");
  p.className = "card-sub";
  p.textContent = sub;
  el.append(h, p);
  return el;
}

function tableView(columns, rows) {
  const d = document.createElement("details");
  d.className = "table";
  const s = document.createElement("summary");
  s.textContent = t.tableView;
  const table = document.createElement("table");

  const head = table.createTHead().insertRow();
  for (const c of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = c;
    head.append(th);
  }
  const body = table.createTBody();
  for (const r of rows) {
    const tr = body.insertRow();
    r.forEach((cell) => { tr.insertCell().textContent = cell; });
  }
  d.append(s, table);
  return d;
}

/**
 * Horizontal bar chart. Every bar is directly labelled, so identity and value
 * never depend on colour alone; colour only reinforces magnitude.
 */
function barChart({ title, sub, rows, format, tooltipLines, columns }) {
  const el = card(title, sub);
  const values = rows.map((r) => r.value);
  const max = Math.max(...values, 0) || 1;

  const wrap = document.createElement("div");
  wrap.className = "bars";

  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const cat = document.createElement("span");
    cat.className = "cat";
    cat.textContent = r.label;
    cat.title = r.label;

    const track = document.createElement("div");
    track.className = "track";
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.width = `${Math.max((r.value / max) * 100, 1.5)}%`;
    bar.style.background = seqColor(r.value, values);
    const stack = document.createElement("div");
    stack.className = "bar-stack";
    stack.append(bar);

    const val = document.createElement("span");
    val.className = "val";
    val.textContent = format(r.value);

    track.append(stack, val);
    row.append(cat, track);
    bindTooltip(row, r.label, tooltipLines(r));
    wrap.append(row);
  }

  el.append(wrap, tableView(columns,
    rows.map((r) => [r.label, format(r.value), ...(r.customers != null ? [num(r.customers)] : []),
      ...(r.churned != null ? [num(r.churned)] : [])])));
  return el;
}

/** Two-series grouped bars — identity matters here, so it carries a legend. */
function groupedChart({ title, sub, series, rows, format }) {
  const el = card(title, sub);

  const legend = document.createElement("div");
  legend.className = "legend";
  series.forEach((name, i) => {
    const item = document.createElement("span");
    const swatch = document.createElement("i");
    swatch.style.background = `var(--series-${i + 1})`;
    item.append(swatch, document.createTextNode(name));
    legend.append(item);
  });

  const max = Math.max(...rows.flatMap((r) => r.values), 0) || 1;
  const wrap = document.createElement("div");
  wrap.className = "bars";

  for (const r of rows) {
    const row = document.createElement("div");
    row.className = "bar-row";
    const cat = document.createElement("span");
    cat.className = "cat";
    cat.textContent = r.label;
    cat.title = r.label;

    const track = document.createElement("div");
    track.className = "track";
    const stack = document.createElement("div");
    stack.className = "bar-stack";
    r.values.forEach((v, i) => {
      const bar = document.createElement("div");
      bar.className = "bar";
      bar.style.width = `${Math.max((v / max) * 100, 1.5)}%`;
      bar.style.background = `var(--series-${i + 1})`;
      stack.append(bar);
    });

    const val = document.createElement("span");
    val.className = "val";
    val.textContent = r.values.map(format).join(" / ");

    track.append(stack, val);
    row.append(cat, track);
    bindTooltip(row, r.label, r.values.map((v, i) => `${series[i]}: ${format(v)}`));
    wrap.append(row);
  }

  el.append(legend, wrap, tableView([t.colMetric, ...series],
    rows.map((r) => [r.label, ...r.values.map(format)])));
  return el;
}

/* ————————————————— dashboard ————————————————— */

const pct = (v) => `${v.toLocaleString(LOCALES[lang])}%`;
const num = (v) => v.toLocaleString(LOCALES[lang]);
const label = (key) => ({ premium: t.segPremium, retail: t.segRetail }[key] ?? key);

function kpi(labelText, value, unit, note) {
  const el = document.createElement("div");
  el.className = "kpi";
  const l = document.createElement("div");
  l.className = "label";
  l.textContent = labelText;
  const v = document.createElement("div");
  v.className = "value";
  v.textContent = value;
  if (unit) {
    const u = document.createElement("span");
    u.className = "unit";
    u.textContent = unit;
    v.append(u);
  }
  const n = document.createElement("div");
  n.className = "note";
  n.textContent = note;
  el.append(l, v, n);
  return el;
}

function renderDashboard(s) {
  const o = s.overview;
  $("kpis").replaceChildren(
    kpi(t.kpiCustomers, num(o.customers), "", t.kpiCustomersNote),
    kpi(t.kpiChurned, num(o.churned), "", t.kpiChurnedNote),
    kpi(t.kpiRate, num(o.churn_rate), "%", t.kpiRateNote),
    kpi(t.kpiTenure, num(o.avg_tenure_months), t.monthsUnit, t.kpiTenureNote(o.premium_share)),
  );

  const rowsOf = (arr, key, localise = (v) => v) => arr.map((r) => ({
    label: localise(r[key]),
    value: r.churn_rate,
    customers: r.customers,
    churned: r.churned,
  }));

  const rateCols = [t.colGroup, t.colRate, t.colCustomers, t.colChurned];
  const lines = (r) => [t.tipCustomers(num(r.customers)), t.tipChurned(num(r.churned))];

  const charts = [
    barChart({
      title: t.chartFailed,
      sub: t.chartFailedSub,
      rows: rowsOf(s.by_failed_tx, "failed_tx"),
      format: pct,
      tooltipLines: lines,
      columns: rateCols,
    }),
    barChart({
      title: t.chartTenure,
      sub: t.chartTenureSub,
      rows: rowsOf(s.by_tenure, "tenure", (v) => t.tenureBuckets[v] ?? v),
      format: pct,
      tooltipLines: lines,
      columns: rateCols,
    }),
    barChart({
      title: t.chartRegion,
      sub: t.chartRegionSub,
      rows: rowsOf(s.by_region, "region"),
      format: pct,
      tooltipLines: lines,
      columns: rateCols,
    }),
    barChart({
      title: t.chartSegment,
      sub: t.chartSegmentSub,
      rows: [...rowsOf(s.by_segment, "segment", label), ...rowsOf(s.by_platform, "platform")],
      format: pct,
      tooltipLines: lines,
      columns: rateCols,
    }),
    groupedChart({
      title: t.chartEngagement,
      sub: t.chartEngagementSub,
      series: s.engagement.map((e) => (e.status === "churned" ? t.statusChurned : t.statusActive)),
      rows: [
        { label: t.metricLogins, values: s.engagement.map((e) => e.avg_monthly_logins) },
        { label: t.metricP2P, values: s.engagement.map((e) => e.avg_p2p_count) },
        { label: t.metricTickets, values: s.engagement.map((e) => e.avg_support_tickets) },
      ],
      format: num,
    }),
  ];

  if (s.by_quarter.length) {
    charts.push(barChart({
      title: t.chartQuarter,
      sub: t.chartQuarterSub,
      rows: s.by_quarter.map((r) => ({ label: r.quarter, value: r.churned })),
      format: num,
      tooltipLines: (r) => [t.tipChurnedOnly(num(r.value))],
      columns: [t.colGroup, t.colChurned],
    }));
  }

  $("charts").replaceChildren(...charts);
}

async function loadDashboard() {
  const charts = $("charts");
  const skeleton = document.createElement("p");
  skeleton.className = "skeleton";
  skeleton.textContent = t.loading;
  charts.replaceChildren(skeleton);
  try {
    const r = await fetch(`${API}/api/stats`);
    if (!r.ok) throw new Error(`stats ${r.status}`);
    stats = await r.json();
    renderDashboard(stats);
  } catch (err) {
    skeleton.textContent = t.loadFailed(err.message);
    charts.replaceChildren(skeleton);
  }
}

/* ————————————————— chat ————————————————— */

function bubble(role, text, cls) {
  const el = document.createElement("div");
  el.className = `msg ${cls || ""}`;
  const roleLabel = document.createElement("span");
  roleLabel.className = "role";
  roleLabel.textContent = role;
  el.append(roleLabel, document.createTextNode(text));
  chat.append(el);
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return el;
}

function addTrace(el, steps) {
  if (!steps?.length) return;
  const d = document.createElement("details");
  d.className = "trace";
  const s = document.createElement("summary");
  s.textContent = t.traceLabel(steps.length);
  const ol = document.createElement("ol");
  for (const step of steps) {
    const li = document.createElement("li");
    li.textContent = step;
    ol.append(li);
  }
  d.append(s, ol);
  el.append(d);
}

function highlightPipeline(agents) {
  for (const node of document.querySelectorAll(".pipeline .node")) {
    node.classList.toggle("active", agents.includes(node.dataset.agent));
  }
}

async function checkHealth() {
  statusEl.className = "status";
  statusEl.textContent = t.statusChecking;
  try {
    const r = await fetch(`${API}/api/health`);
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json();
    statusEl.className = "status ok";
    statusEl.textContent = j.mock_mode ? t.statusMock : t.statusLive;
  } catch {
    statusEl.className = "status down";
    statusEl.textContent = t.statusDown;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  bubble(t.roleYou, question, "you");
  input.value = "";
  send.disabled = true;
  highlightPipeline(["supervisor"]);
  const pending = bubble(t.roleAnalyst, t.thinking, "thinking");

  try {
    const r = await fetch(`${API}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.detail || `Request failed (${r.status})`);
    pending.remove();
    highlightPipeline(["supervisor", ...(body.plan || []), "critic"]);
    const el = bubble(t.roleAnalyst, body.answer || t.emptyAnswer);
    addTrace(el, body.steps);
  } catch (err) {
    pending.remove();
    highlightPipeline([]);
    bubble(t.roleAnalyst, err.message, "error");
  } finally {
    send.disabled = false;
    input.focus();
  }
});

$("examples").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  input.value = e.target.textContent;
  form.requestSubmit();
});

document.documentElement.lang = lang;
buildLangSwitch();
applyStaticCopy();
checkHealth();
loadDashboard();
