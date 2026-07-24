let currentLinks = [];
let currentGroups = [];
let currentPartners = [];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
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
          <td class="actions-cell">
            <button class="btn-secondary" data-action="stats" data-id="${link.id}">Stats</button>
            <button class="btn-secondary" data-action="qr" data-id="${link.id}">QR</button>
            <button class="btn-secondary" data-action="edit" data-id="${link.id}">Editar</button>
            <button class="btn-danger" data-action="delete" data-id="${link.id}">Excluir</button>
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
  const select = document.getElementById("link-group");
  select.innerHTML = currentGroups
    .map((group) => `<option value="${group.id}">${escapeHtml(group.name)}</option>`)
    .join("");
}

async function loadPartners() {
  try {
    currentPartners = await api.listPartners();
  } catch (err) {
    currentPartners = [];
    return;
  }
  const select = document.getElementById("link-partner");
  select.innerHTML =
    '<option value="">Sem parceiro</option>' +
    currentPartners
      .map((partner) => `<option value="${partner.id}">${escapeHtml(partner.name)}</option>`)
      .join("");
}

function togglePartnerUtmBox() {
  const partnerId = document.getElementById("link-partner").value;
  document.getElementById("partner-utm-box").classList.toggle("hidden", !partnerId);
}

function resetPartnerUtmFields() {
  document.getElementById("partner-utm-campaign").value = "";
  document.getElementById("partner-utm-source").value = "";
  document.getElementById("partner-utm-medium").value = "";
  document.getElementById("partner-utm-term").value = "";
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
    document.getElementById("link-group").value = link.group_id || "";
    document.getElementById("link-partner").value = link.partner_id || "";
    document.getElementById("partner-utm-campaign").value = link.utm_campaign || "";
    document.getElementById("partner-utm-source").value = link.utm_source || "";
    document.getElementById("partner-utm-medium").value = link.utm_medium || "";
    document.getElementById("partner-utm-term").value = link.utm_term || "";
    customCodeWrapper.classList.add("hidden");
    activeWrapper.classList.remove("hidden");
  } else {
    title.textContent = "Novo link";
    document.getElementById("link-id").value = "";
    customCodeWrapper.classList.remove("hidden");
    activeWrapper.classList.add("hidden");
  }

  togglePartnerUtmBox();
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
  const groupId = document.getElementById("link-group").value;
  const partnerId = document.getElementById("link-partner").value;
  const partnerUtm = partnerId
    ? {
        utm_campaign: document.getElementById("partner-utm-campaign").value.trim() || null,
        utm_source: document.getElementById("partner-utm-source").value || null,
        utm_medium: document.getElementById("partner-utm-medium").value.trim() || null,
        utm_term: document.getElementById("partner-utm-term").value || null,
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
  document.getElementById("link-partner").addEventListener("change", togglePartnerUtmBox);
}

document.getElementById("logout-btn").addEventListener("click", async () => {
  await api.logout();
  location.href = "/login.html";
});

async function init() {
  initUtmBuilder();
  initModals();
  initTableActions();
  await initNav();
  await loadGroups();
  await loadPartners();
  await loadLinks();
}

init().catch((err) => console.error(err));
