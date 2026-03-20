export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export async function ingestDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/ingest`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to ingest document");
  }

  return await response.json();
}

export async function getMetrics() {
  const response = await fetch(`${API_BASE_URL}/metrics`);
  if (!response.ok) return null;
  return await response.json();
}

/**
 * Executes a streaming chat request.
 * Since the backend returns raw text (not SSE event prefixes),
 * we read the stream as a raw text body.
 */
export async function* streamChat(question: string, sessionId?: string) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error("Chat request failed");
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
