let currentGroups = [];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderGroups(groups) {
  const tbody = document.getElementById("groups-tbody");
  const emptyState = document.getElementById("empty-state");

  if (groups.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  tbody.innerHTML = groups
    .map(
      (group) => `
        <tr data-id="${group.id}">
          <td>${escapeHtml(group.name)}</td>
          <td class="actions-cell">
            <button class="btn-secondary" data-action="edit" data-id="${group.id}">Editar</button>
            <button class="btn-danger" data-action="delete" data-id="${group.id}">Excluir</button>
          </td>
        </tr>
      `
    )
    .join("");
}

async function loadGroups() {
  currentGroups = await api.listGroups();
  renderGroups(currentGroups);
}

function openGroupModal(group = null) {
  const backdrop = document.getElementById("group-modal-backdrop");
  const title = document.getElementById("group-modal-title");
  const errorMsg = document.getElementById("group-error-msg");

  document.getElementById("group-form").reset();
  errorMsg.textContent = "";

  if (group) {
    title.textContent = "Editar grupo";
    document.getElementById("group-id").value = group.id;
    document.getElementById("group-name").value = group.name;
  } else {
    title.textContent = "Novo grupo";
    document.getElementById("group-id").value = "";
  }

  backdrop.classList.remove("hidden");
}

function closeGroupModal() {
  document.getElementById("group-modal-backdrop").classList.add("hidden");
}

async function handleGroupFormSubmit(event) {
  event.preventDefault();
  const errorMsg = document.getElementById("group-error-msg");
  errorMsg.textContent = "";

  const id = document.getElementById("group-id").value;
  const name = document.getElementById("group-name").value.trim();

  try {
    if (id) {
      await api.updateGroup(id, { name });
    } else {
      await api.createGroup({ name });
    }
    closeGroupModal();
    await loadGroups();
  } catch (err) {
    errorMsg.textContent = err.message;
  }
}

async function handleDelete(groupId) {
  if (!confirm("Tem certeza que deseja excluir este grupo? Links associados ficarão sem grupo.")) return;
  try {
    await api.deleteGroup(groupId);
    await loadGroups();
  } catch (err) {
    alert(err.message);
  }
}

function initTableActions() {
  document.getElementById("groups-tbody").addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;

    const { action, id } = btn.dataset;
    const group = currentGroups.find((g) => g.id === id);

    if (action === "edit") openGroupModal(group);
    if (action === "delete") await handleDelete(id);
  });
}

function initModals() {
  document.getElementById("new-group-btn").addEventListener("click", () => openGroupModal());
  document.getElementById("cancel-group-btn").addEventListener("click", closeGroupModal);
  document.getElementById("group-form").addEventListener("submit", handleGroupFormSubmit);
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
  await loadGroups();
}

init().catch((err) => console.error(err));
