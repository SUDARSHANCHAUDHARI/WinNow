import { spawn } from "node:child_process";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";
import { guard, safeError } from "../../../lib/apiGuard";

// Engine lives at <repo>/engine/winnow.py; this app is <repo>/winnow-web.
const ENGINE = path.join(process.cwd(), "..", "engine", "winnow.py");
const ALLOWED_SOURCES = ["appstore", "playstore", "reddit", "pantip", "youtube", "x"];

export const runtime = "nodejs";
export const maxDuration = 120;

type RunBody = {
  topic?: string;
  sources?: string[];
  limit?: number;
  contextExclude?: string;
};

function runEngine(topic: string, sources: string[], limit: number, exclude?: string): Promise<unknown> {
  // spawn with an arg array (never a shell string) so the topic can't inject.
  const args = [
    ENGINE,
    topic,
    "--sources",
    sources.join(","),
    "--limit",
    String(limit),
    "--emit",
    "json",
    "--store", // persist every run so the trend view accumulates history
  ];
  if (exclude && exclude.trim()) args.push("--context-exclude", exclude.trim());
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", args, { cwd: path.dirname(ENGINE) });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d) => (out += d));
    proc.stderr.on("data", (d) => (err += d));
    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) return reject(new Error(err || `engine exited ${code}`));
      try {
        resolve(JSON.parse(out));
      } catch {
        reject(new Error("engine did not return valid JSON"));
      }
    });
  });
}

export async function POST(req: NextRequest) {
  const _guard = guard(req);
  if (_guard) return _guard;
  let body: RunBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const topic = (body.topic ?? "").trim();
  if (!topic) {
    return NextResponse.json({ error: "topic is required" }, { status: 400 });
  }

  const sources = (body.sources ?? ["appstore"]).filter((s) =>
    ALLOWED_SOURCES.includes(s),
  );
  if (sources.length === 0) {
    return NextResponse.json(
      { error: `sources must be a subset of ${ALLOWED_SOURCES.join(", ")}` },
      { status: 400 },
    );
  }

  const limit = Math.min(Math.max(Number(body.limit) || 25, 1), 50);

  try {
    const brief = await runEngine(topic, sources, limit, body.contextExclude);
    return NextResponse.json(brief);
  } catch (e) {
    return safeError(e);
  }
}
