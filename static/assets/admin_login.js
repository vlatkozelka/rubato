const form = document.getElementById("login-form");
const errorBox = document.getElementById("error-box");
const submitBtn = document.getElementById("submit-btn");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.add("visible");
}

function hideError() {
  errorBox.classList.remove("visible");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  submitBtn.disabled = true;
  submitBtn.textContent = "Signing in…";

  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const response = await fetch("/auth/staff/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      showError(detail && detail.detail ? detail.detail : `Login failed (${response.status}).`);
      return;
    }

    const data = await response.json();
    sessionStorage.setItem("rubato_staff_token", data.access_token);
    window.location.href = "/admin/dashboard";
  } catch (err) {
    showError("Couldn't reach the server. Is the API running?");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Log in";
  }
});
