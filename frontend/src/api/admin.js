const ADMIN_TOKEN_KEY = "factory_ai_admin_token";

export function getStoredAdminToken() {
  return sessionStorage.getItem(ADMIN_TOKEN_KEY) || "";
}

export function storeAdminToken(token) {
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearAdminToken() {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
}

export async function adminLogin(password) {
  let response;

  try {
    response = await fetch("/api/admin/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password }),
    });
  } catch {
    throw new Error("无法连接后端管理接口");
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload, "管理员登录失败"));
  }

  return payload.admin_token;
}

export async function fetchAdminApiSummary(adminToken) {
  let response;

  try {
    response = await fetch("/api/admin/api-summary", {
      headers: {
        Authorization: `Bearer ${adminToken}`,
      },
    });
  } catch {
    throw new Error("无法连接后端管理接口");
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload, "读取 API 统计失败"));
  }

  return payload;
}

function getApiErrorMessage(payload, fallback) {
  return payload?.error?.message || payload?.detail || fallback;
}
