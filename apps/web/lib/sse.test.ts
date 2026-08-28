import { describe, expect, it } from "vitest";

import { readSse, type SseEvent } from "./sse";

/** Build a ReadableStream that emits the given string chunks. */
function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<SseEvent[]> {
  const out: SseEvent[] = [];
  for await (const ev of readSse(stream)) out.push(ev);
  return out;
}

describe("readSse", () => {
  it("parses well-formed data frames", async () => {
    const events = await collect(
      streamOf(
        'data: {"type":"start"}\n\n',
        'data: {"type":"tool","tool":"catalog_search","status":"succeeded"}\n\n',
        'data: {"type":"done","assistant":"hi"}\n\n',
      ),
    );
    expect(events.map((e) => e.type)).toEqual(["start", "tool", "done"]);
    expect(events[1]).toMatchObject({ tool: "catalog_search", status: "succeeded" });
  });

  it("reassembles a frame split across chunk boundaries", async () => {
    const events = await collect(streamOf('data: {"type":"pla', 'nning","tools":["order_create"]}\n\n'));
    expect(events).toEqual([{ type: "planning", tools: ["order_create"] }]);
  });

  it("handles multiple frames arriving in one chunk", async () => {
    const events = await collect(streamOf('data: {"type":"a"}\n\ndata: {"type":"b"}\n\n'));
    expect(events.map((e) => e.type)).toEqual(["a", "b"]);
  });

  it("skips a malformed frame instead of throwing", async () => {
    const events = await collect(streamOf("data: not-json\n\n", 'data: {"type":"ok"}\n\n'));
    expect(events).toEqual([{ type: "ok" }]);
  });

  it("ignores a trailing partial frame with no terminator", async () => {
    const events = await collect(streamOf('data: {"type":"one"}\n\ndata: {"type":"tw'));
    expect(events).toEqual([{ type: "one" }]);
  });
});
