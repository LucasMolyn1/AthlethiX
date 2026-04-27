const urlParams  = new URLSearchParams(location.search);
let sessionId    = urlParams.has("id") ? parseInt(urlParams.get("id")) : null;
let exercises    = [];
let rowCounter   = 0;

async function init() {
  document.getElementById("date").value = new Date().toISOString().slice(0, 10);

  try {
    exercises = await API.getExercises();
  } catch (e) {
    showToast("Erreur chargement exercices : " + e.message, "err");
  }

  if (sessionId) {
    document.getElementById("page-title").textContent = "Modifier la séance";
    document.getElementById("btn-delete").style.display = "inline-flex";
    await loadSession();
  }
}

async function loadSession() {
  try {
    const s = await API.getSession(sessionId);
    document.getElementById("date").value         = s.date.slice(0, 10);
    document.getElementById("session-type").value = s.session_type || "";
    document.getElementById("duration").value     = s.duration ? Math.round(s.duration / 60) : "";
    document.getElementById("context").value      = s.context || "";
    document.getElementById("notes").value        = s.notes || "";

    setScore("fatigue", s.fatigue_score);
    setScore("sleep",   s.sleep_score);
    setScore("feeling", s.feeling_score);

    s.sets.forEach(set => addSetRow(set));
  } catch (e) {
    showToast("Erreur : " + e.message, "err");
  }
}

function setScore(id, value) {
  if (!value) return;
  const el = document.getElementById(id);
  el.value = value;
  el.dataset.touched = "1";
  document.getElementById(id + "-val").textContent = value;
}

function getScore(id) {
  const el = document.getElementById(id);
  return el.dataset.touched === "1" ? parseInt(el.value) : null;
}

function addSetRow(preset = {}) {
  rowCounter++;
  const id    = rowCounter;
  const tbody = document.getElementById("sets-tbody");
  document.getElementById("sets-empty").style.display = "none";

  const exOptions = exercises
    .map(e => `<option value="${e.id}" ${preset.exercise_id == e.id ? "selected" : ""}>${e.name}</option>`)
    .join("");

  const feelingOptions = [1, 2, 3, 4, 5]
    .map(n => `<option value="${n}" ${preset.feeling == n ? "selected" : ""}>${n}</option>`)
    .join("");

  const inp = "background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:.84rem";

  const tr = document.createElement("tr");
  tr.id = `set-row-${id}`;
  tr.innerHTML = `
    <td>
      <select class="set-exercise" style="${inp};min-width:160px">
        <option value="">— Exercice —</option>
        ${exOptions}
      </select>
    </td>
    <td>
      <input type="number" class="set-reps" value="${preset.reps ?? ""}" min="1" max="200"
        style="${inp};width:60px">
    </td>
    <td>
      <input type="number" class="set-weight" value="${preset.weight_kg ?? ""}" min="0" max="500" step="0.5"
        style="${inp};width:80px">
    </td>
    <td>
      <select class="set-feeling" style="${inp}">
        <option value="">—</option>
        ${feelingOptions}
      </select>
    </td>
    <td>
      <input type="text" class="set-notes" value="${preset.notes ?? ""}" placeholder="Notes..."
        style="${inp};width:120px">
    </td>
    <td>
      <button class="btn btn-ghost" style="padding:4px 10px;font-size:.8rem"
        onclick="removeRow(${id})">✕</button>
    </td>
  `;
  tbody.appendChild(tr);
}

function removeRow(id) {
  const row = document.getElementById(`set-row-${id}`);
  if (row) row.remove();
  if (!document.getElementById("sets-tbody").querySelector("tr")) {
    document.getElementById("sets-empty").style.display = "block";
  }
}

function buildPayload() {
  const date = document.getElementById("date").value;
  if (!date) { showToast("Date requise", "err"); return null; }

  const durationMin = parseInt(document.getElementById("duration").value);

  const sets = [];
  const exerciseCounts = {};
  document.querySelectorAll("#sets-tbody tr").forEach(row => {
    const exercise_id = parseInt(row.querySelector(".set-exercise").value);
    if (!exercise_id) return;
    exerciseCounts[exercise_id] = (exerciseCounts[exercise_id] || 0) + 1;
    sets.push({
      exercise_id,
      set_number: exerciseCounts[exercise_id],
      reps:       parseInt(row.querySelector(".set-reps").value)    || null,
      weight_kg:  parseFloat(row.querySelector(".set-weight").value) || null,
      feeling:    parseInt(row.querySelector(".set-feeling").value)  || null,
      notes:      row.querySelector(".set-notes").value.trim()       || null,
    });
  });

  return {
    date,
    duration:      !isNaN(durationMin) && durationMin > 0 ? durationMin * 60 : null,
    session_type:  document.getElementById("session-type").value  || null,
    context:       document.getElementById("context").value.trim() || null,
    fatigue_score: getScore("fatigue"),
    sleep_score:   getScore("sleep"),
    feeling_score: getScore("feeling"),
    notes:         document.getElementById("notes").value.trim()   || null,
    sets,
  };
}

async function saveSession() {
  const payload = buildPayload();
  if (!payload) return;
  try {
    if (sessionId) {
      await API.updateSession(sessionId, payload);
      showToast("Séance mise à jour", "ok");
    } else {
      const res = await API.createSession(payload);
      sessionId = res.id;
      history.replaceState({}, "", `?id=${sessionId}`);
      document.getElementById("page-title").textContent = "Modifier la séance";
      document.getElementById("btn-delete").style.display = "inline-flex";
      showToast("Séance créée", "ok");
    }
  } catch (e) {
    showToast(e.message, "err");
  }
}

async function deleteSession() {
  if (!confirm("Supprimer cette séance et toutes ses séries ?")) return;
  try {
    await API.deleteSession(sessionId);
    location.href = "strength.html";
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

init();
