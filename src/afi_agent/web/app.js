"use strict";

// Every piece of user or model text goes through textContent, never innerHTML.

/* ---------- Interface language (French / Arabic) ---------- */

const STRINGS = {
  fr: {
    brand: "Assistant foncier",
    langGroup: "Langue de l'interface",
    brandSub: "Terrains industriels en Tunisie",
    demoChip: "Données de démonstration",
    demoNote: "Les zones, lots et prix affichés sont inventés pour la démonstration ; ce ne sont pas des informations de l'AFI.",
    chatTitle: "Conversation",
    welcomeLead: "Décrivez votre projet comme au guichet : la région, l'activité, la surface, le budget. L'assistant cherche dans les lots de l'AFI et prépare votre demande.",
    welcomeHint: "Essayez une de ces questions :",
    inputLabel: "Votre message",
    inputPlaceholder: "Votre question, dans votre langue…",
    micStart: "Dicter la question",
    micListening: "J'écoute… cliquez pour arrêter",
    micUnavailable: "La dictée n'est pas disponible dans ce navigateur (essayez Chrome ou Edge).",
    micLabel: "Dicter",
    send: "Envoyer",
    micLang: "Langue du micro",
    readAloud: "Lire les réponses",
    voiceNote: "Voix du navigateur, en attendant les modèles vocaux en derja.",
    lotsTitle: "Lots trouvés",
    lotsEmpty: "Les lots que l'assistant trouve s'affichent ici, avec leur surface, leur prix et leur statut.",
    mapTitle: "Zones industrielles",
    mapAria: "Carte des zones industrielles",
    mapOffline: "La carte a besoin d'une connexion internet.",
    requestTitle: "Votre demande",
    requestEmpty: "Aucune demande en cours. Choisissez un lot : l'assistant préparera un brouillon que vous seul pourrez envoyer.",
    lot: "Lot",
    area: "Surface",
    price: "Prix",
    perM2: "Prix / m²",
    sectors: "Secteurs",
    status: { available: "Disponible", reserved: "Réservé", sold: "Vendu" },
    stamp: { reserved: "Réservé", sold: "Vendu" },
    reserveThis: "Réserver",
    reservePrompt: (id) => `Je voudrais réserver le lot ${id}.`,
    lookups: (n) => (n ? `${n} recherche${n > 1 ? "s" : ""}` : "Sans recherche"),
    answeredBy: (model, s) => `Réponse écrite par ${model} en ${s} s.`,
    answeredOffline: "Réponse enregistrée, rejouée en démo hors ligne ; les recherches, elles, sont réelles.",
    noLookup: "Réponse sans recherche dans les données.",
    youTab: "Votre question",
    agentTab: "Assistant",
    thinking: "L'assistant cherche…",
    offlineDemo: "Démo hors ligne",
    serverDown: "Serveur injoignable",
    toolNames: {
      search_lots: "Recherche de lots",
      compare_zones: "Comparaison de zones",
      get_procedure: "Procédure",
      prefill_request: "Brouillon de demande",
      track_dossier: "Suivi de dossier",
      escalate_to_human: "Transfert à un agent",
    },
    blocked: "Refusé par le programme",
    result: {
      search_lots: (o) => `${o.count} lot${o.count > 1 ? "s" : ""} trouvé${o.count > 1 ? "s" : ""}`,
      compare_zones: (o) => `${(o.zones || []).length} zones comparées`,
      get_procedure: (o) => `${(o.steps || []).length} étapes, ${(o.documents || []).length} documents`,
      prefill_request: (o) => `Brouillon ${o.draft_id} préparé, rien n'est envoyé`,
      track_dossier: (o) => `Statut : ${o.status === "received" ? "reçue" : o.status}`,
      escalate_to_human: (o) => `Ticket ${o.ticket_id}`,
    },
    draftHead: "Demande de réservation",
    draftCopy: "Copie carbone",
    fields: { lot: "Lot", applicant: "Demandeur", company: "Société", activity: "Activité", phone: "Téléphone" },
    draftNote: "Vérifiez la copie. L'assistant ne peut pas envoyer la demande : vous seul le pouvez.",
    confirm: "Confirmer et envoyer",
    confirming: "Envoi…",
    confirmError: (m) => `L'envoi a échoué : ${m}. Réessayez.`,
    trackingLabel: "Numéro de suivi",
    trackingNote: "Gardez ce numéro : il permet de suivre votre dossier.",
    replyError: (m) => `Pas de réponse : ${m}. Réessayez dans un instant.`,
    modelFallback: "Modèle de secours",
    modelMain: "Modèle qui répond",
    offline: "hors ligne",
  },
  ar: {
    brand: "المساعد العقاري",
    langGroup: "لغة الواجهة",
    brandSub: "الأراضي الصناعية في تونس",
    demoChip: "بيانات تجريبية",
    demoNote: "المناطق والمقاسم والأسعار المعروضة مُختلَقة لغرض العرض، وليست معطيات الوكالة العقارية الصناعية.",
    chatTitle: "المحادثة",
    welcomeLead: "صِف مشروعك كما تفعل عند الشبّاك: الجهة، النشاط، المساحة، الميزانية. يبحث المساعد في مقاسم الوكالة ويحضّر طلبك.",
    welcomeHint: "جرّب أحد هذه الأسئلة:",
    inputLabel: "رسالتك",
    inputPlaceholder: "سؤالك، بلغتك…",
    micStart: "إملاء السؤال",
    micListening: "أستمع… اضغط للإيقاف",
    micUnavailable: "الإملاء غير متاح في هذا المتصفح (جرّب Chrome أو Edge).",
    micLabel: "إملاء",
    send: "إرسال",
    micLang: "لغة الميكروفون",
    readAloud: "قراءة الأجوبة",
    voiceNote: "صوت المتصفح مؤقتًا، في انتظار نماذج الصوت بالدارجة.",
    lotsTitle: "المقاسم المتاحة",
    lotsEmpty: "تظهر هنا المقاسم التي يجدها المساعد، بمساحتها وسعرها ووضعيتها.",
    mapTitle: "المناطق الصناعية",
    mapAria: "خريطة المناطق الصناعية",
    mapOffline: "تحتاج الخريطة إلى اتصال بالإنترنت.",
    requestTitle: "طلبك",
    requestEmpty: "لا يوجد طلب حاليًا. اختر مقسمًا وسيحضّر المساعد مسودة لا يرسلها أحد غيرك.",
    lot: "المقسم",
    area: "المساحة",
    price: "السعر",
    perM2: "سعر المتر",
    sectors: "القطاعات",
    status: { available: "متاح", reserved: "محجوز", sold: "مَبيع" },
    stamp: { reserved: "محجوز", sold: "مَبيع" },
    reserveThis: "احجز",
    reservePrompt: (id) => `نحب نحجز المقسم ${id}.`,
    lookups: (n) => (n ? `${n} عملية بحث` : "دون بحث"),
    answeredBy: (model, s) => `كتب الجواب ${model} في ${s} ثانية.`,
    answeredOffline: "جواب مسجّل يُعاد في العرض دون اتصال؛ أما عمليات البحث فحقيقية.",
    noLookup: "جواب دون بحث في المعطيات.",
    youTab: "سؤالك",
    agentTab: "المساعد",
    thinking: "المساعد يبحث…",
    offlineDemo: "عرض دون اتصال",
    serverDown: "الخادم غير متاح",
    toolNames: {
      search_lots: "بحث عن مقاسم",
      compare_zones: "مقارنة المناطق",
      get_procedure: "الإجراءات",
      prefill_request: "مسودة الطلب",
      track_dossier: "متابعة الملف",
      escalate_to_human: "تحويل إلى موظف",
    },
    blocked: "رفضه البرنامج",
    result: {
      search_lots: (o) => `وُجد ${o.count} مقسم`,
      compare_zones: (o) => `مقارنة ${(o.zones || []).length} مناطق`,
      get_procedure: (o) => `${(o.steps || []).length} مراحل، ${(o.documents || []).length} وثائق`,
      prefill_request: (o) => `حُضّرت المسودة ${o.draft_id}، ولم يُرسَل شيء`,
      track_dossier: (o) => `الوضعية: ${o.status === "received" ? "وصلت" : o.status}`,
      escalate_to_human: (o) => `تذكرة ${o.ticket_id}`,
    },
    draftHead: "طلب حجز",
    draftCopy: "نسخة كربونية",
    fields: { lot: "المقسم", applicant: "صاحب الطلب", company: "الشركة", activity: "النشاط", phone: "الهاتف" },
    draftNote: "راجع النسخة. لا يستطيع المساعد إرسال الطلب: أنت وحدك تستطيع ذلك.",
    confirm: "تأكيد وإرسال",
    confirming: "جارٍ الإرسال…",
    confirmError: (m) => `تعذّر الإرسال: ${m}. أعد المحاولة.`,
    trackingLabel: "رقم المتابعة",
    trackingNote: "احتفظ بهذا الرقم لمتابعة ملفك.",
    replyError: (m) => `لا يوجد جواب: ${m}. أعد المحاولة بعد لحظة.`,
    modelFallback: "النموذج الاحتياطي",
    modelMain: "النموذج المجيب",
    offline: "دون اتصال",
  },
};

const state = {
  lang: "fr",
  sessionId: null,
  zones: [],
  markers: new Map(),
  map: null,
  busy: false,
  defaultModel: "",
  lastLots: [],
  lastZoneIds: new Set(),
  draft: null,
  dossier: null,
};

const $ = (id) => document.getElementById(id);
const els = {
  messages: $("messages"),
  welcome: $("welcome"),
  form: $("composer"),
  input: $("input"),
  send: $("send"),
  mic: $("mic"),
  speechLang: $("speech-lang"),
  speakReplies: $("speak-replies"),
  modelChip: $("model-chip"),
  modelName: $("model-name"),
  demoChip: $("demo-chip"),
  demoNote: $("demo-note"),
  plans: $("zone-plans"),
  coupons: $("coupons"),
  lotsEmpty: $("lots-empty"),
  lotsCount: $("lots-count"),
  carbon: $("carbon"),
  mapOffline: $("map-offline"),
};

const t = () => STRINGS[state.lang];
const STATUS_COLOR = { available: "#1f7a4a", reserved: "#4b2e83", sold: "#d7262d" };

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

function icon(name, extra = "") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", `icon ${extra}`.trim());
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

const numberFormat = () => new Intl.NumberFormat(state.lang === "ar" ? "ar-TN-u-nu-latn" : "fr-FR");
const money = (n) => `${numberFormat().format(Math.round(n))} DT`;
const area = (n) => `${numberFormat().format(Math.round(n))} m²`;
const zoneCode = (zoneId) => (zoneId.split("-")[1] || zoneId).slice(0, 3);
// "Zone industrielle Kairouan Sud" → "Kairouan Sud": the coupon already says it is a zone.
const shortZoneName = (name) => name.replace(/^zone industrielle\s+/i, "");
const ARABIC = /[؀-ۿ]/;

/* ---------- Language switch ---------- */

function applyLanguage(lang) {
  state.lang = lang;
  const s = STRINGS[lang];
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = s.brand;
  for (const node of document.querySelectorAll("[data-i18n]")) {
    const value = s[node.dataset.i18n];
    if (typeof value === "string") node.textContent = value;
  }
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) node.placeholder = s[node.dataset.i18nPlaceholder];
  for (const node of document.querySelectorAll("[data-i18n-title]")) node.title = s[node.dataset.i18nTitle];
  for (const node of document.querySelectorAll("[data-i18n-aria]")) node.setAttribute("aria-label", s[node.dataset.i18nAria]);
  for (const button of document.querySelectorAll(".lang")) {
    button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
  }
  els.demoChip.title = s.demoNote;
  if (state.lastLots.length || state.lastZoneIds.size) renderLots(state.lastLots, state.lastZoneIds);
  renderCarbon({ settled: true });
  if (state.chipModel !== undefined) setModel(state.chipModel, els.modelChip.classList.contains("fallback"), !state.chipModel);
  relabelLookups();
  try { localStorage.setItem("afi-lang", lang); } catch { /* storage unavailable: keep in memory */ }
}

for (const button of document.querySelectorAll(".lang")) {
  button.addEventListener("click", () => applyLanguage(button.dataset.lang));
}

/* ---------- Server ---------- */

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return body;
}

async function loadStatus() {
  try {
    const status = await api("/status");
    state.defaultModel = status.model;
    setModel(status.model, false);
    if (status.synthetic_data) { els.demoChip.hidden = false; els.demoNote.hidden = false; }
  } catch {
    setModel("", false, true);
  }
}

function setModel(name, isFallback, unreachable = false) {
  state.chipModel = name;
  els.modelName.textContent = unreachable ? t().serverDown : prettyModel(name);
  els.modelChip.classList.toggle("fallback", isFallback);
  els.modelChip.classList.toggle("offline", unreachable || isOffline(name));
  els.modelChip.title = `${isFallback ? t().modelFallback : t().modelMain} : ${name}`;
}

/* ---------- Map ---------- */

async function loadMap() {
  const data = await api("/map");
  state.zones = data.zones;
  if (typeof L === "undefined") { els.mapOffline.hidden = false; return; }
  const map = L.map("map", { zoomControl: false, attributionControl: true, scrollWheelZoom: false });
  L.control.zoom({ position: "bottomright" }).addTo(map);
  state.map = map;
  // OpenStreetMap's own tiles: free for light use such as a demo, with this attribution.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).on("tileerror", () => (els.mapOffline.hidden = false)).addTo(map);

  const bounds = [];
  for (const zone of state.zones) {
    const marker = L.circleMarker([zone.lat, zone.lon], markerStyle(false)).addTo(map);
    marker.bindTooltip(zoneCode(zone.id), {
      permanent: true, direction: "right", offset: [8, 0], className: "zone-label",
    });
    marker.on("click", () => selectZone(zone.id));
    state.markers.set(zone.id, marker);
    bounds.push([zone.lat, zone.lon]);
  }
  map.fitBounds(bounds, { padding: [36, 36], maxZoom: 8 });
}

function markerStyle(active) {
  return {
    radius: active ? 9 : 6,
    color: active ? "#d7262d" : "#0d1b3d",
    weight: 2,
    fillColor: active ? "#d7262d" : "#ffffff",
    fillOpacity: 1,
  };
}

function highlightZones(zoneIds) {
  for (const zone of state.zones) {
    const marker = state.markers.get(zone.id);
    if (!marker) continue;
    const active = zoneIds.has(zone.id);
    marker.setStyle(markerStyle(active));
    const tip = marker.getTooltip();
    if (tip && tip.getElement()) tip.getElement().classList.toggle("active", active);
  }
  if (!state.map || zoneIds.size === 0) return;
  const points = state.zones.filter((z) => zoneIds.has(z.id)).map((z) => [z.lat, z.lon]);
  if (points.length === 1) state.map.flyTo(points[0], 9, { duration: 0.8 });
  else state.map.flyToBounds(points, { padding: [50, 50], maxZoom: 8, duration: 0.8 });
}

function selectZone(zoneId) {
  const first = els.coupons.querySelector(`[data-zone="${CSS.escape(zoneId)}"]`);
  if (first) select(first.dataset.lot);
}

/* ---------- Lots: plans and coupons ---------- */

function renderLots(lots, zoneIds, { deal = false } = {}) {
  state.lastLots = lots;
  state.lastZoneIds = zoneIds;
  const s = t();
  els.lotsEmpty.hidden = lots.length > 0 || zoneIds.size > 0;
  els.lotsCount.textContent = lots.length ? String(lots.length) : "";

  els.plans.replaceChildren();
  const matched = new Set(lots.map((l) => l.id));
  for (const zone of state.zones.filter((z) => zoneIds.has(z.id))) {
    const row = el("div", { class: "plan-row", role: "img", "aria-label": `${zone.name}` });
    for (const lot of zone.lots) {
      const label = `${lot.id}, ${area(lot.area_m2)}, ${s.status[lot.status]}`;
      const plot = el("div", {
        class: `plot ${lot.status}${matched.has(lot.id) ? " match" : ""}`,
        title: label,
        text: lot.id.split("-").pop(),
      });
      plot.style.flexGrow = String(lot.area_m2);
      row.append(plot);
    }
    const title = el("h3", {}, el("b", { text: zoneCode(zone.id), dir: "ltr" }), document.createTextNode(` ${zone.name}`));
    els.plans.append(el("div", { class: "zone-plan" }, title, row));
  }

  els.coupons.replaceChildren(...lots.map((lot, i) => coupon(lot, i, deal)));
  els.coupons.classList.remove("has-selection");
}

function coupon(lot, index, deal) {
  const s = t();
  const zone = state.zones.find((z) => z.id === lot.zone_id) || {};
  const status = lot.status || "available";
  const item = el("li", {
    class: deal ? "coupon deal" : "coupon", // deal in only when results arrive
    "data-lot": lot.id,
    "data-zone": lot.zone_id,
    tabindex: "0",
    "aria-label": `${s.lot} ${lot.id}, ${zone.name || ""}, ${area(lot.area_m2)}, ${money(lot.total_price_tnd)}, ${s.status[status]}`,
  });
  item.style.setProperty("--i", String(index));

  const head = el("div", { class: "coupon-head" },
    el("span", { class: "coupon-serial", text: lot.id, dir: "ltr" }),
    el("span", { class: "coupon-zone", text: shortZoneName(zone.name || lot.zone_name || "") }),
    el("span", { class: `coupon-status ${status}`, text: s.status[status] }),
  );

  const figures = el("div", { class: "coupon-figures" },
    figure(s.area, area(lot.area_m2)),
    figure(s.price, money(lot.total_price_tnd)),
    figure(s.perM2, money(lot.price_tnd_per_m2)),
  );
  const body = el("div", { class: "coupon-body" },
    el("span", { class: "coupon-code", text: zoneCode(lot.zone_id), "aria-hidden": "true" }),
    el("span", { class: "coupon-place", text: zone.governorate || lot.governorate || "" }),
    figures,
  );

  const foot = el("div", { class: "coupon-foot" },
    el("span", { class: "coupon-sectors", text: `${s.sectors} : ${(zone.sectors || lot.sectors || []).join(", ")}` }),
  );
  if (status === "available") {
    const action = el("button", { class: "coupon-action", type: "button", text: s.reserveThis });
    action.addEventListener("click", (event) => {
      event.stopPropagation();
      select(lot.id);
      els.input.value = s.reservePrompt(lot.id);
      autosize();
      els.input.focus();
    });
    foot.append(action);
  }

  item.append(head, body, foot);
  if (status !== "available") item.append(el("span", { class: `coupon-stamp ${status}`, text: s.stamp[status], "aria-hidden": "true" }));
  item.addEventListener("click", () => select(lot.id));
  item.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(lot.id); }
  });
  return item;
}

function figure(label, value) {
  return el("div", { class: "figure" },
    el("span", { class: "figure-label", text: label }),
    el("span", { class: "figure-value", text: value, dir: "ltr" }),
  );
}

function select(lotId) {
  let zoneId = null;
  for (const node of els.coupons.querySelectorAll(".coupon")) {
    const on = node.dataset.lot === lotId;
    node.classList.toggle("selected", on);
    node.setAttribute("aria-current", on ? "true" : "false");
    if (on) zoneId = node.dataset.zone;
  }
  els.coupons.classList.toggle("has-selection", Boolean(zoneId));
  if (zoneId) highlightZones(new Set([zoneId]));
}

/* ---------- The request: a carbon copy ---------- */

function renderCarbon({ settled = false } = {}) {
  const s = t();
  const draft = state.draft;
  els.carbon.replaceChildren();
  if (!draft) {
    els.carbon.dataset.state = "empty";
    els.carbon.append(el("p", { class: "carbon-empty", text: s.requestEmpty }));
    return;
  }
  els.carbon.dataset.state = state.dossier ? "confirmed" : "draft";

  const fields = [
    ["lot", draft.lot_id, true],
    ["applicant", draft.applicant_name],
    ["activity", draft.activity],
    ["company", draft.company_name, true],
    ["phone", draft.phone, true],
  ].filter(([, value]) => value);
  const list = el("dl", { class: "copy-fields" });
  for (const [key, value, ltr] of fields) {
    list.append(el("div", { class: key === "lot" ? "wide" : undefined },
      el("dt", { text: s.fields[key] }),
      el("dd", { text: value, dir: ltr ? "ltr" : "auto" }),
    ));
  }

  const copy = el("div", { class: `copy${state.dossier ? " confirmed" : ""}${settled ? " settled" : ""}` },
    el("div", { class: "copy-head" },
      el("span", { text: s.draftHead }),
      el("span", { class: "serial", text: state.dossier ? state.dossier.tracking_number : draft.id, dir: "ltr" }),
    ),
    list,
    el("div", { class: "perforation", "aria-hidden": "true" }),
  );

  const stub = el("div", { class: "copy-stub" });
  if (state.dossier) {
    stub.append(
      el("div", { class: "tracking" },
        el("span", { class: "label", text: s.trackingLabel }),
        el("span", { class: "number", text: state.dossier.tracking_number, dir: "ltr" }),
      ),
      el("p", { class: "note", text: s.trackingNote }),
    );
    const today = new Date().toLocaleDateString("fr-TN", { day: "2-digit", month: "2-digit", year: "numeric" });
    copy.append(el("div", { class: "stamp", "aria-hidden": "true" },
      el("span", { class: "fr", text: "CONFIRMÉE" }),
      el("span", { class: "ar", text: "مؤكّدة", lang: "ar" }),
      el("span", { class: "date", text: today }),
    ));
  } else {
    const button = el("button", { class: "confirm", type: "button", text: s.confirm });
    const error = el("p", { class: "copy-error", hidden: "", role: "alert" });
    button.addEventListener("click", () => confirmDraft(button, error));
    stub.append(el("p", { class: "note", text: s.draftNote }), button, error);
  }
  copy.append(stub);
  els.carbon.append(copy);
}

async function confirmDraft(button, error) {
  const s = t();
  button.disabled = true;
  button.textContent = s.confirming;
  try {
    state.dossier = await api(`/requests/${encodeURIComponent(state.draft.id)}/confirm`, { method: "POST" });
    renderCarbon();
    await refreshZones();
  } catch (problem) {
    button.disabled = false;
    button.textContent = s.confirm;
    error.hidden = false;
    error.textContent = s.confirmError(problem.message);
  }
}

async function refreshZones() {
  const data = await api("/map");
  state.zones = data.zones;
  const fresh = new Map(state.zones.flatMap((z) => z.lots.map((l) => [l.id, l])));
  const lots = state.lastLots.map((lot) => ({ ...lot, status: (fresh.get(lot.id) || lot).status }));
  renderLots(lots, state.lastZoneIds);
}

/* ---------- Conversation ---------- */

function slipMessage(kind, tabText, ...body) {
  // data-i18n lets the language switch relabel tabs on messages already on screen
  return el("li", { class: `msg msg-${kind}` },
    el("span", { class: "slip-tab", text: tabText, "data-i18n": kind === "user" ? "youTab" : "agentTab" }),
    el("div", { class: "slip" }, ...body),
  );
}

function addUser(text) {
  els.welcome.hidden = true;
  const item = slipMessage("user", t().youTab, el("p", { dir: "auto", text }));
  els.messages.append(item);
  item.scrollIntoView({ behavior: "smooth", block: "end" });
}

function addThinking() {
  const item = slipMessage("agent", t().agentTab,
    el("div", { class: "slip-body" }, el("span", { class: "dot" }), el("span", { class: "dot" }), el("span", { class: "dot" })),
  );
  item.classList.add("thinking");
  item.setAttribute("aria-label", t().thinking);
  els.messages.append(item);
  item.scrollIntoView({ behavior: "smooth", block: "end" });
  return item;
}

function addAgent(response) {
  const text = response.reply;
  // Earlier answers fold their lookups; the newest shows them, so every fact on screen
  // sits next to the lookup it came from.
  for (const toggle of els.messages.querySelectorAll(".lookups-toggle[aria-expanded='true']")) setOpen(toggle, false);
  const body = el("div", { class: "slip-body" }, el("p", { dir: "auto", lang: ARABIC.test(text) ? "ar" : undefined, text }));
  const item = slipMessage("agent", t().agentTab, body, lookups(response));
  agentResponses.set(item, response); // kept so a language switch can relabel the lookups
  els.messages.append(item);
  item.scrollIntoView({ behavior: "smooth", block: "end" });
}

const agentResponses = new WeakMap();

function relabelLookups() {
  for (const item of els.messages.querySelectorAll(".msg-agent")) {
    const response = agentResponses.get(item);
    const old = item.querySelector(".lookups, .lookups-none");
    if (!response || !old) continue;
    const wasOpen = old.querySelector(".lookups-toggle")?.getAttribute("aria-expanded") === "true";
    const fresh = lookups(response);
    old.replaceWith(fresh);
    const toggle = fresh.querySelector(".lookups-toggle");
    if (toggle) setOpen(toggle, wasOpen);
  }
}

function setOpen(toggle, open) {
  toggle.setAttribute("aria-expanded", String(open));
  document.getElementById(toggle.getAttribute("aria-controls")).hidden = !open;
}

function lookups(response) {
  const s = t();
  const calls = response.tool_calls;
  const offline = isOffline(response.model || state.defaultModel);
  if (!calls.length) return el("p", { class: "lookups-none", text: s.noLookup });

  const list = el("ul", { class: "lookups-list" });
  for (const call of calls) {
    const describe = s.result[call.name];
    const result = call.is_error ? s.blocked : describe ? describe(call.output || {}) : "";
    // each lookup is a tabbed row, like the slips and the coupon figures
    list.append(el("li", { class: `lookup${call.is_error ? " blocked" : ""}` },
      el("span", { class: "lookup-tab", text: s.toolNames[call.name] || call.name }),
      el("div", { class: "lookup-row" },
        el("span", { class: "result", text: result }),
        el("code", { text: `${call.name}(${formatArgs(call.input)})` }),
      ),
    ));
  }
  const seconds = (response.latency_ms / 1000).toFixed(1);
  list.append(el("li", { class: "by", text: offline ? s.answeredOffline : s.answeredBy(prettyModel(response.model || state.defaultModel), seconds) }));

  const id = `lk-${Math.random().toString(36).slice(2, 8)}`;
  list.id = id;
  const toggle = el("button", { class: "lookups-toggle", type: "button", "aria-expanded": "true", "aria-controls": id },
    icon("chevron"),
    el("span", { text: s.lookups(calls.length) }),
    offline ? null : el("span", { class: "meta", text: `${seconds} s` }),
  );
  toggle.addEventListener("click", () => setOpen(toggle, toggle.getAttribute("aria-expanded") !== "true"));
  return el("div", { class: "lookups" }, toggle, list);
}

const isOffline = (model) => /offline|replay/i.test(model || "");

// Investor-facing model names; the raw id stays in the chip's tooltip.
function prettyModel(model) {
  if (!model) return "";
  if (isOffline(model)) return t().offlineDemo;
  const known = {
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    "openai/gpt-oss-120b": "Groq gpt-oss-120b",
  };
  return known[model] || model;
}

function formatArgs(input) {
  return Object.entries(input || {})
    .filter(([key, value]) => value !== null && value !== "" && !(key === "limit" && value === 5) && !key.endsWith("_quote"))
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("|") : value}`)
    .join(", ");
}

function applyToolEffects(response) {
  let lots = null;
  const zoneIds = new Set();
  for (const call of response.tool_calls) {
    if (call.is_error) continue;
    const out = call.output || {};
    if (call.name === "search_lots") {
      lots = out.lots || [];
      for (const lot of lots) zoneIds.add(lot.zone_id);
    } else if (call.name === "compare_zones") {
      for (const zone of out.zones || []) zoneIds.add(zone.id);
      lots = lots || (out.zones || []).flatMap((z) => (state.zones.find((x) => x.id === z.id) || { lots: [] }).lots
        .filter((l) => l.status === "available").map((l) => ({ ...l, zone_id: z.id, total_price_tnd: l.area_m2 * l.price_tnd_per_m2 })));
    } else if (call.name === "prefill_request" && out.draft) {
      state.draft = out.draft;
      state.dossier = null;
      renderCarbon();
      els.carbon.querySelector(".copy")?.classList.add("arrive");
      const zone = state.zones.find((z) => z.lots.some((l) => l.id === out.draft.lot_id));
      if (zone) zoneIds.add(zone.id);
    }
  }
  if (lots !== null) renderLots(lots, zoneIds, { deal: true });
  if (zoneIds.size) highlightZones(zoneIds);
  if (state.draft && els.coupons.querySelector(`[data-lot="${CSS.escape(state.draft.lot_id)}"]`)) select(state.draft.lot_id);
}

async function send(text) {
  const message = text.trim();
  if (!message || state.busy) return;
  state.busy = true;
  els.send.disabled = true;
  els.input.value = "";
  autosize();
  addUser(message);
  const thinking = addThinking();
  try {
    const response = await api("/chat", { method: "POST", body: JSON.stringify({ message, session_id: state.sessionId }) });
    state.sessionId = response.session_id;
    thinking.remove();
    addAgent(response);
    if (response.model) setModel(response.model, Boolean(state.defaultModel && response.model !== state.defaultModel && !/offline/.test(state.defaultModel)));
    applyToolEffects(response);
    speak(response.reply);
  } catch (problem) {
    thinking.remove();
    const item = slipMessage("agent", t().agentTab, el("div", { class: "slip-body" }, el("p", { text: t().replyError(problem.message) })));
    item.classList.add("msg-error");
    els.messages.append(item);
  } finally {
    state.busy = false;
    els.send.disabled = false;
    els.input.focus();
  }
}

/* ---------- Voice (browser placeholder) ---------- */

function speak(text) {
  if (!els.speakReplies.checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const lang = ARABIC.test(text) ? "ar" : /\b(le|la|les|des|vous|est|pour|une)\b/i.test(text) ? "fr" : "en";
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.startsWith(lang));
  utterance.lang = voice ? voice.lang : lang;
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function setupSpeechInput() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    els.mic.disabled = true;
    els.mic.title = t().micUnavailable;
    return;
  }
  let recognition = null;
  let finalText = "";
  els.mic.addEventListener("click", () => {
    if (recognition) { recognition.stop(); return; }
    recognition = new Recognition();
    recognition.lang = els.speechLang.value;
    recognition.interimResults = true;
    finalText = "";
    els.mic.setAttribute("aria-pressed", "true");
    els.mic.title = t().micListening;
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece; else interim += piece;
      }
      els.input.value = (finalText + interim).trim();
      autosize();
    };
    recognition.onend = () => {
      els.mic.setAttribute("aria-pressed", "false");
      els.mic.title = t().micStart;
      recognition = null;
      if (finalText.trim()) send(finalText);
    };
    recognition.start();
  });
}

/* ---------- Composer ---------- */

function autosize() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 160)}px`;
}

els.form.addEventListener("submit", (event) => { event.preventDefault(); send(els.input.value); });
els.input.addEventListener("input", autosize);
els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(els.input.value); }
});
for (const example of document.querySelectorAll(".example")) {
  example.addEventListener("click", () => send(example.textContent));
}

let savedLang = "fr";
try { savedLang = localStorage.getItem("afi-lang") || "fr"; } catch { /* storage unavailable */ }
applyLanguage(savedLang === "ar" ? "ar" : "fr");
setupSpeechInput();
loadStatus();
loadMap().catch(() => (els.mapOffline.hidden = false));
