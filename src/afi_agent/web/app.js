"use strict";

// Every piece of user or model text goes through textContent, never innerHTML.

const state = {
  sessionId: null,
  zones: [],
  markers: new Map(),
  map: null,
  busy: false,
  defaultModel: "",
};

const $ = (id) => document.getElementById(id);
const els = {
  messages: $("messages"),
  empty: $("empty"),
  form: $("composer"),
  input: $("input"),
  send: $("send"),
  mic: $("mic"),
  speechLang: $("speech-lang"),
  speakReplies: $("speak-replies"),
  badge: $("model-badge"),
  banner: $("data-banner"),
  plotZones: $("plot-zones"),
  plotsHint: $("plots-hint"),
  traceSteps: $("trace-steps"),
  traceEmpty: $("trace-empty"),
  mapOffline: $("map-offline"),
};

const STATUS_LABEL = { available: "Disponible", reserved: "Réservé", sold: "Vendu" };
const DOSSIER_STATUS = { received: "reçue" };
const STATUS_COLOR = { available: "#4f7f2a", reserved: "#b9832a", sold: "#9c3f2b" };

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

const money = (n) => `${Math.round(n).toLocaleString("fr-FR")} DT`;
const area = (n) => `${Math.round(n).toLocaleString("fr-FR")} m²`;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : response.statusText;
    throw new Error(detail || `Erreur ${response.status}`);
  }
  return body;
}

/* ---------- Status and map ---------- */

async function loadStatus() {
  try {
    const status = await api("/status");
    state.defaultModel = status.model;
    setBadge(status.model, false);
    if (status.synthetic_data) els.banner.hidden = false;
  } catch {
    setBadge("serveur indisponible", true);
  }
}

function setBadge(model, isFallback) {
  els.badge.textContent = model;
  els.badge.classList.toggle("fallback", isFallback);
  els.badge.title = isFallback ? "Modèle de secours" : "Modèle qui répond";
}

async function loadMap() {
  const data = await api("/map");
  state.zones = data.zones;
  if (typeof L === "undefined") {
    els.mapOffline.hidden = false;
    return;
  }
  const map = L.map("map", { zoomControl: true, attributionControl: true });
  state.map = map;
  // OpenStreetMap's own tiles: free for light use such as a demo, with this attribution.
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  })
    .on("tileerror", () => (els.mapOffline.hidden = false))
    .addTo(map);

  const bounds = [];
  for (const zone of state.zones) {
    const marker = L.circleMarker([zone.lat, zone.lon], zoneStyle(zone, false)).addTo(map);
    marker.bindTooltip(zone.governorate, {
      permanent: true, direction: "right", offset: [12, 0], className: "zone-label",
    });
    marker.bindPopup(() => zonePopup(zone));
    state.markers.set(zone.id, marker);
    bounds.push([zone.lat, zone.lon]);
  }
  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
}

function zoneStyle(zone, highlighted) {
  return {
    radius: highlighted ? 16 : 7 + zone.available * 2,
    color: highlighted ? "#17212b" : "#1f3a5f",
    weight: highlighted ? 3 : 1.5,
    fillColor: zone.available ? STATUS_COLOR.available : STATUS_COLOR.sold,
    fillOpacity: highlighted ? 0.9 : 0.55,
  };
}

function zonePopup(zone) {
  const box = el("div", {},
    el("strong", { text: zone.name }),
    el("div", { text: `${zone.governorate}, ${zone.area_ha} ha` }),
    el("div", { text: `Secteurs : ${zone.sectors.join(", ")}` }),
    el("div", { text: `${zone.available} lot(s) disponible(s)` }),
  );
  return box;
}

function highlightZones(zoneIds) {
  for (const zone of state.zones) {
    const marker = state.markers.get(zone.id);
    if (marker) marker.setStyle(zoneStyle(zone, zoneIds.has(zone.id)));
  }
  if (!state.map || zoneIds.size === 0) return;
  const points = state.zones.filter((z) => zoneIds.has(z.id)).map((z) => [z.lat, z.lon]);
  if (points.length === 1) state.map.flyTo(points[0], 9, { duration: 0.8 });
  else state.map.flyToBounds(points, { padding: [80, 80], maxZoom: 8, duration: 0.8 });
}

/* ---------- Plots drawn to scale ---------- */

function renderPlots(zoneIds, matchedLotIds) {
  els.plotZones.replaceChildren();
  const zones = state.zones.filter((z) => zoneIds.has(z.id));
  els.plotsHint.hidden = zones.length > 0;
  for (const zone of zones) {
    const row = el("div", { class: "plot-row" });
    for (const lot of zone.lots) {
      const label = `${lot.id}, ${area(lot.area_m2)}, ${STATUS_LABEL[lot.status]}`;
      const plot = el("div", {
        class: `plot ${lot.status}${matchedLotIds.has(lot.id) ? " match" : ""}`,
        title: label,
        "aria-label": label,
      },
        el("strong", { text: lot.id }),
        el("span", { text: `${area(lot.area_m2)} · ${money(lot.area_m2 * lot.price_tnd_per_m2)}` }),
      );
      plot.style.flexGrow = String(lot.area_m2);
      row.append(plot);
    }
    els.plotZones.append(el("div", { class: "plot-zone" },
      el("h3", { text: `${zone.name}, ${zone.governorate}` }), row));
  }
}

/* ---------- What the agent did ---------- */

function summarizeResult(call) {
  const out = call.output || {};
  if (call.is_error) return `Erreur renvoyée au modèle : ${out.error || "inconnue"}`;
  switch (call.name) {
    case "search_lots": return `${out.count} lot(s) trouvé(s)`;
    case "compare_zones": return `${(out.zones || []).length} zone(s) comparée(s)`;
    case "get_procedure": return `${(out.steps || []).length} étapes, ${(out.documents || []).length} documents`;
    case "prefill_request": return `Brouillon ${out.draft_id} créé, rien n'est envoyé`;
    case "track_dossier": return `Statut : ${DOSSIER_STATUS[out.status] || out.status}`;
    case "escalate_to_human": return `Ticket ${out.ticket_id}`;
    default: return "Terminé";
  }
}

function formatArgs(input) {
  const parts = Object.entries(input || {})
    .filter(([key, value]) => value !== null && value !== "" && !(key === "limit" && value === 5))
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("|") : value}`);
  return parts.join(", ");
}

function renderTrace(response) {
  els.traceSteps.replaceChildren();
  els.traceEmpty.hidden = true;
  for (const call of response.tool_calls) {
    const result = el("span", {
      class: `result${call.is_error ? " bad" : ""}`,
      text: summarizeResult(call),
    });
    const code = el("code", { dir: "ltr", text: `${call.name}(${formatArgs(call.input)})` });
    els.traceSteps.append(el("li", {}, code, result));
  }
  const seconds = (response.latency_ms / 1000).toFixed(1);
  const who = response.model || state.defaultModel;
  const tools = response.tool_calls.length
    ? "" : "Aucun outil utilisé. ";
  els.traceSteps.append(el("li", {
    class: "answered",
    text: `${tools}Réponse écrite par ${who} en ${seconds} s.`,
  }));
}

function applyToolEffects(response) {
  const zoneIds = new Set();
  const lots = new Set();
  for (const call of response.tool_calls) {
    if (call.is_error) continue;
    const out = call.output || {};
    if (call.name === "search_lots") {
      for (const lot of out.lots || []) { zoneIds.add(lot.zone_id); lots.add(lot.id); }
    } else if (call.name === "compare_zones") {
      for (const zone of out.zones || []) zoneIds.add(zone.id);
    } else if (call.name === "prefill_request") {
      const lotId = out.draft && out.draft.lot_id;
      const zone = state.zones.find((z) => z.lots.some((l) => l.id === lotId));
      if (zone) { zoneIds.add(zone.id); lots.add(lotId); }
    }
  }
  if (zoneIds.size) {
    highlightZones(zoneIds);
    renderPlots(zoneIds, lots);
  }
}

/* ---------- Conversation ---------- */

function addMessage(kind, text, meta) {
  els.empty.hidden = true;
  const item = el("li", { class: `msg ${kind}` }, el("p", { dir: "auto", text }));
  if (meta) item.append(el("span", { class: "meta", text: meta }));
  els.messages.append(item);
  item.scrollIntoView({ behavior: "smooth", block: "end" });
  return item;
}

function addDraft(draft) {
  const fields = [
    ["Lot", draft.lot_id],
    ["Demandeur", draft.applicant_name],
    ["Société", draft.company_name],
    ["Activité", draft.activity],
    ["Téléphone", draft.phone],
  ].filter(([, value]) => value);
  const list = el("dl");
  for (const [label, value] of fields) list.append(el("dt", { text: label }), el("dd", { dir: "auto", text: value }));

  const button = el("button", { class: "primary", type: "button", text: "Confirmer et envoyer la demande" });
  const note = el("span", { class: "note", text: "L'assistant ne peut pas envoyer la demande à votre place." });
  const card = el("li", { class: "draft" },
    el("h3", { text: `Brouillon de demande ${draft.id}` }),
    list,
    el("div", { class: "actions" }, button, note),
  );
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const dossier = await api(`/requests/${encodeURIComponent(draft.id)}/confirm`, { method: "POST" });
      card.classList.add("submitted");
      card.querySelector("h3").textContent = `Demande envoyée, numéro de suivi ${dossier.tracking_number}`;
      button.remove();
      const status = DOSSIER_STATUS[dossier.status] || dossier.status;
      note.textContent = `Statut : ${status}. Gardez ce numéro pour suivre votre dossier.`;
      await refreshMap();
    } catch (error) {
      button.disabled = false;
      note.textContent = `Envoi impossible : ${error.message}`;
    }
  });
  els.empty.hidden = true;
  els.messages.append(card);
  card.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function refreshMap() {
  const data = await api("/map");
  state.zones = data.zones;
  for (const zone of state.zones) {
    const marker = state.markers.get(zone.id);
    if (marker) marker.setStyle(zoneStyle(zone, false));
  }
  const shown = new Set([...els.plotZones.querySelectorAll(".plot")].map((p) => p.querySelector("strong").textContent));
  const zoneIds = new Set(state.zones.filter((z) => z.lots.some((l) => shown.has(l.id))).map((z) => z.id));
  if (zoneIds.size) renderPlots(zoneIds, new Set());
}

async function send(text) {
  const message = text.trim();
  if (!message || state.busy) return;
  state.busy = true;
  els.send.disabled = true;
  els.input.value = "";
  autosize();
  addMessage("user", message);
  const thinking = addMessage("agent thinking", "…");
  try {
    const response = await api("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: state.sessionId }),
    });
    state.sessionId = response.session_id;
    thinking.remove();
    const seconds = (response.latency_ms / 1000).toFixed(1);
    addMessage("agent", response.reply, `${seconds} s`);
    const isFallback = Boolean(response.model && state.defaultModel && response.model !== state.defaultModel);
    if (response.model) setBadge(response.model, isFallback);
    renderTrace(response);
    applyToolEffects(response);
    if (response.pending_draft) addDraft(response.pending_draft);
    speak(response.reply);
  } catch (error) {
    thinking.remove();
    addMessage("error", `La réponse n'a pas pu être obtenue : ${error.message}. Réessayez dans un instant.`);
  } finally {
    state.busy = false;
    els.send.disabled = false;
    els.input.focus();
  }
}

/* ---------- Voice (browser placeholder) ---------- */

const ARABIC = /[؀-ۿ]/g;
const LATIN = /[A-Za-z]/g;

function replyLanguage(text) {
  const arabic = (text.match(ARABIC) || []).length;
  const latin = (text.match(LATIN) || []).length;
  if (arabic > latin) return "ar";
  return /\b(le|la|les|des|vous|est|pour|une)\b/i.test(text) ? "fr-FR" : "en-US";
}

function speak(text) {
  if (!els.speakReplies.checked || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const lang = replyLanguage(text);
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.startsWith(lang.slice(0, 2)));
  utterance.lang = voice ? voice.lang : lang;
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}

function setupSpeechInput() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    els.mic.disabled = true;
    els.mic.title = "La saisie vocale n'est pas disponible dans ce navigateur (essayez Chrome ou Edge).";
    return;
  }
  let recognition = null;
  let finalText = "";

  const stop = () => recognition && recognition.stop();
  els.mic.addEventListener("click", () => {
    if (recognition) { stop(); return; }
    recognition = new Recognition();
    recognition.lang = els.speechLang.value;
    recognition.interimResults = true;
    recognition.continuous = false;
    finalText = "";
    els.mic.setAttribute("aria-pressed", "true");
    els.mic.title = "J'écoute… cliquez pour arrêter";
    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece; else interim += piece;
      }
      els.input.value = (finalText + interim).trim();
      autosize();
    };
    recognition.onerror = (event) => {
      els.mic.title = `Micro : ${event.error}`;
    };
    recognition.onend = () => {
      els.mic.setAttribute("aria-pressed", "false");
      els.mic.title = "Parlez votre question";
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

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  send(els.input.value);
});
els.input.addEventListener("input", autosize);
els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send(els.input.value);
  }
});
for (const example of document.querySelectorAll(".example")) {
  example.addEventListener("click", () => send(example.textContent));
}

setupSpeechInput();
loadStatus();
loadMap().catch(() => (els.mapOffline.hidden = false));
