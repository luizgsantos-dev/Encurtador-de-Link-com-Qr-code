async function initNav() {
  try {
    const me = await api.me();
    if (me.is_admin) {
      document.querySelectorAll(".admin-only").forEach((el) => el.classList.remove("hidden"));
    }
    return me;
  } catch (err) {
    return null;
  }
}
