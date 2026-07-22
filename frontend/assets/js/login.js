document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = document.getElementById("error-msg");
  errorEl.textContent = "";

  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    await api.login(username, password);
    location.href = "/dashboard.html";
  } catch (err) {
    errorEl.textContent = err.message;
  }
});
