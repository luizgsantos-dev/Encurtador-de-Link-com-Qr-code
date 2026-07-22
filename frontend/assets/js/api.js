const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (response.status === 401) {
    if (!location.pathname.endsWith("login.html")) {
      location.href = "/login.html";
    }
    throw new Error("Não autenticado");
  }

  if (!response.ok) {
    let detail = "Erro na requisição";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // corpo vazio ou não-JSON, mantém mensagem padrão
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

const api = {
  login: (username, password) =>
    apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => apiRequest("/auth/logout", { method: "POST" }),
  me: () => apiRequest("/auth/me"),
  listLinks: () => apiRequest("/links"),
  getLink: (id) => apiRequest(`/links/${id}`),
  createLink: (payload) => apiRequest("/links", { method: "POST", body: JSON.stringify(payload) }),
  updateLink: (id, payload) =>
    apiRequest(`/links/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteLink: (id) => apiRequest(`/links/${id}`, { method: "DELETE" }),
  getStats: (id) => apiRequest(`/links/${id}/stats`),
  qrCodeUrl: (id, format = "png") => `${API_BASE}/links/${id}/qrcode?format=${format}`,
  listGroups: () => apiRequest("/groups"),
  createGroup: (payload) => apiRequest("/groups", { method: "POST", body: JSON.stringify(payload) }),
  updateGroup: (id, payload) =>
    apiRequest(`/groups/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteGroup: (id) => apiRequest(`/groups/${id}`, { method: "DELETE" }),
  listUsers: () => apiRequest("/users"),
  createUser: (payload) => apiRequest("/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id, payload) =>
    apiRequest(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteUser: (id) => apiRequest(`/users/${id}`, { method: "DELETE" }),
};
