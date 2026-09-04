let currentLinks = [];
let currentGroups = [];
let currentPartners = [];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderChipGroup(containerId, options) {
  const container = document.getElementById(containerId);
  container.innerHTML = options
    .map(
      (opt) =>
        `<button type="button" class="chip" data-value="${opt.value}"><span class="chip-check">✓</span>${escapeHtml(opt.label)}</button>`
    )
    .join("");
  container.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => setChipGroupValue(containerId, chip.dataset.value));
  });
}

function setChipGroupValue(containerId, value) {
  document.getElementById(containerId).querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("chip-selected", chip.dataset.value === value);
  });
}

function getChipGroupValue(containerId) {
  const selected = document.getElementById(containerId).querySelector(".chip-selected");
  return selected ? selected.dataset.value : "";
}

function renderLinks(links) {
  const tbody = document.getElementById("links-tbody");
  const emptyState = document.getElementById("empty-state");

  if (links.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  tbody.innerHTML = links
    .map((link) => {
      const statusBadge = link.is_active
        ? '<span class="badge badge-active">Ativo</span>'
        : '<span class="badge badge-inactive">Inativo</span>';

      return `
        <tr data-id="${link.id}">
          <td>
            <div>${escapeHtml(link.title) || "<em>Sem título</em>"}</div>
            <a class="short-link" href="${link.short_url}" target="_blank" rel="noopener">${link.short_url}</a>
          </td>
          <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(link.destination_url)}">
            ${escapeHtml(link.destination_url)}
          </td>
          <td>${escapeHtml(link.group_name) || "<em>Sem grupo</em>"}</td>
          <td>${escapeHtml(link.partner_name) || "<em>-</em>"}</td>
          <td><a href="/link-detail.html?id=${link.id}">${link.total_clicks}</a></td>
          <td>${statusBadge}</td>
          <td>
            <div class="actions-buttons">
              <button class="btn-secondary" data-action="stats" data-id="${link.id}">Stats</button>
              <button class="btn-secondary" data-action="qr" data-id="${link.id}">QR</button>
              <button class="btn-secondary" data-action="edit" data-id="${link.id}">Editar</button>
              <button class="btn-danger" data-action="delete" data-id="${link.id}">Excluir</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadLinks() {
  currentLinks = await api.listLinks();
  renderLinks(currentLinks);
}

async function loadGroups() {
  currentGroups = await api.listGroups();
  renderChipGroup(
    "link-group-chips",
    currentGroups.map((group) => ({ value: group.id, label: group.name }))
  );
}

async function loadPartners() {
  try {
    currentPartners = await api.listPartners();
  } catch (err) {
    currentPartners = [];
    return;
  }
  renderChipGroup("link-partner-chips", [
    { value: "", label: "Sem parceiro" },
    ...currentPartners.map((partner) => ({ value: partner.id, label: partner.name })),
  ]);
}

function setLinkType(type) {
  document.getElementById("link-type").value = type;

  const campaignBtn = document.getElementById("link-type-campaign-btn");
  const partnerBtn = document.getElementById("link-type-partner-btn");
  campaignBtn.classList.toggle("btn-primary", type === "campaign");
  campaignBtn.classList.toggle("btn-secondary", type !== "campaign");
  partnerBtn.classList.toggle("btn-primary", type === "partner");
  partnerBtn.classList.toggle("btn-secondary", type !== "partner");

  document.getElementById("generic-utm-box").classList.toggle("hidden", type !== "campaign");
  document.getElementById("partner-utm-box").classList.toggle("hidden", type !== "partner");
  document.getElementById("link-partner-section").classList.toggle("hidden", type !== "partner");
}

function resetPartnerUtmFields() {
  document.getElementById("partner-utm-campaign").value = "";
  setChipGroupValue("partner-utm-source-chips", "");
  document.getElementById("partner-utm-medium").value = "";
  setChipGroupValue("partner-utm-term-chips", "");
}

function openLinkModal(link = null) {
  const backdrop = document.getElementById("link-modal-backdrop");
  const title = document.getElementById("link-modal-title");
  const customCodeWrapper = document.getElementById("custom-code-wrapper");
  const activeWrapper = document.getElementById("active-wrapper");
  const errorMsg = document.getElementById("link-error-msg");

  document.getElementById("link-form").reset();
  resetUtmFields();
  resetPartnerUtmFields();
  errorMsg.textContent = "";

  if (link) {
    title.textContent = "Editar link";
    document.getElementById("link-id").value = link.id;
    document.getElementById("title").value = link.title || "";
    document.getElementById("destination-url").value = link.destination_url;
    document.getElementById("is-active").checked = link.is_active;
    setChipGroupValue("link-group-chips", link.group_id || "");
    setChipGroupValue("link-partner-chips", link.partner_id || "");
    document.getElementById("partner-utm-campaign").value = link.utm_campaign || "";
    setChipGroupValue("partner-utm-source-chips", link.utm_source || "");
    document.getElementById("partner-utm-medium").value = link.utm_medium || "";
    setChipGroupValue("partner-utm-term-chips", link.utm_term || "");
    customCodeWrapper.classList.add("hidden");
    activeWrapper.classList.remove("hidden");
    setLinkType(link.partner_id ? "partner" : "campaign");
  } else {
    title.textContent = "Novo link";
    document.getElementById("link-id").value = "";
    setChipGroupValue("link-group-chips", currentGroups[0] ? currentGroups[0].id : "");
    setChipGroupValue("link-partner-chips", "");
    customCodeWrapper.classList.remove("hidden");
    activeWrapper.classList.add("hidden");
    setLinkType("campaign");
  }

  backdrop.classList.remove("hidden");
}

function closeLinkModal() {
  document.getElementById("link-modal-backdrop").classList.add("hidden");
}

async function handleLinkFormSubmit(event) {
  event.preventDefault();
  const errorMsg = document.getElementById("link-error-msg");
  errorMsg.textContent = "";

  const id = document.getElementById("link-id").value;
  const title = document.getElementById("title").value.trim() || null;
  const destinationUrl = document.getElementById("destination-url").value.trim();
  const groupId = getChipGroupValue("link-group-chips");
  const linkType = document.getElementById("link-type").value;
  const partnerId = linkType === "partner" ? getChipGroupValue("link-partner-chips") : "";

  if (!groupId) {
    errorMsg.textContent = "Selecione um grupo";
    return;
  }
  if (linkType === "partner" && !partnerId) {
    errorMsg.textContent = "Selecione um parceiro";
    return;
  }

  const partnerUtm = linkType === "partner" && partnerId
    ? {
        utm_campaign: document.getElementById("partner-utm-campaign").value.trim() || null,
        utm_source: getChipGroupValue("partner-utm-source-chips") || null,
        utm_medium: document.getElementById("partner-utm-medium").value.trim() || null,
        utm_term: getChipGroupValue("partner-utm-term-chips") || null,
      }
    : {};

  try {
    if (id) {
      const isActive = document.getElementById("is-active").checked;
      await api.updateLink(id, {
        title,
        destination_url: destinationUrl,
        is_active: isActive,
        group_id: groupId,
        partner_id: partnerId || null,
        clear_partner: !partnerId,
        ...partnerUtm,
      });
    } else {
      const customCode = document.getElementById("custom-code").value.trim() || null;
      await api.createLink({
        title,
        destination_url: destinationUrl,
        custom_code: customCode,
        group_id: groupId,
        partner_id: partnerId || null,
        ...partnerUtm,
      });
    }
    closeLinkModal();
    await loadLinks();
  } catch (err) {
    errorMsg.textContent = err.message;
  }
}

function openQrModal(linkId) {
  const pngUrl = api.qrCodeUrl(linkId, "png");
  const svgUrl = api.qrCodeUrl(linkId, "svg");

  document.getElementById("qr-image").src = pngUrl;
  document.getElementById("qr-download-png").href = pngUrl;
  document.getElementById("qr-download-svg").href = svgUrl;
  document.getElementById("qr-modal-backdrop").classList.remove("hidden");
}

function closeQrModal() {
  document.getElementById("qr-modal-backdrop").classList.add("hidden");
}

async function handleDelete(linkId) {
  if (!confirm("Tem certeza que deseja excluir este link? Essa ação não pode ser desfeita.")) return;
  await api.deleteLink(linkId);
  await loadLinks();
}

function initTableActions() {
  document.getElementById("links-tbody").addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;

    const { action, id } = btn.dataset;
    const link = currentLinks.find((l) => l.id === id);

    if (action === "edit") openLinkModal(link);
    if (action === "qr") openQrModal(id);
    if (action === "stats") location.href = `/link-detail.html?id=${id}`;
    if (action === "delete") await handleDelete(id);
  });
}

function initModals() {
  document.getElementById("new-link-btn").addEventListener("click", () => openLinkModal());
  document.getElementById("cancel-link-btn").addEventListener("click", closeLinkModal);
  document.getElementById("link-form").addEventListener("submit", handleLinkFormSubmit);
  document.getElementById("close-qr-btn").addEventListener("click", closeQrModal);
  document.getElementById("link-type-campaign-btn").addEventListener("click", () => setLinkType("campaign"));
  document.getElementById("link-type-partner-btn").addEventListener("click", () => setLinkType("partner"));
}

const LINE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"];
const PIE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];

function renderMultiLineChart(canvas, series, tooltipEl, legendEl) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const gridColor = getComputedStyle(document.documentElement).getPropertyValue("--border").trim() || "#e8e3dd";
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim() || "#71757e";

  legendEl.innerHTML = series
    .map(
      (s, i) =>
        `<span class="legend-item"><span class="legend-dot" style="background:${LINE_COLORS[i]}"></span>${escapeHtml(s.label)}</span>`
    )
    .join("");

  const dates = series[0].data.map((d) => d.date);

  if (dates.length === 0) {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = mutedColor;
    ctx.font = "14px sans-serif";
    ctx.fillText("Sem dados de cliques ainda.", padding.left, height / 2);
    canvas.onmousemove = null;
    canvas.onmouseleave = null;
    tooltipEl.classList.add("hidden");
    return;
  }

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const stepX = dates.length > 1 ? plotWidth / (dates.length - 1) : 0;
  const maxCount = Math.max(1, ...series.flatMap((s) => s.data.map((d) => d.count)));

  const xOf = (index) => padding.left + index * stepX;
  const yOf = (count) => height - padding.bottom - (count / maxCount) * plotHeight;

  function draw(hoverIndex) {
    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, height - padding.bottom);
    ctx.lineTo(width - padding.right, height - padding.bottom);
    ctx.stroke();

    series.forEach((s, i) => {
      ctx.strokeStyle = LINE_COLORS[i];
      ctx.lineWidth = 2;
      ctx.beginPath();
      s.data.forEach((point, index) => {
        const x = xOf(index);
        const y = yOf(point.count);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.fillStyle = LINE_COLORS[i];
      s.data.forEach((point, index) => {
        ctx.beginPath();
        ctx.arc(xOf(index), yOf(point.count), 3, 0, Math.PI * 2);
        ctx.fill();
      });
    });

    ctx.fillStyle = mutedColor;
    ctx.font = "11px sans-serif";
    ctx.fillText(String(maxCount), 4, padding.top + 4);
    ctx.fillText("0", 4, height - padding.bottom);
    ctx.fillText(dates[0], padding.left, height - 8);
    const lastLabel = dates[dates.length - 1];
    ctx.fillText(lastLabel, width - padding.right - lastLabel.length * 6, height - 8);

    if (hoverIndex !== null) {
      const x = xOf(hoverIndex);
      ctx.strokeStyle = mutedColor;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, padding.top);
      ctx.lineTo(x, height - padding.bottom);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  draw(null);

  canvas.onmousemove = (event) => {
    const relativeX = event.offsetX - padding.left;
    let index = stepX > 0 ? Math.round(relativeX / stepX) : 0;
    index = Math.max(0, Math.min(dates.length - 1, index));
    draw(index);

    tooltipEl.style.left = `${xOf(index) + 8}px`;
    tooltipEl.style.top = "8px";
    tooltipEl.innerHTML =
      `<strong>${dates[index]}</strong><br>` +
      series
        .map(
          (s, i) =>
            `<span style="color:${LINE_COLORS[i]}">●</span> ${escapeHtml(s.label)}: ${s.data[index].count}`
        )
        .join("<br>");
    tooltipEl.classList.remove("hidden");
  };

  canvas.onmouseleave = () => {
    draw(null);
    tooltipEl.classList.add("hidden");
  };
}

function renderPieChart(canvas, legendEl, tooltipEl, topLinks) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) / 2 - 8;
  const mutedColor = getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim() || "#71757e";

  ctx.clearRect(0, 0, width, height);

  if (topLinks.length === 0) {
    ctx.fillStyle = mutedColor;
    ctx.font = "14px sans-serif";
    ctx.fillText("Sem dados de cliques ainda.", 10, height / 2);
    legendEl.innerHTML = "";
    canvas.onmousemove = null;
    canvas.onmouseleave = null;
    tooltipEl.classList.add("hidden");
    return;
  }

  const total = topLinks.reduce((sum, link) => sum + link.total_clicks, 0);

  let angleAcc = -Math.PI / 2;
  const slices = topLinks.map((link, i) => {
    const fraction = link.total_clicks / total;
    const startAngle = angleAcc;
    const endAngle = angleAcc + fraction * Math.PI * 2;
    angleAcc = endAngle;
    return { ...link, color: PIE_COLORS[i], startAngle, endAngle, fraction };
  });

  slices.forEach((slice) => {
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, slice.startAngle, slice.endAngle);
    ctx.closePath();
    ctx.fillStyle = slice.color;
    ctx.fill();
  });

  legendEl.innerHTML = slices
    .map((s) => {
      const title = s.title || "Sem título";
      const shortTitle = title.length > 24 ? `${title.slice(0, 24)}…` : title;
      return `<div class="legend-item"><span class="legend-dot" style="background:${s.color}"></span>${escapeHtml(shortTitle)} (${s.total_clicks})</div>`;
    })
    .join("");

  canvas.onmousemove = (event) => {
    const dx = event.offsetX - cx;
    const dy = event.offsetY - cy;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > radius) {
      tooltipEl.classList.add("hidden");
      return;
    }

    let angle = Math.atan2(dy, dx);
    if (angle < -Math.PI / 2) angle += Math.PI * 2;

    const hit = slices.find((s) => angle >= s.startAngle && angle < s.endAngle) || slices[slices.length - 1];

    tooltipEl.style.left = `${event.offsetX + 12}px`;
    tooltipEl.style.top = `${event.offsetY}px`;
    const pct = (hit.fraction * 100).toFixed(1);
    tooltipEl.innerHTML = `<strong>${escapeHtml(hit.title || "Sem título")}</strong><br>${hit.total_clicks} cliques (${pct}%)`;
    tooltipEl.classList.remove("hidden");
  };

  canvas.onmouseleave = () => tooltipEl.classList.add("hidden");
}

async function loadOverview() {
  const overview = await api.getDashboardOverview();

  renderMultiLineChart(
    document.getElementById("overview-line-chart"),
    [
      { label: "Total", data: overview.daily_clicks_total },
      { label: "Parceiros", data: overview.daily_clicks_partner },
      { label: "Gerais", data: overview.daily_clicks_general },
    ],
    document.getElementById("overview-line-tooltip"),
    document.getElementById("overview-line-legend")
  );

  renderPieChart(
    document.getElementById("overview-pie-chart"),
    document.getElementById("overview-pie-legend"),
    document.getElementById("overview-pie-tooltip"),
    overview.top_links
  );
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  location.href = "/login.html";
});

async function init() {
  initUtmBuilder();
  initModals();
  initTableActions();
  renderChipGroup("partner-utm-source-chips", [
    { value: "influencer", label: "Influencer" },
    { value: "marca_parceira", label: "Marca parceira" },
  ]);
  renderChipGroup("partner-utm-term-chips", [
    { value: "ig", label: "Instagram" },
    { value: "facebook", label: "Facebook" },
    { value: "youtube", label: "Youtube" },
    { value: "tiktok", label: "TikTok" },
    { value: "qrcode", label: "QR Code" },
  ]);
  await initNav();
  await loadGroups();
  await loadPartners();
  await loadLinks();
  await loadOverview();
}

init().catch((err) => console.error(err));
