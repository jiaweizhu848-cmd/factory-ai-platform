export async function sendChat(messages) {
  let response;

  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages,
        temperature: 0.3,
        max_tokens: 512,
      }),
    });
  } catch {
    throw new Error("网络连接失败，请检查后端服务");
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }

  return payload;
}

export async function sendVision({ input, image, metadata }) {
  let response;

  try {
    response = await fetch("/api/api/v1/vision/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${metadata.apiToken || "factory-dev-token"}`,
      },
      body: JSON.stringify({
        input,
        caller: "browser-chat",
        image,
        metadata: {
          source: "browser-chat",
          file_name: metadata.fileName,
          file_type: metadata.fileType,
        },
        temperature: 0.2,
        max_tokens: 2048,
      }),
    });
  } catch {
    throw new Error("网络连接失败，请检查后端服务");
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }

  return {
    message: {
      role: "assistant",
      content: payload.answer,
    },
  };
}

function getErrorMessage(payload) {
  if (payload?.error?.message) {
    return payload.error.message;
  }

  const detail = payload?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        return item?.msg || item?.message || JSON.stringify(item);
      })
      .filter(Boolean)
      .join("；");
  }

  if (detail && typeof detail === "object") {
    return detail.message || detail.msg || JSON.stringify(detail);
  }

  return "聊天请求失败";
}
