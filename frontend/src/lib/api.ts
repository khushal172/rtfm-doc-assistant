const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_URL = rawApiUrl.endsWith("/") ? rawApiUrl.slice(0, -1) : rawApiUrl;

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

/**
 * Executes a streaming chat request.
 */
export async function* streamChat(question: string, token: string, sessionId?: string, brainId: string = "default") {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId
    },
    body: JSON.stringify({ question, session_id: sessionId }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Chat request failed" }));
    throw new Error(errorData.detail || "Chat request failed");
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    yield decoder.decode(value, { stream: true });
  }
}

export async function ingestDocument(file: File, token: string, version?: string, brainId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (version) formData.append("version", version);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId || "default"
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to ingest document");
  }

  return await response.json();
}

export async function getMetrics(token: string, brainId?: string) {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId || "default"
    }
  });
  if (!response.ok) return null;
  return await response.json();
}

export async function listDocuments(token: string, brainId?: string) {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId || "default"
    }
  });
  if (!response.ok) return [];
  return await response.json();
}

export async function deleteDocument(filename: string, token: string, brainId: string = "default") {
  const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId
    }
  });
  if (!response.ok) throw new Error("Failed to delete document");
  return await response.json();
}

export async function bulkDeleteDocuments(filenames: string[], token: string, brainId: string = "default") {
  const response = await fetch(`${API_BASE_URL}/documents/bulk`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId
    },
    body: JSON.stringify({ filenames })
  });
  if (!response.ok) throw new Error("Failed to delete selected documents");
  return await response.json();
}

export async function deleteAllDocuments(token: string, brainId: string = "default") {
  const response = await fetch(`${API_BASE_URL}/documents/bulk?all=true`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId
    }
  });
  if (!response.ok) throw new Error("Failed to delete all documents");
  return await response.json();
}

export async function listBrains(token: string) {
  const response = await fetch(`${API_BASE_URL}/brains`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!response.ok) return ["default"];
  return await response.json();
}

export async function createBrain(brainId: string, token: string) {
  const response = await fetch(`${API_BASE_URL}/brains/${encodeURIComponent(brainId)}`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });
  return await response.ok;
}

export async function deleteBrain(brainId: string, token: string) {
  const response = await fetch(`${API_BASE_URL}/brains/${encodeURIComponent(brainId)}`, {
    method: "DELETE",
    headers: { "Authorization": `Bearer ${token}` }
  });
  return await response.ok;
}

export async function ingestGithub(repoUrl: string, token: string, brainId: string = "default", githubToken?: string) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

  try {
    const response = await fetch(`${API_BASE_URL}/ingest-github?url=${encodeURIComponent(repoUrl)}&brain_id=${brainId}`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "X-Brain-Id": brainId || "default",
        ...(githubToken ? { "github-token": githubToken } : {})
      },
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error("Failed to start GitHub ingestion");
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function getIngestStatus(token: string) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

  try {
    // Add a timestamp to bypass any browser/proxy caching
    const response = await fetch(`${API_BASE_URL}/ingest-status?t=${Date.now()}`, {
      headers: { "Authorization": `Bearer ${token}` },
      signal: controller.signal,
      cache: "no-store"
    });
    if (!response.ok) return { status: "idle" };
    return await response.json();
  } catch (err) {
    console.error("[API] Status fetch aborted or failed:", err);
    return { status: "idle" };
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function clearCache(token: string, brainId: string = "default") {
  const response = await fetch(`${API_BASE_URL}/cache`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
      "X-Brain-Id": brainId
    }
  });
  if (!response.ok) throw new Error("Failed to clear cache");
  return await response.json();
}
