// 5L-TEP Layer 4 dashboard. Reads data/layer4.json (written by main.py every monitoring cycle) and
// data/cross_check.json (written by cross_check.py once a day). No library, no build step.

const I18N = {
  en: {
    back: "← Back to the repository", eyebrow: "5L-TEP · Layer 4 · Observability & Provenance", loading: "Loading…",
    run: "Run a cycle now ↗", changes_btn: "changes.md ↗", prov_btn: "Provenance logs ↗",
    intro: "Every six hours this repository reads the metadata of every dataset of the portal, compares it with the previous reading, and records each change as a W3C PROV-DM entity derived from the version before it. This page shows what changed, when and how; the records themselves are in the repository.",
    subtitle: "Monitored since {since} · last cycle {last} · page data from {gen}",
    t_datasets: "Datasets monitored", t_datasets_note: "{r} resources · {o} custodian(s)",
    t_cycles: "Monitoring cycles", t_cycles_note: "{n} in the last 30 days · longest gap {g} h",
    t_events: "Changes recorded in PROV", t_events_note: "{n} datasets changed at least once",
    t_critical: "critical", t_critical_tip: "SCHEMA_DRIFT or RETRO_ALTER", t_last: "Last change", t_none: "none yet",
    t_cc: "Cross-check", t_cc_note: "checked {d}",
    months_h: "Changes per month",
    months_note: "The classifier described in the paper has four types: CLEAN_UPDATE (no change; not charted), CONTENT_MOD, SCHEMA_DRIFT and RETRO_ALTER, the last two critical. Each change of the last three types becomes a W3C PROV-DM record. New datasets (recorded as a baseline on their first observation) and removed datasets are also shown, by month of detection; they are not change types and produce no PROV record.",
    table_view: "Table view", month: "Month", total: "Total",
    where_h: "Where the files are",
    where_note: "The server each resource URL points to today, and the moves between servers seen since monitoring began. A move, or a switch between a zip and a plain file, usually keeps the format the portal declares: a program that downloads these files can break without warning.",
    hosts_h: "Resource URLs by server, today", moves_h: "Moves and packaging changes",
    m_from: "From", m_to: "To", m_urls: "URLs", m_datasets: "Datasets", m_last: "Last seen", m_none: "No resource has moved to another server yet.",
    zip_to_plain: "zip → plain file", plain_to_zip: "plain file → zip",
    latest_h: "Latest changes", search_ev: "Search datasets or changes", all_types: "All types",
    c_when: "Detected (UTC)", c_dataset: "Dataset", c_type: "Type", c_what: "What changed", c_prov: "Provenance",
    log: "PROV log", critical: "critical", show_more: "Show all {n}", ev_none: "No change matches.",
    health_h: "Monitoring health",
    health_note: "Monitoring cycles per day over the last 90 days (four are scheduled). A missing cycle delays when a change is seen, never what is recorded: the next cycle compares with the last stored reading.",
    cycles_day: "{n} cycle(s) on {d}", scheduled: "scheduled: 4 a day",
    cc_h: "Independent cross-check", mon_h: "Cycles",
    k_since: "first cycle", k_last: "last cycle", k_cycles: "cycles", k_30d: "cycles in the last 30 days",
    k_gap: "longest gap, last 30 days (h)", k_snaps: "distinct snapshots stored", k_records: "PROV records",
    cc_waiting: "The first cross-check has not run yet.",
    cc_explain: "Once a day, a separate script reads the portal again and compares the fields its custodian sets (last modification, number of resources) with the latest snapshot.",
    s_IN_SYNC: "in sync", s_DEGRADED: "in sync, some datasets not reached", s_PENDING: "pending", s_STALE: "stale",
    s_ERROR: "error", s_WAITING: "waiting",
    datasets_h: "Datasets", search: "Search datasets", only_changed: "only datasets that changed",
    col_dataset: "Dataset", col_org: "Custodian", col_resources: "Resources", col_changes: "Changes",
    col_records: "PROV records", col_last: "Last change", click_note: "Click a dataset to see its changes.",
    no_changes: "No change since monitoring began.",
    footer: "Toolkit {v} · {repo} · Layers 1–3 and 5 of 5L-TEP are separate repositories; this page shows Layer 4 only. Data:",
    type_CONTENT_MOD: "content changed, with a new timestamp", type_SCHEMA_DRIFT: "resources added, removed, renamed or re-formatted",
    type_RETRO_ALTER: "changed without a new timestamp", type_NEW: "dataset published", type_REMOVED: "dataset no longer listed",
    type_NOT_FINGERPRINTED: "only fields outside the fingerprint changed (no PROV record)",
    inv_NEW: "new dataset (baseline)", inv_REMOVED: "removed dataset", inv_NOT_FINGERPRINTED: "outside the fingerprint",
  },
  pt: {
    back: "← Voltar ao repositório", eyebrow: "5L-TEP · Camada 4 · Observabilidade e Proveniência", loading: "Carregando…",
    run: "Rodar um ciclo agora ↗", changes_btn: "changes.md ↗", prov_btn: "Registros de proveniência ↗",
    intro: "A cada seis horas, este repositório lê os metadados de todos os conjuntos de dados do portal, compara com a leitura anterior e registra cada mudança como uma entidade W3C PROV-DM derivada da versão anterior. Esta página mostra o que mudou, quando e como; os registros estão no repositório.",
    subtitle: "Monitorado desde {since} · último ciclo {last} · dados da página de {gen}",
    t_datasets: "Conjuntos monitorados", t_datasets_note: "{r} recursos · {o} custodiante(s)",
    t_cycles: "Ciclos de monitoramento", t_cycles_note: "{n} nos últimos 30 dias · maior intervalo {g} h",
    t_events: "Mudanças registradas em PROV", t_events_note: "{n} conjuntos mudaram ao menos uma vez",
    t_critical: "críticas", t_critical_tip: "SCHEMA_DRIFT ou RETRO_ALTER", t_last: "Última mudança", t_none: "nenhuma ainda",
    t_cc: "Verificação cruzada", t_cc_note: "verificada em {d}",
    months_h: "Mudanças por mês",
    months_note: "O classificador descrito no artigo tem quatro tipos: CLEAN_UPDATE (sem mudança; fora do gráfico), CONTENT_MOD, SCHEMA_DRIFT e RETRO_ALTER, os dois últimos críticos. Cada mudança dos três últimos tipos vira um registro W3C PROV-DM. Conjuntos novos (registrados como linha de base na primeira observação) e conjuntos removidos também aparecem, por mês de detecção; não são tipos de mudança e não geram registro PROV.",
    table_view: "Ver como tabela", month: "Mês", total: "Total",
    where_h: "Onde estão os arquivos",
    where_note: "O servidor para o qual aponta hoje a URL de cada recurso, e as mudanças de servidor vistas desde o início do monitoramento. Uma mudança de servidor, ou a troca entre zip e arquivo simples, costuma manter o formato que o portal declara: um programa que baixa esses arquivos pode quebrar sem aviso.",
    hosts_h: "URLs de recursos por servidor, hoje", moves_h: "Mudanças de servidor e de empacotamento",
    m_from: "De", m_to: "Para", m_urls: "URLs", m_datasets: "Conjuntos", m_last: "Última vez", m_none: "Nenhum recurso mudou de servidor até agora.",
    zip_to_plain: "zip → arquivo simples", plain_to_zip: "arquivo simples → zip",
    latest_h: "Últimas mudanças", search_ev: "Buscar conjuntos ou mudanças", all_types: "Todos os tipos",
    c_when: "Detectada (UTC)", c_dataset: "Conjunto", c_type: "Tipo", c_what: "O que mudou", c_prov: "Proveniência",
    log: "registro PROV", critical: "crítica", show_more: "Mostrar todas as {n}", ev_none: "Nenhuma mudança corresponde.",
    health_h: "Saúde do monitoramento",
    health_note: "Ciclos de monitoramento por dia nos últimos 90 dias (quatro estão agendados). Um ciclo perdido atrasa quando uma mudança é vista, nunca o que é registrado: o ciclo seguinte compara com a última leitura guardada.",
    cycles_day: "{n} ciclo(s) em {d}", scheduled: "agendados: 4 por dia",
    cc_h: "Verificação cruzada independente", mon_h: "Ciclos",
    k_since: "primeiro ciclo", k_last: "último ciclo", k_cycles: "ciclos", k_30d: "ciclos nos últimos 30 dias",
    k_gap: "maior intervalo, últimos 30 dias (h)", k_snaps: "snapshots distintos guardados", k_records: "registros PROV",
    cc_waiting: "A primeira verificação cruzada ainda não rodou.",
    cc_explain: "Uma vez por dia, um script separado lê o portal de novo e compara os campos que o custodiante define (última modificação, número de recursos) com o snapshot mais recente.",
    s_IN_SYNC: "sincronizada", s_DEGRADED: "sincronizada, alguns conjuntos não consultados", s_PENDING: "pendente", s_STALE: "desatualizada",
    s_ERROR: "erro", s_WAITING: "aguardando",
    datasets_h: "Conjuntos de dados", search: "Buscar conjuntos", only_changed: "só conjuntos que mudaram",
    col_dataset: "Conjunto", col_org: "Custodiante", col_resources: "Recursos", col_changes: "Mudanças",
    col_records: "Registros PROV", col_last: "Última mudança", click_note: "Clique num conjunto para ver as mudanças dele.",
    no_changes: "Nenhuma mudança desde o início do monitoramento.",
    footer: "Kit {v} · {repo} · As camadas 1–3 e 5 do 5L-TEP são repositórios separados; esta página mostra só a Camada 4. Dados:",
    type_CONTENT_MOD: "conteúdo mudou, com nova data", type_SCHEMA_DRIFT: "recursos adicionados, removidos, renomeados ou com outro formato",
    type_RETRO_ALTER: "mudou sem nova data", type_NEW: "conjunto publicado", type_REMOVED: "conjunto deixou de ser listado",
    type_NOT_FINGERPRINTED: "só mudaram campos fora da impressão digital (sem registro PROV)",
    inv_NEW: "conjunto novo (linha de base)", inv_REMOVED: "conjunto removido", inv_NOT_FINGERPRINTED: "fora da impressão digital",
  },
};

// Language: ?lang= > the visitor's last choice > the browser's language.
const LANG = (() => {
  const q = new URLSearchParams(location.search).get("lang");
  if (q === "en" || q === "pt") {
    try { localStorage.setItem("l4-lang", q); } catch (e) { /* storage blocked: fine */ }
    return q;
  }
  try {
    const saved = localStorage.getItem("l4-lang");
    if (saved === "en" || saved === "pt") return saved;
  } catch (e) { /* storage blocked: fine */ }
  return (navigator.language || "").toLowerCase().startsWith("pt") ? "pt" : "en";
})();
const T = I18N[LANG];
const t = (key, vars = {}) => String(T[key] ?? I18N.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
const el = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString(LANG === "pt" ? "pt-BR" : "en"));
const day = (iso) => (iso || "").slice(0, 10);
const stamp = (iso) => (iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : "—");
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");

// Heat by severity, bottom of the stack to top: NEW (info), REMOVED (neutral), CONTENT_MOD (warning),
// SCHEMA_DRIFT and RETRO_ALTER (critical; the first hatched). NOT_FINGERPRINTED is grey and never charted.
const TYPES = ["NEW", "REMOVED", "CONTENT_MOD", "SCHEMA_DRIFT", "RETRO_ALTER"];
const PROV_TYPES = new Set(["CONTENT_MOD", "SCHEMA_DRIFT", "RETRO_ALTER"]);
const typeColor = (ty) => (ty === "SCHEMA_DRIFT" ? "url(#hatch-drift)" : `var(--type-${ty})`);
const swatch = (ty) => `<span class="swatch${ty === "SCHEMA_DRIFT" ? " hatch" : ""}" style="background:var(--type-${ty})"></span>`;
// 45° hatch in the critical red, on the chart surface (SVG pattern for SCHEMA_DRIFT bars)
const HATCH = `<defs><pattern id="hatch-drift" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">`
  + `<rect width="5" height="5" style="fill:var(--surface)"/><rect width="3" height="5" style="fill:var(--type-SCHEMA_DRIFT)"/></pattern></defs>`;

function repo() {
  // On GitHub Pages (<owner>.github.io/<repo>/) the repository is github.com/<owner>/<repo>.
  const m = location.hostname.match(/^([^.]+)\.github\.io$/);
  const name = location.pathname.split("/").filter(Boolean)[0];
  return m && name ? `https://github.com/${m[1]}/${name}` : "https://github.com/lsp3cesarschool/5ltep-layer4";
}

function translatePage() {
  document.documentElement.lang = LANG === "pt" ? "pt-BR" : "en";
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => { n.placeholder = t(n.dataset.i18nPlaceholder); });
  for (const lang of ["en", "pt"]) {
    const link = el(`lang-${lang}`);
    const u = new URL(location.href);
    u.searchParams.set("lang", lang);
    link.href = u.search;
    link.classList.toggle("current", lang === LANG);
  }
  const r = repo();
  el("repo-link").href = r;
  el("readme-link").href = `${r}#readme`;
  el("leiame-link").href = `${r}/blob/main/LEIAME.md`;
  el("run-link").href = `${r}/actions/workflows/monitor.yml`;
  el("changes-link").href = `${r}/blob/main/changes.md`;
  el("prov-link").href = `${r}/tree/main/provenance_logs`;
}

// --- tooltip ---------------------------------------------------------------------
const tip = el("tooltip");
function bindTip(node, html) {
  const show = (ev) => {
    tip.innerHTML = html;
    tip.hidden = false;
    const x = Math.min(ev.clientX + 12, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = `${x}px`;
    tip.style.top = `${ev.clientY + 14}px`;
  };
  node.addEventListener("mousemove", show);
  node.addEventListener("mouseleave", () => { tip.hidden = true; });
  node.addEventListener("focus", () => {
    const b = node.getBoundingClientRect();
    show({ clientX: b.left, clientY: b.bottom });
  });
  node.addEventListener("blur", () => { tip.hidden = true; });
}

// The paper's change types are shown as code (CONTENT_MOD...); dataset arrivals and removals, which
// are not change types and have no PROV record, are shown in words.
const isType = (ty) => PROV_TYPES.has(ty);
const typeName = (ty) => (isType(ty) ? ty : t(`inv_${ty}`));
const typeHtml = (ty) => (isType(ty) ? `<code>${esc(ty)}</code>` : esc(t(`inv_${ty}`)));

function typeLabel(ty) {
  const crit = ty === "SCHEMA_DRIFT" || ty === "RETRO_ALTER";
  return `<span class="type" title="${esc(t(`type_${ty}`))}">${swatch(ty)}`
    + `${typeHtml(ty)}</span>${crit ? ` <span class="crit">⚠ ${esc(t("critical"))}</span>` : ""}`;
}

const STATUS_ICON = { IN_SYNC: "✓", DEGRADED: "◐", PENDING: "⏳", STALE: "⚠", ERROR: "✕", WAITING: "…" };
const statusClass = (s) => (s === "IN_SYNC" ? "good" : s === "STALE" || s === "ERROR" ? "bad" : "");

// --- tiles -------------------------------------------------------------------------
function tile(label, value, note = "", meter = null, extra = "") {
  return `<div class="tile"><div class="label">${esc(label)}</div><div class="value">${value}</div>`
    + (meter == null ? "" : `<div class="meter"><span style="width:${Math.max(0, Math.min(1, meter)) * 100}%"></span></div>`)
    + `<div class="note">${note}</div>${extra}</div>`;
}

function renderTiles(d, cc) {
  const s = d.totals, m = d.monitoring;
  const last = d.events.find((e) => e.type !== "NEW") || null;
  const ccStatus = cc ? cc.status : "WAITING";
  const crit = s.critical
    ? `<div class="status bad" title="${esc(t("t_critical_tip"))}">⚠ ${fmt(s.critical)} ${esc(t("t_critical"))}</div>`
    : `<div class="status good" title="${esc(t("t_critical_tip"))}">✓ 0 ${esc(t("t_critical"))}</div>`;
  el("tiles").innerHTML = [
    tile(t("t_datasets"), fmt(s.datasets), esc(t("t_datasets_note", { r: fmt(s.resources), o: fmt(s.organizations) }))),
    tile(t("t_cycles"), fmt(m.cycles), esc(t("t_cycles_note", { n: fmt(m.cycles_30d), g: fmt(m.max_gap_hours_30d) }))),
    tile(t("t_events"), fmt(s.prov_events), esc(t("t_events_note", { n: fmt(s.datasets_changed) })),
      s.datasets ? s.datasets_changed / s.datasets : null, crit),
    tile(t("t_last"), last ? day(last.when) : esc(t("t_none")), last ? esc(last.title) : ""),
    tile(t("t_cc"), `<span class="status ${statusClass(ccStatus)}">${STATUS_ICON[ccStatus] || ""} ${esc(t(`s_${ccStatus}`))}</span>`,
      cc && cc.checked_at ? esc(t("t_cc_note", { d: day(cc.checked_at) })) : ""),
  ].join("");
}

// --- changes per month: stacked bars, one axis, 2px surface gaps -----------------
function months(d) {
  const first = (d.monitoring.since || d.generated_at).slice(0, 7);
  const last = (d.monitoring.last_cycle || d.generated_at).slice(0, 7);
  const out = [];
  let [y, mo] = first.split("-").map(Number);
  while (`${y}-${String(mo).padStart(2, "0")}` <= last) {
    out.push(`${y}-${String(mo).padStart(2, "0")}`);
    mo += 1;
    if (mo > 12) { mo = 1; y += 1; }
  }
  return out;
}

function niceMax(v) {
  if (v <= 5) return 5;
  const step = Math.pow(10, Math.floor(Math.log10(v)));
  return Math.ceil(v / step) * step;
}

function renderMonths(d) {
  const ms = months(d);
  const counts = Object.fromEntries(ms.map((m) => [m, Object.fromEntries(TYPES.map((ty) => [ty, 0]))]));
  for (const e of d.events) {
    const m = e.when.slice(0, 7);
    if (counts[m] && TYPES.includes(e.type)) counts[m][e.type] += 1;
  }
  const present = TYPES.filter((ty) => ms.some((m) => counts[m][ty]));
  el("months-legend").innerHTML = present.map((ty) =>
    `<li>${swatch(ty)}${typeHtml(ty)}${isType(ty) ? ` · ${esc(t(`type_${ty}`))}` : ""}</li>`).join("");

  const totals = ms.map((m) => TYPES.reduce((a, ty) => a + counts[m][ty], 0));
  const max = niceMax(Math.max(1, ...totals));
  const W = 860, H = 240, L = 34, R = 8, Tp = 10, B = 26;
  const pw = W - L - R, ph = H - Tp - B;
  const bw = Math.min(56, (pw / ms.length) * 0.6);
  const x = (i) => L + (pw / ms.length) * (i + 0.5);
  const y = (v) => Tp + ph - (v / max) * ph;
  let svg = "";
  for (let k = 0; k <= 4; k++) {
    const v = (max / 4) * k;
    svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/>`
      + `<text class="axis-label" x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  }
  const hits = [];
  ms.forEach((m, i) => {
    let acc = 0;
    const segs = TYPES.filter((ty) => counts[m][ty]);
    segs.forEach((ty, j) => {
      const v = counts[m][ty];
      const y0 = y(acc), y1 = y(acc + v);
      const top = j === segs.length - 1;
      const h = Math.max(1, y0 - y1 - (top ? 0 : 2));      // 2px surface gap between segments
      const r = top ? 4 : 0;
      svg += top
        ? `<path d="M${x(i) - bw / 2},${y0} V${y1 + r} q0,-${r} ${r},-${r} H${x(i) + bw / 2 - r} q${r},0 ${r},${r} V${y0} Z" style="fill:${typeColor(ty)}"/>`
        : `<rect x="${x(i) - bw / 2}" y="${y0 - h}" width="${bw}" height="${h}" style="fill:${typeColor(ty)}"/>`;
      acc += v;
    });
    if (totals[i]) svg += `<text class="label" x="${x(i)}" y="${y(totals[i]) - 4}" text-anchor="middle">${fmt(totals[i])}</text>`;
    svg += `<text class="axis-label" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(m)}</text>`;
    svg += `<rect class="hit" data-i="${i}" x="${x(i) - pw / ms.length / 2}" y="${Tp}" width="${pw / ms.length}" height="${ph}" tabindex="0"/>`;
    hits.push(`<strong>${esc(m)}</strong> · ${esc(t("total"))} ${fmt(totals[i])}<br>`
      + segs.map((ty) => `${swatch(ty)}${esc(typeName(ty))}: ${fmt(counts[m][ty])}`).join("<br>"));
  });
  el("months-chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t("months_h"))}">${HATCH}${svg}</svg>`;
  el("months-chart").querySelectorAll("rect.hit").forEach((n) => bindTip(n, hits[Number(n.dataset.i)]));

  el("months-table").innerHTML = `<thead><tr><th>${esc(t("month"))}</th>${present.map((ty) => `<th>${esc(typeName(ty))}</th>`).join("")}`
    + `<th>${esc(t("total"))}</th></tr></thead><tbody>`
    + ms.slice().reverse().map((m) => `<tr><td>${esc(m)}</td>${present.map((ty) => `<td>${fmt(counts[m][ty])}</td>`).join("")}`
      + `<td>${fmt(TYPES.reduce((a, ty) => a + counts[m][ty], 0))}</td></tr>`).join("") + "</tbody>";
}

// --- where the files are -----------------------------------------------------------
function renderWhere(d) {
  const hosts = Object.entries(d.hosts_now || {});
  const max = Math.max(1, ...hosts.map(([, n]) => n));
  el("hosts").innerHTML = hosts.map(([h, n]) => `<span class="lbl">${esc(h)}</span>`
    + `<span class="bar"><span style="width:${(n / max) * 100}%"></span></span><span class="n">${fmt(n)}</span>`).join("");
  const moves = d.relocations || [];
  el("moves").innerHTML = moves.length
    ? `<thead><tr><th>${esc(t("m_from"))}</th><th>${esc(t("m_to"))}</th><th class="num">${esc(t("m_urls"))}</th>`
      + `<th class="num">${esc(t("m_datasets"))}</th><th>${esc(t("m_last"))}</th></tr></thead><tbody>`
      + moves.map((m) => `<tr><td>${esc(m.from || "?")}</td><td>${esc(m.to || "?")}</td><td class="num">${fmt(m.urls)}</td>`
        + `<td class="num">${fmt(m.datasets)}</td><td class="when">${esc(day(m.last))}</td></tr>`).join("") + "</tbody>"
    : `<tbody><tr><td class="muted">${esc(t("m_none"))}</td></tr></tbody>`;
  const p = d.packaging || {};
  el("packaging").innerHTML = `<span>${esc(t("zip_to_plain"))}</span><span class="v">${fmt(p.zip_to_plain)}</span>`
    + `<span>${esc(t("plain_to_zip"))}</span><span class="v">${fmt(p.plain_to_zip)}</span>`;
}

// --- latest changes ----------------------------------------------------------------
const PAGE = 50;
let SHOW_ALL = false;

function eventRow(e, portal, withDataset = true) {
  const summary = LANG === "pt" ? e.summary_pt || e.summary : e.summary;
  const prov = e.prov_log ? `<a href="${repo()}/blob/main/provenance_logs/${encodeURIComponent(e.prov_log)}" rel="noopener">${esc(t("log"))}</a>` : "";
  const ds = withDataset
    ? `<td><a href="${esc(safeUrl(`${portal}/dataset/${encodeURIComponent(e.name)}`))}" rel="noopener">${esc(e.title)}</a></td>` : "";
  return `<tr><td class="when">${esc(stamp(e.when))}</td>${ds}<td>${typeLabel(e.type)}</td><td>${esc(summary)}</td><td>${prov}</td></tr>`;
}

function renderEvents() {
  const q = el("ev-search").value.trim().toLowerCase();
  const ty = el("ev-type").value;
  const rows = DATA.events.filter((e) => (!ty || e.type === ty)
    && (!q || `${e.title} ${e.name} ${e.summary} ${e.summary_pt}`.toLowerCase().includes(q)));
  const shown = SHOW_ALL ? rows : rows.slice(0, PAGE);
  el("events").innerHTML = `<thead><tr><th>${esc(t("c_when"))}</th><th>${esc(t("c_dataset"))}</th><th>${esc(t("c_type"))}</th>`
    + `<th>${esc(t("c_what"))}</th><th>${esc(t("c_prov"))}</th></tr></thead><tbody>`
    + (shown.length ? shown.map((e) => eventRow(e, DATA.portal.portal_url)).join("")
      : `<tr><td colspan="5" class="muted">${esc(t("ev_none"))}</td></tr>`) + "</tbody>";
  const more = el("ev-more");
  more.hidden = SHOW_ALL || rows.length <= PAGE;
  more.textContent = t("show_more", { n: fmt(rows.length) });
}

// --- monitoring health ---------------------------------------------------------------
function renderCycles(d) {
  const byDay = d.monitoring.cycles_by_day || {};
  const end = new Date((d.monitoring.last_cycle || d.generated_at).slice(0, 10) + "T00:00:00Z");
  const days = [];
  for (let k = 89; k >= 0; k--) {
    const x = new Date(end);
    x.setUTCDate(x.getUTCDate() - k);
    const key = x.toISOString().slice(0, 10);
    if (!d.monitoring.since || key >= d.monitoring.since.slice(0, 10)) days.push([key, byDay[key] || 0]);
  }
  const max = Math.max(4, ...days.map(([, n]) => n));
  const W = 860, H = 160, L = 34, R = 8, Tp = 20, B = 24;
  const pw = W - L - R, ph = H - Tp - B, slot = pw / Math.max(days.length, 1);
  const bw = Math.max(2, slot - 2);                        // 2px surface gap between bars
  const y = (v) => Tp + ph - (v / max) * ph;
  let svg = "";
  for (const v of [0, 2, 4].filter((v) => v <= max)) {
    svg += `<line class="${v === 4 ? "ref" : "grid"}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/>`
      + `<text class="axis-label" x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  }
  svg += `<text class="label" x="${W - R}" y="${y(4) - 4}" text-anchor="end">${esc(t("scheduled"))}</text>`;
  const tips = [];
  days.forEach(([key, n], i) => {
    const x0 = L + i * slot;
    if (n) {
      const top = y(n), r = Math.min(2, bw / 2);
      svg += `<path d="M${x0},${y(0)} V${top + r} q0,-${r} ${r},-${r} H${x0 + bw - r} q${r},0 ${r},${r} V${y(0)} Z" fill="var(--bar)"/>`;
    }
    if (i % 15 === 0) svg += `<text class="axis-label" x="${x0}" y="${H - 6}">${esc(key.slice(5))}</text>`;
    svg += `<rect class="hit" data-i="${i}" x="${x0 - 1}" y="${Tp}" width="${slot}" height="${ph}"/>`;
    tips.push(esc(t("cycles_day", { n, d: key })));
  });
  el("cycles-chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t("health_h"))}">${svg}</svg>`;
  el("cycles-chart").querySelectorAll("rect.hit").forEach((n) => bindTip(n, tips[Number(n.dataset.i)]));

  const m = d.monitoring;
  el("monitoring").innerHTML = [
    [t("k_since"), stamp(m.since)], [t("k_last"), stamp(m.last_cycle)], [t("k_cycles"), fmt(m.cycles)],
    [t("k_30d"), fmt(m.cycles_30d)], [t("k_gap"), fmt(m.max_gap_hours_30d)],
    [t("k_snaps"), fmt(m.distinct_snapshots)], [t("k_records"), fmt(d.totals.prov_records)],
  ].map(([k, v]) => `<span>${esc(k)}</span><span class="v">${esc(v)}</span>`).join("");
}

function renderCrossCheck(cc) {
  if (!cc || cc.status === "WAITING") {
    el("cross-check").innerHTML = `<p class="muted">${esc(t("cc_waiting"))}</p><p class="small muted">${esc(t("cc_explain"))}</p>`;
    return;
  }
  const sentence = (LANG === "pt" ? cc.sentence_pt : cc.sentence) || "";
  const plain = sentence.replace(/\*\*/g, "").replace(/`/g, "").replace(/^[^\p{L}]+/u, "");
  el("cross-check").innerHTML = `<div class="status ${statusClass(cc.status)}">${STATUS_ICON[cc.status] || ""} ${esc(t(`s_${cc.status}`))}</div>`
    + `<p class="cc-sentence">${esc(plain)}</p><p class="small muted">${esc(t("cc_explain"))} `
    + `<a href="${repo()}/blob/main/data/cross_check_report.json">data/cross_check_report.json</a></p>`;
}

// --- datasets ------------------------------------------------------------------------
let DATA = null;
const OPEN = new Set();

function renderDatasets() {
  const q = el("search").value.trim().toLowerCase();
  const onlyChanged = el("only-changed").checked;
  const portal = DATA.portal.portal_url;
  const byDataset = {};
  for (const e of DATA.events) (byDataset[e.dataset_id] = byDataset[e.dataset_id] || []).push(e);
  const rows = [];
  for (const ds of DATA.datasets) {
    if (onlyChanged && !ds.changes) continue;
    if (q && !`${ds.title} ${ds.name} ${ds.organization || ""}`.toLowerCase().includes(q)) continue;
    const records = ds.prov_log
      ? `<a href="${repo()}/blob/main/provenance_logs/${encodeURIComponent(ds.prov_log)}" rel="noopener">${fmt(ds.prov_records)}</a>` : "0";
    rows.push(`<tr class="ds" data-id="${esc(ds.id)}" tabindex="0"><td><strong>${esc(ds.title)}</strong><br>`
      + `<a class="small" href="${esc(safeUrl(`${portal}/dataset/${encodeURIComponent(ds.name)}`))}" rel="noopener">${esc(ds.name)}</a></td>`
      + `<td class="small">${esc(ds.organization || "—")}</td><td class="num">${fmt(ds.resources)}</td>`
      + `<td class="num">${fmt(ds.changes)}</td><td class="num">${records}</td>`
      + `<td>${ds.last_change ? `<span class="when">${esc(day(ds.last_change))}</span><br>${typeLabel(ds.last_type)}` : "—"}</td></tr>`);
    if (OPEN.has(ds.id)) {
      const evs = byDataset[ds.id] || [];
      rows.push(`<tr class="detail"><td colspan="6">` + (evs.length
        ? `<div class="table-wrap"><table class="files"><tbody>${evs.map((e) => eventRow(e, portal, false)).join("")}</tbody></table></div>`
        : `<span class="muted">${esc(t("no_changes"))}</span>`) + "</td></tr>");
    }
  }
  const body = document.querySelector("#datasets tbody");
  body.innerHTML = rows.join("");
  body.querySelectorAll("tr.ds").forEach((tr) => {
    const toggle = () => {
      const id = tr.dataset.id;
      OPEN.has(id) ? OPEN.delete(id) : OPEN.add(id);
      renderDatasets();
    };
    tr.addEventListener("click", (ev) => { if (ev.target.tagName !== "A") toggle(); });
    tr.addEventListener("keydown", (ev) => { if (ev.key === "Enter") toggle(); });
  });
}

async function main() {
  translatePage();
  try {
    DATA = await (await fetch("data/layer4.json", { cache: "no-cache" })).json();
  } catch (e) {
    el("title").textContent = LANG === "pt" ? "Ainda sem dados: o primeiro ciclo não terminou."
      : "No data yet: the first monitoring cycle has not finished.";
    return;
  }
  let cc = null;
  try { cc = await (await fetch("data/cross_check.json", { cache: "no-cache" })).json(); } catch (e) { /* not run yet */ }

  el("title").textContent = DATA.portal.title || DATA.portal.name;
  el("subtitle").textContent = t("subtitle", { since: day(DATA.monitoring.since), last: stamp(DATA.monitoring.last_cycle),
    gen: stamp(DATA.generated_at) });
  renderTiles(DATA, cc);
  renderMonths(DATA);
  renderWhere(DATA);
  const types = [...new Set(DATA.events.map((e) => e.type))];
  el("ev-type").insertAdjacentHTML("beforeend", types.map((ty) => `<option value="${esc(ty)}">${esc(typeName(ty))}</option>`).join(""));
  renderEvents();
  ["ev-search", "ev-type"].forEach((id) => el(id).addEventListener("input", () => { SHOW_ALL = false; renderEvents(); }));
  el("ev-more").addEventListener("click", () => { SHOW_ALL = true; renderEvents(); });
  renderCycles(DATA);
  renderCrossCheck(cc);
  // ?dataset=<id or name> opens that dataset (links from the README or changes.md)
  const wanted = new URLSearchParams(location.search).get("dataset");
  const target = wanted && DATA.datasets.find((d) => d.id === wanted || d.name === wanted);
  if (target) OPEN.add(target.id);
  renderDatasets();
  ["search", "only-changed"].forEach((id) => el(id).addEventListener("input", renderDatasets));
  if (target) document.querySelector(`tr.ds[data-id="${CSS.escape(target.id)}"]`)?.scrollIntoView({ block: "center" });
  el("footer").innerHTML = esc(t("footer", { v: DATA.toolkit_version || "?", repo: DATA.repository || "" }))
    + ` <a href="data/layer4.json">layer4.json</a> · <a href="data/cross_check.json">cross_check.json</a>`;
}

main();
