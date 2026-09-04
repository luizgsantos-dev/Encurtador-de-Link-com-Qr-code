let currentUsers = [];
let currentGroups = [];

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

function renderUsers(users) {
  const tbody = document.getElementById("users-tbody");
  const emptyState = document.getElementById("empty-state");

  if (users.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  tbody.innerHTML = users
    .map((user) => {
      const groupNames = user.groups.map((g) => escapeHtml(g.name)).join(", ") || "<em>Nenhum</em>";
      const roleBadge = user.is_admin
        ? '<span class="badge badge-active">Admin</span>'
        : '<span class="badge badge-inactive">Usuário</span>';
      const statusBadge = user.is_active
        ? '<span class="badge badge-active">Ativo</span>'
        : '<span class="badge badge-inactive">Inativo</span>';

      return `
        <tr data-id="${user.id}">
          <td>${escapeHtml(user.username)}</td>
          <td>${groupNames}</td>
          <td>${roleBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <div class="actions-buttons">
              <button class="btn-secondary" data-action="edit" data-id="${user.id}">Editar</button>
              <button class="btn-danger" data-action="delete" data-id="${user.id}">Excluir</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function loadUsers() {
  currentUsers = await api.listUsers();
  renderUsers(currentUsers);
}

async function loadGroupCheckboxes(selectedIds = []) {
  currentGroups = await api.listGroups();
  const container = document.getElementById("groups-checkboxes");
  container.innerHTML = currentGroups
    .map(
      (group) => `
        <label>
          <input type="checkbox" value="${group.id}" ${selectedIds.includes(group.id) ? "checked" : ""} />
          ${escapeHtml(group.name)}
        </label>
      `
    )
    .join("");
}

function openUserModal(user = null) {
  const backdrop = document.getElementById("user-modal-backdrop");
  const title = document.getElementById("user-modal-title");
  const usernameInput = document.getElementById("username");
  const passwordHint = document.getElementById("password-hint");
  const activeWrapper = document.getElementById("active-wrapper");
  const errorMsg = document.getElementById("user-error-msg");

  document.getElementById("user-form").reset();
  errorMsg.textContent = "";

  if (user) {
    title.textContent = "Editar usuário";
    document.getElementById("user-id").value = user.id;
    usernameInput.value = user.username;
    usernameInput.disabled = true;
    passwordHint.textContent = "(deixe em branco para manter a atual)";
    document.getElementById("is-admin").checked = user.is_admin;
    document.getElementById("is-active").checked = user.is_active;
    activeWrapper.classList.remove("hidden");
    loadGroupCheckboxes(user.groups.map((g) => g.id));
  } else {
    title.textContent = "Novo usuário";
    document.getElementById("user-id").value = "";
    usernameInput.disabled = false;
    passwordHint.textContent = "";
    activeWrapper.classList.add("hidden");
    loadGroupCheckboxes([]);
  }

  backdrop.classList.remove("hidden");
}

function closeUserModal() {
  document.getElementById("user-modal-backdrop").classList.add("hidden");
}

function getSelectedGroupIds() {
  return Array.from(document.querySelectorAll("#groups-checkboxes input:checked")).map(
    (el) => el.value
  );
}

async function handleUserFormSubmit(event) {
  event.preventDefault();
  const errorMsg = document.getElementById("user-error-msg");
  errorMsg.textContent = "";

  const id = document.getElementById("user-id").value;
  const password = document.getElementById("password").value;
  const isAdmin = document.getElementById("is-admin").checked;
  const groupIds = getSelectedGroupIds();

  try {
    if (id) {
      const payload = {
        is_admin: isAdmin,
        group_ids: groupIds,
        is_active: document.getElementById("is-active").checked,
      };
      if (password) payload.password = password;
      await api.updateUser(id, payload);
    } else {
      const username = document.getElementById("username").value.trim();
      if (!password) {
        errorMsg.textContent = "Senha é obrigatória para novos usuários.";
        return;
      }
      await api.createUser({ username, password, is_admin: isAdmin, group_ids: groupIds });
    }
    closeUserModal();
    await loadUsers();
  } catch (err) {
    errorMsg.textContent = err.message;
  }
}

async function handleDelete(userId) {
  if (!confirm("Tem certeza que deseja excluir este usuário?")) return;
  try {
    await api.deleteUser(userId);
    await loadUsers();
  } catch (err) {
    alert(err.message);
  }
}

function initTableActions() {
  document.getElementById("users-tbody").addEventListener("click", async (event) => {
    const btn = event.target.closest("button[data-action]");
    if (!btn) return;

    const { action, id } = btn.dataset;
    const user = currentUsers.find((u) => u.id === id);

    if (action === "edit") openUserModal(user);
    if (action === "delete") await handleDelete(id);
  });
}

function initModals() {
  document.getElementById("new-user-btn").addEventListener("click", () => openUserModal());
  document.getElementById("cancel-user-btn").addEventListener("click", closeUserModal);
  document.getElementById("user-form").addEventListener("submit", handleUserFormSubmit);
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
  await loadUsers();
}

init().catch((err) => console.error(err));
