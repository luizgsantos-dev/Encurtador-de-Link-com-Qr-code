function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

const DEVICE_LABELS = {
  mobile: "Celular",
  desktop: "Desktop",
  tablet: "Tablet",
  bot: "Bot",
  unknown: "Desconhecido",
};

function getLinkIdFromQuery() {
  const params = new URLSearchParams(location.search);
  return params.get("id");
}

function drawLineChart(canvas, dailyClicks) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };

  ctx.clearRect(0, 0, width, height);

  if (dailyClicks.length === 0) {
    ctx.fillStyle = "#6b7280";
    ctx.font = "14px sans-serif";
    ctx.fillText("Sem dados de cliques ainda.", padding.left, height / 2);
    return;
  }

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxCount = Math.max(...dailyClicks.map((d) => d.count), 1);
  const stepX = dailyClicks.length > 1 ? plotWidth / (dailyClicks.length - 1) : 0;

  // eixos
  ctx.strokeStyle = "#e2e5ea";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();

  // linha de cliques
  ctx.strokeStyle = "#4f46e5";
  ctx.lineWidth = 2;
  ctx.beginPath();
  dailyClicks.forEach((point, index) => {
    const x = padding.left + index * stepX;
    const y = height - padding.bottom - (point.count / maxCount) * plotHeight;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // pontos
  ctx.fillStyle = "#4f46e5";
  dailyClicks.forEach((point, index) => {
    const x = padding.left + index * stepX;
    const y = height - padding.bottom - (point.count / maxCount) * plotHeight;
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  });

  // rótulos do eixo Y (0 e máximo)
  ctx.fillStyle = "#6b7280";
  ctx.font = "11px sans-serif";
  ctx.fillText(String(maxCount), 4, padding.top + 4);
  ctx.fillText("0", 4, height - padding.bottom);

  // rótulos do eixo X (primeira e última data)
  ctx.fillText(dailyClicks[0].date, padding.left, height - 8);
  const lastLabel = dailyClicks[dailyClicks.length - 1].date;
  ctx.fillText(lastLabel, width - padding.right - lastLabel.length * 6, height - 8);
}

function renderTable(tableId, rows, labelKey, labelMap = {}) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  if (rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted);">Sem dados ainda.</td></tr>';
    return;
  }
  tbody.innerHTML = rows
    .map((row) => {
      const label = labelMap[row[labelKey]] || row[labelKey];
      return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(row.count)}</td></tr>`;
    })
    .join("");
}

async function loadLinkDetail() {
  const linkId = getLinkIdFromQuery();
  if (!linkId) {
    location.href = "/dashboard.html";
    return;
  }

  const [link, stats] = await Promise.all([api.getLink(linkId), api.getStats(linkId)]);

  document.getElementById("link-title").textContent = link.title || "Sem título";
  document.getElementById("link-short-url").textContent = link.short_url;
  document.getElementById("link-short-url").href = link.short_url;
  document.getElementById("link-destination").textContent = `Destino atual: ${link.destination_url}`;

  document.getElementById("stat-total").textContent = stats.total_clicks;

  drawLineChart(document.getElementById("clicks-chart"), stats.daily_clicks);
  renderTable("device-table", stats.device_breakdown, "device_type", DEVICE_LABELS);
  renderTable("referrer-table", stats.top_referrers, "referrer");
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  location.href = "/login.html";
});

initNav();
loadLinkDetail().catch((err) => console.error(err));
