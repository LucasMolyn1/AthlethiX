let currentDate = new Date().toISOString().slice(0, 10);
let hasExisting  = false;

async function init() {
  document.getElementById("current-date").value = currentDate;
  updateDayLabel();
  await loadLog(currentDate);
  loadRecent();
}

function updateDayLabel() {
  const d = new Date(currentDate + "T12:00:00");
  const today = new Date().toISOString().slice(0, 10);
  let label = d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
  if (currentDate === today) label += " (aujourd'hui)";
  document.getElementById("day-label").textContent = label;
}

async function loadLog(date) {
  currentDate = date;
  document.getElementById("current-date").value = date;
  updateDayLabel();
  clearForm();

  try {
    const log = await API.getNutritionLog(date);
    populateForm(log);
    hasExisting = true;
    document.getElementById("form-status").textContent = "Journal existant";
    document.getElementById("btn-delete").style.display = "inline-flex";
  } catch (e) {
    if (e.status === 404) {
      hasExisting = false;
      document.getElementById("form-status").textContent = "Nouveau journal";
      document.getElementById("btn-delete").style.display = "none";
    } else {
      showToast(e.message, "err");
    }
  }
}

function populateForm(log) {
  document.getElementById("hydration").value    = log.hydration_liters   ?? "";
  document.getElementById("pre-meal").value     = log.pre_workout_meal   ?? "";
  document.getElementById("post-meal").value    = log.post_workout_meal  ?? "";
  document.getElementById("supplements").value  = log.supplements        ?? "";
  document.getElementById("notes").value        = log.notes              ?? "";

  if (log.nutrition_score) {
    const el = document.getElementById("nutrition-score");
    el.value = log.nutrition_score;
    el.dataset.touched = "1";
    document.getElementById("score-val").textContent = log.nutrition_score;
  }
}

function clearForm() {
  document.getElementById("hydration").value    = "";
  document.getElementById("pre-meal").value     = "";
  document.getElementById("post-meal").value    = "";
  document.getElementById("supplements").value  = "";
  document.getElementById("notes").value        = "";
  const scoreEl = document.getElementById("nutrition-score");
  scoreEl.value          = "5";
  scoreEl.dataset.touched = "0";
  document.getElementById("score-val").textContent = "—";
}

function buildUpdatePayload() {
  const scoreEl   = document.getElementById("nutrition-score");
  const hydration = parseFloat(document.getElementById("hydration").value);
  return {
    hydration_liters:   isNaN(hydration) ? null : hydration,
    nutrition_score:    scoreEl.dataset.touched === "1" ? parseInt(scoreEl.value) : null,
    pre_workout_meal:   document.getElementById("pre-meal").value.trim()    || null,
    post_workout_meal:  document.getElementById("post-meal").value.trim()   || null,
    supplements:        document.getElementById("supplements").value.trim() || null,
    notes:              document.getElementById("notes").value.trim()        || null,
  };
}

async function saveLog() {
  const update = buildUpdatePayload();
  try {
    if (hasExisting) {
      await API.updateNutritionLog(currentDate, update);
      showToast("Journal mis à jour", "ok");
    } else {
      await API.createNutritionLog({ date: currentDate, ...update });
      hasExisting = true;
      document.getElementById("form-status").textContent = "Journal existant";
      document.getElementById("btn-delete").style.display = "inline-flex";
      showToast("Journal créé", "ok");
    }
    loadRecent();
  } catch (e) {
    showToast(e.message, "err");
  }
}

async function deleteLog() {
  if (!confirm("Supprimer ce journal ?")) return;
  try {
    await API.deleteNutritionLog(currentDate);
    hasExisting = false;
    clearForm();
    document.getElementById("form-status").textContent = "Nouveau journal";
    document.getElementById("btn-delete").style.display = "none";
    showToast("Journal supprimé", "ok");
    loadRecent();
  } catch (e) {
    showToast(e.message, "err");
  }
}

async function loadRecent() {
  const tbody = document.getElementById("recent-body");
  try {
    const logs = await API.getNutritionLogs({ limit: 10 });
    if (!logs.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty">Aucun journal enregistré</td></tr>`;
      return;
    }
    tbody.innerHTML = logs.map(l => `
      <tr onclick="loadLog('${l.date}')" style="cursor:pointer">
        <td>${l.date}</td>
        <td>${l.hydration_liters != null ? l.hydration_liters + " L" : "—"}</td>
        <td>${scoreHtml(l.nutrition_score)}</td>
        <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.pre_workout_meal  || "—"}</td>
        <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.post_workout_meal || "—"}</td>
        <td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.supplements       || "—"}</td>
      </tr>
    `).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty">Erreur : ${e.message}</td></tr>`;
  }
}

function prevDay() {
  const d = new Date(currentDate + "T12:00:00");
  d.setDate(d.getDate() - 1);
  loadLog(d.toISOString().slice(0, 10));
}

function nextDay() {
  const d = new Date(currentDate + "T12:00:00");
  d.setDate(d.getDate() + 1);
  loadLog(d.toISOString().slice(0, 10));
}

function scoreHtml(v) {
  if (!v) return '<span style="color:var(--text-muted)">—</span>';
  const c = v >= 7 ? "var(--green)" : v >= 4 ? "var(--orange)" : "var(--red)";
  return `<span style="color:${c};font-weight:700">${v}</span>`;
}

function showToast(msg, type = "ok") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => (t.className = ""), 3000);
}

init();
