export type ChatResponse = {
  question: string;
  type: "structured" | "unstructured" | "hybrid" | "unknown";
  answer?: unknown;
  plan?: unknown;
  sources?: unknown[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function sendChat(question: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question})
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}