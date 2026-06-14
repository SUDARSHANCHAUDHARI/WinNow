import { spawn } from "node:child_process";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";

const ENGINE = path.join(process.cwd(), "..", "engine", "winnow.py");
const ALLOWED_SOURCES = ["appstore", "playstore", "reddit", "pantip", "youtube", "x"];

export const runtime = "nodejs";
export const maxDuration = 120;

type CompareBody = {
  topic?: string;
  vs?: string[];
  sources?: string[];
  contextExclude?: string;
};

function runCompare(topic: string, vs: string[], sources: string[], exclude?: string): Promise<unknown> {
  const args = [ENGINE, topic];
  for (const v of vs) args.push("--vs", v);
  args.push("--sources", sources.join(","), "--limit", "25", "--emit", "json");
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
  let body: CompareBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const topic = (body.topic ?? "").trim();
  const vs = (body.vs ?? []).map((v) => v.trim()).filter(Boolean);
  if (!topic || vs.length === 0) {
    return NextResponse.json({ error: "topic and at least one --vs entity are required" }, { status: 400 });
  }

  const sources = (body.sources ?? ["appstore"]).filter((s) => ALLOWED_SOURCES.includes(s));
  if (sources.length === 0) {
    return NextResponse.json({ error: `sources must be a subset of ${ALLOWED_SOURCES.join(", ")}` }, { status: 400 });
  }

  try {
    return NextResponse.json(await runCompare(topic, vs, sources, body.contextExclude));
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "compare failed" }, { status: 500 });
  }
}
