let currentPartners = [];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderPartners(partners) {
  const tbody = document.getElementById("partners-tbody");
  const emptyState = document.getElementById("empty-state");

  if (partners.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  tbody.innerHTML = partners
    .map((partner) => {
      const statusBadge = partner.is_active
        ? '<span class="badge badge-active">Ativo</span>'
        : '<span class="badge badge-inactive">Inativo</span>';
      const contact = [partner.email, partner.phone].filter(Boolean).map(escapeHtml).join(" · ");

      return `
        <tr data-id="${partner.id}">
          <td>${escapeHtml(partner.name)}</td>
          <td>${contact || "<em>-</em>"}</td>
          <td>${partner.total_links}</td>
          <td>${partner.total_clicks}</td>
          <td>${statusBadge}</td>
          <td>
            <div class="actions-buttons">
              <button class="btn-secondary" data-action="stats" data-id="${partner.id}">Métricas</button>
              <button class="btn-secondary" data-action="edit" data-id="${partner.id}">Editar</button>
              <button class="btn-danger" data-action="delete" data-id="${partner.id}">Excluir</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadPartners() {
  currentPartners = await api.listPartners();
  renderPartners(currentPartners);
}

function openPartnerModal(partner = null) {
  const backdrop = document.getElementById("partner-modal-backdrop");
  const title = document.getElementById("partner-modal-title");
  const activeWrapper = document.getElementById("active-wrapper");
  const errorMsg = document.getElementById("partner-error-msg");

  document.getElementById("partner-form").reset();
  errorMsg.textContent = "";

  if (partner) {
    title.textContent = "Editar parceiro";
    document.getElementById("partner-id").value = partner.id;
    document.getElementById("partner-name").value = partner.name;
    document.getElementById("partner-social").value = partner.social_media || "";
    document.getElementById("partner-email").value = partner.email || "";
    document.getElementById("partner-phone").value = partner.phone || "";
    document.getElementById("partner-description").value = partner.description || "";
    document.getElementById("partner-partnership").value = partner.partnership || "";
    document.getElementById("partner-domain").value = partner.domain || "";
    document.getElementById("is-active").checked = partner.is_active;
    activeWrapper.classList.remove("hidden");
  } else {
    title.textContent = "Novo parceiro";
    document.getElementById("partner-id").value = "";
    activeWrapper.classList.add("hidden");
  }

  backdrop.classList.remove("hidden");
}

function closePartnerModal() {
  document.getElementById("partner-modal-backdrop").classList.add("hidden");
}

async function handlePartnerFormSubmit(event) {
  event.preventDefault();
  const errorMsg = document.getElementById("partner-error-msg");
  errorMsg.textContent = "";

  const id = document.getElementById("partner-id").value;
  const domain = document.getElementById("partner-domain").value.trim() || null;
  const payload = {
    name: document.getElementById("partner-name").value.trim(),
    social_media: document.getElementById("partner-social").value.trim() || null,
    email: document.getElementById("partner-email").value.trim() || null,
    phone: document.getElementById("partner-phone").value.trim() || null,
    description: document.getElementById("partner-description").value.trim() || null,
    partnership: document.getElementById("partner-partnership").value.trim() || null,
    domain,
  };

  try {
    if (id) {
      payload.is_active = document.getElementById("is-active").checked;
      payload.clear_domain = !domain;
      await api.updatePartner(id, payload);
    } else {
      await api.createPartner(payload);
    }
    closePartnerModal();
    await loadPartners();
  } catch (err) {
    errorMsg.textContent = err.message;
  }
}

async function handleDelete(partnerId) {
  if (!confirm("Tem certeza que deseja excluir este parceiro? Os links associados ficarão sem parceiro.")) return;
  try {
    await api.deletePartner(partnerId);
    await loadPartners();
  } catch (err) {
    alert(err.message);
  }
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

  ctx.strokeStyle = "#e2e5ea";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();

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

  ctx.fillStyle = "#4f46e5";
  dailyClicks.forEach((point, index) => {
    const x = padding.left + index * stepX;
    const y = height - padding.bottom - (point.count / maxCount) * plotHeight;
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = "#6b7280";
  ctx.font = "11px sans-serif";
  ctx.fillText(String(maxCount), 4, padding.top + 4);
  ctx.fillText("0", 4, height - padding.bottom);

  ctx.fillText(dailyClicks[0].date, padding.left, height - 8);
  const lastLabel = dailyClicks[dailyClicks.length - 1].date;
  ctx.fillText(lastLabel, width - padding.right - lastLabel.length * 6, height - 8);
}

async function openPartnerStats(partnerId) {
  const partner = currentPartners.find((p) => p.id === partnerId);
  const stats = await api.getPartnerStats(partnerId);

  document.getElementById("partner-stats-title").textContent = `Métricas de ${partner ? partner.name : ""}`;
  document.getElementById("partner-stat-total").textContent = stats.total_clicks;
  drawLineChart(document.getElementById("partner-clicks-chart"), stats.daily_clicks);

  const tbody = document.querySelector("#partner-links-table tbody");
  if (stats.links.length === 0) {
    tbody.innerHTML = '<tr><td colspan="2" style="color:var(--text-muted);">Nenhum link associado ainda.</td></tr>';
  } else {
    tbody.innerHTML = stats.links
      .map(
        (link) => `
          <tr>
            <td>
              <div>${escapeHtml(link.title) || "<em>Sem título</em>"}</div>
              <a class="short-link" href="${link.short_url}" target="_blank" rel="noopener">${link.short_url}</a>
            </td>
            <td>${link.total_clicks}</td>
          </tr>
        `
      )
      .join("");
  }

  document.getElementById("partner-stats-backdrop").classList.remove("hidden");
}

function closePartnerStats() {
  document.getElementById("partner-stats-backdrop").classList.add("hidden");
}

function initTableActions() {
  document.getElementById("partners-tbody").addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-action]");
    if (!btn) return;
    event.preventDefault();

    const { action, id } = btn.dataset;

    if (action === "edit") openPartnerModal(currentPartners.find((p) => p.id === id));
    if (action === "delete") await handleDelete(id);
    if (action === "stats") await openPartnerStats(id);
  });
}

function initModals() {
  document.getElementById("new-partner-btn").addEventListener("click", () => openPartnerModal());
  document.getElementById("cancel-partner-btn").addEventListener("click", closePartnerModal);
  document.getElementById("partner-form").addEventListener("submit", handlePartnerFormSubmit);
  document.getElementById("close-partner-stats-btn").addEventListener("click", closePartnerStats);
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  location.href = "/login.html";
});

async function init() {
  const me = await initNav();
  if (!me || !me.is_admin) {
    location.href = "/dashboard.html";
    return;
  }
  initModals();
  initTableActions();
  await loadPartners();
}

init().catch((err) => console.error(err));
