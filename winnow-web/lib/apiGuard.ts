import { NextRequest, NextResponse } from "next/server";

// Dependency-free in-memory rate limiter + request guards.
// NOTE: in-memory state is per-instance. On multi-instance/serverless deploys,
// swap in a shared store (e.g. @upstash/ratelimit) — the call sites stay the same.
const WINDOW_MS = Number(process.env.RATE_LIMIT_WINDOW_MS ?? 60_000);
const MAX_REQ = Number(process.env.RATE_LIMIT_MAX ?? 20);
const MAX_BODY = Number(process.env.MAX_BODY_BYTES ?? 15_000_000); // ~15MB, covers base64 images

type Bucket = { count: number; reset: number };
const buckets = new Map<string, Bucket>();

function clientIp(req: NextRequest): string {
  const xff = req.headers.get("x-forwarded-for");
  if (xff) return xff.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "unknown";
}

export function rateLimit(req: NextRequest): NextResponse | null {
  const now = Date.now();
  const ip = clientIp(req);
  const b = buckets.get(ip);
  if (!b || now > b.reset) {
    buckets.set(ip, { count: 1, reset: now + WINDOW_MS });
  } else if (++b.count > MAX_REQ) {
    return NextResponse.json(
      { error: "Rate limit exceeded. Try again later." },
      { status: 429, headers: { "Retry-After": String(Math.ceil((b.reset - now) / 1000)) } },
    );
  }
  if (buckets.size > 10_000) for (const [k, v] of buckets) if (now > v.reset) buckets.delete(k);
  return null;
}

// Rate-limit + payload-size gate. Call at the top of every handler.
export function guard(req: NextRequest): NextResponse | null {
  const rl = rateLimit(req);
  if (rl) return rl;
  const len = Number(req.headers.get("content-length") ?? 0);
  if (len > MAX_BODY) return NextResponse.json({ error: "Payload too large" }, { status: 413 });
  return null;
}

// Generic 500 that never leaks internals; logs server-side only.
export function safeError(e: unknown): NextResponse {
  console.error("[api] error:", e);
  return NextResponse.json({ error: "Internal server error" }, { status: 500 });
}

type Block = { type: string; text?: string };
// Safely pull the first text block from an Anthropic message; throws (-> safeError) if none.
export function extractText(msg: { content: Block[] }): string {
  const block = msg.content.find((b) => b.type === "text" && typeof b.text === "string");
  if (!block?.text) throw new Error("model response contained no text block");
  return block.text;
}

// Parse model JSON, tolerating ```json fences. Throws (-> safeError) on invalid JSON.
export function safeJson<T = unknown>(text: string): T {
  const cleaned = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  return JSON.parse(cleaned) as T;
}
