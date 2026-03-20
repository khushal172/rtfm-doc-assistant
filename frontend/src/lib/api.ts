export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

/**
 * Executes a streaming chat request.
 */
export async function* streamChat(question: string, token: string, sessionId?: string) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
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

export async function ingestDocument(file: File, token: string, version?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (version) formData.append("version", version);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to ingest document");
  }

  return await response.json();
}

export async function getMetrics(token: string) {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });
  if (!response.ok) return null;
  return await response.json();
}

export async function listDocuments(token: string) {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });
  if (!response.ok) return [];
  return await response.json();
}
