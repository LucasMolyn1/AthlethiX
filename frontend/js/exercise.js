const params     = new URLSearchParams(location.search);
const exerciseId = parseInt(params.get("id"));

if (!exerciseId) location.href = "strength.html";

const CAT_COLORS = {
  push: "#E8501A", pull: "#22c55e", legs: "#f59e0b", core: "#8b5cf6", cardio: "#ef4444",
};

async function loadProgress() {
  try {
    const { exercise, history, pr } = await API.getExerciseProgress(exerciseId);

    document.title = `AthletiX — ${exercise.name}`;
    document.getElementById("exercise-name").textContent = exercise.name;

    const catEl = document.getElementById("exercise-category");
    const color = CAT_COLORS[exercise.category] || "#999999";
    catEl.textContent = exercise.category;
    catEl.style.cssText = `display:inline-block;background:${color}22;color:${color};
      padding:2px 10px;border-radius:4px;font-size:.75rem;font-weight:700;
      text-transform:uppercase;letter-spacing:.04em;margin-top:4px`;

    if (pr) {
      document.getElementById("pr-1rm").textContent    = pr.best_1rm   ? pr.best_1rm   + " kg" : "—";
      document.getElementById("pr-date").textContent   = pr.date       || "—";
      document.getElementById("pr-weight").textContent = pr.max_weight ? pr.max_weight + " kg" : "—";
      document.getElementById("pr-volume").textContent = pr.total_volume ? pr.total_volume + " kg" : "—";
      document.getElementById("pr-box").style.display  = "block";
    }

    const tbody = document.getElementById("history-body");
    if (!history.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty">Aucune donnée d'entraînement pour cet exercice</td></tr>`;
      return;
    }

    renderChart(history);

    const prOrm = pr ? pr.best_1rm : null;
    tbody.innerHTML = [...history].reverse().map(h => `
      <tr onclick="location.href='strength_session.html?id=${h.session_id}'" style="cursor:pointer">
        <td>${h.date}</td>
        <td>${h.max_weight   ? h.max_weight   + " kg" : "—"}</td>
        <td style="${h.best_1rm && h.best_1rm === prOrm ? "color:var(--green);font-weight:700" : ""}">
          ${h.best_1rm ? h.best_1rm + " kg" : "—"}
        </td>
        <td>${h.total_volume ? h.total_volume + " kg" : "—"}</td>
        <td>${h.sets_count}</td>
      </tr>
    `).join("");

  } catch (e) {
    document.getElementById("exercise-name").textContent = "Erreur";
    showToast(e.message, "err");
  }
}

function renderChart(history) {
  const ctx = document.getElementById("progress-chart").getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      labels: history.map(h => h.date),
      datasets: [{
        label: "1RM estimé (kg)",
        data: history.map(h => h.best_1rm),
        borderColor: "#E8501A",
        backgroundColor: "rgba(232,80,26,.08)",
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: "#E8501A",
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: "#999999", maxTicksLimit: 10 },
          grid:  { color: "#EEEDE8" },
        },
        y: {
          ticks: { color: "#999999", callback: v => v + " kg" },
          grid:  { color: "#EEEDE8" },
        },
      },
    },
  });
}

function showToast(msg, type = "ok") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => (t.className = ""), 3000);
}

loadProgress();
