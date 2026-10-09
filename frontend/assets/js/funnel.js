function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

// etapas na ordem do funil; cada taxa é em relação à etapa anterior
const STAGES = [
  { key: "clicks", label: "Cliques" },
  { key: "accesses", label: "Acessos ao site" },
  { key: "leads", label: "Leads" },
  { key: "appointments", label: "Agendamentos" },
  { key: "visits", label: "Visitas" },
  { key: "sales", label: "Vendas" },
];

let funnelRows = [];

function formatNumber(value) {
  return Number(value || 0).toLocaleString("pt-BR");
}

function formatRate(value, previous) {
  if (!previous) return "–";
  return `${((value / previous) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

function sumRows(rows) {
  const total = {};
  STAGES.forEach((stage) => {
    total[stage.key] = rows.reduce((acc, row) => acc + row[stage.key], 0);
  });
  return total;
}

function rowLabel(row) {
  return row.name || row.title || row.short_code;
}

function renderFunnel(totals) {
  const container = document.getElementById("funnel");
  container.innerHTML = STAGES.map((stage, index) => {
    const previous = index > 0 ? totals[STAGES[index - 1].key] : null;
    const width = 100 - index * 10;
    const rate =
      index > 0
        ? `<div class="funnel-rate"><strong>${formatRate(totals[stage.key], previous)}</strong><span>de ${escapeHtml(
            STAGES[index - 1].label.toLowerCase()
          )}</span></div>`
        : '<div class="funnel-rate"></div>';
    return `
      <div class="funnel-row">
        <div class="funnel-step" style="width:${width}%">
          <div class="funnel-value">${formatNumber(totals[stage.key])}</div>
          <div class="funnel-label">${escapeHtml(stage.label)}</div>
        </div>
        ${rate}
      </div>`;
  }).join("");
}

function tableCells(values) {
  return STAGES.map((stage, index) => {
    const value = `<td>${formatNumber(values[stage.key])}</td>`;
    if (index === 0) return value;
    return `${value}<td>${formatRate(values[stage.key], values[STAGES[index - 1].key])}</td>`;
  }).join("");
}

function renderTable(rows, totals) {
  const tbody = document.getElementById("funnel-tbody");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" style="color:var(--text-muted);">Nenhum link.</td></tr>`;
  } else {
    tbody.innerHTML = rows
      .slice()
      .sort((a, b) => b.clicks - a.clicks)
      .map(
        (row) => `
        <tr>
          <td>
            <div>${escapeHtml(rowLabel(row))}</div>
            <a class="short-link" href="/link-detail.html?id=${row.link_id}">${escapeHtml(row.short_url)}</a>
          </td>
          ${tableCells(row)}
        </tr>`
      )
      .join("");
  }
  document.getElementById("funnel-tfoot").innerHTML = `
    <tr class="funnel-total"><td>Total</td>${tableCells(totals)}</tr>`;
}

function render() {
  const selected = document.getElementById("funnel-link").value;
  const rows = selected ? funnelRows.filter((row) => row.link_id === selected) : funnelRows;
  const totals = sumRows(rows);
  renderFunnel(totals);
  renderTable(rows, totals);
}

function fillLinkSelect(rows) {
  const select = document.getElementById("funnel-link");
  const current = select.value;
  select.innerHTML =
    '<option value="">Todos</option>' +
    rows
      .slice()
      .sort((a, b) => rowLabel(a).localeCompare(rowLabel(b), "pt-BR"))
      .map((row) => `<option value="${row.link_id}">${escapeHtml(rowLabel(row))}</option>`)
      .join("");
  if (rows.some((row) => row.link_id === current)) select.value = current;
}

async function loadFunnel() {
  const start = document.getElementById("funnel-start").value;
  const end = document.getElementById("funnel-end").value;
  const errorEl = document.getElementById("funnel-error");
  errorEl.textContent = "";
  try {
    const data = await api.getFunnel({ start, end });
    funnelRows = data.rows;
    if (!data.crm_available) {
      errorEl.textContent = `${data.crm_error}. Exibindo só os cliques.`;
    }
    fillLinkSelect(funnelRows);
    render();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

document.getElementById("funnel-link").addEventListener("change", render);
document.getElementById("funnel-start").addEventListener("change", loadFunnel);
document.getElementById("funnel-end").addEventListener("change", loadFunnel);
document.getElementById("funnel-clear").addEventListener("click", () => {
  document.getElementById("funnel-start").value = "";
  document.getElementById("funnel-end").value = "";
  loadFunnel();
});
document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  location.href = "/login.html";
});

initNav();
loadFunnel();
