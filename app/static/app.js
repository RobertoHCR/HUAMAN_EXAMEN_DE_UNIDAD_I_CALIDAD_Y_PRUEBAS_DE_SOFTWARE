/* La interfaz consume la API real; los textos se insertan con textContent. */
const $ = (selector) => document.querySelector(selector);
const state = { courts: [], results: [], selected: null, query: null, adminKey: "", user: null };
try { state.user = JSON.parse(localStorage.getItem("courtflow-user")); } catch { localStorage.removeItem("courtflow-user"); }
const money = (cents) => new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(cents / 100);
const limaDate = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Lima", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
const tomorrow = new Date(limaDate() + "T12:00:00");
tomorrow.setDate(tomorrow.getDate() + 1);
$("#date").value = [tomorrow.getFullYear(), String(tomorrow.getMonth() + 1).padStart(2, "0"), String(tomorrow.getDate()).padStart(2, "0")].join("-");
$("#date").min = limaDate();
let toastTimer;
function notify(message, error = false) {
  const toast = $("#toast"); toast.textContent = message; toast.className = error ? "toast error" : "toast"; toast.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.hidden = true; }, 6500);
}
async function api(path, { method = "GET", body, admin = false } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (admin) headers["X-Admin-Token"] = state.adminKey;
  if (state.user) headers["X-User-Key"] = state.user.access_key;
  const response = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Revisa los datos ingresados.");
  return result;
}
function node(tag, className, text) {
  const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element;
}
function empty(container, text) { container.replaceChildren(node("div", "empty", text)); }
function action(label, handler, className = "primary") {
  const button = node("button", className, label); button.type = "button";
  button.addEventListener("click", async () => {
    button.disabled = true;
    try { await handler(); } catch (error) { notify(error.message, true); }
    finally { button.disabled = false; }
  });
  return button;
}
async function search() {
  const button = $("#search-form button"); button.disabled = true;
  const query = { date: $("#date").value, time: $("#time").value, duration: Number($("#duration").value) };
  state.query = null;
  try {
    state.results = await api("/courts/availability?" + new URLSearchParams(query));
    state.query = query; renderCourts();
  } catch (error) { empty($("#courts"), error.message); $("#result-summary").textContent = "Ajusta la búsqueda para consultar una franja."; }
  finally { button.disabled = false; }
}
function renderCourts() {
  const results = state.results.filter((court) => (!$("#sport").value || court.sport === $("#sport").value) && (!$("#venue").value || court.venue === $("#venue").value));
  const container = $("#courts"); container.replaceChildren();
  $("#result-summary").textContent = results.filter((court) => court.available).length + " lozas disponibles · " + state.query.date + " · " + state.query.time;
  if (!results.length) return empty(container, "No hay lozas con esos filtros. Prueba con otro deporte o sede.");
  for (const court of results) {
    const card = node("article", "court-card");
    const visual = node("div", "court-visual " + (court.sport === "Vóley" ? "volley" : court.sport === "Básquet" ? "basket" : ""));
    visual.setAttribute("aria-hidden", "true"); visual.append(node("div", "court-lines"), node("span", "court-tag", court.sport), node("span", "court-number", "LOZA " + String(court.id).padStart(2, "0")));
    const body = node("div", "court-body"); body.append(node("h3", "", court.name), node("p", "court-meta", court.venue + " · Hasta " + court.capacity + " personas"));
    body.append(node("span", "card-status" + (court.available ? "" : " busy"), court.available ? "Disponible en tu horario" : "Franja no disponible"));
    const bottom = node("div", "card-bottom"); const price = node("div", "price", money(court.hourly_rate)); price.append(node("small", "", "por hora"));
    const button = action("Reservar", () => openBooking(court)); button.disabled = !court.available;
    bottom.append(price, button); body.append(bottom); card.append(visual, body); container.append(card);
  }
}
async function loadCourts() {
  state.courts = await api("/courts");
  const venue = $("#venue"); const previous = venue.value; venue.replaceChildren(new Option("Todas las sedes", ""));
  for (const value of new Set(state.courts.map((court) => court.venue))) venue.add(new Option(value, value));
  venue.value = previous;
  for (const id of ["#schedule-court", "#admin-filter"]) {
    const select = $(id); const selected = select.value; select.replaceChildren();
    if (id === "#admin-filter") select.add(new Option("Todas las lozas", ""));
    for (const court of state.courts) select.add(new Option(court.name, court.id));
    if (selected) select.value = selected;
  }
}
function openBooking(court) {
  if (!state.query) return;
  state.selected = court;
  $("#booking-title").textContent = court.name;
  $("#booking-summary").textContent = state.query.date + " · " + state.query.time + " · " + state.query.duration + " min · Total " + money(court.hourly_rate * state.query.duration / 60);
  $("#user-name").value = state.user?.name || ""; $("#user-email").value = state.user?.email || "";
  $("#user-name").disabled = !!state.user; $("#user-email").disabled = !!state.user;
  $("#booking-dialog").showModal();
}
$("#booking-dialog .close").addEventListener("click", () => $("#booking-dialog").close());
$("#booking-form").addEventListener("submit", async (event) => {
  event.preventDefault(); $("#booking-submit").disabled = true;
  try {
    if (!state.user) {
      const email = $("#user-email").value.trim();
      state.user = { ...await api("/users", { method: "POST", body: { name: $("#user-name").value.trim(), email } }), email };
      localStorage.setItem("courtflow-user", JSON.stringify(state.user));
    }
    await api("/rentals", { method: "POST", body: { court_id: state.selected.id, user_id: state.user.id, ...state.query, event: $("#event").value.trim() } });
    $("#booking-dialog").close(); $("#event").value = ""; notify("Solicitud registrada. Puedes consultarla en Mis reservas."); await search();
  } catch (error) { notify(error.message, true); }
  finally { $("#booking-submit").disabled = false; }
});
function renderRecords(container, records, isAdmin) {
  container.replaceChildren();
  if (!records.length) return empty(container, isAdmin ? "No hay solicitudes para esta loza." : "Todavía no tienes reservas. Elige una loza y guarda tu primer encuentro.");
  for (const item of records) {
    const record = node("article", "record"); const content = node("div");
    content.append(node("h3", "", item.court_name), node("p", "", item.date + " · " + item.time + "–" + item.end_time), node("p", "", item.event + (isAdmin ? " · " + item.user_name : "")));
    const actions = node("div", "record-actions");
    actions.append(node("strong", "", money(item.total)), node("span", "status" + (item.status === "Cancelada" ? " cancelled" : ""), item.status + " · " + item.payment));
    if (isAdmin && item.status !== "Cancelada") {
      if (item.status !== "Confirmada") actions.append(action("Confirmar", async () => {
        await api("/rentals/" + item.id + "/confirm", { method: "POST", body: { payment: item.payment }, admin: true }); await loadAdmin(); notify("Alquiler confirmado.");
      }, "secondary"));
      if (item.payment !== "Pagado") actions.append(action("Registrar pago", async () => {
        if (!window.confirm("¿La sede recibió el pago de " + money(item.total) + "?")) return;
        await api("/rentals/" + item.id + "/confirm", { method: "POST", body: { payment: "Pagado" }, admin: true }); await loadAdmin(); notify("Pago registrado.");
      }));
    } else if (!isAdmin && item.status !== "Cancelada" && item.payment !== "Pagado") {
      actions.append(action("Cancelar", async () => {
        if (!window.confirm("¿Cancelar esta reserva y liberar la franja?")) return;
        await api("/rentals/" + item.id + "/cancel", { method: "POST" }); await loadHistory(); notify("Reserva cancelada.");
      }, "secondary"));
    }
    record.append(content, actions); container.append(record);
  }
}
async function loadHistory() {
  if (!state.user) return empty($("#history"), "Todavía no tienes reservas en este navegador.");
  renderRecords($("#history"), await api("/users/" + state.user.id + "/rentals"), false);
}
async function loadAdmin() {
  const suffix = $("#admin-filter").value ? "?court_id=" + $("#admin-filter").value : "";
  renderRecords($("#admin-rentals"), await api("/rentals" + suffix, { admin: true }), true);
}
document.querySelectorAll(".nav").forEach((button) => button.addEventListener("click", async () => {
  document.querySelectorAll(".nav").forEach((tab) => tab.classList.toggle("active", tab === button));
  document.querySelectorAll(".view").forEach((view) => { view.hidden = view.id !== button.dataset.view + "-view"; });
  $("#breadcrumb").textContent = { reserve: "Reservar", history: "Mis reservas", admin: "Administración" }[button.dataset.view];
  try { if (button.dataset.view === "history") await loadHistory(); if (button.dataset.view === "reserve") await search(); } catch (error) { notify(error.message, true); }
}));
$("#search-form").addEventListener("submit", (event) => { event.preventDefault(); search(); });
$("#sport").addEventListener("change", () => { if (state.query) renderCourts(); });
$("#venue").addEventListener("change", () => { if (state.query) renderCourts(); });
$("#admin-login").addEventListener("submit", async (event) => {
  event.preventDefault(); state.adminKey = $("#admin-key").value;
  try { await loadAdmin(); $("#admin-login").hidden = true; $("#admin-content").hidden = false; $("#admin-key").value = ""; }
  catch (error) { state.adminKey = ""; notify(error.message, true); }
});
$("#admin-logout").addEventListener("click", () => { state.adminKey = ""; $("#admin-content").hidden = true; $("#admin-login").hidden = false; $("#admin-rentals").replaceChildren(); });
$("#admin-refresh").addEventListener("click", () => loadAdmin().catch((error) => notify(error.message, true)));
$("#admin-filter").addEventListener("change", () => loadAdmin().catch((error) => notify(error.message, true)));
$("#court-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.target; const values = new FormData(form);
  try {
    await api("/courts", { method: "POST", admin: true, body: { name: values.get("name"), venue: values.get("venue"), sport: values.get("sport"), capacity: Number(values.get("capacity")), hourly_rate: Math.round(Number(values.get("rate")) * 100) } });
    form.reset(); await loadCourts(); await search(); notify("Loza registrada. Disponible todos los días de 08:00 a 23:00.");
  } catch (error) { notify(error.message, true); }
});
$("#schedule-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const values = new FormData(event.target);
  try {
    await api("/courts/" + values.get("court_id") + "/schedules", { method: "POST", admin: true, body: { weekday: Number(values.get("weekday")), opens: values.get("opens"), closes: values.get("closes") } });
    notify("Horario guardado."); await search();
  } catch (error) { notify(error.message, true); }
});
loadCourts().then(search).catch((error) => notify("No se pudo conectar: " + error.message, true));
