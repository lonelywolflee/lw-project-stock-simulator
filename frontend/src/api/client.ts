import type { BacktestParams, SSEEvent } from "./types";

/** SSE 원시 텍스트를 파싱한다. */
function parseSSE(raw: string): SSEEvent | null {
  let eventType = "message";
  const dataLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const dataStr = dataLines.join("\n");
  if (!dataStr) return null;

  try {
    return { type: eventType, data: JSON.parse(dataStr) } as SSEEvent;
  } catch {
    return null;
  }
}

/** 백테스트를 SSE 스트리밍으로 실행한다. */
export async function streamBacktest(
  params: BacktestParams,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const response = await fetch("/api/backtests/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error("ReadableStream not supported");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop()!;

    for (const chunk of chunks) {
      if (!chunk.trim()) continue;
      const event = parseSSE(chunk);
      if (event) onEvent(event);
    }
  }

  if (buffer.trim()) {
    const event = parseSSE(buffer);
    if (event) onEvent(event);
  }
}
