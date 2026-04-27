/**
 * activity.js — Détail d'une activité + journal associé.
 */

const TYPE_META = {
  run:      { icon: "🏃", label: "Course" },
  trail:    { icon: "⛰️",  label: "Trail" },
  cycling:  { icon: "🚴", label: "Vélo" },
  swimming: { icon: "🏊", label: "Natation" },
  strength: { icon: "🏋️", label: "Muscu" },
  other:    { icon: "🎯", label: "Autre" },
};

function fmtDuration(s) {
  if (!s) return "–";
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h > 0 ? `${h}h${String(m).padStart(2,"0")}` : `${m}min ${String(sec).padStart(2,"0")}s`;
}
function fmtDist(m) { return m ? (m >= 1000 ? (m/1000).toFixed(2)+" km" : Math.round(m)+" m") : "–"; }
function fmtDate(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("fr-FR", { weekday:"long", day:"numeric", month:"long", year:"numeric", hour:"2-digit", minute:"2-digit" });
}
function toast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "show " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ""; }, 3500);
}

function getActivityId() {
  return new URLSearchParams(window.location.search).get("id");
}

let hasJournal = false;

async function loadActivity(id) {
  try {
    const a = await API.getActivity(id);
    const m = TYPE_META[a.type] || TYPE_META.other;

    document.title = `AthletiX — ${m.label}`;
    document.getElementById("page-title").textContent = `${m.icon} ${m.label} — ${fmtDate(a.date)}`;
    document.getElementById("activity-badge").innerHTML = `<span class="badge badge-${a.type}">${m.label}</span>`;

    const stats = [
      { label: "Distance",   value: fmtDist(a.distance) },
      { label: "Durée",      value: fmtDuration(a.duration) },
      { label: "Dénivelé",   value: a.elevation_gain ? "+"+Math.round(a.elevation_gain)+"m" : "–" },
      { label: "FC moyenne", value: a.avg_hr ? a.avg_hr+" bpm" : "–" },
      { label: "FC max",     value: a.max_hr ? a.max_hr+" bpm" : "–" },
      { label: "Calories",   value: a.calories ? a.calories+" kcal" : "–" },
    ];

    document.getElementById("detail-stats").innerHTML = stats.map(s => `
      <div class="detail-stat">
        <div class="label">${s.label}</div>
        <div class="value">${s.value}</div>
      </div>`).join("");

    // Pré-remplir le journal si existant
    if (a.journal) {
      hasJournal = true;
      const j = a.journal;
      setJournalFields(j);
      document.getElementById("journal-status").textContent = "Dernière modification : " +
        (j.updated_at || j.created_at || "").slice(0,16).replace("T"," ");
    }
  } catch (e) {
    document.getElementById("detail-stats").innerHTML = `<p class="empty">Erreur : ${e.message}</p>`;
  }
}

function setJournalFields(j) {
  if (j.context)       document.getElementById("j-context").value = j.context;
  if (j.feeling_score) { document.getElementById("j-feeling").value = j.feeling_score; document.getElementById("v-feeling").textContent = j.feeling_score; }
  if (j.fatigue_score) { document.getElementById("j-fatigue").value = j.fatigue_score; document.getElementById("v-fatigue").textContent = j.fatigue_score; }
  if (j.sleep_score)   { document.getElementById("j-sleep").value   = j.sleep_score;   document.getElementById("v-sleep").textContent   = j.sleep_score; }
  if (j.pain_notes)    document.getElementById("j-pain").value   = j.pain_notes;
  if (j.free_notes)    document.getElementById("j-notes").value  = j.free_notes;
}

function readJournalFields() {
  return {
    context:       document.getElementById("j-context").value.trim() || null,
    feeling_score: parseInt(document.getElementById("j-feeling").value),
    fatigue_score: parseInt(document.getElementById("j-fatigue").value),
    sleep_score:   parseInt(document.getElementById("j-sleep").value),
    pain_notes:    document.getElementById("j-pain").value.trim() || null,
    free_notes:    document.getElementById("j-notes").value.trim() || null,
  };
}

async function saveJournal(id) {
  const btn = document.getElementById("btn-save-journal");
  btn.disabled = true;
  try {
    const data = readJournalFields();
    if (hasJournal) {
      await API.updateJournal(id, data);
    } else {
      await API.createJournal(id, data);
      hasJournal = true;
    }
    toast("Journal enregistré", "ok");
    document.getElementById("journal-status").textContent = "Enregistré à " + new Date().toLocaleTimeString("fr-FR", { hour:"2-digit", minute:"2-digit" });
  } catch (e) {
    toast("Erreur : " + e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const id = getActivityId();
  if (!id) { document.getElementById("detail-stats").innerHTML = '<p class="empty">ID activité manquant.</p>'; return; }
  loadActivity(id);
  document.getElementById("btn-save-journal").addEventListener("click", () => saveJournal(id));
});
