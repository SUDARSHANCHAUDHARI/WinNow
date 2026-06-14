import { spawn } from "node:child_process";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";

const TRENDS = path.join(process.cwd(), "..", "engine", "trends.py");

export const runtime = "nodejs";

function runTrends(topic: string): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", [TRENDS, topic], { cwd: path.dirname(TRENDS) });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d) => (out += d));
    proc.stderr.on("data", (d) => (err += d));
    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) return reject(new Error(err || `trends exited ${code}`));
      try {
        resolve(JSON.parse(out));
      } catch {
        reject(new Error("trends did not return valid JSON"));
      }
    });
  });
}

export async function GET(req: NextRequest) {
  const topic = (req.nextUrl.searchParams.get("topic") ?? "").trim();
  if (!topic) {
    return NextResponse.json({ error: "topic is required" }, { status: 400 });
  }
  try {
    return NextResponse.json(await runTrends(topic));
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "trends failed" },
      { status: 500 },
    );
  }
}
