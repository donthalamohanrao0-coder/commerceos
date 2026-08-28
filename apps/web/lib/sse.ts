/** Minimal Server-Sent Events reader for a fetch `Response.body` stream.
 *  Each SSE frame is `data: <json>\n\n`; we yield the parsed JSON objects. */
export interface SseEvent {
  type: string;
  [key: string]: unknown;
}

export async function* readSse(stream: ReadableStream<Uint8Array>): AsyncGenerator<SseEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const data = frame
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim())
          .join("\n");
        if (!data) continue;
        try {
          yield JSON.parse(data) as SseEvent;
        } catch {
          /* ignore a malformed frame rather than break the stream */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
