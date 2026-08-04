const token = sessionStorage.getItem("rubato_staff_token");
if (!token) {
  window.location.href = "/admin";
}

const logoutBtn = document.getElementById("logout-btn");
const approvalsList = document.getElementById("approvals-list");
const approvalsStatus = document.getElementById("approvals-status");
const productsBody = document.getElementById("products-body");
const productsStatus = document.getElementById("products-status");

function logout() {
  sessionStorage.removeItem("rubato_staff_token");
  window.location.href = "/admin";
}

logoutBtn.addEventListener("click", logout);

function authedFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

function handleSessionExpired(statusBox) {
  statusBox.textContent = "Your session expired. Redirecting to login…";
  setTimeout(logout, 1500);
}

function renderApproval(approval) {
  const card = document.createElement("div");
  card.className = "approval-card";

  const info = document.createElement("div");
  info.className = "approval-info";
  info.innerHTML = `
    <div><strong>Order:</strong> ${approval.payload.order_id}</div>
    <div><strong>Reason:</strong> ${approval.payload.reason}</div>
  `;

  const actions = document.createElement("div");
  actions.className = "approval-actions";

  const approveBtn = document.createElement("button");
  approveBtn.type = "button";
  approveBtn.className = "btn-approve";
  approveBtn.textContent = "Approve";
  approveBtn.addEventListener("click", () => resolveApproval(approval.id, "approve"));

  const denyBtn = document.createElement("button");
  denyBtn.type = "button";
  denyBtn.className = "btn-deny";
  denyBtn.textContent = "Deny";
  denyBtn.addEventListener("click", () => {
    const reason = window.prompt("Reason for denying this refund request:");
    if (reason === null || reason.trim() === "") return;
    resolveApproval(approval.id, "deny", reason.trim());
  });

  actions.appendChild(approveBtn);
  actions.appendChild(denyBtn);
  card.appendChild(info);
  card.appendChild(actions);
  return card;
}

async function resolveApproval(approvalId, action, reason) {
  approvalsStatus.textContent = "";
  try {
    const response = await authedFetch(`/approvals/${approvalId}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: action === "deny" ? JSON.stringify({ reason }) : undefined,
    });

    if (response.status === 401) {
      handleSessionExpired(approvalsStatus);
      return;
    }

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      approvalsStatus.textContent = detail && detail.detail ? detail.detail : `Action failed (${response.status}).`;
      return;
    }

    await loadApprovals();
  } catch (err) {
    approvalsStatus.textContent = "Couldn't reach the server. Is the API running?";
  }
}

async function loadApprovals() {
  try {
    const response = await authedFetch("/approvals");

    if (response.status === 401) {
      handleSessionExpired(approvalsStatus);
      return;
    }

    if (!response.ok) {
      approvalsStatus.textContent = `Couldn't load approvals (${response.status}).`;
      return;
    }

    const approvals = await response.json();
    approvalsList.innerHTML = "";
    approvalsStatus.textContent = "";

    if (approvals.length === 0) {
      approvalsStatus.textContent = "No pending approvals.";
      return;
    }

    approvals.forEach((approval) => approvalsList.appendChild(renderApproval(approval)));
  } catch (err) {
    approvalsStatus.textContent = "Couldn't reach the server. Is the API running?";
  }
}

function renderProductRow(product) {
  const row = document.createElement("tr");

  const priceInput = document.createElement("input");
  priceInput.type = "number";
  priceInput.step = "0.01";
  priceInput.min = "0";
  priceInput.value = product.price;

  const stockInput = document.createElement("input");
  stockInput.type = "number";
  stockInput.step = "1";
  stockInput.min = "0";
  stockInput.value = product.stock;

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "btn-save";
  saveBtn.textContent = "Save";
  saveBtn.addEventListener("click", () =>
    saveProduct(product.id, {
      price: parseFloat(priceInput.value),
      stock: parseInt(stockInput.value, 10),
    })
  );

  const nameCell = document.createElement("td");
  nameCell.textContent = product.name;
  const categoryCell = document.createElement("td");
  categoryCell.textContent = product.category;
  const sizeCell = document.createElement("td");
  sizeCell.textContent = product.size || "—";
  const priceCell = document.createElement("td");
  priceCell.appendChild(priceInput);
  const stockCell = document.createElement("td");
  stockCell.appendChild(stockInput);
  const actionCell = document.createElement("td");
  actionCell.appendChild(saveBtn);

  row.appendChild(nameCell);
  row.appendChild(categoryCell);
  row.appendChild(sizeCell);
  row.appendChild(priceCell);
  row.appendChild(stockCell);
  row.appendChild(actionCell);
  return row;
}

async function saveProduct(productId, fields) {
  productsStatus.textContent = "";
  try {
    const response = await authedFetch(`/products/${productId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    });

    if (response.status === 401) {
      handleSessionExpired(productsStatus);
      return;
    }

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      productsStatus.textContent = detail && detail.detail ? detail.detail : `Save failed (${response.status}).`;
      return;
    }

    productsStatus.textContent = "Saved.";
  } catch (err) {
    productsStatus.textContent = "Couldn't reach the server. Is the API running?";
  }
}

async function loadProducts() {
  try {
    const response = await authedFetch("/products");

    if (response.status === 401) {
      handleSessionExpired(productsStatus);
      return;
    }

    if (!response.ok) {
      productsStatus.textContent = `Couldn't load products (${response.status}).`;
      return;
    }

    const products = await response.json();
    productsBody.innerHTML = "";
    products.forEach((product) => productsBody.appendChild(renderProductRow(product)));
  } catch (err) {
    productsStatus.textContent = "Couldn't reach the server. Is the API running?";
  }
}

loadApprovals();
loadProducts();
