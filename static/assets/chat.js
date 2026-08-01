const token = sessionStorage.getItem("rubato_token");
if (!token) {
  window.location.href = "/login";
}

const conversationId = crypto.randomUUID();
const chatLog = document.getElementById("chat-log");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const logoutBtn = document.getElementById("logout-btn");

function appendMessage({ role, text, intent, citations }) {
  const bubble = document.createElement("div");
  bubble.className = `msg ${role}`;
  bubble.textContent = text;

  if (intent && role === "bot") {
    const tag = document.createElement("div");
    tag.className = "intent-tag";
    tag.textContent = intent.replace(/_/g, " ");
    bubble.appendChild(tag);
  }

  if (citations && citations.length > 0) {
    const block = document.createElement("div");
    block.className = "citations";
    const label = document.createElement("div");
    label.textContent = "Sources:";
    const list = document.createElement("ul");
    citations.forEach((c) => {
      const li = document.createElement("li");
      li.textContent = c;
      list.appendChild(li);
    });
    block.appendChild(label);
    block.appendChild(list);
    bubble.appendChild(block);
  }

  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function logout() {
  sessionStorage.removeItem("rubato_token");
  window.location.href = "/login";
}

logoutBtn.addEventListener("click", logout);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage({ role: "user", text: message });
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;

  try {
    const response = await fetch("/support/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ conversation_id: conversationId, message }),
    });

    if (response.status === 401) {
      appendMessage({ role: "system", text: "Your session expired. Redirecting to login…" });
      setTimeout(logout, 1500);
      return;
    }

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      appendMessage({
        role: "system",
        text: detail && detail.detail ? detail.detail : `Something went wrong (${response.status}).`,
      });
      return;
    }

    const data = await response.json();
    appendMessage({ role: "bot", text: data.reply, intent: data.intent, citations: data.citations });
  } catch (err) {
    appendMessage({ role: "system", text: "Couldn't reach the server. Is the API running?" });
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
});
