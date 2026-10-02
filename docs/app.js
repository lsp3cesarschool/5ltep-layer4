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
    t_events: "Changes recorded in PROV", t_events_note: "in {n} of the {total} datasets",
    t_critical: "critical", t_critical_tip: "SCHEMA_DRIFT or RETRO_ALTER", t_no_critical: "no critical change",
    t_events_go: "Click to list the datasets that changed", t_go_datasets: "Click to list every dataset",
    t_go_health: "Click to see the monitoring health", t_go_latest: "Click to see the latest changes",
    t_go_cc: "Click to see the cross-check",
    t_last: "Last change", t_none: "none yet",
    t_cc: "Cross-check", t_cc_note: "checked {d}",
    details: "Details",
    d_datasets: "Datasets the portal lists (`package_list`) and that the last cycle read (`package_show`). Resources are the files and links each dataset publishes. The custodian is the CKAN organization that publishes a dataset: every PROV record attributes the dataset to it (`prov:wasAttributedTo`), apart from this toolkit, which only observes.",
    d_cycles: "A cycle reads the whole portal and compares each dataset with the previous reading. The standard is four cycles a day, scheduled every 6 h; more than four in a day means the workflow was also run by hand, fewer that GitHub delayed or skipped one. Since {since}: {n} cycles, {n30} in the last 30 days (about 120 expected); the longest gap in that period was {g} h. A missed cycle delays when a change is seen but loses nothing: the next cycle compares with the last stored reading. Identical readings are stored once: {snaps} distinct snapshots so far.",
    d_events: "Each time a dataset's fingerprint changes, the classifier gives the change a type and the toolkit writes a W3C PROV-DM record: a new version of the dataset, linked to the one before it. The bar shows the share of datasets with at least one change ({n} of {total}, {pct}); the others only have the baseline of their first observation. New datasets are not counted here.",
    d_by_type: "By type:", d_content: "content changed, with a new modification date (warning)",
    d_drift: "resources added, removed, renamed or re-formatted (critical)", d_retro: "changed without a new modification date (critical)",
    d_critical: "A critical change makes the monitoring workflow fail on purpose, after the record is saved, so GitHub e-mails the maintainer.",
    d_see_changed: "List the datasets that changed", d_see_latest: "latest changes", d_see_records: "records in the repository",
    d_last: "When the most recent change recorded in PROV was detected (the cycle that saw it, not a date given by the portal) and in which dataset. New datasets are not counted.",
    d_cc: "Once a day a separate script reads the portal again and compares, for every dataset, two fields its custodian sets (last modification date and number of resources) with the latest snapshot. In sync: everything matches. Pending: differences the next cycle should record (snapshot up to 7 h old). Stale: older differences (monitoring may have stopped). Error: fewer than 90% of the datasets could be read. Stale and error make the workflow fail, which e-mails the maintainer.",
    d_cc_last: "Last result:",
    months_h: "Changes per month",
    months_note: "The classifier described in the paper has four types: CLEAN_UPDATE (no change; not charted), CONTENT_MOD, SCHEMA_DRIFT and RETRO_ALTER; changes of the last two types are critical. Each change of the last three types becomes a W3C PROV-DM record. New datasets (recorded as a baseline on their first observation) and removed datasets are also shown, by date of detection; they are not change types and produce no PROV record.",
    table_view: "Table view", month: "Month", day: "Day", total: "Total",
    days_h: "Changes per day", period: "Period", p_m: "By month, since monitoring began", p_dall: "By day, since monitoring began", p_d14: "By day, last 14 days",
    p_d30: "By day, last 30 days", p_d90: "By day, last 90 days", no_change_period: "No change detected in this period",
    where_h: "Where the files are",
    where_note: "The server each resource URL points to today, and the moves between servers seen since monitoring began. A move, or a switch between a zip and a plain file, usually keeps the format the portal declares: a program that downloads these files can break without warning.",
    hosts_h: "Resource URLs by server, today", moves_h: "Moves and packaging changes",
    m_from: "From", m_to: "To", m_urls: "URLs", m_datasets: "Datasets", m_last: "Last seen", m_none: "No resource has moved to another server yet.",
    zip_to_plain: "zip → plain file", plain_to_zip: "plain file → zip",
    no_url: "[NO URL]", bad_url: "[URL WITHOUT SERVER]",
    h_tip: "{n} resource URL(s) point to {host}. The portal records each address exactly as it was entered, so the same server written in another way (with its port, for example) shows as a separate line.",
    h_tip_port: "Here the port is written in the address ({port}; 80 is HTTP's default and 443 HTTPS's): the same server as {base}.",
    h_tip_none: "{n} resource(s) published with an empty URL field: the portal records the address as entered, and nothing was entered, so there is no file to download.",
    h_tip_bad: "{n} resource(s) whose URL has no server (no http:// or https://): the portal records the address as entered.",
    latest_h: "Latest changes", f_period: "Period: {p}", clear_filter: "Remove this filter",
    click_bar: "Click to see these changes", search_ev: "Search datasets or changes", all_types: "All types",
    c_when: "Detected (UTC)", c_dataset: "Dataset", c_type: "Type", c_what: "What changed", c_prov: "Provenance",
    log: "PROV log", critical: "critical", show_more: "Show all {n}", ev_none: "No change matches.",
    health_h: "Monitoring health",
    health_note: "Monitoring cycles per day over the last 90 days. The standard is four a day, scheduled every 6 h (dashed line). More than four means the workflow was also run by hand (Actions → Run workflow), for example to test a change or refresh the dashboard; fewer means GitHub delayed or skipped a scheduled cycle. A missing cycle delays when a change is seen, never what is recorded: the next cycle compares with the last stored reading.",
    cycles_day: "{n} cycle(s) on {d}", scheduled: "standard: 4 a day",
    cycles_more: "more than the 4 scheduled: at least {k} run by hand", cycles_fewer: "{k} scheduled cycle(s) delayed or skipped by GitHub",
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
    type_RETRO_ALTER: "changed without a new timestamp", type_NEW: "new dataset published", type_REMOVED: "dataset no longer listed",
    type_NOT_FINGERPRINTED: "only fields outside the fingerprint changed (no PROV record)",
    inv_NEW: "New dataset published (baseline)", inv_REMOVED: "Dataset removed", inv_NOT_FINGERPRINTED: "Outside the fingerprint",
  },
  pt: {
    back: "← Voltar ao repositório", eyebrow: "5L-TEP · Camada 4 · Observabilidade e Proveniência", loading: "Carregando…",
    run: "Rodar um ciclo agora ↗", changes_btn: "changes.md ↗", prov_btn: "Registros de proveniência ↗",
    intro: "A cada seis horas, este repositório lê os metadados de todos os conjuntos de dados do portal, compara com a leitura anterior e registra cada mudança como uma entidade W3C PROV-DM derivada da versão anterior. Esta página mostra o que mudou, quando e como; os registros estão no repositório.",
    subtitle: "Monitorado desde {since} · último ciclo {last} · dados da página de {gen}",
    t_datasets: "Conjuntos monitorados", t_datasets_note: "{r} recursos · {o} custodiante(s)",
    t_cycles: "Ciclos de monitoramento", t_cycles_note: "{n} nos últimos 30 dias · maior intervalo {g} h",
    t_events: "Mudanças registradas em PROV", t_events_note: "em {n} dos {total} conjuntos",
    t_critical: "críticas", t_critical_tip: "SCHEMA_DRIFT ou RETRO_ALTER", t_no_critical: "nenhuma mudança crítica",
    t_events_go: "Clique para listar os conjuntos que mudaram", t_go_datasets: "Clique para listar todos os conjuntos",
    t_go_health: "Clique para ver a saúde do monitoramento", t_go_latest: "Clique para ver as últimas mudanças",
    t_go_cc: "Clique para ver a verificação cruzada",
    t_last: "Última mudança", t_none: "nenhuma ainda",
    t_cc: "Verificação cruzada", t_cc_note: "verificada em {d}",
    details: "Detalhes",
    d_datasets: "Conjuntos que o portal lista (`package_list`) e que o último ciclo leu (`package_show`). Recursos são os arquivos e links que cada conjunto publica. Custodiante é a organização do CKAN que publica o conjunto: cada registro PROV atribui o conjunto a ela (`prov:wasAttributedTo`), separada deste kit, que só observa.",
    d_cycles: "Um ciclo lê o portal inteiro e compara cada conjunto com a leitura anterior. O padrão são quatro ciclos por dia, agendados a cada 6 h; mais de quatro num dia significa que o workflow também foi disparado à mão, e menos, que o GitHub atrasou ou pulou um. Desde {since}: {n} ciclos, {n30} nos últimos 30 dias (cerca de 120 esperados); o maior intervalo nesse período foi de {g} h. Um ciclo perdido atrasa quando a mudança é vista, mas não perde nada: o ciclo seguinte compara com a última leitura guardada. Leituras idênticas são guardadas uma vez só: {snaps} snapshots distintos até agora.",
    d_events: "Sempre que a impressão digital de um conjunto muda, o classificador dá um tipo à mudança e o kit grava um registro W3C PROV-DM: uma nova versão do conjunto, ligada à anterior. A barra mostra a parcela de conjuntos com ao menos uma mudança ({n} de {total}, {pct}); os demais só têm a linha de base da primeira observação. Conjuntos novos não entram nesta conta.",
    d_by_type: "Por tipo:", d_content: "conteúdo mudou, com nova data de modificação (aviso)",
    d_drift: "recursos adicionados, removidos, renomeados ou com outro formato (crítica)", d_retro: "mudou sem nova data de modificação (crítica)",
    d_critical: "Uma mudança crítica faz o workflow de monitoramento falhar de propósito, depois de gravar o registro, e o GitHub avisa o mantenedor por e-mail.",
    d_see_changed: "Listar os conjuntos que mudaram", d_see_latest: "últimas mudanças", d_see_records: "registros no repositório",
    d_last: "Quando foi detectada a mudança mais recente registrada em PROV (no ciclo que a viu, não uma data informada pelo portal) e em qual conjunto. Conjuntos novos não entram nesta conta.",
    d_cc: "Uma vez por dia, um script separado lê o portal de novo e compara, para cada conjunto, dois campos que o custodiante define (data da última modificação e número de recursos) com o snapshot mais recente. Sincronizada: tudo bate. Pendente: diferenças que o próximo ciclo deve registrar (snapshot com até 7 h). Desatualizada: diferenças mais antigas (o monitoramento pode ter parado). Erro: menos de 90% dos conjuntos puderam ser lidos. Desatualizada e erro fazem o workflow falhar, e o GitHub avisa o mantenedor por e-mail.",
    d_cc_last: "Último resultado:",
    months_h: "Mudanças por mês",
    months_note: "O classificador descrito no artigo tem quatro tipos: CLEAN_UPDATE (sem mudança; fora do gráfico), CONTENT_MOD, SCHEMA_DRIFT e RETRO_ALTER; as mudanças dos dois últimos tipos são críticas. Cada mudança dos três últimos tipos vira um registro W3C PROV-DM. Conjuntos novos (registrados como linha de base na primeira observação) e conjuntos removidos também aparecem, pela data de detecção; não são tipos de mudança e não geram registro PROV.",
    table_view: "Ver como tabela", month: "Mês", day: "Dia", total: "Total",
    days_h: "Mudanças por dia", period: "Período", p_m: "Por mês, desde o início da coleta", p_dall: "Por dia, desde o início da coleta", p_d14: "Por dia, últimos 14 dias",
    p_d30: "Por dia, últimos 30 dias", p_d90: "Por dia, últimos 90 dias", no_change_period: "Nenhuma mudança detectada neste período",
    where_h: "Onde estão os arquivos",
    where_note: "O servidor para o qual aponta hoje a URL de cada recurso, e as mudanças de servidor vistas desde o início do monitoramento. Uma mudança de servidor, ou a troca entre zip e arquivo simples, costuma manter o formato que o portal declara: um programa que baixa esses arquivos pode quebrar sem aviso.",
    hosts_h: "URLs de recursos por servidor, hoje", moves_h: "Mudanças de servidor e de empacotamento",
    m_from: "De", m_to: "Para", m_urls: "URLs", m_datasets: "Conjuntos", m_last: "Última vez", m_none: "Nenhum recurso mudou de servidor até agora.",
    zip_to_plain: "zip → arquivo simples", plain_to_zip: "arquivo simples → zip",
    no_url: "[SEM URL]", bad_url: "[URL SEM SERVIDOR]",
    h_tip: "{n} URL(s) de recursos apontam para {host}. O portal grava cada endereço exatamente como foi cadastrado, então o mesmo servidor escrito de outro jeito (com a porta, por exemplo) aparece em outra linha.",
    h_tip_port: "Aqui a porta está escrita no endereço ({port}; 80 é a padrão do HTTP e 443 a do HTTPS): é o mesmo servidor de {base}.",
    h_tip_none: "{n} recurso(s) publicado(s) com o campo de URL vazio: o portal grava o endereço como foi cadastrado, e nada foi cadastrado, então não há arquivo para baixar.",
    h_tip_bad: "{n} recurso(s) cuja URL não tem servidor (sem http:// ou https://): o portal grava o endereço como foi cadastrado.",
    latest_h: "Últimas mudanças", f_period: "Período: {p}", clear_filter: "Remover este filtro",
    click_bar: "Clique para ver estas mudanças", search_ev: "Buscar conjuntos ou mudanças", all_types: "Todos os tipos",
    c_when: "Detectada (UTC)", c_dataset: "Conjunto", c_type: "Tipo", c_what: "O que mudou", c_prov: "Proveniência",
    log: "registro PROV", critical: "crítica", show_more: "Mostrar todas as {n}", ev_none: "Nenhuma mudança corresponde.",
    health_h: "Saúde do monitoramento",
    health_note: "Ciclos de monitoramento por dia nos últimos 90 dias. O padrão são quatro por dia, agendados a cada 6 h (linha tracejada). Mais de quatro significa que o workflow também foi disparado à mão (Actions → Run workflow), por exemplo para testar uma mudança ou atualizar o painel; menos significa que o GitHub atrasou ou pulou um ciclo agendado. Um ciclo perdido atrasa quando a mudança é vista, nunca o que é registrado: o ciclo seguinte compara com a última leitura guardada.",
    cycles_day: "{n} ciclo(s) em {d}", scheduled: "padrão: 4 por dia",
    cycles_more: "mais que os 4 agendados: ao menos {k} disparado(s) à mão", cycles_fewer: "{k} ciclo(s) agendado(s) atrasado(s) ou pulado(s) pelo GitHub",
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
    type_RETRO_ALTER: "mudou sem nova data", type_NEW: "novo conjunto publicado", type_REMOVED: "conjunto deixou de ser listado",
    type_NOT_FINGERPRINTED: "só mudaram campos fora da impressão digital (sem registro PROV)",
    inv_NEW: "Novo conjunto publicado (linha de base)", inv_REMOVED: "Conjunto removido", inv_NOT_FINGERPRINTED: "Fora da impressão digital",
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
const pct = (x) => (x == null ? "—" : (x * 100).toLocaleString(LANG === "pt" ? "pt-BR" : "en", { maximumFractionDigits: 0 }) + "%");
const day = (iso) => (iso || "").slice(0, 10);
const stamp = (iso) => (iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : "—");
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");

// Heat by severity, bottom of the stack to top: the hottest at the base, where it is seen first —
// RETRO_ALTER and SCHEMA_DRIFT (critical; the second hatched), CONTENT_MOD (warning), REMOVED (neutral),
// NEW (info). Legend and table follow the same order. NOT_FINGERPRINTED is grey and never charted.
const TYPES = ["RETRO_ALTER", "SCHEMA_DRIFT", "CONTENT_MOD", "REMOVED", "NEW"];
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
  document.querySelectorAll("[data-i18n-aria]").forEach((n) => { n.setAttribute("aria-label", t(n.dataset.i18nAria)); });
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
// `code` in a translated text becomes <code>; everything else is escaped.
const md = (text) => esc(text).replace(/`([^`]+)`/g, "<code>$1</code>");
const plainSentence = (text) => (text || "").replace(/\*\*/g, "").replace(/`/g, "").replace(/^[^\p{L}]+/u, "");

// Each tile is a link to its section (`go`); its Details toggle and its own links keep their behaviour.
function tile(label, value, note = "", meter = null, extra = "", details = "", go = "") {
  const link = go ? ` data-tile-go="${go}" role="link" tabindex="0" title="${esc(t(TILE_GO[go].tip))}"` : "";
  return `<div class="tile${go ? " go" : ""}"${link}><div class="label">${esc(label)}</div><div class="value">${value}</div>`
    + (meter == null ? "" : `<div class="meter"><span style="width:${Math.max(0, Math.min(1, meter)) * 100}%"></span></div>`)
    + `<div class="note">${note}</div>${extra}`
    + (details ? `<details class="tile-more"><summary>${esc(t("details"))}</summary>${details}</details>` : "")
    + "</div>";
}

function scrollToId(id) {
  el(id).scrollIntoView({ behavior: "smooth", block: "start" });
}

// The datasets table, all of them or only the ones that changed.
function showDatasets(onlyChanged) {
  el("only-changed").checked = onlyChanged;
  el("search").value = "";
  renderDatasets();
  scrollToId("datasets-head");
}

const TILE_GO = {
  datasets: { tip: "t_go_datasets", run: () => showDatasets(false) },
  health: { tip: "t_go_health", run: () => scrollToId("health") },
  changed: { tip: "t_events_go", run: () => showDatasets(true) },
  latest: {
    tip: "t_go_latest",
    run: () => {                       // unfiltered, so the first row is the last change
      el("ev-search").value = "";
      el("ev-type").value = "";
      EV_PERIOD = null;
      SHOW_ALL = false;
      renderEvents();
      scrollToId("latest");
    },
  },
  cc: { tip: "t_go_cc", run: () => scrollToId("cross-check-panel") },
};

function bindTileLinks() {
  const tiles = el("tiles");
  tiles.addEventListener("click", (ev) => {
    const own = ev.target.closest("[data-go]");      // a link inside Details that does the same
    if (!own && ev.target.closest("summary, .tile-more, a")) return;
    const node = own ? own.closest(".tile") : ev.target.closest(".tile[data-tile-go]");
    if (!node) return;
    ev.preventDefault();
    TILE_GO[node.dataset.tileGo].run();
  });
  tiles.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.matches(".tile[data-tile-go]")) TILE_GO[ev.target.dataset.tileGo].run();
  });
  window.addEventListener("resize", () => requestAnimationFrame(equalizeTiles));
}

// Collapsed tiles share one height (the tallest collapsed tile); an open tile grows alone. Measured
// with every Details closed, so opening one never changes the others.
function equalizeTiles() {
  const all = [...document.querySelectorAll("#tiles .tile")];
  const open = [...document.querySelectorAll("#tiles details[open]")];
  open.forEach((d) => { d.open = false; });
  all.forEach((x) => { x.style.minHeight = ""; });
  const height = Math.max(...all.map((x) => x.offsetHeight));
  all.forEach((x) => { x.style.minHeight = `${height}px`; });
  open.forEach((d) => { d.open = true; });
}

function renderTiles(d, cc) {
  const s = d.totals, m = d.monitoring, by = s.by_type || {};
  const last = d.events.find((e) => PROV_TYPES.has(e.type)) || null;
  const ccStatus = cc ? cc.status : "WAITING";
  const share = s.datasets ? s.datasets_changed / s.datasets : null;
  const crit = s.critical
    ? `<div class="status bad" title="${esc(t("t_critical_tip"))}">⚠ ${fmt(s.critical)} ${esc(t("t_critical"))}</div>`
    : `<div class="status good" title="${esc(t("t_critical_tip"))}">✓ ${esc(t("t_no_critical"))}</div>`;
  const r = repo();
  const eventsDetails = `<p>${md(t("d_events", { n: fmt(s.datasets_changed), total: fmt(s.datasets), pct: pct(share) }))}</p>`
    + `<p>${esc(t("d_by_type"))}</p><ul>`
    + [["CONTENT_MOD", "d_content"], ["SCHEMA_DRIFT", "d_drift"], ["RETRO_ALTER", "d_retro"]].map(([ty, key]) =>
      `<li>${swatch(ty)}<code>${ty}</code> <strong>${fmt(by[ty] || 0)}</strong>: ${esc(t(key))}</li>`).join("")
    + `</ul><p>${esc(t("d_critical"))}</p>`
    + `<p><a href="#datasets-head" data-go="changed">${esc(t("d_see_changed"))}</a> · <a href="#latest">${esc(t("d_see_latest"))}</a>`
    + ` · <a href="${r}/tree/main/provenance_logs" rel="noopener">${esc(t("d_see_records"))}</a></p>`;
  const lastDetails = `<p>${esc(t("d_last"))}</p>` + (last
    ? `<p>${typeLabel(last.type)}<br>${esc(stamp(last.when))} UTC · ${esc(LANG === "pt" ? last.summary_pt || last.summary : last.summary)}</p>` : "");
  const ccDetails = `<p>${esc(t("d_cc"))}</p>` + (cc && cc.sentence
    ? `<p>${esc(t("d_cc_last"))} ${esc(plainSentence(LANG === "pt" ? cc.sentence_pt : cc.sentence))}</p>` : "");
  el("tiles").innerHTML = [
    tile(t("t_datasets"), fmt(s.datasets), esc(t("t_datasets_note", { r: fmt(s.resources), o: fmt(s.organizations) })),
      null, "", `<p>${md(t("d_datasets"))}</p>`, "datasets"),
    tile(t("t_cycles"), fmt(m.cycles), esc(t("t_cycles_note", { n: fmt(m.cycles_30d), g: fmt(m.max_gap_hours_30d) })),
      null, "", `<p>${md(t("d_cycles", { since: day(m.since), n: fmt(m.cycles), n30: fmt(m.cycles_30d),
        g: fmt(m.max_gap_hours_30d), snaps: fmt(m.distinct_snapshots) }))}</p>`, "health"),
    tile(t("t_events"), fmt(s.prov_events), esc(t("t_events_note", { n: fmt(s.datasets_changed), total: fmt(s.datasets) })),
      share, crit, eventsDetails, "changed"),
    tile(t("t_last"), last ? day(last.when) : esc(t("t_none")), last ? esc(last.title) : "", null, "", lastDetails, "latest"),
    tile(t("t_cc"), `<span class="status ${statusClass(ccStatus)}">${STATUS_ICON[ccStatus] || ""} ${esc(t(`s_${ccStatus}`))}</span>`,
      cc && cc.checked_at ? esc(t("t_cc_note", { d: day(cc.checked_at) })) : "", null, "", ccDetails, "cc"),
  ].join("");
  equalizeTiles();
}

// --- changes per month: stacked bars, one axis, 2px surface gaps -----------------
// Periods of the changes chart: by month since monitoring began, or by day over the last N days.
// A repository monitored for less than 60 days opens by day, so a new instance shows its first changes.
const PERIODS = ["m", "dall", "d14", "d30", "d90"];

function defaultPeriod(d) {
  const asked = new URLSearchParams(location.search).get("period");
  if (PERIODS.includes(asked)) return asked;
  const since = Date.parse(d.monitoring.since || d.generated_at);
  return Date.now() - since < 60 * 86400e3 ? "d30" : "m";
}

function buckets(d, period) {
  const end = (d.monitoring.last_cycle || d.generated_at);
  const since = (d.monitoring.since || d.generated_at);
  if (period === "m") {
    const out = [];
    let [y, mo] = since.slice(0, 7).split("-").map(Number);
    while (`${y}-${String(mo).padStart(2, "0")}` <= end.slice(0, 7)) {
      out.push(`${y}-${String(mo).padStart(2, "0")}`);
      mo += 1;
      if (mo > 12) { mo = 1; y += 1; }
    }
    return { keys: out, keyOf: (iso) => iso.slice(0, 7), short: (k) => k };
  }
  const last = new Date(end.slice(0, 10) + "T00:00:00Z");
  const first = new Date(since.slice(0, 10) + "T00:00:00Z");
  const days = period === "dall" ? Math.round((last - first) / 86400e3) + 1 : Number(period.slice(1));
  const out = [];
  for (let k = days - 1; k >= 0; k--) {
    const x = new Date(last);
    x.setUTCDate(x.getUTCDate() - k);
    const key = x.toISOString().slice(0, 10);
    if (key >= since.slice(0, 10)) out.push(key);
  }
  return { keys: out, keyOf: (iso) => iso.slice(0, 10), short: (k) => k.slice(5) };
}

function niceMax(v) {
  if (v <= 5) return 5;
  const step = Math.pow(10, Math.floor(Math.log10(v)));
  return Math.ceil(v / step) * step;
}

function renderMonths(d) {
  const period = el("period").value;
  const byMonth = period === "m";
  el("months-title").textContent = t(byMonth ? "months_h" : "days_h");
  const { keys: ms, keyOf, short } = buckets(d, period);
  const counts = Object.fromEntries(ms.map((m) => [m, Object.fromEntries(TYPES.map((ty) => [ty, 0]))]));
  for (const e of d.events) {
    const m = keyOf(e.when);
    if (counts[m] && TYPES.includes(e.type)) counts[m][e.type] += 1;
  }
  const present = TYPES.filter((ty) => ms.some((m) => counts[m][ty]));
  el("months-legend").innerHTML = present.map((ty) =>
    `<li>${swatch(ty)}${typeHtml(ty)}${isType(ty) ? ` · ${esc(t(`type_${ty}`))}` : ""}</li>`).join("");

  const totals = ms.map((m) => TYPES.reduce((a, ty) => a + counts[m][ty], 0));
  // Whole numbers on the axis (counts are integers): steps of 1 up to 4, then a nice step.
  const highest = Math.max(1, ...totals);
  const tick = highest <= 4 ? 1 : Math.ceil(niceMax(highest) / 4);
  const max = tick * 4;
  const W = 860, H = 240, L = 34, R = 8, Tp = 10, B = 26;
  const pw = W - L - R, ph = H - Tp - B;
  const bw = Math.max(2, Math.min(56, (pw / ms.length) * 0.6));
  // Selective labels: every axis label and bar total only while they fit; the tooltip always has them.
  const step = Math.ceil(ms.length / 12);
  const fits = ms.length <= 31;
  const x = (i) => L + (pw / ms.length) * (i + 0.5);
  const y = (v) => Tp + ph - (v / max) * ph;
  let svg = "";
  for (let k = 0; k <= 4; k++) {
    const v = tick * k;
    svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/>`
      + `<text class="axis-label" x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  }
  const hits = [];
  ms.forEach((m, i) => {
    let acc = 0;
    const segs = TYPES.filter((ty) => counts[m][ty]);
    // the column's hit area first, so the blocks drawn after it receive their own clicks
    svg += `<rect class="hit${totals[i] ? " has" : ""}" data-i="${i}" data-key="${esc(m)}" x="${x(i) - pw / ms.length / 2}" y="${Tp}"`
      + ` width="${pw / ms.length}" height="${ph}"${totals[i] ? ' tabindex="0" role="link"' : ""}/>`;
    segs.forEach((ty, j) => {
      const v = counts[m][ty];
      const y0 = y(acc), y1 = y(acc + v);
      const top = j === segs.length - 1;
      const h = Math.max(1, y0 - y1 - (top ? 0 : 2));      // 2px surface gap between segments
      const r = top ? 4 : 0;
      const seg = `class="seg" data-i="${i}" data-key="${esc(m)}" data-ty="${ty}" style="fill:${typeColor(ty)}"`;
      svg += top
        ? `<path d="M${x(i) - bw / 2},${y0} V${y1 + r} q0,-${r} ${r},-${r} H${x(i) + bw / 2 - r} q${r},0 ${r},${r} V${y0} Z" ${seg}/>`
        : `<rect x="${x(i) - bw / 2}" y="${y0 - h}" width="${bw}" height="${h}" ${seg}/>`;
      acc += v;
    });
    if (totals[i] && fits) svg += `<text class="label" x="${x(i)}" y="${y(totals[i]) - 4}" text-anchor="middle">${fmt(totals[i])}</text>`;
    const lastFits = i === ms.length - 1 && (step === 1 || i % step >= step * 0.7);   // the last day, unless it would overlap
    if (i % step === 0 || lastFits) {
      svg += `<text class="axis-label" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(short(m))}</text>`;
    }
    hits.push(`<strong>${esc(m)}</strong> · ${esc(t("total"))} ${fmt(totals[i])}<br>`
      // listed top to bottom as the bar is drawn: cool types above, hot ones below
      + segs.slice().reverse().map((ty) => `${swatch(ty)}${esc(typeName(ty))}: ${fmt(counts[m][ty])}`).join("<br>")
      + (totals[i] ? `<br><em>${esc(t("click_bar"))}</em>` : ""));
  });
  if (!totals.some(Boolean)) {
    svg += `<text class="label" x="${L + pw / 2}" y="${Tp + ph / 2}" text-anchor="middle">${esc(t("no_change_period"))}</text>`;
  }
  el("months-chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(el("months-title").textContent)}">${HATCH}${svg}</svg>`;
  el("months-chart").querySelectorAll(".hit, .seg").forEach((n) => bindTip(n, hits[Number(n.dataset.i)]));

  el("months-table").innerHTML = `<thead><tr><th>${esc(t(byMonth ? "month" : "day"))}</th>${present.map((ty) => `<th>${esc(typeName(ty))}</th>`).join("")}`
    + `<th>${esc(t("total"))}</th></tr></thead><tbody>`
    + ms.slice().reverse().map((m) => `<tr><td>${esc(m)}</td>${present.map((ty) => `<td>${fmt(counts[m][ty])}</td>`).join("")}`
      + `<td>${fmt(TYPES.reduce((a, ty) => a + counts[m][ty], 0))}</td></tr>`).join("") + "</tbody>";
}

// --- where the files are -----------------------------------------------------------
function renderWhere(d) {
  const hosts = Object.entries(d.hosts_now || {});
  const max = Math.max(1, ...hosts.map(([, n]) => n));
  const missing = d.urls_without_host || [];
  const hostLabel = (h) => (h === "" ? t("no_url") : h === "?" ? t("bad_url") : h);
  // The tooltip explains each line: as recorded by the portal, a written port, or no server at all.
  const hostTip = (h, n) => {
    if (h === "" || h === "?") {
      const items = missing.filter((x) => x.host === h || (h === "?" && x.host === undefined));
      return esc(t(h === "" ? "h_tip_none" : "h_tip_bad", { n: fmt(n) }))
        + items.map((x) => `<br>· ${esc(x.title)}: ${esc(x.resource)}${x.format ? ` (${esc(x.format)})` : ""}`).join("");
    }
    const port = h.match(/^(.*):(\d+)$/);
    return esc(t("h_tip", { n: fmt(n), host: h }))
      + (port ? `<br>${esc(t("h_tip_port", { port: `:${port[2]}`, base: port[1] }))}` : "");
  };
  el("hosts").innerHTML = hosts.map(([h, n], i) => `<span class="lbl host-row" data-i="${i}" tabindex="0">${esc(hostLabel(h))}</span>`
    + `<span class="bar host-row" data-i="${i}"><span style="width:${(n / max) * 100}%"></span></span>`
    + `<span class="n host-row" data-i="${i}">${fmt(n)}</span>`).join("");
  el("hosts").querySelectorAll(".host-row").forEach((node) => {
    const [h, n] = hosts[Number(node.dataset.i)];
    bindTip(node, hostTip(h, n));
  });
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
let EV_PERIOD = null;          // "2026-08" or "2026-08-14", set by clicking the changes chart

// From the changes chart: Latest changes for one period, and one type when a coloured block was clicked.
function showEvents(period, type) {
  EV_PERIOD = period;
  el("ev-search").value = "";
  el("ev-type").value = [...el("ev-type").options].some((o) => o.value === type) ? type : "";
  SHOW_ALL = false;
  renderEvents();
  tip.hidden = true;
  scrollToId("latest");
}

function bindChartLinks() {
  const chart = el("months-chart");
  chart.addEventListener("click", (ev) => {
    const seg = ev.target.closest(".seg");
    const col = ev.target.closest(".hit.has");
    if (seg) showEvents(seg.dataset.key, seg.dataset.ty);
    else if (col) showEvents(col.dataset.key, "");
  });
  chart.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.matches(".hit.has")) showEvents(ev.target.dataset.key, "");
  });
  el("ev-period-clear").addEventListener("click", () => {
    EV_PERIOD = null;
    renderEvents();
  });
}

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
    && (!EV_PERIOD || e.when.startsWith(EV_PERIOD))
    && (!q || `${e.title} ${e.name} ${e.summary} ${e.summary_pt}`.toLowerCase().includes(q)));
  el("ev-period").hidden = !EV_PERIOD;
  el("ev-period-label").textContent = EV_PERIOD ? t("f_period", { p: EV_PERIOD }) : "";
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
    const partial = i === 0 && key === (d.monitoring.since || "").slice(0, 10) || i === days.length - 1;
    tips.push(esc(t("cycles_day", { n, d: key }))
      + (n > 4 ? `<br>${esc(t("cycles_more", { k: n - 4 }))}` : "")
      + (n < 4 && !partial ? `<br>${esc(t("cycles_fewer", { k: 4 - n }))}` : ""));
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
  bindTileLinks();
  el("period").value = defaultPeriod(DATA);
  el("period").addEventListener("input", () => renderMonths(DATA));
  bindChartLinks();
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
