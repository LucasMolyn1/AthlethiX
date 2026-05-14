const PAGE_SIZE = 20;
const SESSION_TYPES = {
  full_body: "Full Body", push: "Push", pull: "Pull", legs: "Legs",
  upper: "Haut du corps", lower: "Bas du corps", cardio: "Cardio", other: "Autre",
};
const CAT_COLORS = {
  push: "#E8501A", pull: "#22c55e", legs: "#f59e0b", core: "#8b5cf6", cardio: "#ef4444",
};

let offset = 0;
let currentSessions = [];

function fmtDate(s) { return s ? s.slice(0, 10) : "—"; }

function fmtDur(secs) {
  if (!secs) return "—";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h${String(m).padStart(2, "0")}` : `${m}min`;
}

function scoreHtml(v) {
  if (!v) return '<span style="color:var(--text-muted)">—</span>';
  const c = v >= 7 ? "var(--green)" : v >= 4 ? "var(--orange)" : "var(--red)";
  return `<span style="color:${c};font-weight:700">${v}</span>`;
}

async function loadSessions() {
  const dateFrom = document.getElementById("date-from").value || null;
  const dateTo   = document.getElementById("date-to").value   || null;
  const tbody    = document.getElementById("sessions-body");
  tbody.innerHTML = `<tr><td colspan="7" class="loading">Chargement...</td></tr>`;
  try {
    currentSessions = await API.getSessions({ date_from: dateFrom, date_to: dateTo, limit: PAGE_SIZE, offset });
    renderSessions();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

function renderSessions() {
  const tbody = document.getElementById("sessions-body");
  if (!currentSessions.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Aucune séance enregistrée</td></tr>`;
  } else {
    tbody.innerHTML = currentSessions.map(s => `
      <tr onclick="location.href='strength_session.html?id=${s.id}'" style="cursor:pointer">
        <td>${fmtDate(s.date)}</td>
        <td>${s.session_type ? (SESSION_TYPES[s.session_type] || s.session_type) : '<span style="color:var(--text-muted)">—</span>'}</td>
        <td>${fmtDur(s.duration)}</td>
        <td>${s.sets_count}</td>
        <td>${scoreHtml(s.feeling_score)}</td>
        <td>${scoreHtml(s.fatigue_score)}</td>
        <td>${scoreHtml(s.sleep_score)}</td>
      </tr>
    `).join("");
  }
  document.getElementById("btn-prev").disabled = offset === 0;
  document.getElementById("btn-next").disabled = currentSessions.length < PAGE_SIZE;
  document.getElementById("page-info").textContent = `Page ${Math.floor(offset / PAGE_SIZE) + 1}`;
}

function applyFilters() { offset = 0; loadSessions(); }
function resetFilters() {
  document.getElementById("date-from").value = "";
  document.getElementById("date-to").value   = "";
  offset = 0;
  loadSessions();
}
function prevPage() { if (offset >= PAGE_SIZE) { offset -= PAGE_SIZE; loadSessions(); } }
function nextPage() { offset += PAGE_SIZE; loadSessions(); }

async function loadExercises() {
  const container = document.getElementById("exercises-list");
  try {
    const exercises = await API.getExercises();
    if (!exercises.length) {
      container.innerHTML = `<span class="empty">Aucun exercice</span>`;
      return;
    }
    container.innerHTML = exercises.map(e => `
      <a href="exercise.html?id=${e.id}"
        style="display:inline-flex;align-items:center;gap:6px;background:var(--surface2);
               border:1px solid var(--border);border-radius:6px;padding:6px 12px;
               font-size:.84rem;color:var(--text);text-decoration:none;transition:background .15s"
        onmouseover="this.style.background='var(--bg)'"
        onmouseout="this.style.background='var(--surface2)'">
        <span style="width:8px;height:8px;border-radius:50%;background:${CAT_COLORS[e.category] || "#999999"};flex-shrink:0"></span>
        ${e.name}
        ${e.is_custom ? '<span style="font-size:.7rem;color:var(--text-muted)">(custom)</span>' : ""}
      </a>
    `).join("");
  } catch (e) {
    container.innerHTML = `<span style="color:var(--red)">Erreur : ${e.message}</span>`;
  }
}

function toggleExerciseForm() {
  const f = document.getElementById("exercise-form");
  f.style.display = f.style.display === "none" ? "block" : "none";
}

async function createExercise() {
  const name     = document.getElementById("ex-name").value.trim();
  const category = document.getElementById("ex-category").value;
  if (!name) { showToast("Nom requis", "err"); return; }
  try {
    await API.createExercise({ name, category });
    document.getElementById("ex-name").value    = "";
    document.getElementById("exercise-form").style.display = "none";
    showToast("Exercice créé", "ok");
    loadExercises();
  } catch (e) {
    showToast(e.message, "err");
  }
}

function showToast(msg, type = "ok") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => (t.className = ""), 3000);
}

loadSessions();
loadExercises();
